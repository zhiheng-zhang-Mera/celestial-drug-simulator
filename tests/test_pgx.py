import math
import unittest
from src.pgx import estimate, phenotype
from src.sources import load_snapshot
from pathlib import Path
from datetime import datetime, timezone
import json

def fixture():
    data = json.loads((Path(__file__).parent / 'fixtures' / 'cpic-sources.json').read_text(encoding='utf-8'))
    data['retrieved_at'] = datetime.now(timezone.utc).isoformat()
    return data

class PgxTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = fixture()
        self.case = dict(weight_kg=70, age_years=30, dose_mg=40, diplotype='*1/*1', source='synthetic fixture', scenario_confirmed=True, route='oral', compound_id='atomoxetine', concomitants=[])
    def test_real_mapping_and_reversed_alleles(self):
        self.assertEqual(phenotype('*4/*1', self.snapshot)['generesult'], 'Intermediate Metabolizer')
        self.assertEqual(phenotype('*4/*4', self.snapshot)['totalactivityscore'], '0.0')
    def test_weight_and_gene_modify_numeric_result(self):
        normal = estimate(self.case, self.snapshot)
        poor = estimate(dict(self.case, diplotype='*4/*4'), self.snapshot)
        heavy = estimate(dict(self.case, weight_kg=100), self.snapshot)
        self.assertAlmostEqual(normal['apparent_clearance_l_h'], 24.5)
        self.assertAlmostEqual(poor['auc_per_dose_mg_h_l'], 40 / 2.1)
        self.assertAlmostEqual(heavy['auc_per_dose_mg_h_l'], 40 / 35)
        self.assertEqual(poor['half_life_h'], 21.6)
        self.assertFalse(poor['clinical_prediction_validated'])
    def test_domain_refuses(self):
        for change in ({'diplotype':'*1/*4'}, {'diplotype':'*1x2/*4'}, {'weight_kg':float('nan')}, {'weight_kg':True}, {'age_years':12}, {'scenario_confirmed':False}, {'source':''}, {'route':'iv_bolus'}, {'compound_id':'custom'}, {'concomitants':['fluoxetine']}, {'dose_mg':1000}):
            with self.subTest(change=change), self.assertRaises(ValueError): estimate(dict(self.case, **change), self.snapshot)
    def test_tampered_mapping_refuses(self):
        import copy
        bad = copy.deepcopy(self.snapshot)
        bad['diplotypes']['data'][0]['generesult'] = 'Poor Metabolizer'
        with self.assertRaises(ValueError): estimate(self.case, bad)

class SourceTests(unittest.TestCase):
    def test_failure_replaces_success_not_silent_stale(self):
        import tempfile
        from pathlib import Path
        from src.sources import refresh_sources
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'sources.json'
            def fail(_): raise OSError('offline')
            result = refresh_sources(path, fail)
            self.assertEqual(result['diplotypes']['status'], 'FETCH_FAILED')
            with self.assertRaises(ValueError): load_snapshot(path)
    def test_expiry_and_pair_identity(self):
        import copy
        from src.sources import validate_snapshot, digest
        data = fixture()
        for change in ('expiry', 'pair'):
            bad = copy.deepcopy(data)
            if change == 'expiry': bad['retrieved_at'] = '2020-01-01T00:00:00+00:00'
            else:
                bad['pair']['data'][0]['removed'] = True
                bad['pair']['data_sha256'] = digest(bad['pair']['data'])
            with self.assertRaises(ValueError): validate_snapshot(bad)

class MayoTests(unittest.TestCase):
    def test_mechanism_fact_from_real_page(self):
        from src.sources import mayo_facts
        self.assertEqual(mayo_facts('<h1>Atomoxetine (oral route)</h1><h2>Description</h2><p>It belongs to selective norepinephrine reuptake inhibitors.</p>')['mechanism_class'], 'selective norepinephrine reuptake inhibitor')
        with self.assertRaises(ValueError): mayo_facts('<h1>Access Denied</h1>')


class MalformedTests(unittest.TestCase):
    def test_malformed_rows_fail_with_value_error(self):
        from src.sources import validate_snapshot, digest
        for rows in ([None], ['bad'], {}, [{'diplotype':'*1/*1'}]):
            with self.subTest(rows=rows):
                data=fixture(); data['diplotypes']['data']=rows; data['diplotypes']['data_sha256']=digest(rows)
                with self.assertRaises(ValueError): validate_snapshot(data)
