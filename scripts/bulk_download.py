import argparse
import datetime
import functools
import io
import multiprocessing

import requests
from uspto_crawling_tools.bulk_data import get_full_text_links, get_zip_links, \
    get_patents_from_zip

from uspto_tools.fetch import proxy


def fetch_and_parse(zip_url, namespace):
    """

    Parameters
    ----------
    zip_url : str
        URL to zip-file.
    namespace : argparse.Namespace

    Returns
    -------

    """

    session = session_from_args(namespace)
    response = session.get(zip_url)
    zip_io = io.BytesIO(response.content)
    patents = get_patents_from_zip(zip_io)
    return patents


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

    session = session_from_args(args)
    links = get_full_text_links(session, args.text_format, args.start_year,
                                args.end_year)

    zip_links = list()
    for year_url in links:
        if args.text_format == 'aps':
            new_links = get_zip_links(session, year_url, 'pftaps.*')
        else:
            new_links = get_zip_links(session, year_url, 'i?pg.*')

        zip_links.extend(new_links)

    n_links = len(zip_links)
    if args.n_jobs == -1:
        results = [fetch_and_parse(url, args) for url in zip_links]
    else:
        pool = multiprocessing.Pool(args.n_jobs)
        results = pool.map(functools.partial(fetch_and_parse, namespace=args),
                           zip_links)

        for zip_url in zip_links:
            response = session.get(zip_url, stream=True)
            zip_io = io.BytesIO(response.content)
            patents = get_patents_from_zip(zip_io)