#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, too-many-arguments, broad-except, anomalous-backslash-in-string
# pylint: disable=missing-docstring, line-too-long, too-few-public-methods
"""
# @Author  : wxt
# @Software: PyCharm
"""

import redis
import datetime
from app import TBG
from ..utils.logger import Logger
from ..utils.util import Time
from ..controller.pokeman import Pokeman


class FusingControl(object):
    """
    熔断模块
    """

    @staticmethod
    def is_fusing(fusing_type,fusing_var):
        """
        判断是否熔断
        :param fusing_type:  熔断数据类型 可选 ota  bp_key
        :param fusing_var:  熔断项，目前仅支持  ota_name  bp_key
        :return: True  False
        """
        key = '%s_%s'%(fusing_type,fusing_var)
        fusing_result = TBG.redis_conn.redis_pool.hget('fusing_repo',key)
        if fusing_result:
            source, curr_time_str, ttl = fusing_result.split('|')
            # print source,curr_time_str,ttl
            # print datetime.datetime.now()
            if (datetime.datetime.strptime(curr_time_str, '%Y-%m-%d %H:%M:%S') + datetime.timedelta(seconds=int(ttl))) < datetime.datetime.now():
                FusingControl.del_fusing(key)
                return False
            else:
                return True
        if fusing_result:
            return True
        else:
            return False

    @staticmethod
    def add_fusing(fusing_type,fusing_var,source='',ttl=86400):
        """
        添加熔断黑名单
        :param fusing_type:  熔断数据类型 可选 ota  routing_key
        :param fusing_var:  熔断项，目前仅支持  ota_name  routingkey
        :param source 数据来源（可选）:  表明该数据从哪里添加
        :param ttl 超时时间:  单位秒，默认一天
        :return:
        """
        TBG.redis_conn.redis_pool.hset('fusing_repo', '%s_%s' % (fusing_type, fusing_var),"%s|%s|%s" % (source,Time.time_str(),ttl))
        Logger().swarn('fusing added %s %s %s %s' % (fusing_type,fusing_var,source,ttl))
        # TBG.redis_conn.redis_pool.hset('fusing_repo', '%s_%s' % (fusing_type, fusing_var), "%s|%s" % (source, "2019-02-19 14:54:54"))
        if TBG.global_config['RUN_MODE'] == 'TEST':
            content = '熔断类型:{fusing_type}\n熔断数据:{fusing_var}\n熔断来源:{source}\nTTL:{ttl}\n'.format(fusing_type=fusing_type,fusing_var=fusing_var,source=source,ttl=ttl)
            subject = '熔断事件触发'
            Pokeman.send_wechat(content=content,subject=subject,agentid=1000010)

    @staticmethod
    def fusing_repo_list():
        """
        返回库列表

        :return: True  False
        """
        fusing_result = TBG.redis_conn.redis_pool.hgetall('fusing_repo')
        Logger().sdebug('fusing_repo_list %s'% fusing_result)
        # 遍历 删除过期项目
        ret = {}
        for fusing_record,v in fusing_result.items():
            source,curr_time_str,ttl = v.split('|')
            if (datetime.datetime.strptime(curr_time_str, '%Y-%m-%d %H:%M:%S') + datetime.timedelta(seconds=int(ttl))) < datetime.datetime.now():
                FusingControl.del_fusing(fusing_record)
            else:
                ret[fusing_record] = v
        return ret

    @staticmethod
    def del_fusing(fusing_record):
        """
        删除熔断黑名单
        :param fusing_type:  熔断数据类型 可选 ota  routing_key
        :param fusing_var:  熔断项，目前仅支持  ota_name  routingkey
        :return:
        """
        TBG.redis_conn.redis_pool.hdel('fusing_repo', fusing_record)


    @staticmethod
    def del_all_fusing():
        """
        删除熔断黑名单
        :param fusing_type:  熔断数据类型 可选 ota  routing_key
        :param fusing_var:  熔断项，目前仅支持  ota_name  routingkey
        :return:
        """
        TBG.redis_conn.redis_pool.delete('fusing_repo')


if __name__ == '__main__':
    pass