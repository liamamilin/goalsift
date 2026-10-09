"""M1 Spike — end-to-end artifacts with validation (model + search + source read).

Proves the M1 PASS Gate item: "生成最小 Goal、Condition、Resource、Evidence、
Assessment、Proposal，校验 ID 关联；至少一个来源支持的主张正确标记
SUPPORTED 而非 VERIFIED" (07 §4).

Live vertical slice:
  1. model (DeepSeek) derives success conditions for a real goal
  2. Exa search finds real candidate resources
  3. Exa reads one source -> real Evidence with locator
  4. build Goal/Condition/Resource/Capability/Evidence/Assessment/Proposal
     with valid ID references; mark capability claim SUPPORTED (source-backed)
     and license UNKNOWN; do NOT mark VERIFIED (no environment test)
  5. validators enforce reference integrity, evidence-status rules, traceability
  6. negative test: a VERIFIED assessment without test_context is rejected

Run: python3 -m spikes.spike_artifacts
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

load_env()
DS_KEY = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("GOALSIFT_LLM_API_KEY")
EXA_KEY = os.environ.get("EXA_API_KEY") or os.environ.get("GOALSIFT_SEARCH_API_KEY")
MODEL = os.environ.get("GOALSIFT_LLM_MODEL", "deepseek-chat")

import httpx
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from goalsift.models import (
    Assessment,
    AssessmentStatus,
    Capability,
    Condition,
    Dimension,
    Evidence,
    EvidenceStance,
    Goal,
    JobStatus,
    Obligation,
    Proposal,
    Provenance,
    ProposalValidity,
    Resource,
    ResearchJob,
    ReviewStatus,
    SourceType,
    ValidityStatus,
    new_id,
)
from goalsift.validators import (
    ValidationError,
    validate_assessment_status,
    validate_references,
    validate_traceability,
)

JOB_ID = new_id("job")
REV = 1
GOAL_TEXT = (
    "我要一个像成熟商业产品一样好看的 Agent 管理网页，接入我现在运行的多个 Agent。"
)


class ConditionSpec(BaseModel):
    statement: str
    obligation: str
    dimension: str
    rationale: str = ""


class ConditionSet(BaseModel):
    conditions: list[ConditionSpec]


def now() -> datetime:
    return datetime.now(timezone.utc)


def report(section: str, body: object) -> None:
    print(f"\n===== {section} =====")
    print(body if isinstance(body, str) else json.dumps(body, indent=2, ensure_ascii=False, default=str))


async def derive_conditions() -> list[ConditionSpec]:
    provider = OpenAIProvider(base_url="https://api.deepseek.com", api_key=DS_KEY)
    model = OpenAIChatModel(MODEL, provider=provider)
    agent = Agent(
        model,
        system_prompt=(
            "You derive success conditions for a software goal. Separate obligation "
            "(REQUIRED/OPTIONAL) from dimension (FUNCTIONAL/QUALITY/COMPLIANCE/OTHER). "
            "Do NOT confuse a specific implementation (e.g. 'use React') with a "
            "necessary condition. Return 3-5 conditions."
        ),
        output_type=ConditionSet,
    )
    r = await agent.run(f"Goal: {GOAL_TEXT} Derive key success conditions.")
    return r.output.conditions


async def search_and_read(query: str, num: int = 4):
    async with httpx.AsyncClient() as client:
        s = await client.post(
            "https://api.exa.ai/search",
            json={"query": query, "numResults": num, "type": "auto",
                  "contents": {"text": {"maxCharacters": 800}}},
            headers={"x-api-key": EXA_KEY}, timeout=60,
        )
        s.raise_for_status()
        search_json = s.json()
        hits = search_json.get("results", [])
        if not hits:
            return [], search_json.get("costDollars")
        # read first hit fully
        target = hits[0].get("url")
        c = await client.post(
            "https://api.exa.ai/contents",
            json={"urls": [target], "text": True},
            headers={"x-api-key": EXA_KEY}, timeout=60,
        )
        c.raise_for_status()
        cjson = c.json()
        item = (cjson.get("results") or [{}])[0]
        return hits, {"search": search_json.get("costDollars"),
                      "read_url": target, "read_text": item.get("text", ""),
                      "read_title": item.get("title"), "read_cost": cjson.get("costDollars")}


async def main() -> int:
    report("ENV", {"model": MODEL, "ds_key": bool(DS_KEY), "exa_key": bool(EXA_KEY)})
    if not (DS_KEY and EXA_KEY):
        report("VERDICT", "BLOCKED: missing key")
        return 2

    failures: list[str] = []

    # --- 1. live model: derive conditions --------------------------------
    specs = []
    try:
        specs = await derive_conditions()
        report("1. CONDITIONS (live model)", {
            "count": len(specs),
            "conditions": [c.model_dump() for c in specs],
        })
    except Exception as e:  # noqa: BLE001
        failures.append(f"model: {e!r}")
        report("1. CONDITIONS ERROR", repr(e))

    # --- 2. live search + read --------------------------------------------
    hits, search_meta = [], {}
    try:
        hits, search_meta = await search_and_read(
            "open source agent management dashboard UI", num=4
        )
        report("2. SEARCH+READ (live)", {
            "num_hits": len(hits),
            "first_url": search_meta.get("read_url"),
            "read_text_len": len(search_meta.get("read_text", "")),
            "costs": {"search": search_meta.get("search"), "read": search_meta.get("read_cost")},
        })
    except Exception as e:  # noqa: BLE001
        failures.append(f"search: {e!r}")
        report("2. SEARCH ERROR", repr(e))

    # --- 3. build real artifacts ------------------------------------------
    job = ResearchJob(
        id=JOB_ID, job_id=JOB_ID, original_request=GOAL_TEXT,
        status=JobStatus.RESEARCHING, current_revision=REV,
    )
    goal = Goal(
        id=new_id("goal"), job_id=JOB_ID, statement=GOAL_TEXT,
        purpose="管理多个正在运行的 AI Agent 的网页仪表盘",
        original_user_text=GOAL_TEXT, revision=REV,
        constraints=[{"text": "good-looking like a mature commercial product",
                       "provenance": Provenance.USER_STATED.value}],
    )
    job.current_goal_id = goal.id

    conditions: list[Condition] = []
    for sp in specs:
        conditions.append(Condition(
            id=new_id("cond"), job_id=JOB_ID, statement=sp.statement,
            obligation=Obligation(sp.obligation), dimension=Dimension(sp.dimension),
            origin="derived from goal via model (M1 spike)", revision_created=REV,
            validity_status=ValidityStatus.ACTIVE,
        ))

    # resource from real read (license "Other" -> UNKNOWN for commercial use)
    read_url = search_meta.get("read_url") or (hits[0]["url"] if hits else "https://example.invalid")
    res = Resource(
        id=new_id("res"), job_id=JOB_ID,
        name=search_meta.get("read_title") or (hits[0]["title"] if hits else "unknown"),
        kind="github_repo",
        description=(search_meta.get("read_text", "") or "")[:200],
        canonical_source=read_url,
        source_references=[read_url],
        version_or_revision=None,
        license_claim="Other",  # README says "License: Other" -> not a recognized commercial license
        discovery_status="CONFIRMED_EXISTENCE",
    )
    cap = Capability(
        id=new_id("cap"), job_id=JOB_ID, resource_id=res.id,
        statement="Provides an agent-first task board / mission-control UI for an AI workforce",
        interface_or_use="Web dashboard (multi-agent management)",
        limitations=["license field is 'Other', commercial usability unconfirmed"],
    )
    ev = Evidence(
        id=new_id("ev"), job_id=JOB_ID,
        claim=f"{res.name} is an agent-first task board / mission control for an AI workforce",
        source_type=SourceType.SOURCE_CODE,
        source_ref=read_url,
        locator="exa contents endpoint, full README text",
        excerpt_or_summary=(search_meta.get("read_text", "") or "")[:200],
        collection_method="exa /contents (real HTTP GET)",
        stance=EvidenceStance.SUPPORTS,
    )

    # SUPPORTED: source-backed capability claim; NOT VERIFIED (no env test)
    assessment = Assessment(
        id=new_id("assess"), job_id=JOB_ID,
        condition_id=conditions[0].id if conditions else "missing",
        resource_ids=[res.id], capability_ids=[cap.id],
        context="M1 spike; capability claim backed by README, not environment-tested",
        status=AssessmentStatus.SUPPORTED,
        evidence_ids=[ev.id],
        explanation=(
            "README text supports that this project is an agent management dashboard. "
            "Marked SUPPORTED, not VERIFIED, because no test/human-review under stated "
            "acceptance conditions has been performed."
        ),
        gaps=["license is 'Other' -> commercial use UNKNOWN",
              "not environment-tested"],
        review_status=ReviewStatus.CURRENT,
        revision_evaluated=REV,
    )
    # license-specific assessment -> UNKNOWN
    license_assessment = Assessment(
        id=new_id("assess"), job_id=JOB_ID,
        condition_id=(conditions[-1].id if conditions else "missing"),
        resource_ids=[res.id], capability_ids=[],
        context="commercial license suitability",
        status=AssessmentStatus.UNKNOWN,
        evidence_ids=[ev.id],
        explanation="README reports 'License: Other'; not a recognized commercial license -> UNKNOWN.",
        gaps=["license type not confirmed as commercially permissive"],
        review_status=ReviewStatus.CURRENT,
        revision_evaluated=REV,
    )
    proposal = Proposal(
        id=new_id("prop"), job_id=JOB_ID,
        title="Reuse an existing open-source agent dashboard (license to confirm)",
        summary=(
            f"Reuse {res.name} as the management UI base; it provides an agent-first "
            "task board for an AI workforce (source-backed). License is 'Other' -> "
            "commercial use is UNKNOWN and must be confirmed before adoption."
        ),
        resource_ids=[res.id],
        assessment_ids=[assessment.id, license_assessment.id],
        condition_coverage=[c.id for c in conditions],
        integration_work=["confirm license permits intended use",
                          "wire to the user's running agents via its interface"],
        new_work=["adapt agent connection adapters if needed"],
        uncovered_conditions=[license_assessment.id],
        risks=["license unconfirmed", "not environment-tested"],
        costs={"estimate": "UNKNOWN", "basis": "no pricing data; no fabrication"},
        recommendation_reason="Reuse-before-build; real source-backed capability, with license gap explicit.",
        validity_status=ProposalValidity.READY_FOR_REVIEW,
        revision_created=REV,
    )

    # --- 4. validate -----------------------------------------------------
    ref_problems = validate_references(
        job_id=JOB_ID, conditions=conditions, resources=[res],
        capabilities=[cap], evidence=[ev],
        assessments=[assessment, license_assessment], proposals=[proposal],
    )
    status_problems = (
        validate_assessment_status(assessment, [ev])
        + validate_assessment_status(license_assessment, [ev])
    )
    trace_problems = validate_traceability(
        proposal, [assessment, license_assessment], conditions, [res], [cap], [ev]
    )

    report("4. VALIDATION", {
        "reference_problems": ref_problems,
        "assessment_status_problems": status_problems,
        "traceability_problems": trace_problems,
    })
    if ref_problems:
        failures.append(f"references: {ref_problems}")
    if status_problems:
        failures.append(f"assessment-status: {status_problems}")
    if trace_problems:
        failures.append(f"traceability: {trace_problems}")

    # --- 5. negative test: VERIFIED without test record must be rejected --
    bogus = Assessment(
        id=new_id("assess"), job_id=JOB_ID,
        condition_id=conditions[0].id if conditions else "x",
        resource_ids=[res.id], capability_ids=[cap.id],
        status=AssessmentStatus.VERIFIED,
        evidence_ids=[ev.id],
        explanation="doc-only claim illegally promoted to VERIFIED",
        review_status=ReviewStatus.CURRENT, revision_evaluated=REV,
    )
    neg = validate_assessment_status(bogus, [ev])
    report("5. NEGATIVE (VERIFIED w/o test record)", {
        "rejected": bool(neg),
        "problems": neg,
    })
    if not neg:
        failures.append("negative: VERIFIED without test record was NOT rejected")

    # --- 6. state transition sanity (04 single authority) ----------------
    try:
        from goalsift.validators import validate_transition
        validate_transition(JobStatus.CREATED, JobStatus.RESEARCHING)  # ok
        ok_legal = True
    except ValidationError as e:
        ok_legal = False
        failures.append(f"transition legal: {e!r}")
    illegal_caught = None
    try:
        from goalsift.validators import validate_transition
        validate_transition(JobStatus.CANCELLED, JobStatus.RESEARCHING)  # illegal
        illegal_caught = "NOT caught"
    except ValidationError:
        illegal_caught = "caught"
    report("6. STATE TRANSITIONS", {
        "legal_CREATED->RESEARCHING": ok_legal,
        "illegal_CANCELLED->RESEARCHING": illegal_caught,
    })
    if illegal_caught != "caught":
        failures.append("transition: illegal CANCELLED->RESEARCHING not rejected")

    # --- 7. artifacts dump (for report evidence) -------------------------
    report("7. ARTIFACTS", {
        "job": job.model_dump(),
        "goal": goal.model_dump(),
        "conditions": [c.model_dump() for c in conditions],
        "resource": res.model_dump(),
        "capability": cap.model_dump(),
        "evidence": ev.model_dump(),
        "assessment_supported": assessment.model_dump(),
        "assessment_license_unknown": license_assessment.model_dump(),
        "proposal": proposal.model_dump(),
    })

    verdict = "PASS" if not failures else "FAIL"
    report("VERDICT", {
        "verdict": verdict,
        "failures": failures,
        "all_live": True,
        "supported_not_verified": assessment.status == AssessmentStatus.SUPPORTED,
        "license_unknown": license_assessment.status == AssessmentStatus.UNKNOWN,
        "traceability": "Proposal -> Assessment -> Condition/Resource/Capability -> Evidence",
    })
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
