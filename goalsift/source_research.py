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


def select_excerpt(text: str, focus: str = '') -> dict:
    """Select bounded literal spans; offsets refer to the saved source text.

    This is lexical selection, not an inference that a feature exists. Keep
    the old fallback for unrelated text and legacy pending checkpoints.
    """
    if len(text) <= 2400:
        ranges = [[0, len(text)]]
    else:
        clean_focus = re.sub(r'https?://\S+', '', focus[:3000]).lower()
        stop = {'the', 'and', 'for', 'with', 'that', 'from', 'this', 'must', 'should',
                'have', 'without', 'agent', 'agents', 'control', 'dashboard', 'system'}
        terms = set(re.findall(r'[a-z][a-z0-9_-]{2,39}', clean_focus)) - stop
        for trigger, words in (
            (r'状态|运行中|空闲|异常', 'status running idle error presence state'),
            (r'响应式|移动|窄屏|断点', 'responsive mobile viewport breakpoint media'),
            (r'许可|商用|开源', 'license licence permission commercial copying'),
            (r'接口|启动|暂停', 'api endpoint start pause stop resume'),
            (r'部署|安装|本地', 'install deployment docker setup requirements'),
            (r'任务', 'task queue pipeline'),
            (r'鉴权|登录', 'auth authentication login session'),
        ):
            if re.search(trigger, clean_focus) or terms.intersection(words.split()):
                terms.update(words.split())
                terms.update(trigger.split('|'))
        weights = {'status': 6, 'responsive': 6, 'license': 6, 'licence': 6,
                   '状态': 6, '响应式': 6, '许可': 6,
                   'idle': 4, 'running': 4, 'error': 4, 'pause': 4, 'viewport': 4, 'api': 4}
        patterns = [(re.compile(re.escape(t) if re.search(r'[\u4e00-\u9fff]', t) else r'(?i)(?<![\w-])' + re.escape(t) + r'(?:s)?(?![\w-])'), weights.get(t, 1))
                    for t in sorted(terms, key=lambda t: (-weights.get(t, 1), t))[:60]]
        candidates = set()
        primary = []
        for pattern, weight in patterns:
            for hit in list(pattern.finditer(text))[:20]:
                start = max(550, hit.start() - 200)
                span = (start, min(len(text), start + 550))
                candidates.add(span)
                primary.append((-weight, hit.start(), span))
        ranked = sorted(candidates, key=lambda span: (-sum(w for p, w in patterns if p.search(text[span[0]:span[1]])), span[0]))
        # Keep the first occurrence of the most specific term, then distinct
        # dense passages. A dense later section must not hide the first clue.
        if primary: ranked.insert(0, min(primary)[2])
        chosen = []
        for start, end in ranked:
            if any(start < b and a < end for a, b in chosen): continue
            chosen.append([start, end])
            if len(chosen) == 3: break
        if chosen:
            ranges = [[0, 550]] + sorted(chosen)
        else:
            match = re.search(r'(?im)^.{0,12}(?:installation|deployment|quick ?start|getting started|api|requirements|安装|部署|接口)\b', text[1100:])
            start = 1100 + match.start() if match else 1100
            ranges = [[0, 1100], [start, min(len(text), start + 1250)]]
    excerpt = '\n[省略；以下为原文片段]\n'.join(text[a:b] for a, b in ranges)
    return {'text': excerpt, 'excerpt_ranges': ranges, 'stored_characters': len(text),
            'supplied_characters': sum(b-a for a, b in ranges), 'is_partial': excerpt != text}


def focused_excerpt(text: str) -> str:
    return select_excerpt(text)['text']


def locate_quote(quote: str, cited: list, available: list, supplied_ranges: dict | None = None) -> tuple:
    """Resolve only literal words in actually supplied, resource-bound sources.

    Prefer the model's valid citation. A wrong ID can be corrected only when
    one provided source uniquely contains the quotation. Whitespace may vary;
    the persisted quotation is always the exact original source substring.
    """
    if not quote.strip() or len(quote) > 1000: return None, ''
    pattern = re.compile(r'\s+'.join(re.escape(word) for word in quote.split()))
    def found(e):
        for match in pattern.finditer(e.excerpt_or_summary):
            if supplied_ranges is None or any(0 <= a <= match.start() and match.end() <= b <= len(e.excerpt_or_summary)
                    for a, b in supplied_ranges.get(e.id, [])):
                return e, match.group(0)
        return None
    supplied = {e.id for e in available}
    for e in cited:
        if e.id in supplied:
            hit = found(e)
            if hit: return hit
    matches = [hit for e in available if (hit := found(e))]
    return matches[0] if len(matches) == 1 else (None, '')
