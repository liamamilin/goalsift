"""LLM adapter — wraps Pydantic AI + DeepSeek.

The model produces *candidate* data; nothing here writes trusted state.
Trusted writes go through the Repository + Validators (04 §5).
"""

from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from .config import load_env

load_env()
_KEY = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("GOALSIFT_LLM_API_KEY")
_MODEL = os.environ.get("GOALSIFT_LLM_MODEL", "deepseek-chat")
_BASE = "https://api.deepseek.com"


class ConditionSpec(BaseModel):
    statement: str
    obligation: str = Field(description="REQUIRED or OPTIONAL")
    dimension: str = Field(description="FUNCTIONAL/QUALITY/COMPLIANCE/OTHER")
    rationale: str = ""


class ConditionSet(BaseModel):
    conditions: list[ConditionSpec]


class ResourceMatch(BaseModel):
    """Model's candidate assessment of a resource against a condition."""
    condition_statement: str
    resource_name: str
    status: str  # SUPPORTED / UNKNOWN / NOT_SATISFIED / PARTIAL
    explanation: str
    gaps: list[str] = Field(default_factory=list)


class MatchSet(BaseModel):
    matches: list[ResourceMatch]


class ChallengeFinding(BaseModel):
    """One counterexample finding from the Challenge operation."""
    kind: str = Field(description="completeness / necessity / consistency")
    target_condition: str
    finding: str
    recommendation: str = Field(description="keep / mark_optional / supersede / add_condition")


class ChallengeReport(BaseModel):
    findings: list[ChallengeFinding]
    revised: bool = False


class ProposalDraft(BaseModel):
    title: str
    summary: str
    recommendation_reason: str
    integration_work: list[str] = Field(default_factory=list)
    new_work: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


def _provider() -> OpenAIProvider:
    return OpenAIProvider(base_url=_BASE, api_key=_KEY)


def _model() -> OpenAIChatModel:
    return OpenAIChatModel(_MODEL, provider=_provider())


class LLMAdapter:
    """Thin wrapper; each method is one model role in the pipeline."""

    def __init__(self) -> None:
        self._cond_agent = Agent(
            _model(),
            system_prompt=(
                "You derive success conditions for a software goal. Separate obligation "
                "(REQUIRED/OPTIONAL) from dimension (FUNCTIONAL/QUALITY/COMPLIANCE/OTHER). "
                "Do NOT confuse a specific implementation (e.g. 'use React') with a necessary "
                "condition. Return 3-5 conditions."
            ),
            output_type=ConditionSet,
        )
        self._match_agent = Agent(
            _model(),
            system_prompt=(
                "You assess whether a real resource satisfies a condition. Use only the "
                "provided source text. If the source supports the claim, say SUPPORTED. "
                "If the source shows it fails, say NOT_SATISFIED. If insufficient evidence, "
                "say UNKNOWN. Never say VERIFIED — that requires an environment test you "
                "cannot perform. Mark license claims UNKNOWN unless the source explicitly "
                "names a recognized open-source license."
            ),
            output_type=MatchSet,
        )
        self._propose_agent = Agent(
            _model(),
            system_prompt=(
                "You draft a candidate implementation proposal reusing discovered resources. "
                "Be honest about gaps, license unknowns and risks. Do not fabricate costs; "
                "use 'UNKNOWN' when no pricing exists. Never claim execution."
            ),
            output_type=ProposalDraft,
        )
        self._challenge_agent = Agent(
            _model(),
            system_prompt=(
                "You challenge a condition model (02 §4.3). Run three checks:\n"
                "1. COMPLETENESS: if all conditions were satisfied, could the goal still "
                "fail for a reasonable reason not covered? Add the missing condition.\n"
                "2. NECESSITY: is any REQUIRED condition actually not necessary — could the "
                "goal still be met without it via another path? Mark it optional.\n"
                "3. CONSISTENCY: do any conditions conflict or smuggle a specific "
                "implementation (React/REST) as a universal necessity? Supersede or revise.\n"
                "Return concrete findings with a recommendation per condition. Be honest; "
                "'keep' is valid when no real counterexample exists."
            ),
            output_type=ChallengeReport,
        )

    async def derive_conditions(self, goal_text: str) -> list[ConditionSpec]:
        r = await self._cond_agent.run(f"Goal: {goal_text}")
        return r.output.conditions

    async def assess_resources(
        self, goal_text: str, conditions: list[str], resources: list[dict[str, Any]]
    ) -> list[ResourceMatch]:
        prompt = (
            f"Goal: {goal_text}\n\nConditions:\n"
            + "\n".join(f"- {c}" for c in conditions)
            + "\n\nDiscovered resources (with source text excerpts):\n"
        )
        for res in resources:
            prompt += (
                f"\n## {res['name']}\nurl: {res['url']}\nlicense: {res.get('license','UNKNOWN')}\n"
                f"source text:\n{res.get('text','')[:800]}\n"
            )
        prompt += (
            "\nFor each resource, assess whether it satisfies each condition. "
            "Return one match per (condition, resource)."
        )
        r = await self._match_agent.run(prompt)
        return r.output.matches

    async def draft_proposal(
        self, goal_text: str, resources: list[dict[str, Any]], matches: list[ResourceMatch]
    ) -> ProposalDraft:
        prompt = (
            f"Goal: {goal_text}\n\nResources:\n"
            + "\n".join(f"- {r['name']} ({r.get('license','UNKNOWN')}): {r['url']}" for r in resources)
            + "\n\nAssessments:\n"
            + "\n".join(f"- {m.condition_statement} | {m.resource_name} | {m.status} | {m.explanation}" for m in matches)
        )
        r = await self._propose_agent.run(prompt + "\n\nDraft ONE candidate proposal reusing the best resource.")
        return r.output

    async def challenge_conditions(
        self, goal_text: str, conditions: list[dict[str, Any]]
    ) -> "ChallengeReport":
        """02 §4.3 Challenge: completeness/necessity/consistency counterexamples."""
        prompt = (
            f"Goal: {goal_text}\n\nCurrent condition model:\n"
            + "\n".join(
                f"- [{c['obligation']}/{c['dimension']}] {c['statement']}" for c in conditions
            )
            + "\n\nChallenge this model. Return findings with a per-condition recommendation."
        )
        r = await self._challenge_agent.run(prompt)
        return r.output
