""" This module contains chunker and parser for USPTO APS
full-text used for patents granted 1976-2001.
"""

import re
import itertools
from uspto_tools.parse.patent import PatentClassification, USPatent,\
    USReference, Inventor
from uspto_tools.parse.exceptions import ParseError


class Tag:
    """ A single APS-tag. """
    def __init__(self, key, data):
        self.key = key
        self.data = data

    def is_paragraph(self):
        return bool(re.match('PA.', self.key))

    def __repr__(self):
        return 'Tag("{}", "{}")'.format(self.key, self.data)


class NameSpace:
    """ An APS namespace consisting of one or more `Tag`'s"""
    def __init__(self, name, data=None):
        self.name = name
        self.data = list() if data is None else data

    def add_tag(self, tag):
        if not isinstance(tag, Tag):
            raise ValueError('must be Tag-instance')

        self.data.append(tag)

    def as_paragraphs(self):
        """ Join paragraphs (tags with name PA*) with new-lines.

        Returns
        -------
        paragraphs : str
            New-line joined paragraphs.
        """
        paragraph_tags = [tag for tag in self.data
                          if re.match(r'PA.', tag.key)]
        tag_data = [tag.data if not tag.data.isupper() else tag.data + ' '
                    for tag in paragraph_tags]
        return '\n'.join(tag_data)

    def get_tags_by_key(self, key):
        """ Get all instances of tags of type `key`.

        Parameters
        ----------
        key : str
            Tag-name.

        Returns
        -------
        list[Tag]
        """
        return [tag for tag in self.data if tag.key == key]

    def __repr__(self):
        return '{}(name="{}", data={})'.format(self.__class__.__name__,
                                               self.name,
                                               repr(self.data))


def parse_aps_into_namespaces(lines):
    """ Parse APS-text into list of `NameSpace`-instances.

    Parameters
    ----------
    text : str
        APS full text.

    Returns
    -------
    list[NameSpace]
        Parsed
    """
    name_spaces = list()

    current_namespace = None
    previous_tag = None
    for line in lines:
        # pftaps19800101_wk01.txt line 95551
        if line.startswith("INVT"):
            line = "INVT"
        if len(line) == 4:
            current_namespace = NameSpace(line)
            name_spaces.append(current_namespace)
        else:
            tag = line[:3]
            data = line[5:]

            if not tag.strip():
                previous_tag.data += data
            else:
                if current_namespace is None:
                    raise ParseError('malformed APS')
                new_tag = Tag(tag, data)
                current_namespace.add_tag(new_tag)
                previous_tag = new_tag

    return name_spaces


def chunk_aps_file(aps):
    """ Iterate over patents in APS-file.

    Parameters
    ----------
    aps : str, file_like
        Path or file-handle to APS-file or already read APS-contents.
    chunk_on : str
        String to chunk file on. Defaults to "PATN".

    Yields
    ------
    chunk : str
        A single patent.
    """
    if isinstance(aps, str):
        try:
            with open(aps) as f:
                all_contents = f.readlines()
        except IOError:  # Assume APS-contents.
            all_contents = aps
    elif hasattr(aps, 'read'):  # File-like.
        all_contents = aps.readlines()
    else:
        raise ValueError('invalid aps')

    # trailing spaces in files like pftaps19780627_wk26.txt
    all_contents = map(str.rstrip, all_contents[1:])
    # empty lines in patents like 044883030 in pftaps19841211_wk50.txt
    all_contents = list(filter(len, all_contents))
    # "PATN" appears in some patens as text
    indices = [i for i, j in enumerate(all_contents) if j == "PATN"]
    patents = (all_contents[i:j] for i,j in zip(indices, indices[1:]+[None]))
    for patent in patents:
        yield patent


def parse_aps_chunk(chunk):
    """ Parse patent from APS text chunk.

    Parameters
    ----------
    chunk : str
        APS text chunk containing patent.

    Returns
    -------
    USPatent
    """
    namespaces = parse_aps_into_namespaces(chunk)

    mapping = {
        'PATN': {
            'WKU': 'patent_number',
            'SRC': 'series_code',
            'APN': 'application_number',
            'APT': 'application_type',
            'APD': 'application_date',
            'TTL': 'title',
            'EXP': 'primary_examiner'
        },
        'RLAP': {
            'COD': 'parent_code',
            'APN': 'parent_application_number',
            'PSC': 'parent_status_code'
        }
    }
    to_paragraphs = {
        'ABST': 'abstract',
        'BSUM': 'brief_summary',
        'DETD': 'description',
        'DCLM': 'design_claims'
    }
    to_class = {
        'CLAS': ('patent_classification', _classification_from_aps)
    }
    to_lists = {
        'INVT': ('inventors', _inventor_from_aps),
        'UREF': ('us_references', _reference_from_aps)
    }

    all_values = dict()
    for namespace in namespaces:
        name = namespace.name
        if name in mapping:
            values = _get_aps_tag_values(namespace, mapping[name])

        elif name in to_paragraphs:
            values = {to_paragraphs[name]: namespace.as_paragraphs()}

        elif name in to_class:
            attr, build_func = to_class[name]
            values = {attr: build_func(namespace)}

        elif name in to_lists:
            attr, build_func = to_lists[name]
            new_instance = build_func(namespace)
            if attr in all_values:
                all_values[attr].append(new_instance)
                values = dict()
            else:
                values = {attr: [new_instance]}
        elif name == 'CLMS':
            values = {'claims': _get_aps_claims(namespace)}
        else:
            continue

        all_values.update(values)

    return USPatent(**all_values)


def _inventor_from_aps(namespace):
    """ Build `Inventor` from `NameSpace`-instance.

    Parameters
    ----------
    namespace : uspto_parsing_tools.aps.NameSpace
        Inventor namespace.

    Returns
    -------
    Inventor
    """
    if not namespace.name == 'INVT':
        raise ValueError('not inventor namespace: {}'.format(namespace))

    mapping = {
        'NAM': 'name',
        'CNT': 'country',
        'CTY': 'city',
        'ZIP': 'zip_code',
        'STA': 'state'
    }
    values = _get_aps_tag_values(namespace, mapping)
    return Inventor(**values)


def _classification_from_aps(namespace):
    """ Build `PatentClassification` from `NameSpace`-instance.

    Parameters
    ----------
    namespace : uspto_parsing_tools.aps.NameSpace
        Classification namespace.

    Returns
    -------
    PatentClassification
    """
    if not namespace.name == 'CLAS':
        raise ValueError('not classification namespace: {}'.format(namespace))

    mapping = {
        'OCL': 'us_classification',
        'XCL': 'cross_reference',
        'UCL': 'unofficial_reference',
        'DCL': 'digest_reference',
        'EDF': 'edition_field',
        'ICL': 'international_classification',
        'FSC': 'field_of_search_class',
        'FSS': 'field_of_search_subclasses'
    }
    values = _get_aps_tag_values(namespace, mapping)
    return PatentClassification(**values)


def _reference_from_aps(namespace):
    """ Build `USReference` from `NameSpace`-instance.

     Parameters
     ----------
     namespace : uspto_parsing_tools.aps.NameSpace
         US reference namespace.

     Returns
     -------
     USReference
     """
    if not namespace.name == 'UREF':
        raise ValueError('not classification namespace: {}'.format(namespace))

    mapping = {
        'PNO': 'patent_number',
        'ISD': 'issue_date',
        'NAM': 'patentee_name'
    }
    values = _get_aps_tag_values(namespace, mapping)
    return USReference(**values)


def _get_aps_claims(namespace):
    """ Get claims in a list with paragraphs separated by newlines.

    Parameters
    ----------
    namespace : uspto_parsing_tools.aps.NameSpace
        Namespace to parse.

    Returns
    -------
    list[str]
    """
    claims = list()
    start_i = 0
    while True:
        try:
            first_p = next(itertools.dropwhile(lambda tag: not tag.is_paragraph(),
                                               namespace.data[start_i:]))
        except StopIteration:
            break

        first_p_i = namespace.data.index(first_p)

        claim_tags = itertools.takewhile(lambda tag: tag.is_paragraph(),
                                         namespace.data[first_p_i:])
        claim = '\n'.join(tag.data for tag in claim_tags)

        start_i = first_p_i + claim.count('\n') + 1
        claims.append(claim)

    return claims


def _get_aps_tag_values(namespace, mapping):
    """ Get tag values of keys in `mapping` from `namespace`.

    If `namespace` contain several instances of the same tag, for instance
    in the case of "PAR"-tags in description, join them by new-lines.

    Parameters
    ----------
    namespace : uspto_parsing_tools.aps.NameSpace
        Namespace to parse.
    mapping : dict[str, str]
        Tag-names to attribute name-mapping.

    Returns
    -------
    tag_values: dict[str, str]
        Attribute-name to value mapping.
    """
    tag_values = dict()
    for tag_key, attribute_name in mapping.items():
        tags = namespace.get_tags_by_key(tag_key)
        value = '\n'.join(tag.data for tag in tags)
        tag_values[attribute_name] = value

    return tag_values