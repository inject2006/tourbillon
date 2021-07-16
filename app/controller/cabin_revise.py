#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, too-many-arguments, broad-except, anomalous-backslash-in-string
# pylint: disable=missing-docstring, line-too-long, too-few-public-methods
"""
# @Author  : wxt
# @Software: PyCharm
"""

from app import TBG
import redis
from ..utils.logger import Logger
from ..utils.util import Time


class CabinReviseControl(object):
    """
    舱位修正库模块
    """
    @staticmethod
    def get(un_key):
        """
        查询是否有仓位差，如果没有或者过期返回0，有的话返回value，
        过期会对数据进行删除
        """
        cabin_result = TBG.redis_conn.redis_pool.hget('cabin_revise_repo',un_key)
        return cabin_result

    @staticmethod
    def add(un_key,cabin_diff_value):
        """
        添加或更新舱位修正条目，过期时间固定为一天
        :param un_key:
        :param cabin_diff_value: 舱位差值
        :return:
        """
        cabin_result = TBG.redis_conn.redis_pool.hget('cabin_revise_repo', un_key)
        if cabin_result:
            diff_value, curr_ts = cabin_result.split('|')
            if Time.timestamp_s() - int(curr_ts) > 86400:
                CabinReviseControl.delete(un_key)
                TBG.redis_conn.redis_pool.hset('cabin_revise_repo', un_key, "%s|%s" % (cabin_diff_value, Time.timestamp_s()))
            else:
                Logger().debug('diff_value %s' % diff_value)
                diff_value = int(diff_value) + cabin_diff_value
                Logger().debug('diff_value %s'%diff_value)
                CabinReviseControl.delete(un_key)
                TBG.redis_conn.redis_pool.hset('cabin_revise_repo', un_key, "%s|%s" % (diff_value, Time.timestamp_s()))
        else:
            TBG.redis_conn.redis_pool.hset('cabin_revise_repo', un_key, "%s|%s" % (cabin_diff_value, Time.timestamp_s()))
        return True

    @staticmethod
    def repo_list():
        """
        返回列表，遇到过期的数据则会清理
        :return: 返回库字典 {"un_key":diff_value}
        """
        cabin_revise_result = TBG.redis_conn.redis_pool.hgetall('cabin_revise_repo')
        Logger().sdebug('cabin_revise_result %s'% cabin_revise_result)
        # 遍历 删除过期项目
        ret = {}
        for un_key,v in cabin_revise_result.items():
            diff_value,curr_ts = v.split('|')
            if Time.timestamp_s() - int(curr_ts) > 86400:
                CabinReviseControl.delete(un_key)
            else:
                ret[un_key] = int(diff_value)
        return ret

    @staticmethod
    def delete(un_key):
        """
        删除过期的修正缓存条目
        :return:
        """
        TBG.redis_conn.redis_pool.hdel('cabin_revise_repo', un_key)



if __name__ == '__main__':
    pass