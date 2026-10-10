"""Offline browser QA only; fake providers, actual API/Controller/SQLite/UI."""
import os, asyncio, runpy, json, tempfile, socket
from pathlib import Path
os.environ['GOALSIFT_DATA_DIR'] = tempfile.mkdtemp(prefix='goalsift-review-qa-', dir='/private/tmp')
os.environ['GOALSIFT_MAX_ACTIONS'] = '40'
os.environ['GOALSIFT_MAX_RUNTIME_SECONDS'] = '60'
os.environ['GOALSIFT_BUDGET_USD'] = '1'
from goalsift.app import create_app
from goalsift.repository import Repository
from goalsift.controller import Controller
from goalsift.llm_adapter import GoalDefinition
fixtures = runpy.run_path('tests/test_goal_review_depth.py')

class UIModel(fixtures['ReviewModel']):
    async def define_goal(self, text):
        self.calls.append('define')
        return GoalDefinition(statement=text, purpose='查看 Agent 的运行状态与清晰的状态面板',
                              assumptions=['演示暂以单用户本地环境为前提', '尚未在目标环境验收'])

model, search = UIModel(), fixtures['DeepSearch']()
repo = Repository()
assert Path(repo._conn.execute('PRAGMA database_list').fetchone()[2]).resolve().is_relative_to(Path(os.environ['GOALSIFT_DATA_DIR']))
async def seed():
    ctrl = Controller(repo, model, search)
    job = repo.create_job('[UI 隔离验证] 查看 Agent 运行状态，页面清晰可读。无需固定动画或帧率。')
    await ctrl.start(job.id)
    await ctrl._runs[job.id]
    assert repo.get_job(job.id).status.value == 'COMPLETED'
    return job.id
jid = asyncio.run(seed())
sock = socket.socket()
sock.bind(('127.0.0.1', 0))
port = sock.getsockname()[1]
info = {'job_id': jid, 'port': port, 'data_dir': os.environ['GOALSIFT_DATA_DIR'], 'providers': 'explicit test fixtures, no paid requests'}
Path('/private/tmp/goalsift-review-fixture.json').write_text(json.dumps(info))
print(json.dumps(info), flush=True)
import uvicorn
uvicorn.Server(uvicorn.Config(create_app(repository=repo, llm=model, search=search),
                             host='127.0.0.1', port=port, log_level='warning')).run(sockets=[sock])
