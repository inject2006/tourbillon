#!/usr/bin/env python
# -*- coding: utf-8 -*-


import logging
import functools
import inspect
import logging.config
import logging.handlers

import json
from logging import getLevelName
from ..utils.util import Random, Time
# from app import TBG


def logger_config(frame_name, exception_http_log_point=False, frame_id=True):
    def real_warp(func):
        @functools.wraps(func)
        def _wrap(*args, **kw):
            lf = inspect.currentframe()
            # print 'logger_name %s'% logger_name
            last_fid = ''
            if frame_id:
                TB_FRAME_ID = Random.gen_alpha(5)

            if exception_http_log_point:
                TB_EXCEPTION_HTTP_LOG_POINT = Random.gen_alpha(8)  # 设置异常日志记录点
            for x in range(0, 20):
                lf = lf.f_back
                if (last_fid) or lf == None:
                    break

                if not last_fid and 'TB_FRAME_ID' in lf.f_locals:
                    last_fid = lf.f_locals['TB_FRAME_ID']

            if last_fid:
                TB_FRAME_ID = '%s.%s' % (last_fid, TB_FRAME_ID)

            TB_FRAME_NAME = frame_name

            try:
                rsp_body = func(*args, **kw)
            except Exception as e:
                if exception_http_log_point:
                    Logger().http_log_print(log_point=TB_EXCEPTION_HTTP_LOG_POINT)
                # if exception_http_log_point:  # 抛出所有异常日志
                #     Logger().exception_log_print(log_point=TB_EXCEPTION_HTTP_LOG_POINT)
                raise
            return rsp_body

        return _wrap

    return real_warp


def singleton(cls, *args, **kwargs):
    """
    单例修饰器
    """
    instances = {}

    def _singleton():
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return _singleton


class MyLoggerAdapter(logging.LoggerAdapter):

    def auto_json(self,data):
        """
        自动将str进行json包装，如果已经是json结构则不进行包装
        :return:
        """
        if isinstance(data,dict):
            try:
                d = json.dumps(data)
                return d
            except Exception as e:
                return data
        else:
            return data

    def log(self, level,msg,**kwargs):
        from app import TBG
        set_level = TBG.global_config['LOG_LEVEL']
        if set_level == 'INFO' and level == 'DEBUG':
            return

        if 'delay_conf' in kwargs['extra']:
            msg = self.auto_json(msg)
            # 代表此类日志为延迟记录类日志
            pass
        else:
            # print 'loggggggggggggggggggggg'
            lf = inspect.currentframe()
            current_frame_name = ''
            last_fid = ''
            last_request_id = ''
            last_order_id = ''
            last_provider_channel = ''
            last_sub_order_id = ''
            last_ota_name = ''
            last_proxy_pool = ''
            last_tb_is_log_debug = ''

            # 日志level
            sub_level = kwargs.get('extra',{}).get('sub_level', 'SYS')
            for x in range(0, 10):
                lf = lf.f_back
                if (last_provider_channel and last_ota_name and last_request_id and last_fid and last_order_id and current_frame_name and last_tb_is_log_debug and last_proxy_pool) or lf == None:
                    break

                if not last_provider_channel and 'TB_PROVIDER_CHANNEL' in lf.f_locals:
                    last_provider_channel = lf.f_locals['TB_PROVIDER_CHANNEL']
                if not last_ota_name and 'TB_OTA_NAME' in lf.f_locals:
                    last_ota_name = lf.f_locals['TB_OTA_NAME']
                if not last_fid and 'TB_FRAME_ID' in lf.f_locals:
                    last_fid = lf.f_locals['TB_FRAME_ID']
                if not last_fid and 'TB_FRAME_ID' in lf.f_locals:
                    last_fid = lf.f_locals['TB_FRAME_ID']
                if not current_frame_name and 'TB_FRAME_NAME' in lf.f_locals:
                    current_frame_name = lf.f_locals['TB_FRAME_NAME']
                if not last_request_id and 'TB_REQUEST_ID' in lf.f_locals:
                    last_request_id = lf.f_locals['TB_REQUEST_ID']
                if not last_order_id and 'TB_ORDER_ID' in lf.f_locals:
                    last_order_id = lf.f_locals['TB_ORDER_ID']
                if not last_sub_order_id and 'TB_SUB_ORDER_ID' in lf.f_locals:
                    last_sub_order_id = lf.f_locals['TB_SUB_ORDER_ID']

                if not last_proxy_pool and 'TB_PROXY_POOL' in lf.f_locals:
                    last_proxy_pool = lf.f_locals['TB_PROXY_POOL']
                if not last_tb_is_log_debug and 'TB_IS_LOG_DEBUG' in lf.f_locals:
                    last_tb_is_log_debug = lf.f_locals['TB_IS_LOG_DEBUG']

            if last_tb_is_log_debug == 'Enable' and level == 'DEBUG': # 如果调试日志功能开启，则所有日志变为 info等级
                level = 'INFO'
            kwargs['extra'] = {'tbasctime': Time.time_str_2(), 'frame_id': last_fid, 'frame_name': current_frame_name, 'request_id': last_request_id, 'sub_level': sub_level, 'order_id': last_order_id,
                               'tb_app_name': self.extra.get('tb_app_name', ''), 'ota_name': last_ota_name, 'provider_channel': last_provider_channel,'sub_order_id':last_sub_order_id,'proxy_pool':last_proxy_pool}


            msg = self.auto_json(msg)
        int_level =  getLevelName(level)

        self.logger.log(int_level, msg,**kwargs)


@singleton
class Logger(object):
    """
    封装日志输出 - 单例
    """

    def __init__(self):
        self.logger = None
        self.http_log_storage_dict = {}

    def init_main_logger(self, conf, sentry_logger=None, tb_app_name=''):
        """
        初始化主日志，用于错误/异常的记录
        :param sentry_logger:  sentry logger
        :param conf:
        :return:
        """
        logging.config.dictConfig(conf)
        logger = logging.getLogger('logger_access_log')
        # 初始化一个要传递给LoggerAdapter构造方法的上下文字典对象
        extra_dict = {"frame_id": "", "frame_name": "", 'request_id': '', 'tb_app_name': tb_app_name, 'sub_level': '', 'order_id': '', 'provider_channel': '', 'ota_name': '','sub_order_id':'','proxy_pool':''}

        # 获取一个自定义LoggerAdapter类的实例
        self.logger = MyLoggerAdapter(logger, extra_dict)
        self.tb_app_name = tb_app_name
        self.sentry_logger = sentry_logger

    def error(self, info, trackback=True, to_sentry=True):
        """
        日志打印[error]
        :param to_sentry: 是否发送 sentry
        :param info: 打印信息
        :param trackback: 是否打印栈信息
        """

        if trackback:
            self.logger.log('ERROR',info, exc_info=True, extra={'sub_level': 'USR','main_level':'ERROR'})
        else:
            self.logger.log('ERROR',info, extra={'sub_level': 'USR','main_level':'ERROR'})
        if to_sentry and self.sentry_logger:
            try:
                self.sentry_logger.captureException()
            except Exception as e:
                pass

    def warn(self, info, to_sentry=True):
        """
        日志打印[warn]
        :param to_sentry: 是否发送 sentry
        :param info: 打印信息
        """

        self.logger.log('WARNING',info, extra={'sub_level': 'USR','main_level':'WARN'})
        if to_sentry and self.sentry_logger:
            self.sentry_logger.captureMessage(info)

    def debug(self, info):
        """
        日志打印[debug]
        :param info: 打印信息
        :param trackback: 是否打印栈信息
        """

        self.logger.log('DEBUG',info, extra={'sub_level': 'USR','main_level':'DEBUG'})

    def info(self, info):
        """
        日志打印[info]
        :param info: 打印信息
        """
        self.logger.log('INFO',info, extra={'sub_level': 'USR','main_level':'INFO'})

    def serror(self, info, trackback=True, to_sentry=True):
        """
        日志打印[error]
        :param to_sentry: 是否发送 sentry
        :param info: 打印信息
        :param trackback: 是否打印栈信息
        """

        if trackback:
            self.logger.log('ERROR',info, exc_info=True, extra={'sub_level': 'SYS','main_level':'ERROR'})
        else:
            self.logger.log('ERROR',info, extra={'sub_level': 'SYS','main_level':'ERROR'})
        if to_sentry and self.sentry_logger:
            try:
                self.sentry_logger.captureException()
            except Exception as e:
                pass

    def swarn(self, info, to_sentry=True):
        """
        日志打印[warn]
        :param to_sentry: 是否发送 sentry
        :param info: 打印信息
        """

        self.logger.log('WARNING',info, extra={'sub_level': 'SYS','main_level':'WARN'})
        if to_sentry and self.sentry_logger:
            self.sentry_logger.captureMessage(info)

    def sdebug(self, info):
        """
        日志打印[debug]
        :param info: 打印信息
        :param trackback: 是否打印栈信息
        """

        self.logger.log('DEBUG',info, extra={'sub_level': 'SYS','main_level':'DEBUG'})

    def sinfo(self, info):
        """
        日志打印[info]
        :param info: 打印信息
        """
        self.logger.log('INFO',info, extra={'sub_level': 'SYS','main_level':'INFO'})

    def hinfo(self, info):
        """
        日志打印[info]
        :param info: 打印信息
        """
        self.logger.log('INFO',info, extra={'sub_level': 'HTTP','main_level':'INFO'})

    def hdebug(self, info):
        """
        日志打印[info]
        :param info: 打印信息
        """
        self.logger.log('DEBUG',info, extra={'sub_level': 'HTTP','main_level':'DEBUG'})

    def herror(self, info):
        """
        日志打印[info]
        :param info: 打印信息
        """
        self.logger.log('ERROR',info,exc_info=True,  extra={'sub_level': 'HTTP','main_level':'ERROR'})

    def hwarn(self, info):
        """
        日志打印[info]
        :param info: 打印信息
        """
        self.logger.log('WARNING',info, extra={'sub_level': 'HTTP','main_level':'WARN'})



    def http_log(self, http_result):
        """
        用于记录http请求响应日志
        :return:
        """

        # 寻找最近的 LOG POINT并记录日志

        lf = inspect.currentframe()
        last_exception_http_log_point = None
        current_frame_name = ''
        last_fid = ''
        last_request_id = ''
        last_order_id = ''
        last_provider_channel = ''
        last_ota_name = ''
        last_sub_order_id = ''
        last_proxy_pool = ''
        sub_level = 'HTTP'


        for x in range(0, 20):
            lf = lf.f_back

            if (last_exception_http_log_point is not None and last_request_id and last_fid and last_order_id and current_frame_name and last_proxy_pool) or lf == None:
                break
            # print lf.f_locals
            if not last_provider_channel and 'TB_PROVIDER_CHANNEL' in lf.f_locals:
                last_provider_channel = lf.f_locals['TB_PROVIDER_CHANNEL']
            if not last_ota_name and 'TB_OTA_NAME' in lf.f_locals:
                last_ota_name = lf.f_locals['TB_OTA_NAME']

            if not last_fid and 'TB_FRAME_ID' in lf.f_locals:
                last_fid = lf.f_locals['TB_FRAME_ID']
            if not current_frame_name and 'TB_FRAME_NAME' in lf.f_locals:
                current_frame_name = lf.f_locals['TB_FRAME_NAME']
            if not last_request_id and 'TB_REQUEST_ID' in lf.f_locals:
                last_request_id = lf.f_locals['TB_REQUEST_ID']
            if not last_order_id and 'TB_ORDER_ID' in lf.f_locals:
                last_order_id = lf.f_locals['TB_ORDER_ID']
            if not last_sub_order_id and 'TB_SUB_ORDER_ID' in lf.f_locals:
                last_sub_order_id = lf.f_locals['TB_SUB_ORDER_ID']
            if not last_proxy_pool and 'TB_PROXY_POOL' in lf.f_locals:
                last_proxy_pool = lf.f_locals['TB_PROXY_POOL']
            if last_exception_http_log_point is None and 'TB_EXCEPTION_HTTP_LOG_POINT' in lf.f_locals:
                last_exception_http_log_point = lf.f_locals.get('TB_EXCEPTION_HTTP_LOG_POINT', '')

        if last_exception_http_log_point:
            extra = {'tbasctime': Time.time_str_2(), 'frame_id': last_fid, 'frame_name': current_frame_name, 'request_id': last_request_id, 'sub_level': sub_level, 'order_id': last_order_id,
                     'tb_app_name': self.tb_app_name, 'delay_conf': '', 'ota_name': last_ota_name, 'provider_channel': last_provider_channel,'sub_order_id':last_sub_order_id,'proxy_pool':last_proxy_pool}
            if last_exception_http_log_point in self.http_log_storage_dict:
                self.http_log_storage_dict[last_exception_http_log_point].append({'http_result': http_result, 'extra': extra})
            else:
                self.http_log_storage_dict[last_exception_http_log_point] = [{'http_result': http_result, 'extra': extra}]

    def http_log_print(self, log_point):
        """
        打印存储的节点http请求日志
        :param log_point:
        :return:
        """
        if log_point in self.http_log_storage_dict:
            for log in self.http_log_storage_dict[log_point]:
                self.logger.log('INFO',log['http_result'], extra=log['extra'])
