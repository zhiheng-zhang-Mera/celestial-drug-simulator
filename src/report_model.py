"""Pure view-model assembly for the multi-drug interaction report.

The report answers two separate questions for each substance:

1. what does the single-substance evidence say (individual mechanism, regions,
   provenance gaps), and
2. what is documented about the pair (mechanism clue or catalog study)?

Everything here is derived from already-computed ``simulate()`` /
``analyze_labels()`` data plus the curated ``anatomy.EVIDENCE`` table.  The
module performs no I/O, no network access and no prediction: it never computes
exposure, an effect size, an interaction delta or a risk multiplier.  Display
labels live here only where the report needs a stable Chinese wording (gap
codes); all remaining codes are passed through for the UI layer to map.
"""
from functools import lru_cache
from itertools import combinations
import json
from pathlib import Path

from src import anatomy

REVIEWS_PATH = Path(__file__).resolve().parent.parent / 'data' / 'interaction_reviews.json'

DISCLAIMER = ('本报告只呈现来源事实与机制线索；未计算个体暴露/效应预测，'
              '也未计算联合风险倍率。')

MISSING_MECHANISM = '未收录可引用的个体机制摘要'
MISSING_REGIONS = '未收录区域级证据'
NO_PAIR_CLUE = ('本资料库与在线说明书均未给出可引用的组合机制线索；'
                '未检出不等于无相互作用。')
CATALOG_CLUE = ('目录研究库收录该组合的 {count} 条研究观察；来源章节：{sections}。'
                '研究观察仅作外部参考，不是本方案预测；人群、条件与不确定性见下方。')
PREDICTION_REFUSED = '当前方案预测：未准入（不把研究比率当成本方案预测）'

# Only entry['gaps'] codes produced by simulation are mapped.  Unknown codes
# fall back to an explicit "unmapped" label while keeping the raw code visible.
GAP_LABELS = {
    'PARAMETERS_NOT_REVIEWED': '药代参数未审核',
    'MODEL_DOMAIN_NOT_VALIDATED': '模型适用域未验证',
    'NO_VALIDATED_EXPOSURE_MODEL': '无已验证暴露模型',
    'UNSUPPORTED_ROUTE': '该途径无已验证标签',
    'COMPOSITION_NOT_RESOLVED': '成分未解析',
}
UNKNOWN_GAP_LABEL = '未映射的缺口代码'


@lru_cache(maxsize=1)
def load_reviews():
    """Load the curated interaction review fixture once (read-only, no network).

    The report remains usable if the file is absent or malformed: callers get an
    empty review set and fall back to the pre-existing label/catalog behaviour.
    """
    try:
        data = json.loads(REVIEWS_PATH.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {'drugs': {}, 'pairs': {}}
    if not isinstance(data, dict):
        return {'drugs': {}, 'pairs': {}}
    drugs = data.get('drugs') if isinstance(data.get('drugs'), dict) else {}
    pairs = data.get('pairs') if isinstance(data.get('pairs'), dict) else {}
    return dict(data, drugs=drugs, pairs=pairs)


def _reviews(reviews=None):
    return reviews if isinstance(reviews, dict) else load_reviews()


def _normalise(value):
    return ''.join(str(value or '').split()).casefold()


def resolve_identity(name, reviews=None):
    """Map a display name to a curated canonical compound id, exact aliases only."""
    data = _reviews(reviews)
    normalized = _normalise(name)
    if not normalized:
        return None
    for compound_id, drug in (data.get('drugs') or {}).items():
        if not isinstance(drug, dict):
            continue
        names = [compound_id, drug.get('canonical_name')]
        names.extend(drug.get('aliases') or [])
        if any(candidate and _normalise(candidate) == normalized for candidate in names):
            return compound_id
    return None


def _drug_review(canonical_id, reviews):
    if not canonical_id:
        return None
    drug = (reviews.get('drugs') or {}).get(canonical_id)
    return drug if isinstance(drug, dict) else None


def _pair_review(left, right, reviews):
    left_id = (left or {}).get('canonical_id')
    right_id = (right or {}).get('canonical_id')
    if not left_id or not right_id:
        return None
    pairs = reviews.get('pairs') or {}
    for key in ('+'.join((left_id, right_id)), '+'.join((right_id, left_id))):
        review = pairs.get(key)
        if isinstance(review, dict):
            return review
    return None


def _source_views(sources):
    views = []
    for item in (sources or []):
        if isinstance(item, dict):
            views.append(dict(label=str(item.get('label') or ''),
                              url=str(item.get('url') or ''),
                              section=str(item.get('section') or '')))
        elif isinstance(item, str) and item.strip():
            views.append(dict(label='', url=item.strip(), section=''))
    return views


def _item_views(items):
    views = []
    for item in (items or []):
        if isinstance(item, dict):
            text = str(item.get('text') or '').strip()
            source = str(item.get('source') or '').strip()
        else:
            text, source = str(item or '').strip(), ''
        if text:
            views.append(dict(text=text, source=source))
    return views


def _section_views(sections):
    views = []
    for item in (sections or []):
        if not isinstance(item, dict):
            continue
        title = str(item.get('title') or '').strip()
        if not title:
            continue
        views.append(dict(id=str(item.get('id') or ''), title=title,
                          body=str(item.get('body') or '').strip(),
                          items=_item_views(item.get('items'))))
    return views


def _combined_effect_view(value):
    if isinstance(value, str):
        return dict(headline=value.strip(), items=[], note='')
    if not isinstance(value, dict):
        return None
    headline = str(value.get('headline') or '').strip()
    items = [str(item).strip() for item in (value.get('items') or [])
             if str(item).strip()]
    note = str(value.get('note') or '').strip()
    if not (headline or items or note):
        return None
    return dict(headline=headline, items=items, note=note)


def _pd_view(drug, canonical_id, display_name):
    if not drug or not canonical_id:
        return None
    alias_note = ''
    for name, note in (drug.get('alias_notes') or {}).items():
        if _normalise(name) == _normalise(display_name) and note:
            alias_note = str(note)
            break
    return dict(
        canonical_id=canonical_id,
        canonical_name=str(drug.get('canonical_name') or ''),
        display_name=str(display_name or ''),
        drug_class=str(drug.get('drug_class') or ''),
        target=str(drug.get('pd_target') or ''),
        summary=str(drug.get('pd_summary') or ''),
        effects=[str(item) for item in (drug.get('pd_effects') or []) if str(item).strip()],
        mechanism=str(drug.get('mechanism') or ''),
        evidence_grade=str(drug.get('evidence_grade') or ''),
        evidence_grade_label=str(drug.get('evidence_grade_label') or ''),
        uncertainty=str(drug.get('uncertainty') or ''),
        alias_note=alias_note,
        sources=_source_views(drug.get('sources')),
    )


def _pair_review_view(review):
    if not review:
        return None
    return dict(
        status=str(review.get('status') or ''),
        evidence_grade=str(review.get('evidence_grade') or ''),
        evidence_grade_label=str(review.get('evidence_grade_label') or ''),
        summary=str(review.get('summary') or ''),
        combined_effect=_combined_effect_view(review.get('combined_effect')),
        disclosure_sections=_section_views(review.get('disclosure_sections')),
        not_computed=str(review.get('not_computed') or ''),
        uncertainty=str(review.get('uncertainty') or ''),
        sources=_source_views(review.get('sources')),
    )


def _unique(values):
    seen, result = set(), []
    for value in values:
        value = ' '.join(str(value).split()) if isinstance(value, str) else value
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _first_sentence(value):
    text = ' '.join(str(value or '').split())
    for index, character in enumerate(text):
        if character in '。！？':
            return text[:index + 1]
    return text


def _records(labels):
    if not isinstance(labels, dict):
        return []
    records = labels.get('records')
    return records if isinstance(records, list) else []


def _label_pairs(labels):
    if not isinstance(labels, dict):
        return []
    pairs = labels.get('pairs')
    return pairs if isinstance(pairs, list) else []


def _result_pairs(result):
    pairs = result.get('pairs') if isinstance(result, dict) else None
    return pairs if isinstance(pairs, list) else []


def _entries(result):
    entries = result.get('entries') if isinstance(result, dict) else None
    return entries if isinstance(entries, list) else []


def _mechanism(record, entry):
    """Individual mechanism summary from real record/profile fields.

    Order of provenance (documented in the module report):
    record fact summaries (seeded curated facts) → source-profile fact
    summaries → the label record's own summary → explicit missing statement.
    The record summary is the last textual fallback because the label service
    uses it for provenance (online/cache/seed age), not for mechanism content.
    """
    from_record = []
    for fact in (record.get('fact_evidence') or []):
        if isinstance(fact, dict) and fact.get('summary'):
            from_record.append(fact['summary'])
    from_record = _unique(from_record)

    profile = entry.get('source_profile') or {}
    from_profile = []
    if not from_record:
        for fact in (profile.get('facts') or []):
            if isinstance(fact, dict) and fact.get('summary'):
                from_profile.append(fact['summary'])
        from_profile = _unique(from_profile)

    points = (from_record or from_profile)[:3]
    if points:
        return {'text': ' '.join(points),
                'source': 'record_facts' if from_record else 'profile_facts',
                'points': points}
    summary = record.get('summary')
    if isinstance(summary, str) and summary.strip():
        return {'text': summary.strip(), 'source': 'record_summary', 'points': []}
    return {'text': MISSING_MECHANISM, 'source': 'missing', 'points': []}


def _region_views(entry):
    """Region-level individual evidence from the curated anatomy table."""
    if not anatomy.identity(entry):
        return []
    regions = []
    for region in anatomy.highlighted_regions(entry):
        detail = anatomy.region_details(entry, region)
        evidence = detail.get('evidence') or []
        if not evidence:
            continue
        categories = _unique([item.get('category') for item in evidence if item.get('category')])
        text = ' '.join(' '.join(str(item.get('text', '')).split())
                        for item in evidence if item.get('text'))
        first = evidence[0]
        regions.append(dict(id=region, name=detail['name'], kind=detail['kind'],
                            category=categories[0] if categories else '',
                            categories=categories, text=text,
                            section=first.get('section', ''),
                            url=first.get('url', ''),
                            review_status=first.get('review_status', '')))
    return regions


def _gap_views(entry):
    return [dict(code=str(code),
                 label=GAP_LABELS.get(code, UNKNOWN_GAP_LABEL))
            for code in (entry.get('gaps') or [])]


def individual_view(result, labels, reviews=None):
    """One display record per input substance; order matches simulate()."""
    data = _reviews(reviews)
    records = _records(labels)
    views = []
    for index, entry in enumerate(_entries(result)):
        entry = entry if isinstance(entry, dict) else {}
        record = records[index] if index < len(records) and isinstance(records[index], dict) else {}
        profile = entry.get('source_profile') or {}
        mechanism = _mechanism(record, entry)
        source_url = record.get('url') or profile.get('source_url') or ''
        name = str(entry.get('name') or record.get('name') or '未命名物质')
        if entry.get('kind') == 'catalog' and entry.get('compound_id'):
            canonical_id = str(entry.get('compound_id'))
        else:
            canonical_id = resolve_identity(name, data) or ''
        pd = _pd_view(_drug_review(canonical_id, data), canonical_id, name)
        views.append(dict(
            index=index,
            name=name,
            kind=entry.get('kind', 'custom'),
            compound_id=entry.get('compound_id', ''),
            canonical_id=canonical_id,
            category=entry.get('category', 'medicine'),
            status=entry.get('status', 'PENDING_REVIEW'),
            route=entry.get('route', ''),
            dose_mg=entry.get('dose_mg'),
            interval_h=entry.get('interval_h'),
            count=entry.get('count'),
            mechanism=mechanism,
            pd=pd,
            regions=_region_views(entry),
            gaps=_gap_views(entry),
            record_status=record.get('status', 'unavailable'),
            record_summary=str(record.get('summary') or ''),
            record_error=str(record.get('error') or record.get('cache_error') or ''),
            retrieved_at=record.get('retrieved_at'),
            source_url=str(source_url or ''),
            source_section=str(profile.get('source_section') or ''),
        ))
    return views


def _has_pair_clue(result_pair, label_pair, review=None):
    if review and review.get('summary'):
        return True
    if label_pair.get('status') == 'MECHANISM_INFERENCE':
        return True
    if label_pair.get('summary') and label_pair.get('status') != 'INSUFFICIENT_EVIDENCE':
        return True
    return bool(result_pair.get('evidence'))


def _pair_summary(result_pair, label_pair):
    status = label_pair.get('status')
    summary = str(label_pair.get('summary') or '').strip()
    if status == 'MECHANISM_INFERENCE' and summary:
        return summary
    evidence = [item for item in (result_pair.get('evidence') or []) if isinstance(item, dict)]
    if evidence:
        sections = _unique([item.get('source_location') or '来源章节未记录'
                            for item in evidence])
        return CATALOG_CLUE.format(count=len(evidence), sections='；'.join(sections))
    if summary and status not in (None, '', 'INSUFFICIENT_EVIDENCE'):
        return summary
    return NO_PAIR_CLUE


def _study_views(result_pair):
    studies = []
    for item in (result_pair.get('evidence') or []):
        if not isinstance(item, dict):
            continue
        source = item.get('source') if isinstance(item.get('source'), dict) else {}
        studies.append(dict(
            source_location=str(item.get('source_location') or '来源章节未记录'),
            population=str(item.get('population') or ''),
            context=str(item.get('context') or ''),
            uncertainty=str(item.get('uncertainty') or ''),
            applicability=str(item.get('applicability') or ''),
            structural_check=str(item.get('structural_check') or ''),
            auc_ratio=item.get('auc_ratio'),
            source_url=str(source.get('url') or ''),
            source_name=str(source.get('publisher') or ''),
            prediction_admitted=False,
            prediction_text=PREDICTION_REFUSED,
        ))
    return studies


def _individual_line(view):
    summary = _first_sentence((view.get('mechanism') or {}).get('text'))
    regions = [region['name'] for region in (view.get('regions') or [])]
    return dict(
        name=view.get('name', ''),
        summary=summary or MISSING_MECHANISM,
        regions=regions,
        region_text='、'.join(regions[:3]) if regions else MISSING_REGIONS,
        mechanism_missing=(view.get('mechanism') or {}).get('source') == 'missing',
    )


def interaction_view(result, labels, reviews=None):
    """One display record per unordered pair; order matches simulate() pairs.

    Curated PD/interaction reviews are merged first; without review data the
    function falls back to the previous label/catalog-only behaviour.
    """
    data = _reviews(reviews)
    individuals = individual_view(result, labels, data)
    result_pairs = _result_pairs(result)
    labels_pairs = _label_pairs(labels)
    indexes = list(combinations(range(len(individuals)), 2))
    views = []
    for index, result_pair in enumerate(result_pairs):
        result_pair = result_pair if isinstance(result_pair, dict) else {}
        label_pair = (labels_pairs[index] if index < len(labels_pairs)
                      and isinstance(labels_pairs[index], dict) else {})
        names = result_pair.get('drugs') if isinstance(result_pair.get('drugs'), list) else []
        a_index, b_index = indexes[index] if index < len(indexes) else (None, None)
        left = individuals[a_index] if a_index is not None and a_index < len(individuals) else {}
        right = individuals[b_index] if b_index is not None and b_index < len(individuals) else {}
        review = _pair_review_view(_pair_review(left, right, data))
        studies = _study_views(result_pair)
        review_sources = review['sources'] if review else []
        sources = _unique(list(label_pair.get('sources') or []) +
                          [study['source_url'] for study in studies] +
                          [source['url'] for source in review_sources])
        if review and review['status'] == 'mechanism_inference':
            status = 'MECHANISM_INFERENCE'
        elif label_pair.get('status') == 'MECHANISM_INFERENCE':
            status = 'MECHANISM_INFERENCE'
        elif result_pair.get('evidence'):
            status = 'HOLD_FOR_REVIEW'
        else:
            status = 'INSUFFICIENT_EVIDENCE'
        summary = review['summary'] if review and review['summary'] else _pair_summary(
            result_pair, label_pair)
        views.append(dict(
            index=index,
            names=[str(name) for name in names] if names else
                  [left.get('name', 'A'), right.get('name', 'B')],
            a=_individual_line(left) if left else _individual_line({}),
            b=_individual_line(right) if right else _individual_line({}),
            pd_individual_a=left.get('pd'),
            pd_individual_b=right.get('pd'),
            status=status,
            result_status=str(result_pair.get('status') or ''),
            label_status=str(label_pair.get('status') or ''),
            summary=summary,
            combined_effect=review['combined_effect'] if review else None,
            disclosure_sections=review['disclosure_sections'] if review else [],
            evidence_grade=review['evidence_grade'] if review else '',
            evidence_grade_label=review['evidence_grade_label'] if review else '',
            uncertainty=review['uncertainty'] if review else '',
            not_computed=review['not_computed'] if review else '',
            review_sources=review_sources,
            has_review=bool(review),
            studies=studies,
            sources=sources,
            has_label_clue=label_pair.get('status') == 'MECHANISM_INFERENCE',
            has_catalog_observations=bool(result_pair.get('evidence')),
            prediction_admitted=bool(result_pair.get('prediction_admitted', False)),
        ))
    return views


def overview_view(result, labels, reviews=None):
    """Counts for the silent metric row plus the report-wide disclaimer."""
    data = _reviews(reviews)
    entries = _entries(result)
    result_pairs = _result_pairs(result)
    labels_pairs = _label_pairs(labels)
    individuals = individual_view(result, labels, data)
    indexes = list(combinations(range(len(individuals)), 2))
    mechanism_pairs = 0
    for index, result_pair in enumerate(result_pairs):
        label_pair = (labels_pairs[index] if index < len(labels_pairs)
                      and isinstance(labels_pairs[index], dict) else {})
        a_index, b_index = indexes[index] if index < len(indexes) else (None, None)
        left = individuals[a_index] if a_index is not None and a_index < len(individuals) else {}
        right = individuals[b_index] if b_index is not None and b_index < len(individuals) else {}
        review = _pair_review_view(_pair_review(left, right, data))
        if _has_pair_clue(result_pair if isinstance(result_pair, dict) else {},
                          label_pair, review):
            mechanism_pairs += 1
    context = result.get('context') if isinstance(result.get('context'), dict) else {}
    sampling = result.get('sampling') if isinstance(result.get('sampling'), dict) else {}
    return dict(
        counts=dict(substances=len(entries),
                    pairs=len(result_pairs),
                    mechanism_pairs=mechanism_pairs,
                    data_gaps=sum(len(entry.get('gaps') or []) for entry in entries
                                  if isinstance(entry, dict))),
        disclaimer=DISCLAIMER,
        overall=str(result.get('overall') or ''),
        explanation=str(result.get('explanation') or ''),
        label_note=str((labels or {}).get('note') or '') if isinstance(labels, dict) else '',
        context_note=str(context.get('note') or ''),
        input_sha256=str(result.get('input_sha256') or ''),
        snapshot_id=str(result.get('snapshot_id') or ''),
        sampling=dict(sampling),
        export_note=('导出报告仍为 simulate() 的原始 JSON 结构；本页的分组视图只存在于界面层，'
                     '不写入导出数据。'),
    )
