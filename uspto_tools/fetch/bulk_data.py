""" This module contain utility functions to fetch data from
https://bulkdata.uspto.gov/

Copyright (c) 2017 clicumu
Licensed under MIT license as described in LICENSE.txt
"""
import re
import zipfile
import logging

from bs4 import BeautifulSoup

from uspto_tools import parse
from uspto_tools.parse.exceptions import ParseError


def get_full_text_links(session, text_format=None,
                        start_year=None, end_year=None):
    """ Get list of full-text URL:s from bulkdata.uspto.gov.

    Parameters
    ----------
    session : requests.Session
        Session-instance to fetch data.
    text_format : {'APS', 'XML', 'SGML'}, optional
        If provided, filter links by format.

    Returns
    -------
    hrefs : link[str]
        URL:s to full-text pages.
    """
    url = 'https://bulkdata.uspto.gov/'
    response = session.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    all_links = soup.find_all('a')
    filter_str = 'Patent Grant Full Text Data'
    if text_format is not None:
        filter_str += '/{}'.format(text_format.upper())

    links = [link for link in all_links if link.text.startswith(filter_str)]
    year_pattern = r'.*\(JAN (\d{4}) - DEC \d{4}\)'
    if start_year is not None:
        links = [link for link in links if
                 int(re.match(year_pattern, link.text).group(1)) >= start_year]
    if end_year is not None:
        links = [link for link in links if
                 int(re.match(year_pattern, link.text).group(1)) <= end_year]

    hrefs = [link['href'] for link in links]
    return hrefs


def get_zip_links(session, url, filter_pattern=None):
    """ Get list of all zip-files at `url`.

    Parameters
    ----------
    session : requests.Session
        Session-instance to fetch data with.
    url : str
        URL-string.
    filter_pattern : str, optional
        Regexp pattern to filter link-texts.

    Returns
    -------
    hrefs : list[str]
        URL:s to zip-files.
    """
    response = session.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    all_links = soup.find_all('a')
    zip_links = [link for link in all_links if link.text.endswith('.zip')]
    if filter_pattern:
        zip_links = [link for link in zip_links
                     if re.match(filter_pattern, link.text)]

    zip_names = [link['href'] for link in zip_links]
    hrefs = ['/'.join([url, name]) for name in zip_names]
    return hrefs


def get_patents_from_zip(zip_file):
    """ Unzip and parse patents in USPTO bulk-data zip-file.

    Parameters
    ----------
    zip_file : str, file-like
        File containing USPTO full-text data.

    Returns
    -------
    list[uspto_tools.parse.patent.USPatent]
        Parsed patents.
    int
        Number of parse-failures.
    """
    zip_file = zipfile.ZipFile(zip_file)
    unzipped = {name: zip_file.read(name) for name in zip_file.namelist()}

    patents = list()
    n_failures = 0
    for name, file in unzipped.items():
        name_match = re.search(r'.*((?:pg|pftaps|ipg)\d+.*)', name)
        if name_match is None:
            continue

        cleaned_name = name_match.groups()[0]
        if isinstance(file, bytes):
            file = file.decode()

        if cleaned_name.startswith('pftaps'):
            splitter = parse.aps.chunk_aps_file
            parser = parse.aps.parse_aps_chunk
        else:
            is_v4 = re.search(r'us-patent-grant-v4\d', file[:200]) is not None
            if cleaned_name.startswith('pg') and not is_v4:
                splitter = parse.sgml.chunk_sgml_file
                parser = parse.sgml.parse_sgml_chunk
            elif cleaned_name.startswith('ipg') or is_v4:
                splitter = parse.xml.chunk_xml_file
                parser = parse.xml.parse_xml_chunk
            else:
                logging.info('Ignoring: {}'.format(name))
                continue

        for chunk in splitter(file):
            try:
                patent = parser(chunk)
            except ParseError:
                n_failures += 1
                continue
            patents.append(patent)

    return patents, n_failures