import unittest
from src.context import normalize_context
from src.simulation import simulate
from test_simulation import row


class ContextTests(unittest.TestCase):
    def test_unknown_stays_unknown(self):
        context = normalize_context(None)
        self.assertIsNone(context['physiology']['weight_kg'])
        self.assertEqual(context['physiology']['physiological_sex'], 'unknown')
        self.assertEqual(context['applied_modifiers'], [])

    def test_invalid_values_and_unknown_keys_refuse(self):
        for profile in ({'weight_kg': -1}, {'body_fat_percent': 101},
                        {'height_cm': float('nan')}, {'physiological_sex': 'guess'},
                        {'weight_kg': True}, {'unsupported': 1}):
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                normalize_context({'physiology': profile})

    def test_gene_result_is_not_inferred_activity(self):
        context = normalize_context({'genes': [{'gene': 'CYP2D6', 'result': '*1/*4', 'source': 'synthetic test'}]})
        self.assertEqual(context['genes'][0]['phenotype'], 'NOT_INFERRED')
        self.assertIn('GENE_MECHANISM_MODEL_NOT_VALIDATED', context['gaps'])

    def test_context_changes_hash_not_unvalidated_exposure(self):
        a = simulate([row()], {'physiology': {'weight_kg': 60}})
        b = simulate([row()], {'physiology': {'weight_kg': 90}})
        self.assertNotEqual(a['input_sha256'], b['input_sha256'])
        self.assertEqual(a['curves'], b['curves'])
        self.assertEqual(b['context']['applied_modifiers'], [])

    def test_supplement_category_preserved_and_unknown_composition_flagged(self):
        result = simulate([dict(row(), category='supplement')])
        self.assertIn('COMPOSITION_NOT_RESOLVED', result['entries'][0]['gaps'])
        self.assertEqual(result['entries'][0]['category'], 'supplement')

