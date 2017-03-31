import argparse
import datetime
import traceback
import sys
import io
import zipfile
import multiprocessing

import requests
from uspto_tools.fetch.bulk_data import get_full_text_links, get_zip_links, \
    get_patents_from_zip

from uspto_tools.fetch import proxy

STOP_TOKEN = None


class Message:

    """ Simple wrapper between-process result passing. """

    def __init__(self, name, content):
        self.name = name
        self.content = content
        self.is_failure = False


def log_error(output_path, name, exc_class, tb_str):
    path = output_path.rsplit('.', 1)[0]
    path += '_error.txt'

    line = '{};{};{}\r\n'.format(name, exc_class, tb_str)

    with open(path, 'a') as f:
        f.write(line)


def listener(output_path, queue):

    while True:
        try:
            content = queue.get()
        except (KeyboardInterrupt, SystemExit):
            raise

        if content == STOP_TOKEN:
            print('Finished')
            break

        if not isinstance(content, Message):
            print('Listener did not receive message: {}.'.format(type(content)))
            continue

        zip_url = content.name
        name = zip_url.rsplit('/', 1)[1].rsplit('.', 1)[0] + '.txt'
        if content.is_failure:
            log_error(output_path, name, *content.content)
            continue
        else:
            patents = content.content

        attrs = ('patent_number', 'series_code', 'application_number',
                 'application_type', 'application_date', 'title', 'abstract',
                 'brief_summary', 'description', 'design_claims')
        lines = list()
        for patent in patents:
            lines.append('PATENT')
            for attr in attrs:
                line = attr.upper().replace('_', ' ') + ': '
                line += '{}'.format(getattr(patent, attr))
                lines.append(line)

            claims = getattr(patent, 'claims')
            line = 'CLAIMS: '
            line += ' '.join(claims) if claims else 'None'
            lines.append(line)
            lines.append('')

        text = '\r\n'.join(lines)

        print('Writes {} to archive.'.format(name))
        with zipfile.ZipFile(output_path, 'a',
                             compression=zipfile.ZIP_DEFLATED,
                             allowZip64=True) as zf:
            zf.writestr(name, text)


def fetch_and_parse(zip_url, args, queue):
    """ Fetch zip-file, parse contents and put to results-queue.

    Parameters
    ----------
    zip_url : str
        URL to zip-file.
    args : argparse.Namespace
        Script arguments.
    queue : multiprocessing.managers.AutoProxy[Queue]
        Queue to put results to.
    """
    try:
        session = session_from_args(args)
        response = session.get(zip_url)
        zip_io = io.BytesIO(response.content)
        patents = get_patents_from_zip(zip_io)
        result = Message(zip_url, patents)
        queue.put(result)
    except Exception as e:
        _, exc_class, tb = sys.exc_info()
        message = Message(zip_url, (exc_class, traceback.format_tb(tb)))
        message.is_failure = True
        queue.put(message)


def make_parser():

    parser = argparse.ArgumentParser('USPTO Bulk download')
    parser.add_argument('--text_format', choices=('aps', 'xml', 'sgml'),
                        help='Only fetch single format')
    parser.add_argument('--start_year', type=int, default=1976,
                        help='Year to start fetching from (default 1976).')

    this_year = datetime.datetime.now().year
    end_year_help = 'Last year to fetch from, (default {}).'.format(this_year)
    parser.add_argument('--end_year', type=int, default=this_year,
                        help=end_year_help)
    parser.add_argument('--proxy', default=None,
                        help=('Proxy to use. If \'auto\', auto fetch proxies., '
                              'otherwise provide proxy IP:port.'))
    parser.add_argument('--n_jobs', default=-1, type=int,
                        help=('Number of concurrent zip-files to fetch, '
                              'if -1, run serially (default -1).'))

    parser.add_argument('output', help='Output zip archive name.')

    return parser


def session_from_args(args):
    """ Create and configure `requests.Session` from `args`.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed arguments.

    Returns
    -------
    request.Session
    """
    if args.proxy == 'auto':
        return proxy.USProxySession()
    else:
        session = requests.Session()
        if args.proxy is not None:
            session.proxies = {
                'http': 'http://{}'.format(args.proxy),
                'https': 'https://{}'.format(args.proxy)
            }
        return session


if __name__ == '__main__':
    parser = make_parser()
    args = parser.parse_args()

    out = args.output
    output_path = '{}.zip'.format(out) if not out.endswith('.zip') else out
    session = session_from_args(args)
    links = get_full_text_links(session, args.text_format, args.start_year,
                                args.end_year)

    zip_links = list()
    for year_url in links:
        if args.text_format == 'aps':
            new_links = get_zip_links(session, year_url, 'pftaps.*')
        elif args.text_format is not None:
            new_links = get_zip_links(session, year_url, 'i?pg.*')
        else:
            new_links = get_zip_links(session, year_url)

        zip_links.extend(new_links)

    pool = multiprocessing.Pool(max([args.n_jobs, 0]) + 1)
    manager = multiprocessing.Manager()
    queue = manager.Queue()

    pool.apply_async(listener, (output_path, queue))

    zip_links = zip_links
    if args.n_jobs == -1:
        results = [fetch_and_parse(url, args, queue) for url in zip_links]
    else:
        jobs = list()
        for link in zip_links:
            job = pool.apply_async(fetch_and_parse, (link, args, queue))
            jobs.append(job)

        for job in jobs:
            job.get()

    queue.put(None)
    pool.close()
    pool.join()