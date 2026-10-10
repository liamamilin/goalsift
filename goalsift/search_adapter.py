"""Bounded read-only Exa API access; public source URLs only."""
from __future__ import annotations
import os
import asyncio
import ipaddress
import socket
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse
import httpx
from .config import load_env
from .security import redact_secrets
load_env()
EXA_SEARCH = 'https://api.exa.ai/search'
EXA_CONTENTS = 'https://api.exa.ai/contents'

@dataclass
class SearchResult:
    url: str
    title: str
    text: str
    retrieved_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    cost_dollars: float | None = None
    version: str | None = None

class SearchAdapter:
    # Reserve a conservative ceiling before each request; actual costs come from costDollars.
    search_reservation = 0.05
    read_reservation = 0.02

    def __init__(self, timeout: float = 45.0):
        self._timeout = timeout
        self.key = os.environ.get('GOALSIFT_SEARCH_API_KEY') or os.environ.get('EXA_API_KEY')

    def validate_config(self):
        if (os.environ.get('GOALSIFT_SEARCH_PROVIDER') or 'exa') != 'exa':
            raise ValueError('当前搜索适配器支持 Exa；请设置 GOALSIFT_SEARCH_PROVIDER=exa')
        if not self.key: raise ValueError('缺少搜索 API key，请配置服务端 .env')

    async def _post(self, url: str, payload: dict):
        self.validate_config()
        async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=False) as client:
            async with client.stream('POST', url, json=payload, headers={'x-api-key': self.key}) as response:
                response.raise_for_status()
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > 2_000_000: raise ValueError('搜索响应超过 2 MB 限制')
        import json
        return json.loads(body)

    async def _public_dns(self, host: str) -> list[str]:
        """Fixed HTTPS resolver for VPN fake-IP DNS, with validation still enabled.

        Only source hostnames are sent. Exa, rather than this computer, fetches
        sources; a local VPN route in 198.18/15 is not the source's address.
        https://developers.google.com/speed/public-dns/docs/doh/json
        """
        async with httpx.AsyncClient(timeout=8, follow_redirects=False) as client:
            async def query(kind):
                async with client.stream('GET', 'https://dns.google/resolve',
                    params={'name': host, 'type': kind, 'edns_client_subnet': '0.0.0.0/0'}) as response:
                    response.raise_for_status()
                    data = bytearray()
                    async for chunk in response.aiter_bytes():
                        data.extend(chunk)
                        if len(data) > 32000: raise ValueError('DNS response too large')
                import json
                answer = json.loads(data)
                if answer.get('Status') != 0 or answer.get('TC'): raise ValueError('DNS resolution failed')
                return [r['data'] for r in answer.get('Answer', []) if r.get('type') in (1, 28)]
            records = await asyncio.gather(query('A'), query('AAAA'))
            return records[0] + records[1]

    async def _public(self, url: str):
        try:
            parsed = urlparse(url)
            host = (parsed.hostname or '').rstrip('.').lower()
            if parsed.scheme not in ('http', 'https') or not host or parsed.username or parsed.password:
                return False
            if parsed.port not in (None, 80, 443): return False
            if '.' not in host or host.endswith(('.localhost', '.local', '.internal')): return False
            infos = await asyncio.to_thread(socket.getaddrinfo, host, None)
            addresses = [ipaddress.ip_address(i[4][0]) for i in infos]
            fake_range = ipaddress.ip_network('198.18.0.0/15')
            if addresses and all(a.version == 4 and a in fake_range for a in addresses):
                # Never override ordinary private/loopback answers. This exception
                # applies solely to Exa's delegated fetch with confirmed public DNS.
                addresses = [ipaddress.ip_address(a) for a in await self._public_dns(host)]
            return bool(addresses) and all(a.is_global and not a.is_multicast for a in addresses)
        except (ValueError, OSError, httpx.HTTPError):
            return False

    async def search(self, query: str, num: int = 4) -> tuple[list[SearchResult], dict[str, Any]]:
        data = await self._post(EXA_SEARCH, {'query': query[:1500], 'numResults': min(max(num, 1), 8),
            'type': 'auto', 'contents': {'text': {'maxCharacters': 6000}}})
        results = []
        rejected = 0
        for h in data.get('results', []):
            url = h.get('url', '')
            if not await self._public(url):
                rejected += 1
                continue
            results.append(SearchResult(url=url, title=redact_secrets(h.get('title', '')),
                text=redact_secrets(h.get('text') or '')[:12000], version=h.get('publishedDate')))
        cost = (data.get('costDollars') or {}).get('total')
        return results, {'cost_dollars': cost, 'query': query, 'num': len(results),
                         'rejected_urls': rejected, 'request_id': data.get('requestId')}

    async def read_source(self, url: str) -> tuple[SearchResult, dict[str, Any]]:
        if not await self._public(url): raise ValueError('拒绝访问非公共 HTTP(S) 来源')
        data = await self._post(EXA_CONTENTS, {'urls': [url], 'text': {'maxCharacters': 12000}})
        items = data.get('results') or []
        if not items or not items[0].get('text'): raise ValueError('来源未返回可读取内容')
        item = items[0]
        final_url = item.get('url') or url
        if not await self._public(final_url): raise ValueError('来源重定向到受限地址')
        cost = (data.get('costDollars') or {}).get('total')
        text = redact_secrets(item['text'])[:12000]
        return SearchResult(url=final_url, title=redact_secrets(item.get('title', '')),
            text=text, cost_dollars=cost, version=item.get('publishedDate')), {
                'read_cost': cost, 'content_length': len(text), 'request_id': data.get('requestId')}
