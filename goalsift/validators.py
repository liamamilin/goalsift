"""Deterministic validators — the only trusted write gate (04 §5).

Model output and fetched content are untrusted; these validators enforce the
05 invariants before objects become trusted state. Used by the Repository in
later milestones and by the M1 Spike to prove reference integrity.
"""

from __future__ import annotations

from typing import Iterable

from .models import (
    ALLOWED_TRANSITIONS,
    Assessment,
    AssessmentStatus,
    Capability,
    Condition,
    Evidence,
    JobStatus,
    Proposal,
    Resource,
    ReviewStatus,
    ValidityStatus,
)

__all__ = [
    "ValidationError",
    "validate_references",
    "validate_assessment_status",
    "validate_transition",
    "validate_traceability",
]


class ValidationError(Exception):
    """Raised when an object violates a 05 invariant."""


def _index(ids: Iterable[str]) -> set[str]:
    return set(ids)


def validate_references(
    *,
    job_id: str,
    conditions: list[Condition],
    resources: list[Resource],
    capabilities: list[Capability],
    evidence: list[Evidence],
    assessments: list[Assessment],
    proposals: list[Proposal],
) -> list[str]:
    """Check ID existence and ownership. Returns a list of problems (empty=ok)."""
    problems: list[str] = []
    cond_ids = _index(c.id for c in conditions)
    res_ids = _index(r.id for r in resources)
    cap_ids = _index(c.id for c in capabilities)
    ev_ids = _index(e.id for e in evidence)
    ass_ids = _index(a.id for a in assessments)

    for coll, label in [
        (conditions, "condition"), (resources, "resource"),
        (capabilities, "capability"), (evidence, "evidence"),
        (assessments, "assessment"), (proposals, "proposal"),
    ]:
        for obj in coll:
            if obj.job_id != job_id:
                problems.append(f"{label} {obj.id} job_id mismatch")
            # duplicate id
        # duplicate id check
        ids = [o.id for o in coll]
        if len(ids) != len(set(ids)):
            problems.append(f"duplicate {label} ids: {[i for i in ids if ids.count(i)>1]}")

    for cap in capabilities:
        if cap.resource_id not in res_ids:
            problems.append(f"capability {cap.id} -> missing resource {cap.resource_id}")
        for eid in cap.evidence_ids:
            if eid not in ev_ids:
                problems.append(f"capability {cap.id} -> missing evidence {eid}")

    for ev in evidence:
        if not ev.source_ref:
            problems.append(f"evidence {ev.id} has empty source_ref")

    for a in assessments:
        if a.condition_id not in cond_ids:
            problems.append(f"assessment {a.id} -> missing condition {a.condition_id}")
        for rid in a.resource_ids:
            if rid not in res_ids:
                problems.append(f"assessment {a.id} -> missing resource {rid}")
        for cid in a.capability_ids:
            if cid not in cap_ids:
                problems.append(f"assessment {a.id} -> missing capability {cid}")
        for eid in a.evidence_ids:
            if eid not in ev_ids:
                problems.append(f"assessment {a.id} -> missing evidence {eid}")

    for p in proposals:
        for rid in p.resource_ids:
            if rid not in res_ids:
                problems.append(f"proposal {p.id} -> missing resource {rid}")
        for aid in p.assessment_ids:
            if aid not in ass_ids:
                problems.append(f"proposal {p.id} -> missing assessment {aid}")
        for cid in p.condition_coverage:
            if cid not in cond_ids:
                problems.append(f"proposal {p.id} -> missing condition {cid}")

    return problems


def validate_assessment_status(a: Assessment, evidence: list[Evidence]) -> list[str]:
    """Enforce 05 §9 rules: VERIFIED needs a test/review record; SUPPORTED needs a
    located, read source. Pure documentation never promotes to VERIFIED."""
    problems: list[str] = []
    ev = [e for e in evidence if e.id in a.evidence_ids]
    if a.status == AssessmentStatus.VERIFIED:
        has_test = any(
            e.test_context is not None and e.observed_result is not None
            for e in ev
        )
        if not has_test:
            problems.append(
                f"assessment {a.id} VERIFIED requires a test/human-review record "
                f"(test_context + observed_result); doc-only evidence is not enough"
            )
    elif a.status == AssessmentStatus.SUPPORTED:
        if not any(e.source_ref for e in ev):
            problems.append(
                f"assessment {a.id} SUPPORTED requires a located, read source_ref"
            )
    elif a.status == AssessmentStatus.UNKNOWN:
        # UNKNOWN must not carry contradictory verified evidence
        pass
    return problems


def validate_transition(current: JobStatus, target: JobStatus) -> None:
    """04 §3 single authority. Illegal transitions raise."""
    allowed = ALLOWED_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise ValidationError(
            f"illegal transition {current.value} -> {target.value}; "
            f"allowed: {sorted(s.value for s in allowed) or '(terminal)'}"
        )


def validate_traceability(
    proposal: Proposal,
    assessments: list[Assessment],
    conditions: list[Condition],
    resources: list[Resource],
    capabilities: list[Capability],
    evidence: list[Evidence],
) -> list[str]:
    """05 §14: every visible proposal must trace to Condition -> Assessment ->
    Resource/Capability -> Evidence. Returns problems (empty = traceable)."""
    problems: list[str] = []
    ass_by_id = {a.id: a for a in assessments}
    cond_by_id = {c.id: c for c in conditions}
    res_by_id = {r.id: r for r in resources}
    cap_by_id = {c.id: c for c in capabilities}
    ev_by_id = {e.id: e for e in evidence}

    if not proposal.assessment_ids:
        problems.append(f"proposal {proposal.id} has no assessments (untraceable)")
    for aid in proposal.assessment_ids:
        a = ass_by_id.get(aid)
        if not a:
            problems.append(f"proposal {proposal.id} -> missing assessment {aid}")
            continue
        c = cond_by_id.get(a.condition_id)
        if not c:
            problems.append(f"proposal {proposal.id} -> assessment {aid} -> missing condition")
        if not a.evidence_ids:
            problems.append(f"proposal {proposal.id} -> assessment {aid} has no evidence")
        for eid in a.evidence_ids:
            if eid not in ev_by_id:
                problems.append(f"proposal {proposal.id} -> missing evidence {eid}")
        if not a.resource_ids and not a.capability_ids:
            problems.append(f"proposal {proposal.id} -> assessment {aid} has no resource/capability")
        for rid in a.resource_ids:
            if rid not in res_by_id:
                problems.append(f"proposal {proposal.id} -> missing resource {rid}")
        for cid in a.capability_ids:
            cap = cap_by_id.get(cid)
            if not cap:
                problems.append(f"proposal {proposal.id} -> missing capability {cid}")
            elif cap.resource_id not in res_by_id:
                problems.append(f"proposal {proposal.id} -> capability {cid} -> missing resource")
    return problems
