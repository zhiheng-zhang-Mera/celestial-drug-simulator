"""Behavioral checks for public label identity, evidence and offline persistence."""
import importlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import parse_qs, urlparse


def item(compound_id, **extra):
    return dict(name=compound_id, kind='catalog', compound_id=compound_id,
                route='oral', **extra)


def response_for(ingredient, *, section=True, route='ORAL', combination=False):
    label = {
        'set_id': '11111111-2222-4333-8444-555555555555',
        'effective_time': '20261001',
        'openfda': {'generic_name': [ingredient.upper()],
                    'substance_name': [ingredient.upper()], 'route': [route]},
        'description': [ingredient + ' tablets for oral administration.'],
    }
    if combination:
        label['openfda']['substance_name'].append('OTHER ACTIVE INGREDIENT')
    if section:
        if ingredient == 'estradiol':
            label['clinical_pharmacology'] = [
                'Drug Interactions. Estrogens are metabolized partially by cytochrome P450 3A4 (CYP3A4).']
        elif ingredient == 'bicalutamide':
            label['drug_interactions'] = [
                'In vitro studies have shown that R-bicalutamide is an inhibitor of CYP 3A4.']
    return json.dumps({'results': [label]}).encode()


class DrugLibraryTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('src.drug_library'),
                             'Drug label library service is missing')
        self.lib = importlib.import_module('src.drug_library')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cache = Path(self.temp.name)

    def analyze(self, entries, online=False, transport=None):
        return self.lib.analyze_labels(entries, online=online,
                                       cache_dir=self.cache, transport=transport)

    def test_exact_aliases_resolve_without_guessing_ester_or_combination(self):
        for name, expected in [('雌二醇', 'estradiol'), ('雌二醇 / estradiol', 'estradiol'), ('比卡鲁胺', 'bicalutamide'),
                               ('  ESTRADIOL  ', 'estradiol'), ('氟康唑', 'fluconazole')]:
            self.assertEqual(self.lib.resolve_name(name), expected)
        for name in ['estradiol valerate', 'estradiol + bicalutamide', '雌二醇注射剂', 'atomoxetine', '', None]:
            self.assertIsNone(self.lib.resolve_name(name))

    def test_defaults_keep_route_population_and_missing_half_life(self):
        estradiol = self.lib.profile_for('estradiol')
        self.assertIsNone(estradiol['half_life_h'])
        self.assertEqual(estradiol['formulation'], 'micronized oral tablet')
        bica = self.lib.profile_for('bicalutamide')
        self.assertAlmostEqual(bica['half_life_h'], 139.2)
        self.assertIn('n=30', bica['population'])
        self.assertIn('R-', bica['parameter_note'])
        self.assertEqual(self.lib.profile_for('fluconazole')['half_life_h'], 30)
        for route in ['transdermal', 'iv_bolus', '', 'unknown']:
            profile = self.lib.profile_for('bicalutamide', route)
            self.assertIsNone(profile['half_life_h'])
            self.assertEqual(profile['route'], route)
        self.assertIsNone(self.lib.profile_for('not-a-drug'))

    def test_offline_pair_uses_two_curated_sections_and_never_admits_prediction(self):
        result = self.analyze([item('estradiol'), item('bicalutamide')])
        self.assertEqual([r['status'] for r in result['records']], ['seed', 'seed'])
        pair = result['pairs'][0]
        self.assertEqual(pair['status'], 'MECHANISM_INFERENCE')
        self.assertEqual(len(pair['sources']), 2)
        self.assertFalse(pair['prediction_admitted'])
        self.assertNotIn('auc_ratio', pair)
        self.assertTrue(all(r['fact_evidence'][0]['section'] for r in result['records']))

    def test_seed_without_cache_works_earlier_on_review_date(self):
        from datetime import datetime, timezone
        from unittest.mock import patch
        with patch('src.drug_library.datetime', wraps=datetime) as clock:
            clock.now.return_value = datetime(2026, 11, 5, 9, tzinfo=timezone.utc)
            result = self.analyze([item('estradiol'), item('bicalutamide')])
        self.assertEqual([r['status'] for r in result['records']], ['seed', 'seed'])
        self.assertEqual(result['pairs'][0]['status'], 'MECHANISM_INFERENCE')

    def test_historical_sources_are_visible_at_pair_level(self):
        from datetime import datetime, timezone
        from unittest.mock import patch
        with patch('src.drug_library.datetime', wraps=datetime) as clock:
            clock.now.return_value = datetime(2030, 1, 1, tzinfo=timezone.utc)
            result = self.analyze([item('estradiol'), item('bicalutamide')])
        pair = result['pairs'][0]
        self.assertTrue(pair.get('stale'))
        self.assertIn('历史', pair['summary'])
        self.assertFalse(pair['prediction_admitted'])

    def test_custom_name_or_spoofed_id_cannot_promote_identity_or_send_input(self):
        def forbidden(_):
            self.fail('Unconfirmed custom input must not be transmitted')
        entries = [dict(item('estradiol'), kind='custom', name='estradiol'),
                   dict(item('bicalutamide'), kind='synthetic'),
                   item('../private-profile')]
        result = self.analyze(entries, online=True, transport=forbidden)
        self.assertTrue(all(r['status'] == 'unknown' for r in result['records']))
        self.assertTrue(all(p['status'] == 'INSUFFICIENT_EVIDENCE' for p in result['pairs']))
        self.assertEqual(list(self.cache.iterdir()), [])

    def test_online_query_only_contains_public_canonical_ingredient(self):
        requests = []
        def transport(url):
            requests.append(url)
            return response_for('estradiol')
        row = item('estradiol', patient_name='PRIVATE PERSON', genotype='PRIVATE GENE')
        row['name'] = 'PRIVATE DISPLAY NAME'
        record = self.analyze([row], online=True, transport=transport)['records'][0]
        self.assertEqual(record['status'], 'online')
        query = parse_qs(urlparse(requests[0]).query)
        self.assertEqual(query['search'], ['openfda.generic_name.exact:"ESTRADIOL" AND openfda.route.exact:"ORAL"'])
        self.assertEqual(query['limit'], ['1'])
        self.assertNotIn('PRIVATE', requests[0])
        self.assertNotIn('PRIVATE', ''.join(p.read_text('utf-8') for p in self.cache.iterdir()))
        self.assertEqual(len(record['content_sha256']), 64)

    def test_successful_refresh_then_failed_refresh_retains_valid_cache(self):
        first = self.analyze([item('estradiol')], True, lambda _: response_for('estradiol'))
        before = {p.name: p.read_bytes() for p in self.cache.iterdir()}
        def offline(_):
            raise OSError('offline')
        cached = self.analyze([item('estradiol')], True, offline)['records'][0]
        self.assertEqual(cached['status'], 'cache')
        self.assertIn('error', cached)
        self.assertEqual(cached['content_sha256'], first['records'][0]['content_sha256'])
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.cache.iterdir()})

    def test_online_is_attempted_even_with_fresh_cache(self):
        self.analyze([item('estradiol')], True, lambda _: response_for('estradiol'))
        fresh = self.analyze([item('estradiol')], True, lambda _: response_for('estradiol', section=False))
        self.assertEqual(fresh['records'][0]['status'], 'online')
        self.assertEqual(fresh['records'][0]['fact_evidence'], [])

    def test_missing_actual_section_does_not_inherit_seed_pair_fact(self):
        def transport(url):
            name = 'estradiol' if 'ESTRADIOL' in url else 'bicalutamide'
            return response_for(name, section=(name == 'bicalutamide'))
        result = self.analyze([item('estradiol'), item('bicalutamide')], True, transport)
        self.assertEqual(result['pairs'][0]['status'], 'INSUFFICIENT_EVIDENCE')
        self.assertEqual(result['records'][0]['fact_evidence'], [])

    def test_wrong_ingredient_route_or_combination_fails_closed_to_seed(self):
        for raw in [response_for('ethinyl estradiol'), response_for('estradiol', route='TRANSDERMAL'),
                    response_for('estradiol', combination=True), b'{broken']:
            with self.subTest(raw=raw[:80]):
                record = self.analyze([item('estradiol')], True, lambda _: raw)['records'][0]
                self.assertEqual(record['status'], 'seed')
                self.assertIn('error', record)
                self.assertEqual(list(self.cache.iterdir()), [])

    def test_corrupt_cache_cannot_supply_pair_evidence(self):
        self.analyze([item('estradiol')], True, lambda _: response_for('estradiol'))
        file = next(self.cache.iterdir())
        data = json.loads(file.read_text('utf-8'))
        data['content_sha256'] = '0' * 64
        file.write_text(json.dumps(data), encoding='utf-8')
        record = self.analyze([item('estradiol')])['records'][0]
        self.assertEqual(record['status'], 'seed')
        self.assertIn('cache_error', record)
        self.assertNotEqual(record['content_sha256'], '0' * 64)

    def test_expired_cache_is_reported_as_stale_with_original_timestamp(self):
        self.analyze([item('estradiol')], True, lambda _: response_for('estradiol'))
        file = next(self.cache.iterdir())
        data = json.loads(file.read_text('utf-8'))
        data['payload']['retrieved_at'] = '2020-01-01T00:00:00+00:00'
        import hashlib
        data['content_sha256'] = hashlib.sha256(json.dumps(data['payload'], sort_keys=True,
            ensure_ascii=False, allow_nan=False).encode()).hexdigest()
        file.write_text(json.dumps(data), encoding='utf-8')
        record = self.analyze([item('estradiol')])['records'][0]
        self.assertEqual(record['status'], 'cache')
        self.assertTrue(record['stale'])
        self.assertGreater(record['age_days'], 30)
        self.assertEqual(record['retrieved_at'], '2020-01-01T00:00:00+00:00')

    def test_boolean_cache_schema_is_rejected_even_with_valid_content_hash(self):
        self.analyze([item('estradiol')], True, lambda _: response_for('estradiol'))
        file = next(self.cache.iterdir())
        data = json.loads(file.read_text('utf-8'))
        data['schema'] = True
        file.write_text(json.dumps(data), encoding='utf-8')
        record = self.analyze([item('estradiol')])['records'][0]
        self.assertEqual(record['status'], 'seed')
        self.assertIn('cache_error', record)

    def test_future_cache_timestamp_and_rehashed_unsupported_fact_are_rejected(self):
        import hashlib
        for mutation in ['future', 'unsupported_fact']:
            self.analyze([item('estradiol')], True, lambda _: response_for('estradiol'))
            file = next(self.cache.iterdir())
            data = json.loads(file.read_text('utf-8'))
            if mutation == 'future':
                data['payload']['retrieved_at'] = '2999-01-01T00:00:00+00:00'
            else:
                data['payload']['fact_evidence'][0]['excerpt'] = 'Unsupported conclusion'
            data['content_sha256'] = hashlib.sha256(json.dumps(data['payload'], sort_keys=True,
                ensure_ascii=False, allow_nan=False).encode()).hexdigest()
            file.write_text(json.dumps(data), encoding='utf-8')
            record = self.analyze([item('estradiol')])['records'][0]
            self.assertEqual(record['status'], 'seed')
            self.assertIn('cache_error', record)

    def test_matching_words_in_unrelated_section_are_not_mechanism_evidence(self):
        data = json.loads(response_for('bicalutamide'))
        label = data['results'][0]
        label['how_supplied'] = label.pop('drug_interactions')
        raw = json.dumps(data).encode()
        record = self.analyze([item('bicalutamide')], True, lambda _: raw)['records'][0]
        self.assertEqual(record['status'], 'online')
        self.assertEqual(record['fact_evidence'], [])

    def test_transport_rejects_oversized_body_and_unofficial_url(self):
        from unittest.mock import patch
        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def geturl(self):
                return 'https://api.fda.gov/drug/label.json'
            def read(self, limit):
                return b'x' * limit
        class Opener:
            def open(self, request, timeout):
                if timeout > 15:
                    raise AssertionError('HTTP timeout must be bounded')
                return Response()
        with patch('src.drug_library.build_opener', return_value=Opener()):
            with self.assertRaises(ValueError):
                self.lib.fetch('https://api.fda.gov/drug/label.json')
            for url in ['https://evil.example/drug/label.json', 'http://api.fda.gov/drug/label.json']:
                with self.assertRaises(ValueError):
                    self.lib.fetch(url)

    def test_unsupported_route_has_no_borrowed_oral_mechanism(self):
        result = self.analyze([dict(item('estradiol'), route='transdermal'), item('bicalutamide')])
        self.assertEqual(result['records'][0]['status'], 'unsupported_route')
        self.assertEqual(result['records'][0]['fact_evidence'], [])
        self.assertEqual(result['pairs'][0]['status'], 'INSUFFICIENT_EVIDENCE')

    def test_all_pairs_up_to_32_and_bound_overflow(self):
        result = self.analyze([dict(item('estradiol'), kind='custom', name=str(n)) for n in range(32)])
        self.assertEqual(len(result['pairs']), 496)
        for rows in [[], [item('estradiol')] * 33]:
            with self.assertRaises(ValueError):
                self.analyze(rows)


if __name__ == '__main__':
    unittest.main()
