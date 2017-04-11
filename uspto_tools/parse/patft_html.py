""" Module to parse pieces of patents given HTML."""
import re
import collections


def get_patent_abstract(soup):
    """ Get abstract from USPTO patft HTML.

    Parameters
    ----------
    soup : bs4.BeautifulSoup
        Patent HTML.

    Returns
    -------
    str, None
        Patent abstract if present else None.
    """
    try:
        abs_header = next(t for t in soup.find_all('center')
                          if t.text.lower() == 'abstract')
    except StopIteration:
        return None

    # Concatenate paragraphs.
    abstract_paragraphs = list()
    for abstract_tag in walk_consecutive_paragraphs(abs_header):
        paragraph = abstract_tag.text.strip()
        paragraph = ' '.join(line.strip() for line in paragraph.splitlines())

        abstract_paragraphs.append(paragraph)

    abstract = '\n'.join(abstract_paragraphs)
    return abstract if abstract else None


def get_patent_claims(soup):
    """ Get claims from USPTO patft HTML.

    Parameters
    ----------
    soup : bs4.BeautifulSoup
        Patent HTML.

    Returns
    -------
    list[str]
        List of claims.
    """
    try:
        claim_header = next(t for t in soup.find_all('center')
                            if t.text.lower() == 'claims')
    except StopIteration:
        return None

    claim_tag_w_junk = claim_header.find_next('hr')
    claim_text = str(claim_tag_w_junk).split('<hr>')[1]

    claims = [text.lstrip() for text in claim_text.split('<br><br>')
              if re.match(r'^\d+\. ', text.strip())]

    return claims if claims else None


def get_patent_descriptions(soup):
    """ Get description from USPTO patft HTML.

    Parameters
    ----------
    soup : bs4.BeautifulSoup
        Patent HTML.

    Returns
    -------
    dict[str, str]
        Description header - text mapping.
    """
    try:
        descr_header = next(t for t in soup.find_all('center')
                            if t.text.lower() == 'description')
    except StopIteration:
        return None

    descr_contents = descr_header.find_next('hr')
    descr_lines = str(descr_contents).split('<br><br>')[1:-1]

    descriptions_as_lines = collections.defaultdict(list)
    current_header = None
    for line in (l.strip() for l in descr_lines):
        if line.isupper():  # I.e. header row.
            current_header = line
        else:
            descriptions_as_lines[current_header].append(line)

    descriptions = {key: ' '.join(value) for key, value
                    in descriptions_as_lines.items()}
    return descriptions


def get_patent_id(soup):
    """ Get patent-ID from USPTO patent HTML.

    Parameters
    ----------
    soup : bs4.BeautifulSoup
        Patent HTML.

    Returns
    -------
    patent_id : str
        Patent-ID
    """
    title_tag = soup.findChild('head').find('title')
    _, patent_id = title_tag.text.split(': ')
    return patent_id


def walk_consecutive_paragraphs(tag):
    """ Generator function over consecutive paragraph-tags following `tag`.

    Parameters
    ----------
    tag : bs4.element.Tag
        Base-tag.

    Yields
    ------
    paragraph_tag : bs4.element.Tag
        Consecutive paragraph tags.
    """
    # Find first paragraph.
    paragraph_tag = tag.find_next()
    while paragraph_tag.name != 'p':
        paragraph_tag = paragraph_tag.find_next()

    # Iterate over consecutive paragraphs.
    while paragraph_tag.name == 'p':
        yield paragraph_tag

        paragraph_tag = paragraph_tag.find_next()