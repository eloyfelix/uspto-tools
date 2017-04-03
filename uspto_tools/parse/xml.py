""" This module contains chunker and parser for USPTO XML v4+
full-text used for patents granted 2005-2017.

Copyright (c) 2017 clicumu
Licensed under MIT license as described in LICENSE.txt
"""
from bs4 import BeautifulSoup

from .patent import USPatent, Inventor, PatentClassification, USReference


def chunk_xml_file(xml):
    """ Iterate over patents in XML-file.

    Parameters
    ----------
    xlm : str, file_like
        Path or file-handle to SGML-file or already read XML-contents.
    chunk_on : str
        String to chunk file on. Defaults to "PATDOC".

    Yields
    ------
    chunk : str
        A single patent.
    """
    if isinstance(xml, str):
        try:
            with open(xml) as f:
                contents = f.read()
        except IOError:  # Assume APS-contents.
            contents = xml
    elif hasattr(xml, 'read'):  # File-like.
        contents = xml.read()
    else:
        raise ValueError('invalid sgml')

    lines = contents.splitlines()

    start_tag = '<us-patent-grant'
    end_tag = '</us-patent-grant'

    # Skip header line
    start_i = 0
    for i, line in enumerate(lines):
        if line.startswith(start_tag):
            start_i = i
        elif line.startswith(end_tag):
            yield '\n'.join(lines[start_i:i + 1])


def parse_xml_chunk(chunk):
    """ Parse XML chunk into patent.

    TODO: Parse classifications.

    Parameters
    ----------
    chunk : str
        Single USPTO patent in XML format.

    Returns
    -------
    USPatent
        Parsed patent.
    """
    soup = BeautifulSoup(chunk, 'lxml')
    patent_soup = soup.find('us-patent-grant')
    if patent_soup is None:
        raise ValueError('no patent in chunk.')

    version = patent_soup['dtd-version'].split()[0]
    parsed = dict()
    parsed.update(_parse_pub_ref(patent_soup))
    parsed.update(_parse_app_ref(patent_soup))
    parsed['us_references'] = _parse_us_references(patent_soup, version)
    parsed['series_code'] = safe_text(patent_soup.find('us-application-series-code'))
    parsed['inventors'] = _parse_inventors(patent_soup)
    parsed['primary_examiner'] = _parse_name_group(
        patent_soup.find('primary-examiner'))['name']
    parsed['abstract'] = safe_text(patent_soup.find('abstract'))

    parsed['claims'] = _parse_claims(patent_soup)
    parsed['description'] = safe_text(patent_soup.find('description'))
    parsed['title'] = safe_text(patent_soup.find('invention-title'))

    return USPatent(**parsed)


def _parse_claims(soup):
    """ Parse claims if present.

    Parameters
    ----------
    soup : bs4.BeautifulSoup
        Patent soup.

    Returns
    -------
    list[str] | None
    """
    claims_tag = soup.find('claims')
    if claims_tag is None:
        return None

    claims = [safe_text(tag) for tag in claims_tag.find_all('claim')]
    return claims


def _parse_inventors(soup):
    """ Parse inventors.

    Parameters
    ----------
    soup : bs4.BeautifulSoup
        Patent soup.
    version : str
        Version string on format "v4.x"

    Returns
    -------
    list[Inventor]
    """
    inventor_tags = soup.find('inventors').find_all('inventor')

    inventors = list()
    for tag in inventor_tags:
        parsed = _parse_name_group(tag)
        inventors.append(Inventor(**parsed))

    return inventors


def _parse_name_group(tag):
    """ Parse name-group.

    Parameters
    ----------
    tag : bs4.element.Tag
        Tag containing name-group

    Returns
    -------
    dict[str, str] | None
        None if `tag` is None.
    """
    if tag is None:
        return None

    parsed = dict()
    last_name = safe_text(tag.find('last-name'))
    first_name = safe_text(tag.find('first-name'))

    parsed['name'] = ' '.join(filter(None, [first_name, last_name]))
    parsed.update({
        'city': safe_text(tag.find('city')),
        'country': safe_text(tag.find('country')),
        'state': safe_text(tag.find('state'))
    })
    return parsed


def _parse_pub_ref(soup):
    """ Parse publication reference.

    Parameters
    ----------
    soup : bs4.BeautifulSoup
        Patent soup.

    Returns
    -------
    dict[str, str]
    """
    pub_ref = soup.find('publication-reference')
    parsed = {
        'patent_number': pub_ref.find('doc-number').text.strip(),
        'country': pub_ref.find('country').text.strip(),
        'kind': safe_text(pub_ref.find('kind')),
        'date': safe_text(pub_ref.find('date'))
    }
    return parsed


def _parse_app_ref(soup):
    """ Parse application reference.

    Parameters
    ----------
    soup : bs4.BeautifulSoup
        Patent soup.

    Returns
    -------
    dict[str, str]
    """
    pub_ref = soup.find('application-reference')
    parsed = {
        'application_number': pub_ref.find('doc-number').text.strip(),
        'application_country': pub_ref.find('country').text.strip(),
        'application_date': safe_text(pub_ref.find('date'))
    }
    return parsed


def _parse_us_references(soup, version):
    """ Parse application reference.

    Parameters
    ----------
    soup : bs4.BeautifulSoup
        Patent soup.
    version : str
        Version string on format "v4.x"

    Returns
    -------
    list[USReference]
    """
    if version < 'v4.3':
        main_tag = 'references-cited'
        ref_tag = 'citation'
    else:
        main_tag = 'us-references-cited'
        ref_tag = 'us-citation'

    parsed_refs = list()
    try:
        references = soup.find(main_tag).find_all(ref_tag)
    except AttributeError:  # main_tag is None.
        return parsed_refs

    for ref in references:
        doc_id = ref.find('document-id')
        if doc_id is None:
             continue
        parsed_ref = {
            'patent_number': doc_id.find('doc-number').text.strip(),
            'country': doc_id.find('country').text.strip(),
            'patentee_name': safe_text(doc_id.find('name')),
            'issue_date': safe_text(doc_id.find('date'))
        }
        new_ref = USReference(**parsed_ref)
        parsed_refs.append(new_ref)

    return parsed_refs


def safe_text(tag):
    return tag if tag is None else tag.text.strip()