"""Exporter — Markdown + JSON from the current valid revision (05 §13).

Both views derive from the same validated data; the LLM may polish wording in
the report but never introduces new uninvestigated resource facts.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from .repository import Repository


def to_json(repo: Repository, job_id: str) -> dict:
    job = repo.get_job(job_id)
    goal = repo.get_goal(job_id)
    conditions = repo.list_conditions(job_id)
    resources = repo.list_resources(job_id)
    capabilities = repo.list_capabilities(job_id)
    evidence = repo.list_evidence(job_id)
    assessments = repo.list_assessments(job_id)
    proposal = repo.get_proposal(job_id)
    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "job": job.model_dump() if job else None,
        "goal": goal.model_dump() if goal else None,
        "conditions": [c.model_dump() for c in conditions],
        "resources": [r.model_dump() for r in resources],
        "capabilities": [c.model_dump() for c in capabilities],
        "evidence": [e.model_dump() for e in evidence],
        "assessments": [a.model_dump() for a in assessments],
        "proposal": proposal.model_dump() if proposal else None,
    }


def to_markdown(repo: Repository, job_id: str) -> str:
    job = repo.get_job(job_id)
    goal = repo.get_goal(job_id)
    conditions = repo.list_conditions(job_id)
    resources = repo.list_resources(job_id)
    evidence = repo.list_evidence(job_id)
    assessments = repo.list_assessments(job_id)
    proposal = repo.get_proposal(job_id)
    L: list[str] = []
    L.append(f"# GoalSift Research Report\n")
    L.append(f"- Job: `{job_id}`  \n- Status: {job.status.value if job else '?'}  \n- Exported: {datetime.now(timezone.utc).isoformat()}\n")
    L.append("\n## 1. Goal Brief\n")
    if goal:
        L.append(f"**Statement**: {goal.statement}\n")
        L.append(f"**Original user text** (preserved): {goal.original_user_text}\n")
    else:
        L.append("_No goal defined._\n")
    L.append("\n## 2. Condition Model\n")
    for c in conditions:
        L.append(f"- [{c.obligation.value}/{c.dimension.value}] {c.statement}")
    L.append("\n## 3. Resource Catalog\n")
    for r in resources:
        L.append(f"- **{r.name}** ({r.kind}) — license: `{r.license_claim or 'UNKNOWN'}`")
        L.append(f"  - source: {r.canonical_source}")
        L.append(f"  - {r.description[:160]}")
    L.append("\n## 4. Satisfaction Analysis\n")
    for a in assessments:
        L.append(f"- **{a.status.value}** — {a.explanation}")
        if a.gaps:
            L.append(f"  - gaps: {a.gaps}")
    L.append("\n## 5. Proposal Set\n")
    if proposal:
        L.append(f"### {proposal.title}\n")
        L.append(f"{proposal.summary}\n")
        L.append(f"- **Recommendation reason**: {proposal.recommendation_reason}")
        L.append(f"- **Risks**: {proposal.risks}")
        L.append(f"- **Costs**: {proposal.costs}")
        L.append(f"- _READY_FOR_REVIEW — not executed; user decision required._")
    else:
        L.append("_No proposal yet._")
    L.append("\n## 6. Open Questions\n")
    unknown = [a for a in assessments if a.status.value == "UNKNOWN"]
    if unknown:
        for a in unknown:
            L.append(f"- license/feasibility UNKNOWN: {a.explanation}")
    else:
        L.append("_None._")
    L.append(f"\n---\n_Evidence count: {len(evidence)}.  Export derived from current validated revision only._\n")
    return "\n".join(L)
