"""Offline report boundary: identifiers, pair coverage and fail-closed evidence."""
from hashlib import sha256
from itertools import combinations
from pathlib import Path
import json
import math
from src.exposure import Regimen, concentration
from src.context import normalize_context

CATALOG = Path(__file__).resolve().parent.parent / 'data' / 'catalog.json'


def load_catalog():
    return json.loads(CATALOG.read_text(encoding='utf-8-sig'))


def digest(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def simulate(items, context=None):
    normalized_context = normalize_context(context)
    if not isinstance(items, list) or not 1 <= len(items) <= 32:
        raise ValueError('方案必须包含 1 到 32 种药物。')
    catalog = load_catalog()
    sources = {source['id']: source for source in catalog['sources']}
    entries, regimes, names, identities = [], [], set(), set()
    for raw in items:
        if not isinstance(raw, dict): raise ValueError('无效药物条目。')
        name = str(raw.get('name', '')).strip()
        if not name or len(name) > 120 or name.casefold() in names:
            raise ValueError('名称不能为空、重复或超过 120 字符。')
        names.add(name.casefold())
        kind, compound_id = raw.get('kind'), raw.get('compound_id', '')
        if kind not in ('synthetic', 'custom', 'catalog'):
            raise ValueError('未知药物类型。')
        if kind == 'catalog':
            if compound_id not in catalog['compounds']:
                from src.drug_library import profile_for
                profile=profile_for(compound_id, raw.get('route','oral'))
                if profile is None: raise ValueError('来源库无此药物 ID。')
                catalog['compounds'][compound_id]=profile
            if compound_id in identities: raise ValueError('同一来源药物不能重复添加；请更新原条目。')
            identities.add(compound_id)
        elif compound_id:
            raise ValueError('自定义与合成药物不能冒用来源库 ID。')
        evidence_mode=raw.get('model_mode')=='evidence'
        regimen=None
        if evidence_mode:
            for key in ('dose_mg','interval_h','half_life_h','volume_l'):
                value=raw.get(key)
                if value is not None and (isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0):
                    raise ValueError('填写的剂量、时间或参数必须为有限正数。')
            if raw.get('count') is not None and (type(raw['count']) is not int or not 1<=raw['count']<=1000):
                raise ValueError('次数必须为1到1000的整数。')
        else:
            try:
                regimen = Regimen(*(raw[key] for key in ('dose_mg', 'volume_l', 'half_life_h', 'interval_h', 'count')))
            except (KeyError, TypeError) as exc:
                raise ValueError('缺少或无效的数值参数。') from exc
            horizon = (regimen.count - 1) * regimen.interval_h + 5 * regimen.half_life_h
            if not 0 < horizon <= 8760: raise ValueError('此版本时间范围必须小于等于 8760 小时。')
        route = raw.get('route')
        if route not in ('iv_bolus', 'oral', 'infusion','transdermal','sublingual','injection','other'): raise ValueError('未知给药途径。')
        gaps = []
        category = raw.get('category', 'medicine')
        if category not in ('medicine', 'supplement', 'botanical', 'food_beverage', 'other'):
            raise ValueError('未知物质类别。')
        if category != 'medicine': gaps.append('COMPOSITION_NOT_RESOLVED')
        if kind != 'synthetic': gaps += ['PARAMETERS_NOT_REVIEWED', 'MODEL_DOMAIN_NOT_VALIDATED']
        if route != 'iv_bolus': gaps.append('UNSUPPORTED_ROUTE')
        if evidence_mode:gaps.append('NO_VALIDATED_EXPOSURE_MODEL')
        entry = dict(raw, name=name, category=category, gaps=gaps,
                     status='SYNTHETIC_ONLY' if kind == 'synthetic' else 'PENDING_REVIEW')
        if kind == 'catalog': entry['source_profile'] = catalog['compounds'][compound_id]
        entries.append(entry)
        regimes.append(regimen)
    active_regimes=[r for r in regimes if r is not None]
    times = sorted({max((r.count - 1) * r.interval_h + 5 * r.half_life_h for r in active_regimes) * i / 100
                    for i in range(101)} | {i * r.interval_h for r in active_regimes for i in range(r.count)}) if active_regimes else []
    full_sample_count = len(times)
    if len(times) > 2048:
        times = [times[round(i * (len(times) - 1) / 2047)] for i in range(2048)]
    curves = [dict(name=entry['name'], interpretation=('SYNTHETIC_IV_BASELINE_NO_DDI' if entry['kind'] == 'synthetic'
                                                    else 'UNVERIFIED_USER_PARAMETER_WHAT_IF_NO_DDI'),
                   values=[concentration(regimen, time) for time in times])
              for entry, regimen in zip(entries, regimes) if regimen is not None and entry['kind'] in ('synthetic', 'custom') and entry['route'] == 'iv_bolus']
    pairs = []
    for a, b in combinations(entries, 2):
        evidence = []
        for record in catalog['interactions']:
            if a['kind'] == b['kind'] == 'catalog' and {a['compound_id'], b['compound_id']} == {record['perpetrator'], record['victim']}:
                source = sources.get(record['source_id'])
                complete = bool(source and source.get('url') and record.get('source_location')
                                and record.get('population') and record.get('context') and record.get('uncertainty'))
                evidence.append(dict(record, source=source, structural_check='PASS' if complete else 'MISSING_PROVENANCE',
                                     applicability='CONTEXT_MISMATCH' if a['route'] != record['route'] or b['route'] != record['route'] else 'DOSE_TIMELINE_POPULATION_NOT_VERIFIED',
                                     prediction_admitted=False))
        pairs.append(dict(drugs=[a['name'], b['name']], status='HOLD_FOR_REVIEW' if evidence else 'INSUFFICIENT_EVIDENCE',
                          evidence=evidence, predicted_effect=None))
    return dict(schema_version='1.1', simulator_version='0.3',
                input_sha256=digest({'items': items, 'context': normalized_context}), context=normalized_context,
                snapshot_sha256=digest(catalog), snapshot_id=catalog['snapshot_id'],
                overall='INSUFFICIENT_EVIDENCE',
                explanation='研究观察值不是当前方案预测。多药交互不能由两药倍率相乘；未知不等于无相互作用。',
                validation={'L1': 'UNIT_TESTED_SYNTHETIC_KERNEL', 'L2': 'NOT_RUN', 'L3': 'NOT_RUN', 'forest': 'HOLD_FOR_REVIEW'},
                sampling={'original_points': full_sample_count, 'displayed_points': len(times),
                          'downsampled': full_sample_count > len(times), 'note': '点采样上限 2048；大方案可能省略给药边界点，不用于寻找峰值。'},
                entries=entries, pairs=pairs, sources=catalog['sources'], times_h=times, curves=curves)
