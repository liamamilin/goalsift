"""One authorized real-provider investigation in a fresh isolated DB copy.

No browser simulation; invokes the same Controller command as the API.
Does not execute the candidate project. Cost cap: USD 0.08.
"""
import asyncio
import json
import os
import sqlite3
import tempfile
from pathlib import Path

proof = Path(__file__).resolve().parent
origin = Path('/private/tmp/goalsift-targeted-live-ljzczi7q/goalsift.sqlite')
audit_existing = os.environ.get('GOALSIFT_AUDIT_EXISTING_DATA')
data = Path(audit_existing) if audit_existing else Path(tempfile.mkdtemp(prefix='goalsift-excerpts-live-', dir='/private/tmp'))
database = data / 'goalsift.sqlite'
assert origin.exists() and data.parent == Path('/private/tmp') and data.name.startswith('goalsift-excerpts-live-')
if not audit_existing:
    with sqlite3.connect(f'file:{origin}?mode=ro', uri=True) as source, sqlite3.connect(database) as copy:
        source.backup(copy)
        assert copy.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
os.environ.update(GOALSIFT_DATA_DIR=str(data), GOALSIFT_BUDGET_USD='0.08',
    GOALSIFT_MAX_ACTIONS='40', GOALSIFT_MAX_RUNTIME_SECONDS='300',
    GOALSIFT_LLM_MODEL='deepseek-flash', PYDANTIC_AI_NO_BANNER='1')
from goalsift.controller import Controller
from goalsift.llm_adapter import LLMAdapter
from goalsift.search_adapter import SearchAdapter
from goalsift.repository import Repository
from goalsift.targeted_research import TargetedResearch
from goalsift.exporter import to_markdown, to_json
from goalsift.revision_diff import compare_revisions

async def main():
    repo = Repository()
    assert Path(repo.db_path).resolve() == database.resolve()
    assert Path(repo._conn.execute('PRAGMA database_list').fetchone()[2]).resolve() == database.resolve()
    jid = 'job_7f396bd6fd70462b'
    before = repo.get_revision(jid, 3)
    assert before['status'] == 'COMPLETED' and before['revision'] == 3
    with sqlite3.connect(f'file:{origin}?mode=ro', uri=True) as original_db:
        old_snapshot = original_db.execute('SELECT data FROM revision_snapshots WHERE job_id=? AND revision=3', (jid,)).fetchone()[0]
    old_ids = {e['id'] for e in before['evidence']}
    cid = next(c['id'] for c in before['conditions'] if '状态指示' in c['statement'])
    rid = next(r['id'] for r in before['resources'] if r['name'] == 'builderz-labs/mission-control')
    if not audit_existing:
        assert repo.get_job(jid).current_revision == 3
        ctrl = Controller(repo, LLMAdapter(), SearchAdapter())
        assert await ctrl.investigate(jid, TargetedResearch(expected_revision=3, condition_ids=[cid],
            resource_ids=[rid], budget_usd=0.08, question='核查界面运行状态指示的具体文档依据；只依据实际提供的片段，不推断整份文档没有某项能力。'))
        print(json.dumps({'started': True, 'database': str(database), 'cap_usd': 0.08}), flush=True)
        await asyncio.wait_for(ctrl._runs[jid], 300)
    else:
        print(json.dumps({'audit_only': True, 'database': str(database)}), flush=True)
    after = repo.current_view(jid)
    (proof/'live-result.json').write_text(json.dumps(after, ensure_ascii=False, indent=2))
    (proof/'live-events.json').write_text(json.dumps(repo.events_page(jid), ensure_ascii=False, indent=2))
    (proof/'live-diff.json').write_text(json.dumps(compare_revisions(before, after), ensure_ascii=False, indent=2))
    (proof/'live-export.md').write_text(to_markdown(repo, jid))
    (proof/'live-export.json').write_text(json.dumps(to_json(repo, jid), ensure_ascii=False, indent=2))
    assert old_snapshot == repo._conn.execute('SELECT data FROM revision_snapshots WHERE job_id=? AND revision=3', (jid,)).fetchone()[0]
    usage = after['budget_usage']
    upper_cost = usage.get('cost_usd', 0) + usage.get('reserved_usd', 0)
    ledger = {'prior_cumulative_usd': 0.5388616, 'authorized_total_usd': 1,
        'request_cap_usd': 0.08, 'new_usage': usage,
        'cumulative_known_or_reserved_usd': round(0.5388616 + upper_cost, 7),
        'not_provider_invoice': True}
    (proof/'fee-ledger.json').write_text(json.dumps(ledger, ensure_ascii=False, indent=2))
    assert after['status'] == 'COMPLETED', after['status']
    assert upper_cost <= 0.08 and ledger['cumulative_known_or_reserved_usd'] <= 1
    assert not usage.get('cost_unknown') and usage['reserved_usd'] == 0
    assert len(after['conditions']) == 7 and len(after['resources']) == 8
    assert all(c['provenance'] == 'USER_CONFIRMED' for c in after['conditions'])
    assert not any(a['status'] == 'VERIFIED' for a in after['assessments'])
    contexts = after['source_reviews'][rid]['match_context']
    index = {e['id']: e for e in after['evidence']}
    ranges = {s['evidence_id']: s['excerpt_ranges'] for s in contexts}
    claims = [e for e in after['evidence'] if e['id'] not in old_ids and e['stance'] != 'CONTEXT']
    assert claims and any(s['is_partial'] for s in contexts)
    for claim in claims:
        parent = claim['locator'].removeprefix('exact source quote: ')
        receipt = index[parent]
        assert any(claim['excerpt_or_summary'] in receipt['excerpt_or_summary'][a:b] for a,b in ranges[parent])
        assert claim['source_version'] == receipt['source_version'] and claim['retrieved_at'] == receipt['retrieved_at']
    result = {'verdict': 'PASS', 'integration': 'real Controller/SQLite/DeepSeek/Exa/GitHub; no new browser test',
        'revision': after['revision'], 'status': after['status'], 'new_literal_claims_audited': len(claims),
        'matching_source_count': len(contexts), 'partial_sources': sum(s['is_partial'] for s in contexts),
        'all_new_claims_in_actual_supplied_spans': True, 'claim_read_times_and_versions_preserved': True,
        'prior_snapshot_byte_identical': True, 'reused_assessments': len(after['reused_assessment_ids']),
        'coverage': len(after['proposal']['condition_coverage']), 'condition_count': 7,
        'data_dir': str(data), 'usage': usage}
    (proof/'live-audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False), flush=True)
    repo.close()

asyncio.run(main())
