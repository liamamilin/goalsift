"""Budget guard — hard execution limits enforced by the backend (04 §7).

The Controller consults this before every external action (model call, search,
source read). Limits come from env config; exceeding any limit stops new
external actions and forces PARTIAL delivery. Never relies on the prompt.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any

from .config import load_env

load_env()


@dataclass
class BudgetConfig:
    max_actions: int = int(os.environ.get("GOALSIFT_MAX_ACTIONS") or 30)
    max_tool_calls: int = int(os.environ.get("GOALSIFT_MAX_TOOL_CALLS") or 20)
    max_runtime_seconds: int = int(os.environ.get("GOALSIFT_MAX_RUNTIME_SECONDS") or 300)
    budget_usd: float | None = (
        float(os.environ.get("GOALSIFT_BUDGET_USD"))
        if os.environ.get("GOALSIFT_BUDGET_USD") else None
    )


@dataclass
class BudgetUsage:
    actions: int = 0
    tool_calls: int = 0
    cost_usd: float = 0.0
    started_at: float = field(default_factory=time.monotonic)
    stopped_reason: str | None = None

    def snapshot(self) -> dict[str, Any]:
        return {
            "actions": self.actions,
            "tool_calls": self.tool_calls,
            "cost_usd": round(self.cost_usd, 6),
            "elapsed_seconds": round(time.monotonic() - self.started_at, 1),
            "stopped_reason": self.stopped_reason,
        }


class BudgetExhausted(RuntimeError):
    """Raised when a hard limit is reached; the Controller catches it to PARTIAL."""


class BudgetGuard:
    def __init__(self, config: BudgetConfig | None = None) -> None:
        self.config = config or BudgetConfig()
        self.usage = BudgetUsage()

    def check(self, *, tool_call: bool = False, cost_increment: float = 0.0) -> None:
        """Raise BudgetExhausted if any hard limit is exceeded."""
        self.usage.actions += 1
        if tool_call:
            self.usage.tool_calls += 1
        if cost_increment:
            self.usage.cost_usd += cost_increment
        elapsed = time.monotonic() - self.usage.started_at
        reason = None
        if self.usage.actions > self.config.max_actions:
            reason = "max_actions"
        elif self.usage.tool_calls > self.config.max_tool_calls:
            reason = "max_tool_calls"
        elif elapsed > self.config.max_runtime_seconds:
            reason = "max_runtime"
        elif (self.config.budget_usd is not None
              and self.usage.cost_usd > self.config.budget_usd):
            reason = "budget_usd"
        if reason:
            self.usage.stopped_reason = reason
            raise BudgetExhausted(f"budget exhausted: {reason}")

    def cost_unknown_prompt(self) -> str:
        """05 §10 / 04 §7: when model price is unavailable, show 'cost unknown'."""
        if self.config.budget_usd is None:
            return "cost_unknown: no spend cap configured; token usage tracked, USD cost unknown"
        return ""
