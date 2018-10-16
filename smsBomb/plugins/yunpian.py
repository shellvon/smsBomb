# coding=utf-8

import random

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
        resp = self._req.post(self.API_URLS['tpl_get'], {
            'apikey': self.auth['api_key']}).json()
        if resp and isinstance(resp, (list,)):
            return random.choice(resp)

    def send(self, mobile, **kwargs):
        tpl = self.get_one_tpl()
        if not tpl:
            self.logger.error('无法获取到模版信息(云片网)')
            return False
        self.logger.debug('随机获取模版消息: %s', tpl)
        payloads = {
            'mobile': mobile,
            'apikey': self.auth['api_key'],
            'text': tpl.get('tpl_content')
        }
        resp = self._req.post(self.api, data=payloads).json()
        self.logger.info(resp)
        return resp['code'] == 0
