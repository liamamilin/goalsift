"""Domain data models — single source of truth for Phase A object schemas.

Implements the field and enum contracts defined authoritatively in
`05_DATA_AND_ARTIFACTS.md`. These are the minimal, spec-compliant structures
used by the M1 Spike and grown in later milestones. Enums are defined here
only; do not create inconsistent local enums elsewhere (AGENTS.md §6).

Status definitions (05 §9 Assessment) are reproduced in docstrings so that
`SUPPORTED` vs `VERIFIED` cannot be confused.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

__all__ = [
    # enums
    "JobStatus",
    "ActionType",
    "Obligation",
    "Dimension",
    "ConditionRelation",
    "ValidityStatus",
    "DiscoveryStatus",
    "AssessmentStatus",
    "ReviewStatus",
    "ProposalValidity",
    "Provenance",
    "EvidenceStance",
    "SourceType",
    # models
    "ResearchJob",
    "Goal",
    "Condition",
    "Resource",
    "Capability",
    "Evidence",
    "Assessment",
    "Proposal",
    "ResearchEvent",
    "new_id",
]


def new_id(prefix: str) -> str:
    """Stable, unique ID with a human-meaningful prefix; IDs are referenced by ID."""
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --- Enums (authoritative definitions per 04/05) ---------------------------


class JobStatus(str, Enum):
    """Single authority: 04_AGENT_RUNTIME.md §3. Do not redefine elsewhere."""

    CREATED = "CREATED"
    RESEARCHING = "RESEARCHING"
    NEEDS_INPUT = "NEEDS_INPUT"
    PAUSED = "PAUSED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


# Allowed transitions per 04 §3 table.
ALLOWED_TRANSITIONS: dict[JobStatus, frozenset[JobStatus]] = {
    JobStatus.CREATED: frozenset({JobStatus.RESEARCHING, JobStatus.CANCELLED}),
    JobStatus.RESEARCHING: frozenset({
        JobStatus.NEEDS_INPUT, JobStatus.PAUSED, JobStatus.PARTIAL,
        JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED,
    }),
    JobStatus.NEEDS_INPUT: frozenset({JobStatus.RESEARCHING, JobStatus.PAUSED, JobStatus.CANCELLED}),
    JobStatus.PAUSED: frozenset({JobStatus.RESEARCHING, JobStatus.CANCELLED}),
    JobStatus.PARTIAL: frozenset({JobStatus.RESEARCHING, JobStatus.CANCELLED}),
    JobStatus.FAILED: frozenset({JobStatus.RESEARCHING, JobStatus.CANCELLED}),
    JobStatus.COMPLETED: frozenset({JobStatus.RESEARCHING}),  # Refine -> new revision -> RESEARCHING
    JobStatus.CANCELLED: frozenset(),  # terminal
}


class ActionType(str, Enum):
    """04 §4 action kinds."""
    REASON = "REASON"
    SEARCH = "SEARCH"
    INSPECT = "INSPECT"
    VERIFY = "VERIFY"
    REVISE = "REVISE"
    ASK_USER = "ASK_USER"
    PROPOSE = "PROPOSE"
    FINISH = "FINISH"


class Obligation(str, Enum):
    """02 §3, 05 §5 — independent of dimension."""
    REQUIRED = "REQUIRED"
    OPTIONAL = "OPTIONAL"


class Dimension(str, Enum):
    """02 §3, 05 §5 — independent of obligation."""
    FUNCTIONAL = "FUNCTIONAL"
    QUALITY = "QUALITY"
    COMPLIANCE = "COMPLIANCE"
    OTHER = "OTHER"


class ConditionRelation(str, Enum):
    """02 §3 relation semantics."""
    ALL_OF = "ALL_OF"
    ANY_OF = "ANY_OF"
    REQUIRES = "REQUIRES"


class ValidityStatus(str, Enum):
    """05 §5 — validity for current revision, NOT real-world satisfaction."""
    ACTIVE = "ACTIVE"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    SUPERSEDED = "SUPERSEDED"


class DiscoveryStatus(str, Enum):
    """05 §6."""
    CONFIRMED_EXISTENCE = "CONFIRMED_EXISTENCE"
    UNVERIFIED_LEAD = "UNVERIFIED_LEAD"


class AssessmentStatus(str, Enum):
    """05 §9 — single authority. Do not confuse SUPPORTED with VERIFIED."""

    VERIFIED = "VERIFIED"
    """Actual test/human-review record under stated acceptance conditions."""

    SUPPORTED = "SUPPORTED"
    """Located, read source supports the claim, but NOT yet verified under conditions."""

    PARTIAL = "PARTIAL"
    """Only some aspects covered; gap explicit."""

    NOT_SATISFIED = "NOT_SATISFIED"
    """Evidence shows not satisfied in stated context."""

    UNKNOWN = "UNKNOWN"
    """No sufficient basis; must not guess."""

    CONFLICTED = "CONFLICTED"
    """Evidence conflict on key claim, unresolved."""


class ReviewStatus(str, Enum):
    """05 §9 — independent of satisfaction status."""
    CURRENT = "CURRENT"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    SUPERSEDED = "SUPERSEDED"


class ProposalValidity(str, Enum):
    """05 §10."""
    CANDIDATE = "CANDIDATE"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    SUPERSEDED = "SUPERSEDED"


class Provenance(str, Enum):
    """05 §4."""
    USER_STATED = "USER_STATED"
    USER_CONFIRMED = "USER_CONFIRMED"
    SYSTEM_ASSUMED = "SYSTEM_ASSUMED"


class EvidenceStance(str, Enum):
    """05 §8."""
    SUPPORTS = "SUPPORTS"
    REFUTES = "REFUTES"
    CONTEXT = "CONTEXT"


class SourceType(str, Enum):
    """05 §8."""
    OFFICIAL_DOC = "OFFICIAL_DOC"
    SOURCE_CODE = "SOURCE_CODE"
    THIRD_PARTY = "THIRD_PARTY"
    USER_MATERIAL = "USER_MATERIAL"
    TEST_OR_REVIEW = "TEST_OR_REVIEW"


# --- Base -------------------------------------------------------------------


class _Base(BaseModel):
    model_config = {"frozen": False, "extra": "forbid"}

    id: str
    job_id: str
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


# --- Research Job (05 §3) ---------------------------------------------------


class ResearchJob(_Base):
    original_request: str
    current_goal_id: str | None = None
    current_revision: int = 1
    status: JobStatus = JobStatus.CREATED
    budget_config: dict[str, Any] = Field(default_factory=dict)
    budget_usage: dict[str, Any] = Field(default_factory=dict)
    active_run_id: str | None = None
    checkpoint_ref: str | None = None
    open_questions: list[str] = Field(default_factory=list)


# --- Goal (05 §4) -----------------------------------------------------------


class _Provenanced(BaseModel):
    provenance: Provenance = Provenance.SYSTEM_ASSUMED


class Goal(_Base):
    statement: str
    purpose: str | None = None
    requirements: list[dict[str, Any]] = Field(default_factory=list)
    constraints: list[dict[str, Any]] = Field(default_factory=list)
    assumptions: list[dict[str, Any]] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    revision: int = 1
    original_user_text: str = ""  # never overwritten
    # Explicit review decisions survive later model derivations. Removed items
    # remain here for traceability; they are never physical deletions.
    condition_decisions: list[dict[str, Any]] = Field(default_factory=list)
    assumption_decisions: list[dict[str, Any]] = Field(default_factory=list)


# --- Condition (05 §5) -------------------------------------------------------


class Condition(_Base):
    statement: str
    obligation: Obligation
    dimension: Dimension
    origin: str
    provenance: Provenance = Provenance.SYSTEM_ASSUMED
    lineage_id: str | None = None
    source_refs: list[str] = Field(default_factory=list)
    scope: str | None = None
    verification_method: str | None = None
    relations: list[dict[str, Any]] = Field(default_factory=list)
    validity_status: ValidityStatus = ValidityStatus.ACTIVE
    revision_created: int = 1

    @field_validator("obligation", "dimension", mode="before")
    @classmethod
    def _coerce_enum(cls, v: Any) -> Any:
        return v


# --- Resource (05 §6) --------------------------------------------------------


class Resource(_Base):
    name: str
    kind: str
    description: str = ""
    canonical_source: str = ""
    source_references: list[str] = Field(default_factory=list)
    version_or_revision: str | None = None
    availability: str | None = None
    license_claim: str | None = None  # None/UNKNOWN when not found (05 §6)
    environment: str | None = None
    discovery_status: DiscoveryStatus = DiscoveryStatus.UNVERIFIED_LEAD
    discovered_at: datetime = Field(default_factory=_now)


# --- Capability (05 §7) ------------------------------------------------------


class Capability(_Base):
    resource_id: str
    statement: str
    preconditions: list[str] = Field(default_factory=list)
    interface_or_use: str | None = None
    effects: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


# --- Evidence (05 §8) --------------------------------------------------------


class Evidence(_Base):
    claim: str
    source_type: SourceType
    source_ref: str  # URL or internal resolvable ref
    locator: str = ""
    excerpt_or_summary: str = ""
    retrieved_at: datetime = Field(default_factory=_now)
    source_version: str | None = None
    collection_method: str = ""
    stance: EvidenceStance = EvidenceStance.SUPPORTS
    verification_method: str | None = None
    test_context: str | None = None
    observed_result: str | None = None


# --- Assessment (05 §9) ------------------------------------------------------


class Assessment(_Base):
    condition_id: str
    resource_ids: list[str] = Field(default_factory=list)
    capability_ids: list[str] = Field(default_factory=list)
    context: str = ""
    status: AssessmentStatus = AssessmentStatus.UNKNOWN
    evidence_ids: list[str] = Field(default_factory=list)
    explanation: str = ""
    gaps: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    review_status: ReviewStatus = ReviewStatus.CURRENT
    revision_evaluated: int = 1


# --- Proposal (05 §10) ------------------------------------------------------


class Proposal(_Base):
    title: str
    summary: str
    resource_ids: list[str] = Field(default_factory=list)
    assessment_ids: list[str] = Field(default_factory=list)
    condition_coverage: list[str] = Field(default_factory=list)
    integration_work: list[str] = Field(default_factory=list)
    new_work: list[str] = Field(default_factory=list)
    uncovered_conditions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    costs: dict[str, Any] = Field(default_factory=dict)
    recommendation_reason: str = ""
    validity_status: ProposalValidity = ProposalValidity.CANDIDATE
    revision_created: int = 1


# --- Research Event (05 §11) ------------------------------------------------


class ResearchEvent(_Base):
    event_id: str
    revision: int
    run_id: str | None = None
    action_type: ActionType
    status: str = ""
    started_at: datetime = Field(default_factory=_now)
    ended_at: datetime | None = None
    related_object_ids: list[str] = Field(default_factory=list)
    tool_result_ref: str | None = None
    usage: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
