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
    Dimension,
    Evidence,
    EvidenceStance,
    JobStatus,
    Obligation,
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
    "validate_condition_necessity",
    "validate_evidence_sources",
    "detect_conflict",
    "validate_conflict_handling",
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


# --- M3 evidence-integrity rules (gates 1, 4, 6) --------------------------

# Tech that is an implementation choice, not a universal necessity (02 §3).
_IMPL_TECH = (
    "react", "vue", "angular", "svelte", "next.js", "nextjs", "rest api", "rest",
    "graphql", "node.js", "nodejs", "express", "django", "fastapi", "flask",
    "postgres", "postgresql", "mysql", "mongodb", "redis", "typescript",
    "websocket", "grpc", "kafka",
)


def validate_condition_necessity(conditions: list[Condition]) -> list[str]:
    """Gate 4 (07 §6): a generic goal must not treat a specific implementation
    (React/REST/Node/...) as a REQUIRED-FUNCTIONAL condition. Such conditions
    are flagged as solution-dependency smuggled into goal conditions (02 §3)."""
    problems: list[str] = []
    for c in conditions:
        if c.obligation != Obligation.REQUIRED or c.dimension != Dimension.FUNCTIONAL:
            continue
        text = c.statement.lower()
        hit = next((t for t in _IMPL_TECH if t in text), None)
        if hit and "model-derived" in (c.origin or "").lower():
            problems.append(
                f"condition {c.id} asserts '{hit}' as REQUIRED+FUNCTIONAL — "
                f"likely solution-dependency, not a goal necessity (challenge it)"
            )
    return problems


def validate_evidence_sources(
    evidence: list[Evidence], fetched_urls: set[str]
) -> list[str]:
    """Gate 1 (07 §6): model-fabricated URLs/claims cannot become confirmed
    sources. Every Evidence.source_ref must appear in the set of URLs actually
    fetched by a real tool call."""
    problems: list[str] = []
    for e in evidence:
        if not e.source_ref:
            problems.append(f"evidence {e.id} has empty source_ref")
            continue
        if e.source_ref not in fetched_urls:
            problems.append(
                f"evidence {e.id} source_ref '{e.source_ref}' was NOT produced "
                f"by a real tool fetch — fabricated source rejected"
            )
    return problems


def detect_conflict(assessment: Assessment, evidence: list[Evidence]) -> bool:
    """Gate 6 (07 §6): if evidence on a claim is both SUPPORTS and REFUTES,
    the assessment must be CONFLICTED, not silently resolved."""
    ev = [e for e in evidence if e.id in assessment.evidence_ids]
    has_supports = any(e.stance == EvidenceStance.SUPPORTS for e in ev)
    has_refutes = any(e.stance == EvidenceStance.REFUTES for e in ev)
    return has_supports and has_refutes


def validate_conflict_handling(
    assessments: list[Assessment], evidence: list[Evidence]
) -> list[str]:
    """Gate 6: assessments with contradictory evidence must be CONFLICTED,
    never VERIFIED/SUPPORTED/NOT_SATISFIED."""
    problems: list[str] = []
    for a in assessments:
        if detect_conflict(a, evidence) and a.status != AssessmentStatus.CONFLICTED:
            problems.append(
                f"assessment {a.id} has SUPPORTS+REFUTES evidence but status="
                f"{a.status.value}; must be CONFLICTED"
            )
    return problems
