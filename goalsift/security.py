"""Security boundary helpers (06 §9.3).

- SSRF guard for any direct URL fetch (loopback/private/link-local/metadata blocked)
- Prompt-injection boundary: external content is data, never system instructions
- Secret redaction for logs/events/exports
"""

from __future__ import annotations

import ipaddress
import os
import re
import socket
from urllib.parse import urlparse

__all__ = [
    "is_safe_url",
    "redact_secrets",
    "external_content_as_data",
]

# Patterns that must never appear unredacted in logs/exports.
_SECRET_PATTERNS = [
    re.compile(r"(sk-[A-Za-z0-9]{8,})"),           # openai/deepseek style
    re.compile(r"(sk-ant-[A-Za-z0-9]{8,})"),       # anthropic style
    re.compile(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", re.I),  # uuid api keys
    re.compile(r"(Bearer\s+[A-Za-z0-9\.\-_]{8,})", re.I),
]
_REDACTED = "[REDACTED]"


def redact_secrets(text: str) -> str:
    """Replace anything that looks like an API key/bearer token with [REDACTED]."""
    if not text:
        return text
    out = text
    for key in ('GOALSIFT_LLM_API_KEY', 'DEEPSEEK_API_KEY', 'GOALSIFT_SEARCH_API_KEY', 'EXA_API_KEY'):
        secret = os.environ.get(key, '')
        if len(secret) >= 8: out = out.replace(secret, _REDACTED)
    for pat in _SECRET_PATTERNS:
        out = pat.sub(_REDACTED, out)
    return out


def is_safe_url(url: str, *, allow_private: bool = False) -> bool:
    """SSRF guard. Reject non-http(s), and any host resolving to loopback /
    private / link-local / reserved / multicast / cloud-metadata addresses."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = parsed.hostname
    if not host:
        return False
    if allow_private:
        return True
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
        if (addr.is_loopback or addr.is_private or addr.is_link_local
                or addr.is_reserved or addr.is_multicast
                or str(addr) == "169.254.169.254"):
            return False
    return True


def external_content_as_data(content: str) -> str:
    """Wrap external content so it is treated as untrusted DATA, not instructions.

    The model receives external text only inside a clearly-delimited data block,
    never as a system prompt. Any 'ignore previous instructions' inside it has no
    operational authority (04 §6.3, 06 §9.3)."""
    return (
        "<<<UNTRUSTED_EXTERNAL_DATA_BEGIN>>>\n"
        f"{content}\n"
        "<<<UNTRUSTED_EXTERNAL_DATA_END>>>"
    )
