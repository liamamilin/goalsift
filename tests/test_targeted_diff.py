"""Real isolated API/Controller/SQLite; provider fixtures never use the network."""
import asyncio
import copy
import runpy
import sqlite3
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from goalsift.app import create_app
from goalsift.controller import Controller
from goalsift.goal_review import GoalReview
from goalsift.llm_adapter import ConditionSpec, ResourceMatch
from goalsift.models import Condition, Resource, Assessment, Capability
from goalsift.repository import Repository
from goalsift.revision_diff import compare_revisions
from goalsift.search_adapter import SearchResult
from goalsift.targeted_research import TargetedResearch
from goalsift.budget import BudgetExhausted

fixtures = runpy.run_path(str(Path(__file__).with_name('test_runtime_integration.py')))
ModelFixture, SearchFixture, finish = (fixtures[k] for k in ('ModelFixture', 'SearchFixture', 'finish'))


class ScopeModel(ModelFixture):
    def __init__(self):
        super().__init__()
        self.scopes, self.plans = [], []
    async def derive_conditions(self, text):
        self.calls.append('derive')
        return [ConditionSpec(statement=s, obligation='REQUIRED', dimension='FUNCTIONAL')
                for s in ('显示运行状态', '启动暂停接口', '本地部署')]
    async def plan_search(self, text, conditions, gaps, previous):
        self.plans.append((text, conditions))
        return await super().plan_search(text, conditions, gaps, previous)
    async def assess_resources(self, text, conditions, resources):
        self.calls.append('match')
        self.scopes += [(r['resource_id'], [c['statement'] for c in conditions]) for r in resources]
        result = []
        for r in resources:
            for c in conditions:
                quote = 'Pause agent' if c['statement'] == '启动暂停接口' else 'Shows running agents'
                doc = next((s for s in r['sources'] if quote in s['text']), None)
                result.append(ResourceMatch(condition_id=c['id'], resource_id=r['resource_id'],
                    status='SUPPORTED' if doc else 'UNKNOWN', explanation=quote if doc else '接口依据未知',
                    evidence_ids=[doc['evidence_id']] if doc else [], supporting_quote=quote if doc else ''))
        return result


class ScopeSearch(SearchFixture):
    def __init__(self):
        super().__init__()
        self.deep_reads = 0
    async def search(self, query, num):
        self.searches += 1
        return [SearchResult(url='https://github.com/acme/dash', title='Dash', text='Shows running agents'),
                SearchResult(url='https://example.org/dashboard', title='Other', text='Shows running agents')], {'cost_dollars': 0.001}
    async def read_repository(self, url):
        self.deep_reads += 1
        return [SearchResult(url='https://github.com/acme/dash/blob/main/README.md', title='README',
            text='Shows running agents' + ('\nPause agent' if self.deep_reads > 1 else ''),
            version=f'sha-{self.deep_reads}', category='接口与使用说明', collection_method='github public API')], {'read_cost': 0, 'notes': []}


@pytest.fixture
def repo(isolated_data_root, monkeypatch):
    for name, value in {'MAX_ACTIONS': '40', 'MAX_RUNTIME_SECONDS': '60', 'BUDGET_USD': '0.2'}.items():
        monkeypatch.setenv('GOALSIFT_' + name, value)
    r = Repository()
    assert Path(r._conn.execute('PRAGMA database_list').fetchone()['file']).is_relative_to(isolated_data_root)
    yield r
    r.close()


async def completed(repo, search=None):
    model, search = ScopeModel(), search or ScopeSearch()
    ctrl = Controller(repo, model, search)
    job = repo.create_job('显示运行状态、启动暂停和本地部署')
    await ctrl.start(job.id)
    await finish(ctrl, job.id)
    view = repo.current_view(job.id)
    assert view['status'] == 'COMPLETED', view
    return ctrl, job.id, view


def request(view, restricted=False, budget=0.1):
    cid = next(c['id'] for c in view['conditions'] if c['statement'] == '启动暂停接口')
    rid = next(r['id'] for r in view['resources'] if r['name'] == 'Dash')
    return TargetedResearch(expected_revision=view['revision'], condition_ids=[cid],
        resource_ids=[rid] if restricted else [], budget_usd=budget, question='核查启动暂停接口')


@pytest.mark.asyncio
@pytest.mark.parametrize('restricted', [True, False])
async def test_targeted_scope_reuses_unaffected_judgments_and_refresh_invalidates_resource(repo, restricted):
    ctrl, jid, before = await completed(repo)
    old_snapshot = repo.get_revision(jid, 1)
    ctrl.llm.calls.clear(); ctrl.llm.scopes.clear(); ctrl.llm.plans.clear()
    assert await ctrl.investigate(jid, request(before, restricted))
    await finish(ctrl, jid)
    after = repo.current_view(jid)
    assert after['status'] == 'COMPLETED', after
    assert after['goal']['purpose'] == before['goal']['purpose']
    assert [c['statement'] for c in after['conditions']] == [c['statement'] for c in before['conditions']]
    assert 'derive' not in ctrl.llm.calls and 'challenge' not in ctrl.llm.calls and 'define' not in ctrl.llm.calls
    assert all([c['statement'] for c in p[1]] == ['启动暂停接口'] for p in ctrl.llm.plans)
    a, b = (next(r['id'] for r in after['resources'] if r['name'] == name) for name in ('Dash', 'Other'))
    assert next(scope for rid, scope in ctrl.llm.scopes if rid == a) == ['显示运行状态', '启动暂停接口', '本地部署']
    if restricted: assert all(rid == a for rid, scope in ctrl.llm.scopes)
    else: assert next(scope for rid, scope in ctrl.llm.scopes if rid == b) == ['启动暂停接口']
    assert len(after['reused_assessment_ids']) == (3 if restricted else 2)
    assert after['budget_config']['budget_usd'] == 0.1
    assert len(after['assessments']) == 6 and all(a['status'] != 'VERIFIED' for a in after['assessments'])
    assert repo.get_revision(jid, 1) == old_snapshot
    diff = compare_revisions(old_snapshot, after)
    assert diff['conditions']['unchanged'] == 3 and not diff['conditions']['changed']
    assert diff['summary']['changed_sources'] == 1
    assert any(a['before'] == ['UNKNOWN'] and a['after'] == ['SUPPORTED'] for a in diff['assessment_changes'])
    assert diff['newly_covered'] == ['启动暂停接口']


@pytest.mark.asyncio
async def test_targeted_invalid_refs_stale_requests_concurrent_and_budget_do_not_mutate(repo):
    ctrl, jid, before = await completed(repo)
    for edits in ({'condition_ids':['foreign']}, {'resource_ids':['foreign']}, {'budget_usd':0.3}):
        with pytest.raises(ValueError): await ctrl.investigate(jid, request(before).model_copy(update=edits))
        assert repo.current_view(jid) == before
    outcomes = await asyncio.gather(ctrl.investigate(jid, request(before)), ctrl.investigate(jid, request(before)))
    assert outcomes == [True, False]
    await finish(ctrl, jid)
    assert not await ctrl.investigate(jid, request(before))
    assert repo.get_job(jid).current_revision == 2


@pytest.mark.asyncio
async def test_targeted_budget_stops_before_paid_search_and_survives_resume(repo, monkeypatch):
    ctrl, jid, before = await completed(repo)
    ctrl.search.search_reservation = 0.01
    initial_searches = ctrl.search.searches
    assert await ctrl.investigate(jid, request(before, budget=0.001))
    await finish(ctrl, jid)
    view = repo.current_view(jid)
    assert view['status'] == 'PARTIAL' and 'budget' in view['stopped_reason']
    assert ctrl.search.searches == initial_searches
    monkeypatch.setenv('GOALSIFT_BUDGET_USD', '1')
    assert await ctrl.start(jid)
    await finish(ctrl, jid)
    assert repo.current_view(jid)['budget_config']['budget_usd'] == 0.001
    assert ctrl.search.searches == initial_searches


@pytest.mark.asyncio
async def test_targeted_pause_restart_and_cancel_preserve_owned_checkpoints(repo):
    ctrl, jid, before = await completed(repo)
    search = ctrl.search
    original = search.read_repository
    entered, release = asyncio.Event(), asyncio.Event()
    async def blocked(url):
        entered.set(); await release.wait(); return await original(url)
    search.read_repository = blocked
    assert await ctrl.investigate(jid, request(before, restricted=True))
    await entered.wait()
    assert ctrl.pause(jid)
    release.set(); await finish(ctrl, jid)
    assert repo.get_job(jid).status.value == 'PAUSED'
    search.read_repository = original
    resumed = Controller(repo, ctrl.llm, search)
    assert await resumed.start(jid)
    await finish(resumed, jid)
    assert repo.get_job(jid).status.value == 'COMPLETED'
    assert search.deep_reads == 2
    entered.clear(); release.clear(); search.read_repository = blocked
    before_cancel = repo.current_view(jid)
    assert await resumed.investigate(jid, request(before_cancel, restricted=True))
    await entered.wait()
    evidence_ids = {e.id for e in repo.list_evidence(jid)}
    assert resumed.cancel(jid)
    release.set(); await finish(resumed, jid)
    assert repo.get_job(jid).status.value == 'CANCELLED'
    assert {e.id for e in repo.list_evidence(jid)} == evidence_ids


@pytest.mark.asyncio
async def test_targeted_limits_new_candidates_even_when_original_catalog_is_full(repo):
    ctrl, jid, before = await completed(repo)
    state = repo.get_checkpoint(jid, 1)
    for index in range(6):
        r = Resource(id=f'existing-{index}', job_id=jid, name=f'Existing {index}', kind='web_resource', canonical_source=f'https://example.net/{index}')
        repo.save_resource(r); state['resource_ids'].append(r.id); state['inspected_ids'].append(r.id)
    repo.save_checkpoint(jid, 1, state)
    before = repo.current_view(jid)
    async def many(query, num):
        return [SearchResult(url=f'https://new.example/{i}', title=f'New {i}', text='Shows running agents') for i in range(6)], {'cost_dollars': 0.001}
    ctrl.search.search = many
    assert await ctrl.investigate(jid, request(before))
    await finish(ctrl, jid)
    view = repo.current_view(jid)
    assert view['status'] == 'COMPLETED', view
    assert len(view['resources']) == 10
    assert len([r for r in view['resources'] if r['name'].startswith('New')]) == 2


@pytest.mark.asyncio
async def test_review_lineage_diff_and_legacy_schema_columns_remain_writable(repo):
    ctrl, jid, before = await completed(repo)
    cid = before['conditions'][0]['id']
    assert await ctrl.review_goal(jid, GoalReview(expected_revision=1, conditions=[{'condition_id':cid, 'action':'update', 'statement':'状态清晰可读', 'dimension':'QUALITY'}]))
    await finish(ctrl, jid)
    after = repo.current_view(jid)
    diff = compare_revisions(before, after)
    assert len(diff['conditions']['changed']) == 1 and not diff['conditions']['added'] and not diff['conditions']['removed']
    assert diff['conditions']['changed'][0]['before']['id'] == cid
    path = repo.db_path
    old_snapshot = repo.get_revision(jid, 1)
    repo.close()
    with sqlite3.connect(path) as connection:
        connection.execute('ALTER TABLE conditions DROP COLUMN lineage_id')
    migrated = Repository(path)
    condition = migrated.list_conditions(jid)[0]
    assert condition.lineage_id is None
    condition.lineage_id = condition.id
    migrated.save_condition(condition)
    assert migrated.list_conditions(jid)[0].lineage_id == condition.id
    assert migrated.get_revision(jid, 1) == old_snapshot
    migrated.close()


def test_compare_legacy_does_not_match_distinct_languages_or_claim_removed_conditions_improved():
    before = {'id':'j','revision':1,'status':'COMPLETED','conditions':[{'id':'cpp','statement':'C++','obligation':'REQUIRED','dimension':'FUNCTIONAL'}, {'id':'sharp','statement':'C#','obligation':'REQUIRED','dimension':'FUNCTIONAL'}], 'resources':[], 'evidence':[], 'assessments':[], 'proposal':{'condition_coverage':['cpp']}}
    after = copy.deepcopy(before); after.update(revision=2, conditions=[{'id':'new','statement':'C#','obligation':'REQUIRED','dimension':'QUALITY'}], proposal={'condition_coverage':[]})
    diff = compare_revisions(before, after)
    assert [c['statement'] for c in diff['conditions']['removed']] == ['C++']
    assert len(diff['conditions']['changed']) == 1
    assert not diff['newly_covered'] and not diff['newly_uncovered']
    assert diff['usage']['before'] == {}  # missing cost stays unknown in the UI


def test_targeted_api_schema_state_origins_and_comparison_read_only(repo):
    app = create_app(repo, ScopeModel(), ScopeSearch())
    with TestClient(app) as client:
        jid = client.post('/api/jobs', json={'request':'显示状态'}).json()['id']
        payload = {'expected_revision':1,'condition_ids':['foreign'],'budget_usd':0.1}
        assert client.post(f'/api/jobs/{jid}/investigate', json=payload).status_code == 409
        assert client.post(f'/api/jobs/{jid}/investigate', json=payload, headers={'Origin':'https://evil.example'}).status_code == 403
        for bad in ({'condition_ids':[]}, {'condition_ids':['c','c']}, {'budget_usd':0}, {'budget_usd':1.01}, {'resource_ids':['a','b','c']}, {'unknown':True}):
            assert client.post(f'/api/jobs/{jid}/investigate', json={**payload, **bad}).status_code == 422
        assert client.get(f'/api/jobs/{jid}/compare?base=1').status_code == 404
        with pytest.raises(ValidationError): TargetedResearch(**{**payload,'budget_usd':float('nan')})


def test_api_submitted_scope_and_snapshot_comparison_use_same_saved_revision(repo):
    ctrl, jid, before = asyncio.run(completed(repo))
    payload = request(before, restricted=True).model_dump(mode='json')
    with TestClient(create_app(repo, ctrl.llm, ctrl.search)) as client:
        assert client.post(f'/api/jobs/{jid}/investigate', json=payload).status_code == 200
        for _ in range(40):
            after = client.get(f'/api/jobs/{jid}').json()
            if after['status'] != 'RESEARCHING': break
        assert after['status'] == 'COMPLETED'
        current = client.get(f'/api/jobs/{jid}/compare?base=1').json()
        saved = client.get(f'/api/jobs/{jid}/compare?base=1&target=2').json()
        assert current == saved
        assert current['summary']['reused_assessments'] == 3
        assert client.get(f'/api/jobs/{jid}/compare?base=2').status_code == 400
        assert client.get(f'/api/jobs/{jid}/compare?base=1&target=999').status_code == 404
        assert client.post(f'/api/jobs/{jid}/investigate', json=payload).status_code == 409
        assert client.get(f'/api/jobs/{jid}/revisions/1').json() == before
        assert client.get(f'/api/jobs/{jid}/export?fmt=json').json()['research_scope'] == after['research_scope']
        assert '本轮定向补查' in client.get(f'/api/jobs/{jid}/export?fmt=markdown').text


@pytest.mark.asyncio
async def test_new_source_invalidates_carried_judgments_before_blocked_rematch(repo):
    ctrl, jid, before = await completed(repo)
    old_snapshot = repo.get_revision(jid, 1)
    # Use an actual GitHub alias so identity is deterministic and resource-bound.
    other = next(r for r in repo.list_resources(jid) if r.name == 'Other')
    other.canonical_source = 'https://github.com/acme/other'
    repo.save_resource(other)
    async def alias(query, num):
        return [SearchResult(url='https://github.com/acme/other/blob/main/API.md', title='API', text='New opposing documentation')], {'cost_dollars':0.001}
    ctrl.search = SearchFixture()  # no direct GitHub reader; cached judgments are carried first
    ctrl.search.search = alias
    model_original = ctrl.llm.assess_resources
    async def interrupted(text, conditions, resources):
        if 'New opposing documentation' in str(resources): raise BudgetExhausted('budget exhausted: fixture interruption after source commit')
        return await model_original(text, conditions, resources)
    ctrl.llm.assess_resources = interrupted
    assert await ctrl.investigate(jid, request(repo.current_view(jid)))
    await finish(ctrl, jid)
    after = repo.current_view(jid)
    assert after['status'] == 'PARTIAL'
    assert not any(other.id in a['resource_ids'] for a in after['assessments'])
    assert len(after['reused_assessment_ids']) == 2  # only the other candidate's unrelated judgments survive
    assert any(e['excerpt_or_summary'] == 'New opposing documentation' for e in after['evidence'])
    assert repo.get_revision(jid, 1) == old_snapshot


@pytest.mark.asyncio
async def test_legacy_alias_candidate_ids_are_canonicalized_without_dangling_reused_refs(repo):
    ctrl, jid, before = await completed(repo)
    source = next(r for r in repo.list_resources(jid) if r.name == 'Dash')
    alias = source.model_copy(update={'id':'alias', 'canonical_source':'https://github.com/acme/dash/blob/main/README.md'})
    repo.save_resource(alias)
    state = repo.get_checkpoint(jid, 1); state['resource_ids'].append(alias.id)
    repo.save_checkpoint(jid, 1, state)
    for a in repo.list_assessments(jid):
        if source.id in a.resource_ids:
            repo.save_assessment(a.model_copy(update={'id':'alias-'+a.id, 'resource_ids':[alias.id]}))
    original = repo.get_revision(jid, 1)
    body = request(repo.current_view(jid)).model_copy(update={'resource_ids':[alias.id]})
    assert await ctrl.investigate(jid, body)
    await finish(ctrl, jid)
    after = repo.current_view(jid)
    assert after['status'] == 'COMPLETED', after
    assert len(after['resources']) == 2 and len(after['assessments']) == 6
    assert all('alias' not in a['resource_ids'] for a in after['assessments'])
    assert repo.get_revision(jid, 1) == original
