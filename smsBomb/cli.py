# coding=utf-8

import argparse

from smsBomb import plugins
from smsBomb import smsBomb


def parse_command_line(sms_services):
    """
    :param sms_services: 支持短信产品列表
    :type  sms_services: list
    :return:
    """
    parser = argparse.ArgumentParser(description='短信轰炸机', epilog="See https://von.sh/smsBomb", prog='python -m smsBomb')
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
    sms_plugins = smsBomb.load_plugins(plugins)
    # 支持的短信服务商.
    supported_sms_service = [name.replace(
        plugin_prefix, '') for name in sms_plugins.keys()]

    args = parse_command_line(supported_sms_service)

    logger = smsBomb.setup_logger(None,
                                  use_colors=True,
                                  verbose_count=args.verbose_count)
    config = smsBomb.load_config(args.config, args.product)
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

    sms_bomb = smsBomb.SmsBomb(sms_plugins, config, args.target,
                               process_num=args.process_num,
                               msg=args.message,
                               limit=args.times,
                               prefix=plugin_prefix,
                               proxies=proxies
                               )
    sms_bomb.start()


if __name__ == '__main__':
    main()
