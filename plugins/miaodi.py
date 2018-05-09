# coding=utf-8

import hashlib
import time

from smsBomb import SmsPlugin


class MiaodiPlugin(SmsPlugin):
    """秒滴云

    文档: http://www.miaodiyun.com/doc/https_sms.html
    """

    API_URLS = {
        'send': 'https://api.miaodiyun.com/20150822/industrySMS/sendSMS'
    }

    @property
    def curtime(self):
        return time.strftime('%Y%m%d%H%M%S')

    def checksum(self, ts):
        plain_text = '{sid}{token}{ts}'.format(
            ts=ts, **self.auth).encode('utf-8')
        return hashlib.md5(plain_text).hexdigest()

    def send(self, mobile, **kwargs):
        ts = self.curtime
        kwargs.update({
            'to': mobile,
            'timestamp': ts,
            'sig': self.checksum(ts)
        })
        resp = self._req.post(self.api, data=kwargs).json()
        self.logger.info(resp)
        return resp['respCode'] == '00000'
