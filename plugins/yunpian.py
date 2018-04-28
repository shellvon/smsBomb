# coding=utf-8

import random
import requests
from smsBomb import SmsPlugin


class YunpianPlugin(SmsPlugin):
    """云片网

         文档: https://www.yunpian.com/doc/zh_CN/domestic/list.html
        """
    API_URLS = {
        'send': 'https://sms.yunpian.com/v2/sms/single_send.json',
        'tpl_get': 'https://sms.yunpian.com/v2/tpl/get.json',
        'tpl_create': 'https://sms.yunpian.com/v2/tpl/add.json',
    }

    def get_one_tpl(self):
        resp = requests.post(self.API_URLS['tpl_get'], {
            'apikey': self.auth['api_key']}).json()
        return random.choice(resp)

    def send(self, mobile, **kwargs):
        payloads = {
            'mobile': mobile,
            'apikey': self.auth['api_key'],
            'text': self.get_one_tpl()['tpl_content']
        }
        resp = requests.post(self.api, data=payloads).json()
        print(self, resp)
        return resp['code'] == 0
