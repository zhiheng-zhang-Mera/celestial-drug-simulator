"""Offline-first drug name search with an optional Mayo cloud update.

Design boundaries:

* The embedded `data/pharmacopoeia/index.json` always works offline. It is built
  from the curated profiles, the interaction catalog and reviewed aliases.
* Mayo is the only cloud provider (per product requirement). Requests carry the
  drug name only — never dose, physiology, genetics or identity. The site blocks
  automated access from some networks (HTTP 403); that is reported as a real
  error and the local index stays usable.
* Successful cloud responses are cached under `data/cache/pharmacopoeia/` with
  URL, retrieval time and a content hash. The cache is runtime state, not a
  source of clinical claims.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / 'data' / 'pharmacopoeia' / 'index.json'
CACHE_DIR = ROOT / 'data' / 'cache' / 'pharmacopoeia'

MAYO_SEARCH = 'https://www.mayoclinic.org/search/drugs-supplements?q={query}'
SOURCE_LABELS = {
    'local_profile': '本地药典 · 来源档案',
    'local_evidence': '本地药典 · 文献关联',
    'local_index': '本地药典',
    'mayo_cache': '本地缓存 · Mayo',
}
USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
)


class PharmacopoeiaError(RuntimeError):
    """Readable failure with a stable code for the UI."""

    def __init__(self, code, message, status=None):
        super().__init__(message)
        self.code = code
        self.status = status


class _PageParser(HTMLParser):
    """Small extractor: title, meta description, headings, paragraph text and links."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ''
        self.meta_description = ''
        self.sections = []
        self.links = []
        self._heading = None
        self._buffer = []
        self._in_title = False
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('script', 'style'):
            self._skip += 1
            return
        if tag == 'title':
            self._in_title = True
        elif tag == 'a' and attrs.get('href'):
            self.links.append(attrs['href'])
        elif tag == 'meta' and attrs.get('name', '').lower() in ('description', 'og:description'):
            self.meta_description = (attrs.get('content') or '').strip()
        elif tag in ('h1', 'h2', 'h3'):
            self._flush()
            self._heading = ''
        elif tag in ('p', 'li') and not self._heading:
            self._buffer.append('')

    def handle_endtag(self, tag):
        if tag in ('script', 'style') and self._skip:
            self._skip -= 1
            return
        if tag == 'title':
            self._in_title = False
        elif tag in ('h1', 'h2', 'h3') and self._heading is not None:
            heading = _clean(self._heading)
            if heading:
                self.sections.append({'heading': heading, 'text': ''})
            self._heading = None
        elif tag in ('p', 'li'):
            self._flush()

    def handle_data(self, data):
        if self._skip:
            return
        if self._in_title:
            self.title += data
        elif self._heading is not None:
            self._heading += data
        else:
            self._buffer.append(data)

    def _flush(self):
        if not self._buffer:
            return
        text = _clean(''.join(self._buffer))
        self._buffer = []
        if not text:
            return
        if self.sections:
            existing = self.sections[-1]['text']
            self.sections[-1]['text'] = (existing + ' ' + text).strip()[:1200]
        else:
            self.sections.append({'heading': '摘要', 'text': text[:1200]})


def _clean(text):
    return re.sub(r'\s+', ' ', text or '').strip()


def normalize(text):
    return _clean(str(text or '')).casefold()


def search_url(name):
    return MAYO_SEARCH.format(query=quote(_clean(name)))


def _default_transport(url, timeout):
    request = Request(url, headers={
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'en-US,en;q=0.9',
    })
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode('utf-8', 'replace')
    except HTTPError as error:
        return error.code, ''
    except URLError as error:
        raise PharmacopoeiaError('MAYO_UNREACHABLE', '无法连接 Mayo：' + str(error.reason)) from error
    except TimeoutError as error:
        raise PharmacopoeiaError('MAYO_TIMEOUT', 'Mayo 请求超时。') from error


def load_entries(cache_dir=None, include_cache=True):
    """Embedded entries plus (optionally) cached Mayo records."""
    cache_dir = Path(cache_dir) if cache_dir else CACHE_DIR
    entries = []
    if INDEX_PATH.exists():
        payload = json.loads(INDEX_PATH.read_text(encoding='utf-8'))
        entries.extend(payload.get('entries', []))
    if include_cache and cache_dir.is_dir():
        known = {entry['identity'] for entry in entries}
        for path in sorted(cache_dir.glob('*.json')):
            try:
                record = json.loads(path.read_text(encoding='utf-8'))
            except (OSError, ValueError):
                continue
            identity = str(record.get('identity') or path.stem)
            if identity in known:
                continue
            names = [name for name in (record.get('query'), record.get('title')) if name]
            if not names:
                continue
            entries.append({
                'identity': identity,
                'display': record.get('title') or record.get('query') or identity,
                'names': list(dict.fromkeys(names)),
                'source': 'mayo_cache',
                'status': 'mayo_cache',
                'has_profile': False,
                'has_label_cache': False,
                'catalog_present': False,
                'note': 'Mayo 缓存记录 · 仅名称与摘要，未做临床校验',
                'label_url': record.get('url', ''),
                'cached_at': record.get('retrieved_at'),
            })
    return entries


def search(query, entries=None, limit=8):
    query = _clean(query)
    if not query:
        return []
    key = query.casefold()
    scored = []
    for entry in entries if entries is not None else load_entries():
        best = None
        for name in entry.get('names', []):
            name_key = str(name).casefold()
            if name_key == key:
                best = 0 if best is None else min(best, 0)
            elif name_key.startswith(key):
                best = 1 if best is None else min(best, 1)
            elif key in name_key:
                best = 2 if best is None else min(best, 2)
        if best is not None:
            scored.append((best, entry.get('display', ''), entry))
    scored.sort(key=lambda item: (item[0], item[1]))
    return [entry for _score, _display, entry in scored[:limit]]


def resolve(name, entries=None):
    query = _clean(name)
    if not query:
        return None
    exact = []
    for entry in entries if entries is not None else load_entries():
        for candidate in entry.get('names', []):
            if str(candidate).casefold() == query.casefold():
                exact.append(entry)
                break
    if len(exact) == 1:
        return exact[0]
    matches = search(query, entries=entries, limit=2)
    return matches[0] if len(matches) == 1 else None


def source_label(entry):
    return SOURCE_LABELS.get(entry.get('source', ''), entry.get('source', '本地药典'))


def cache_path(identity, cache_dir=None):
    key = _clean(identity) or 'entry'
    slug = re.sub(r'[^a-z0-9._-]+', '-', key.casefold()).strip('-') or 'entry'
    return (Path(cache_dir) if cache_dir else CACHE_DIR) / (slug + '.json')


def read_cache(identity, cache_dir=None):
    path = cache_path(identity, cache_dir)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def write_cache(record, cache_dir=None):
    path = cache_path(record.get('identity') or record.get('query'), cache_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return path


def parse_page(html, url=''):
    parser = _PageParser()
    parser.feed(html or '')
    title = _clean(parser.title) or ''
    excerpt = _clean(parser.meta_description)
    sections = []
    for section in parser.sections:
        text = _clean(section.get('text'))
        if text and text.casefold() != title.casefold():
            sections.append({'heading': section.get('heading') or '摘要', 'text': text})
    if not sections and excerpt:
        sections = [{'heading': '摘要', 'text': excerpt}]
    return {
        'url': url,
        'title': title,
        'excerpt': excerpt,
        'sections': sections[:10],
        'links': parser.links,
    }


def _drug_detail_link(links, base_url):
    """Pick the first Mayo drug monograph link from a search result page."""
    for href in links:
        target = urljoin(base_url, href)
        if '/drugs-supplements/' in target and '/description/drg-' in target:
            return target
    return None


class MayoClient:
    """Fetch a Mayo drug page and cache the parsed summary.

    `transport(url, timeout) -> (status, html)` is injectable for tests.
    """

    def __init__(self, transport=None, timeout=12, cache_dir=None):
        self.transport = transport or _default_transport
        self.timeout = timeout
        self.cache_dir = Path(cache_dir) if cache_dir else CACHE_DIR

    def update(self, query, identity=None):
        query = _clean(query)
        if not query:
            raise PharmacopoeiaError('MAYO_QUERY_EMPTY', '请先输入药物名称。')
        search_page = search_url(query)
        status, html = self.transport(search_page, self.timeout)
        if status == 403:
            raise PharmacopoeiaError('MAYO_FORBIDDEN', 'Mayo 拒绝自动访问（HTTP 403）；本地药典仍可用。', status=403)
        if status >= 400:
            raise PharmacopoeiaError('MAYO_HTTP_ERROR', f'Mayo 返回 HTTP {status}；本地药典仍可用。', status=status)
        page = parse_page(html, search_page)
        page_url = search_page
        detail_url = _drug_detail_link(page.get('links', []), search_page)
        if detail_url:
            detail_status, detail_html = self.transport(detail_url, self.timeout)
            if detail_status < 400 and detail_html:
                detail_page = parse_page(detail_html, detail_url)
                if detail_page['title'] or detail_page['sections']:
                    page = detail_page
                    page_url = detail_url
        if not page['title'] and not page['sections']:
            raise PharmacopoeiaError('MAYO_PARSE_EMPTY', 'Mayo 页面没有可解析的药物摘要。', status=status)
        record = {
            'schema': 1,
            'identity': _clean(identity) or _slug(query),
            'query': query,
            'url': page_url,
            'search_url': search_page,
            'status': 'mayo_cache',
            'retrieved_at': datetime.now(timezone.utc).isoformat(),
            'title': page['title'] or query,
            'excerpt': page['excerpt'],
            'sections': page['sections'],
            'content_sha256': hashlib.sha256((html or '').encode('utf-8')).hexdigest(),
            'not_clinically_validated': True,
        }
        write_cache(record, self.cache_dir)
        return record


def _slug(text):
    slug = re.sub(r'[^a-z0-9]+', '-', normalize(text)).strip('-')
    return slug or 'entry'
