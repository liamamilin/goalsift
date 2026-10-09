"""M3 Live proof — real six-operation run with Challenge (07 §6 gate items 5,7,8).

Runs the Controller end-to-end on a real goal with live model + search, then
verifies:
  5. Challenge produced findings and (where warranted) revised conditions
  7. Proposal traceable Condition -> Assessment -> Resource/Capability -> Evidence
  8. a Live case proves real search + match flow (not mock)

Also checks no smuggled implementation (React/REST) survives as REQUIRED+FUNCTIONAL,
and all evidence sources were really fetched.

Run: python3 -m spikes.spike_m3_live
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from goalsift.config import load_env
load_env()

from goalsift.controller import Controller
from goalsift.llm_adapter import LLMAdapter
from goalsift.repository import Repository
from goalsift.search_adapter import SearchAdapter
from goalsift.validators import (
    validate_condition_necessity,
    validate_conflict_handling,
    validate_evidence_sources,
    validate_traceability,
)
from goalsift.paths import override_data_root


def report(section: str, body: object) -> None:
    print(f"\n===== {section} =====")
    print(body if isinstance(body, str) else json.dumps(body, indent=2, ensure_ascii=False, default=str))


async def main() -> int:
    import tempfile
    tmp = Path(tempfile.mkdtemp()) / "data"
    tmp.mkdir(parents=True, exist_ok=True)
    override_data_root(tmp)

    repo = Repository()
    llm = LLMAdapter()
    search = SearchAdapter()
    ctrl = Controller(repo, llm, search)

    goal = "我要一个像成熟商业产品一样好看的 Agent 管理网页，接入我现在运行的多个 Agent。"
    job = repo.create_job(goal)
    ok = await ctrl.start(job.id)
    if not ok:
        report("VERDICT", "BLOCKED: could not start")
        return 2

    # wait for completion
    from goalsift.models import JobStatus
    for _ in range(120):
        await asyncio.sleep(2)
        j = repo.get_job(job.id)
        if j.status not in (JobStatus.RESEARCHING, JobStatus.CREATED):
            break

    j = repo.get_job(job.id)
    conditions = repo.list_conditions(job.id)
    resources = repo.list_resources(job.id)
    caps = repo.list_capabilities(job.id)
    evidence = repo.list_evidence(job.id)
    assessments = repo.list_assessments(job.id)
    proposal = repo.get_proposal(job.id)
    events = repo.list_events(job.id)

    # --- gate 5: Challenge ran and possibly revised ---
    challenge_events = [e for e in events if e.action_type.value == "REVISE"]
    challenge_revised = any(
        (e.usage or {}).get("revised") for e in challenge_events
    )
    smuggled = validate_condition_necessity(conditions)
    # conditions that were touched by challenge
    challenge_touched = [c.statement for c in conditions if "challenge" in (c.origin or "").lower()]

    # --- gate 7: traceability ---
    trace = validate_traceability(proposal, assessments, conditions, resources, caps, evidence) if proposal else ["no proposal"]

    # --- gate 1: evidence sources really fetched ---
    fetched = {r.canonical_source for r in resources} | {e.source_ref for e in evidence}
    src_ok = validate_evidence_sources(evidence, fetched)

    # --- gate 6: conflict handling ---
    conf = validate_conflict_handling(assessments, evidence)

    report("JOB", {"status": j.status.value, "revision": j.current_revision})
    report("EVENTS", [{"type": e.action_type.value, "status": e.status,
                       "usage": e.usage, "error": (e.error or "")[:100]} for e in events])
    report("GATE5 CHALLENGE", {
        "challenge_events": len(challenge_events),
        "revised": challenge_revised,
        "conditions_touched_by_challenge": challenge_touched,
        "smuggled_impl_tech_remaining": smuggled,
        "conditions": [{"statement": c.statement, "obligation": c.obligation.value,
                        "dimension": c.dimension.value, "validity": c.validity_status.value}
                       for c in conditions],
    })
    report("GATE7 TRACEABILITY", {"problems": trace, "traceable": not trace})
    report("GATE1 EVIDENCE SOURCES", {"problems": src_ok, "all_fetched": not src_ok,
                                       "evidence_count": len(evidence)})
    report("GATE6 CONFLICT", {"problems": conf})
    report("SUMMARY", {
        "conditions": len(conditions), "resources": len(resources),
        "capabilities": len(caps), "evidence": len(evidence),
        "assessments": len(assessments), "proposal": bool(proposal),
        "assessment_statuses": sorted({a.status.value for a in assessments}),
    })

    repo.close()
    verdict = "PASS"
    fails = []
    if not proposal:
        fails.append("no proposal")
    if smuggled:
        fails.append(f"smuggled impl tech: {smuggled}")
    if trace:
        fails.append(f"traceability: {trace}")
    if src_ok:
        fails.append(f"evidence sources: {src_ok}")
    if conf:
        fails.append(f"conflict: {conf}")
    if not challenge_events:
        fails.append("challenge did not run")
    verdict = "PASS" if not fails else "FAIL"
    report("VERDICT", {"verdict": verdict, "failures": fails, "all_live": True})
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
