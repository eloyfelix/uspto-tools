import re


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
        tag_data = [tag.data for tag in paragraph_tags]
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


def parse_aps_into_namespaces(text):
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
    lines = text.split('\n')
    name_spaces = list()

    current_namespace = None
    previous_tag = None
    for line in lines:
        if len(line) == 4:
            current_namespace = NameSpace(line)
            name_spaces.append(current_namespace)

        else:
            tag = line[:3]
            data = line[5:]

            if not tag.strip():
                previous_tag.data += data
            else:
                new_tag = Tag(tag, data)
                current_namespace.add_tag(new_tag)
                previous_tag = new_tag

    return name_spaces


def chunk_aps_file(aps, chunk_on='PATN'):
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
                all_contents = f.read()
        except IOError:  # Assume APS-contents.
            all_contents = aps
    elif hasattr(aps, 'read'):  # File-like.
        all_contents = aps.read()
    else:
        raise ValueError('invalid aps')

    # Skip header line
    contents = all_contents.split('\n', 1)[1]
    last_pos = contents.index(chunk_on)

    while True:
        try:
            loc = contents.index(chunk_on, last_pos + 1)
        except ValueError:
            yield contents[last_pos:]
            break
        else:
            yield contents[last_pos: loc]
            last_pos = loc