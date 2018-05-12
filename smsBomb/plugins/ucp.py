# coding=utf-8

from smsBomb import SmsPlugin


class UcpPlugin(SmsPlugin):
    """云之讯通讯

    官网: http://www.ucpaas.com/
    文档地址: http://docs.ucpaas.com/doku.php?id=%E7%9F%AD%E4%BF%A1:about_sms
    """

    API_URLS = {
        'send': 'https://open.ucpaas.com/ol/sms/sendsms',
        'send_batch': 'https://open.ucpaas.com/ol/sms/sendsms_batch'
    }

    def __init__(self, **kwargs):
        SmsPlugin.__init__(self, **kwargs)
        self.sid = self.auth['sid']
        self.app_id = self.auth['app_id']
        self.token = self.auth['token']

    def send(self, mobile, **kwargs):
        kwargs.update({'mobile': mobile})
        kwargs.update({
            'sid': self.sid,  # AcoountSid.
            'token': self.token,
            'appid': self.app_id,
            'mobile': str(mobile)
        })
        resp = self._req.post(self.api, json=kwargs).json()
        self.logger.info(resp)
        return resp['code'] == '000000'
