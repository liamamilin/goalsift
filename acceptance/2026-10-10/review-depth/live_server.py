"""Independent, budgeted live browser acceptance using production adapters."""
import os, json, tempfile, socket
from pathlib import Path
os.environ['GOALSIFT_DATA_DIR'] = tempfile.mkdtemp(prefix='goalsift-review-live-', dir='/private/tmp')
os.environ['GOALSIFT_BUDGET_USD'] = '0.15'
os.environ['GOALSIFT_MAX_ACTIONS'] = '40'
os.environ['GOALSIFT_MAX_RUNTIME_SECONDS'] = '600'
os.environ['GOALSIFT_LLM_MODEL'] = 'deepseek-flash'
os.environ['PYDANTIC_AI_NO_BANNER'] = '1'
from goalsift.app import create_app
from goalsift.repository import Repository
repo = Repository()
assert Path(repo._conn.execute('PRAGMA database_list').fetchone()[2]).resolve().is_relative_to(Path(os.environ['GOALSIFT_DATA_DIR']))
sock = socket.socket()
sock.bind(('127.0.0.1', 0))
port = sock.getsockname()[1]
info = {'port': port, 'data_dir': os.environ['GOALSIFT_DATA_DIR'], 'budget_per_revision': 0.15,
        'maximum_authorized_test_revisions': 2, 'prior_spend': 0.3987574, 'total_authorization': 1.0}
Path('/private/tmp/goalsift-review-live-server.json').write_text(json.dumps(info))
print(json.dumps(info), flush=True)
import uvicorn
uvicorn.Server(uvicorn.Config(create_app(repository=repo), host='127.0.0.1', port=port, log_level='warning')).run(sockets=[sock])
