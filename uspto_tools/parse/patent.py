import itertools


class Inventor:

    """ Patent inventor. """

    def __init__(self, **kwargs):
        self.name = None
        self.country = None
        self.city = None
        self.zip_code = None
        self.state = None

        _set_attributes_from_kwargs(self, kwargs)

    @classmethod
    def from_aps_namespace(cls, namespace):
        """ Build from `NameSpace`-instance.

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
        return cls(**values)

    def __repr__(self):
        return '{}(name="{}", city="{}")'.format(self.__class__.__name__,
                                                 self.name, self.city)


class PatentClassification:

    def __init__(self, **kwargs):
        self.us_classification = None
        self.cross_reference = None
        self.unofficial_reference = None
        self.digest_reference = None
        self.edition_field = None
        self.international_classification = None
        self.field_of_search_class = None
        self.field_of_search_subclasses = None

    @classmethod
    def from_aps_namespace(cls, namespace):
        """ Build from `NameSpace`-instance.

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
        return cls(**values)

    def __repr__(self):
        return '{}(us_classification="{}")'.format(self.__class__.__name__,
                                                   self.us_classification)


class USReference:

    def __init__(self, **kwargs):
        self.patent_number = None
        self.issue_date = None
        self.patentee_name = None

        _set_attributes_from_kwargs(self, kwargs)

    @classmethod
    def from_aps_namespace(cls, namespace):
        """ Build from `NameSpace`-instance.

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
        return cls(**values)

    def __repr__(self):
        base_str = '{}(patent_number="{}", issue_data="{}", patentee_name="{}")'
        return base_str.format(self.__class__.__name__, self.patent_number,
                               self.issue_date, self.patentee_name)


class USPatent:

    """ A single patent instance. """

    def __init__(self, **kwargs):
        self.patent_number = None
        self.series_code = None
        self.application_number = None
        self.application_type = None
        self.art_unit = None
        self.application_date = None
        self.title = None
        self.primary_examiner = None

        self.parent_code = None
        self.parent_application_number = None
        self.parent_status_code = None

        self.us_references = list()
        self.inventors = list()
        self.claims = list()
        self.design_claims = None

        self.abstract = None
        self.brief_summary = None
        self.description = None

        self.patent_classification = None

        _set_attributes_from_kwargs(self, kwargs)

    @classmethod
    def from_aps_namespaces(cls, namespaces):
        """ Build from APS-name spaces.

        Parameters
        ----------
        namespaces : list[uspto_parsing_tools.aps.NameSpace]
            Namespaces constituting patent.

        Returns
        -------
        USPatent
        """

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
            'CLAS': ('patent_classification', PatentClassification)
        }
        to_lists = {
            'INVT': ('inventors', Inventor),
            'UREF': ('us_references', USReference)
        }

        all_values = dict()
        for namespace in namespaces:
            name = namespace.name
            if name in mapping:
                values = _get_aps_tag_values(namespace, mapping[name])

            elif name in to_paragraphs:
                values = {to_paragraphs[name]: namespace.as_paragraphs()}

            elif name in to_class:
                attr, class_ = to_class[name]
                values = {attr: class_.from_aps_namespace(namespace)}

            elif name in to_lists:
                attr, class_ = to_lists[name]
                new_instance = class_.from_aps_namespace(namespace)
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

        return cls(**all_values)


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


def _set_attributes_from_kwargs(instance, kwargs):
    """ Set attributes of `instance` from keywords in `kwargs.`

    Parameters
    ----------
    instance : Any
        Target-instance.
    kwargs : dict
        Keyword-arguments.

    Raises
    ------
    ValueError
        If any key in `kwargs` does not match any attribute of `instance`.
    """
    for key, value in kwargs.items():
        if hasattr(instance, key):
            setattr(instance, key, value)
        else:
            raise ValueError('Invalid key-word argument: {}'.format(key))