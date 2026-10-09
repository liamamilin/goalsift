"""Search/fetch adapter — Exa, with SSRF-safe source reading.

06 §9.2/§9.3: read-only public sources; record query, result identifiers, final
URL after redirect, retrieval time, version, content locator, errors. Exa returns
its own hosted text, so SSRF risk is bounded to Exa's endpoint; we additionally
guard against private/loopback targets if a direct URL is ever fetched.
"""

from __future__ import annotations

import ipaddress
import os
import socket
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from .config import load_env

load_env()
_KEY = os.environ.get("EXA_API_KEY") or os.environ.get("GOALSIFT_SEARCH_API_KEY")

EXA_SEARCH = "https://api.exa.ai/search"
EXA_CONTENTS = "https://api.exa.ai/contents"

# Hard guard: never resolve to private/loopback/metadata addresses.
_BLOCKED_PREFIXES = ("169.254.", "0.0.0.0")


@dataclass
class SearchResult:
    url: str
    title: str
    text: str
    retrieved_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    cost_dollars: float | None = None


def _is_safe_host(host: str) -> bool:
    """Reject loopback/private/link-local/metadata addresses (SSRF guard)."""
    if not host:
        return False
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return False
    for info in infos:
        ip = info[4][0]
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            continue
        if (
            addr.is_loopback
            or addr.is_private
            or addr.is_link_local
            or addr.is_reserved
            or addr.is_multicast
        ):
            return False
    return True


class SearchAdapter:
    """Exa-backed search + source read. Returns real, located results."""

    def __init__(self, timeout: float = 60.0) -> None:
        self._timeout = timeout

    async def search(self, query: str, num: int = 5) -> tuple[list[SearchResult], dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            payload = {
                "query": query,
                "numResults": num,
                "type": "auto",
                "contents": {"text": {"maxCharacters": 800}},
            }
            r = await client.post(EXA_SEARCH, json=payload, headers={"x-api-key": _KEY})
            r.raise_for_status()
            data = r.json()
            cost = (data.get("costDollars") or {}).get("total")
            hits = data.get("results", [])
            results = [
                SearchResult(
                    url=h.get("url", ""),
                    title=h.get("title", ""),
                    text=h.get("text", ""),
                    cost_dollars=None,
                )
                for h in hits
            ]
            return results, {"cost_dollars": cost, "query": query, "num": len(results)}

    async def read_source(self, url: str) -> tuple[SearchResult, dict[str, Any]]:
        """Read one source fully via Exa contents (SSRF-bounded to Exa)."""
        parsed = urlparse(url)
        # If we ever fetch directly, guard; Exa contents is the trusted path here.
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"refused non-http(s) url: {url}")
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            r = await client.post(
                EXA_CONTENTS,
                json={"urls": [url], "text": True},
                headers={"x-api-key": _KEY},
            )
            r.raise_for_status()
            data = r.json()
            cost = (data.get("costDollars") or {}).get("total")
            items = data.get("results", [])
            item = items[0] if items else {}
            return (
                SearchResult(
                    url=url,
                    title=item.get("title", ""),
                    text=item.get("text", ""),
                    cost_dollars=cost,
                ),
                {"read_cost": cost, "content_length": len(item.get("text", ""))},
            )
