"""Real Controller/SQLite/API integration; only paid providers are deterministic fixtures."""
from __future__ import annotations
import asyncio
from concurrent.futures import ThreadPoolExecutor
import httpx
import pytest
from fastapi.testclient import TestClient
from goalsift.app import create_app
from goalsift.controller import Controller
from goalsift.exporter import to_json, to_markdown
from goalsift.llm_adapter import (
    AmbiguityCheck, GoalDefinition, ConditionSpec, ChallengeReport, ChallengeFinding,
    SearchPlan, ResourceMatch, ProposalDraft,
)
from goalsift.models import JobStatus
from goalsift.repository import Repository
from goalsift.search_adapter import SearchResult

class ModelFixture:
    def __init__(self, ambiguous=False, hallucinate=False, challenge_add=False):
        self.calls = []
        self.ambiguous, self.hallucinate, self.challenge_add = ambiguous, hallucinate, challenge_add
    async def check_ambiguity(self, text):
        self.calls.append('ambiguity')
        return AmbiguityCheck(is_decisively_ambiguous=self.ambiguous, question='管理哪种运行时？', rationale='接口决定方案空间')
    async def define_goal(self, text):
        self.calls.append('define')
        return GoalDefinition(statement=text, assumptions=['尚未在目标环境验收'])
    async def derive_conditions(self, text):
        self.calls.append('derive')
        return [ConditionSpec(statement='显示运行中的 Agent', obligation='REQUIRED', dimension='FUNCTIONAL', verification_method='实际查看运行状态')]
    async def challenge_conditions(self, text, conditions):
        self.calls.append('challenge')
        return ChallengeReport(findings=[ChallengeFinding(kind='completeness', target_condition='',
            finding='缺少可读性要求', recommendation='add_condition', replacement='状态信息可读', dimension='QUALITY')]
            if self.challenge_add else [])
    async def plan_search(self, text, conditions, gaps, previous):
        self.calls.append('plan')
        return SearchPlan(query=f'agent dashboard source {len(previous)}', rationale='查现成整体解')
    async def assess_resources(self, text, conditions, resources):
        self.calls.append('match')
        return [ResourceMatch(condition_id=c['id'], resource_id=r['resource_id'],
            status='VERIFIED', explanation='来源声明可显示运行状态，尚未环境验收',
            evidence_ids=[r['sources'][0]['evidence_id']] if r['sources'] else [],
            supporting_quote='invented claim' if self.hallucinate else 'Shows running agents',
            gaps=[]) for c in conditions for r in resources]
    async def draft_proposal(self, text, resources, matches):
        self.calls.append('propose')
        return ProposalDraft(title='复用现有 Agent 仪表盘', summary='复用来源支持的状态界面；仍需接口适配和环境验收。',
            recommendation_reason='真实来源支持显示状态', resource_ids=[resources[0]['id']],
            integration_work=['适配运行时接口'], new_work=['验收状态更新'], risks=['许可 UNKNOWN'])

class SearchFixture:
    search_reservation = read_reservation = 0.0
    def __init__(self, empty=False, fail=False):
        self.empty, self.fail = empty, fail
        self.searches = self.reads = 0
        self.entered = asyncio.Event()
        self.release: asyncio.Event | None = None
    async def search(self, query, num):
        self.searches += 1
        if self.fail: raise httpx.ConnectError('unavailable')
        return ([] if self.empty else [SearchResult(url='https://example.org/dashboard',
            title='Dashboard', text='Shows running agents. Source availability does not establish a license.')]), {'cost_dollars': 0.01}
    async def read_source(self, url):
        self.reads += 1
        self.entered.set()
        if self.release: await self.release.wait()
        return SearchResult(url=url, title='Dashboard', text='Shows running agents. No commercial license supplied.'), {'read_cost': 0.001}

@pytest.fixture
def runtime(monkeypatch):
    monkeypatch.setenv('GOALSIFT_MAX_ACTIONS', '40')
    monkeypatch.setenv('GOALSIFT_MAX_TOOL_CALLS', '20')
    monkeypatch.setenv('GOALSIFT_MAX_RUNTIME_SECONDS', '60')
    monkeypatch.setenv('GOALSIFT_BUDGET_USD', '1')
    repo = Repository()
    yield repo
    repo.close()

async def finish(ctrl, job_id):
    task = ctrl._runs.get(job_id)
    if task: await asyncio.wait_for(task, 3)

@pytest.mark.asyncio
async def test_production_pipeline_is_traceable_and_never_model_verified(runtime):
    model, search = ModelFixture(challenge_add=True), SearchFixture()
    ctrl = Controller(runtime, model, search)
    job = runtime.create_job('显示多个 Agent 的实时运行状态')
    assert await ctrl.start(job.id)
    await finish(ctrl, job.id)
    view = runtime.current_view(job.id)
    assert view['status'] == 'COMPLETED', view
    assert len(view['conditions']) == 2
    assert view['conditions'][1]['dimension'] == 'QUALITY'
    assert all(a['status'] == 'SUPPORTED' for a in view['assessments'])
    assert view['proposal']['uncovered_conditions'] == []
    assert view['resources'][0]['license_claim'] == 'UNKNOWN'
    assert view['budget_usage']['actions'] == len(model.calls) + search.searches + search.reads
    assert view['budget_usage']['known_cost_usd'] == pytest.approx(0.011)
    assert all(e['source_ref'] == 'https://example.org/dashboard' for e in view['evidence'])
    assert runtime.get_revision(job.id, 1)['status'] == 'COMPLETED'
    assert 'https://example.org/dashboard' in to_markdown(runtime, job.id)

@pytest.mark.asyncio
async def test_empty_search_is_honest_completed_without_fabricated_proposal(runtime):
    ctrl = Controller(runtime, ModelFixture(), SearchFixture(empty=True))
    job = runtime.create_job('研究可用资源')
    await ctrl.start(job.id); await finish(ctrl, job.id)
    view = runtime.current_view(job.id)
    assert view['status'] == 'COMPLETED'
    assert not view['resources'] and view['proposal'] is None
    assert 'propose' not in ctrl.llm.calls
    assert len(runtime.get_checkpoint(job.id, 1)['queries']) == 2

@pytest.mark.asyncio
async def test_hallucinated_quote_cannot_become_supported(runtime):
    ctrl = Controller(runtime, ModelFixture(hallucinate=True), SearchFixture())
    job = runtime.create_job('研究状态仪表盘')
    await ctrl.start(job.id); await finish(ctrl, job.id)
    view = runtime.current_view(job.id)
    assert view['status'] == 'COMPLETED'
    assert view['proposal'] is None
    assert all(a['status'] == 'UNKNOWN' for a in view['assessments'])
    assert all('invented claim' not in e['excerpt_or_summary'] for e in view['evidence'])

@pytest.mark.asyncio
async def test_decisive_ambiguity_then_answer_continues_same_revision(runtime):
    ctrl = Controller(runtime, ModelFixture(ambiguous=True), SearchFixture())
    job = runtime.create_job('做一个很好的产品')
    await ctrl.start(job.id); await finish(ctrl, job.id)
    assert runtime.get_job(job.id).status == JobStatus.NEEDS_INPUT
    assert ctrl.search.searches == 0
    assert await ctrl.answer_input(job.id, '做 Agent 管理网页，先假设 REST 接口')
    await finish(ctrl, job.id)
    assert runtime.get_job(job.id).status == JobStatus.COMPLETED
    assert ctrl.llm.calls.count('ambiguity') == 1
    assert runtime.current_view(job.id)['goal']['open_questions'] == []
    assert runtime.get_job(job.id).current_revision == 1

@pytest.mark.asyncio
async def test_pause_inflight_then_resume_skips_committed_stages(runtime):
    model, search = ModelFixture(), SearchFixture()
    search.release = asyncio.Event()
    ctrl = Controller(runtime, model, search)
    job = runtime.create_job('显示 Agent 状态')
    await ctrl.start(job.id)
    await asyncio.wait_for(search.entered.wait(), 2)
    assert ctrl.pause(job.id)
    assert not await ctrl.start(job.id)
    search.release.set()
    await finish(ctrl, job.id)
    assert runtime.get_job(job.id).status == JobStatus.PAUSED
    assert 'match' not in model.calls
    assert await ctrl.start(job.id)
    await finish(ctrl, job.id)
    assert runtime.get_job(job.id).status == JobStatus.COMPLETED
    assert model.calls.count('derive') == 1 and search.searches == 1 and search.reads == 1

@pytest.mark.asyncio
async def test_cancel_inflight_revokes_late_writes_and_is_terminal(runtime):
    search = SearchFixture(); search.release = asyncio.Event()
    ctrl = Controller(runtime, ModelFixture(), search)
    job = runtime.create_job('显示 Agent 状态')
    await ctrl.start(job.id); await asyncio.wait_for(search.entered.wait(), 2)
    before = len(runtime.list_evidence(job.id))
    assert ctrl.cancel(job.id)
    await finish(ctrl, job.id)
    assert runtime.get_job(job.id).status == JobStatus.CANCELLED
    assert len(runtime.list_evidence(job.id)) == before
    assert not await ctrl.start(job.id) and not ctrl.cancel(job.id)
    assert 'match' not in ctrl.llm.calls

@pytest.mark.asyncio
async def test_tool_failure_resumes_only_uncommitted_search(runtime):
    search = SearchFixture(fail=True)
    ctrl = Controller(runtime, ModelFixture(), search)
    job = runtime.create_job('显示 Agent 状态')
    await ctrl.start(job.id); await finish(ctrl, job.id)
    assert runtime.get_job(job.id).status == JobStatus.PARTIAL
    assert runtime.get_checkpoint(job.id, 1)['stage'] == 'search'
    search.fail = False
    assert await ctrl.start(job.id); await finish(ctrl, job.id)
    assert runtime.get_job(job.id).status == JobStatus.COMPLETED
    assert ctrl.llm.calls.count('derive') == 1
    assert search.searches == 2

@pytest.mark.asyncio
async def test_real_controller_budget_exhaustion_persists_across_resume(runtime, monkeypatch):
    monkeypatch.setenv('GOALSIFT_MAX_ACTIONS', '1')
    model, search = ModelFixture(), SearchFixture()
    ctrl = Controller(runtime, model, search)
    job = runtime.create_job('显示 Agent 状态')
    await ctrl.start(job.id); await finish(ctrl, job.id)
    assert runtime.get_job(job.id).status == JobStatus.PARTIAL
    assert model.calls == ['ambiguity'] and search.searches == 0
    await ctrl.start(job.id); await finish(ctrl, job.id)
    assert model.calls == ['ambiguity']
    monkeypatch.setenv('GOALSIFT_MAX_ACTIONS', '40')
    await ctrl.start(job.id); await finish(ctrl, job.id)
    assert runtime.get_job(job.id).status == JobStatus.COMPLETED
    assert model.calls.count('ambiguity') == 1

@pytest.mark.asyncio
async def test_refine_preserves_snapshot_reuses_sources_and_filters_current_export(runtime):
    model, search = ModelFixture(), SearchFixture()
    ctrl = Controller(runtime, model, search)
    job = runtime.create_job('显示 Agent 状态')
    await ctrl.start(job.id); await finish(ctrl, job.id)
    old = runtime.get_revision(job.id, 1)
    old_condition_ids = {c['id'] for c in old['conditions']}
    assert await ctrl.refine(job.id, '增加新要求')
    await finish(ctrl, job.id)
    current = to_json(runtime, job.id)
    assert current['status'] == 'COMPLETED', current
    assert current['revision'] == 2 and current['goal']['revision'] == 2
    assert old_condition_ids.isdisjoint(c['id'] for c in current['conditions'])
    assert all(a['revision_evaluated'] == 2 for a in current['assessments'])
    assert runtime.get_revision(job.id, 1) == old
    assert search.searches == 1 and search.reads == 1
    assert old['goal']['constraints'] != current['goal']['constraints']


def test_independent_connections_claim_exactly_one_owner(runtime):
    job = runtime.create_job('状态')
    other = Repository(runtime.db_path)
    with ThreadPoolExecutor(2) as pool:
        outcomes = list(pool.map(lambda pair: pair[0].claim_run(job.id, pair[1]),
                                 [(runtime, 'runner1'), (other, 'runner2')]))
    assert sorted(outcomes) == [False, True]
    other.close()


def test_nested_bundle_failure_rolls_back_checkpoint_and_objects(runtime):
    job = runtime.create_job('状态')
    with pytest.raises(RuntimeError):
        with runtime.transaction():
            runtime.save_checkpoint(job.id, 1, {'stage': 'search'})
            runtime.add_constraint(job.id, 'must not survive')
            raise RuntimeError('failed multi-object commit')
    assert runtime.get_checkpoint(job.id, 1) == {} and runtime.get_goal(job.id) is None


def test_api_exports_are_files_missing_jobs_and_cross_origin_fail(runtime):
    app = create_app(runtime, ModelFixture(), SearchFixture())
    with TestClient(app) as client:
        r = client.post('/api/jobs', json={'request': '研究仪表盘'})
        jid = r.json()['id']
        assert client.get(f'/api/jobs/{jid}').json()['status'] == 'CREATED'
        md = client.get(f'/api/jobs/{jid}/export')
        assert md.headers['content-type'].startswith('text/plain')
        assert 'attachment' in md.headers['content-disposition']
        assert client.get('/api/jobs/missing/export').status_code == 404
        assert client.post('/api/jobs', json={'request': 'x'}, headers={'Origin': 'https://evil.example'}).status_code == 403
        assert client.post(f'/api/jobs/{jid}/pause').status_code == 409
        assert client.get(f'/api/jobs/{jid}/export?fmt=invalid').status_code == 400
        assert client.get(f'/api/jobs/{jid}/revisions/99').status_code == 404


def test_event_cursor_is_exact_and_errors_are_redacted(runtime):
    from goalsift.models import ResearchEvent, new_id
    job = runtime.create_job('状态')
    runtime.append_event(ResearchEvent(id=new_id('e'), event_id=new_id('e'), job_id=job.id,
        revision=1, action_type='SEARCH', error='Bearer abcdefghijklmnop'))
    page = runtime.events_page(job.id)
    assert len(page) == 2 and page[0]['cursor'] < page[1]['cursor']
    assert len(runtime.events_page(job.id, page[0]['cursor'])) == 1
    assert 'abcdefghijklmnop' not in page[1]['error']

@pytest.mark.asyncio
async def test_restart_continues_inspect_checkpoint_without_rederiving(runtime):
    search = SearchFixture(); search.release = asyncio.Event()
    model = ModelFixture(); ctrl = Controller(runtime, model, search)
    job = runtime.create_job('显示 Agent 状态')
    await ctrl.start(job.id); await asyncio.wait_for(search.entered.wait(), 2)
    # Shutdown cannot resume an in-flight network request; the committed search survives.
    await ctrl.shutdown()
    runtime.set_job_status(job.id, 'RESEARCHING', active_run_id='orphan_after_crash')
    reopened = Repository(runtime.db_path)
    assert reopened.recover_orphans() == [job.id]
    continued_model, continued_search = ModelFixture(), SearchFixture()
    continued = Controller(reopened, continued_model, continued_search)
    await continued.start(job.id); await finish(continued, job.id)
    assert reopened.get_job(job.id).status == JobStatus.COMPLETED
    assert not {'define', 'derive', 'challenge', 'plan'} & set(continued_model.calls)
    assert continued_search.searches == 0 and continued_search.reads == 1
    reopened.close()

@pytest.mark.asyncio
async def test_model_error_does_not_skip_delivery_gate(runtime):
    model = ModelFixture()
    async def fail_challenge(*args): raise ValueError('invalid structured output')
    model.challenge_conditions = fail_challenge
    ctrl = Controller(runtime, model, SearchFixture())
    job = runtime.create_job('显示 Agent 状态')
    await ctrl.start(job.id); await finish(ctrl, job.id)
    assert runtime.get_job(job.id).status == JobStatus.FAILED
    assert runtime.get_checkpoint(job.id, 1)['stage'] == 'challenge'
    assert ctrl.search.searches == 0 and runtime.get_proposal(job.id) is None

@pytest.mark.asyncio
async def test_read_failure_keeps_source_supported_research_with_visible_limit(runtime):
    model, search = ModelFixture(), SearchFixture()
    async def fail_read(*args): raise httpx.ConnectError('source unavailable')
    search.read_source = fail_read
    ctrl = Controller(runtime, model, search)
    job = runtime.create_job('显示 Agent 状态')
    await ctrl.start(job.id); await finish(ctrl, job.id)
    view = runtime.current_view(job.id)
    assert view['status'] == 'COMPLETED'
    assert any('全文读取失败' in note for note in view['delivery_notes'])
    assert view['evidence'] and all(e['collection_method'] == 'exa /search' for e in view['evidence'])


def test_supported_without_source_and_conflicted_without_conflict_rejected():
    from goalsift.models import Assessment, AssessmentStatus
    from goalsift.validators import validate_assessment_status, validate_conflict_handling
    a = Assessment(id='a', job_id='j', condition_id='c', status=AssessmentStatus.SUPPORTED)
    assert validate_assessment_status(a, [])
    a.status = AssessmentStatus.CONFLICTED
    assert validate_conflict_handling([a], [])


def test_cost_reservation_blocks_before_service_and_unknown_is_not_zero():
    from goalsift.budget import BudgetGuard, BudgetConfig, BudgetExhausted
    guard = BudgetGuard(BudgetConfig(budget_usd=0.02))
    with pytest.raises(BudgetExhausted): guard.check(reserve_usd=0.021)
    assert guard.usage.actions == 0
    guard = BudgetGuard(BudgetConfig(budget_usd=1))
    guard.record({'cost_usd': None, 'input_tokens': 3})
    assert guard.usage.snapshot()['cost_usd'] is None
    with pytest.raises(BudgetExhausted): guard.check()

def test_invalid_price_overrides_cannot_bypass_preflight_budget(monkeypatch):
    from goalsift.llm_adapter import LLMAdapter
    adapter = LLMAdapter()
    for inp, out in [('-1', '1'), ('nan', '1'), ('1', 'inf'), ('1', '')]:
        monkeypatch.setenv('GOALSIFT_LLM_INPUT_USD_PER_MILLION', inp)
        monkeypatch.setenv('GOALSIFT_LLM_OUTPUT_USD_PER_MILLION', out)
        with pytest.raises(ValueError): adapter.reservation(50000, 5000)
    monkeypatch.setenv('GOALSIFT_LLM_INPUT_USD_PER_MILLION', '0.3')
    monkeypatch.setenv('GOALSIFT_LLM_OUTPUT_USD_PER_MILLION', '1.2')
    assert adapter.reservation(50000, 5000) == pytest.approx(0.021)

@pytest.mark.asyncio
async def test_real_search_adapter_refuses_private_url_before_exa(monkeypatch):
    from goalsift.search_adapter import SearchAdapter
    adapter = SearchAdapter()
    calls = []
    async def unexpected(*args): calls.append(args); return {}
    monkeypatch.setattr(adapter, '_post', unexpected)
    for url in ('http://127.0.0.1:8000', 'http://169.254.169.254/meta', 'file:///etc/passwd', 'javascript:alert(1)'):
        with pytest.raises(ValueError): await adapter.read_source(url)
    assert calls == []

@pytest.mark.asyncio
async def test_provider_usage_crosses_timeout_task_boundary(runtime, monkeypatch):
    from goalsift.llm_adapter import LLMAdapter
    monkeypatch.setenv('GOALSIFT_MAX_ACTIONS', '1')
    class UsageModel(LLMAdapter):
        async def check_ambiguity(self, text):
            self._usage.set({'input_tokens': 100, 'output_tokens': 5, 'model_requests': 1, 'cost_usd': 0.00013})
            return AmbiguityCheck(is_decisively_ambiguous=False)
    model = UsageModel()
    model.key = 'test-key'
    model.model_name = 'deepseek-flash'
    ctrl = Controller(runtime, model, SearchFixture())
    job = runtime.create_job('状态')
    await ctrl.start(job.id); await finish(ctrl, job.id)
    usage = runtime.get_job(job.id).budget_usage
    assert usage['input_tokens'] == 100 and usage['output_tokens'] == 5
    assert usage['model_requests'] == 1 and not usage['cost_unknown']
    assert usage['cost_usd'] == pytest.approx(0.00013)


def test_shared_connection_serializes_readers_writers_and_views(runtime):
    from concurrent.futures import ThreadPoolExecutor
    from goalsift.models import ResearchEvent, new_id
    repo = runtime
    job = repo.create_job('concurrent readers and writer')
    def worker(index):
        for step in range(100):
            if index % 2:
                repo.append_event(ResearchEvent(id=new_id('ev'), event_id=new_id('ev'),
                    job_id=job.id, revision=1, action_type='REASON', status='CHECK'))
            else:
                assert repo.current_view(job.id)['id'] == job.id
                repo.list_jobs()
                repo.events_page(job.id)
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(worker, range(8)))
    assert len(repo.events_page(job.id)) == 401

@pytest.mark.asyncio
async def test_exa_fake_ip_dns_requires_confirmed_public_resolution(monkeypatch):
    from goalsift.search_adapter import SearchAdapter
    import socket
    adapter = SearchAdapter()
    monkeypatch.setattr(socket, 'getaddrinfo', lambda *a: [(2, 1, 6, '', ('198.18.0.102', 0))])
    calls = []
    async def public(host): calls.append(host); return ['140.82.112.4']
    monkeypatch.setattr(adapter, '_public_dns', public)
    assert await adapter._public('https://github.com/example')
    assert calls == ['github.com']
    async def private(host): return ['127.0.0.1']
    monkeypatch.setattr(adapter, '_public_dns', private)
    assert not await adapter._public('https://evil.example')
    monkeypatch.setattr(socket, 'getaddrinfo', lambda *a: [(2, 1, 6, '', ('192.168.1.2', 0))])
    assert not await adapter._public('https://private.example')
    assert not await adapter._public('http://127.0.0.1')
    assert not await adapter._public('https://user:pass@github.com')
    assert not await adapter._public('https://github.com:8080')

@pytest.mark.asyncio
async def test_invalid_budget_configuration_finishes_failed_instead_of_orphan(runtime, monkeypatch):
    monkeypatch.setenv('GOALSIFT_MAX_ACTIONS', '0')
    ctrl = Controller(runtime, ModelFixture(), SearchFixture())
    job = runtime.create_job('configuration error')
    assert await ctrl.start(job.id)
    await finish(ctrl, job.id)
    assert runtime.get_job(job.id).status == JobStatus.FAILED
    assert runtime.get_job(job.id).active_run_id is None

@pytest.mark.asyncio
async def test_conflicting_exact_quotes_remain_conflicted(runtime):
    class ConflictModel(ModelFixture):
        async def assess_resources(self, text, conditions, resources):
            return [ResourceMatch(condition_id=c['id'], resource_id=r['resource_id'], status='CONFLICTED',
                explanation='Two exact source claims disagree', evidence_ids=[r['sources'][0]['evidence_id']],
                supporting_quote='Shows running agents', refuting_quote='Does not show running agents',
                refuting_evidence_ids=[r['sources'][0]['evidence_id']]) for c in conditions for r in resources]
    class ConflictSearch(SearchFixture):
        async def search(self, query, num):
            return [SearchResult(url='https://example.org/dashboard', title='Dashboard',
                text='Shows running agents. Does not show running agents.')], {'cost_dollars':0.01}
        async def read_source(self, url):
            return SearchResult(url=url,title='Dashboard',text='Shows running agents. Does not show running agents.'), {'read_cost':0.001}
    ctrl = Controller(runtime, ConflictModel(), ConflictSearch())
    job = runtime.create_job('Display agents')
    assert await ctrl.start(job.id)
    await finish(ctrl,job.id)
    view = runtime.current_view(job.id)
    assert view['assessments'][0]['status'] == 'CONFLICTED'
    assert view['proposal'] is None

@pytest.mark.asyncio
async def test_match_checkpoint_skips_already_received_batches_on_resume(runtime):
    class TwoResources(SearchFixture):
        async def search(self, query, num):
            hits, meta = await super().search(query,num)
            hits.append(SearchResult(url='https://example.org/other',title='Other',text='Shows running agents'))
            return hits,meta
    model, search = ModelFixture(), TwoResources()
    original = model.assess_resources
    ctrl = Controller(runtime,model,search)
    async def match(*args):
        result = await original(*args)
        ctrl._pause_requests.add(job.id)
        return result
    model.assess_resources = match
    job = runtime.create_job('Display agents')
    assert await ctrl.start(job.id)
    await finish(ctrl,job.id)
    assert runtime.get_job(job.id).status == JobStatus.PAUSED
    assert runtime.get_checkpoint(job.id,1)['pending_matches']
    count = model.calls.count('match')
    model.assess_resources = original
    assert await ctrl.start(job.id)
    await finish(ctrl,job.id)
    assert runtime.get_job(job.id).status == JobStatus.COMPLETED
    assert model.calls.count('match') == count + 1


def test_condition_cycles_and_uncovered_references_are_rejected():
    from goalsift.models import Condition
    from goalsift.validators import validate_references
    a=Condition(id='a',job_id='j',statement='A',origin='user',obligation='REQUIRED',dimension='FUNCTIONAL',relations=[{'type':'REQUIRES','target_ids':['b']}])
    b=Condition(id='b',job_id='j',statement='B',origin='user',obligation='REQUIRED',dimension='FUNCTIONAL',relations=[{'type':'ALL_OF','target_ids':['a']}])
    errors=validate_references(job_id='j',conditions=[a,b],resources=[],capabilities=[],evidence=[],assessments=[],proposals=[])
    assert any('cycle' in e for e in errors)
