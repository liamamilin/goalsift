"""User decisions, separate from source evidence and satisfaction judgments."""
from __future__ import annotations
import re
from typing import Literal
from pydantic import BaseModel, Field, model_validator
from .models import Dimension, Obligation


class ConditionEdit(BaseModel):
    model_config = {'extra': 'forbid'}
    condition_id: str
    action: Literal['confirm', 'update', 'remove']
    statement: str | None = Field(default=None, min_length=1, max_length=2000)
    obligation: Obligation | None = None
    dimension: Dimension | None = None
    verification_method: str | None = Field(default=None, max_length=2000)

    @model_validator(mode='after')
    def valid_edit(self):
        changed = any(v is not None for v in (self.statement, self.obligation,
                                             self.dimension, self.verification_method))
        if self.action != 'update' and changed:
            raise ValueError('确认或移除不能同时修改条件')
        if self.action == 'update' and not changed:
            raise ValueError('修改需要填写变更')
        if self.statement is not None:
            self.statement = self.statement.strip()
            if not self.statement: raise ValueError('条件不能为空')
        return self


class AssumptionEdit(BaseModel):
    model_config = {'extra': 'forbid'}
    index: int = Field(ge=0)
    action: Literal['confirm', 'remove']


class GoalReview(BaseModel):
    model_config = {'extra': 'forbid'}
    expected_revision: int = Field(ge=1)
    conditions: list[ConditionEdit] = Field(default_factory=list, max_length=30)
    assumptions: list[AssumptionEdit] = Field(default_factory=list, max_length=20)
    purpose: str | None = Field(default=None, min_length=1, max_length=2000)

    @model_validator(mode='after')
    def unique_edits(self):
        if not self.conditions and not self.assumptions and self.purpose is None:
            raise ValueError('至少提交一项调整')
        if len({e.condition_id for e in self.conditions}) != len(self.conditions):
            raise ValueError('同一条件不能重复调整')
        if len({e.index for e in self.assumptions}) != len(self.assumptions):
            raise ValueError('同一假设不能重复调整')
        if self.purpose is not None:
            self.purpose = self.purpose.strip()
            if not self.purpose: raise ValueError('目标理解不能为空')
        return self


def normalized(text: str) -> str:
    # Operators, punctuation and case can distinguish code or API requirements.
    return re.sub(r'\s+', ' ', text.strip())


def review_context(goal) -> str:
    """Explicit corrections take precedence over the original wording."""
    lines = []
    for d in goal.condition_decisions:
        if d['action'] == 'remove':
            lines.append('用户已移出目标的条件，禁止重新加入：' + d['original_statement'])
        else:
            lines.append(f"用户已确认条件（{d['obligation']} / {d['dimension']}）：{d['statement']}")
            if normalized(d['original_statement']) != normalized(d['statement']):
                lines.append('以上条件替代原推导：' + d['original_statement'])
    for d in goal.assumption_decisions:
        lines.append(('用户已确认前提：' if d['action'] == 'confirm' else '用户已移除假设，禁止作为要求：') + d['text'])
    return '\n'.join(lines)
