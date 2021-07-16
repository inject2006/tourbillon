#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, too-many-arguments, broad-except, anomalous-backslash-in-string
# pylint: disable=missing-docstring, line-too-long, too-few-public-methods
"""
# @Author  : wxt
# @Software: PyCharm
验证码识别模块
"""

import json
import requests
from urllib import quote
from ..utils.exception import *
from ..utils.util import Time
from .captcha_vender.fateadm_api import FateadmApi
from ..utils.logger import Logger
from app import TBG


class CaptchaCracker(object):
    @staticmethod
    def select(vender_class):
        """

        :param vender_class: 传入验证码厂商类名
        :return:
        """
        for sub_class in CaptchaBase.__subclasses__():
            if sub_class.__name__ == vender_class:
                return sub_class()
        raise Exception('No such captcha vender: %s' % vender_class)


class CaptchaBase(object):
    """
    验证码破解基类
    """

    def query_balc(self, **kwargs):
        Logger().sinfo('Captcha[{vender}] query_balc '.format(vender=self.__class__.__name__))
        try:
            return self._query_balc(**kwargs)
        except Exception as e:
            Logger().serror('Captcha[{vender}] query_balc Error'.format(vender=self.__class__.__name__))
            raise CaptchaQueryBalcException

    def _query_balc(self, **kwargs):
        """
        查询余额
        :return:
        """
        pass

    def crack(self, *args, **kwargs):
        exception = ''
        start_time = Time.timestamp_ms()
        Logger().sinfo('Captcha[{vender}] Crack '.format(vender=self.__class__.__name__))
        try:
            crack_result = self._crack(*args, **kwargs)
            Logger().sinfo('Captcha[{vender}] Crack result {crack_result}'.format(vender=self.__class__.__name__, crack_result=crack_result))
            return_status = 'SUCCESS'
        except Exception as e:
            Logger().serror('Captcha[{vender}] Crack Error'.format(vender=self.__class__.__name__))
            return_status = 'ERROR'
            exception = str(e)

        total_latency = Time.timestamp_ms() - start_time
        TBG.tb_metrics.write(
            "FRAMEWORK.CAPTCHA",
            tags=dict(
                app=self.captcha_app,
                return_status=return_status,
                exception=exception
            ),
            fields=dict(
                total_latency=total_latency,
                count=1
            ))
        if return_status == 'ERROR':
            raise CaptchaCrackException
        else:
            return crack_result


    def _crack(self, **kwargs):
        """
        破解主逻辑
        :param kwargs:
        :return:
        """
        raise NotImplementedError

    def justice(self, **kwargs):
        exception = ''
        start_time = Time.timestamp_ms()
        Logger().sinfo('Captcha[{vender}] justice'.format(vender=self.__class__.__name__))

        try:
            result = self._justice(**kwargs)
            return_status = 'JUSTICE'
        except Exception as e:
            Logger().serror('Captcha[{vender}] justice Error'.format(vender=self.__class__.__name__))
            return_status = 'ERROR'
            exception = str(e)

        total_latency = Time.timestamp_ms() - start_time
        TBG.tb_metrics.write(
            "FRAMEWORK.CAPTCHA",
            tags=dict(
                app=self.captcha_app,
                return_status=return_status,
                exception=exception
            ),
            fields=dict(
                total_latency=total_latency,
                count=1
            ))
        if return_status == 'ERROR':
            raise CaptchaJusticeException
        else:
            return result
    def _justice(self, **kwargs):
        """
        验证错误需调用此接口
        :return:
        """
        pass


class Fateadm(CaptchaBase):
    """

    """
    captcha_app = 'fateadm'

    def __init__(self):
        # 账号信息
        pd_id = "103696"
        pd_key = "hkydLE5TUCcPDRDPlBuV/Rr02S/ipt8i"
        app_id = "303896"
        app_key = "g5Jf4Jrwjm+tQpcAL6xr+C71EzD/WfS4"

        self.pred_type = "30400"
        self.request_id = None
        self.api = FateadmApi(app_id, app_key, pd_id, pd_key)

    def _query_balc(self):
        """
        :return:
        """
        rsp = self.api.QueryBalc()
        if rsp.ret_code == 0:
            Logger().sinfo("query succ ret: {} cust_val: {} rsp: {} pred: {}".format(rsp.ret_code, rsp.cust_val, rsp.err_msg,
                                                                                     rsp.pred_rsp.value))
        else:
            Logger().swarn("query failed ret: {} err: {}".format(rsp.ret_code, rsp.err_msg.encode('utf-8')))

    def _crack(self, img_stream):
        """
        返回识别结果
        :param img_stream:  图片流
        :return:
        """

        with open('login_captcha.jpg', 'wb') as fp:
            fp.write(img_stream)
        tries = 3
        try_count = 0
        while 1:
            rsp = self.api.Predict(self.pred_type, img_stream)
            if rsp.ret_code == 0:
                captcha_code = rsp.pred_rsp.value
                self.request_id = rsp.request_id
                return captcha_code
            else:
                Logger().swarn("recognize rsp error")
                try_count += 1
                if tries == 3:
                    break
        raise CaptchaCrackException

    def _justice(self):
        self.api.Justice(self.request_id)


class C2567(CaptchaBase):
    """
    验证码破解基类
    """

    captcha_app = 'c2567'

    def __init__(self):
        self.referer = quote('https://www.douban.com')
        self.user = 'inject2006'
        self.password = 'xiaoxiao1'

    def _query_balc(self):
        """
        查询余额
        :return:
        """

        checked_gee = requests.get(
            'http://jiyanapi.c2567.com/chaxundianshu?user=%s&pass=%s' % (self.user, self.password)).json()
        Logger().sinfo(checked_gee)
        return checked_gee

    def _crack(self, geetest_gt, geetest_challenge):
        """
        破解主逻辑
        :param kwargs:
        :return: fail {u'status': u'no', u'msg': u'\u8bf7\u91cd\u8bd5 2004'}
        """
        checked_gee = requests.get(
            'http://jiyanapi.c2567.com/shibie?gt=%s&challenge=%s&referer=%s&area=null&user=%s&pass=%s&return=json&format=utf8&model=3' % (
                geetest_gt, geetest_challenge, self.referer, self.user, self.password)).json()
        if checked_gee['status'] == 'no':
            raise CaptchaCrackException
        return checked_gee


class AliSlide(CaptchaBase):
    def __init__(self):
        """
        初始化Ali滑动
        :param key: 平台Key
        """
        self.__key = 'xA2uPxQSOH'

    def get_nvc(self, a, scene):
        """
        获取无感知
        :param a: 阿里ID e.g. FFFF0N00000000000B27
        :param scene: 阿里场景 e.g. ic_login
        :return: 阿里滑动结果
        """
        session = requests.Session()
        session.headers = {
            "User-Agent": "YEXP"
        }
        # 从冷月API获取UA
        params = {
            "token": self.__key,
            "channel": 10
        }
        ua_data = json.loads(session.get(
            "https://api.yuekuai.tech/api/ali-ua",
            params=params
        ).text)

        if not ua_data["code"] == 0:
            raise Exception("UA获取失败, " + ua_data["msg"])
        ua_data = ua_data["data"]

        # nvcPrepare 包
        prepare_data = {
            "a": a,
            "d": scene,
            "c": ua_data["t"]
        }
        params = {
            "a": json.dumps(prepare_data),
            "callback": "callback"
        }
        response = session.get(
            "http://cf.aliyun.com/nvc/nvcPrepare.jsonp",
            params=params
        ).text
        response = response.replace("callback(", "").replace(");", "")
        prepare_value = json.loads(response)["result"]["result"]["c"]

        # nvcAnalyze 包
        analyze_data = {
            "a": a,
            "d": scene,
            "c": ua_data["t"],
            "h": {
                "key1": "code0",
                "nvcCode": 200
            },
            "j": {
                "test": 1
            },
            "b": ua_data["n"],
            "e": prepare_value
        }
        params = {
            "a": json.dumps(analyze_data),
            "callback": "callback"
        }
        response = session.get(
            "http://cf.aliyun.com/nvc/nvcAnalyze.jsonp",
            params=params
        ).text
        response = response.replace("callback(", "").replace(");", "")
        data = json.loads(response)
        answer = dict()
        answer["data"] = dict()
        answer["code"] = data["result"]["code"]
        if data["result"]["code"] == 200:
            answer["data"] = {
                "token": ua_data["t"],
                "sig": data["result"]["result"]["sig"],
                "sessionId": data["result"]["result"]["sessionId"]
            }
        return answer

    def get(self, a, scene, token=""):
        """
        获取普通滑动
        :param a: 阿里ID e.g. FFFF0N00000000000B27
        :param scene: 阿里场景 e.g. ic_login
        :param token: 自定义Token
        :return: 阿里滑动结果
        """
        session = requests.Session()
        session.headers = {
            "User-Agent": "YEXP"
        }
        # 从冷月API获取UA
        params = {
            "token": self.__key,
            "channel": 2
        }
        if token != "":
            params["channel"] = 1001
            params["ali_token"] = token
        ua_data = json.loads(session.get(
            "https://api.yuekuai.tech/api/ali-ua",
            params=params
        ).text)
        print(ua_data)
        if not ua_data["code"] == 0:
            raise Exception("UA获取失败, " + ua_data["msg"])
        ua_data = ua_data["data"]

        # analyze 包
        params = {
            "a": a,
            "scene": scene,
            "t": ua_data["t"],
            "n": ua_data["n"],
            "p": '{"key1":"code0","ncSessionID":"6ec92a1a8218"}',
            "asyn": 0,
            "lang": "cn",
            "v": 948,
            "callback": "jsonp_005435618450401902"
        }
        response = session.get(
            "http://cf.aliyun.com/nocaptcha/analyze.jsonp",
            params=params
        ).text
        response = response.replace("jsonp_005435618450401902(", "").replace(");", "")
        data = json.loads(response)
        answer = dict()
        answer["data"] = dict()
        answer["code"] = data["result"]["code"]
        if data["result"]["code"] == 0:
            answer["data"] = {
                "token": ua_data["t"],
                "sig": data["result"]["value"],
                "csessionid": data["result"]["csessionid"]
            }
        return answer

    def get_scratch(self, a, scene):
        """
        获取普通滑动
        :param a: 阿里ID e.g. FFFF0N00000000000B27
        :param scene: 阿里场景 e.g. ic_login
        :return: 阿里滑动结果
        """
        session = requests.Session()
        session.headers = {
            "User-Agent": "YEXP"
        }
        # 从冷月API获取UA
        params = {
            "token": self.__key,
            "channel": 6
        }
        ua_data = json.loads(session.get(
            "https://api.yuekuai.tech/api/ali-ua",
            params=params
        ).text)
        if not ua_data["code"] == 0:
            raise Exception("UA获取失败, " + ua_data["msg"])
        ua_data = ua_data["data"]
        # analyze 包
        params = {
            "a": a,
            "scene": scene,
            "t": ua_data["t"],
            "n": ua_data["n"],
            "p": '{"key1":"code0"}',
            "jsType": "h5",
            "lang": "cn",
            "s": ua_data["u"],
            "v": 933,
            "callback": "__jsonp_005435618450401902"
        }
        response = session.get(
            "http://cf.aliyun.com/scratchCardSlide/analyze.jsonp",
            params=params
        ).text
        response = response.replace("__jsonp_005435618450401902(", "").replace(");", "")
        data = json.loads(response)
        answer = dict()
        answer["data"] = dict()
        answer["code"] = data["result"]["result"]["code"]
        if data["success"]:
            answer["data"] = {
                "token": ua_data["t"],
                "sig": data["result"]["result"]["sig"],
                "csessionid": data["result"]["result"]["sessionId"]
            }
        return answer


if __name__ == '__main__':
    pass
