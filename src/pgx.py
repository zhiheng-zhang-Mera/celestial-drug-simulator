"""Conditional population-parameter research, never prescribing or personal prognosis."""
import math
from src.sources import validate_snapshot, digest

LABEL_URL = 'https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=b080e703-3fab-4914-8529-ffaa59da693d'
EXPECTED = {'*1/*1': ('Normal Metabolizer', '2.0'), '*1/*4': ('Intermediate Metabolizer', '1.0'), '*4/*4': ('Poor Metabolizer', '0.0')}

def phenotype(call, snapshot):
    validate_snapshot(snapshot)
    if not isinstance(call, str): raise ValueError('双倍型必须是文本。')
    parts = call.strip().split('/')
    if len(parts) != 2: raise ValueError('仅支持明确的两等位基因调用。')
    canonical = '/'.join(sorted(parts))
    if canonical not in EXPECTED: raise ValueError('未覆盖此双倍型/拷贝数，不能外推。')
    matches = [r for r in snapshot['diplotypes']['data'] if r.get('diplotype') == canonical and r.get('genesymbol') == 'CYP2D6']
    if len(matches) != 1: raise ValueError('双倍型来源缺失或冲突。')
    record = matches[0]
    if (record.get('generesult'), record.get('totalactivityscore')) != EXPECTED[canonical]:
        raise ValueError('CPIC 映射已变化或冲突，需要模型重新审核。')
    return record

def estimate(case, snapshot):
    if case.get('scenario_confirmed') is not True or case.get('concomitants') != []:
        raise ValueError('仅支持明确无其它暴露、正常器官功能的研究场景；联用/表型转换未校准。')
    if case.get('route') != 'oral' or case.get('compound_id') != 'atomoxetine': raise ValueError('模型仅支持 atomoxetine 口服。')
    for key, lower, upper in [('weight_kg', 40, 120), ('age_years', 18, 64), ('dose_mg', 0, 100)]:
        value = case.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or not lower <= value <= upper or value == 0:
            raise ValueError(key + ' 超出本研究实现范围（非用药剂量建议）。')
    if not isinstance(case.get('source'), str) or not case['source'].strip(): raise ValueError('测量及检测来源不能为空。')
    mapping = phenotype(case.get('diplotype'), snapshot)
    category = mapping['generesult']
    coefficients = {'Normal Metabolizer': (0.35, 5.2), 'Poor Metabolizer': (0.03, 21.6)}
    if category not in coefficients: raise ValueError('没有已选定的中间/超快表型数值参数；禁止插值。')
    clearance_per_kg, half_life = coefficients[category]
    clearance = clearance_per_kg * case['weight_kg']
    return {'status': 'CONDITIONAL_POPULATION_RESEARCH_ESTIMATE', 'model_version': 'atomoxetine-label-0.1',
            'clinical_prediction_validated': False, 'input_sha256': digest(case), 'source_snapshot_sha256': digest(snapshot),
            'genotype_predicted_phenotype': mapping, 'measured_enzyme_activity': None,
            'mechanism': ['CYP2D6', 'atomoxetine metabolism', 'apparent oral clearance', 'parent-drug AUC'],
            'apparent_clearance_l_h': clearance, 'auc_per_dose_mg_h_l': case['dose_mg'] / clearance,
            'half_life_h': half_life, 'applied_covariates': ['weight_kg', 'CYP2D6 diplotype-derived phenotype'],
            'unapplied_covariates': ['height', 'body_fat', 'sex'], 'label_source': LABEL_URL, 'label_section': '12.3',
            'coefficient_l_h_kg': clearance_per_kg, 'formula': 'CL/F = label group coefficient × weight; AUC per dose = dose / (CL/F)',
            'uncertainty': 'Group means; individual prediction interval unavailable. Legacy label extensive metabolizer mapped to current normal only as an explicit research approximation. No IM extrapolation. CL/F already includes F; do not multiply bioavailability again.',
            'mayo_reference': snapshot.get('mayo', {}),
            'limitations': 'Not actual individual exposure, efficacy, safety, dose advice, metabolite or DDI prediction. Population PK calibration and independent clinical review pending.'}
