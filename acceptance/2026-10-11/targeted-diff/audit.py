"""Read-only acceptance audit. No research submission or provider calls.

Run from the repository root while the explicitly isolated QA servers run.
"""
import json
import sqlite3
import urllib.request
from pathlib import Path
from goalsift.models import Condition, Resource, Capability, Evidence, Assessment, Proposal
from goalsift.validators import validate_references, validate_traceability, validate_assessment_status

proof = Path(__file__).resolve().parent
repo_root = proof.parents[2]
live_dir = Path('/private/tmp/goalsift-targeted-live-ljzczi7q')
offline_dir = Path('/private/tmp/goalsift-targeted-qa-8ldufnlh')
preview_dir = Path('/private/tmp/goalsift-completion-live')
for directory in (live_dir, offline_dir, preview_dir):
    assert directory.is_relative_to('/private/tmp')
    assert not directory.is_relative_to(repo_root)

def fetch(url, filename):
    content = urllib.request.urlopen(url, timeout=15).read()
    (proof / filename).write_bytes(content)
    return json.loads(content) if filename.endswith('.json') else content

def db(directory):
    conn = sqlite3.connect(f'file:{directory / "goalsift.sqlite"}?mode=ro', uri=True)
    assert Path(conn.execute('PRAGMA database_list').fetchone()[2]).resolve() == (directory / 'goalsift.sqlite').resolve()
    assert conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    return conn

def snapshot(conn, job, revision):
    return conn.execute('SELECT data FROM revision_snapshots WHERE job_id=? AND revision=?', (job, revision)).fetchone()[0]

live = fetch('http://127.0.0.1:61894/api/jobs/job_7f396bd6fd70462b', 'live-after.json')
live_events = fetch('http://127.0.0.1:61894/api/jobs/job_7f396bd6fd70462b/events/history', 'live-events.json')
live_diff = fetch('http://127.0.0.1:61894/api/jobs/job_7f396bd6fd70462b/compare?base=2&target=3', 'live-diff.json')
for fmt, suffix in (('json', 'json'), ('markdown', 'md')):
    fetch(f'http://127.0.0.1:61894/api/jobs/job_7f396bd6fd70462b/export?fmt={fmt}', f'live-r3-export.{suffix}')
offline = fetch('http://127.0.0.1:61326/api/jobs/job_d9bc4d1e9ede42c4', 'offline-after.json')
fetch('http://127.0.0.1:61326/api/jobs/job_d9bc4d1e9ede42c4/compare?base=1&target=2', 'offline-diff.json')
for fmt, suffix in (('json', 'json'), ('markdown', 'md')):
    fetch(f'http://127.0.0.1:61326/api/jobs/job_d9bc4d1e9ede42c4/export?fmt={fmt}', f'offline-r2-export.{suffix}')

previous = json.loads((proof / 'live-before.json').read_text())
assert live['status'] == 'COMPLETED' and live['revision'] == 3
assert len(live['conditions']) == 7 and len(live['resources']) == 8
assert len(live['assessments']) == 56 and len(live['reused_assessment_ids']) == 49
assert all(c['provenance'] == 'USER_CONFIRMED' for c in live['conditions'])
assert live['goal']['purpose'] == previous['goal']['purpose']
assert live['goal']['constraints'] == previous['goal']['constraints']
assert {c['statement'] for c in live['conditions']} == {c['statement'] for c in previous['conditions']}
assert not any(a['status'] == 'VERIFIED' for a in live['assessments'])
args = {key: [model.model_validate(item) for item in live[key]] for key, model in
        [('conditions', Condition), ('resources', Resource), ('capabilities', Capability), ('evidence', Evidence), ('assessments', Assessment)]}
proposal = Proposal.model_validate(live['proposal'])
assert not validate_references(job_id=live['id'], **args, proposals=[proposal])
assert not validate_traceability(proposal=proposal, **args)
assert not [p for a in args['assessments'] for p in validate_assessment_status(a, args['evidence'])]

current_db = db(live_dir)
origin_db = db(Path('/private/tmp/goalsift-review-live-a2993wyu'))
assert snapshot(current_db, live['id'], 2) == snapshot(origin_db, live['id'], 2)
offline_db = db(offline_dir)
assert json.loads(snapshot(offline_db, offline['id'], 1)) == json.loads((proof / 'offline-before.json').read_text())

# The preview API gained compatibility defaults, so compare actual durable
# values with its pre-upgrade SQLite backup, rather than comparing API shapes.
preview_db = db(preview_dir)
backup_db = sqlite3.connect(f'file:{preview_dir / "backups/before-targeted-diff.sqlite"}?mode=ro', uri=True)
tables = [row[0] for row in backup_db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
for table in tables:
    assert table.replace('_', '').isalnum()
    columns = [row[1] for row in backup_db.execute(f'PRAGMA table_info({table})')]
    selection = ','.join('"' + column + '"' for column in columns)
    a = backup_db.execute(f'SELECT {selection} FROM {table}').fetchall()
    b = preview_db.execute(f'SELECT {selection} FROM {table}').fetchall()
    assert sorted(a, key=repr) == sorted(b, key=repr), table

events = [event for event in live_events if event['revision'] == 3]
actions = [event['status'] for event in events]
assert not any(action.startswith(('DEFINED', 'DERIVED', 'CHALLENGED')) for action in actions)
assert live['budget_usage']['model_requests'] == 4
assert live['budget_usage']['reserved_usd'] == 0 and not live['budget_usage']['cost_unknown']
assert live_diff['summary']['reused_assessments'] == 49
assert live_diff['summary']['coverage_before'] == live_diff['summary']['coverage_after'] == 5
usage_before = live['budget_usage'].copy()
fetch('http://127.0.0.1:61894/api/jobs/job_7f396bd6fd70462b/compare?base=2&target=3', 'live-diff-repeat.json')
again = json.load(urllib.request.urlopen('http://127.0.0.1:61894/api/jobs/job_7f396bd6fd70462b'))
assert again['budget_usage'] == usage_before

cost = live['budget_usage']['cost_usd']
ledger = {'authorized_total_usd': 1, 'prior_conservative_usd': 0.5211726,
          'new_test_server_cap_usd': 0.12, 'new_test_requested_cap_usd': 0.1,
          'new_recorded_usd': cost, 'new_reserved_usd': 0, 'cost_unknown': False,
          'cumulative_recorded_or_conservative_usd': round(0.5211726 + cost, 7),
          'remaining_usd': round(1 - 0.5211726 - cost, 7),
          'basis': 'application conservative model token rates plus Exa reported cost; not a provider invoice'}
assert ledger['cumulative_recorded_or_conservative_usd'] <= 1
(proof / 'fee-ledger.json').write_text(json.dumps(ledger, ensure_ascii=False, indent=2))
result = {'verdict': 'PASS', 'live_status': live['status'], 'live_revision': live['revision'],
          'condition_count': 7, 'resource_count': 8, 'assessment_count': 56,
          'reused_assessment_count': 49, 'confirmed_conditions_preserved': True,
          'no_verified_from_docs': True, 'references_and_traceability': True,
          'live_previous_snapshot_byte_identical': True, 'offline_previous_snapshot_identical': True,
          'preview_durable_tables_identical_to_backup': tables,
          'free_comparison_no_new_usage': True, 'revision_action_types': actions,
          'diff_summary': live_diff['summary'], 'fee_ledger': ledger}
(proof / 'audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
print(json.dumps(result, ensure_ascii=False, indent=2))
