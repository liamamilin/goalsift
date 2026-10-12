"""Checkpointed, budgeted research loop with atomic execution ownership."""
from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from typing import Any
import httpx
from .budget import BudgetConfig, BudgetExhausted, BudgetGuard
from .goal_review import GoalReview, normalized, review_context
from .targeted_research import TargetedResearch
from .llm_adapter import LLMAdapter, ResourceMatch
from .models import (
    Assessment, AssessmentStatus, Capability, Condition, Dimension, DiscoveryStatus, Evidence,
    EvidenceStance, Goal, JobStatus, Obligation, Proposal, ProposalValidity,
    Provenance, Resource, ResearchEvent, ReviewStatus, SourceType, ValidityStatus, new_id,
)
from .repository import Repository
from .search_adapter import SearchAdapter
from .source_research import github_repository, related_document_links, select_excerpt, source_identity, locate_quote
from .security import redact_secrets
from .validators import (ValidationError, validate_transition, validate_references,
    validate_assessment_status, validate_evidence_sources, validate_conflict_handling,
    validate_traceability)

class PauseRequested(Exception):
    pass

class Controller:
    def __init__(self, repo: Repository, llm: LLMAdapter, search: SearchAdapter):
        self.repo, self.llm, self.search = repo, llm, search
        self._runs: dict[str, asyncio.Task] = {}
        self._pause_requests: set[str] = set()

    def _ev(self, job_id, revision, action, status, **extra):
        return ResearchEvent(id=new_id('ev'), event_id=new_id('ev'), job_id=job_id,
            revision=revision, run_id=extra.get('run_id'), action_type=action, status=status,
            related_object_ids=extra.get('refs', []), tool_result_ref=extra.get('tool_ref'),
            usage=extra.get('usage', {}), error=redact_secrets(str(extra.get('error') or '')) or None)

    def _stopped(self, job_id):
        job = self.repo.get_job(job_id)
        return not job or job.status in (JobStatus.PAUSED, JobStatus.CANCELLED) or job_id in self._pause_requests

    async def start(self, job_id):
        return await self._schedule_run(job_id)

    async def _schedule_run(self, job_id, revision=None, *, refine=False):
        task = self._runs.get(job_id)
        if task and not task.done(): return False
        run_id = new_id('run')
        if not self.repo.claim_run(job_id, run_id, refine=refine): return False
        job = self.repo.get_job(job_id)
        self._pause_requests.discard(job_id)
        self.repo.append_event(self._ev(job_id, job.current_revision, 'REASON', 'RESEARCHING', run_id=run_id))
        self._runs[job_id] = asyncio.create_task(self._run(job_id, run_id, job.current_revision))
        return True

    async def refine(self, job_id, constraint):
        job = self.repo.get_job(job_id)
        if not job or job.status != JobStatus.COMPLETED or not constraint.strip(): return False
        with self.repo.transaction():
            previous = self.repo.current_view(job_id)
            rev = self.repo.new_revision(job_id)
            self.repo.add_constraint(job_id, constraint.strip())
            # Reuse fetched sources, never carry forward their old applicability judgments.
            self.repo.save_checkpoint(job_id, rev, {'stage': 'define', **self._reused_sources(previous)})
        return await self._schedule_run(job_id, rev, refine=True)

    def _reused_sources(self, previous):
        grouped = {}
        for raw in previous['resources']:
            resource = Resource.model_validate(raw)
            key = source_identity(resource.canonical_source)
            if key not in grouped: grouped[key] = resource
            else:
                owner = grouped[key]
                owner.source_references = list(dict.fromkeys(owner.source_references + resource.source_references))
                claims = {owner.license_claim, resource.license_claim} - {None, 'UNKNOWN'}
                if len(claims) > 1: owner.license_claim = 'UNKNOWN'
        for resource in grouped.values(): self.repo.save_resource(resource)
        ids = [r.id for r in grouped.values()]
        return {'resource_ids': ids, 'inspected_ids': ids, 'reused_sources': bool(ids),
                'evidence_ids': [e['id'] for e in previous['evidence']],
                'fetched_urls': [e['source_ref'] for e in previous['evidence']]}

    async def investigate(self, job_id: str, request: TargetedResearch) -> bool:
        with self.repo.transaction():
            job = self.repo.get_job(job_id)
            if (not job or job.status != JobStatus.COMPLETED or job.active_run_id
                    or job.current_revision != request.expected_revision): return False
            config = BudgetConfig.from_env()
            if config.budget_usd is not None and request.budget_usd > config.budget_usd:
                raise ValueError('本次费用上限不能超过服务端研究上限')
            previous = self.repo.current_view(job_id)
            if not previous['goal']: raise ValueError('目标尚未定义，不能定向补查')
            conditions = {c['id']: Condition.model_validate(c) for c in previous['conditions']}
            resources = {r['id']: Resource.model_validate(r) for r in previous['resources']}
            if not set(request.condition_ids) <= conditions.keys(): raise ValueError('条件不属于当前修订')
            if not set(request.resource_ids) <= resources.keys(): raise ValueError('候选不属于当前修订')
            selected = set(request.condition_ids)
            owners = {}
            canonical = {rid: owners.setdefault(source_identity(r.canonical_source), rid) for rid, r in resources.items()}
            merged = {canonical[rid] for rid in resources if rid != canonical[rid]}
            # Source refresh can affect every judgment about that resource.
            scores = {'SUPPORTED': 3, 'VERIFIED': 3, 'PARTIAL': 1}
            ranked = sorted(resources, key=lambda rid: sum(scores.get(a['status'], 0)
                for a in previous['assessments'] if a['condition_id'] in selected and rid in a['resource_ids']), reverse=True)
            readable = [rid for rid in ranked if (github_repository(resources[rid].canonical_source) and hasattr(self.search, 'read_repository'))
                or related_document_links(resources[rid].canonical_source, [e['excerpt_or_summary'] for e in previous['evidence'] if e['source_ref'] in resources[rid].source_references])]
            targets = list(dict.fromkeys(canonical[rid] for rid in (request.resource_ids or readable)))[:2]
            revision = self.repo.new_revision(job_id)
            goal = self.repo.get_goal(job_id)
            goal.open_questions = list(previous['goal'].get('open_questions', []))
            self.repo.save_goal(goal)
            mapping = {cid: new_id('cond') for cid in conditions}
            for c in conditions.values():
                clone = c.model_copy(deep=True)
                clone.id, clone.lineage_id = mapping[c.id], c.lineage_id or c.id
                clone.revision_created = revision
                clone.relations = [{**rel, 'target_ids': [mapping[t] for t in rel['target_ids']]} for rel in c.relations]
                self.repo.save_condition(clone)
            state = self._reused_sources(previous)
            affected = {}
            for rid in state['resource_ids']:
                affected[rid] = list(mapping.values()) if rid in targets or rid in merged else (
                    [] if request.resource_ids else [mapping[cid] for cid in request.condition_ids])
            reused = []
            for raw in previous['assessments']:
                old = Assessment.model_validate(raw)
                if any(mapping[old.condition_id] in affected[canonical[rid]] for rid in old.resource_ids): continue
                clone = old.model_copy(deep=True)
                clone.id, clone.condition_id = new_id('assess'), mapping[old.condition_id]
                clone.revision_evaluated, clone.review_status = revision, ReviewStatus.CURRENT
                self.repo.save_assessment(clone)
                reused.append(clone.id)
            state.update(stage='deep_inspect' if targets else 'plan_search', defined=True, challenged=True,
                ambiguity_checked=True, matched=True, affected_conditions=affected,
                initial_resource_ids=list(state['resource_ids']),
                matched_resource_ids=[rid for rid, ids in affected.items() if not ids],
                deep_targets=targets, source_reviews=previous.get('source_reviews', {}),
                deep_inspected_ids=[rid for rid, review in previous.get('source_reviews', {}).items()
                    if review.get('status') in ('READ', 'UNAVAILABLE') and rid not in targets and rid in state['resource_ids']],
                reused_assessment_ids=reused,
                research_scope={'type': 'targeted', 'base_revision': request.expected_revision,
                    'condition_ids': [mapping[cid] for cid in request.condition_ids],
                    'resource_ids': list(dict.fromkeys(canonical[rid] for rid in request.resource_ids)), 'refreshed_resource_ids': targets,
                    'budget_usd': request.budget_usd, 'question': request.question},
                delivery_notes=['定向补查保留原目标与条件；未受影响的评价沿用前修订。新增资料会重新核查对应候选的全部条件。'])
            self.repo.save_checkpoint(job_id, revision, state)
            self.repo.append_event(self._ev(job_id, revision, 'REVISE', 'INVESTIGATION_REQUESTED',
                refs=request.condition_ids + request.resource_ids,
                usage={'scope': state['research_scope']}))
        return await self._schedule_run(job_id, revision, refine=True)

    async def review_goal(self, job_id: str, review: GoalReview) -> bool:
        """Apply a whole review atomically, then research its new revision."""
        with self.repo.transaction():
            job = self.repo.get_job(job_id)
            if (not job or job.status != JobStatus.COMPLETED or job.active_run_id
                    or job.current_revision != review.expected_revision): return False
            previous = self.repo.current_view(job_id)
            old_conditions = {c['id']: Condition.model_validate(c) for c in previous['conditions']}
            old_goal = self.repo.get_goal(job_id)
            if not old_goal: raise ValueError('目标尚未定义')
            if any(e.condition_id not in old_conditions for e in review.conditions):
                raise ValueError('条件不属于当前任务修订')
            if any(e.index >= len(old_goal.assumptions) for e in review.assumptions):
                raise ValueError('假设不属于当前目标')
            removed = {e.condition_id for e in review.conditions if e.action == 'remove'}
            if not set(old_conditions) - removed: raise ValueError('至少保留一项成立条件')
            if any(set(rel.get('target_ids', [])) & removed for c in old_conditions.values()
                   if c.id not in removed for rel in c.relations):
                raise ValueError('其他条件依赖待移除的条件；请先调整依赖条件')
            rev = self.repo.new_revision(job_id)
            goal = self.repo.get_goal(job_id)
            if review.purpose is not None:
                goal.purpose = review.purpose
                goal.constraints = [c for c in goal.constraints if not (
                    c.get('text', '').startswith('目标理解：') and c.get('provenance') == 'USER_CONFIRMED')]
                goal.constraints.append({'text': '目标理解：' + review.purpose, 'provenance': 'USER_CONFIRMED'})
            edits = {e.condition_id: e for e in review.conditions}
            new_ids = {cid: new_id('cond') for cid in old_conditions if cid not in removed}
            for old in old_conditions.values():
                edit = edits.get(old.id)
                if edit:
                    original = next((d['original_statement'] for d in goal.condition_decisions
                                     if normalized(d.get('statement', '')) == normalized(old.statement)), old.statement)
                    goal.condition_decisions = [d for d in goal.condition_decisions
                                                if normalized(d['original_statement']) != normalized(original)]
                    goal.condition_decisions.append({
                        'condition_id': old.id, 'original_statement': original,
                        'statement': edit.statement or old.statement, 'action': edit.action,
                        'obligation': (edit.obligation or old.obligation).value,
                        'dimension': (edit.dimension or old.dimension).value,
                        'verification_method': edit.verification_method if edit.verification_method is not None else old.verification_method,
                        'revision': rev, 'provenance': 'USER_CONFIRMED',
                    })
                if old.id in removed: continue
                c = old.model_copy(deep=True)
                c.id, c.revision_created = new_ids[old.id], rev
                c.lineage_id = old.lineage_id or old.id
                c.relations = [{**rel, 'target_ids': [new_ids[t] for t in rel['target_ids']]} for rel in c.relations]
                c.validity_status = ValidityStatus.ACTIVE
                c.created_at = c.updated_at = datetime.now(timezone.utc)
                if edit:
                    c.statement = edit.statement or c.statement
                    c.obligation = edit.obligation or c.obligation
                    c.dimension = edit.dimension or c.dimension
                    if edit.verification_method is not None: c.verification_method = edit.verification_method.strip()
                    c.provenance = Provenance.USER_CONFIRMED
                    c.origin = f'用户确认于修订 {rev}；原条件 {old.id}'
                self.repo.save_condition(c)
            assumption_edits = {e.index: e.action for e in review.assumptions}
            retained = []
            for index, a in enumerate(goal.assumptions):
                if index not in assumption_edits:
                    retained.append(a)
                    continue
                action = assumption_edits[index]
                goal.assumption_decisions = [d for d in goal.assumption_decisions if normalized(d['text']) != normalized(a['text'])]
                goal.assumption_decisions.append({'text': a['text'], 'action': action,
                                                 'provenance': 'USER_CONFIRMED', 'revision': rev})
                if action == 'confirm': goal.constraints.append({'text': a['text'], 'provenance': 'USER_CONFIRMED'})
            goal.assumptions = retained
            goal.requirements = [{'text': job.original_request, 'provenance': 'USER_STATED'}] + [
                {'text': d['statement'], 'provenance': 'USER_CONFIRMED'} for d in goal.condition_decisions if d['action'] != 'remove']
            self.repo.save_goal(goal)
            self.repo.save_checkpoint(job_id, rev, {
                'stage': 'challenge', 'defined': True, 'ambiguity_checked': True,
                **self._reused_sources(previous),
            })
            self.repo.append_event(self._ev(job_id, rev, 'REVISE', 'USER_REVIEWED',
                refs=[e.condition_id for e in review.conditions], usage={'review': review.model_dump(mode='json')}))
        return await self._schedule_run(job_id, rev, refine=True)

    async def answer_input(self, job_id, answer):
        job = self.repo.get_job(job_id)
        if not job or job.status != JobStatus.NEEDS_INPUT or not answer.strip(): return False
        with self.repo.transaction():
            self.repo.add_constraint(job_id, '[clarification] ' + answer.strip())
            goal = self.repo.get_goal(job_id)
            goal.open_questions = []
            self.repo.save_goal(goal)
            state = self.repo.get_checkpoint(job_id, job.current_revision)
            state.update(stage='define', clarified=True)
            self.repo.save_checkpoint(job_id, job.current_revision, state)
            self.repo.append_event(self._ev(job_id, job.current_revision, 'ASK_USER', 'INPUT_ANSWERED',
                                           usage={'answer': redact_secrets(answer.strip())}))
        return await self.start(job_id)

    def pause(self, job_id):
        job = self.repo.get_job(job_id)
        if not job or job.status not in (JobStatus.RESEARCHING, JobStatus.NEEDS_INPUT): return False
        if job.status == JobStatus.NEEDS_INPUT:
            self.repo.set_job_status(job_id, JobStatus.PAUSED.value, active_run_id=None)
        else:
            self._pause_requests.add(job_id)
        self.repo.append_event(self._ev(job_id, job.current_revision, 'REASON', 'PAUSE_REQUESTED'))
        return True

    def cancel(self, job_id):
        job = self.repo.get_job(job_id)
        if not job: return False
        try: validate_transition(job.status, JobStatus.CANCELLED)
        except ValidationError: return False
        task = self._runs.get(job_id)
        # Revoke ownership before interrupting so a late result can never commit.
        self.repo.set_job_status(job_id, JobStatus.CANCELLED.value, active_run_id=None)
        self.repo.append_event(self._ev(job_id, job.current_revision, 'FINISH', 'CANCELLED'))
        if task and not task.done(): task.cancel()
        return True

    async def shutdown(self):
        tasks = list(self._runs.values())
        for jid in list(self._runs): self.pause(jid)
        # A clean shutdown preserves checkpoints, and never starts another request.
        for task in tasks: task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        if isinstance(self.llm, LLMAdapter): await self.llm.close()

    async def _run(self, job_id, run_id, revision):
        job = self.repo.get_job(job_id)
        state = self.repo.get_checkpoint(job_id, revision) or {'stage': 'define'}
        try:
            config = BudgetConfig.from_env()
            if state.get('research_scope'):
                requested = state['research_scope']['budget_usd']
                config.budget_usd = min(requested, config.budget_usd) if config.budget_usd else requested
                config.max_search_rounds = min(config.max_search_rounds, 1)
        except Exception as exc:
            reason = '预算配置错误：' + redact_secrets(str(exc))
            self.repo.finish_run(job_id, run_id, revision, 'FAILED', job.budget_usage, reason)
            self.repo.append_event(self._ev(job_id, revision, 'FINISH', 'FAILED', error=reason))
            self._runs.pop(job_id, None)
            return
        guard = BudgetGuard(config, job.budget_usage)
        for key in ('resource_ids', 'evidence_ids', 'fetched_urls', 'queries', 'inspected_ids', 'delivery_notes'):
            state.setdefault(key, [])
        self.repo.set_job_status(job_id, JobStatus.RESEARCHING.value, budget_config=config.__dict__)

        def checkpoint(stage=None):
            with self.repo.transaction():
                if not self.repo.owns_run(job_id, run_id, revision): raise asyncio.CancelledError()
                if stage: state['stage'] = stage
                self.repo.save_checkpoint(job_id, revision, state)
                self.repo.set_job_status(job_id, JobStatus.RESEARCHING.value, budget_usage=guard.usage.snapshot())

        def event(action, status, **kw):
            self.repo.append_event(self._ev(job_id, revision, action, status, run_id=run_id, **kw))

        async def external(action, status, method, *args, tool=False, reserve=0.0):
            if not self.repo.owns_run(job_id, run_id, revision): raise asyncio.CancelledError()
            if job_id in self._pause_requests: raise PauseRequested()
            if action != 'SEARCH' and action != 'INSPECT' and isinstance(self.llm, LLMAdapter):
                reserve_value = self.llm.reservation(config.max_model_input_tokens, config.max_model_output_tokens)
                if reserve_value is None and config.budget_usd is not None:
                    raise BudgetExhausted('budget exhausted: unknown model price; configure token prices')
                reserve = reserve_value or 0.0
                self.llm.configure_limits(config.max_model_input_tokens, config.max_model_output_tokens)
            guard.check(tool_call=tool, reserve_usd=reserve)
            # Hold the full preflight estimate until a response reconciles actual usage.
            # Interrupted/unknown-billing requests retain this conservative charge.
            guard.usage.reserved_usd += reserve
            checkpoint()
            event(action, status + '_STARTED')
            observed_usage = {}
            async def invoke():
                try:
                    return await method(*args)
                finally:
                    if isinstance(self.llm, LLMAdapter) and action not in ('SEARCH', 'INSPECT'):
                        observed_usage.update(self.llm.pop_usage())
            try:
                value = await asyncio.wait_for(invoke(), timeout=min(
                    config.request_timeout_seconds, guard.remaining_seconds()))
            except Exception as exc:
                # Structured-output failures can still have a paid response.
                # Record its receipt; unknown/in-flight billing keeps the reservation.
                if observed_usage.get('input_tokens') or observed_usage.get('output_tokens'):
                    guard.usage.reserved_usd -= reserve
                    guard.record(observed_usage)
                    checkpoint()
                event(action, status + '_ERROR', usage=observed_usage,
                      error=type(exc).__name__ + ': ' + str(exc))
                raise
            if not self.repo.owns_run(job_id, run_id, revision): raise asyncio.CancelledError()
            if action in ('SEARCH', 'INSPECT'):
                stats = value[1]
            else:
                stats = observed_usage if isinstance(self.llm, LLMAdapter) else {
                    'cost_usd': 0.0, 'model_requests': 1}
            guard.usage.reserved_usd -= reserve
            guard.record(stats)
            checkpoint()
            event(action, status, usage=stats)
            return value

        def current_conditions():
            return [c for c in self.repo.list_conditions(job_id) if c.revision_created == revision
                    and c.validity_status == ValidityStatus.ACTIVE]

        def source_objects():
            rs = [r for r in self.repo.list_resources(job_id) if r.id in state['resource_ids']]
            es = [e for e in self.repo.list_evidence(job_id) if e.id in state['evidence_ids']]
            cs = [c for c in self.repo.list_capabilities(job_id) if c.resource_id in state['resource_ids']]
            return rs, es, cs

        def invalidate_resource(rid):
            # Invalidate at source commit, even if budget/pause blocks rematching.
            invalidated = set()
            for a in self.repo.list_assessments(job_id):
                if a.revision_evaluated == revision and a.review_status == ReviewStatus.CURRENT and rid in a.resource_ids:
                    a.review_status = ReviewStatus.NEEDS_REVIEW
                    self.repo.save_assessment(a)
                    invalidated.add(a.id)
            state['reused_assessment_ids'] = [aid for aid in state.get('reused_assessment_ids', []) if aid not in invalidated]
            if state.get('research_scope'): state['affected_conditions'][rid] = [c.id for c in current_conditions()]
            state['matched_resource_ids'] = [item for item in state.get('matched_resource_ids', []) if item != rid]
            state.setdefault('pending_matches', {}).pop(rid, None)
            state.setdefault('pending_match_payloads', {}).pop(rid, None)
            state.get('source_reviews', {}).get(rid, {}).pop('match_context', None)

        def save_deep_document(resource, doc):
            # Called inside an owned transaction. A read receipt is CONTEXT;
            # assess_resources must still produce a validated, exact quotation.
            e = Evidence(id=new_id('evidence'), job_id=job_id, claim='主要候选文档：' + resource.name,
                source_type=SourceType.SOURCE_CODE if doc.collection_method == 'github public API' else SourceType.OFFICIAL_DOC,
                source_ref=doc.url, locator='深度文档：' + (doc.category or doc.title),
                excerpt_or_summary=doc.text[:12000], source_version=doc.version,
                collection_method=doc.collection_method or 'exa /contents', stance=EvidenceStance.CONTEXT)
            self.repo.save_evidence(e)
            state['evidence_ids'].append(e.id)
            if doc.url not in state['fetched_urls']: state['fetched_urls'].append(doc.url)
            if doc.url not in resource.source_references: resource.source_references.append(doc.url)
            self.repo.save_resource(resource)
            review = state.setdefault('source_reviews', {}).setdefault(resource.id, {'documents': [], 'notes': []})
            review['documents'] = [d for d in review['documents'] if d['url'] != doc.url]
            review['documents'].append({'url': doc.url, 'category': doc.category or doc.title, 'version': doc.version})
            review['status'] = 'READ'
            state.setdefault('deep_read_urls', []).append(doc.url)
            invalidate_resource(resource.id)

        def settle(status, reason=None):
            usage = guard.usage.snapshot()
            if self.repo.finish_run(job_id, run_id, revision, status, usage, reason):
                event('FINISH', status, error=reason, usage=usage)
                if status == 'COMPLETED': self.repo.snapshot_revision(job_id)

        try:
            # No adapter/client is constructed at API import time; configuration failures are visible jobs.
            if isinstance(self.llm, LLMAdapter): self.llm.validate_config()
            if isinstance(self.search, SearchAdapter): self.search.validate_config()
            goal = self.repo.get_goal(job_id)
            goal_text = job.original_request
            statement_text = goal_text
            if goal:
                additions = [c['text'] for c in goal.constraints if isinstance(c, dict)
                             and c.get('text') and c['text'] != job.original_request]
                if additions: goal_text += '\n用户补充：' + '\n'.join(additions)
                statement_text = goal_text
                goal_text += '\n明确的用户复核决定（优先于原推导）：\n' + review_context(goal)
                # A model's definition cannot smuggle an unresearched feasibility
                # judgment, reuse percentage or candidate recommendation into the goal.
                goal.statement = statement_text
                self.repo.save_goal(goal)
            focus = state.get('research_scope')
            research_text = goal_text
            if focus:
                focused = [c.statement for c in current_conditions() if c.id in focus['condition_ids']]
                research_text += '\n本次仅补查以下条件，不改变目标或条件：\n' + '\n'.join(focused)
                if focus['question']: research_text += '\n本次调查问题：' + focus['question']
                if focus['resource_ids']:
                    research_text += '\n仅调查这些候选的资料：' + ', '.join(r.canonical_source for r in source_objects()[0] if r.id in focus['resource_ids'])
            while True:
                if not self.repo.owns_run(job_id, run_id, revision): raise asyncio.CancelledError()
                if job_id in self._pause_requests: raise PauseRequested()
                stage = state['stage']
                if stage == 'define':
                    if not goal:
                        goal = Goal(id=new_id('goal'), job_id=job_id, statement=goal_text,
                            original_user_text=job.original_request, revision=revision,
                            constraints=[{'text': job.original_request, 'provenance': 'USER_STATED'}])
                        with self.repo.transaction():
                            self.repo.save_goal(goal)
                            self.repo.set_job_status(job_id, JobStatus.RESEARCHING.value, current_goal_id=goal.id)
                    if not state.get('ambiguity_checked') and not state.get('clarified'):
                        amb = await external('REASON', 'AMBIGUITY_CHECKED', self.llm.check_ambiguity, goal_text)
                        state['ambiguity_checked'] = True
                        if amb.is_decisively_ambiguous and amb.question:
                            goal.open_questions = [amb.question]
                            self.repo.save_goal(goal)
                            checkpoint()
                            event('ASK_USER', 'NEEDS_INPUT', usage={'question': amb.question, 'rationale': amb.rationale})
                            settle('NEEDS_INPUT')
                            return
                        checkpoint()
                    definition = await external('REASON', 'DEFINED', self.llm.define_goal, goal_text)
                    goal.statement = statement_text
                    if not any(c['text'].startswith('目标理解：') and c['provenance'] == 'USER_CONFIRMED' for c in goal.constraints):
                        goal.purpose = definition.purpose
                    goal.requirements = [{'text': job.original_request, 'provenance': 'USER_STATED'}]
                    goal.requirements += [{'text': d['statement'], 'provenance': 'USER_CONFIRMED'}
                                          for d in goal.condition_decisions if d['action'] != 'remove']
                    reviewed_assumptions = {normalized(d['text']) for d in goal.assumption_decisions}
                    goal.assumptions = [{'text': s, 'provenance': 'SYSTEM_ASSUMED'}
                                        for s in definition.assumptions if normalized(s) not in reviewed_assumptions]
                    goal.open_questions = definition.open_questions
                    self.repo.save_goal(goal)
                    state['defined'] = True
                    checkpoint('derive')
                elif stage == 'derive':
                    specs = await external('REASON', 'DERIVED', self.llm.derive_conditions, goal_text)
                    if not specs and not any(d['action'] != 'remove' for d in goal.condition_decisions):
                        raise ValueError('模型没有返回可用于研究的条件')
                    reviewed_texts = {normalized(d[k]) for d in goal.condition_decisions for k in ('original_statement', 'statement')}
                    parent = self.repo.get_revision(job_id, revision - 1) or {}
                    ancestors = {}
                    for c in parent.get('conditions', []): ancestors.setdefault(normalized(c['statement']), []).append(c)
                    def lineage(statement):
                        matches = ancestors.get(normalized(statement), [])
                        return (matches[0].get('lineage_id') or matches[0]['id']) if len(matches) == 1 else None
                    with self.repo.transaction():
                        for sp in specs:
                            if normalized(sp.statement) in reviewed_texts: continue
                            self.repo.save_condition(Condition(id=new_id('cond'), job_id=job_id,
                                statement=sp.statement, obligation=Obligation(sp.obligation),
                                dimension=Dimension(sp.dimension), origin='model-derived: ' + sp.rationale,
                                lineage_id=lineage(sp.statement),
                                scope=goal_text, verification_method=sp.verification_method or '待核查具体验收条件',
                                revision_created=revision))
                        for d in goal.condition_decisions:
                            if d['action'] == 'remove': continue
                            self.repo.save_condition(Condition(id=new_id('cond'), job_id=job_id,
                                statement=d['statement'], obligation=d['obligation'], dimension=d['dimension'],
                                verification_method=d.get('verification_method'), provenance=Provenance.USER_CONFIRMED,
                                lineage_id=lineage(d['statement']),
                                origin='用户已确认：' + d['condition_id'], scope=goal_text, revision_created=revision))
                        checkpoint('challenge')
                elif stage == 'challenge':
                    conditions = current_conditions()
                    report = await external('REVISE', 'CHALLENGED', self.llm.challenge_conditions,
                        goal_text, [c.model_dump(mode='json') for c in conditions])
                    by_statement = {c.statement: c for c in conditions}
                    with self.repo.transaction():
                        for finding in report.findings:
                            target = by_statement.get(finding.target_condition)
                            rec = finding.recommendation.lower()
                            if target and target.provenance == Provenance.USER_CONFIRMED:
                                if rec != 'keep': state['delivery_notes'].append('已确认条件保持不变；复核建议：' + finding.finding)
                                continue
                            if normalized(finding.replacement or finding.finding) in {
                                normalized(d[k]) for d in goal.condition_decisions for k in ('original_statement', 'statement')
                            }: continue
                            if rec == 'add_condition':
                                statement = finding.replacement or finding.finding
                                if statement not in by_statement:
                                    c = Condition(id=new_id('cond'), job_id=job_id, statement=statement,
                                        obligation=Obligation(finding.obligation), dimension=Dimension(finding.dimension),
                                        origin='challenge: ' + finding.finding, scope=goal_text,
                                        verification_method='需要来源或限定环境的实际验收', revision_created=revision)
                                    self.repo.save_condition(c)
                                    by_statement[statement] = c
                            elif target:
                                target.origin += '; challenge: ' + finding.finding
                                if rec == 'mark_optional': target.obligation = Obligation.OPTIONAL
                                elif rec == 'supersede':
                                    target.validity_status = ValidityStatus.SUPERSEDED
                                    if finding.replacement:
                                        replacement = target.model_copy(deep=True)
                                        replacement.id = new_id('cond')
                                        replacement.lineage_id = target.lineage_id or target.id
                                        replacement.statement = finding.replacement
                                        replacement.validity_status = ValidityStatus.ACTIVE
                                        self.repo.save_condition(replacement)
                                self.repo.save_condition(target)
                        if not current_conditions(): raise ValueError('条件审查后没有有效条件')
                        state['challenged'] = True
                        checkpoint('match' if state.get('reused_sources') else 'plan_search')
                elif stage == 'plan_search':
                    search_conditions = [c for c in current_conditions() if not focus or c.id in focus['condition_ids']]
                    plan = await external('REASON', 'SEARCH_PLANNED', self.llm.plan_search,
                        research_text, [c.model_dump(mode='json') for c in search_conditions],
                        [c.statement for c in search_conditions] if focus else state.get('gaps', []), state['queries'])
                    if not plan.query.strip() or plan.query in state['queries']:
                        state['delivery_notes'].append('没有产生新的有效检索方向，已停止重复研究。')
                        checkpoint('propose')
                    else:
                        state['pending_query'] = plan.query
                        checkpoint('search')
                elif stage == 'search':
                    results, meta = await external('SEARCH', 'SEARCHED', self.search.search,
                        state['pending_query'], 4, tool=True, reserve=getattr(self.search, 'search_reservation', 0.05))
                    known_resources = {source_identity(r.canonical_source): r for r in source_objects()[0]}
                    added = 0
                    added_sources = 0
                    with self.repo.transaction():
                        if meta.get('rejected_urls'):
                            state['delivery_notes'].append(f"本次检索有 {meta['rejected_urls']} 个来源未通过公共 URL 安全校验，未用于判断。")
                        for hit in results:
                            key = source_identity(hit.url)
                            existing = known_resources.get(key)
                            if focus and focus['resource_ids'] and (not existing or existing.id not in focus['resource_ids']): continue
                            if existing:
                                if hit.url in existing.source_references or not hit.text: continue
                                existing.source_references.append(hit.url)
                                self.repo.save_resource(existing)
                                e = Evidence(id=new_id('evidence'), job_id=job_id,
                                    claim='同一候选的补充检索来源：' + existing.name, source_type=SourceType.THIRD_PARTY,
                                    source_ref=hit.url, locator='Exa /search contents.text',
                                    excerpt_or_summary=hit.text[:12000], collection_method='exa /search',
                                    stance=EvidenceStance.CONTEXT, source_version=hit.version)
                                self.repo.save_evidence(e)
                                state['evidence_ids'].append(e.id)
                                state['fetched_urls'].append(hit.url)
                                invalidate_resource(existing.id)
                                added_sources += 1
                                continue
                            limit = min(len(state.get('initial_resource_ids', state['resource_ids'])) + 2, 24) if focus else 8
                            if len(state['resource_ids']) >= limit:
                                note = f'本修订候选目录上限为 {limit} 个；未调查的候选不作结论。'
                                if note not in state['delivery_notes']: state['delivery_notes'].append(note)
                                break
                            resource = Resource(id=new_id('res'), job_id=job_id, name=hit.title or hit.url,
                                kind='web_resource', description=hit.text[:800], canonical_source=hit.url,
                                source_references=[hit.url], license_claim='UNKNOWN',
                                version_or_revision=hit.version,
                                discovery_status='CONFIRMED_EXISTENCE' if hit.text else 'UNVERIFIED_LEAD')
                            self.repo.save_resource(resource)
                            state['resource_ids'].append(resource.id)
                            if hit.text:
                                evidence = Evidence(id=new_id('evidence'), job_id=job_id,
                                    claim='来源读取记录：' + resource.name, source_type=SourceType.THIRD_PARTY,
                                    source_ref=hit.url, locator='Exa /search contents.text',
                                    excerpt_or_summary=hit.text[:12000], collection_method='exa /search',
                                    stance=EvidenceStance.CONTEXT, source_version=hit.version)
                                self.repo.save_evidence(evidence)
                                state['evidence_ids'].append(evidence.id)
                                state['fetched_urls'].append(hit.url)
                            known_resources[key] = resource
                            added += 1
                        state['queries'].append(state['pending_query'])
                        state['rounds'] = state.get('rounds', 0) + 1
                        state['no_novelty'] = 0 if added or added_sources else state.get('no_novelty', 0) + 1
                        checkpoint(('match' if added_sources else 'decide') if not added and state.get('matched') else 'inspect')
                elif stage == 'inspect':
                    resources, evidence, _ = source_objects()
                    pending = [r for r in resources if r.id not in state['inspected_ids']]
                    for resource in pending:
                        try:
                            hit, meta = await external('INSPECT', 'SOURCE_READ', self.search.read_source,
                                resource.canonical_source, tool=True,
                                reserve=getattr(self.search, 'read_reservation', 0.02))
                        except (BudgetExhausted, PauseRequested, asyncio.CancelledError): raise
                        except Exception as exc:
                            state['delivery_notes'].append(f'{resource.name} 全文读取失败：{type(exc).__name__}；仅保留已有来源。')
                            state['inspected_ids'].append(resource.id)
                            checkpoint()
                            continue
                        with self.repo.transaction():
                            e = Evidence(id=new_id('evidence'), job_id=job_id,
                                claim='全文来源读取：' + resource.name, source_type=SourceType.THIRD_PARTY,
                                source_ref=hit.url, locator='Exa /contents full source text',
                                excerpt_or_summary=hit.text[:12000], collection_method='exa /contents',
                                stance=EvidenceStance.CONTEXT, source_version=hit.version)
                            self.repo.save_evidence(e)
                            state['evidence_ids'].append(e.id)
                            state['fetched_urls'].append(hit.url)
                            resource.description = hit.text[:800]
                            if hit.url not in resource.source_references: resource.source_references.append(hit.url)
                            resource.discovery_status = DiscoveryStatus.CONFIRMED_EXISTENCE
                            # Public availability alone never becomes a commercial license.
                            import re
                            license_match = re.search(r'(?i)(?:licensed under|license[:\s]+|released under)[^\n]{0,80}?(MIT|Apache(?: License)?[ -]?2(?:\.0)?|BSD-3-Clause|BSD-2-Clause|MPL-2\.0)\b', hit.text)
                            if license_match:
                                resource.license_claim = license_match.group(1)
                                license_evidence = Evidence(id=new_id('evidence'), job_id=job_id,
                                    claim='来源明确的许可声明：' + resource.license_claim,
                                    source_type=SourceType.THIRD_PARTY, source_ref=hit.url,
                                    locator='license statement', excerpt_or_summary=license_match.group(0),
                                    collection_method='exa /contents', stance=EvidenceStance.CONTEXT)
                                self.repo.save_evidence(license_evidence)
                                state['evidence_ids'].append(license_evidence.id)
                            self.repo.save_resource(resource)
                            state['inspected_ids'].append(resource.id)
                            checkpoint()
                    checkpoint('match')
                elif stage == 'match':
                    conditions = current_conditions()
                    resources, evidence, capabilities = source_objects()
                    if not resources:
                        state['gaps'] = [c.statement for c in conditions if c.obligation == Obligation.REQUIRED]
                        checkpoint('decide')
                        continue
                    source_map = {e.id: e for e in evidence}
                    completed_ids = set(state.get('matched_resource_ids', []))
                    fresh = [r for r in resources if r.id not in completed_ids]
                    pending_matches = state.setdefault('pending_matches', {})
                    pending_payloads = state.setdefault('pending_match_payloads', {})
                    focus_ids = set((state.get('research_scope') or {}).get('condition_ids', []))
                    focus_text = '\n'.join(c.statement for c in conditions if not focus_ids or c.id in focus_ids)
                    focus_text += '\n' + (state.get('research_scope') or {}).get('question', '')
                    payload = []
                    for r in fresh:
                        if r.id in pending_payloads:
                            payload.append(pending_payloads[r.id])
                            continue
                        es = [e for e in evidence if e.source_ref in r.source_references
                              and e.stance == EvidenceStance.CONTEXT]
                        latest = {}
                        for e in sorted(es, key=lambda e: e.retrieved_at): latest[e.source_ref] = e
                        es = list(latest.values())
                        es.sort(key=lambda e: (e.locator.startswith('深度文档：'), len(e.excerpt_or_summary)), reverse=True)
                        payload.append({'resource_id': r.id, 'name': r.name, 'url': r.canonical_source,
                            'license': r.license_claim, 'sources': [{'evidence_id': e.id,
                            'url': e.source_ref, 'category': e.locator,
                            **select_excerpt(e.excerpt_or_summary, '' if r.id in pending_matches else focus_text)} for e in es[:6]]})
                    matches = []
                    provided_by_resource = {item['resource_id']: [source_map[s['evidence_id']] for s in item['sources']] for item in payload}
                    condition_ids_by_resource = {r.id: set(state.get('affected_conditions', {}).get(r.id, [c.id for c in conditions])) for r in fresh}
                    for item in payload:
                        rid = item['resource_id']
                        if rid not in pending_matches:
                            batch = await external('REASON', 'MATCHED', self.llm.assess_resources,
                                goal_text, [{'id': c.id, 'statement': c.statement, 'obligation': c.obligation.value, 'dimension': c.dimension.value} for c in conditions if c.id in condition_ids_by_resource[rid]], [item])
                            pending_matches[rid] = [m.model_dump(mode='json') for m in batch]
                            pending_payloads[rid] = item
                            checkpoint()
                        matches.extend(ResourceMatch.model_validate(m) for m in pending_matches[rid])
                    by_cond, by_res = {c.id: c for c in conditions}, {r.id: r for r in resources}
                    assessments, claim_evidence = [], []
                    caps_by_res = {c.resource_id: c for c in capabilities}
                    for r in resources:
                        if r.id not in caps_by_res:
                            es = [e for e in evidence if e.source_ref in r.source_references]
                            caps_by_res[r.id] = Capability(id=new_id('cap'), job_id=job_id, resource_id=r.id,
                                statement=r.description or '能力未获得足够来源',
                                limitations=['未经目标环境验收', '许可和适用前提需逐项检查'],
                                evidence_ids=[e.id for e in es])
                    seen = set()
                    for m in matches:
                        # Never repair a hallucinated reference by attaching it to the first object.
                        if m.condition_id not in by_cond or m.condition_id not in condition_ids_by_resource.get(m.resource_id, set()): continue
                        pair = (m.condition_id, m.resource_id)
                        if pair in seen: continue
                        seen.add(pair)
                        try: status = AssessmentStatus(m.status)
                        except ValueError: status = AssessmentStatus.UNKNOWN
                        if status == AssessmentStatus.VERIFIED: status = AssessmentStatus.SUPPORTED
                        es = [source_map[eid] for eid in m.evidence_ids if eid in source_map
                              and source_map[eid].source_ref in by_res[m.resource_id].source_references]
                        quote = m.supporting_quote.strip()
                        available = provided_by_resource.get(m.resource_id, [])
                        ranges = {s['evidence_id']: s['excerpt_ranges'] for item in payload if item['resource_id'] == m.resource_id for s in item['sources']}
                        located, quote = locate_quote(quote, es, available, ranges)
                        ids = []
                        gaps = list(m.gaps)
                        if status == AssessmentStatus.CONFLICTED:
                            refuting = [source_map[eid] for eid in m.refuting_evidence_ids if eid in source_map
                                and source_map[eid].source_ref in by_res[m.resource_id].source_references]
                            refute_quote = m.refuting_quote.strip()
                            refute_source, refute_quote = locate_quote(refute_quote, refuting, available, ranges)
                            if located and refute_source and quote != refute_quote:
                                for src, excerpt, stance in ((located, quote, EvidenceStance.SUPPORTS),
                                        (refute_source, refute_quote, EvidenceStance.REFUTES)):
                                    e = Evidence(id=new_id('evidence'), job_id=job_id, claim=m.explanation,
                                        source_type=src.source_type, source_ref=src.source_ref,
                                        source_version=src.source_version, retrieved_at=src.retrieved_at,
                                        locator='exact source quote: ' + src.id, excerpt_or_summary=excerpt,
                                        collection_method=src.collection_method, stance=stance)
                                    claim_evidence.append(e)
                                    ids.append(e.id)
                            else:
                                status = AssessmentStatus.UNKNOWN
                                gaps.append('冲突缺少两条可定位的相反原文依据')
                        if status in (AssessmentStatus.SUPPORTED, AssessmentStatus.PARTIAL, AssessmentStatus.NOT_SATISFIED):
                            if not located:
                                status = AssessmentStatus.UNKNOWN
                                gaps.append('判断缺少可定位的原文依据，已降为 UNKNOWN')
                            else:
                                e = Evidence(id=new_id('evidence'), job_id=job_id, claim=m.explanation,
                                    source_type=located.source_type, source_ref=located.source_ref,
                                    source_version=located.source_version, retrieved_at=located.retrieved_at,
                                    locator='exact source quote: ' + located.id,
                                    excerpt_or_summary=quote, collection_method=located.collection_method,
                                    stance=EvidenceStance.REFUTES if status == AssessmentStatus.NOT_SATISFIED else EvidenceStance.SUPPORTS)
                                claim_evidence.append(e)
                                ids = [e.id]
                        condition_text = by_cond[m.condition_id].statement.lower()
                        if status == AssessmentStatus.SUPPORTED and any(word in condition_text for word in ('commercial', '商用')) and located and located.locator == '深度文档：仓库与许可声明':
                            status = AssessmentStatus.PARTIAL
                            gaps.append('许可元数据只说明许可标识；商用适用性还需核对许可原文与使用范围')
                        if status in (AssessmentStatus.SUPPORTED, AssessmentStatus.PARTIAL, AssessmentStatus.NOT_SATISFIED) and any(word in condition_text for word in ('license', 'commercial', '商用', '许可', '开源')) and by_res[m.resource_id].license_claim == 'UNKNOWN':
                            status = AssessmentStatus.UNKNOWN
                            gaps.append('未确认资源许可；不能据此认定可商用或符合开源约束')
                        if not ids: ids = [e.id for e in es]
                        a = Assessment(id=new_id('assess'), job_id=job_id, condition_id=m.condition_id,
                            resource_ids=[m.resource_id], capability_ids=[caps_by_res[m.resource_id].id],
                            status=status, context=goal_text, evidence_ids=ids, explanation=m.explanation,
                            gaps=gaps, revision_evaluated=revision)
                        if validate_assessment_status(a, evidence + claim_evidence) or validate_conflict_handling([a], evidence + claim_evidence):
                            a.status = AssessmentStatus.UNKNOWN
                            a.gaps.append('证据等级或冲突规则未通过，保留为未知')
                        assessments.append(a)
                    for c in conditions:
                        for r in fresh:
                            if c.id not in condition_ids_by_resource[r.id]: continue
                            if (c.id, r.id) not in seen:
                                es = [e.id for e in evidence if e.source_ref in r.source_references]
                                assessments.append(Assessment(id=new_id('assess'), job_id=job_id,
                                    condition_id=c.id, resource_ids=[r.id], capability_ids=[caps_by_res[r.id].id],
                                    evidence_ids=es, context=goal_text, status=AssessmentStatus.UNKNOWN,
                                    explanation='当前来源不足以判断该条件的满足程度。',
                                    gaps=['需补充相关能力、许可或组合证据'], revision_evaluated=revision))
                    problems = validate_references(job_id=job_id, conditions=conditions, resources=resources,
                        capabilities=list(caps_by_res.values()), evidence=evidence + claim_evidence,
                        assessments=assessments, proposals=[])
                    problems += validate_evidence_sources(evidence + claim_evidence, set(state['fetched_urls']))
                    if problems: raise ValueError('; '.join(problems))
                    with self.repo.transaction():
                        fresh_ids = {r.id for r in fresh}
                        for old in self.repo.list_assessments(job_id):
                            if (old.revision_evaluated == revision and old.review_status in (ReviewStatus.CURRENT, ReviewStatus.NEEDS_REVIEW)
                                    and any(rid in fresh_ids and old.condition_id in condition_ids_by_resource[rid] for rid in old.resource_ids)):
                                old.review_status = ReviewStatus.SUPERSEDED
                                self.repo.save_assessment(old)
                        for e in claim_evidence:
                            self.repo.save_evidence(e)
                            state['evidence_ids'].append(e.id)
                        for cap in caps_by_res.values(): self.repo.save_capability(cap)
                        for a in assessments: self.repo.save_assessment(a)
                        for item in payload:
                            review = state.setdefault('source_reviews', {}).setdefault(item['resource_id'], {'documents': [], 'notes': []})
                            review['match_context'] = [{k: s[k] for k in ('evidence_id', 'url', 'stored_characters', 'supplied_characters', 'is_partial', 'excerpt_ranges')} for s in item['sources']]
                        state['reused_assessment_ids'] = [a.id for a in self.repo.list_assessments(job_id)
                            if a.id in state.get('reused_assessment_ids', []) and a.review_status == ReviewStatus.CURRENT]
                        all_current = [a for a in self.repo.list_assessments(job_id)
                            if a.revision_evaluated == revision and a.review_status == ReviewStatus.CURRENT]
                        state['gaps'] = [c.statement for c in conditions if c.obligation == Obligation.REQUIRED
                            and not any(a.condition_id == c.id and a.status in
                                        (AssessmentStatus.SUPPORTED, AssessmentStatus.VERIFIED) for a in all_current)]
                        state['matched_resource_ids'] = [r.id for r in resources]
                        state.pop('pending_matches', None)
                        state.pop('pending_match_payloads', None)
                        state['matched'] = True
                        checkpoint('decide')
                elif stage == 'deep_inspect':
                    resources, evidence, _ = source_objects()
                    completed = state.setdefault('deep_inspected_ids', [])
                    targets = state['deep_targets']
                    for rid in targets:
                        if rid in completed: continue
                        resource = next(r for r in resources if r.id == rid)
                        if github_repository(resource.canonical_source) and hasattr(self.search, 'read_repository'):
                            try:
                                docs, meta = await external('INSPECT', 'REPOSITORY_DOCUMENTS',
                                    self.search.read_repository, resource.canonical_source, tool=True, reserve=0.0)
                            except (BudgetExhausted, PauseRequested, asyncio.CancelledError): raise
                            except Exception as exc:
                                docs, meta = [], {'notes': ['仓库文档读取失败：' + type(exc).__name__]}
                            for note in meta.get('notes', []): state['delivery_notes'].append(resource.name + '：' + note)
                            claim = meta.get('license_claim', 'UNKNOWN')
                            if docs and claim != 'UNKNOWN': resource.license_claim = claim
                        else:
                            urls = related_document_links(resource.canonical_source,
                                [e.excerpt_or_summary for e in evidence if e.source_ref in resource.source_references])
                            if focus and not urls: urls = [resource.canonical_source]
                            docs = []
                            for url in urls:
                                if url in state.get('deep_read_urls', []) or (not focus and url in resource.source_references): continue
                                try:
                                    doc, _ = await external('INSPECT', 'LINKED_DOCUMENT', self.search.read_source,
                                        url, tool=True, reserve=getattr(self.search, 'read_reservation', 0.02))
                                    doc.category = '许可、接口或部署文档'
                                    docs.append(doc)
                                    # Commit each paid read before attempting another one.
                                    with self.repo.transaction():
                                        save_deep_document(resource, doc)
                                        checkpoint()
                                except (BudgetExhausted, PauseRequested, asyncio.CancelledError): raise
                                except Exception as exc:
                                    state['delivery_notes'].append(resource.name + ' 关联文档读取失败：' + type(exc).__name__)
                        with self.repo.transaction():
                            if github_repository(resource.canonical_source):
                                for doc in docs: save_deep_document(resource, doc)
                            self.repo.save_resource(resource)
                            completed.append(rid)
                            review = state.setdefault('source_reviews', {}).setdefault(rid, {'documents': [], 'notes': []})
                            review['status'] = 'READ' if review['documents'] else 'UNAVAILABLE'
                            review['notes'] = meta.get('notes', []) if github_repository(resource.canonical_source) else []
                            if docs:
                                state['matched_resource_ids'] = [id for id in state.get('matched_resource_ids', []) if id != rid]
                                state.setdefault('pending_matches', {}).pop(rid, None)
                                state.setdefault('pending_match_payloads', {}).pop(rid, None)
                            else: state['delivery_notes'].append(resource.name + '：未获得额外文档，相关问题仍待核查。')
                            checkpoint()
                    checkpoint('match')
                elif stage == 'decide':
                    resources, evidence, _ = source_objects()
                    if focus:
                        if state.get('rounds', 0) < config.max_search_rounds: checkpoint('plan_search')
                        else: checkpoint('propose')
                        continue
                    if not state.get('deep_targets'):
                        assessments = self.repo.current_view(job_id)['assessments']
                        def rank(r):
                            scores = {'SUPPORTED': 3, 'VERIFIED': 3, 'PARTIAL': 1}
                            return sum(scores.get(a['status'], 0) for a in assessments if r.id in a['resource_ids'])
                        candidates = [r for r in resources if (
                            (github_repository(r.canonical_source) and hasattr(self.search, 'read_repository'))
                            or related_document_links(r.canonical_source, [e.excerpt_or_summary for e in evidence if e.source_ref in r.source_references]))]
                        candidates.sort(key=rank, reverse=True)
                        seen_sources = set()
                        unique = []
                        for r in candidates:
                            key = source_identity(r.canonical_source)
                            if key in seen_sources: continue
                            seen_sources.add(key)
                            unique.append(r)
                        candidates = unique
                        if candidates:
                            state['deep_targets'] = [r.id for r in candidates[:2]]
                            checkpoint('deep_inspect')
                            continue
                    # Unknown coverage, no candidates and license/integration gaps direct subsequent searches.
                    more = bool(state.get('gaps')) and state.get('rounds', 0) < config.max_search_rounds
                    if state.get('no_novelty', 0) >= 2: more = False
                    if more: checkpoint('plan_search')
                    else:
                        if state.get('gaps'): state['delivery_notes'].append('检索范围内仍有未覆盖条件；这些缺口已保留，不代表目标已实现。')
                        checkpoint('propose')
                elif stage == 'propose':
                    view = self.repo.current_view(job_id)
                    eligible = [a for a in view['assessments'] if a['status'] in ('SUPPORTED', 'PARTIAL', 'VERIFIED')]
                    if not eligible:
                        state['delivery_notes'].append('当前检索没有形成有依据的候选路径；请查看未知项或补充研究范围。')
                        checkpoint('finish')
                        continue
                    draft = await external('PROPOSE', 'PROPOSED', self.llm.draft_proposal,
                        goal_text, [{**r, 'read_documents': state.get('source_reviews', {}).get(r['id'], {}).get('documents', [])}
                                    for r in view['resources']], view['assessments'])
                    resources, evidence, capabilities = source_objects()
                    assessments = [Assessment.model_validate(a) for a in view['assessments']]
                    selected = set(draft.resource_ids)
                    valid_ids = {r.id for r in resources}
                    if not selected or not selected <= valid_ids:
                        raise ValueError('方案包含未调查或未选择的资源引用')
                    if not selected & {rid for a in eligible for rid in a['resource_ids']}:
                        raise ValueError('所选路径没有任何来源支持的能力')
                    relevant = [a for a in assessments if set(a.resource_ids) & selected]
                    conditions = current_conditions()
                    covered = {a.condition_id for a in relevant if a.status in (AssessmentStatus.SUPPORTED, AssessmentStatus.VERIFIED)}
                    proposal = Proposal(id=new_id('prop'), job_id=job_id, title=draft.title, summary=draft.summary,
                        resource_ids=sorted(selected), assessment_ids=[a.id for a in relevant],
                        condition_coverage=sorted(covered), integration_work=draft.integration_work,
                        new_work=draft.new_work, uncovered_conditions=[c.id for c in conditions if c.id not in covered],
                        risks=draft.risks, assumptions=[a['text'] for a in goal.assumptions],
                        costs={'estimate': 'UNKNOWN', 'basis': '没有经核实的方案实施价格'},
                        recommendation_reason=draft.recommendation_reason,
                        validity_status=ProposalValidity.READY_FOR_REVIEW, revision_created=revision)
                    if not selected <= set(state.get('deep_inspected_ids', [])):
                        proposal.risks.append('部分所选资源没有补充文档读取；许可、接口、部署和依赖缺口需人工核查。')
                    problems = validate_references(job_id=job_id, conditions=conditions, resources=resources,
                        capabilities=capabilities, evidence=evidence, assessments=assessments, proposals=[proposal])
                    # UNKNOWN can be traceable to the explicit absence of sufficient evidence.
                    problems += validate_traceability(proposal, relevant, conditions, resources, capabilities, evidence)
                    if problems: raise ValueError('; '.join(problems))
                    with self.repo.transaction():
                        self.repo.save_proposal(proposal)
                        checkpoint('finish')
                elif stage == 'finish':
                    if not state.get('defined') or not state.get('challenged'):
                        raise ValueError('交付检查失败：目标定义或条件挑战尚未完成')
                    if not state.get('queries') and not state.get('reused_sources'):
                        raise ValueError('交付检查失败：没有实际检索或已读取的可复用来源')
                    checkpoint()
                    settle('COMPLETED')
                    return
                else: raise ValueError('未知研究检查点：' + stage)
        except PauseRequested:
            settle('PAUSED')
        except asyncio.CancelledError:
            # Cancellation revokes ownership; clean shutdown still owns it and becomes PAUSED.
            settle('PAUSED', '服务停止；已提交数据保留，可继续研究')
        except BudgetExhausted as exc:
            settle('PARTIAL', str(exc))
        except (httpx.HTTPError, TimeoutError, asyncio.TimeoutError) as exc:
            settle('PARTIAL', redact_secrets(type(exc).__name__ + ': ' + str(exc)))
        except Exception as exc:
            settle('FAILED', redact_secrets(type(exc).__name__ + ': ' + str(exc)))
        finally:
            if self._runs.get(job_id) is asyncio.current_task(): self._runs.pop(job_id, None)
            self._pause_requests.discard(job_id)
