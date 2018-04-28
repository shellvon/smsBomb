# coding=utf-8

import requests
from smsBomb import SmsPlugin


class LuosimaoPlugin(SmsPlugin):
    """螺丝帽

        文档: https://luosimao.com/docs/api/20#send_msg
        """

    API_URLS = {
        'send': 'http://sms-api.luosimao.com/v1/send.json'
    }

    def send(self, mobile, **kwargs):
        basic_auth = ('api', 'key-%s' % self.auth['key'])
        kwargs['mobile'] = mobile
        kwargs['message'] = kwargs.get('message', kwargs.get('msg'))
        resp = requests.post(self.api, auth=basic_auth, data=kwargs).json()
        print(self, resp)
        return resp['error'] == 0
