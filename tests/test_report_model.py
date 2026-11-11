"""Unit tests for the pure report view model (no Tk, no network)."""
import copy
import tempfile
import unittest
from pathlib import Path

from src import report_model
from src.drug_library import analyze_labels
from src.simulation import simulate


def entry(name, kind='custom', compound_id='', route='oral', **extra):
    item = dict(name=name, kind=kind, compound_id=compound_id, category='medicine',
                route=route, source='', dose_mg=None, interval_h=None, count=None,
                model_mode='evidence', volume_l=None, half_life_h=None)
    item.update(extra)
    return item


class ReportModelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cache = Path(self.temp.name)

    def labels(self, items):
        return analyze_labels(items, online=False, cache_dir=self.cache)

    def build(self, items):
        return simulate(items), self.labels(items)

    def test_single_substance_has_individual_view_and_no_pairs(self):
        result, labels = self.build([entry('雌二醇', 'catalog', 'estradiol')])
        individuals = report_model.individual_view(result, labels)
        self.assertEqual(len(individuals), 1)
        person = individuals[0]
        self.assertEqual(person['name'], '雌二醇')
        self.assertEqual(person['kind'], 'catalog')
        self.assertEqual(person['route'], 'oral')
        self.assertIn('CYP3A4', person['mechanism']['text'])
        self.assertEqual(person['regions'], [])
        self.assertTrue(person['source_url'].startswith('https://dailymed.nlm.nih.gov/'))
        self.assertEqual(report_model.interaction_view(result, labels), [])
        overview = report_model.overview_view(result, labels)
        self.assertEqual(overview['counts']['substances'], 1)
        self.assertEqual(overview['counts']['pairs'], 0)
        self.assertEqual(overview['counts']['mechanism_pairs'], 0)
        self.assertIn('未计算个体暴露/效应预测', overview['disclaimer'])
        self.assertIn('未计算联合风险倍率', overview['disclaimer'])

    def test_two_substances_show_individual_lines_and_cross_mechanism(self):
        result, labels = self.build([entry('雌二醇', 'catalog', 'estradiol'),
                                     entry('比卡鲁胺', 'catalog', 'bicalutamide')])
        individuals = report_model.individual_view(result, labels)
        self.assertEqual([item['name'] for item in individuals], ['雌二醇', '比卡鲁胺'])
        self.assertIn('CYP3A4', individuals[0]['mechanism']['text'])
        self.assertIn('CYP3A4', individuals[1]['mechanism']['text'])
        interactions = report_model.interaction_view(result, labels)
        self.assertEqual(len(interactions), 1)
        pair = interactions[0]
        self.assertEqual(pair['names'], ['雌二醇', '比卡鲁胺'])
        self.assertEqual(pair['status'], 'MECHANISM_INFERENCE')
        self.assertEqual(pair['a']['name'], '雌二醇')
        self.assertEqual(pair['b']['name'], '比卡鲁胺')
        self.assertIn('CYP3A4', pair['a']['summary'])
        self.assertIn('CYP3A4', pair['b']['summary'])
        self.assertEqual(pair['a']['region_text'], report_model.MISSING_REGIONS)
        self.assertIn('CYP3A4', pair['summary'])
        self.assertEqual(len(pair['sources']), 2)
        self.assertEqual(pair['studies'], [])
        overview = report_model.overview_view(result, labels)
        self.assertEqual(overview['counts']['pairs'], 1)
        self.assertEqual(overview['counts']['mechanism_pairs'], 1)

    def test_three_substances_produce_three_pairs(self):
        result, labels = self.build([entry('雌二醇', 'catalog', 'estradiol'),
                                     entry('比卡鲁胺', 'catalog', 'bicalutamide'),
                                     entry('氟康唑', 'catalog', 'fluconazole')])
        interactions = report_model.interaction_view(result, labels)
        self.assertEqual(len(interactions), 3)
        self.assertEqual([pair['names'] for pair in interactions],
                         [['雌二醇', '比卡鲁胺'], ['雌二醇', '氟康唑'],
                          ['比卡鲁胺', '氟康唑']])
        overview = report_model.overview_view(result, labels)
        self.assertEqual(overview['counts']['substances'], 3)
        self.assertEqual(overview['counts']['pairs'], 3)

    def test_missing_labels_state_is_explicit_not_invented(self):
        result = simulate([entry('未知物质')])
        individuals = report_model.individual_view(result, None)
        person = individuals[0]
        self.assertEqual(person['mechanism']['text'], report_model.MISSING_MECHANISM)
        self.assertEqual(person['mechanism']['source'], 'missing')
        self.assertEqual(person['record_status'], 'unavailable')
        self.assertEqual(person['source_url'], '')
        self.assertEqual(person['regions'], [])
        self.assertEqual(report_model.interaction_view(result, None), [])

    def test_profile_facts_are_used_when_the_label_record_has_no_mechanism(self):
        result = simulate([entry('雌二醇', 'catalog', 'estradiol')])
        person = report_model.individual_view(result, None)[0]
        self.assertEqual(person['mechanism']['source'], 'profile_facts')
        self.assertIn('CYP3A4', person['mechanism']['text'])

    def test_gap_codes_map_to_chinese_and_keep_the_code(self):
        result = simulate([entry('补充剂', category='supplement')])
        person = report_model.individual_view(result, None)[0]
        codes = [gap['code'] for gap in person['gaps']]
        for expected in ('COMPOSITION_NOT_RESOLVED', 'PARAMETERS_NOT_REVIEWED',
                         'MODEL_DOMAIN_NOT_VALIDATED', 'UNSUPPORTED_ROUTE',
                         'NO_VALIDATED_EXPOSURE_MODEL'):
            self.assertIn(expected, codes)
        mapping = {gap['code']: gap['label'] for gap in person['gaps']}
        self.assertEqual(mapping['COMPOSITION_NOT_RESOLVED'], '成分未解析')
        self.assertEqual(mapping['PARAMETERS_NOT_REVIEWED'], '药代参数未审核')
        self.assertEqual(mapping['MODEL_DOMAIN_NOT_VALIDATED'], '模型适用域未验证')
        self.assertEqual(mapping['UNSUPPORTED_ROUTE'], '该途径无已验证标签')
        self.assertEqual(mapping['NO_VALIDATED_EXPOSURE_MODEL'], '无已验证暴露模型')

        future = copy.deepcopy(result)
        future['entries'][0]['gaps'] = ['FUTURE_GAP']
        unmapped = report_model.individual_view(future, None)[0]['gaps'][0]
        self.assertEqual(unmapped['code'], 'FUTURE_GAP')
        self.assertEqual(unmapped['label'], report_model.UNKNOWN_GAP_LABEL)

    def test_no_gaps_is_rendered_as_an_empty_list(self):
        result = simulate([dict(entry('合成', 'synthetic', route='iv_bolus'),
                                model_mode='synthetic', dose_mg=100, volume_l=10,
                                half_life_h=4, interval_h=8, count=3)])
        self.assertEqual(report_model.individual_view(result, None)[0]['gaps'], [])

    def test_catalog_observations_are_shown_without_admission(self):
        result, labels = self.build([entry('氟康唑', 'catalog', 'fluconazole'),
                                     entry('咪达唑仑', 'catalog', 'midazolam')])
        pair = report_model.interaction_view(result, labels)[0]
        self.assertEqual(pair['status'], 'HOLD_FOR_REVIEW')
        self.assertTrue(pair['has_catalog_observations'])
        self.assertIn('目录研究库', pair['summary'])
        self.assertEqual(len(pair['studies']), 1)
        study = pair['studies'][0]
        self.assertEqual(study['auc_ratio'], 3.59)
        self.assertFalse(study['prediction_admitted'])
        self.assertIn('未准入', study['prediction_text'])
        self.assertTrue(study['source_url'].startswith('https://dailymed.nlm.nih.gov/'))
        self.assertIn(study['source_url'], pair['sources'])

    def test_regions_come_from_the_curated_anatomy_table(self):
        # atomoxetine is not in the curated profile library, so it cannot pass
        # simulate() as a catalog identity; the anatomy table is keyed by the
        # same catalog identity contract, so the region view is tested directly.
        synthetic = dict(kind='catalog', compound_id='atomoxetine', name='阿托莫西汀')
        regions = report_model._region_views(synthetic)
        names = [region['name'] for region in regions]
        self.assertIn('肝脏', names)
        self.assertTrue(all(region['text'] for region in regions))
        self.assertTrue(all(region['category'] for region in regions))

    def test_view_models_never_add_predictions_or_risk_values(self):
        result, labels = self.build([entry('雌二醇', 'catalog', 'estradiol'),
                                     entry('比卡鲁胺', 'catalog', 'bicalutamide'),
                                     entry('氟康唑', 'catalog', 'fluconazole')])
        forbidden = {'predicted_effect', 'prediction', 'risk_ratio', 'risk_multiplier',
                     'effect_size', 'exposure_prediction', 'combined_risk'}
        views = (report_model.overview_view(result, labels),
                 report_model.individual_view(result, labels),
                 report_model.interaction_view(result, labels))

        def walk(value, path=''):
            if isinstance(value, dict):
                for key, child in value.items():
                    self.assertNotIn(key, forbidden, path + '/' + str(key))
                    walk(child, path + '/' + str(key))
            elif isinstance(value, (list, tuple)):
                for index, child in enumerate(value):
                    walk(child, path + f'/{index}')

        for view in views:
            walk(view)
        for pair in report_model.interaction_view(result, labels):
            self.assertFalse(pair['prediction_admitted'])
            for study in pair['studies']:
                self.assertFalse(study['prediction_admitted'])

    def test_inputs_are_not_mutated_by_view_assembly(self):
        result, labels = self.build([entry('雌二醇', 'catalog', 'estradiol'),
                                     entry('比卡鲁胺', 'catalog', 'bicalutamide')])
        result_before = copy.deepcopy(result)
        labels_before = copy.deepcopy(labels)
        report_model.overview_view(result, labels)
        report_model.individual_view(result, labels)
        report_model.interaction_view(result, labels)
        self.assertEqual(result, result_before)
        self.assertEqual(labels, labels_before)


if __name__ == '__main__':
    unittest.main()
