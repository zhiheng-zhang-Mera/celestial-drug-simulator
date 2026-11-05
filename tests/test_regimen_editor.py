import unittest
from src.regimen_ui import editor_item, study_lines


class RegimenEditorTests(unittest.TestCase):
    def test_study_display_preserves_refusals_and_observed_only_values(self):
        text='\n'.join(study_lines(dict(context='study',uncertainty='unknown',
            applicability='CONTEXT_MISMATCH',structural_check='MISSING_PROVENANCE',
            source_location='Section 12',auc_ratio=3.59,source={})))
        for expected in ('CONTEXT_MISMATCH','MISSING_PROVENANCE','Section 12','3.59','未准入'):
            self.assertIn(expected,text)

    def test_exact_chinese_names_resolve_without_manual_half_life(self):
        item=editor_item({'name':'比卡鲁胺'},'oral')
        self.assertEqual(item['compound_id'],'bicalutamide')
        self.assertEqual(item['half_life_h'],139.2)
        self.assertIsNone(item['dose_mg'])

    def test_estradiol_missing_parameter_is_not_a_blocker(self):
        item=editor_item({'name':'雌二醇'},'oral')
        self.assertEqual(item['compound_id'],'estradiol')
        self.assertIsNone(item['half_life_h'])

    def test_explicit_custom_cannot_impersonate_catalog(self):
        item=editor_item({'name':'比卡鲁胺'},'oral',custom=True)
        self.assertEqual(item['kind'],'custom')
        self.assertEqual(item['compound_id'],'')
        self.assertIsNone(item['half_life_h'])

    def test_route_change_clears_unmatched_defaults(self):
        item=editor_item({'name':'比卡鲁胺'},'transdermal')
        self.assertIsNone(item['half_life_h'])
