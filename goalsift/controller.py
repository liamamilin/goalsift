"""Research Controller — simplified fixed-order pipeline (M2).

07 §5 allows a temporary fixed action order: Define → Derive → Discover →
Match → Propose. M3 replaces this with the full six-operation loop.

The Controller is the single trusted write entrypoint (04 §2). Model output is
untrusted; everything passes through validators before the repository commits.
One active run per job is enforced by `active_run_id` (04 §3.2).
"""

from __future__ import annotations

import asyncio
import traceback
from datetime import datetime, timezone
from typing import Any

from .llm_adapter import LLMAdapter, ResourceMatch
from .models import (
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
    ProposalValidity,
    Provenance,
    Resource,
    ResearchEvent,
    ReviewStatus,
    SourceType,
    ValidityStatus,
    new_id,
)
from .repository import Repository
from .search_adapter import SearchAdapter
from .validators import validate_references, validate_assessment_status

ACTION = {
    "define": "REASON", "derive": "REASON", "discover": "SEARCH",
    "inspect": "INSPECT", "match": "REASON", "propose": "PROPOSE",
}


class Controller:
    def __init__(self, repo: Repository, llm: LLMAdapter, search: SearchAdapter) -> None:
        self.repo = repo
        self.llm = llm
        self.search = search
        self._runs: dict[str, asyncio.Task] = {}

    def _ev(self, job_id: str, revision: int, action: str, status: str,
            **extra: Any) -> ResearchEvent:
        return ResearchEvent(
            id=new_id("ev"), event_id=new_id("ev"), job_id=job_id, revision=revision,
            action_type=action, status=status, related_object_ids=extra.get("refs", []),
            tool_result_ref=extra.get("tool_ref"), usage=extra.get("usage", {}),
            error=extra.get("error"),
        )

    async def start(self, job_id: str) -> bool:
        """Begin research in the background. Returns False if already running."""
        job = self.repo.get_job(job_id)
        if not job:
            return False
        if job.active_run_id:
            return False  # single executor (04 §3.2)
        if job.status == JobStatus.COMPLETED:
            return False  # COMPLETED needs Refine (M4); not start
        # legal transition check
        from .validators import validate_transition, ValidationError
        try:
            validate_transition(JobStatus(job.status), JobStatus.RESEARCHING)
        except ValidationError:
            return False
        run_id = new_id("run")
        self.repo.set_job_status(job_id, JobStatus.RESEARCHING.value, active_run_id=run_id)
        self.repo.append_event(self._ev(job_id, job.current_revision, "REASON", "RESEARCHING", refs=[run_id]))
        task = asyncio.create_task(self._run(job_id, run_id, job.current_revision))
        self._runs[job_id] = task
        return True  # noqa: B019

    async def _run(self, job_id: str, run_id: str, revision: int) -> None:
        try:
            job = self.repo.get_job(job_id)
            assert job is not None
            goal_text = job.original_request

            # --- Define ---
            goal = Goal(
                id=new_id("goal"), job_id=job_id, statement=goal_text,
                purpose=None, original_user_text=goal_text, revision=revision,
                constraints=[{"text": goal_text, "provenance": Provenance.USER_STATED.value}],
            )
            self.repo.save_goal(goal)
            self.repo.set_job_status(job_id, JobStatus.RESEARCHING.value, current_goal_id=goal.id)
            self.repo.append_event(self._ev(job_id, revision, "REASON", "DEFINED", refs=[goal.id]))

            # --- Derive ---
            specs = await self.llm.derive_conditions(goal_text)
            conditions: list[Condition] = []
            for sp in specs:
                c = Condition(
                    id=new_id("cond"), job_id=job_id, statement=sp.statement,
                    obligation=Obligation(sp.obligation), dimension=Dimension(sp.dimension),
                    origin="model-derived (M2)", revision_created=revision,
                    validity_status=ValidityStatus.ACTIVE,
                )
                self.repo.save_condition(c)
                conditions.append(c)
            self.repo.append_event(self._ev(
                job_id, revision, "REASON", "DERIVED",
                refs=[c.id for c in conditions], usage={"conditions": len(conditions)},
            ))

            # --- Discover ---
            results, meta = await self.search.search(goal_text, num=4)
            resources: list[Resource] = []
            for sr in results:
                res = Resource(
                    id=new_id("res"), job_id=job_id, name=sr.title or sr.url,
                    kind="web_resource", description=sr.text[:300],
                    canonical_source=sr.url, source_references=[sr.url],
                    license_claim="UNKNOWN",  # not confirmed; per 05 §6
                    discovery_status="CONFIRMED_EXISTENCE",
                )
                self.repo.save_resource(res)
                resources.append(res)
            self.repo.append_event(self._ev(
                job_id, revision, "SEARCH", "DISCOVERED",
                refs=[r.id for r in resources], usage=meta, tool_ref="exa/search",
            ))

            # --- Inspect: read top source fully -> Evidence ---
            evidence_list: list[Evidence] = []
            capabilities: list[Capability] = []
            if results:
                top = results[0]
                try:
                    sr, read_meta = await self.search.read_source(top.url)
                    ev = Evidence(
                        id=new_id("ev"), job_id=job_id,
                        claim=f"{top.title} is described in its source as an agent management dashboard",
                        source_type=SourceType.THIRD_PARTY,
                        source_ref=top.url,
                        locator="exa /contents full text",
                        excerpt_or_summary=sr.text[:400],
                        collection_method="exa /contents",
                        stance=EvidenceStance.SUPPORTS,
                    )
                    self.repo.save_evidence(ev)
                    evidence_list.append(ev)
                    cap = Capability(
                        id=new_id("cap"), job_id=job_id, resource_id=resources[0].id,
                        statement="Provides an agent management dashboard UI",
                        interface_or_use="web",
                        limitations=["license UNKNOWN", "not environment-tested"],
                        evidence_ids=[ev.id],
                    )
                    self.repo.save_capability(cap)
                    capabilities.append(cap)
                    self.repo.append_event(self._ev(
                        job_id, revision, "INSPECT", "READ_SOURCE",
                        refs=[ev.id, cap.id], usage=read_meta, tool_ref="exa/contents",
                    ))
                except Exception as e:  # noqa: BLE001
                    self.repo.append_event(self._ev(
                        job_id, revision, "INSPECT", "ERROR", error=repr(e),
                    ))

            # --- Match ---
            res_dicts = [{"name": r.name, "url": r.canonical_source,
                          "license": r.license_claim or "UNKNOWN",
                          "text": r.description} for r in resources]
            cond_stmts = [c.statement for c in conditions]
            matches: list[ResourceMatch] = []
            try:
                matches = await self.llm.assess_resources(goal_text, cond_stmts, res_dicts)
            except Exception as e:  # noqa: BLE001
                self.repo.append_event(self._ev(
                    job_id, revision, "REASON", "MATCH_ERROR", error=repr(e),
                ))

            assessments: list[Assessment] = []
            cond_by_stmt = {c.statement: c for c in conditions}
            res_by_name = {r.name: r for r in resources}
            for m in matches:
                cond = cond_by_stmt.get(m.condition_statement) or (conditions[0] if conditions else None)
                res = res_by_name.get(m.resource_name) or (resources[0] if resources else None)
                if not cond or not res:
                    continue
                try:
                    status = AssessmentStatus(m.status)
                except ValueError:
                    status = AssessmentStatus.UNKNOWN
                a = Assessment(
                    id=new_id("assess"), job_id=job_id, condition_id=cond.id,
                    resource_ids=[res.id], capability_ids=[cap.id for cap in capabilities if cap.resource_id == res.id],
                    context="M2 model assessment from source text",
                    status=status,
                    evidence_ids=[e.id for e in evidence_list if e.id in (cap.evidence_ids for cap in capabilities)],
                    explanation=m.explanation, gaps=m.gaps,
                    review_status=ReviewStatus.CURRENT, revision_evaluated=revision,
                )
                # enforce: never let model claim VERIFIED (05 §9)
                if a.status == AssessmentStatus.VERIFIED:
                    a.status = AssessmentStatus.SUPPORTED
                    a.explanation += " [downgraded VERIFIED->SUPPORTED: no environment test]"
                problems = validate_assessment_status(a, evidence_list)
                if problems:
                    a.gaps.append(problems[0])
                self.repo.save_assessment(a)
                assessments.append(a)
            # explicit license assessment: UNKNOWN (05 §6)
            if resources and evidence_list:
                lic_cond = conditions[-1] if conditions else None
                if lic_cond:
                    la = Assessment(
                        id=new_id("assess"), job_id=job_id, condition_id=lic_cond.id,
                        resource_ids=[resources[0].id], context="commercial license suitability",
                        status=AssessmentStatus.UNKNOWN,
                        evidence_ids=[e.id for e in evidence_list],
                        explanation="license field not a recognized commercial license -> UNKNOWN",
                        gaps=["license type unconfirmed"],
                        review_status=ReviewStatus.CURRENT, revision_evaluated=revision,
                    )
                    self.repo.save_assessment(la)
                    assessments.append(la)
            self.repo.append_event(self._ev(
                job_id, revision, "REASON", "MATCHED",
                refs=[a.id for a in assessments], usage={"assessments": len(assessments)},
            ))

            # --- Propose ---
            draft = await self.llm.draft_proposal(
                goal_text,
                [{"name": r.name, "url": r.canonical_source,
                  "license": r.license_claim or "UNKNOWN"} for r in resources],
                matches,
            )
            proposal = Proposal(
                id=new_id("prop"), job_id=job_id, title=draft.title, summary=draft.summary,
                resource_ids=[r.id for r in resources],
                assessment_ids=[a.id for a in assessments],
                condition_coverage=[c.id for c in conditions],
                integration_work=draft.integration_work, new_work=draft.new_work,
                uncovered_conditions=[a.id for a in assessments if a.status in
                                      (AssessmentStatus.UNKNOWN, AssessmentStatus.NOT_SATISFIED)],
                risks=draft.risks,
                costs={"estimate": "UNKNOWN", "basis": "no pricing data; not fabricated"},
                recommendation_reason=draft.recommendation_reason,
                validity_status=ProposalValidity.READY_FOR_REVIEW, revision_created=revision,
            )
            # validate references before commit
            ref_problems = validate_references(
                job_id=job_id, conditions=conditions, resources=resources,
                capabilities=capabilities, evidence=evidence_list,
                assessments=assessments, proposals=[proposal],
            )
            if ref_problems:
                raise RuntimeError(f"reference validation failed: {ref_problems}")
            self.repo.save_proposal(proposal)
            self.repo.append_event(self._ev(
                job_id, revision, "PROPOSE", "PROPOSED",
                refs=[proposal.id], usage={"proposal": 1},
            ))

            # --- Finish ---
            self.repo.set_job_status(job_id, JobStatus.COMPLETED.value, active_run_id=None)
            self.repo.append_event(self._ev(job_id, revision, "FINISH", "COMPLETED",
                                            refs=[proposal.id]))

        except Exception as e:  # noqa: BLE001
            self.repo.set_job_status(job_id, JobStatus.FAILED.value, active_run_id=None)
            self.repo.append_event(self._ev(
                job_id, revision, "FINISH", "FAILED",
                error=f"{e!r}\n{traceback.format_exc()[-800:]}",
            ))
        finally:
            self._runs.pop(job_id, None)

    # --- lifecycle commands (04 §3) ---
    def pause(self, job_id: str) -> bool:
        job = self.repo.get_job(job_id)
        if not job or job.status != JobStatus.RESEARCHING:
            return False
        self.repo.set_job_status(job_id, JobStatus.PAUSED.value, active_run_id=None)
        return True

    def cancel(self, job_id: str) -> bool:
        job = self.repo.get_job(job_id)
        if not job or job.status == JobStatus.CANCELLED:
            return False
        task = self._runs.get(job_id)
        if task and not task.done():
            task.cancel()
        self.repo.set_job_status(job_id, JobStatus.CANCELLED.value, active_run_id=None)
        return True
