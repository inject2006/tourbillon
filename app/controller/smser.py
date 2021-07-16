#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, too-many-arguments, broad-except, anomalous-backslash-in-string
# pylint: disable=missing-docstring, line-too-long, too-few-public-methods
"""
# @Author  : wxt
# @Software: PyCharm
"""

import gevent
import datetime
import re
from ..utils.util import Time
from pony.orm import select
from ..dao.models import SmsMessage
from ..utils.logger import Logger
from pony.orm import db_session,flush,commit
from app import TBG
import functools

def sms_lock():

    def real_warp(func):
        @functools.wraps(func)
        def _wrap(*args, **kw):
            # 防止短信冲突
            have_lock = False
            lock_id = "%s_%s" % (kw['sms_func'],kw['mobile_info']['sms_device_id']) # 设备ID只在包装函数中使用，所以弹出，防止污染真正函数入参
            Logger().sinfo('lock_id %s'%lock_id)
            my_lock = TBG.redis_conn.redis_pool.lock(lock_id, timeout=25)  # 跟self.sms_wait_time = 20  同步多几秒
            try:
                Logger().sinfo('waiting for unlock')
                have_lock = my_lock.acquire(blocking=True)
                if have_lock:
                    Logger().sinfo('already unlock ')
                    rsp_body = func(*args, **kw)
                    if rsp_body:
                        success = 1
                    else:
                        success = 0
                    TBG.tb_metrics.write(
                        "FRAMEWORK.MOBILE_SMS_RECV",
                        tags=dict(
                            sms_func=kw['sms_func'],
                            sms_device_id=kw['mobile_info']['sms_device_id'],
                            mobile=kw['mobile_info']['mobile'],
                            success=success
                        ),
                        fields=dict(
                            count=1
                        ))
                    return rsp_body
            except Exception as e:
                Logger().serror(e)
            finally:
                if have_lock:
                    try:
                        my_lock.release()
                    except Exception as e:
                        pass
        return _wrap

    return real_warp



class Smser(object):
    def __init__(self):
        self.sms_wait_time = 25  # 如果接受不到短信，需等待的时间


    def get_99bill_verify_code(self, provider_price, bank_card):
        """
        快捷验证码短信解析，
        :param provider_price: 支付价格，用于匹配短信
        :param bank_card:
        :return: list
        """
        if TBG.global_config.get('RUN_MODE','PROD') == 'TEST':
            verify_code = raw_input('input sms verify code\n')
            return [verify_code]
        start_time = Time.timestamp_s()
        start_datetime = Time.curr_date_obj()
        search_datetime = Time.curr_date_obj() - datetime.timedelta(seconds=10)
        ret_list = []
        verify_code_exp = re.compile(u'验证码：(\d*)。')
        gevent.sleep(3)
        while 1:
            with db_session:
                Logger().sdebug('get sms loop')
                sms_list = select(s for s in SmsMessage if s.create_time > search_datetime)
                commit()
                for s in sms_list:
                    if u'快钱' in s.message:
                        if str(provider_price) in s.message and bank_card[-4:] in s.message:
                            re_group = verify_code_exp.findall(s.message)
                            if re_group:
                                ret_list.append(re_group[0])
                if ret_list:
                    return ret_list
                elif Time.timestamp_s() - start_time > self.sms_wait_time:
                    return ret_list
                else:
                    gevent.sleep(2)

    def get_yeepay_verify_code(self, provider_price):
        """
        快捷验证码短信解析，
        :param provider_price: 支付价格，用于匹配短信
        :param bank_card:
        :return: list
        """
        if TBG.global_config.get('RUN_MODE','PROD') == 'TEST':
            verify_code = raw_input('input sms verify code\n')
            return [verify_code]
        start_time = Time.timestamp_s()
        search_datetime = Time.curr_date_obj() - datetime.timedelta(seconds=10)
        ret_list = []
        verify_code_exp = re.compile(u'验证码为:(\d*),')
        gevent.sleep(3)
        while 1:
            with db_session:
                Logger().sdebug('get sms loop')
                sms_list = select(s for s in SmsMessage if s.create_time > search_datetime)
                commit()
                for s in sms_list:
                    if u'易宝' in s.message:
                        if str(provider_price) in s.message:
                            re_group = verify_code_exp.findall(s.message)
                            if re_group:
                                ret_list.append(re_group[0])
                if ret_list:
                    return ret_list
                elif Time.timestamp_s() - start_time > self.sms_wait_time:
                    return ret_list
                else:
                    gevent.sleep(2)


    def get_ceair_booking_verify_code(self,mobile_info):
        """
        东航在下单时候的手机验证码收发
        【东方航空】您的动态验证码为：29+27，请输入计算结果，感谢您对东航官网的支持！
        :return: list
        """
        # TODO 临时注释
        if TBG.global_config.get('RUN_MODE','PROD') == 'TEST':
            verify_code = raw_input('input sms verify code\n')
            return [verify_code]
        else:
            # 短信逻辑
            Logger().sinfo('start get sms')
            start_time = Time.timestamp_s()
            search_datetime = Time.curr_date_obj()
            ret_list = []
            verify_code_exp = re.compile(u'您的动态验证码为：(.*?)，')
            while 1:
                with db_session:
                    Logger().sinfo('get sms loop')
                    sms_list = select(s for s in SmsMessage if s.receive_time > search_datetime and s.sms_device_id==mobile_info['sms_device_id'])
                    flush()
                    commit()

                    for s in sms_list:

                        if u'【东方航空】您的动态验证码为' in s.message:

                            re_group = verify_code_exp.findall(s.message)
                            if re_group:
                                try:
                                    a, b = re_group[0].split('+')
                                    result = int(a) + int(b)
                                    ret_list.append(result)
                                except  Exception as e:
                                    Logger().sdebug('get_ceair_booking_verify_code error %s' % re_group[0])
                    if ret_list:
                        return ret_list
                    elif Time.timestamp_s() - start_time > self.sms_wait_time:
                        return ret_list
                    else:
                        gevent.sleep(2)


    def get_ceair_h5_register_verify_code(self,mobile_info):
        """
        H5通道在注册时候的验证码
        【东方航空】尊敬的客户：你申请“东方万里行”网上入会的手机验证码为764498(30分钟有效)。
        :return: list
        """
        # TODO 临时注释
        if TBG.global_config.get('RUN_MODE','PROD') == 'TEST':
            verify_code = raw_input('input sms verify code\n')
            return [verify_code]
        else:
            # 短信逻辑
            Logger().sinfo('start get sms %s' % mobile_info)
            start_time = Time.timestamp_s()
            search_datetime = Time.curr_date_obj()
            ret_list = []
            verify_code_exp = re.compile(u'手机验证码为(.*?)\(30分钟有效\)')
            while 1:
                with db_session:
                    Logger().sinfo('get sms loop ')
                    sms_list = select(s for s in SmsMessage if s.create_time > search_datetime and s.sms_device_id==mobile_info['sms_device_id'])
                    flush()
                    commit()

                    for s in sms_list:

                        if u'你申请“东方万里行”网上入会' in s.message:

                            re_group = verify_code_exp.findall(s.message)
                            if re_group:
                                try:
                                    ret_list.append(re_group[0])
                                except  Exception as e:
                                    Logger().swarn('get_ceair_h5_register_verify_code error %s' % re_group[0])
                    if ret_list:
                        return ret_list
                    elif Time.timestamp_s() - start_time > self.sms_wait_time:
                        return ret_list
                    else:
                        gevent.sleep(2)


    def get_tongcheng_booking_verify_code(self):

        start_time = Time.timestamp_s()
        search_datetime = Time.curr_date_obj() - datetime.timedelta(seconds=10)
        result = ''
        verify_code_exp = re.compile(u'您的验证码为(.*?)，')
        while 1:
            with db_session:
                Logger().sinfo('get sms loop')
                sms_list = select(s for s in SmsMessage if s.create_time > search_datetime)
                commit()
                for s in sms_list:

                    if u'【同程艺龙】您的验证码为' in s.message:

                        re_group = verify_code_exp.findall(s.message)
                        if re_group:
                            try:
                                result = re_group[0]
                            except  Exception as e:
                                Logger().sdebug('get_ceair_booking_verify_code error %s' % re_group[0])
                if result:
                    return result
                elif Time.timestamp_s() - start_time > self.sms_wait_time:
                    return result
                else:
                    gevent.sleep(2)


if __name__ == '__main__':
    pass
