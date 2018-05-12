# coding=utf-8

import hashlib

from smsBomb import SmsPlugin


class SmsbaoPlugin(SmsPlugin):
    """短信宝

    文档: http://api.smsbao.com/
    """

    API_URLS = {
        'send': 'http://api.smsbao.com/sms',
        'voice': 'http://api.smsbao.com/voice'
    }

    ERROR_CODES = {
        0: '成功',
        30: '密码错误',
        40: '账号不存在',
        41: '余额不足',
        42: '帐号过期',
        43: 'IP地址限制',
        50: '内容含有敏感词',
        51: '手机号码不正确',
    }

    def send(self, mobile, **kwargs):
        p = hashlib.md5(self.auth['password'].encode('utf-8')).hexdigest()
        payload = {
            'u': self.auth['username'],
            'p': p,
            'c': self.get_msg_content(kwargs, 'msg'),
            'm': mobile
        }
        code = int(self._req.get(self.api, params=payload).content)
        self.logger.info(self.ERROR_CODES.get(code, '未知错误代码:%d' % code))
        return code == 0
