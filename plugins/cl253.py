# coding=utf-8

import requests
from smsBomb import SmsPlugin


class Cl253Plugin(SmsPlugin):
    """蓝创253

       文档地址: https://www.253.com/#/document/api_doc/zz
       """

    API_URLS = {
        'send': 'http://smssh1.253.com/msg/send/json',
        'balance': 'http://smssh1.253.com/msg/balance/json',
        'variable': 'http://smssh1.253.com/msg/variable/json'
    }

    def send(self, mobile, **kwargs):
        kwargs.update({
            'account': self.auth['account'],
            'password': self.auth['password'],
            'phone': str(mobile),
            'msg': kwargs.get('msg', '您的验证码是: 123456')
        })
        resp = requests.post(self.api, json=kwargs).json()
        print(self, resp)
        return resp['code'] == '0'
