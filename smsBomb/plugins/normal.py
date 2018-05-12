# coding=utf-8

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
                kwargs.get('sign_name', ''),
                self.get_msg_content(kwargs, 'msg')))
            payloads[k] = v

        self.logger.debug('普通消息,进行参数替换:%s', payloads)
        resp = self._req.request(self.method, self.api,
                                 headers=self.headers, params=payloads)
        self.logger.info(resp.content)
        return resp.status_code == 200
