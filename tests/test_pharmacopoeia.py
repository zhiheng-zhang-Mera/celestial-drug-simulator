"""Pharmacopoeia index, search, cache and Mayo failure-path tests."""
import json
import tempfile
import unittest
from pathlib import Path

from src import pharmacopoeia


SAMPLE_PAGE = """<html><head><title>Estradiol (oral route) - Mayo Clinic</title>
<meta name="description" content="Estradiol is an estrogen used to treat menopausal symptoms.">
</head><body><h1>Estradiol (oral route)</h1>
<h2>Description</h2><p>Estradiol is a form of estrogen, a female sex hormone.</p>
<h2>Before using</h2><p>Tell your doctor about liver disease and blood clots.</p>
</body></html>"""


class PharmacopoeiaTests(unittest.TestCase):
    def test_embedded_index_resolves_valerate_alias(self):
        entries = pharmacopoeia.load_entries(include_cache=False)
        self.assertGreaterEqual(len(entries), 6)
        entry = pharmacopoeia.resolve('戊酸雌二醇', entries=entries)
        self.assertIsNotNone(entry)
        self.assertEqual(entry['identity'], 'estradiol')
        self.assertIn('戊酸雌二醇', entry['names'])

    def test_search_matches_chinese_and_english(self):
        entries = pharmacopoeia.load_entries(include_cache=False)
        self.assertEqual(pharmacopoeia.search('雌', entries=entries)[0]['identity'], 'estradiol')
        self.assertEqual(pharmacopoeia.search('BICALUTAMIDE', entries=entries)[0]['identity'], 'bicalutamide')
        self.assertEqual(pharmacopoeia.search('不存在的药', entries=entries), [])
        self.assertEqual(pharmacopoeia.search('', entries=entries), [])

    def test_source_labels_are_readable(self):
        entry = pharmacopoeia.resolve('estradiol')
        self.assertIn('本地药典', pharmacopoeia.source_label(entry))
        self.assertIn('estradiol', pharmacopoeia.search_url('estradiol'))

    def test_cache_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            record = {'identity': 'estradiol', 'query': 'estradiol', 'title': 'Cached'}
            path = pharmacopoeia.write_cache(record, cache_dir=directory)
            self.assertTrue(Path(path).exists())
            loaded = pharmacopoeia.read_cache('estradiol', cache_dir=directory)
            self.assertEqual(loaded['title'], 'Cached')
            self.assertIsNone(pharmacopoeia.read_cache('missing', cache_dir=directory))

    def test_cached_entries_join_search(self):
        with tempfile.TemporaryDirectory() as directory:
            pharmacopoeia.write_cache(
                {'identity': 'example', 'query': 'Example', 'title': 'Example drug',
                 'url': 'https://example.invalid', 'retrieved_at': '2026-11-12T00:00:00+00:00'},
                cache_dir=directory,
            )
            entries = pharmacopoeia.load_entries(cache_dir=directory)
            identities = {entry['identity'] for entry in entries}
            self.assertIn('example', identities)

    def test_parse_page_extracts_title_and_sections(self):
        page = pharmacopoeia.parse_page(SAMPLE_PAGE, 'https://www.mayoclinic.org/example')
        self.assertIn('Estradiol', page['title'])
        self.assertIn('estrogen', page['excerpt'])
        headings = [section['heading'] for section in page['sections']]
        self.assertIn('Description', headings)
        self.assertIn('Before using', headings)

    def test_mayo_forbidden_is_reported_without_cache(self):
        def transport(url, timeout):
            return 403, ''
        with tempfile.TemporaryDirectory() as directory:
            client = pharmacopoeia.MayoClient(transport=transport, cache_dir=directory)
            with self.assertRaises(pharmacopoeia.PharmacopoeiaError) as raised:
                client.update('estradiol')
            self.assertEqual(raised.exception.code, 'MAYO_FORBIDDEN')
            self.assertEqual(raised.exception.status, 403)
            self.assertEqual(list(Path(directory).glob('*.json')), [])

    def test_mayo_success_caches_parsed_summary(self):
        def transport(url, timeout):
            self.assertIn('estradiol', url)
            return 200, SAMPLE_PAGE
        with tempfile.TemporaryDirectory() as directory:
            client = pharmacopoeia.MayoClient(transport=transport, cache_dir=directory)
            record = client.update('estradiol')
            self.assertEqual(record['status'], 'mayo_cache')
            self.assertTrue(record['sections'])
            self.assertTrue(record['content_sha256'])
            self.assertTrue(pharmacopoeia.read_cache('estradiol', cache_dir=directory))

    def test_mayo_http_error_is_reported(self):
        def transport(url, timeout):
            return 500, ''
        client = pharmacopoeia.MayoClient(transport=transport, cache_dir=tempfile.gettempdir())
        with self.assertRaises(pharmacopoeia.PharmacopoeiaError) as raised:
            client.update('estradiol')
        self.assertEqual(raised.exception.code, 'MAYO_HTTP_ERROR')

    def test_mayo_parse_empty_is_reported(self):
        def transport(url, timeout):
            return 200, '<html><body></body></html>'
        with tempfile.TemporaryDirectory() as directory:
            client = pharmacopoeia.MayoClient(transport=transport, cache_dir=directory)
            with self.assertRaises(pharmacopoeia.PharmacopoeiaError) as raised:
                client.update('unknown')
            self.assertEqual(raised.exception.code, 'MAYO_PARSE_EMPTY')

    def test_mayo_follows_first_drug_monograph_link(self):
        search_page = ('<html><head><title>Search results</title></head><body>'
                       '<a href="/drugs-supplements/estradiol-oral-route/description/drg-20070739">'
                       'Estradiol</a></body></html>')
        detail_url = 'https://www.mayoclinic.org/drugs-supplements/estradiol-oral-route/description/drg-20070739'

        def transport(url, timeout):
            if url == detail_url:
                return 200, SAMPLE_PAGE
            return 200, search_page

        with tempfile.TemporaryDirectory() as directory:
            client = pharmacopoeia.MayoClient(transport=transport, cache_dir=directory)
            record = client.update('estradiol')
            self.assertEqual(record['url'], detail_url)
            self.assertIn('Estradiol', record['title'])
            self.assertIn('estrogen', record['excerpt'])

    def test_index_artifact_is_current(self):
        payload = json.loads(pharmacopoeia.INDEX_PATH.read_text(encoding='utf-8'))
        identities = {entry['identity'] for entry in payload['entries']}
        self.assertIn('estradiol', identities)
        self.assertIn('bicalutamide', identities)


if __name__ == '__main__':
    unittest.main()
