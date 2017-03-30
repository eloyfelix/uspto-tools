"""  Module for fetching data from http://patft.uspto.gov.

Copyright (c) 2017 clicumu
Licensed under MIT license as described in LICENSE.txt
"""
import re

import requests
from bs4 import BeautifulSoup


PATID_FAMID_QUERY_URL = (
    'http://patft.uspto.gov/netacgi/nph-Parser?Sect1=PTO2&Sect2=HITOFF'
    '&p=1&u=%2Fnetahtml%2FPTO%2Fsearch-bool.html&r=1&f=G&l=50&co1=AND'
    '&d=PTXT&s1={pid}.PN.&s2={fmid}.FMID.&OS=PN/{pid}+AND+FMID/{fmid}'
    '&RS=PN/{pid}+AND+FMID/{fmid}'
)


FAMID_QUERY_URLS = (
    'http://patft.uspto.gov/netacgi/nph-Parser?Sect1=PTO2&Sect2=HITOFF'
    '&p=1&u=%2Fnetahtml%2FPTO%2Fsearch-bool.html&r=0&f=S&l=50'
    '&TERM1={fmid}&FIELD1=FMID&co1=AND&TERM2=&FIELD2=&d=PTXT'
)

ALL_FIELDS_QUERLY_URL = (
    'http://patft.uspto.gov/netacgi/nph-Parser?Sect1=PTO2&Sect2=HITOFF'
    '&p=1&u=%2Fnetahtml%2FPTO%2Fsearch-bool.html&r=1&f=G&l=50&co1=AND'
    '&d=PTXT&s1=%22{term}%22&OS='
)

BULK_SEARCH_URL = (
    'http://patft.uspto.gov/netacgi/nph-Parser?TERM1={term}'
    '&Sect1=PTO1&Sect2=HITOFF&d=PALL&p=1&u=%2Fnetahtml'
    '%2FPTO%2Fsrchnum.htm&r=0&f=S&l=50'
)

URL_ROOT = 'http://patft.uspto.gov'


class RetrievalIsEmpty(Exception):
    pass


def call_and_parse_url(url, method=requests.get):
    """ Call `url` and parse contents using BeautifulSoup.

    Parameters
    ----------
    url : str
        URL to call
    method : Callable
        Function to call `url` with.

    Returns
    -------
    bs4.BeautifulSoup
        Response text content.

    Raises
    ------
    requests.HTTPError
        If GET-request fails.
    """
    response = method(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup


def fetch_searching_all_fields(term):
    """ Make free form search of USPTO patft.

    Spaces will be substituded with plus-signs.

    Parameters
    ----------
    term : str
        Search term.

    Returns
    -------
    bs4.BeautifulSoup
        Response text content.

    Raises
    ------
    requests.HTTPError
        If GET-request fails.
    RetrievalIsEmpty
        If response contained no patent.
    """
    term = term.strip().replace(' ', '+')
    url = ALL_FIELDS_QUERLY_URL.format(term=term)
    soup = call_and_parse_url(url)
    check_retrieval_is_not_empty(soup)
    return soup


def fetch_with_patent_id_and_family_id(patent_id, family_id):
    """ Fetch a single full-text patent from USPTO using query of
    patent-ID and family-ID.

    Parameters
    ----------
    patent_id : int, str
        Patent-ID.
    family_id : int, str
        Patent family-ID.

    Returns
    -------
    bs4.BeautifulSoup
        Response text content.

    Raises
    ------
    requests.HTTPError
        If GET-request fails.
    RetrievalIsEmpty
        If response contained no patent.
    """
    url = PATID_FAMID_QUERY_URL.format(pid=patent_id, fmid=family_id)
    soup = call_and_parse_url(url)
    check_retrieval_is_not_empty(soup)
    return soup


def fetch_patent_family(family_id):
    """ Fetch a complete patent family from USPTO.

    Parameters
    ----------
    family_id : int, str
        Patent family-ID.

    Returns
    -------
    dict[str, bs4.BeautifulSoup]
        Patent-id - patent-html mapping.

    Raises
    ------
    requests.HTTPError
        If GET-request fails.
    RetrievalIsEmpty
        If response contained no patent.
    """
    url = FAMID_QUERY_URLS.format(fmid=family_id)
    family_soup = call_and_parse_url(url)
    check_retrieval_is_not_empty(family_soup)
    return split_bulk_fetch(family_soup)


def fetch_multiple_patents(patent_ids):
    """ Fetch multiple patent-ID:s from USPTO.

    Parameters
    ----------
    patent_ids : list[str], list[int]
        List of patent-ID:s.

    Returns
    -------
    dict[str, bs4.BeautifulSoup]
        Patent-id - patent-html mapping.

    Raises
    ------
    requests.HTTPError
        If GET-request fails.
    RetrievalIsEmpty
        If response contained no patent.
    """
    term = '+'.join(map(str, patent_ids))
    url = BULK_SEARCH_URL.format(term=term)
    soup = call_and_parse_url(url)
    check_retrieval_is_not_empty(soup)
    return split_bulk_fetch(soup)


def split_bulk_fetch(soup):
    """ Fetch all patents from bulk sarch.

    Parameters
    ----------
    soup : bs4.BeautifulSoup
        USPTO bulk search HTML.

    Returns
    -------
    dict[str, bs4.BeautifulSoup]
        Patent-ID - Patent HTML-mapping.
    """
    links = dict()
    for a in soup.find_all('a'):
        id_match = re.match(r'(\d+[,\d+]*)', a.text)
        if id_match is not None:
            raw_id = id_match.group()
            patent_id = raw_id.replace(',', '')
            links[patent_id] = URL_ROOT + a['href']
    return {id_: call_and_parse_url(link) for id_, link in links.items()}


def check_retrieval_is_not_empty(soup):
    """ Check if query return empty results.

    Parameters
    ----------
    soup : bs4.BeautifulSoup
        USPTO patent HTML.

    Raises
    ------
    PatentIsAbsent
        If there is no patent in html.
    """
    second_center = soup.find_all('center')[1]
    next_b = second_center.find_next('b')

    if next_b is None:
        return

    has_result_text = next_b.text.startswith('Results of Search')

    # Now this is pretty...
    if has_result_text:
        no_match = 'No patents have matched' in soup.text

        if has_result_text and no_match:
            raise RetrievalIsEmpty