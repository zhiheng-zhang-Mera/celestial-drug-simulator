"""Local context intake; never infers a physiological or genetic PK modifier."""
import math

PROVIDERS = [
    {'id': 'mayo', 'url': 'https://www.mayoclinic.org/drugs-supplements',
     'status': 'CANDIDATE_NOT_CONNECTED', 'role': 'education/mechanism',
     'license': 'AUTHORIZATION_NOT_VERIFIED'},
    {'id': 'cpic', 'url': 'https://api.cpicpgx.org/',
     'status': 'CANDIDATE_NOT_CONNECTED', 'role': 'gene-drug/phenotype',
     'license': 'SNAPSHOT_REVIEW_PENDING'}]


def normalize_context(raw):
    if raw is None: raw = {}
    if not isinstance(raw, dict) or set(raw) - {'physiology', 'genes'}:
        raise ValueError('未知生理/基因上下文字段。')
    profile = raw.get('physiology', {})
    allowed = {'height_cm', 'weight_kg', 'body_fat_percent', 'age_years',
               'physiological_sex', 'measurement_source'}
    if not isinstance(profile, dict) or set(profile) - allowed:
        raise ValueError('未知生理基线字段。')
    normalized = {}
    for key in ('height_cm', 'weight_kg', 'body_fat_percent', 'age_years'):
        value = profile.get(key)
        if value is not None:
            if type(value) not in (float, int) or not math.isfinite(value):
                raise ValueError(key + ' 必须是有限数值或留空。')
            if value < 0 or (key != 'age_years' and value == 0):
                raise ValueError(key + ' 超出输入范围。')
            if key == 'body_fat_percent' and value >= 100:
                raise ValueError('体脂百分比必须在 0 与 100 之间。')
        normalized[key] = value
    sex = profile.get('physiological_sex', 'unknown')
    if sex not in ('unknown', 'female', 'male', 'intersex'):
        raise ValueError('生理性别必须明确指定或 unknown。')
    normalized['physiological_sex'] = sex
    source = profile.get('measurement_source', '')
    if not isinstance(source, str) or len(source) > 2000: raise ValueError('测量来源过长或无效。')
    normalized['measurement_source'] = source
    genes = raw.get('genes', [])
    if not isinstance(genes, list) or len(genes) > 100: raise ValueError('基因记录须为列表，至多 100 项。')
    normalized_genes, seen = [], set()
    for record in genes:
        if not isinstance(record, dict) or set(record) - {'gene', 'result', 'source'}:
            raise ValueError('基因记录须包含 gene/result/source。')
        clean = {}
        for key in ('gene', 'result', 'source'):
            value = record.get(key, '')
            if not isinstance(value, str) or not value.strip() or len(value) > 2000:
                raise ValueError('基因名称、结果与检测来源不能缺失或过长。')
            clean[key] = value.strip()
        clean['gene'] = clean['gene'].upper()
        if clean['gene'] in seen: raise ValueError('重复基因记录需要先解决冲突。')
        seen.add(clean['gene'])
        normalized_genes.append(dict(clean, phenotype='NOT_INFERRED', review_status='PENDING_REVIEW'))
    gaps = ['PHYSIOLOGY_MODEL_NOT_VALIDATED']
    if normalized_genes: gaps.append('GENE_MECHANISM_MODEL_NOT_VALIDATED')
    return dict(physiology=normalized, genes=normalized_genes, gaps=gaps,
                applied_modifiers=[], status='HOLD_FOR_REVIEW',
                note='身体与基因数据尚未用于修正暴露；当前曲线不体现个体代谢。',
                providers=PROVIDERS)
