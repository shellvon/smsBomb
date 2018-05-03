# coding=utf-8

import hashlib
import json
import random

from smsBomb import SmsPlugin


class TencentPlugin(SmsPlugin):
    """腾讯短信

    文档: https://cloud.tencent.com/document/product/382/5976
    """

    API_URLS = {
        'send': 'https://yun.tim.qq.com/v5/tlssmssvr/sendsms',
        'tpl_get': 'https://yun.tim.qq.com/v5/tlssmssvr/get_template'
    }

    def __init__(self, **kwargs):
        SmsPlugin.__init__(self, **kwargs)
        self.tpl_content = kwargs.get('tpl_content', '')
        if not self.tpl_content:
            self.tpl_content = self.get_one_tpl()
            self.logger.debug('没有默认的模版消息,随机获取:%s', self.tpl_content)
        self.tpl_param = kwargs.get('tpl_params', [])

    @staticmethod
    def checksum(plain_text):
        return hashlib.sha256(plain_text).hexdigest()

    def get_one_tpl(self, tpl_id=None, tpl_page=None):
        nonce = self.nonce
        ts = self.curtime
        url = '{0}?sdkappid={1}&random={2}'.format(
            self.API_URLS['tpl_get'], self.auth['app_id'], nonce)
        plain_text = 'appkey={appkey}&random={nonce}&time={ts}'.format(
            appkey=self.auth['app_secret'],
            nonce=nonce,
            ts=ts).encode('utf-8')
        payloads = {
            'sig': self.checksum(plain_text),
            'time': ts
        }
        if tpl_id:
            payloads['tpl_id'] = tpl_id
        elif tpl_page:
            payloads['tpl_page'] = tpl_page
        if not tpl_id and not tpl_page:
            payloads['tpl_page'] = {
                'max': 10,
                'offset': 0
            }

        resp = self._req.post(url, json.dumps(payloads)).json()
        return random.choice(resp['data'])['text']

    def send(self, mobile, **kwargs):
        nonce = self.nonce
        ts = self.curtime

        data = {
            'appkey': self.auth['app_secret'],
            'nonce': nonce,
            'ts': ts,
            'mobile': mobile
        }
        # 字段根据公式 sha256（appkey=$appkey&random=$random&time=$time&mobile=$mobile）生成
        plain_text = 'appkey={appkey}&random={nonce}&time={ts}&mobile={mobile}'.format(
            **data).encode('utf-8')
        msg = self.tpl_content.format(None, *self.tpl_param)
        payloads = {
            "ext": "",
            "extend": "",
            "msg": msg,
            "sig": self.checksum(plain_text),
            "tel": {
                "mobile": str(mobile),
                "nationcode": "86"
            },
            "time": int(ts),  # 请求发起时间，unix 时间戳（单位：秒），如果和系统时间相差超过 10 分钟则会返回失败
            "type": 0  # 短信类型，Enum{0: 普通短信, 1: 营销短信}（
        }

        url = '{0}?sdkappid={1}&random={2}'.format(
            self.api, self.auth['app_id'], nonce)
        resp = self._req.post(url, data=json.dumps(payloads)).json()
        self.logger.info(resp)
        return resp['result'] == 0
