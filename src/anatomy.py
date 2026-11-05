"""Anatomical membership is distinct from source-backed substance association."""
REGIONS = {
    'brain': ('大脑', 'organ', ['nervous']),
    'heart': ('心脏', 'organ', ['cardiovascular']),
    'lungs': ('肺', 'organ', ['respiratory']),
    'liver': ('肝脏', 'organ', ['metabolic']),
    'stomach': ('胃', 'organ', ['digestive']),
    'kidneys': ('双肾', 'organ', ['urinary']),
    'bladder': ('膀胱', 'organ', ['urinary']),
    'testes': ('睾丸', 'organ', ['reproductive']),
    'uterus': ('子宫', 'organ', ['reproductive']),
    'biceps': ('肱二头肌群', 'muscle', ['muscular']),
    'triceps': ('肱三头肌群', 'muscle', ['muscular']),
    'quadriceps': ('股四头肌群', 'muscle', ['muscular']),
    'nervous': ('神经系统', 'system', ['brain']),
    'metabolic': ('代谢相关器官', 'system', ['liver']),
    'urinary': ('泌尿系统', 'system', ['kidneys', 'bladder']),
    'digestive': ('消化系统', 'system', ['stomach', 'liver']),
    'cardiovascular': ('心血管系统', 'system', ['heart']),
    'respiratory': ('呼吸系统', 'system', ['lungs']),
    'reproductive': ('生殖器官分层', 'system', ['testes', 'uterus']),
    'muscular': ('肌肉系统', 'system', ['biceps', 'triceps', 'quadriceps']),
}
MAYO = 'https://www.mayoclinic.org/drugs-supplements/atomoxetine-oral-route/description/drg-20066904'
LABEL = 'https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=309de576-c318-404a-bc15-660c2b1876fb'

def fact(category, text, section, url=LABEL):
    return dict(category=category, text=text, section=section, url=url,
                review_status='PENDING_REVIEW', checked_on='2026-11-05',
                interpretation='文献关联，不是当前使用者实测或个人发生概率')

EVIDENCE = {'atomoxetine': {
    'brain': [fact('mechanism', '选择性去甲肾上腺素再摄取抑制机制；脑部只作中枢作用定位，未估计具体脑区疗效。', 'Description', MAYO)],
    'liver': [fact('metabolism', '主要经 CYP2D6 通路代谢；基因表型可关联母药暴露。此处不将暴露估计转换为肝损伤。', '12.3 Pharmacokinetics')],
    'heart': [fact('label_concern', '标签提示血压与心率可能变化；未计算个人发生概率。', '5.4 Effects on Blood Pressure and Heart Rate')],
    'kidneys': [fact('excretion', '主要代谢物经尿液排出。肾脏仅表示排泄系统位置，不代表肾脏疗效或肾毒性。', '12.3 Excretion')],
    'bladder': [fact('label_concern', '标签记录排尿迟疑及尿潴留；图示为泌尿功能关联，不能认定病变位置。', '5.9 Effects on Urine Outflow from the Bladder')],
}}

def identity(drug):
    return drug.get('compound_id') if isinstance(drug, dict) and drug.get('kind') == 'catalog' else None

def highlighted_regions(drug):
    return set(EVIDENCE.get(identity(drug), {}))

def region_details(drug, region):
    if region not in REGIONS: raise ValueError('未知解剖区域')
    label, kind, related = REGIONS[region]
    evidence = EVIDENCE.get(identity(drug), {}).get(region, [])
    return dict(id=region, name=label, kind=kind, evidence=[dict(e) for e in evidence],
                status='SOURCE_ASSOCIATION' if evidence else 'INSUFFICIENT_EVIDENCE',
                individual_effect_known=False, members=list(related),
                relation_note='结构/功能关联只用于导航；不把一个区域的药物效应传播到其它区域。')
