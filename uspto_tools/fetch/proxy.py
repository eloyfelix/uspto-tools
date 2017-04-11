""" This module contain wrappers of `requests.Session` which automatically
fetches proxies.
"""
import logging
import requests
from bs4 import BeautifulSoup

from requests.exceptions import ProxyError


class ProxySession(requests.Session):

    def __init__(self):
        super(ProxySession, self).__init__()
        self.max_tries = 3
        self.proxies = self.fetch_proxies()

    def get(self, url, **kwargs):
        for _ in range(self.max_tries):
            try:
                return super(ProxySession, self).get(url, **kwargs)
            except ProxyError:
                logging.info('ProxyError: Retries with new proxy.')
                self.proxies = self.fetch_proxies()

    def fetch_proxies(self):
        raise NotImplementedError('Missing method to fetch proxy.')


class USProxySession(ProxySession):

    """ Extend `requests.Session` to auto-update proxies with IP:s
    fetched from www.us-proxy.org.
    """

    def __init__(self, level='elite proxy'):
        self.level = level
        super(USProxySession, self).__init__()

    def fetch_proxies(self):
        r = requests.get('https://www.us-proxy.org/')
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
        table = next(t for t in soup.find_all('table')
                     if t.has_attr('id') and t['id'] == 'proxylisttable')
        header = table.find('thead').text.strip().split('\n')
        header_map = {h: i for i, h in enumerate(header)}

        rows = table.find('tbody').find_all('tr')
        rows_at_level = (row for row in rows if
                         list(row)[header_map['Anonymity']].text == self.level)
        first_at_level = next(rows_at_level)
        ip = list(first_at_level)[header_map['IP Address']].text
        port = list(first_at_level)[header_map['Port']].text

        proxies = {
            'http': 'http://{}:{}'.format(ip, port),
            'https': 'https://{}:{}'.format(ip, port)
        }
        return proxies
