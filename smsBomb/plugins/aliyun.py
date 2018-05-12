# coding=utf-8

import base64
import datetime
import hmac
import json
import urllib.parse

from smsBomb import SmsPlugin


def quote(s, safe='~'):
    """URL编码"""
    return urllib.parse.quote(s, safe=safe)


def stringify(**kwargs):
    """参见阿里云签名需要"""
    pairs = []
    for k, v in sorted(kwargs.items()):
        pairs.append('{}={}'.format(k, v))
    return '&'.join(pairs)


def canonicalize(**kwargs):
    """阿里云签名算法需要"""
    pairs = []
    for k, v in sorted(kwargs.items()):
        pair = '{}={}'.format(quote(k), quote(v))
        pairs.append(pair)
    return quote('&'.join(pairs))


class AliyunPlugin(SmsPlugin):
    """阿里大鱼短信"""

    API_URLS = {
        'send': 'https://dysmsapi.aliyuncs.com'
    }

    @property
    def curtime(self):
        return datetime.datetime.utcnow().isoformat("T")

    def checksum(self, plain_text, secret_key=None):
        plain_text = plain_text.encode('utf-8')
        secret_key = secret_key if secret_key else self.auth['app_secret']
        key = (secret_key + '&').encode('utf-8')
        digest = hmac.new(key, plain_text, 'sha1').digest()
        return quote(base64.b64encode(digest))

    def _create_params(self, mobile,
                       sign_name,
                       template_code,
                       template_params):
        """
        :param mobile: 手机号
        :param sign_name: 签名
        :param template_code: 模版编号
        :param template_params: 模版参数
        :return:
        """
        return {
            'AccessKeyId': self.auth['app_key'],
            'Action': 'SendSms',
            'Format': 'JSON',
            'PhoneNumbers': str(mobile),
            'RegionId': 'cn-hangzhou',
            'SignName': sign_name,
            'SignatureMethod': 'HMAC-SHA1',
            'SignatureNonce': self.nonce,
            'SignatureVersion': '1.0',
            'TemplateCode': template_code,
            'TemplateParam': json.dumps(template_params),
            'Timestamp': self.curtime,
            'Version': '2017-05-25',
        }

    def send(self, mobile, **kwargs):
        params = self._create_params(
            mobile,
            kwargs['sign_name'],
            kwargs['template_code'],
            kwargs.get('template_params'))
        plain_text = 'POST&%2F&' + canonicalize(**params)
        sign = self.checksum(plain_text)
        body = 'Signature={}&{}'.format(sign, stringify(**params))
        self.logger.debug('拼接完成请求体: %s', body)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        resp = self._req.post(self.api, headers=headers,
                              data=body.encode('utf-8')).json()
        self.logger.info(resp)

        return resp['Code'] == 'OK'
