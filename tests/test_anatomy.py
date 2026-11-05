import unittest
from src.anatomy import REGIONS, region_details, highlighted_regions

class AnatomyTests(unittest.TestCase):
    def test_required_regions_present(self):
        self.assertTrue({'brain','liver','stomach','kidneys','testes','uterus','triceps','urinary','metabolic'} <= set(REGIONS))
    def test_identity_not_name_drives_highlights(self):
        custom={'kind':'custom','name':'atomoxetine','compound_id':''}
        self.assertEqual(highlighted_regions(custom), set())
        self.assertIn('liver',highlighted_regions({'kind':'catalog','compound_id':'atomoxetine'}))
    def test_system_membership_does_not_invent_effect(self):
        drug={'kind':'catalog','compound_id':'atomoxetine'}
        detail=region_details(drug,'urinary')
        self.assertIn('kidneys',detail['members'])
        self.assertEqual(detail['evidence'], [])
        self.assertFalse(detail['individual_effect_known'])
    def test_unknown_organs_clear_previous_effects(self):
        drug={'kind':'catalog','compound_id':'atomoxetine'}
        for region in ('testes','uterus','triceps'):
            self.assertEqual(region_details(drug,region)['status'],'INSUFFICIENT_EVIDENCE')
        self.assertEqual(region_details(None,'liver')['evidence'],[])
    def test_every_evidence_has_source_and_class(self):
        drug={'kind':'catalog','compound_id':'atomoxetine'}
        for region in highlighted_regions(drug):
            for item in region_details(drug,region)['evidence']:
                self.assertTrue(item['url'].startswith('https://'))
                self.assertTrue(item['section'])
                self.assertIn(item['category'],('mechanism','metabolism','excretion','label_concern'))
