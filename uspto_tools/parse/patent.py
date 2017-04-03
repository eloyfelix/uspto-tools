""" This module containt simple wrapper classes for a US-patent,
inventor, patent-reference and classification.

Copyright (c) 2017 clicumu
Licensed under MIT license as described in LICENSE.txt
"""


class USPatent:

    """ A single patent instance. """

    def __init__(self, **kwargs):
        self.patent_number = None
        self.date = None
        self.country = None
        self.series_code = None
        self.kind = None
        self.application_number = None
        self.application_type = None
        self.application_country = None
        self.application_date = None
        self.art_unit = None
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

    @property
    def document_id(self):
        document_id = ' '.join(filter(None, [self.country,
                                             self.patent_number,
                                             self.kind]))
        if self.date is not None:
            document_id += '-{}'.format(self.date)

        return document_id

    def __repr__(self):
        return '<{}: {}>'.format(self.__class__.__name__, self.document_id)


class Inventor:

    """ Patent inventor. """

    def __init__(self, **kwargs):
        self.name = None
        self.country = None
        self.city = None
        self.zip_code = None
        self.state = None

        _set_attributes_from_kwargs(self, kwargs)

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
        _set_attributes_from_kwargs(self, kwargs)

    def __repr__(self):
        return '{}(us_classification="{}")'.format(self.__class__.__name__,
                                                   self.us_classification)


class USReference:

    def __init__(self, **kwargs):
        self.patent_number = None
        self.issue_date = None
        self.patentee_name = None
        self.country = None

        _set_attributes_from_kwargs(self, kwargs)

    def __repr__(self):
        base_str = '{}(patent_number="{}", issue_data="{}", patentee_name="{}")'
        return base_str.format(self.__class__.__name__, self.patent_number,
                               self.issue_date, self.patentee_name)





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