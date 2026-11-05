"""Small route-specific public-label library; no patient data enters requests.

Online identity and section checks precede persistence. Mechanism observations are
qualitative evidence, never an admission to a concentration or dosing model.
"""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import tempfile
from urllib.parse import urlencode, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import UUID


ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / 'data' / 'cache' / 'drug_labels'
API_URL = 'https://api.fda.gov/drug/label.json'
MAX_RESPONSE_BYTES = 1_000_000
CACHE_MAX_BYTES = 64_000
TIMEOUT_SECONDS = 8
STALE_DAYS = 30
_LIBRARY = json.loads((ROOT / 'data' / 'drug_profiles.json').read_text(encoding='utf-8'))
_PROFILES = _LIBRARY['profiles']
_FACT_RULES = {
    'estradiol': ('estrogen_partial_cyp3a4_metabolism',
                  r'estrogens are metabolized partially by cytochrome p450 3a4\s*\(cyp3a4\)',
                  ('clinical_pharmacology', 'drug_interactions')),
    'bicalutamide': ('r_bicalutamide_cyp3a4_inhibition',
                     r'r-bicalutamide is an inhibitor of cyp\s*3a4',
                     ('drug_interactions',)),
}
_PAYLOAD_KEYS = {'compound_id', 'lookup_name', 'route', 'formulation', 'url', 'set_id',
                 'retrieved_at', 'effective_time', 'response_sha256', 'fact_evidence'}


def _digest(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             allow_nan=False).encode()).hexdigest()


def resolve_name(name):
    """Resolve only explicit exact aliases, never esters, combinations or substrings."""
    if not isinstance(name, str):
        return None
    normalized = name.strip().casefold()
    for compound_id, profile in _PROFILES.items():
        if normalized in {n.casefold() for n in profile['aliases'] + [profile['name']]}:
            return compound_id
    return None


def profile_for(compound_id, route='oral'):
    """Curated display defaults only; unknown identities return None."""
    if not isinstance(compound_id, str) or compound_id not in _PROFILES:
        return None
    result = deepcopy(_PROFILES[compound_id])
    result['compound_id'] = compound_id
    if route != result['route']:
        result.update(route=route, formulation='未建立此给药途径的剂型参数', half_life_h=None,
                      population='此给药途径资料不足', facts=[], source_url='', source_section='',
                      parameter_note='给药途径不匹配：此途径没有已整理的参数，不能沿用口服参数。')
    return result


def _query_url(compound_id):
    # Only whitelisted public English ingredient names reach the HTTP adapter.
    name = _PROFILES[compound_id]['lookup_name']
    return API_URL + '?' + urlencode({
        'search': f'openfda.generic_name.exact:"{name}" AND openfda.route.exact:"ORAL"',
        'limit': 1, 'sort': 'effective_time:desc'})


def _validate_api_url(url):
    parsed = urlparse(url)
    if (parsed.scheme != 'https' or parsed.netloc != 'api.fda.gov'
            or parsed.path != '/drug/label.json' or parsed.fragment):
        raise ValueError('非授权公共标签地址')


class _OfficialRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validate_api_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url):
    """Bounded HTTPS fetch; redirects are checked before any redirected request."""
    _validate_api_url(url)
    request = Request(url, headers={'User-Agent': 'CelestialDrugResearch/0.5',
                                    'Accept': 'application/json'})
    with build_opener(_OfficialRedirect()).open(request, timeout=TIMEOUT_SECONDS) as response:
        _validate_api_url(response.geturl())
        raw = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError('标签响应超过大小上限')
    return raw


def _text(label, section):
    value = label.get(section, [])
    if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
        raise ValueError('标签段落结构无效')
    return ' '.join(' '.join(value).split())


def _fact_evidence(compound_id, label):
    rule = _FACT_RULES.get(compound_id)
    if not rule:
        return []
    fact, pattern, sections = rule
    for section in sections:
        text = _text(label, section)
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return [{'fact': fact, 'section': section, 'excerpt': match.group(),
                     'section_sha256': sha256(text.encode()).hexdigest()}]
    return []


def _parse_response(compound_id, raw):
    if not isinstance(raw, bytes) or len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError('标签响应无效或过大')
    data = json.loads(raw)
    results = data.get('results') if isinstance(data, dict) else None
    if not isinstance(results, list) or len(results) != 1 or not isinstance(results[0], dict):
        raise ValueError('未找到唯一标签候选')
    label = results[0]
    identity = label.get('openfda')
    if not isinstance(identity, dict):
        raise ValueError('缺少可校验的标签成分身份')
    name = _PROFILES[compound_id]['lookup_name']
    for field in ('generic_name', 'substance_name'):
        values = identity.get(field)
        if (not isinstance(values, list) or not values
                or any(not isinstance(v, str) for v in values)
                or {v.strip().upper() for v in values} != {name}):
            raise ValueError('标签成分不完全匹配或属于复方')
    if identity.get('route') != ['ORAL']:
        raise ValueError('标签不是已支持的单一口服途径')
    description = _text(label, 'description')
    if not re.search(r'\btablets?\b', description, re.IGNORECASE):
        raise ValueError('标签口服片剂身份未确认')
    set_id = str(UUID(label['set_id']))
    effective = label.get('effective_time', '')
    if not isinstance(effective, str) or not re.fullmatch(r'\d{8}', effective):
        raise ValueError('标签版本日期无效')
    datetime.strptime(effective, '%Y%m%d')
    return {'compound_id': compound_id, 'lookup_name': name, 'route': 'oral',
            'formulation': 'oral tablet', 'set_id': set_id,
            'url': 'https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=' + set_id,
            'effective_time': effective, 'retrieved_at': datetime.now(timezone.utc).isoformat(),
            'response_sha256': sha256(raw).hexdigest(),
            'fact_evidence': _fact_evidence(compound_id, label)}


def _age(timestamp):
    parsed = datetime.fromisoformat(timestamp)
    if parsed.tzinfo is None:
        raise ValueError('缓存时间没有时区')
    seconds = (datetime.now(timezone.utc) - parsed).total_seconds()
    if seconds < -300:
        raise ValueError('缓存时间在未来')
    return max(0, seconds / 86400)


def _hash_valid(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def _validate_payload(compound_id, payload):
    if not isinstance(payload, dict) or set(payload) != _PAYLOAD_KEYS:
        raise ValueError('缓存字段结构无效')
    if (payload['compound_id'] != compound_id or payload['lookup_name'] != _PROFILES[compound_id]['lookup_name']
            or payload['route'] != 'oral' or payload['formulation'] != 'oral tablet'):
        raise ValueError('缓存成分或途径不匹配')
    set_id = str(UUID(payload['set_id']))
    if payload['url'] != 'https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=' + set_id:
        raise ValueError('缓存来源地址不匹配')
    _age(payload['retrieved_at'])
    datetime.strptime(payload['effective_time'], '%Y%m%d')
    if not _hash_valid(payload['response_sha256']):
        raise ValueError('缓存响应摘要无效')
    evidence = payload['fact_evidence']
    if not isinstance(evidence, list) or len(evidence) > 1:
        raise ValueError('缓存事实结构无效')
    for fact in evidence:
        rule = _FACT_RULES.get(compound_id)
        if (not rule or not isinstance(fact, dict)
                or set(fact) != {'fact', 'section', 'excerpt', 'section_sha256'}
                or fact['fact'] != rule[0] or fact['section'] not in rule[2]
                or not isinstance(fact['excerpt'], str)
                or re.fullmatch(rule[1], fact['excerpt'], re.IGNORECASE) is None
                or not _hash_valid(fact['section_sha256'])):
            raise ValueError('缓存事实与支持段落不匹配')


def _read_cache(compound_id, path):
    if path.is_symlink() or path.stat().st_size > CACHE_MAX_BYTES:
        raise ValueError('缓存文件无效或过大')
    envelope = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(envelope, dict) or set(envelope) != {'schema', 'content_sha256', 'payload'}:
        raise ValueError('缓存封套无效')
    if (type(envelope['schema']) is not int or envelope['schema'] != 1
            or envelope['content_sha256'] != _digest(envelope['payload'])):
        raise ValueError('缓存摘要校验失败')
    _validate_payload(compound_id, envelope['payload'])
    return envelope['payload']


def _write_cache(compound_id, path, payload):
    _validate_payload(compound_id, payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError('拒绝覆盖链接缓存')
    envelope = {'schema': 1, 'content_sha256': _digest(payload), 'payload': payload}
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix=compound_id + '-', suffix='.tmp', delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(envelope, handle, ensure_ascii=False, indent=2, allow_nan=False)
        temporary.replace(path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _record(compound_id, payload, status):
    age = _age(payload['retrieved_at'])
    fact_count = len(payload['fact_evidence'])
    provenance = {'online': '在线官方标签', 'cache': '已校验的本地标签缓存', 'seed': '随程序提供的来源事实'}[status]
    return dict(payload, name=_PROFILES[compound_id]['name'], status=status,
                age_days=round(age, 2), stale=age > STALE_DAYS,
                content_sha256=_digest(payload), prediction_admitted=False,
                summary=f'{provenance}；距获取 {age:.1f} 天。' +
                ('已保留可核对的机制段落。' if fact_count else '未提取可用于本组合机制推断的段落。') +
                ('超过 30 天，仅作历史来源。' if age > STALE_DAYS else ''))


def _seed_record(compound_id):
    profile = _PROFILES[compound_id]
    if not profile.get('standalone_seed', True):
        return _empty_record(compound_id, profile['name'], 'unavailable',
                             '尚无已校验的独立药品标签；现有目录仅保留另一药品标签中的研究引用。')
    payload = {'compound_id': compound_id, 'lookup_name': profile['lookup_name'], 'route': 'oral',
               'formulation': profile['formulation'], 'url': profile['source_url'],
               'retrieved_at': _LIBRARY['reviewed_at'], 'effective_time': None,
               'timestamp_precision': _LIBRARY['review_timestamp_precision'],
               'response_sha256': None, 'fact_evidence': deepcopy(profile['facts'])}
    return _record(compound_id, payload, 'seed')


def _empty_record(compound_id, name, status, summary):
    return {'compound_id': compound_id, 'name': name, 'status': status, 'url': '',
            'retrieved_at': None, 'age_days': None, 'stale': False, 'content_sha256': None,
            'response_sha256': None, 'fact_evidence': [], 'summary': summary,
            'prediction_admitted': False}


def _lookup(compound_id, online, cache_dir, transport):
    path = cache_dir / (compound_id + '-oral.json')
    errors = {}
    if online:
        try:
            payload = _parse_response(compound_id, transport(_query_url(compound_id)))
            record = _record(compound_id, payload, 'online')
            try:
                _write_cache(compound_id, path, payload)
            except (OSError, ValueError) as exc:
                record['cache_error'] = str(exc)[:200]
            return record
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            errors['error'] = '在线标签获取或校验失败：' + str(exc)[:200]
    try:
        payload = _read_cache(compound_id, path)
        record = _record(compound_id, payload, 'cache')
    except FileNotFoundError:
        record = _seed_record(compound_id)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError) as exc:
        errors['cache_error'] = '缓存未采用：' + str(exc)[:200]
        record = _seed_record(compound_id)
    return dict(record, **errors)


def _pair(left, right):
    pair = {'ids': [left['compound_id'], right['compound_id']],
            'status': 'INSUFFICIENT_EVIDENCE', 'sources': [], 'prediction_admitted': False, 'stale': False,
            'summary': '本资料库没有足够的组合证据；未检出不等于无相互作用。'}
    records = {r['compound_id']: r for r in (left, right)}
    required = {'estradiol': 'estrogen_partial_cyp3a4_metabolism',
                'bicalutamide': 'r_bicalutamide_cyp3a4_inhibition'}
    if all(cid in records and any(f['fact'] == fact for f in records[cid]['fact_evidence'])
           for cid, fact in required.items()):
        pair.update(status='MECHANISM_INFERENCE', sources=[records[cid]['url'] for cid in required],
                    stale=any(records[cid]['stale'] for cid in required),
                    summary='机制推断：雌二醇标签指出雌激素部分经 CYP3A4 代谢；比卡鲁胺标签记载活性 R-对映体抑制 CYP3A4。合用可能影响雌激素暴露，但这两段资料不是该组合的直接临床试验证据；无法量化变化或给出剂量建议。')
        if pair['stale']:
            pair['summary'] = '历史来源：至少一份支持资料已超过 30 天，尚未确认现行标签。' + pair['summary']
    return pair


def analyze_labels(items, online=True, *, cache_dir=None, transport=None):
    """Return provenance records and all unordered pairs for 1–32 input rows.

    Only explicit ``kind='catalog'`` plus a known id can use evidence. Display
    names and all other fields (dose, patient context, genetics) remain local.
    """
    if not isinstance(items, (list, tuple)) or not 1 <= len(items) <= 32:
        raise ValueError('药品条目必须为 1–32 项')
    if any(not isinstance(row, dict) for row in items):
        raise ValueError('药品条目结构无效')
    cache_dir = Path(cache_dir) if cache_dir is not None else CACHE_DIR
    transport = transport or fetch
    records, memo = [], {}
    for index, row in enumerate(items):
        compound_id = row.get('compound_id')
        if row.get('kind') != 'catalog' or not isinstance(compound_id, str) or compound_id not in _PROFILES:
            record = _empty_record(None, str(row.get('name', '未命名')), 'unknown',
                                   '自定义或未确认身份；未自动匹配药品，也未发送名称或个人资料。')
        elif row.get('route', 'oral') != 'oral':
            record = _empty_record(compound_id, _PROFILES[compound_id]['name'], 'unsupported_route',
                                   '此给药途径尚无已校验标签；不沿用口服参数或机制段落。')
        else:
            if compound_id not in memo:
                memo[compound_id] = _lookup(compound_id, online, cache_dir, transport)
            record = deepcopy(memo[compound_id])
        record['input_index'] = index
        records.append(record)
    return {'records': records,
            'pairs': [_pair(left, right) for i, left in enumerate(records) for right in records[i + 1:]],
            'note': '这是按需积累的部分官方标签资料库，并非完整药典。在线优先；失败后采用已校验缓存或明确标注的种子事实。来源支持定性研究，不自动批准个体预测；不相乘组合比值。'}
