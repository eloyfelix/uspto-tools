""" Patent ZIP-archive to sqlite.

This script parses and transfer patents from the stupid text-format
in bulk_download.py to a query-friendly sqlite datbase.
"""
import collections
import sqlite3
import re
import os
import itertools
import datetime


with open(os.path.join(os.path.dirname(__file__), 'create_db.sql')) as f:
    INIT_DB = f.read()

INSERT_PATENT = "insert or replace into patentdata values (?, ?, ?, ?, ?, ?)"

INSERT_IGNORE_PNUM = "insert or ignore into patents (PNum) values (?)"

INSERT_FULLTEXT = """ insert into fulltexts values (
    NULL,
    ?,
    (select Id from texttypes where Name=?),
    ?
)
"""

INSERT_CITATION = "insert into citations values (?, ?)"


def connect_and_init_db(path):
    """ Connect to database and initialize schema.

    Parameters
    ----------
    path : str
        Path to sqlite-database file.

    Returns
    -------
    sqlite3.Connection, sqlite3.Cursor
    """

    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute('PRAGMA foreign_keys = ON')
    cur.executescript(INIT_DB)

    return conn, cur


def load_patents(file):
    """ Read and split patent file.

    Parameters
    ----------
    file : str, file-like
        Path to, or file-handle to file containing patents in stupid
        text format.

    Returns
    -------
    list[str]
        List of patents in stupid text-format.
    """
    if isinstance(file, str):
        try:
            with open(file, encoding='utf-8') as f:
                contents = f.read()
        except OSError:
            contents = file
    else:
        contents = file.read()

    if isinstance(contents, bytes):
        contents = contents.decode('utf-8')

    if '\r\n' in contents:
        patents = contents.split('PATENT\r\n')
    else:
        patents = contents.split('PATENT\n')

    if not patents[0]:
        patents = patents[1:]
    return patents


def parse_patent(patent_str):
    """ Parse a single patent in stupid text-format in dict.

    Parameters
    ----------
    patent_str : str
        A single patent in stupid text-format.

    Returns
    -------
    dict
    """
    keys = [
        'PATENT NUMBER',
        'SERIES CODE',
        'APPLICATION NUMBER',
        'APPLICATION TYPE',
        'APPLICATION DATE',
        'TITLE',
        'ABSTRACT',
        'BRIEF SUMMARY',
        'DESCRIPTION',
        'CLAIMS',
        'REFERENCES',
        'DESIGN CLAIMS',
    ]
    current_key = None
    parsed = collections.defaultdict(list)
    for line in patent_str.splitlines():
        if any(line.startswith('{}: '.format(k)) for k in keys):
            current_key, data = line.split(': ', 1)
        else:
            data = line
        parsed[current_key].append(data)
    parsed = {key: '\n'.join(data) for key, data in parsed.items()}
    parsed['REFERENCES'] = parsed.get('REFERENCES', '').strip().split(';')

    return parsed


def insert_patents(patents, cursor):
    """ Insert parsed patents into database.

    Parameters
    ----------
    patent : list[dict[str, str]]
        Parsed patent dict.
    cursor : sqlite3.Cursor
        Database cursor.
    """
    values = list()
    fulltexts = list()
    references = list()
    for patent in patents:
        field_type, p_num, app_num, series_code, date = _get_patent_info(patent)

        values.append((
            p_num,
            field_type,
            int(app_num),
            series_code if series_code != 'None' else None,
            date,
            patent['TITLE']
        ))
        fulltexts.extend(_get_fulltexts(patent, p_num))
        references.extend(_get_references(patent, p_num))

    cursor.executemany(INSERT_IGNORE_PNUM, [(v[0], ) for v in values])
    cursor.executemany(INSERT_PATENT, values)
    cursor.executemany(INSERT_FULLTEXT, fulltexts)

    referred = set((ref, ) for p, ref in references)
    cursor.executemany(INSERT_IGNORE_PNUM, referred)
    cursor.executemany(INSERT_CITATION, references)


def _get_references(patent, patent_number):
    references = list()
    for raw_ref in patent['REFERENCES']:
        try:
            _, ref = _parse_patent_number(raw_ref)
        except ValueError:
            continue
        references.append(ref)

    return list(zip(itertools.repeat(patent_number), references))


def _get_fulltexts(patent, patent_number):
    fulltexts = list()
    for key in ('DESCRIPTION', 'ABSTRACT', 'BRIEF SUMMARY', 'CLAIMS'):
        if patent.get(key, 'None') != 'None':
            fulltexts.append((patent_number, key, patent[key]))

    if patent.get('DESIGN CLAIMS', 'None') != 'None':
        fulltexts.append((patent_number, 'CLAIMS', patent['DESIGN CLAIMS']))

    return fulltexts


def _get_patent_info(patent):
    raw_p_num = patent['PATENT NUMBER']

    field_type, p_num = _parse_patent_number(raw_p_num)

    app_num = re.sub(r'[^0-9]', '', patent['APPLICATION NUMBER'])
    series_code = patent['SERIES CODE']
    date = patent['APPLICATION DATE']
    if date != 'None':
        date = _safe_date(date).toordinal()
    else:
        date = None

    return field_type, p_num, app_num, series_code, date


def _safe_date(date_str):
    try:
        date = datetime.datetime.strptime(date_str, '%Y%m%d')
    except ValueError as e:
        if str(e) == 'day is out of range for month':
            # Some dates has been wrongly entered into the original database
            # meaning that some dates does not exist. If non-existing day,
            # decrement day until exists.
            new_date = '{}{:02d}'.format(date_str[:-2], int(date_str[-2:]) - 1)
            return _safe_date(new_date)
        else:
            raise e

    return date


def _parse_patent_number(raw_p_num):
    if raw_p_num.isdigit():
        p_num = int(raw_p_num)
        field_type = None
    else:
        try:
            field_type, p_num = re.match(r'([A-z]+)(\d+)', raw_p_num).groups()
            p_num = int(p_num)
        except (TypeError, AttributeError):
            raise ValueError('bad patent-number: {}'.format(raw_p_num))
    return field_type, p_num


def _make_parser():
    import argparse
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('archive',
                        help='Zip archives containing patent text-files.')
    default_output = 'patents.db'
    parser.add_argument('-o', '--output',
                        help='Output path (default {})'.format(default_output),
                        default=default_output)
    parser.add_argument('--skip', help=('File containing names of files in '
                                        'archives to skip separated '
                                        'by new-lines.'))
    parser.add_argument('-l', '--log', default=None,
                        help='Log file (default stdout)')

    return parser


if __name__ == '__main__':
    import logging
    import zipfile

    parser = _make_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        filename=args.log,
        format='%(asctime)s:%(levelname)s: %(message)s'
    )

    conn, cur = connect_and_init_db(args.output)
    patent_count = 0

    if args.skip:
        with open(args.skip) as f:
            to_skip = set(line.strip() for line in f.readlines())
    else:
        to_skip = set()

    start = datetime.datetime.now()
    logging.info('Opens archive')
    with zipfile.ZipFile(args.archive, allowZip64=True) as z:
        for name in z.namelist():
            if name in to_skip:
                logging.info('Skips: {}'.format(name))
                continue
            logging.info('Reads: {}'.format(name))
            with z.open(name) as file:
                patents_raw = load_patents(file)

            logging.info('Parses {} patents.'.format(len(patents_raw)))
            patents = [parse_patent(p_str) for p_str in patents_raw]

            logging.info('Insert into database.')
            insert_patents(patents, cur)

            logging.info('Commits changes.')
            conn.commit()

            patent_count += len(patents)

    logging.info('Closes connection.')
    conn.close()

    end = datetime.datetime.now()
    logging.info('Total {} patents inserted (time elapsed: {}).'.format(
        patent_count, end-start))