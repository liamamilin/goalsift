"""FastAPI application — HTTP API + SSE for research jobs (06 §6).

Single trusted write entry is the Controller. The browser never holds model or
search keys. Binds to loopback by default (06 §9.3).
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .controller import Controller
from .exporter import to_json, to_markdown
from .llm_adapter import LLMAdapter
from .models import JobStatus
from .repository import Repository
from .search_adapter import SearchAdapter
from .validators import ValidationError, validate_transition

repo = Repository()
llm = LLMAdapter()
search = SearchAdapter()
controller = Controller(repo, llm, search)

# 04 §9 crash recovery: on startup, recover orphaned RESEARCHING jobs to PAUSED
_recovered = repo.recover_orphans()

app = FastAPI(title="GoalSift", version="0.2.0a0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"], allow_headers=["*"],
)


class CreateJob(BaseModel):
    request: str


def _job_dict(job_id: str) -> dict[str, Any]:
    job = repo.get_job(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    goal = repo.get_goal(job_id)
    conditions = repo.list_conditions(job_id)
    resources = repo.list_resources(job_id)
    evidence = repo.list_evidence(job_id)
    assessments = repo.list_assessments(job_id)
    proposal = repo.get_proposal(job_id)
    return {
        "id": job.id, "status": job.status.value, "revision": job.current_revision,
        "original_request": job.original_request,
        "goal": goal.model_dump() if goal else None,
        "conditions": [c.model_dump() for c in conditions],
        "resources": [r.model_dump() for r in resources],
        "evidence": [e.model_dump() for e in evidence],
        "assessments": [a.model_dump() for a in assessments],
        "proposal": proposal.model_dump() if proposal else None,
    }


@app.post("/api/jobs")
def create_job(body: CreateJob):
    if not body.request.strip():
        raise HTTPException(400, "empty request")
    job = repo.create_job(body.request)
    return {"id": job.id, "status": job.status.value}


@app.get("/api/jobs")
def list_jobs():
    return [{"id": j.id, "status": j.status.value,
             "original_request": j.original_request[:120],
             "revision": j.current_revision} for j in repo.list_jobs()]


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    return _job_dict(job_id)


@app.post("/api/jobs/{job_id}/start")
async def start(job_id: str):
    job = repo.get_job(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    try:
        validate_transition(JobStatus(job.status), JobStatus.RESEARCHING)
    except ValidationError as e:
        raise HTTPException(400, str(e))
    ok = await controller.start(job_id)
    if not ok:
        raise HTTPException(409, "job already running or not startable")
    return {"id": job_id, "status": "RESEARCHING"}


@app.post("/api/jobs/{job_id}/pause")
async def pause(job_id: str):
    if not controller.pause(job_id):
        raise HTTPException(409, "cannot pause")
    return {"id": job_id, "status": "PAUSED"}


@app.post("/api/jobs/{job_id}/resume")
async def resume(job_id: str):
    return await start(job_id)


@app.post("/api/jobs/{job_id}/cancel")
async def cancel(job_id: str):
    if not controller.cancel(job_id):
        raise HTTPException(409, "cannot cancel")
    return {"id": job_id, "status": "CANCELLED"}


class InputCmd(BaseModel):
    constraint: str


@app.post("/api/jobs/{job_id}/input")
async def input_cmd(job_id: str, body: InputCmd):
    """Handle user input: Refine (COMPLETED -> new revision) or answer (NEEDS_INPUT -> resume).
    04 §3.1, 05 §12."""
    job = repo.get_job(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    if not body.constraint.strip():
        raise HTTPException(400, "empty input")
    if job.status == JobStatus.COMPLETED:
        ok = await controller.refine(job_id, body.constraint)
        if not ok:
            raise HTTPException(409, "refine could not start new revision")
        return {"id": job_id, "status": "RESEARCHING",
                "revision": repo.get_job(job_id).current_revision}
    if job.status == JobStatus.NEEDS_INPUT:
        ok = await controller.answer_input(job_id, body.constraint)
        if not ok:
            raise HTTPException(409, "could not resume from NEEDS_INPUT")
        return {"id": job_id, "status": "RESEARCHING"}
    raise HTTPException(409, f"cannot accept input in {job.status.value} state")


@app.get("/api/jobs/{job_id}/results")
def results(job_id: str):
    return _job_dict(job_id)


@app.get("/api/jobs/{job_id}/export")
def export(job_id: str, fmt: str = "markdown"):
    if fmt == "json":
        return to_json(repo, job_id)
    return to_markdown(repo, job_id)


@app.get("/api/jobs/{job_id}/events")
async def events(job_id: str, last: int = 0):
    """SSE stream of real research events (04 §10)."""
    async def gen():
        cursor = last
        while True:
            evs = repo.list_events(job_id, after=cursor)
            for ev in evs:
                cursor = max(cursor, repo.max_event_rowid(job_id))
                payload = {
                    "event_id": ev.event_id, "revision": ev.revision,
                    "event_type": ev.action_type.value, "status": ev.status,
                    "timestamp": ev.started_at.isoformat() if ev.started_at else None,
                    "related": ev.related_object_ids,
                    "error": ev.error, "usage": ev.usage,
                    "tool": ev.tool_result_ref,
                }
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            job = repo.get_job(job_id)
            if job and job.status in (JobStatus.COMPLETED, JobStatus.FAILED,
                                       JobStatus.CANCELLED, JobStatus.PAUSED,
                                       JobStatus.NEEDS_INPUT, JobStatus.PARTIAL):
                yield f"data: {json.dumps({'event_type':'DONE','status':job.status.value})}\n\n"
                return
            await asyncio.sleep(0.5)
    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/settings")
def settings():
    """Config status for the Settings page. Never returns secret values —
    only whether each provider key is configured, plus budget caps."""
    import os as _os
    from .security import redact_secrets
    llm_key = bool(_os.environ.get("DEEPSEEK_API_KEY") or _os.environ.get("GOALSIFT_LLM_API_KEY"))
    search_key = bool(_os.environ.get("EXA_API_KEY") or _os.environ.get("GOALSIFT_SEARCH_API_KEY"))
    return {
        "llm": {
            "configured": llm_key,
            "provider": _os.environ.get("GOALSIFT_LLM_PROVIDER", "deepseek"),
            "model": _os.environ.get("GOALSIFT_LLM_MODEL", "deepseek-chat"),
            "key_preview": "***" if llm_key else "(unset)",  # never the real value
        },
        "search": {
            "configured": search_key,
            "provider": _os.environ.get("GOALSIFT_SEARCH_PROVIDER", "exa"),
            "key_preview": "***" if search_key else "(unset)",
        },
        "budget": {
            "max_actions": int(_os.environ.get("GOALSIFT_MAX_ACTIONS") or 30),
            "max_tool_calls": int(_os.environ.get("GOALSIFT_MAX_TOOL_CALLS") or 20),
            "max_runtime_seconds": int(_os.environ.get("GOALSIFT_MAX_RUNTIME_SECONDS") or 300),
            "budget_usd": (_os.environ.get("GOALSIFT_BUDGET_USD")
                           or "unknown (no spend cap)"),
        },
        "binding": "127.0.0.1 (loopback only)",
        "note": "Keys are never exposed to the browser or logs.",
    }
