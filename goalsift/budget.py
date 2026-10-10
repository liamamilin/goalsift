"""Persistent per-revision limits with reservations before external calls."""
from __future__ import annotations
import os
import time
import math
from dataclasses import dataclass, field
from typing import Any

from .config import load_env
load_env()

@dataclass
class BudgetConfig:
    max_actions: int = 30
    max_tool_calls: int = 20
    max_runtime_seconds: int = 300
    budget_usd: float | None = None
    max_model_output_tokens: int = 5000
    max_model_input_tokens: int = 50000
    max_search_rounds: int = 3
    request_timeout_seconds: int = 60

    def __post_init__(self):
        for name in ('max_actions', 'max_tool_calls', 'max_runtime_seconds',
                     'max_model_output_tokens', 'max_model_input_tokens',
                     'max_search_rounds', 'request_timeout_seconds'):
            if getattr(self, name) <= 0:
                raise ValueError(f'{name} must be positive')
        if self.budget_usd is not None and (not math.isfinite(self.budget_usd) or self.budget_usd <= 0):
            raise ValueError('budget_usd must be positive')

    @classmethod
    def from_env(cls):
        values = {}
        for name in cls.__dataclass_fields__:
            value = os.environ.get('GOALSIFT_' + name.upper())
            if value:
                values[name] = float(value) if name == 'budget_usd' else int(value)
        return cls(**values)

@dataclass
class BudgetUsage:
    actions: int = 0
    tool_calls: int = 0
    cost_usd: float = 0.0
    reserved_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    model_requests: int = 0
    cost_unknown: bool = False
    elapsed_before: float = 0.0
    started_at: float = field(default_factory=time.monotonic)
    stopped_reason: str | None = None

    def snapshot(self) -> dict[str, Any]:
        return {'actions': self.actions, 'tool_calls': self.tool_calls,
                'cost_usd': None if self.cost_unknown else round(self.cost_usd, 8),
                'known_cost_usd': round(self.cost_usd, 8), 'reserved_usd': round(self.reserved_usd, 8),
                'input_tokens': self.input_tokens, 'output_tokens': self.output_tokens,
                'model_requests': self.model_requests, 'cost_unknown': self.cost_unknown,
                'elapsed_seconds': round(self.elapsed_before + time.monotonic() - self.started_at, 2),
                'stopped_reason': self.stopped_reason}

class BudgetExhausted(RuntimeError):
    pass

class BudgetGuard:
    def __init__(self, config: BudgetConfig | None = None, previous: dict | None = None):
        self.config = config or BudgetConfig.from_env()
        p = previous or {}
        self.usage = BudgetUsage(**{k: p[k] for k in
            ('actions', 'tool_calls', 'input_tokens', 'output_tokens', 'model_requests', 'cost_unknown', 'reserved_usd')
            if k in p}, cost_usd=p.get('known_cost_usd', p.get('cost_usd')) or 0.0,
            elapsed_before=p.get('elapsed_seconds', 0.0))

    def check(self, *, tool_call: bool = False, cost_increment: float = 0.0,
              reserve_usd: float = 0.0):
        if cost_increment:
            self.usage.cost_usd += cost_increment
        elapsed = self.usage.elapsed_before + time.monotonic() - self.usage.started_at
        reason = None
        if self.usage.actions >= self.config.max_actions: reason = 'max_actions'
        elif tool_call and self.usage.tool_calls >= self.config.max_tool_calls: reason = 'max_tool_calls'
        elif elapsed >= self.config.max_runtime_seconds: reason = 'max_runtime'
        elif self.config.budget_usd is not None:
            if self.usage.cost_unknown: reason = 'cost_unknown'
            elif self.usage.cost_usd + self.usage.reserved_usd + reserve_usd > self.config.budget_usd: reason = 'budget_usd'
        if reason:
            self.usage.stopped_reason = reason
            raise BudgetExhausted(f'budget exhausted: {reason}')
        self.usage.actions += 1
        if tool_call: self.usage.tool_calls += 1

    def record(self, stats: dict):
        cost = stats.get('cost_usd', stats.get('cost_dollars', stats.get('read_cost')))
        if cost is None: self.usage.cost_unknown = True
        else: self.usage.cost_usd += float(cost)
        for name in ('input_tokens', 'output_tokens', 'model_requests'):
            setattr(self.usage, name, getattr(self.usage, name) + int(stats.get(name, 0)))
        if self.config.budget_usd is not None and self.usage.cost_usd > self.config.budget_usd:
            self.usage.stopped_reason = 'budget_usd'
            raise BudgetExhausted('budget exhausted: budget_usd')

    def remaining_seconds(self):
        return max(0.01, self.config.max_runtime_seconds - self.usage.elapsed_before
                   - (time.monotonic() - self.usage.started_at))

    def cost_unknown_prompt(self):
        return '费用未知：模型单价或服务用量未提供。' if self.usage.cost_unknown else ''
