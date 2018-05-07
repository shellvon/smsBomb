# coding=utf-8

import threading

import kivy

import plugins
import smsBomb

kivy.require('1.10.1')

from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.popup import Popup
from kivy.properties import NumericProperty, StringProperty


class SmsBomber(GridLayout):
    attack_cnt = NumericProperty(1)
    current_attacked_cnt = NumericProperty(0)

    def __init__(self, app, sms_services):
        super(GridLayout, self).__init__()
        self.app = app
        self.sms_services = sms_services

    def refresh_progress_bar(
            self,
            success,
            failed,
            limit,
            force_finished=False,
    ):
        self.current_attacked_cnt = success
        self.attack_cnt = limit
        if force_finished:
            self.attack_cnt = self.current_attacked_cnt

    def attack(self):
        target_phone = self.ids.target.text
        if not target_phone:
            popup = ErrorPopup('target phone is missing.')
            popup.open()
            return
        try:
            times = int(self.ids.times.text)
        except:
            times = 5
        self.attack_cnt = times
        product = self.ids.product.text or None
        process_num = int(self.ids.process_num.text or 5)
        proxy = self.ids.proxy.text or None
        config = smsBomb.load_config('config/sms.json', product)
        if not config:
            popup = ErrorPopup('no configuration available')
            popup.open()
            return
        app = smsBomb.SmsBomb(
            self.sms_services,
            config,
            target_phone,
            prefix='plugins.',
            proxy=proxy,
            process_num=process_num,
            times=times,
        )

        threading.Thread(target=app.start,
                         kwargs={'cb': self.refresh_progress_bar}).start()


class ErrorPopup(Popup):
    """错误提示弹框"""

    message = StringProperty('Oops, Something goes wrong')

    def __init__(self, message):
        super(ErrorPopup, self).__init__()
        self.message = message


class SmsBombApp(App):
    """The application"""

    def __init__(self):
        super(SmsBombApp, self).__init__()

    def build(self):
        my_plugins = smsBomb.load_plugins(plugins)

        return SmsBomber(self, my_plugins)


if __name__ == '__main__':
    smsBomb.setup_logger('smsBomb.SmsBomb', verbose_count=2)
    # import logging
    #
    # multiprocessing.log_to_stderr(logging.DEBUG)
    SmsBombApp().run()
