# coding=utf-8

from smsBomb import SmsPlugin


class JuhePlugin(SmsPlugin):
    """聚合服务

    文档: https://www.juhe.cn/docs/api/id/54
    """
    API_URLS = {
        'send': 'http://v.juhe.cn/sms/send'
    }
