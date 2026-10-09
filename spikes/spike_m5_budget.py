"""M5 live proof — budget exhaustion -> PARTIAL with real external actions.

Runs the real Controller with max_actions=1 so the 2nd external action is
blocked; the job must end PARTIAL (not FAILED), with committed work saved.
Run: python3 -m spikes.spike_m5_budget
"""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from goalsift.config import load_env
load_env()
# shrink budget AFTER load_env so it overrides .env
os.environ["GOALSIFT_MAX_ACTIONS"] = "1"
os.environ["GOALSIFT_MAX_TOOL_CALLS"] = "1"

from goalsift.budget import BudgetConfig
from goalsift.controller import Controller
from goalsift.llm_adapter import LLMAdapter
from goalsift.paths import override_data_root
from goalsift.repository import Repository
from goalsift.search_adapter import SearchAdapter
from goalsift.models import JobStatus


async def main() -> int:
    tmp = Path(tempfile.mkdtemp()) / "data"
    tmp.mkdir(parents=True)
    override_data_root(tmp)
    repo = Repository()
    llm = LLMAdapter()
    search = SearchAdapter()
    ctrl = Controller(repo, llm, search)
    # force tiny budget on the controller's _run (it builds BudgetGuard from env)
    job = repo.create_job("build a polished agent management web dashboard")
    await ctrl.start(job.id)
    for _ in range(60):
        await asyncio.sleep(2)
        j = repo.get_job(job.id)
        if j.status not in (JobStatus.RESEARCHING, JobStatus.CREATED):
            break
    j = repo.get_job(job.id)
    events = repo.list_events(job.id)
    finish_events = [e for e in events if e.status in ("PARTIAL", "FAILED", "COMPLETED")]
    print("===== M5 BUDGET LIVE =====")
    import json
    print(json.dumps({
        "final_status": j.status.value,
        "finish_event_statuses": [e.status for e in finish_events],
        "stopped_reason": (j.checkpoint_ref or ""),
        "config_used": BudgetConfig().__dict__,
        "events_count": len(events),
    }, indent=2))
    verdict = "PASS" if j.status == JobStatus.PARTIAL else "FAIL"
    print(f"VERDICT: {verdict} (expected PARTIAL)")
    repo.close()
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
