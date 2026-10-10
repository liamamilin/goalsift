"""Bounded source selection. Links are data, never tool instructions."""
from __future__ import annotations
import re
from urllib.parse import urlparse, urljoin


def github_repository(url: str) -> tuple[str, str] | None:
    try:
        p = urlparse(url)
        port = p.port
    except ValueError: return None
    parts = p.path.strip('/').split('/')
    if p.scheme != 'https' or p.hostname not in ('github.com', 'raw.githubusercontent.com') or p.username or p.password or port not in (None, 443): return None
    if len(parts) < 2: return None
    owner, repo = parts[:2]
    repo = repo.removesuffix('.git')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}', owner): return None
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', repo) or repo in ('.', '..'): return None
    # A GitHub issue or search is not a candidate repository document.
    if owner in ('search', 'topics', 'features', 'marketplace', 'settings'): return None
    return owner.lower(), repo.lower()


def source_identity(url: str) -> tuple:
    """Repository pages are sources for one candidate, not extra candidates."""
    repo = github_repository(url)
    if repo: return ('github', *repo)
    return ('url', url.rstrip('/'))


def related_document_links(base: str, texts: list[str]) -> list[str]:
    """Only literal document links on the candidate's own public host."""
    host = urlparse(base).hostname
    links = []
    for text in texts:
        matches = re.findall(r'https?://[^\s<>\[\]"\)]+', text)
        matches += re.findall(r'\]\((/[^\s\)]+)\)', text)
        for raw in matches:
            url = urljoin(base, raw.rstrip('.,;'))
            try:
                p = urlparse(url)
                port = p.port
            except ValueError: continue
            if (p.hostname != host or p.scheme not in ('http', 'https') or p.username or p.password
                    or port not in (None, 80, 443) or p.query or p.fragment or url == base): continue
            if not re.search(r'(?i)(?:license|licence|docs?|api|deploy|install|getting-started|quickstart)', p.path): continue
            if url not in links: links.append(url)
    return links[:2]


def document_category(path: str) -> str | None:
    name = path.rsplit('/', 1)[-1].lower()
    if name.startswith(('license', 'licence', 'copying')): return '许可原文'
    if name.startswith('readme'): return '接口与使用说明'
    if name in ('package.json', 'pyproject.toml', 'requirements.txt', 'cargo.toml', 'go.mod'): return '运行依赖'
    if name in ('dockerfile', 'docker-compose.yml', 'docker-compose.yaml', 'compose.yml', 'compose.yaml'): return '部署配置'
    return None


def focused_excerpt(text: str) -> str:
    """Keep the introduction plus a literal section on integration or use."""
    if len(text) <= 2400: return text
    match = re.search(r'(?im)^.{0,12}(?:installation|deployment|quick ?start|getting started|api|requirements|安装|部署|接口)\b', text[1100:])
    start = 1100 + match.start() if match else 1100
    return text[:1100] + '\n[省略；以下为原文片段]\n' + text[start:start + 1250]


def locate_quote(quote: str, cited: list, available: list) -> tuple:
    """Resolve only literal words in actually supplied, resource-bound sources.

    Prefer the model's valid citation. A wrong ID can be corrected only when
    one provided source uniquely contains the quotation. Whitespace may vary;
    the persisted quotation is always the exact original source substring.
    """
    if not quote.strip() or len(quote) > 1000: return None, ''
    pattern = re.compile(r'\s+'.join(re.escape(word) for word in quote.split()))
    def found(e):
        match = pattern.search(e.excerpt_or_summary)
        return (e, match.group(0)) if match else None
    supplied = {e.id for e in available}
    for e in cited:
        if e.id in supplied:
            hit = found(e)
            if hit: return hit
    matches = [hit for e in available if (hit := found(e))]
    return matches[0] if len(matches) == 1 else (None, '')
