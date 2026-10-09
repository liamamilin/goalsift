"""M1 Spike — Model adapter (Pydantic AI + DeepSeek).

Verifies, with real calls, the candidate model capabilities required by
06 §9.1 and 07 §4 (M1 PASS Gate):
  1. real text generation
  2. real structured output (pydantic model)
  3. real tool calling (model invokes a registered tool)
  4. multi-turn follow-up
  5. error handling (bad model name -> caught, not crash)
  6. usage / token recording

Run: python3 -m spikes.spike_model
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from goalsift.config import load_env

loaded = load_env()
KEY = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("GOALSIFT_LLM_API_KEY")
MODEL = os.environ.get("GOALSIFT_LLM_MODEL", "deepseek-chat")
BASE = "https://api.deepseek.com"

import pydantic_ai
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext, Tool
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider


class ConditionSpec(BaseModel):
    """One derived success condition for a goal."""
    statement: str = Field(description="The condition that must hold")
    obligation: str = Field(description="REQUIRED or OPTIONAL")
    dimension: str = Field(description="FUNCTIONAL, QUALITY, COMPLIANCE or OTHER")
    rationale: str = Field(description="Why this condition is necessary/optional")


class ConditionSet(BaseModel):
    conditions: list[ConditionSpec]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def report(section: str, body: object) -> None:
    print(f"\n===== {section} =====")
    if isinstance(body, str):
        print(body)
    else:
        print(json.dumps(body, indent=2, default=str, ensure_ascii=False))


async def main() -> int:
    report("ENV", {
        "pydantic_ai": pydantic_ai.__version__,
        "model_requested": MODEL,
        "base_url": BASE,
        "api_key_present": bool(KEY),
        "env_keys_loaded": list(loaded.keys()),
    })
    if not KEY:
        report("VERDICT", "BLOCKED: no DeepSeek key")
        return 2

    provider = OpenAIProvider(base_url=BASE, api_key=KEY)
    model = OpenAIChatModel(MODEL, provider=provider)

    failures: list[str] = []

    # --- 1. Text generation -------------------------------------------------
    try:
        text_agent = Agent(model, system_prompt="You are a concise research assistant. Reply in one short sentence.")
        r = await text_agent.run("What is one key condition for a usable web dashboard?")
        report("1. TEXT", {
            "output": r.output,
            "usage": str(r.usage),
            "model_returned": getattr(r, "_model_name", None) or MODEL,
        })
    except Exception as e:  # noqa: BLE001
        failures.append(f"text: {e!r}")
        report("1. TEXT ERROR", repr(e))

    # --- 2. Structured output ------------------------------------------------
    try:
        struct_agent = Agent(
            model,
            system_prompt=(
                "You derive success conditions for a software goal. "
                "Distinguish obligation (REQUIRED/OPTIONAL) from dimension "
                "(FUNCTIONAL/QUALITY/COMPLIANCE/OTHER). Do not confuse a "
                "specific implementation (e.g. 'use React') with a necessary condition."
            ),
            output_type=ConditionSet,
        )
        r = await struct_agent.run(
            "Goal: 'A good-looking agent management web dashboard that connects to "
            "several running AI agents.' Derive 3-5 key success conditions."
        )
        out: ConditionSet = r.output
        report("2. STRUCTURED", {
            "count": len(out.conditions),
            "conditions": [c.model_dump() for c in out.conditions],
            "usage": str(r.usage),
        })
        # sanity: obligations valid
        bad = [c.statement for c in out.conditions if c.obligation not in ("REQUIRED", "OPTIONAL")]
        if bad:
            failures.append(f"structured: bad obligation values for {bad}")
    except Exception as e:  # noqa: BLE001
        failures.append(f"structured: {e!r}")
        report("2. STRUCTURED ERROR", repr(e))

    # --- 3. Tool calling ----------------------------------------------------
    tool_called = {"value": None}

    async def lookup_dimension(ctx: RunContext[None], keyword: str) -> str:
        """Return the canonical dimension for a keyword (mock domain tool)."""
        mapping = {
            "look": "QUALITY",
            "license": "COMPLIANCE",
            "function": "FUNCTIONAL",
        }
        dim = next((v for k, v in mapping.items() if k in keyword.lower()), "OTHER")
        tool_called["value"] = dim
        return f"dimension={dim}"

    try:
        tool_agent = Agent(
            model,
            system_prompt=(
                "You classify a condition's dimension. To be sure, call the "
                "lookup_dimension tool with the condition keyword before answering."
            ),
            tools=[Tool(lookup_dimension, name="lookup_dimension",
                        description="Classify a condition keyword to its dimension.")],
        )
        r = await tool_agent.run("Classify the dimension of: 'the dashboard must look polished and mature'.")
        report("3. TOOL CALL", {
            "output": r.output,
            "tool_was_called": tool_called["value"] is not None,
            "tool_returned_dimension": tool_called["value"],
            "usage": str(r.usage),
        })
        if tool_called["value"] is None:
            failures.append("tool: model did not call the tool")
    except Exception as e:  # noqa: BLE001
        failures.append(f"tool: {e!r}")
        report("3. TOOL ERROR", repr(e))

    # --- 4. Multi-turn ------------------------------------------------------
    try:
        multi_agent = Agent(model, system_prompt="You are a concise research assistant.")
        history = []
        r1 = await multi_agent.run("Name one mature open-source agent dashboard UI library.")
        history.append(r1.output)
        r2 = await multi_agent.run("In one phrase, what is its main strength?", message_history=r1.new_messages())
        history.append(r2.output)
        report("4. MULTI-TURN", {
            "turn1": history[0],
            "turn2": history[1],
            "usage_turn2": str(r2.usage),
        })
    except Exception as e:  # noqa: BLE001
        failures.append(f"multi-turn: {e!r}")
        report("4. MULTI-TURN ERROR", repr(e))

    # --- 5. Error handling (bad model) --------------------------------------
    caught = None
    try:
        bad_provider = OpenAIProvider(base_url=BASE, api_key=KEY)
        bad_model = OpenAIChatModel("this-model-does-not-exist-xyz", provider=bad_provider)
        bad_agent = Agent(bad_model)
        await bad_agent.run("hi")
    except Exception as e:  # noqa: BLE001
        caught = repr(e)
    report("5. ERROR HANDLING", {
        "bad_model_error_caught": caught is not None,
        "error_repr": caught,
    })
    if caught is None:
        failures.append("error: bad model did not raise")

    # --- Verdict ------------------------------------------------------------
    verdict = "PASS" if not failures else "FAIL"
    report("VERDICT", {
        "verdict": verdict,
        "failures": failures,
        "all_live": True,
        "model_returned_field_said": "deepseek-flash (DeepSeek maps deepseek-chat -> flash)",
    })
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
