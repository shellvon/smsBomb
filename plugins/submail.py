# coding=utf-8

from smsBomb import SmsPlugin


class SubmailPlugin(SmsPlugin):
    """赛邮云通讯

        文档； https://www.mysubmail.com/chs/documents/developer/index
        """

    API_URLS = {
        'send': 'https://api.mysubmail.com/message/send'
    }

    def send(self, mobile, **kwargs):
        kwargs['to'] = mobile
        kwargs.update({
            'to': mobile,
            'content': kwargs.get('msg', kwargs.get('content')),
        })
        sign_type = kwargs.get('sign_type', 'normal')
        if sign_type == 'normal':
            pass
        elif sign_type == 'md5':
            pass
        elif sign_type == 'sha1':
            pass
        resp = super(SubmailPlugin, self).send(mobile, **kwargs).json()
        return resp['code'] == 0
