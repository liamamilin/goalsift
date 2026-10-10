"""Checkpointed, budgeted research loop with atomic execution ownership."""
from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from typing import Any
import httpx
from .budget import BudgetConfig, BudgetExhausted, BudgetGuard
from .llm_adapter import LLMAdapter, ResourceMatch
from .models import (
    Assessment, AssessmentStatus, Capability, Condition, Dimension, DiscoveryStatus, Evidence,
    EvidenceStance, Goal, JobStatus, Obligation, Proposal, ProposalValidity,
    Provenance, Resource, ResearchEvent, ReviewStatus, SourceType, ValidityStatus, new_id,
)
from .repository import Repository
from .search_adapter import SearchAdapter
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
            self.repo.save_checkpoint(job_id, rev, {
                'stage': 'define', 'resource_ids': [r['id'] for r in previous['resources']],
                'evidence_ids': [e['id'] for e in previous['evidence']],
                'fetched_urls': [e['source_ref'] for e in previous['evidence']],
                'inspected_ids': [r['id'] for r in previous['resources']],
                'reused_sources': bool(previous['resources']),
            })
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
        try:
            config = BudgetConfig.from_env()
        except Exception as exc:
            reason = '预算配置错误：' + redact_secrets(str(exc))
            self.repo.finish_run(job_id, run_id, revision, 'FAILED', job.budget_usage, reason)
            self.repo.append_event(self._ev(job_id, revision, 'FINISH', 'FAILED', error=reason))
            self._runs.pop(job_id, None)
            return
        guard = BudgetGuard(config, job.budget_usage)
        state = self.repo.get_checkpoint(job_id, revision) or {'stage': 'define'}
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
            if goal:
                additions = [c['text'] for c in goal.constraints if isinstance(c, dict)
                             and c.get('text') and c['text'] != job.original_request]
                if additions: goal_text += '\n用户补充：' + '\n'.join(additions)
                # A model's definition cannot smuggle an unresearched feasibility
                # judgment, reuse percentage or candidate recommendation into the goal.
                goal.statement = goal_text
                self.repo.save_goal(goal)
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
                    goal.statement, goal.purpose = goal_text, definition.purpose
                    goal.requirements = [{'text': job.original_request, 'provenance': 'USER_STATED'}]
                    goal.assumptions = [{'text': s, 'provenance': 'SYSTEM_ASSUMED'} for s in definition.assumptions]
                    goal.open_questions = definition.open_questions
                    self.repo.save_goal(goal)
                    state['defined'] = True
                    checkpoint('derive')
                elif stage == 'derive':
                    specs = await external('REASON', 'DERIVED', self.llm.derive_conditions, goal_text)
                    if not specs: raise ValueError('模型没有返回可用于研究的条件')
                    with self.repo.transaction():
                        for sp in specs:
                            self.repo.save_condition(Condition(id=new_id('cond'), job_id=job_id,
                                statement=sp.statement, obligation=Obligation(sp.obligation),
                                dimension=Dimension(sp.dimension), origin='model-derived: ' + sp.rationale,
                                scope=goal_text, verification_method=sp.verification_method or '待核查具体验收条件',
                                revision_created=revision))
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
                            if rec == 'add_condition':
                                statement = finding.replacement or finding.finding
                                if statement not in by_statement:
                                    c = Condition(id=new_id('cond'), job_id=job_id, statement=statement,
                                        obligation=Obligation.REQUIRED, dimension=Dimension(finding.dimension),
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
                                        replacement.statement = finding.replacement
                                        replacement.validity_status = ValidityStatus.ACTIVE
                                        self.repo.save_condition(replacement)
                                self.repo.save_condition(target)
                        if not current_conditions(): raise ValueError('条件审查后没有有效条件')
                        state['challenged'] = True
                        checkpoint('match' if state.get('reused_sources') else 'plan_search')
                elif stage == 'plan_search':
                    plan = await external('REASON', 'SEARCH_PLANNED', self.llm.plan_search,
                        goal_text, [c.model_dump(mode='json') for c in current_conditions()],
                        state.get('gaps', []), state['queries'])
                    if not plan.query.strip() or plan.query in state['queries']:
                        state['delivery_notes'].append('没有产生新的有效检索方向，已停止重复研究。')
                        checkpoint('propose')
                    else:
                        state['pending_query'] = plan.query
                        checkpoint('search')
                elif stage == 'search':
                    results, meta = await external('SEARCH', 'SEARCHED', self.search.search,
                        state['pending_query'], 4, tool=True, reserve=getattr(self.search, 'search_reservation', 0.05))
                    known_urls = {r.canonical_source for r in source_objects()[0]}
                    added = 0
                    with self.repo.transaction():
                        if meta.get('rejected_urls'):
                            state['delivery_notes'].append(f"本次检索有 {meta['rejected_urls']} 个来源未通过公共 URL 安全校验，未用于判断。")
                        for hit in results:
                            if hit.url in known_urls: continue
                            if len(state['resource_ids']) >= 8:
                                if '候选目录限制为 8 个资源；未调查的候选不作结论。' not in state['delivery_notes']:
                                    state['delivery_notes'].append('候选目录限制为 8 个资源；未调查的候选不作结论。')
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
                            known_urls.add(hit.url)
                            added += 1
                        state['queries'].append(state['pending_query'])
                        state['rounds'] = state.get('rounds', 0) + 1
                        state['no_novelty'] = 0 if added else state.get('no_novelty', 0) + 1
                        checkpoint('decide' if not added and state.get('matched') else 'inspect')
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
                    payload = []
                    for r in fresh:
                        es = [e for e in evidence if e.source_ref in r.source_references
                              and e.stance == EvidenceStance.CONTEXT]
                        es.sort(key=lambda e: len(e.excerpt_or_summary), reverse=True)
                        payload.append({'resource_id': r.id, 'name': r.name, 'url': r.canonical_source,
                            'license': r.license_claim, 'sources': [{'evidence_id': e.id,
                            'text': e.excerpt_or_summary[:2400]} for e in es[:2]]})
                    matches = []
                    pending_matches = state.setdefault('pending_matches', {})
                    for item in payload:
                        rid = item['resource_id']
                        if rid not in pending_matches:
                            batch = await external('REASON', 'MATCHED', self.llm.assess_resources,
                                goal_text, [{'id': c.id, 'statement': c.statement, 'obligation': c.obligation.value, 'dimension': c.dimension.value} for c in conditions], [item])
                            pending_matches[rid] = [m.model_dump(mode='json') for m in batch]
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
                        if m.condition_id not in by_cond or m.resource_id not in {r.id for r in fresh}: continue
                        pair = (m.condition_id, m.resource_id)
                        if pair in seen: continue
                        seen.add(pair)
                        try: status = AssessmentStatus(m.status)
                        except ValueError: status = AssessmentStatus.UNKNOWN
                        if status == AssessmentStatus.VERIFIED: status = AssessmentStatus.SUPPORTED
                        es = [source_map[eid] for eid in m.evidence_ids if eid in source_map
                              and source_map[eid].source_ref in by_res[m.resource_id].source_references]
                        quote = m.supporting_quote.strip()
                        located = next((e for e in es if quote and quote in e.excerpt_or_summary), None)
                        ids = []
                        gaps = list(m.gaps)
                        if status == AssessmentStatus.CONFLICTED:
                            refuting = [source_map[eid] for eid in m.refuting_evidence_ids if eid in source_map
                                and source_map[eid].source_ref in by_res[m.resource_id].source_references]
                            refute_quote = m.refuting_quote.strip()
                            refute_source = next((e for e in refuting if refute_quote and refute_quote in e.excerpt_or_summary), None)
                            if located and refute_source and quote != refute_quote:
                                for src, excerpt, stance in ((located, quote, EvidenceStance.SUPPORTS),
                                        (refute_source, refute_quote, EvidenceStance.REFUTES)):
                                    e = Evidence(id=new_id('evidence'), job_id=job_id, claim=m.explanation,
                                        source_type=src.source_type, source_ref=src.source_ref,
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
                                    locator='exact source quote: ' + located.id,
                                    excerpt_or_summary=quote, collection_method=located.collection_method,
                                    stance=EvidenceStance.REFUTES if status == AssessmentStatus.NOT_SATISFIED else EvidenceStance.SUPPORTS)
                                claim_evidence.append(e)
                                ids = [e.id]
                        condition_text = by_cond[m.condition_id].statement.lower()
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
                            if old.revision_evaluated == revision and old.review_status == ReviewStatus.CURRENT and set(old.resource_ids) & fresh_ids:
                                old.review_status = ReviewStatus.SUPERSEDED
                                self.repo.save_assessment(old)
                        for e in claim_evidence:
                            self.repo.save_evidence(e)
                            state['evidence_ids'].append(e.id)
                        for cap in caps_by_res.values(): self.repo.save_capability(cap)
                        for a in assessments: self.repo.save_assessment(a)
                        all_current = [a for a in self.repo.list_assessments(job_id)
                            if a.revision_evaluated == revision and a.review_status == ReviewStatus.CURRENT]
                        state['gaps'] = [c.statement for c in conditions if c.obligation == Obligation.REQUIRED
                            and not any(a.condition_id == c.id and a.status in
                                        (AssessmentStatus.SUPPORTED, AssessmentStatus.VERIFIED) for a in all_current)]
                        state['matched_resource_ids'] = [r.id for r in resources]
                        state.pop('pending_matches', None)
                        state['matched'] = True
                        checkpoint('decide')
                elif stage == 'decide':
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
                        goal_text, view['resources'], view['assessments'])
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
