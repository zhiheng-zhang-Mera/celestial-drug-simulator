import unittest
from src import anatomy


class WebAnatomyContractTests(unittest.TestCase):
    def test_payload_preserves_identity_boundary_and_clears_effects(self):
        from src.web_anatomy import make_state
        state = make_state({'kind': 'catalog', 'compound_id': 'atomoxetine', 'name': '<script>x</script>'}, 'liver')
        self.assertEqual(set(state['effects']), {'brain', 'heart', 'liver', 'kidneys', 'bladder'})
        self.assertEqual(state['selected'], 'liver')
        self.assertEqual(len(state['regions']), 20)
        self.assertEqual(make_state(None, 'liver')['effects'], {})
        self.assertEqual(make_state({'kind': 'custom', 'name': 'atomoxetine'}, 'liver')['effects'], {})

    def test_bridge_accepts_only_known_region_selection(self):
        from src.web_anatomy import read_selection
        self.assertEqual(read_selection('{"event":"select","region":"liver"}'), 'liver')
        for message in ('bad', '[]', '{"event":"select","region":"intestine"}',
                        '{"event":"exec","region":"liver"}', '{"event":"select","region":{}}'):
            self.assertIsNone(read_selection(message))

    def test_payload_rejects_unknown_region(self):
        from src.web_anatomy import make_state
        with self.assertRaises(ValueError):
            make_state(None, 'unknown')

    def test_fallback_preserves_selected_layer_and_back_view(self):
        from src.web_anatomy import fallback_view
        self.assertEqual(fallback_view('uterus'), ('正面','子宫分层'))
        self.assertEqual(fallback_view('testes'), ('正面','睾丸分层'))
        self.assertEqual(fallback_view('triceps'), ('背面','隐藏'))


if __name__ == '__main__':
    unittest.main()
