#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, too-many-arguments, broad-except, anomalous-backslash-in-string
# pylint: disable=missing-docstring, line-too-long, too-few-public-methods
"""
# @Author  : wxt
# @Software: PyCharm
"""

import gevent
import time
from ..utils.logger import Logger
from ..controller.dynamic_fare import DynamicFareRuleEngine
from threading import Thread

def run_in_thread(func,*args,**kwargs):

    thread = Thread(target=func,args=args,kwargs=kwargs)
    thread.daemon = True
    thread.start()
    return thread


class CachedMeta(object):
    """
    缓存预加载
    """
    sleep_interval = 60

    active_auths = []
    active_tokens = []
    active_users = []

    @classmethod
    def run_async(cls):
        daemon = run_in_thread(cls._daemon_run)

    @classmethod
    def run_sync(cls):
        cls.try_run_refresh(cls.refresh_dynamic_fare_strategy)

    @classmethod
    def _daemon_run(cls):
        time.sleep(2)
        while True:
            cls.try_run_refresh(cls.refresh_dynamic_fare_strategy)

            gevent.sleep(cls.sleep_interval)

    @classmethod
    def try_run_refresh(cls, func):
        for count in range(1, 10):
            try:
                func()
                break
            except Exception as e:
                Logger().serror(e)

    @classmethod
    def refresh_dynamic_fare_strategy(cls):
        """
        刷新动态运价策略到内存
        格式
        {'dfs_hash':'sdp'}
        dfs_hash:
        :return:
        """
        DynamicFareRuleEngine.load()

if __name__ == '__main__':
    pass