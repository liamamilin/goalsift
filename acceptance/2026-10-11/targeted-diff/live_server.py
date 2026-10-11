"""Real providers, independent copy of the prior isolated Live acceptance DB.

Startup is read-only research-wise. Only a browser-submitted investigation runs.
"""
import json, os, socket, sqlite3, tempfile
from pathlib import Path
source = Path('/private/tmp/goalsift-review-live-a2993wyu/goalsift.sqlite')
root = Path(tempfile.mkdtemp(prefix='goalsift-targeted-live-', dir='/private/tmp'))
assert source.exists() and not source.is_relative_to(root)
destination = root / 'goalsift.sqlite'
with sqlite3.connect(f'file:{source}?mode=ro', uri=True) as origin, sqlite3.connect(destination) as clone:
    origin.backup(clone)
    assert clone.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
os.environ['GOALSIFT_DATA_DIR'] = str(root)
os.environ['GOALSIFT_BUDGET_USD'] = '0.12'
os.environ['GOALSIFT_MAX_ACTIONS'] = '40'
os.environ['GOALSIFT_MAX_RUNTIME_SECONDS'] = '600'
os.environ['GOALSIFT_LLM_MODEL'] = 'deepseek-flash'
from goalsift.repository import Repository
from goalsift.app import create_app
repo = Repository()
assert Path(repo.db_path).resolve() == destination.resolve()
assert Path(repo._conn.execute('PRAGMA database_list').fetchone()[2]).resolve() == destination.resolve()
jid = 'job_7f396bd6fd70462b'
assert repo.get_job(jid).status.value == 'COMPLETED' and repo.get_job(jid).current_revision == 2
sock = socket.socket(); sock.bind(('127.0.0.1', 0))
info = {'job_id':jid, 'port':sock.getsockname()[1], 'data_dir':str(root), 'providers':'production DeepSeek/Exa/GitHub adapters', 'source_backup':str(source)}
Path('/private/tmp/goalsift-targeted-live.json').write_text(json.dumps(info))
print(json.dumps(info), flush=True)
import uvicorn
uvicorn.Server(uvicorn.Config(create_app(repository=repo), host='127.0.0.1', port=info['port'], log_level='warning')).run(sockets=[sock])
