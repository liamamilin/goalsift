"""Explicit mock providers for UI QA; all application layers are real."""
import asyncio, json, os, runpy, socket, tempfile
from pathlib import Path
os.environ['GOALSIFT_DATA_DIR'] = tempfile.mkdtemp(prefix='goalsift-targeted-qa-', dir='/private/tmp')
os.environ['GOALSIFT_BUDGET_USD'] = '0.2'
os.environ['GOALSIFT_MAX_ACTIONS'] = '40'
os.environ['GOALSIFT_MAX_RUNTIME_SECONDS'] = '60'
from goalsift.app import create_app
from goalsift.repository import Repository
from goalsift.controller import Controller
from goalsift.llm_adapter import GoalDefinition
fixtures = runpy.run_path('tests/test_targeted_diff.py')
class UIModel(fixtures['ScopeModel']):
    async def define_goal(self, text):
        return GoalDefinition(statement=text, purpose='研究可在本地部署、展示状态并提供启动暂停接口的 Agent 控制台', assumptions=['接口还需目标环境验收'])
model, search, repo = UIModel(), fixtures['ScopeSearch'](), Repository()
assert Path(repo.db_path).resolve().is_relative_to(Path(os.environ['GOALSIFT_DATA_DIR']))
assert Path(repo._conn.execute('PRAGMA database_list').fetchone()[2]).resolve() == Path(repo.db_path).resolve()
async def seed():
    ctrl = Controller(repo, model, search)
    job = repo.create_job('[隔离 UI 测试；假模型/假搜索] 本地 Agent 控制台，展示运行状态、启动暂停接口、本地部署。')
    await ctrl.start(job.id); await ctrl._runs[job.id]
    assert repo.get_job(job.id).status.value == 'COMPLETED'
    return job.id
jid = asyncio.run(seed())
sock = socket.socket(); sock.bind(('127.0.0.1', 0))
info = {'job_id':jid, 'port':sock.getsockname()[1], 'data_dir':os.environ['GOALSIFT_DATA_DIR'], 'providers':'explicit fixtures; no paid requests'}
Path('/private/tmp/goalsift-targeted-qa.json').write_text(json.dumps(info))
print(json.dumps(info), flush=True)
import uvicorn
uvicorn.Server(uvicorn.Config(create_app(repo, model, search), host='127.0.0.1', port=info['port'], log_level='warning')).run(sockets=[sock])
