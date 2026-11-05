import unittest
import math
from unittest.mock import patch
from src.simulation import load_catalog, simulate
from src.exposure import Regimen, concentration


def row(name='A', kind='synthetic', compound_id=''):
    return dict(name=name, kind=kind, compound_id=compound_id, dose_mg=100,
                volume_l=10, half_life_h=4, interval_h=8, count=3,
                route='iv_bolus', source='')


class SimulationTests(unittest.TestCase):
    def test_geometric_sum_matches_direct_dose_oracle(self):
        for half, interval in ((4, 8), (1000, .01), (.001, 100), (1e300, 1e-100)):
            regimen = Regimen(100, 10, half, interval, 20)
            for time in (0, interval, 1.5 * interval, 19 * interval, 50 * interval):
                expected = sum(10 * math.exp(-math.log(2) * ((time - i * interval) / half))
                               for i in range(20) if time >= i * interval)
                self.assertAlmostEqual(concentration(regimen, time), expected, delta=1e-10)

    def test_large_plan_bounds_display_samples(self):
        result = simulate([dict(row(str(i)), count=1000, interval_h=1 + i / 100)
                           for i in range(32)])
        self.assertLessEqual(len(result['times_h']), 2048)
        self.assertEqual(len(result['pairs']), 496)

    def test_missing_source_is_reportable(self):
        catalog = load_catalog()
        catalog['sources'] = []
        with patch('src.simulation.load_catalog', return_value=catalog):
            result = simulate([row('F', 'catalog', 'fluconazole'), row('M', 'catalog', 'midazolam')])
        self.assertEqual(result['pairs'][0]['evidence'][0]['structural_check'], 'MISSING_PROVENANCE')

    def test_three_drugs_all_pairs_and_exposure(self):
        result = simulate([row(n) for n in 'ABC'])
        self.assertEqual(len(result['pairs']), 3)
        self.assertEqual(len(result['curves']), 3)
        self.assertEqual(result['curves'][0]['values'][0], 10)
        self.assertEqual(result['overall'], 'INSUFFICIENT_EVIDENCE')

    def test_real_sources_do_not_approve_prediction(self):
        result = simulate([row('F', 'catalog', 'fluconazole'), row('M', 'catalog', 'midazolam')])
        self.assertEqual(result['pairs'][0]['status'], 'HOLD_FOR_REVIEW')
        self.assertEqual(result['pairs'][0]['evidence'][0]['auc_ratio'], 3.59)
        self.assertEqual(result['curves'], [])
        self.assertEqual(result['pairs'][0]['evidence'][0]['applicability'], 'CONTEXT_MISMATCH')

    def test_custom_named_like_catalog_never_inherits_evidence(self):
        result = simulate([row('fluconazole', 'custom'), row('midazolam', 'custom')])
        self.assertEqual(result['pairs'][0]['evidence'], [])
        self.assertEqual(len(result['curves']), 2)
        self.assertEqual(result['curves'][0]['interpretation'], 'UNVERIFIED_USER_PARAMETER_WHAT_IF_NO_DDI')

    def test_invalid_inputs_rejected(self):
        for items in ([], [row()] * 33, [row(), row()], [row(' ')],
                      [dict(row(), dose_mg=float('nan'))],
                      [row('X', 'catalog', 'missing')], [dict(row(), count=2.5)]):
            with self.subTest(items=items), self.assertRaises(ValueError):
                simulate(items)

    def test_oral_does_not_use_iv_equation(self):
        result = simulate([dict(row(), route='oral')])
        self.assertEqual(result['curves'], [])
        self.assertIn('UNSUPPORTED_ROUTE', result['entries'][0]['gaps'])

    def test_source_snapshot_and_request_hash(self):
        a = simulate([row()])
        b = simulate([dict(row(), dose_mg=50)])
        self.assertNotEqual(a['input_sha256'], b['input_sha256'])
        self.assertEqual(len(a['snapshot_sha256']), 64)
        catalog = load_catalog()
        self.assertTrue(catalog['sources'][0]['url'].startswith('https://dailymed.nlm.nih.gov/'))
        self.assertEqual(catalog['sources'][0]['review_status'], 'PENDING_REVIEW')

    def test_every_pair_missing_remains_unknown(self):
        result = simulate([row('F', 'catalog', 'fluconazole'),
                           row('M', 'catalog', 'midazolam'), row('未知药', 'custom')])
        self.assertEqual(len(result['pairs']), 3)
        self.assertEqual(sum(bool(p['evidence']) for p in result['pairs']), 1)
        self.assertEqual(result['overall'], 'INSUFFICIENT_EVIDENCE')

if __name__ == '__main__':
    unittest.main()
