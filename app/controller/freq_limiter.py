#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, too-many-arguments, broad-except, anomalous-backslash-in-string
# pylint: disable=missing-docstring, line-too-long, too-few-public-methods
"""
# @Author  : wxt
# @Software: PyCharm
"""

import redis
from ..utils.exception import *
from ..utils.logger import Logger
from ..utils.util import Time

from app import TBG

class OTAFrequencyVerification(object):

    # Verification based of Leaky-Bucket
    # Src: https://github.com/titan-web/rate-limit/blob/master/leaky_bucket/__init__.py

    def __call__(self, redis_pool=None, ota_name=None, freq_info=None,api_name=None):
        self.ota_name = ota_name,
        self.api_name = api_name
        if not freq_info:
            return True
        self.freq_limits = self.freq_limits_calc(freq_info)
        self.redis_pool = TBG.redis_conn.redis_pool

        if not self.verify_frequency():
            return False
        else:
            return True

    def freq_limits_calc(self,freq_info):  # enabled frequency limits
        # {60: -1, 300: -1, 3600: -1, 21600: -1, 86400: -1}
        return {k: limit for k, limit in dict(zip((
            60, 5 * 60, 60 * 60, 360 * 60, 1440 * 60), [int(v) for v in str(freq_info).split(',')]
        )).items() if limit > 0}

    def verify_frequency(self):
        if not self.freq_limits:
            return True  # no frequency limit
        verify_results = []
        for time_interval, limit in self.freq_limits.items():
            try:
                verify_results.append(self.get_token(time_interval, limit))
            except redis.exceptions:
                pass
        if len(verify_results):
            return all(verify_results)
        else:
            return True  # network problem

    def get_token(self, time_interval, capacity):
        refill_rate = float(capacity) / float(time_interval * 1000)  # r/ms
        key = "{}_{}_{}".format(self.ota_name,self.api_name, time_interval)
        tk = self.redis_pool.hget(key, "tk_counts")

        # Logger().sdebug("key:{}, refill_rate:{}, tk:{}".format(key, refill_rate, tk))

        if tk is None:
            self._create_bucket(key, capacity=capacity)

        tk = self.consume_and_refill(key, rate=refill_rate, capacity=capacity)
        if tk < 0:
            return False
        return True

    def _create_bucket(self, key, capacity=None):
        # create the bucket if it is not exist yet.
        self.redis_pool.pipeline().hsetnx(key, "tk_counts", capacity).\
            hset(key, "last_fill_time", Time.timestamp_ms())\
            .execute()

    def consume_and_refill(self, key, rate=None, capacity=None):
        last_refill = float(self.redis_pool.hget(key, "last_fill_time"))
        ms_delta = int((Time.timestamp_ms() - last_refill))

        if ms_delta <= 0:
            return -1  # Time is not synchronized among the cluster

        # consume a token
        current_tk = self.redis_pool.hincrbyfloat(key, "tk_counts", amount=-1)
        if current_tk <= 0:
            refill_tks = min(rate * ms_delta + 1, capacity)
            # Logger().sdebug("key:{},current_tk_counts:{}. refill_counts:{}".format(
            #     key, current_tk, refill_tks))
            self.redis_pool.pipeline()\
                .hset(key, "last_fill_time", Time.timestamp_ms()) \
                .hincrbyfloat(key, "tk_counts", amount=refill_tks) \
                .execute()  # put the token back
        else:
            # Logger().sdebug("key:{}, current_tk_counts:{}".format(key, current_tk))

            pass

        return current_tk


class ProviderSearchFreqLimiter(object):
    """
    供应商搜索模块限流器
    """

    @staticmethod
    def acquire_lock(provider_channel,proxy_pool,blocking=True,timeout=30):
        """
        将间隔锁写入redis
        供应商+代理池
        :return:
        """
        lock_key = 'psfl_lock_%s_%s' % (proxy_pool,provider_channel)
        interval_time = ProviderSearchFreqLimiter.repo_list_with_cache().get(provider_channel,None)
        if not interval_time:
            from ..automatic_repo.base import ProviderAutoRepo
            provider_app = ProviderAutoRepo.select(provider_channel)
            ProviderSearchFreqLimiter.add(provider_channel,provider_app.search_interval_time)
        if interval_time > 10: # 限制间隔时间最小不能小于0.01
            sleep_time = 2
        elif interval_time > 1:
            sleep_time = 0.5
        elif interval_time > 0.1:
            sleep_time = 0.05
        elif interval_time > 0.01:
            sleep_time = 0.01
        else:
            sleep_time = 0.01
            interval_time = 0.01

        my_lock = TBG.redis_conn.redis_pool.lock(lock_key,timeout=interval_time,sleep=sleep_time)
        have_lock = my_lock.acquire(blocking=blocking,blocking_timeout=timeout)
        if have_lock:
            # Logger().sdebug('have_lock %s' % lock_key)
            return True
        else:
            # Logger().sdebug('no lock!!!!!!!!!!!!!!!!')
            raise HighFreqLockException(lock_key)

    @staticmethod
    def repo_list():
        """
        返回供应商限流列表
        """
        psfl_result = TBG.redis_conn.redis_pool.hgetall('provider_search_freq_limiter_repo')
        Logger().sdebug('psfl_result %s'% psfl_result)
        # 遍历 删除过期项目
        ret = {}
        for provider_channel,v in psfl_result.items():
            ret[provider_channel] = float(v)
        return ret


    @staticmethod
    @TBG.fcache.cached(TBG.global_config['FCACHE_TIMEOUT'], key_prefix='repo_list_with_cache')
    def repo_list_with_cache():
        """
        返回供应商限流列表（带缓存）
        """
        return ProviderSearchFreqLimiter.repo_list()

    @staticmethod
    def add(provider_channel,interval_time):
        """
        添加或更新供应商限流配置
        interval_time  单位秒
        """
        psfl_result = TBG.redis_conn.redis_pool.hget('provider_search_freq_limiter_repo', provider_channel)
        if psfl_result:
            ProviderSearchFreqLimiter.delete(provider_channel)
            TBG.redis_conn.redis_pool.hset('provider_search_freq_limiter_repo', provider_channel, interval_time)
        else:
            TBG.redis_conn.redis_pool.hset('provider_search_freq_limiter_repo', provider_channel, interval_time)
        return True

    @staticmethod
    def delete(provider_channel):
        """
        删除条目
        :return:
        """
        TBG.redis_conn.redis_pool.hdel('provider_search_freq_limiter_repo', provider_channel)


if __name__ == '__main__':
    pass