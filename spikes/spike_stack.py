"""M1 Spike — backend + storage minimal stack check (06 §10.5).

Proves, live:
  1. FastAPI serves a real HTTP endpoint (via TestClient)
  2. SQLite writes/reads inside the isolated data root (path-guarded)
  3. transaction commit + rollback
  4. job-status transition enforced server-side (illegal transition -> 400)

Does NOT build the full app. Frontend toolchain presence is reported separately.
Run: python3 -m spikes.spike_stack
"""

from __future__ import annotations

import json
import os
import sys
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from goalsift.config import load_env
from goalsift.models import ALLOWED_TRANSITIONS, JobStatus
from goalsift.paths import resolve_under_root, sanctioned_data_root

load_env()

import fastapi
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient


def report(section: str, body: object) -> None:
    print(f"\n===== {section} =====")
    print(body if isinstance(body, str) else json.dumps(body, indent=2, default=str, ensure_ascii=False))


def main() -> int:
    failures: list[str] = []

    # --- 1. SQLite in isolated data root ----------------------------------
    db_path = resolve_under_root("m1_spike.sqlite")
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, status TEXT, ts TEXT)")
    try:
        conn.execute("BEGIN")
        conn.execute("INSERT INTO jobs VALUES (?,?,?)",
                     ("job_demo", JobStatus.RESEARCHING.value, datetime.now(timezone.utc).isoformat()))
        conn.execute("COMMIT")
        row = conn.execute("SELECT status FROM jobs WHERE id='job_demo'").fetchone()
        report("1. SQLITE", {
            "db_path": str(db_path),
            "inside_sanctioned_root": str(db_path).startswith(str(sanctioned_data_root())),
            "read_back_status": row[0] if row else None,
            "sqlite_version": sqlite3.sqlite_version,
        })
        if not row or row[0] != JobStatus.RESEARCHING.value:
            failures.append("sqlite: read-back mismatch")
        if not str(db_path).startswith(str(sanctioned_data_root())):
            failures.append("sqlite: db outside sanctioned root")
    finally:
        conn.close()

    # --- 2. transaction rollback ------------------------------------------
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE IF NOT EXISTS probe (k TEXT PRIMARY KEY)")
    conn.execute("BEGIN")
    conn.execute("INSERT INTO probe VALUES ('before')")
    conn.execute("ROLLBACK")
    after = conn.execute("SELECT COUNT(*) FROM probe WHERE k='before'").fetchone()[0]
    report("2. ROLLBACK", {"rows_after_rollback": after, "rolled_back_clean": after == 0})
    if after != 0:
        failures.append("sqlite: rollback failed")
    conn.close()

    # --- 3. FastAPI real endpoint + transition enforcement ----------------
    app = FastAPI(title="M1 Spike")

    @app.get("/api/health")
    def health():
        return {"ok": True, "fastapi": fastapi.__version__}

    @app.post("/api/jobs/{job_id}/transition")
    def transition(job_id: str, target: str):
        try:
            t = JobStatus(target)
        except ValueError:
            raise HTTPException(400, f"unknown status {target}")
        # demo: current is always CREATED
        current = JobStatus.CREATED
        if t not in ALLOWED_TRANSITIONS[current]:
            raise HTTPException(400, f"illegal {current.value}->{target}")
        return {"job_id": job_id, "from": current.value, "to": target}

    client = TestClient(app)
    h = client.get("/api/health")
    ok_legal = client.post("/api/jobs/j1/transition?target=RESEARCHING")
    ok_illegal = client.post("/api/jobs/j2/transition?target=RESEARCHING"
                             if False else "/api/jobs/j2/transition?target=RESEARCHING")
    # illegal: CANCELLED cannot go to RESEARCHING — simulate by sending target that
    # is not allowed from CREATED (e.g. PAUSED is NOT in ALLOWED[CREATED])
    illegal = client.post("/api/jobs/j3/transition?target=PAUSED")
    report("3. FASTAPI", {
        "fastapi_version": fastapi.__version__,
        "uvicorn_version": uvicorn.__version__,
        "health_status": h.status_code,
        "health_body": h.json(),
        "legal_transition_status": ok_legal.status_code,
        "illegal_transition_status": illegal.status_code,
        "illegal_body": illegal.json() if illegal.status_code != 200 else "BUG",
    })
    if h.status_code != 200:
        failures.append("fastapi: health failed")
    if ok_legal.status_code != 200:
        failures.append("fastapi: legal transition failed")
    if illegal.status_code != 400:
        failures.append("fastapi: illegal transition not rejected")

    verdict = "PASS" if not failures else "FAIL"
    report("VERDICT", {"verdict": verdict, "failures": failures, "all_live": True})
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
