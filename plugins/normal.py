# coding=utf-8

import requests
from smsBomb import SmsPlugin


class NormalPlugin(SmsPlugin):
    """其他普通短信"""

    def __init__(self, **kwargs):
        SmsPlugin.__init__(self, **kwargs)
        self.headers = kwargs.get('headers')

    def send(self, target, **kwargs):
        payloads = kwargs
        payloads.update(self.auth)
        for (k, v) in payloads.items():
            if not isinstance(v, str):
                continue
            v = v.replace('{{mobile}}', str(target))
            payloads[k] = v
            v = v.replace('{{content}}', '{0}{1}'.format(
                kwargs.get('sign_name', ''), kwargs.get('msg', '')))
            payloads[k] = v

        import urllib.parse
        print(self.api, urllib.parse.urlencode(payloads))
        resp = requests.request(self.method, self.api,
                                headers=self.headers, params=payloads)
        print(self, resp.content)
        return resp.status_code == 200
