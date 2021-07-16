#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, too-many-arguments, broad-except, anomalous-backslash-in-string
# pylint: disable=missing-docstring, line-too-long, too-few-public-methods
"""
# @Author  : wxt
# @Software: PyCharm
"""

# 供应商搜索异常
PROVIDER_SEARCH_ERR_CODE = {
    'HIGH_REQ_LIMIT':'高频限制',
    'NOFLIGHT' :'无航班',
    'REQPARAM_ERROR' :'请求参数错误',
    'ERROR': '未知错误',
}

class TBException(Exception):
    def __init__(self, err='',err_code='ERROR'):
        if not err:
            err = "%s,err_code:%s" %(self.err,err_code)
        self.err_code = err_code
        Exception.__init__(self, err)

class Critical(TBException):
    """
    致命异常，用于忽略所有错误重试，直接返回使用
    """
    err = ''


#验证码

class CaptchaCrackException(TBException):
    err = '验证码识别错误'


class CaptchaQueryBalcException(TBException):
    err = '验证码余额查询错误'

class CaptchaJusticeException(TBException):
    err = '验证码报错回填错误'

class CaptchaLackBalcException(TBException):
    err = '验证码余额不足'

# 邮件

class MailRecvException(TBException):
    err = '邮件收取错误'


# provider error

class RegisterCritical(Critical):
    err = '注册致命错误'

class NoSmsMobileCritical(Critical):
    err = '没有可用手机'

class NoEmailCritical(Critical):
    err = '没有可用邮箱'

class RegisterException(TBException):
    err = '注册错误'

class ProviderVerifyException(TBException):
    err = '供应商验价异常'

class ProviderVerifyFail(TBException):
    err = '供应商验价失败'

class LoginException(TBException):
    err = '登陆错误'

class GetSessionException(TBException):
    err = '获取session错误'


class LoginCritical(Critical):
    err = '注册致命错误'

class BookingException(TBException):
    err = '下单错误'

class CheckOrderStatusException(TBException):
    err = '订单状态检查错误'


class FlightSearchException(TBException):
    err = '航班查询错误'

class FlightSearchCritical(Critical):
    err = '航班查询致命错误'

class PayException(TBException):
    err = '支付错误'


class GetCouponException(TBException):
    err = '优惠券获取错误'

class PreOrderCheckException(TBException):
    err = '订单预检测错误'

class NoSimulateBookingDefineException(TBException):
    err = '没有定义仿真下单模块'

class CaptchaCrackResultWrongException(TBException):
    err = '验证码识别错误'

class HighFreqLockException(TBException):
    err = '高频搜索错误'

#OTA

class FusingException(TBException):
    err = '熔断报错'

class NotAllowChildException(TBException):
    err = '不允许儿童报错'

class OTATokenException(TBException):
    err = 'OTAToken 错误'

class ProviderTokenException(TBException):
    err = 'ProviderToken 错误'

class VerifyInterfaceException(TBException):
    err = '验价接口错误'


class SearchInterfaceException(TBException):
    err = '询价接口错误'

class OrderInterfaceException(TBException):
    err = '生单接口错误'

class NoticePayInterfaceException(TBException):
    err = '通知扣款接口错误'

class NoticeIssueInterfaceException(TBException):
    err = '通知出票接口错误'

class OrderDetailInterfaceException(TBException):
    err = '订单详情接口错误'

class OrderListInterfaceException(TBException):
    err = '订单列表接口错误'

class ConfigInterfaceException(TBException):
    err = '配置接口错误'

class ExportOrderListException(TBException):
    err = '导出订单列表错误'


class ExportOrderDetailException(TBException):
    err = '导出订单详情错误'


class SetOrderIssuedException(TBException):
    err = '回调票号错误'

class OrderByPollException(TBException):
    err = '拉取订单错误'

class NoSuchOTAException(TBException):
    err = '无此供应商错误'

class NoSuchProviderException(TBException):
    err = '无此供应商错误'

class FetchOTAConfigException(TBException):
    err = '获取供应商配置错误'


class OrderStatusException(TBException):
    err = '订单状态输入错误'



class AccessControlException(TBException):
    err = '访问控制异常'


# router
class RouterDeliverExeception(TBException):
    err = '路由分发错误'


#crawler

class CrawlerException(TBException):
    err = '路由分发错误'

class ProxyException(TBException):
    err = '代理错误'

#http
class HttpException(TBException):
    err = 'Http错误'

# 内部数据错误


class InternalDataException(TBException):
    err = '内部数据错误'

if __name__ == '__main__':
    try:
        f = s
        raise LoginCritical
    except Critical as e:
        a = e
    except Exception as e:
        a = e

    raise e