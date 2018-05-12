# coding=utf-8

import hashlib

from smsBomb import SmsPlugin


class NeteasePlugin(SmsPlugin):
    """网易云短信

    文档: http://dev.netease.im/docs/product/短信/短信接口指南
    """
    API_URLS = {
        'send': 'https://api.netease.im/sms/sendcode.action',
        'verify': 'https://api.netease.im/sms/verifycode.action',
        'send_template': 'https://api.netease.im/sms/sendtemplate.action',
        'query_status': 'https://api.netease.im/sms/querystatus.action',
    }

    def checksum(self, nonce, curtime):
        plain_text = '{0}{1}{2}'.format(
            self.auth['app_secret'], nonce, curtime).encode('utf-8')
        return hashlib.sha1(plain_text).hexdigest()

    @property
    def headers(self):
        ts = self.curtime
        nonce = self.nonce
        return {
            'AppKey': self.auth['app_key'],
            'CurTime': ts,
            'Nonce': nonce,
            "CheckSum": self.checksum(nonce, ts),
            'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8'
        }

    def send(self, mobile, **kwargs):
        kwargs.update({'mobile': mobile})
        headers = self.headers
        self.logger.debug('请求头: %s', headers)
        resp = self._req.post(
            self.api, headers=headers, data=kwargs).json()
        self.logger.debug(resp)
        return resp['code'] == 200
