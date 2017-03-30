import logging
import requests
from requests.exceptions import ProxyError

import pandas as pd


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
        tables = pd.read_html(r.text)
        ip_table = next(table for table in tables
                        if 'IP Address' in table.columns)
        correct_level = ip_table[ip_table['Anonymity'] == self.level]
        with_https = correct_level[correct_level['Https'] == 'yes']
        most_fresh = with_https.iloc[0]
        ip = most_fresh['IP Address']
        port = int(most_fresh['Port'])
        proxies = {
            'http': 'http://{}:{}'.format(ip, port),
            'https': 'https://{}:{}'.format(ip, port)
        }
        return proxies
