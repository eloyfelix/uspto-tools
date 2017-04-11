""" This module contains chunker and parser for USPTO SGML/XML v2.5
full-text used for patents granted 2002-2004.
"""
from bs4 import BeautifulSoup

from .patent import USPatent, Inventor, PatentClassification, USReference


def chunk_sgml_file(sgml, chunk_on='PATDOC'):
    """ Iterate over patents in SGML-file.

    Parameters
    ----------
    sgml : str, file_like
        Path or file-handle to SGML-file or already read SGML-contents.
    chunk_on : str
        String to chunk file on. Defaults to "PATDOC".

    Yields
    ------
    chunk : str
        A single patent.
    """
    if isinstance(sgml, str):
        try:
            with open(sgml) as f:
                contents = f.read()
        except IOError:  # Assume APS-contents.
            contents = sgml
    elif hasattr(sgml, 'read'):  # File-like.
        contents = sgml.read()
    else:
        raise ValueError('invalid sgml')

    start_tag = '<{}'.format(chunk_on)
    end_tag = '</{}'.format(chunk_on)

    # Skip header line
    lines = contents.splitlines()
    start_i = 0
    for i, line in enumerate(lines):
        if line.startswith(start_tag):
            start_i = i
        elif line.startswith(end_tag):
            yield '\n'.join(lines[start_i:i + 1])


def parse_sgml_chunk(chunk):
    """ Parse SGML chunk into patent.

    Parameters
    ----------
    chunk : str
        Single USPTO patent in SGML format.

    Returns
    -------
    USPatent
        Parsed patent.
    """
    soup = BeautifulSoup(chunk, 'lxml')
    parsed = {
        'claims': [c.text.strip() for c in soup.find('cl').find_all('clm')],
        'inventors': [sgml_to_inventor(tag) for tag in soup.find_all('b721')],
        'patent_classification': [sgml_to_classification(tag) for
                                  tag in soup.find_all('b582')],
        'us_references': [sgml_to_reference(tag) for tag in soup.find_all('b561')],
        'application_number': soup.find('b210').text.replace(' ', ''),
        'application_date': soup.find('b220').text.replace(' ', ''),
        'patent_number': soup.find('b110').text,

    }

    check_if_none = {
        'brief_summary': soup.find('brfsum'),
        'primary_examiner': soup.find('b746'),
        'title': soup.find('b540'),
        'kind': soup.find('b130'),
        'description': soup.find('detdesc'),
        'abstract': soup.find('sdoab')
    }

    checked_for_none = {name: safe_text(val)
                        for name, val in check_if_none.items()}
    parsed.update(checked_for_none)
    return USPatent(**parsed)


def sgml_to_inventor(tag):
    """ Parse inventor tag.

    Parameters
    ----------
    tag : bs4.element.Tag
        Inventor tag.

    Returns
    -------
    Inventor
    """
    nam_tag = tag.find('nam')
    parsed = {
        'name': '{} {}'.format(safe_text(nam_tag.find('fnm')),
                              safe_text(nam_tag.find('snm'))),
        'city': safe_text(tag.find('city')),
        'country': safe_text(tag.find('ctry'))
    }
    return Inventor(**parsed)


def sgml_to_classification(tag):
    """ Parse classification tag.

    Parameters
    ----------
    tag : bs4.element.Tag
        Classification tag.

    Returns
    -------
    PatentClassification
    """
    return PatentClassification(us_classification=tag.text.strip())


def sgml_to_reference(tag):
    """ Parse reference tag.

    Parameters
    ----------
    tag : bs4.element.Tag
        Reference tag.

    Returns
    -------
    USReference
    """
    p_num = tag.find('dnum').find('pdat').text
    p_date = tag.find('date').find('pdat').text
    name = '; '.join(t.text.strip() for t in tag.find_all('party-us'))
    return USReference(patent_number=p_num, issue_date=p_date,
                       patentee_name=name)



def safe_text(tag):
    return tag if tag is None else tag.text.strip()