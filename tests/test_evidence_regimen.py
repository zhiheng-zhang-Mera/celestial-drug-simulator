import unittest
from src.simulation import simulate


def entry(name, **kwargs):
    return dict(name=name, kind='custom', compound_id='', route='oral',
                model_mode='evidence', **kwargs)


class EvidenceRegimenTests(unittest.TestCase):
    def test_names_alone_allow_pair_review_without_iv_parameters(self):
        result=simulate([entry('雌二醇'),entry('比卡鲁胺')])
        self.assertEqual(len(result['pairs']),1)
        self.assertEqual(result['curves'],[])
        self.assertEqual(result['times_h'],[])

    def test_optional_dose_is_validated_when_supplied(self):
        for dose in (-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):simulate([entry('药物',dose_mg=dose)])

    def test_custom_half_life_does_not_create_an_iv_curve_in_evidence_mode(self):
        result=simulate([entry('自定义',half_life_h=4,volume_l=10,dose_mg=100,
                               interval_h=8,count=3)])
        self.assertEqual(result['curves'],[])
        self.assertIn('NO_VALIDATED_EXPOSURE_MODEL',result['entries'][0]['gaps'])

    def test_evidence_mode_route_is_not_silently_iv(self):
        for route in ('oral','transdermal','sublingual','injection','other'):
            result=simulate([dict(entry('药物'),route=route)])
            self.assertEqual(result['entries'][0]['route'],route)
            self.assertEqual(result['curves'],[])
