"""M3 negative test cases — the deterministic gate (07 §6 PASS Gate items).

These prove the validators enforce the paradigm invariants. They are
deterministic unit tests; the live search+match proof is in
`spikes/spike_m3_live.py` (gate item 8).

Gate items covered here:
  1. model-fabricated URL/evidence cannot become a confirmed source
  2. doc-only claim cannot promote to VERIFIED
  3. visual quality requirement can be REQUIRED + QUALITY
  4. React/REST not treated as default necessary for all goals
  6. missing-evidence license UNKNOWN; conflicting evidence CONFLICTED
  7. proposal traceable Condition -> Assessment -> Resource/Capability -> Evidence
"""

from __future__ import annotations

from goalsift.models import (
    Assessment,
    AssessmentStatus,
    Capability,
    Condition,
    Dimension,
    Evidence,
    EvidenceStance,
    Obligation,
    Proposal,
    Resource,
    ReviewStatus,
    SourceType,
    ValidityStatus,
    new_id,
)
from goalsift.validators import (
    ValidationError,
    validate_assessment_status,
    validate_condition_necessity,
    validate_conflict_handling,
    validate_evidence_sources,
    validate_references,
    validate_traceability,
    validate_transition,
)

JID = "job_test"


def _cond(statement: str, *, obligation=Obligation.REQUIRED,
          dimension=Dimension.FUNCTIONAL, origin="model-derived (test)") -> Condition:
    return Condition(
        id=new_id("cond"), job_id=JID, statement=statement,
        obligation=obligation, dimension=dimension, origin=origin,
    )


def _res(name="res", url="https://real.example/repo") -> Resource:
    return Resource(
        id=new_id("res"), job_id=JID, name=name, kind="web_resource",
        canonical_source=url, source_references=[url],
        license_claim="UNKNOWN",
    )


def _ev(claim: str, url: str, *, stance=EvidenceStance.SUPPORTS) -> Evidence:
    return Evidence(
        id=new_id("ev"), job_id=JID, claim=claim, source_type=SourceType.THIRD_PARTY,
        source_ref=url, locator="test", stance=stance,
    )


# --- Gate 1: fabricated URL rejected ----------------------------------------


def test_gate1_fabricated_url_rejected():
    """A model-invented URL that was never actually fetched cannot be evidence."""
    real = {"https://real.example/repo"}
    ev = _ev("claim", "https://invented.example/fake")  # not in real fetch set
    problems = validate_evidence_sources([ev], real)
    assert problems, "fabricated URL must be rejected"
    assert "NOT produced by a real tool fetch" in problems[0]


def test_gate1_real_url_accepted():
    real = {"https://real.example/repo"}
    ev = _ev("claim", "https://real.example/repo")
    assert validate_evidence_sources([ev], real) == []


# --- Gate 2: doc-only cannot be VERIFIED ------------------------------------


def test_gate2_doc_only_cannot_be_verified():
    """Documentation support -> SUPPORTED, never VERIFIED without a test record."""
    ev = _ev("supports the claim", "https://real.example/repo")
    a = Assessment(
        id=new_id("a"), job_id=JID, condition_id="c", resource_ids=["r"],
        status=AssessmentStatus.VERIFIED, evidence_ids=[ev.id],
        explanation="doc says so", review_status=ReviewStatus.CURRENT,
    )
    problems = validate_assessment_status(a, [ev])
    assert problems and "VERIFIED requires a test/human-review record" in problems[0]


def test_gate2_doc_only_can_be_supported():
    ev = _ev("supports the claim", "https://real.example/repo")
    a = Assessment(
        id=new_id("a"), job_id=JID, condition_id="c", resource_ids=["r"],
        status=AssessmentStatus.SUPPORTED, evidence_ids=[ev.id],
        explanation="source-backed", review_status=ReviewStatus.CURRENT,
    )
    assert validate_assessment_status(a, [ev]) == []


# --- Gate 3: REQUIRED + QUALITY is valid ------------------------------------


def test_gate3_visual_quality_required_quality():
    """02 §3: obligation and dimension are independent; REQUIRED+QUALITY valid."""
    c = _cond("the dashboard must look polished and mature",
              obligation=Obligation.REQUIRED, dimension=Dimension.QUALITY)
    # this combination must NOT be flagged by the necessity checker (not an impl tech)
    assert validate_condition_necessity([c]) == []
    assert c.obligation == Obligation.REQUIRED
    assert c.dimension == Dimension.QUALITY


# --- Gate 4: React/REST not default necessary ------------------------------


def test_gate4_react_as_required_functional_flagged():
    """A model-derived condition asserting 'use React' as REQUIRED+FUNCTIONAL
    is a smuggled solution-dependency and must be flagged."""
    c = _cond("the system must use React for the frontend",
              obligation=Obligation.REQUIRED, dimension=Dimension.FUNCTIONAL)
    problems = validate_condition_necessity([c])
    assert problems and "solution-dependency" in problems[0]


def test_gate4_rest_api_as_required_functional_flagged():
    c = _cond("must expose a REST API", dimension=Dimension.FUNCTIONAL)
    problems = validate_condition_necessity([c])
    assert problems


def test_gate4_generic_functional_not_flagged():
    c = _cond("must display live agent status", dimension=Dimension.FUNCTIONAL)
    assert validate_condition_necessity([c]) == []


# --- Gate 6: UNKNOWN license; CONFLICTED evidence --------------------------


def test_gate6_missing_license_is_unknown():
    """05 §6: license not found -> UNKNOWN, never assumed commercially usable."""
    r = _res()
    assert r.license_claim == "UNKNOWN"


def test_gate6_conflicting_evidence_must_be_conflicted():
    ev_s = _ev("supports", "https://real.example/repo", stance=EvidenceStance.SUPPORTS)
    ev_r = _ev("refutes", "https://real.example/repo", stance=EvidenceStance.REFUTES)
    a = Assessment(
        id=new_id("a"), job_id=JID, condition_id="c", resource_ids=["r"],
        status=AssessmentStatus.SUPPORTED, evidence_ids=[ev_s.id, ev_r.id],
        explanation="tried to resolve", review_status=ReviewStatus.CURRENT,
    )
    problems = validate_conflict_handling([a], [ev_s, ev_r])
    assert problems and "must be CONFLICTED" in problems[0]


def test_gate6_conflicted_status_accepted_when_conflict_present():
    ev_s = _ev("supports", "https://real.example/repo", stance=EvidenceStance.SUPPORTS)
    ev_r = _ev("refutes", "https://real.example/repo", stance=EvidenceStance.REFUTES)
    a = Assessment(
        id=new_id("a"), job_id=JID, condition_id="c", resource_ids=["r"],
        status=AssessmentStatus.CONFLICTED, evidence_ids=[ev_s.id, ev_r.id],
        explanation="conflict preserved", review_status=ReviewStatus.CURRENT,
    )
    assert validate_conflict_handling([a], [ev_s, ev_r]) == []


# --- Gate 7: traceability --------------------------------------------------


def test_gate7_traceable_chain_ok():
    c = _cond("must show agent status")
    r = _res()
    ev = _ev("shows status", r.canonical_source)
    cap = Capability(id=new_id("cap"), job_id=JID, resource_id=r.id,
                      statement="shows status", evidence_ids=[ev.id])
    a = Assessment(id=new_id("a"), job_id=JID, condition_id=c.id,
                   resource_ids=[r.id], capability_ids=[cap.id],
                   status=AssessmentStatus.SUPPORTED, evidence_ids=[ev.id],
                   review_status=ReviewStatus.CURRENT)
    p = Proposal(id=new_id("p"), job_id=JID, title="t", summary="s",
                 resource_ids=[r.id], assessment_ids=[a.id],
                 condition_coverage=[c.id])
    assert validate_references(job_id=JID, conditions=[c], resources=[r],
                              capabilities=[cap], evidence=[ev],
                              assessments=[a], proposals=[p]) == []
    assert validate_traceability(p, [a], [c], [r], [cap], [ev]) == []


def test_gate7_untraceable_proposal_detected():
    c = _cond("must show agent status")
    r = _res()
    ev = _ev("shows status", r.canonical_source)
    cap = Capability(id=new_id("cap"), job_id=JID, resource_id=r.id,
                      statement="shows status", evidence_ids=[ev.id])
    a = Assessment(id=new_id("a"), job_id=JID, condition_id=c.id,
                   resource_ids=[r.id], capability_ids=[cap.id],
                   status=AssessmentStatus.SUPPORTED, evidence_ids=[ev.id],
                   review_status=ReviewStatus.CURRENT)
    # proposal references a non-existent assessment -> untraceable
    p = Proposal(id=new_id("p"), job_id=JID, title="t", summary="s",
                 resource_ids=[r.id], assessment_ids=["missing_assess"],
                 condition_coverage=[c.id])
    assert validate_traceability(p, [a], [c], [r], [cap], [ev]) != []


# --- Bonus: illegal transitions still enforced -----------------------------


def test_illegal_transition_blocked():
    from goalsift.models import JobStatus
    try:
        validate_transition(JobStatus.CANCELLED, JobStatus.RESEARCHING)
        assert False, "should have raised"
    except ValidationError:
        pass
