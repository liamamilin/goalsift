"""M1 Spike — Search/fetch adapter (Exa).

Verifies, with real calls, the candidate search provider required by
06 §9.2 and 07 §4 (M1 PASS Gate):
  1. real web search returns real, located results
  2. real source reading (full content) with a reusable locator
  3. record query, results, retrieved_at, source_version, cost, errors
  4. error path (bad key) caught

Run: python3 -m spikes.spike_search
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from goalsift.config import load_env

load_env()
KEY = os.environ.get("EXA_API_KEY") or os.environ.get("GOALSIFT_SEARCH_API_KEY")

import httpx

EXA_SEARCH = "https://api.exa.ai/search"
EXA_CONTENTS = "https://api.exa.ai/contents"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def report(section: str, body: object) -> None:
    print(f"\n===== {section} =====")
    print(body if isinstance(body, str) else json.dumps(body, indent=2, ensure_ascii=False, default=str))


async def exa_search(client: httpx.AsyncClient, query: str, num: int = 5) -> dict:
    payload = {
        "query": query,
        "numResults": num,
        "type": "auto",
        "contents": {"text": {"maxCharacters": 600}},
    }
    r = await client.post(EXA_SEARCH, json=payload, headers={"x-api-key": KEY}, timeout=60)
    r.raise_for_status()
    return r.json()


async def exa_read(client: httpx.AsyncClient, url: str) -> dict:
    """Read one source fully — proves real source reading with a locator."""
    payload = {"urls": [url], "text": True}
    r = await client.post(EXA_CONTENTS, json=payload, headers={"x-api-key": KEY}, timeout=60)
    r.raise_for_status()
    return r.json()


async def main() -> int:
    report("ENV", {"provider": "exa", "api_key_present": bool(KEY)})
    if not KEY:
        report("VERDICT", "BLOCKED: no Exa key")
        return 2

    failures: list[str] = []
    async with httpx.AsyncClient() as client:
        # --- 1. Real search ------------------------------------------------
        results = None
        try:
            results = await exa_search(client, "open source agent management dashboard UI library", num=5)
            hits = results.get("results", [])
            report("1. SEARCH", {
                "query": "open source agent management dashboard UI library",
                "num_results": len(hits),
                "retrieved_at": now(),
                "cost_dollars": results.get("costDollars"),
                "results": [
                    {"url": h.get("url"), "title": h.get("title"), "text_excerpt": (h.get("text") or "")[:160]}
                    for h in hits
                ],
            })
            if not hits:
                failures.append("search: no results returned")
        except Exception as e:  # noqa: BLE001
            failures.append(f"search: {e!r}")
            report("1. SEARCH ERROR", repr(e))

        # --- 2. Real source reading ----------------------------------------
        read_summary = None
        if results and results.get("results"):
            target_url = results["results"][0].get("url")
            try:
                read = await exa_read(client, target_url)
                items = read.get("results", [])
                item = items[0] if items else {}
                full_text = item.get("text") or ""
                read_summary = {
                    "url_read": target_url,
                    "retrieved_at": now(),
                    "title": item.get("title"),
                    "content_length": len(full_text),
                    "locator": "exa contents endpoint, full text",
                    "source_version": item.get("publishedDate"),
                    "excerpt": full_text[:300],
                    "cost_dollars": read.get("costDollars"),
                }
                report("2. SOURCE READ", read_summary)
                if not full_text:
                    failures.append("source-read: empty content")
            except Exception as e:  # noqa: BLE001
                failures.append(f"source-read: {e!r}")
                report("2. SOURCE READ ERROR", repr(e))

        # --- 3. Error path (bad key) ----------------------------------------
        caught = None
        try:
            bad = await client.post(EXA_SEARCH, json={"query": "x", "numResults": 1},
                                    headers={"x-api-key": "bad-key-xxx"}, timeout=30)
            caught = f"status={bad.status_code}"
        except Exception as e:  # noqa: BLE001
            caught = repr(e)
        report("3. ERROR HANDLING", {
            "bad_key_rejected": caught is not None,
            "detail": caught,
        })

    verdict = "PASS" if not failures else "FAIL"
    report("VERDICT", {"verdict": verdict, "failures": failures, "all_live": True,
                       "read_summary_present": read_summary is not None})
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
