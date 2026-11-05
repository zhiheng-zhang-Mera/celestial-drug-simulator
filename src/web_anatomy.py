"""Small, data-only contract between the authoritative Python model and HTML."""
import json
from src.anatomy import REGIONS, highlighted_regions, region_details


def fallback_view(selected):
    return ('背面' if selected=='triceps' else '正面',
            {'testes':'睾丸分层','uterus':'子宫分层'}.get(selected,'隐藏'))


def make_state(drug, selected):
    detail = region_details(drug, selected)
    return {
        'selected': selected,
        'name': detail['name'],
        'regions': [{'id': key, 'name': value[0]} for key, value in REGIONS.items()],
        'effects': {key: region_details(drug, key)['evidence'][0]['category']
                    for key in highlighted_regions(drug)},
        'members': detail['members'] if detail['kind'] == 'system' else [],
        'evidence': detail['evidence'],
        'substance': drug.get('name', drug.get('compound_id', '')) if drug else '未选择物质',
    }


def read_selection(line):
    try:
        message = json.loads(line)
        if (isinstance(message, dict) and message.get('event') == 'select'
                and isinstance(message.get('region'), str) and message['region'] in REGIONS):
            return message['region']
    except (ValueError, TypeError):
        pass
    return None
