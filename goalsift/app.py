"""Local API, durable SSE and a single application executor."""
from __future__ import annotations
import asyncio
import json
import os
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, PlainTextResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .budget import BudgetConfig
from .config import load_env
from .controller import Controller
from .exporter import to_json, to_markdown
from .llm_adapter import LLMAdapter
from .models import JobStatus
from .repository import Repository
from .search_adapter import SearchAdapter
from .security import redact_secrets
from .paths import resolve_under_root
load_env()

class CreateJob(BaseModel):
    request: str = Field(min_length=1, max_length=12000)
class InputCmd(BaseModel):
    constraint: str = Field(min_length=1, max_length=6000)


def create_app(repository: Repository | None = None, llm=None, search=None):
    @asynccontextmanager
    async def lifespan(app):
        lock_file = None
        if repository is None:
            import fcntl
            lock_file = resolve_under_root('executor.lock').open('a')
            try:
                fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                lock_file.close()
                raise RuntimeError('此数据目录已由另一个 GoalSift 服务使用；只运行一个 worker')
        try:
            runtime()
            # Importing a module never opens or changes the production database.
            app.state.repo.recover_orphans()
            yield
        finally:
            if app.state.controller: await app.state.controller.shutdown()
            if repository is None and app.state.repo: app.state.repo.close()
            if lock_file: lock_file.close()

    app = FastAPI(title='GoalSift', version='0.2.1', lifespan=lifespan)
    app.state.repo = repository
    app.state.controller = None
    origins = ['http://localhost:5173', 'http://127.0.0.1:5173']
    app.add_middleware(CORSMiddleware, allow_origins=origins,
        allow_methods=['GET', 'POST'], allow_headers=['Content-Type', 'Last-Event-ID'])

    def runtime():
        if app.state.repo is None: app.state.repo = Repository()
        if app.state.controller is None:
            app.state.controller = Controller(app.state.repo, llm or LLMAdapter(), search or SearchAdapter())
        return app.state.repo, app.state.controller

    @app.middleware('http')
    async def local_requests(request: Request, call_next):
        # A hostile web page cannot mutate the user's local jobs, even with an ordinary form POST.
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            origin = request.headers.get('origin')
            same_origin = str(request.base_url).rstrip('/')
            if origin and origin not in origins and origin != same_origin:
                return JSONResponse({'detail': '不允许此来源修改本地研究任务'}, status_code=403)
            if request.headers.get('sec-fetch-site') == 'cross-site':
                return JSONResponse({'detail': '拒绝跨站请求'}, status_code=403)
        host = request.headers.get('host', '').split(':')[0].strip('[]')
        if host not in ('127.0.0.1', 'localhost', 'testserver', ''):
            return JSONResponse({'detail': '只接受本地地址'}, status_code=400)
        return await call_next(request)

    def require(job_id):
        repo, ctrl = runtime()
        job = repo.get_job(job_id)
        if not job: raise HTTPException(404, '研究任务不存在')
        return repo, ctrl, job

    @app.post('/api/jobs')
    def create_job(body: CreateJob):
        if not body.request.strip(): raise HTTPException(400, '目标不能为空')
        repo, _ = runtime()
        job = repo.create_job(body.request.strip())
        return {'id': job.id, 'status': job.status.value}

    @app.get('/api/jobs')
    def list_jobs():
        repo, _ = runtime()
        return [{'id': j.id, 'status': j.status.value, 'original_request': j.original_request[:120],
                 'revision': j.current_revision, 'created_at': j.created_at.isoformat()}
                for j in repo.list_jobs()]

    @app.get('/api/jobs/{job_id}')
    @app.get('/api/jobs/{job_id}/results')
    def get_job(job_id: str):
        repo, _, _ = require(job_id)
        return repo.current_view(job_id)

    @app.post('/api/jobs/{job_id}/start')
    @app.post('/api/jobs/{job_id}/resume')
    async def start(job_id: str):
        _, ctrl, _ = require(job_id)
        if not await ctrl.start(job_id): raise HTTPException(409, '当前状态不能启动，或任务正在运行')
        return {'id': job_id, 'status': 'RESEARCHING'}

    @app.post('/api/jobs/{job_id}/pause')
    async def pause(job_id: str):
        repo, ctrl, _ = require(job_id)
        if not ctrl.pause(job_id): raise HTTPException(409, '当前状态不能暂停')
        return {'id': job_id, 'status': repo.get_job(job_id).status.value, 'pause_requested': True}

    @app.post('/api/jobs/{job_id}/cancel')
    async def cancel(job_id: str):
        _, ctrl, _ = require(job_id)
        if not ctrl.cancel(job_id): raise HTTPException(409, '当前状态不能取消')
        return {'id': job_id, 'status': 'CANCELLED'}

    @app.post('/api/jobs/{job_id}/input')
    async def input_cmd(job_id: str, body: InputCmd):
        repo, ctrl, job = require(job_id)
        if not body.constraint.strip(): raise HTTPException(400, '补充内容不能为空')
        if job.status == JobStatus.COMPLETED: ok = await ctrl.refine(job_id, body.constraint)
        elif job.status == JobStatus.NEEDS_INPUT: ok = await ctrl.answer_input(job_id, body.constraint)
        else: raise HTTPException(409, '当前状态不接受补充输入')
        if not ok: raise HTTPException(409, '任务已在运行或输入未提交')
        return {'id': job_id, 'status': 'RESEARCHING', 'revision': repo.get_job(job_id).current_revision}

    @app.get('/api/jobs/{job_id}/revisions')
    def revisions(job_id: str):
        repo, _, _ = require(job_id)
        return repo.list_revisions(job_id)

    @app.get('/api/jobs/{job_id}/revisions/{revision}')
    def revision_result(job_id: str, revision: int):
        repo, _, _ = require(job_id)
        result = repo.get_revision(job_id, revision)
        if result is None: raise HTTPException(404, '该修订尚无完成快照')
        return result

    @app.get('/api/jobs/{job_id}/export')
    def export(job_id: str, fmt: str = 'markdown', revision: int | None = None):
        repo, _, job = require(job_id)
        if fmt not in ('json', 'markdown'): raise HTTPException(400, '格式必须是 markdown 或 json')
        view = repo.current_view(job_id) if revision is None else repo.get_revision(job_id, revision)
        if view is None: raise HTTPException(404, '修订不存在')
        filename = f'goalsift-{job_id}-r{view["revision"]}'
        headers = {'Content-Disposition': f'attachment; filename="{filename}.{"json" if fmt == "json" else "md"}"'}
        if fmt == 'json': return JSONResponse(to_json(repo, job_id, view=view), headers=headers)
        return PlainTextResponse(to_markdown(repo, job_id, view=view), headers=headers)

    @app.get('/api/jobs/{job_id}/events/history')
    def event_history(job_id: str, after: int = 0):
        repo, _, _ = require(job_id)
        return repo.events_page(job_id, max(0, after))

    @app.get('/api/jobs/{job_id}/events')
    async def events(job_id: str, request: Request, last: int = 0):
        repo, _, _ = require(job_id)
        try: cursor = max(last, int(request.headers.get('last-event-id') or 0))
        except ValueError: raise HTTPException(400, '事件游标无效')
        async def gen():
            nonlocal cursor
            idle = 0
            while not await request.is_disconnected():
                for ev in repo.events_page(job_id, cursor):
                    cursor = ev['cursor']
                    yield f'id: {cursor}\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n'
                job = repo.get_job(job_id)
                if job.status not in (JobStatus.CREATED, JobStatus.RESEARCHING):
                    yield 'data: ' + json.dumps({'event_type': 'DONE', 'status': job.status.value,
                                                'revision': job.current_revision, 'cursor': cursor}) + '\n\n'
                    return
                idle += 1
                if idle % 20 == 0: yield ': heartbeat\n\n'
                await asyncio.sleep(0.5)
        return StreamingResponse(gen(), media_type='text/event-stream',
            headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

    @app.get('/api/health')
    def health(): return {'ok': True, 'version': '0.2.1'}

    @app.get('/api/settings')
    def settings():
        config = BudgetConfig.from_env()
        llm_key = bool(os.environ.get('GOALSIFT_LLM_API_KEY') or os.environ.get('DEEPSEEK_API_KEY'))
        search_key = bool(os.environ.get('GOALSIFT_SEARCH_API_KEY') or os.environ.get('EXA_API_KEY'))
        return {'llm': {'configured': llm_key, 'provider': os.environ.get('GOALSIFT_LLM_PROVIDER') or 'deepseek',
                       'model': os.environ.get('GOALSIFT_LLM_MODEL') or 'deepseek-flash',
                       'key_preview': '***' if llm_key else '(unset)'},
                'search': {'configured': search_key, 'provider': os.environ.get('GOALSIFT_SEARCH_PROVIDER') or 'exa',
                           'key_preview': '***' if search_key else '(unset)'},
                'budget': {**config.__dict__, 'budget_usd': str(config.budget_usd) if config.budget_usd else 'unknown (no spend cap)'},
                'binding': '127.0.0.1 (loopback only)', 'note': '配置在服务端 .env 修改后重启生效。'}
    built_ui = Path(__file__).resolve().parent.parent / 'frontend' / 'dist'
    if built_ui.is_dir():
        app.mount('/', StaticFiles(directory=built_ui, html=True), name='frontend')
    return app

app = create_app()
