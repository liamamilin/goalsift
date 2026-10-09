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

    def _stopped(self, job_id: str) -> bool:
        """True if the job has been paused/cancelled (no active run should proceed)."""
        job = self.repo.get_job(job_id)
        if not job:
            return True
        return job.status in (JobStatus.PAUSED, JobStatus.CANCELLED)

    async def refine(self, job_id: str, constraint: str) -> bool:
        """COMPLETED -> new revision with an added constraint (04 §3.1, 05 §12).
        Preserves prior revision; invalidates its dependent objects."""
        job = self.repo.get_job(job_id)
        if not job or job.status != JobStatus.COMPLETED:
            return False
        new_rev = self.repo.new_revision(job_id)          # COMPLETED->RESEARCHING + invalidates old
        self.repo.add_constraint(job_id, constraint)      # adds to goal
        self.repo.append_event(self._ev(
            job_id, new_rev, "ASK_USER", "REFINE_RECEIVED",
            refs=[], usage={"constraint": constraint},
        ))
        # begin the new revision's research (status already RESEARCHING)
        return await self._schedule_run(job_id, new_rev)

    async def answer_input(self, job_id: str, answer: str) -> bool:
        """NEEDS_INPUT -> record the user's clarifying answer and resume (04 §3)."""
        job = self.repo.get_job(job_id)
        if not job or job.status != JobStatus.NEEDS_INPUT:
            return False
        self.repo.add_constraint(job_id, f"[clarification] {answer}")
        self.repo.append_event(self._ev(
            job_id, job.current_revision, "ASK_USER", "INPUT_ANSWERED",
            usage={"answer": answer},
        ))
        return await self._schedule_run(job_id, job.current_revision)

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
        self.repo.set_job_status(job_id, JobStatus.RESEARCHING.value)
        return await self._schedule_run(job_id, job.current_revision)

    async def _schedule_run(self, job_id: str, revision: int) -> bool:
        """Create the background run (assumes status already RESEARCHING).
        Enforces single executor via active_run_id (04 §3.2)."""
        job = self.repo.get_job(job_id)
        if not job or job.active_run_id:
            return False
        run_id = new_id("run")
        self.repo.set_job_status(job_id, JobStatus.RESEARCHING.value, active_run_id=run_id)
        self.repo.append_event(self._ev(job_id, revision, "REASON", "RESEARCHING", refs=[run_id]))
        task = asyncio.create_task(self._run(job_id, run_id, revision))
        self._runs[job_id] = task
        return True

    async def _run(self, job_id: str, run_id: str, revision: int) -> None:
        from .budget import BudgetExhausted, BudgetGuard
        guard = BudgetGuard()
        try:
            job = self.repo.get_job(job_id)
            assert job is not None
            goal_text = job.original_request
            existing_goal = self.repo.get_goal(job_id)
            # enrich with any clarifying constraints collected via NEEDS_INPUT answers
            if existing_goal and existing_goal.constraints:
                clar = [
                    c["text"] for c in existing_goal.constraints
                    if isinstance(c, dict) and c.get("text")
                    and c["text"] != job.original_request
                ]
                if clar:
                    goal_text = job.original_request + " | Clarifications: " + "; ".join(clar)

            # --- Define ---
            if existing_goal:
                goal = existing_goal
                goal.statement = goal_text  # effective goal includes clarifications
                self.repo.save_goal(goal)
            else:
                goal = Goal(
                    id=new_id("goal"), job_id=job_id, statement=goal_text,
                    purpose=None, original_user_text=job.original_request, revision=revision,
                    constraints=[{"text": job.original_request, "provenance": Provenance.USER_STATED.value}],
                )
                self.repo.save_goal(goal)
                self.repo.set_job_status(job_id, JobStatus.RESEARCHING.value, current_goal_id=goal.id)
                self.repo.append_event(self._ev(job_id, revision, "REASON", "DEFINED", refs=[goal.id]))

            # --- Ambiguity gate (03 §5): decisive ambiguity -> NEEDS_INPUT ---
            # only when the goal has NOT been clarified yet
            clarified = bool(existing_goal and any(
                isinstance(c, dict) and c.get("text") != job.original_request
                for c in existing_goal.constraints
            ))
            if not clarified:
                try:
                    amb = await self.llm.check_ambiguity(goal_text)
                    if amb.is_decisively_ambiguous and amb.question:
                        goal.open_questions = [amb.question]
                        self.repo.save_goal(goal)
                        self.repo.set_job_status(job_id, JobStatus.NEEDS_INPUT.value, active_run_id=None)
                        self.repo.append_event(self._ev(
                            job_id, revision, "ASK_USER", "NEEDS_INPUT",
                            usage={"question": amb.question, "rationale": amb.rationale},
                        ))
                        return  # wait for user clarification; do not fabricate
                except Exception as e:  # noqa: BLE001
                    self.repo.append_event(self._ev(
                        job_id, revision, "REASON", "AMBIGUITY_CHECK_ERROR", error=repr(e),
                    ))

            # --- Derive ---
            guard.check()
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

            # --- Challenge (02 §4.3) — may modify conditions, not just comment ---
            try:
                report_obj = await self.llm.challenge_conditions(
                    goal_text,
                    [{"statement": c.statement, "obligation": c.obligation.value,
                      "dimension": c.dimension.value} for c in conditions],
                )
                cond_by_stmt = {c.statement: c for c in conditions}
                revised = False
                for f in report_obj.findings:
                    target = cond_by_stmt.get(f.target_condition)
                    if not target:
                        continue
                    rec = (f.recommendation or "").lower()
                    if "optional" in rec and target.obligation == Obligation.REQUIRED:
                        target.obligation = Obligation.OPTIONAL
                        target.origin += f"; challenge: {f.finding}"
                        target.validity_status = ValidityStatus.ACTIVE
                        self.repo.save_condition(target)
                        revised = True
                    elif "supersede" in rec:
                        target.validity_status = ValidityStatus.SUPERSEDED
                        target.origin += f"; challenge: {f.finding}"
                        self.repo.save_condition(target)
                        revised = True
                    elif "add" in rec:
                        nc = Condition(
                            id=new_id("cond"), job_id=job_id, statement=f.finding,
                            obligation=Obligation.REQUIRED, dimension=Dimension.FUNCTIONAL,
                            origin=f"challenge-added: {f.finding}", revision_created=revision,
                        )
                        self.repo.save_condition(nc)
                        conditions.append(nc)
                        revised = True
                    else:
                        target.origin += f"; challenge kept: {f.finding}"
                        self.repo.save_condition(target)
                # necessity validator: flag smuggled implementation conditions
                from .validators import validate_condition_necessity
                nec = validate_condition_necessity(conditions)
                for msg in nec:
                    self.repo.append_event(self._ev(
                        job_id, revision, "REVISE", "CHALLENGE_FLAG", error=msg,
                    ))
                    # downgrade flagged impl-tech conditions to OPTIONAL (02 §3)
                    cid = msg.split(" ")[1]
                    for c in conditions:
                        if c.id == cid and c.obligation == Obligation.REQUIRED:
                            c.obligation = Obligation.OPTIONAL
                            c.origin += "; downgraded: solution-dependency not goal necessity"
                            self.repo.save_condition(c)
                            revised = True
                conditions = [c for c in conditions if c.validity_status != ValidityStatus.SUPERSEDED]
                self.repo.append_event(self._ev(
                    job_id, revision, "REVISE", "CHALLENGED",
                    refs=[c.id for c in conditions],
                    usage={"findings": len(report_obj.findings), "revised": revised},
                ))
            except Exception as e:  # noqa: BLE001
                self.repo.append_event(self._ev(
                    job_id, revision, "REVISE", "CHALLENGE_ERROR", error=repr(e),
                ))

            # --- Discover ---
            if self._stopped(job_id):
                return
            guard.check(tool_call=True)
            results, meta = await self.search.search(goal_text, num=4)
            fetched_urls: set[str] = set()
            resources: list[Resource] = []
            for sr in results:
                fetched_urls.add(sr.url)
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

            # --- Inspect: source reading -> Evidence for EACH resource ---
            # The Exa search already returned source text per result; that is a real
            # read. We record an Evidence per resource so every assessment is traceable,
            # and additionally do a full read of the top source for deeper evidence.
            evidence_list: list[Evidence] = []
            capabilities: list[Capability] = []
            fetched_urls.update(sr.url for sr in results)
            for idx, sr in enumerate(results):
                res = resources[idx] if idx < len(resources) else None
                if not res:
                    continue
                # use search text as the source excerpt (real fetched content)
                text = sr.text or ""
                if not text:
                    # fallback: full read this source
                    try:
                        sr2, _ = await self.search.read_source(sr.url)
                        text = sr2.text
                        fetched_urls.add(sr.url)
                    except Exception:
                        text = ""
                ev = Evidence(
                    id=new_id("ev"), job_id=job_id,
                    claim=f"{res.name} is described in its source as relevant to the goal",
                    source_type=SourceType.THIRD_PARTY,
                    source_ref=sr.url,
                    locator="exa search content (text field)",
                    excerpt_or_summary=text[:400],
                    collection_method="exa /search contents.text",
                    stance=EvidenceStance.SUPPORTS,
                )
                self.repo.save_evidence(ev)
                evidence_list.append(ev)
                cap = Capability(
                    id=new_id("cap"), job_id=job_id, resource_id=res.id,
                    statement="Provides a resource relevant to the goal",
                    interface_or_use="web",
                    limitations=["license UNKNOWN", "not environment-tested"],
                    evidence_ids=[ev.id],
                )
                self.repo.save_capability(cap)
                capabilities.append(cap)
            # deeper full read of the top source (additional evidence, not the only one)
            if results:
                top = results[0]
                fetched_urls.add(top.url)
                try:
                    guard.check(tool_call=True)
                    sr_deep, read_meta = await self.search.read_source(top.url)
                    ev_deep = Evidence(
                        id=new_id("ev"), job_id=job_id,
                        claim=f"{top.title} full source content read",
                        source_type=SourceType.THIRD_PARTY,
                        source_ref=top.url,
                        locator="exa /contents full text",
                        excerpt_or_summary=sr_deep.text[:400],
                        collection_method="exa /contents",
                        stance=EvidenceStance.SUPPORTS,
                    )
                    self.repo.save_evidence(ev_deep)
                    evidence_list.append(ev_deep)
                    # attach to top resource's capability
                    if capabilities:
                        capabilities[0].evidence_ids.append(ev_deep.id)
                        self.repo.save_capability(capabilities[0])
                    self.repo.append_event(self._ev(
                        job_id, revision, "INSPECT", "READ_SOURCE_DEEP",
                        refs=[ev_deep.id], usage=read_meta, tool_ref="exa/contents",
                    ))
                except Exception as e:  # noqa: BLE001
                    self.repo.append_event(self._ev(
                        job_id, revision, "INSPECT", "ERROR", error=repr(e),
                    ))
            self.repo.append_event(self._ev(
                job_id, revision, "INSPECT", "READ_SOURCES",
                refs=[e.id for e in evidence_list], usage={"evidence": len(evidence_list)},
                tool_ref="exa/search+contents",
            ))

            # --- Match ---
            if self._stopped(job_id):
                return
            guard.check(tool_call=True)
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
                # evidence belonging to this resource's capabilities (proper link)
                res_ev_ids = {eid for cap in capabilities if cap.resource_id == res.id
                              for eid in cap.evidence_ids}
                a = Assessment(
                    id=new_id("assess"), job_id=job_id, condition_id=cond.id,
                    resource_ids=[res.id], capability_ids=[cap.id for cap in capabilities if cap.resource_id == res.id],
                    context="model assessment from source text",
                    status=status,
                    evidence_ids=[e.id for e in evidence_list if e.id in res_ev_ids],
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
            if self._stopped(job_id):
                return
            guard.check(tool_call=True)
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
            # validate references + M3 evidence integrity before commit
            from .validators import (
                validate_conflict_handling, validate_evidence_sources,
                validate_traceability,
            )
            ref_problems = validate_references(
                job_id=job_id, conditions=conditions, resources=resources,
                capabilities=capabilities, evidence=evidence_list,
                assessments=assessments, proposals=[proposal],
            )
            src_problems = validate_evidence_sources(evidence_list, fetched_urls)
            conf_problems = validate_conflict_handling(assessments, evidence_list)
            trace_problems = validate_traceability(
                proposal, assessments, conditions, resources, capabilities, evidence_list
            )
            all_problems = ref_problems + src_problems + conf_problems + trace_problems
            if all_problems:
                raise RuntimeError(f"validation failed: {all_problems}")
            self.repo.save_proposal(proposal)
            self.repo.append_event(self._ev(
                job_id, revision, "PROPOSE", "PROPOSED",
                refs=[proposal.id], usage={"proposal": 1},
            ))

            # --- Finish ---
            self.repo.set_job_status(job_id, JobStatus.COMPLETED.value, active_run_id=None)
            self.repo.append_event(self._ev(job_id, revision, "FINISH", "COMPLETED",
                                            refs=[proposal.id], usage=guard.usage.snapshot()))

        except BudgetExhausted as e:
            # 04 §7: budget exhausted -> PARTIAL, save committed work
            self.repo.set_job_status(job_id, JobStatus.PARTIAL.value, active_run_id=None,
                                     checkpoint_ref=str(e))
            self.repo.append_event(self._ev(
                job_id, revision, "FINISH", "PARTIAL",
                error=str(e), usage=guard.usage.snapshot(),
            ))
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
