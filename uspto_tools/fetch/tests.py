""" Unit-test suite.

Copyright (c) 2017 clicumu
Licensed under MIT license as described in LICENSE.txt
"""

import collections
import unittest

from bs4 import BeautifulSoup

from uspto_tools.fetch import patft

id_pair = collections.namedtuple('IdPair', ['patent_id', 'family_id'])

GOOD_PAIR = id_pair(6187568, 1341416)
GOOD_PAIR2 = id_pair(4376120, 3560569)
PAIR_BAD_PID = id_pair(20050037444, 3636418)
BAD_PAIR = id_pair(20020197269, 3635970)


class TestFetch(unittest.TestCase):
    def test_fetch_present_patent_gets_soup(self):
        soup = patft.fetch_with_patent_id_and_family_id(*GOOD_PAIR)
        self.assertIsInstance(soup, BeautifulSoup)

    def test_raises_on_absent_pid(self):
        self.assertRaises(patft.RetrievalIsEmpty,
                          patft.fetch_with_patent_id_and_family_id,
                          *PAIR_BAD_PID)

    def test_fetch_family_gets_dict_of_soups(self):
        family = patft.fetch_patent_family(PAIR_BAD_PID.family_id)
        self.assertIsInstance(family, dict)
        for id_, soup in family.items():
            self.assertIsInstance(id_, str)
            self.assertTrue(id_.isdigit())
            self.assertIsInstance(soup, BeautifulSoup)
            try:
                patft.check_retrieval_is_not_empty(soup)
            except patft.RetrievalIsEmpty:
                self.fail('Failed to fetch patent from family')

    def test_raises_on_absent_famid(self):
        self.assertRaises(patft.RetrievalIsEmpty,
                          patft.fetch_patent_family,
                          BAD_PAIR.family_id)

    def test_fetch_multiple_good_retrieves_all(self):
        patents = patft.fetch_multiple_patents([GOOD_PAIR.patent_id,
                                                GOOD_PAIR2.patent_id,
                                                PAIR_BAD_PID.patent_id])

        self.assertEqual(len(patents), 2)
        self.assertIn(str(GOOD_PAIR.patent_id), patents)
        self.assertIn(str(GOOD_PAIR2.patent_id), patents)

        for soup in patents.values():
            self.assertIsInstance(soup, BeautifulSoup)

    def test_fetch_multiple_raises_on_empty_retrieval(self):
        self.assertRaises(
            patft.RetrievalIsEmpty,
            patft.fetch_multiple_patents,
            [BAD_PAIR.patent_id, PAIR_BAD_PID.patent_id]
        )


if __name__ == '__main__':
    unittest.main()
