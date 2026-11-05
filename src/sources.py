"""Bounded public-source adapters. No patient parameters accepted or transmitted."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / 'data' / 'cache' / 'sources.json'
MAYO_URL = 'https://www.mayoclinic.org/drugs-supplements/atomoxetine-oral-route/description/drg-20066904'
URLS = {
    'diplotypes': 'https://api.cpicpgx.org/v1/diplotype?genesymbol=eq.CYP2D6&diplotype=in.(*1/*1,*1/*4,*4/*4)&select=genesymbol,diplotype,function1,function2,totalactivityscore,generesult',
    'pair': 'https://api.cpicpgx.org/v1/pair?genesymbol=eq.CYP2D6&drugid=eq.RxNorm:38400',
}

def mayo_facts(html):
    class Text(HTMLParser):
        def __init__(self): super().__init__(); self.parts = []
        def handle_data(self, data): self.parts.append(data)
    parser = Text(); parser.feed(html)
    text = ' '.join(' '.join(parser.parts).split())
    if 'Atomoxetine (oral route)' not in text or 'Description' not in text:
        raise ValueError('Mayo page identity/section missing')
    description = text.split('Description', 1)[1].split('Before Using', 1)[0]
    if 'selective norepinephrine reuptake inhibitors' not in description:
        raise ValueError('Mayo mechanism fact unavailable; parser requires review')
    return {'compound_id': 'atomoxetine', 'route': 'oral',
            'mechanism_class': 'selective norepinephrine reuptake inhibitor',
            'source_section': 'Description', 'extraction_status': 'FACT_EXTRACTED_REVIEW_PENDING'}

def digest(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()

def fetch(url):
    # URLs are fixed constants, never derived from a genetic/profile input.
    request = Request(url, headers={'User-Agent': 'CelestialDrugResearch/0.4', 'Accept': 'application/json,text/html'})
    with urlopen(request, timeout=15) as response:
        if response.url.split('/')[2] != url.split('/')[2]: raise ValueError('Unexpected source redirect host')
        body = response.read(2_000_001)
        if len(body) > 2_000_000: raise ValueError('Source response exceeds limit')
        return body

def refresh_sources(path=CACHE, transport=fetch):
    snapshot = {'schema': 1, 'retrieved_at': datetime.now(timezone.utc).isoformat()}
    for key, url in URLS.items():
        try:
            raw = transport(url)
            data = json.loads(raw)
            if not isinstance(data, list) or not data: raise ValueError('Empty or malformed source')
            snapshot[key] = {'status': 'FETCHED', 'url': url, 'data': data, 'data_sha256': digest(data),
                             'response_sha256': sha256(raw).hexdigest(), 'license_review': 'PENDING'}
        except Exception as exc:
            snapshot[key] = {'status': 'FETCH_FAILED', 'url': url, 'error': str(exc)[:300]}
    try:
        raw = transport(MAYO_URL)
        text = raw.decode('utf-8', errors='replace')
        facts = mayo_facts(text)
        # Store transport/identity metadata, never republish the copyrighted full article.
        snapshot['mayo'] = {'status': 'FACTS_FETCHED', 'url': MAYO_URL, 'facts': facts,
                            'facts_sha256': digest(facts),
                            'response_sha256': sha256(raw).hexdigest(), 'content_import': 'NOT_LICENSED',
                            'role': 'educational reference only; not numeric model input'}
    except Exception as exc:
        snapshot['mayo'] = {'status': 'FETCH_FAILED', 'url': MAYO_URL, 'error': str(exc)[:300]}
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)
    return snapshot

def load_snapshot(path=CACHE):
    try: snapshot = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc: raise ValueError('缺少可读来源快照；请刷新公共资料。') from exc
    validate_snapshot(snapshot)
    return snapshot

def validate_snapshot(snapshot):
    try:
        if not isinstance(snapshot, dict) or snapshot.get('schema') != 1: raise ValueError('无效快照版本。')
        timestamp = datetime.fromisoformat(snapshot['retrieved_at'])
        age = (datetime.now(timezone.utc) - timestamp).total_seconds()
        if not 0 <= age <= 30 * 86400: raise ValueError('来源快照过期或时间无效，请刷新。')
        for key, url in URLS.items():
            record = snapshot[key]
            if not isinstance(record, dict): raise ValueError('来源记录无效。')
            if record['status'] != 'FETCHED' or record['url'] != url or record['data_sha256'] != digest(record['data']):
                raise ValueError('来源失败或完整性校验失败。')
            rows = record['data']
            if not isinstance(rows, list) or not rows or any(not isinstance(row, dict) for row in rows):
                raise ValueError('来源行结构无效。')
        diplotypes = snapshot['diplotypes']['data']
        required = ('genesymbol', 'diplotype', 'function1', 'function2', 'totalactivityscore', 'generesult')
        if any(any(not isinstance(row.get(key), str) or not row[key] for key in required) for row in diplotypes):
            raise ValueError('双倍型来源字段缺失。')
        pair = snapshot['pair']['data']
        if len(pair) != 1 or pair[0]['genesymbol'] != 'CYP2D6' or pair[0]['drugid'] != 'RxNorm:38400' or pair[0]['removed'] is not False or pair[0]['usedforrecommendation'] is not True:
            raise ValueError('CPIC 基因药物机制关系不匹配。')
    except (KeyError, TypeError, OverflowError) as exc: raise ValueError('来源快照结构无效。') from exc
