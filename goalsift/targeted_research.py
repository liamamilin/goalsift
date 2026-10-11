"""An explicit, bounded investigation without changing the user's goal."""
from pydantic import BaseModel, Field, model_validator


class TargetedResearch(BaseModel):
    model_config = {'extra': 'forbid'}
    expected_revision: int = Field(ge=1)
    condition_ids: list[str] = Field(min_length=1, max_length=8)
    resource_ids: list[str] = Field(default_factory=list, max_length=2)
    budget_usd: float = Field(gt=0, le=1, allow_inf_nan=False)
    question: str = Field(default='', max_length=600)

    @model_validator(mode='after')
    def unique_references(self):
        for refs in (self.condition_ids, self.resource_ids):
            if len(refs) != len(set(refs)) or any(not ref.strip() for ref in refs):
                raise ValueError('补查对象不能重复或为空')
        self.question = self.question.strip()
        return self
