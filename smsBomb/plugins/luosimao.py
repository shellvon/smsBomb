# coding=utf-8

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
        kwargs['message'] = self.get_msg_content(kwargs, 'message')
        resp = self._req.post(self.api, auth=basic_auth, data=kwargs).json()
        self.logger.info(resp)
        return resp['error'] == 0
