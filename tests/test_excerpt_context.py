"""Actual saved sources and isolated Controller; no provider calls."""
import json
import base64
import httpx
from pathlib import Path
import pytest
from goalsift.budget import BudgetExhausted
from goalsift.controller import Controller
from goalsift.exporter import to_markdown
from goalsift.llm_adapter import ResourceMatch
from goalsift.models import Evidence
from goalsift.repository import Repository
from goalsift.search_adapter import SearchResult
from goalsift.source_research import focused_excerpt, locate_quote, select_excerpt
from tests.test_runtime_integration import ModelFixture, SearchFixture, finish


def source(text, eid='source'):
    return Evidence(id=eid, job_id='job', claim='Read receipt', source_type='OFFICIAL_DOC',
                    source_ref='https://example.org/doc', locator='Document',
                    excerpt_or_summary=text, collection_method='fixture')


def test_actual_live_readme_clue_previously_omitted_is_now_available():
    path = Path(__file__).resolve().parents[1] / 'acceptance/2026-10-11/targeted-diff/live-after.json'
    view = json.loads(path.read_text())
    receipts = [e for e in view['evidence'] if e['stance'] == 'CONTEXT'
        and e['source_ref'].endswith('/README.md') and 'builderz-labs' in e['source_ref']
        and e['locator'].startswith('深度文档')]
    e = Evidence.model_validate(max(receipts, key=lambda e: e['retrieved_at']))
    quote = 'live activity, fleet status per runtime, and the task pipeline'
    old = select_excerpt(e.excerpt_or_summary)
    new = select_excerpt(e.excerpt_or_summary, '展示 Agent 运行状态、空闲与异常')
    assert quote not in old['text'] and quote in new['text']
    assert locate_quote(quote, [e], [e])[0] is e  # Previous guard searched the full saved source.
    assert locate_quote(quote, [e], [e], {e.id: old['excerpt_ranges']}) == (None, '')
    assert locate_quote(quote, [e], [e], {e.id: new['excerpt_ranges']}) == (e, quote)
    assert len(new['text']) <= 2400 and new['is_partial']
    assert all(e.excerpt_or_summary[a:b] in new['text'] for a, b in new['excerpt_ranges'])


def test_short_and_irrelevant_sources_remain_literal_and_bounded():
    short = 'Permission is hereby granted, free of charge.'
    assert select_excerpt(short, '许可')['text'] == short
    long = 'Intro.\n' + 'z' * 4000 + '\n## Installation\nUse npm install.\n' + 'z' * 3000
    assert select_excerpt(long, '与软件无关的内容')['text'] == focused_excerpt(long)
    assert 'Use npm install.' in focused_excerpt(long)
    assert len(focused_excerpt(long)) < 2400


def test_english_question_selects_chinese_status_passage_without_word_boundary_loss():
    text = '说明\n' + '无关资料。'*1000 + '\n运行状态：空闲或异常。\n' + '无关资料。'*800
    result = select_excerpt(text, 'Agent status idle error')
    assert '运行状态：空闲或异常。' in result['text']
    assert len(result['text']) <= 2400


def test_quote_must_fit_one_supplied_span_and_repeated_quote_uses_visible_occurrence():
    text = 'same phrase\nHIDDEN\nsame phrase\nalpha beta'
    e = source(text)
    start = text.rindex('same phrase')
    assert locate_quote('same phrase', [e], [e], {e.id: [[start, start+11]]}) == (e, 'same phrase')
    alpha = text.index('alpha')
    assert locate_quote('alpha beta', [e], [e], {e.id: [[alpha, alpha+5], [alpha+6, len(text)]]}) == (None, '')
    assert locate_quote('HIDDEN', [e], [e], {}) == (None, '')
    other = source(text, 'other')
    assert locate_quote('same phrase', [], [e, other], {e.id: [[start, start+11]], other.id: [[start,start+11]]}) == (None, '')


@pytest.fixture
def repo(isolated_data_root, monkeypatch):
    monkeypatch.setenv('GOALSIFT_MAX_ACTIONS', '40')
    monkeypatch.setenv('GOALSIFT_MAX_RUNTIME_SECONDS', '60')
    monkeypatch.setenv('GOALSIFT_BUDGET_USD', '1')
    r = Repository()
    assert Path(r._conn.execute('PRAGMA database_list').fetchone()['file']).is_relative_to(isolated_data_root)
    yield r
    r.close()


class LongSearch(SearchFixture):
    def __init__(self, relevant=False, two=False):
        super().__init__()
        self.relevant, self.two = relevant, two
    async def search(self, query, num):
        self.searches += 1
        return [SearchResult(url=f'https://example.org/{name}', title=name, text=self.body(name))
            for name in (['FIRST','SECOND'] if self.two else ['FIRST'])], {'cost_dollars': 0}
    def body(self, name):
        quote = 'Agent status: running, idle, error.' if self.relevant else 'Exotic unsupported claim.'
        return name + '\nShows running agents.\n' + 'z' * 3200 + '\n' + quote + '\n' + 'z' * 2200
    async def read_source(self, url):
        name = url.rsplit('/', 1)[-1]
        return SearchResult(url=url, title=name, text=self.body(name)), {'read_cost': 0}


class QuoteModel(ModelFixture):
    def __init__(self, status='SUPPORTED', relevant=False, interrupt=False):
        super().__init__()
        self.status, self.relevant, self.interrupt = status, relevant, interrupt
        self.received = []
    async def assess_resources(self, text, conditions, resources):
        item = resources[0]
        self.received.append(item)
        if self.interrupt and len(self.received) == 2: raise BudgetExhausted('fixture interrupted after first saved match')
        quote = 'Agent status: running, idle, error.' if self.relevant else 'Exotic unsupported claim.'
        return [ResourceMatch(condition_id=c['id'], resource_id=item['resource_id'], status=self.status,
            explanation='Fixture judgment', evidence_ids=[item['sources'][0]['evidence_id']],
            supporting_quote='Shows running agents.' if self.status == 'CONFLICTED' else quote,
            refuting_quote=quote if self.status == 'CONFLICTED' else '',
            refuting_evidence_ids=[item['sources'][0]['evidence_id']] if self.status == 'CONFLICTED' else []) for c in conditions]


@pytest.mark.asyncio
@pytest.mark.parametrize('status', ['SUPPORTED', 'NOT_SATISFIED', 'CONFLICTED'])
async def test_actual_controller_rejects_held_out_quotes_for_support_refutation_and_conflict(repo, status):
    model = QuoteModel(status=status)
    ctrl = Controller(repo, model, LongSearch())
    job = repo.create_job('显示运行状态')
    await ctrl.start(job.id); await finish(ctrl, job.id)
    view = repo.current_view(job.id)
    assert view['status'] == 'COMPLETED'
    assert all(a['status'] == 'UNKNOWN' for a in view['assessments'])
    assert all('Exotic unsupported claim.' not in s['text'] for item in model.received for s in item['sources'])
    assert not any(e['stance'] in ('SUPPORTS', 'REFUTES') for e in view['evidence'])


@pytest.mark.asyncio
async def test_relevant_tail_is_supplied_and_successful_match_context_is_exported(repo):
    model = QuoteModel(relevant=True)
    ctrl = Controller(repo, model, LongSearch(relevant=True))
    job = repo.create_job('显示运行状态')
    await ctrl.start(job.id); await finish(ctrl, job.id)
    view = repo.current_view(job.id)
    assert view['status'] == 'COMPLETED'
    assert view['assessments'][0]['status'] == 'SUPPORTED'
    assert any('Agent status: running, idle, error.' in s['text'] for item in model.received for s in item['sources'])
    contexts = [s for review in view['source_reviews'].values() for s in review['match_context']]
    assert contexts and all(s['is_partial'] and s['supplied_characters'] < s['stored_characters'] for s in contexts)
    evidence = {e['id']: e for e in view['evidence']}
    for e in evidence.values():
        if e['locator'].startswith('exact source quote: '):
            receipt = evidence[e['locator'].removeprefix('exact source quote: ')]
            assert e['retrieved_at'] == receipt['retrieved_at'] and e['source_version'] == receipt['source_version']
    assert '实际提供' in to_markdown(repo, job.id)


@pytest.mark.asyncio
@pytest.mark.parametrize('legacy', [False, True])
async def test_restart_uses_saved_pending_payload_even_after_excerpt_selector_changes(repo, monkeypatch, legacy):
    model, search = QuoteModel(relevant=True, interrupt=True), LongSearch(relevant=True, two=True)
    ctrl = Controller(repo, model, search)
    job = repo.create_job('显示运行状态')
    await ctrl.start(job.id); await finish(ctrl, job.id)
    assert repo.get_job(job.id).status.value == 'PARTIAL'
    state = repo.get_checkpoint(job.id, 1)
    saved = next(iter(state['pending_match_payloads'].values()))
    if legacy:
        state.pop('pending_match_payloads')
        state['pending_matches'][saved['resource_id']][0]['supporting_quote'] = 'Shows running agents.'
        repo.save_checkpoint(job.id, 1, state)
    import goalsift.controller as module
    original = module.select_excerpt
    def changed(text, focus=''):
        assert not text.startswith('FIRST') or (legacy and focus == ''), 'Pending context must use the saved input or legacy fallback'
        return original(text, focus)
    monkeypatch.setattr(module, 'select_excerpt', changed)
    resumed_model = QuoteModel(relevant=True)
    resumed = Controller(repo, resumed_model, search)
    await resumed.start(job.id); await finish(resumed, job.id)
    view = repo.current_view(job.id)
    assert view['status'] == 'COMPLETED'
    assert all(a['status'] == 'SUPPORTED' for a in view['assessments'])
    assert all(item['resource_id'] != saved['resource_id'] for item in resumed_model.received)
    if not legacy:
        assert view['source_reviews'][saved['resource_id']]['match_context'][0]['excerpt_ranges'] == saved['sources'][0]['excerpt_ranges']


@pytest.mark.asyncio
async def test_repository_read_limit_is_explicit_without_extra_requests(monkeypatch):
    from goalsift.search_adapter import SearchAdapter
    requests = []
    def handler(request):
        requests.append(request)
        if request.url.path.endswith('/acme/dash'):
            return httpx.Response(200, json={'default_branch': 'main'})
        if request.url.path.endswith('/contents'):
            return httpx.Response(200, json=[{'path': 'README.md', 'type': 'file', 'size': 18000}])
        return httpx.Response(200, json={'type': 'file', 'encoding': 'base64', 'sha': 'sha',
            'content': base64.b64encode(('status\n' + 'z'*18000).encode()).decode(),
            'html_url': 'https://github.com/acme/dash/blob/main/README.md'})
    client = httpx.AsyncClient
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kw: client(transport=httpx.MockTransport(handler), **kw))
    adapter = SearchAdapter()
    async def public(url): return True
    monkeypatch.setattr(adapter, '_public', public)
    docs, meta = await adapter.read_repository('https://github.com/acme/dash')
    assert len(requests) == 3 and meta['http_requests'] == 3
    assert len(next(d.text for d in docs if d.title == 'README.md')) == 12000
    assert any('后文未用于匹配判断' in note for note in meta['notes'])
