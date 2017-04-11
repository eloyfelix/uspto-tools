import unittest

from uspto_tools.fetch.tests import GOOD_PAIR

from uspto_tools.fetch import patft
from uspto_tools.parse import patft_html


class TestParse(unittest.TestCase):

    def setUp(self):
        self.soup = patft.fetch_with_patent_id_and_family_id(*GOOD_PAIR)

    def test_parse_abstract(self):
        abstract = patft_html.get_patent_abstract(self.soup)
        self.assertIsInstance(abstract, str)
        self.assertFalse(not abstract)

    def test_parse_claims(self):
        claims = patft_html.get_patent_claims(self.soup)
        self.assertIsInstance(claims, list)
        for claim in claims:
            self.assertIsInstance(claim, str)

    def test_parse_description(self):
        descriptions = patft_html.get_patent_descriptions(self.soup)
        self.assertIsInstance(descriptions, dict)
        for key, value in descriptions.items():
            self.assertTrue(key, str)
            self.assertTrue(key.isupper())
            self.assertIsInstance(value, str)

    def test_parse_id(self):
        id_ = patft_html.get_patent_id(self.soup)
        self.assertIsInstance(id_, str)
        self.assertTrue(id_.isdigit())