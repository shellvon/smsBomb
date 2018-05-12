# coding=utf-8

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
            'msg': self.get_msg_content(kwargs, 'msg')
        })
        resp = self._req.post(self.api, json=kwargs).json()
        self.logger.info(resp)
        return resp['code'] == '0'
