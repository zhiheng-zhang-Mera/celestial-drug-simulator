"""Build the embedded local pharmacopoeia index.

The index is a committed, offline artifact. It joins the curated drug profiles,
the interaction catalog and the local label cache into a single searchable list,
and adds reviewed aliases (including the estradiol valerate alias required by the
clinical reading workflow). Runtime code never builds this file; regenerating it
is a deliberate release step:

    python tools/build_pharmacopoeia.py
    python tools/build_pharmacopoeia.py --check
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ROOT / 'data' / 'drug_profiles.json'
CATALOG = ROOT / 'data' / 'catalog.json'
LABEL_CACHE = ROOT / 'data' / 'cache' / 'drug_labels'
OUTPUT = ROOT / 'data' / 'pharmacopoeia' / 'index.json'

SCHEMA = 1

# Reviewed display names and aliases. The profile names are "中文 / 英文" pairs;
# these entries add the names a reader may search for in either language.
REVIEWED = {
    'estradiol': {
        'display': '雌二醇 / estradiol',
        'names': ['雌二醇', '戊酸雌二醇', 'estradiol', 'estradiol valerate', '17β-雌二醇'],
        'note': '戊酸雌二醇按雌二醇身份检索；酯类的药代参数未单独建模。',
        'status': 'profile',
    },
    'bicalutamide': {
        'display': '比卡鲁胺 / bicalutamide',
        'names': ['比卡鲁胺', 'bicalutamide'],
        'note': '非甾体抗雄激素；标签机制与药代资料来自本地档案。',
        'status': 'profile',
    },
    'fluconazole': {
        'display': '氟康唑 / fluconazole',
        'names': ['氟康唑', 'fluconazole'],
        'note': '',
        'status': 'profile',
    },
    'midazolam': {
        'display': '咪达唑仑 / midazolam',
        'names': ['咪达唑仑', 'midazolam'],
        'note': '',
        'status': 'profile',
    },
    'tofacitinib': {
        'display': '托法替布 / tofacitinib',
        'names': ['托法替布', 'tofacitinib'],
        'note': '',
        'status': 'profile',
    },
    'atomoxetine': {
        'display': '阿托莫西汀 / atomoxetine',
        'names': ['阿托莫西汀', '托莫西汀', 'atomoxetine'],
        'note': '仅有本地文献关联（人体区域证据），没有口服标签缓存。',
        'status': 'evidence_only',
    },
}


def load_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def build():
    profiles = load_json(PROFILES).get('profiles', {})
    compounds = load_json(CATALOG).get('compounds', {})
    entries = []
    seen = set()
    for identity, review in REVIEWED.items():
        profile = profiles.get(identity)
        cached = (LABEL_CACHE / (identity + '-oral.json')).exists()
        names = list(dict.fromkeys(review['names']))
        if profile:
            for alias in profile.get('aliases', []):
                alias = str(alias).strip()
                if alias and alias not in names:
                    names.append(alias)
            profile_name = str(profile.get('name', '')).strip()
            if profile_name and profile_name not in names:
                names.append(profile_name)
        source = 'local_profile' if profile else ('local_evidence' if identity in compounds or identity == 'atomoxetine' else 'local_index')
        entries.append({
            'identity': identity,
            'display': review['display'],
            'names': names,
            'source': source,
            'status': review['status'],
            'has_profile': bool(profile),
            'has_label_cache': cached,
            'catalog_present': identity in compounds,
            'note': review['note'],
            'label_url': (profile or {}).get('source_url', ''),
        })
        seen.add(identity)
    # Keep any future profile that is not reviewed yet; it stays searchable by its own names.
    for identity, profile in sorted(profiles.items()):
        if identity in seen:
            continue
        names = [str(alias).strip() for alias in profile.get('aliases', []) if str(alias).strip()]
        name = str(profile.get('name', '')).strip()
        if name:
            names.insert(0, name)
        if not names:
            names = [identity]
        entries.append({
            'identity': identity,
            'display': name or identity,
            'names': list(dict.fromkeys(names)),
            'source': 'local_profile',
            'status': 'profile',
            'has_profile': True,
            'has_label_cache': (LABEL_CACHE / (identity + '-oral.json')).exists(),
            'catalog_present': identity in compounds,
            'note': '',
            'label_url': profile.get('source_url', ''),
        })
    entries.sort(key=lambda item: item['identity'])
    payload = {
        'schema': SCHEMA,
        'license_note': 'Local index over Celestial-curated drug profiles, interaction catalog and cached public labels. '
                        'Display names/aliases are editorial; source links point to DailyMed/openFDA/Mayo pages. '
                        'Not a pharmacopoeia substitute and not clinical validation.',
        'entries': entries,
    }
    return payload


def digest(payload):
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='verify the committed index is current')
    args = parser.parse_args()
    payload = build()
    serialized = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + '\n'
    if args.check:
        current = OUTPUT.read_text(encoding='utf-8') if OUTPUT.exists() else ''
        if current != serialized:
            raise SystemExit('pharmacopoeia index is stale; run python tools/build_pharmacopoeia.py')
        print('pharmacopoeia index is current; sha256=' + digest(payload))
        return
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(serialized, encoding='utf-8')
    print('wrote', OUTPUT, 'entries=' + str(len(payload['entries'])), 'sha256=' + digest(payload))


if __name__ == '__main__':
    main()
