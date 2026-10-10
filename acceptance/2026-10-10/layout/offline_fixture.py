"""Offline browser QA only. All research providers are test fixtures."""
import os, asyncio, runpy, json, tempfile
from pathlib import Path
os.environ['GOALSIFT_DATA_DIR'] = tempfile.mkdtemp(prefix='goalsift-layout-qa-', dir='/private/tmp')
os.environ['GOALSIFT_MAX_ACTIONS'] = '40'
os.environ['GOALSIFT_MAX_RUNTIME_SECONDS'] = '60'
os.environ['GOALSIFT_BUDGET_USD'] = '1'
from goalsift.app import create_app
from goalsift.repository import Repository
from goalsift.controller import Controller
fixtures = runpy.run_path('tests/test_runtime_integration.py')
model, search = fixtures['ModelFixture'](ambiguous=True), fixtures['SearchFixture']()
repo = Repository()
assert Path(repo._conn.execute('PRAGMA database_list').fetchone()[2]).resolve().is_relative_to(Path(os.environ['GOALSIFT_DATA_DIR']))
async def seed():
    ctrl = Controller(repo, model, search)
    question = repo.create_job('[UI 验证数据] 需要澄清的 Agent 控制台目标')
    await ctrl.start(question.id)
    await ctrl._runs[question.id]
    assert repo.get_job(question.id).status.value == 'NEEDS_INPUT'
    partial = repo.create_job('[UI 验证数据] 服务错误后的部分结果')
    repo.set_job_status(partial.id, 'RESEARCHING')
    repo.set_job_status(partial.id, 'PARTIAL', checkpoint_ref='UI fixture: source unavailable', budget_usage={'cost_unknown':True,'cost_usd':None,'stopped_reason':'UI fixture: source unavailable'})
    created = repo.create_job('[UI 验证数据] 尚未开始的研究')
    ids = {'question':question.id,'partial':partial.id,'created':created.id}
    Path('/private/tmp/goalsift-layout-fixture-ids.json').write_text(json.dumps(ids))
    print(json.dumps(ids),flush=True)
asyncio.run(seed())
assert search.searches == search.reads == 0
app = create_app(repository=repo, llm=model, search=search)
import uvicorn
import socket
sock = socket.socket()
sock.bind(('127.0.0.1', 0))
port = sock.getsockname()[1]
print(f'Offline browser QA port: {port}', flush=True)
uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=port, log_level='warning')).run(sockets=[sock])
