#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, too-many-arguments, broad-except, anomalous-backslash-in-string
# pylint: disable=missing-docstring, line-too-long, too-few-public-methods
"""
# @Author  : wxt
# @Software: PyCharm
"""

import requests
import datetime
import json as json_obj
import inspect
import gevent
import random
import traceback
from app import TBG
from ..utils.util import Time
from ..utils.exception import *
from ..utils.logger import Logger
from requests.adapters import ProxyError


class HttpResult:
    __slots__ = ['request_time', 'req_raw_url', 'latency', 'response_headers', 'is_redirect',
                 'response_status_code', 'is_req_success', 'is_req_timeout', 'is_proxy_error',
                 'exception', 'content', 'content_type', 'req_raw_data', 'retries', 'req_cookie', 'is_loop_waited', 'proxy_backend_ip',
                 'current_url','proxy_pool','proxy_info']

    def __init__(self):
        self.content_truncate_length = 2000
        self.request_time = Time.time_str()
        self.req_raw_url = None
        self.req_raw_data = None
        self.latency = 0
        self.content = ''
        self.content_type = ''
        self.response_status_code = None
        self.is_req_success = None
        self.is_req_timeout = False
        self.is_proxy_error = False
        self.proxy_backend_ip = None  # 如果挂载代理则其代理IP地址
        self.req_cookie = None
        self.response_headers = []
        self.exception = ""
        self.proxy_pool = ""
        self.proxy_info = ""
        self.retries = 0
        self.is_loop_waited = False  # 是否在anti_block_wait 模式下进行了等待
        self.is_redirect = False
        self.current_url = ''

    def to_json(self):
        try:
            return json_obj.loads(self.content)
        except Exception as e:
            raise HttpException('JSON LOADS FAILED')

    def sub_string(self, string, length):
        if length >= len(string):
            return string

        result = ''
        i = 0
        p = 0

        while True:
            ch = ord(string[i])
            # 1111110x
            if ch >= 252:
                p = p + 6
            # 111110xx
            elif ch >= 248:
                p = p + 5
            # 11110xxx
            elif ch >= 240:
                p = p + 4
            # 1110xxxx
            elif ch >= 224:
                p = p + 3
            # 110xxxxx
            elif ch >= 192:
                p = p + 2
            else:
                p = p + 1

            if p >= length:
                break
            else:
                i = p
        return string[0:i]

    def sub_content(self, length):
        c = self.content
        try:
            c.decode('utf8')
        except Exception as e:
            c = 'unable to decode'
        return self.sub_string(c, length)

    def to_log_json(self):
        # 缩减content大小，用于存放日志

        dic = {attr: getattr(self, attr) for attr in self.__slots__}
        if self.content_type == 'image':
            dic['content'] = 'image data'
        else:
            try:
                dic['content'].decode('utf8')
            except Exception as e:
                dic['content'] = 'unable to decode'
        dic['content'] = self.sub_string(dic['content'], self.content_truncate_length)
        return dic


class HttpRequest(object):
    def __init__(self, lock_proxy_pool=None,  timeout=30):

        if TBG.global_config['RUN_MODE'] == 'TEST':  # 锁定该session只能使用某种代理模式，只对生产有效
            self.lock_proxy_pool = None
        else:
            self.lock_proxy_pool = lock_proxy_pool
        TB_PROXY_POOL = self.lock_proxy_pool
        requests.packages.urllib3.disable_warnings()
        self.timeout = timeout or 10
        self.proxy_error_tries = 2  # 因为代理失败导致的请求失败重试次数
        self.http_session = requests.Session()

        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36'
                   }

        self.http_session.headers.update(headers)
        # 代理相关
        self.retry_get_anti_block_ip_count = 5  # 被封IP重新尝试次数
        self.current_proxy_ip = None  # 当前预置的代理IP，下次请求将使用此IP 赋值格式元组： (proxy_url,backend_ip,)

        self.last_http_result = None  # 记录上一次的result实例

    def update_cookie(self, cookie_dict={}):
        c = requests.cookies.RequestsCookieJar()  # 定义一个cookie对象
        for k, v in cookie_dict.iteritems():
            c.set(k, v)  # 增加cookie的值
        self.http_session.cookies.update(c)

    def update_headers(self, headers={}):
        self.http_session.headers.update(headers)

    def get_cookies(self):
        return self.http_session.cookies.get_dict()

    def get_headers(self):
        return dict(self.http_session.headers)


    def proxy_pool_a(self):
        """

        """
        first_proxy_ip = None
        try:
            proxy_pool_key = 'PPOOL_A'
            while 1:
                proxy_ip = TBG.redis_conn.redis_pool.brpoplpush(proxy_pool_key, proxy_pool_key, 3)
                # Logger().hdebug('proxy_data %s'%proxy_ip)
                if not proxy_ip:
                    break
                if first_proxy_ip == None:
                    first_proxy_ip = proxy_ip
                elif first_proxy_ip == proxy_ip:
                    # 认为已经轮询过一圈
                    # Logger().debug('first_proxy_ip %s proxy_ip %s'%(first_proxy_ip,proxy_ip))
                    raise ProxyException('NoAvailableProxyIp')

                try:
                    if (datetime.datetime.strptime(proxy_ip.split('@')[-1], '%Y-%m-%d %H:%M:%S'
                                                   ) - datetime.timedelta(seconds=15)) < datetime.datetime.now():
                        continue
                except Exception as e:
                    continue

                proxy_ip = proxy_ip.split('@')[0]
                return 'http://%s' % proxy_ip,proxy_ip.split(':')[0]
        except Exception as e:
            Logger().herror(e)
            raise ProxyException('NoAvailableProxyIp')

    def proxy_pool_c(self):
        """

        :return:
        """
        first_proxy_ip = None
        try:
            proxy_pool_key = 'PPOOL_C'
            while 1:
                proxy_ip = TBG.redis_conn.redis_pool.brpoplpush(
                    proxy_pool_key, proxy_pool_key, 3)
                # Logger().hdebug('proxy_data %s'%proxy_ip)
                if not proxy_ip:
                    break

                if first_proxy_ip == None:
                    first_proxy_ip = proxy_ip
                elif first_proxy_ip == proxy_ip:
                    # 认为已经轮询过一圈
                    # Logger().debug('first_proxy_ip %s proxy_ip %s'%(first_proxy_ip,proxy_ip))
                    raise ProxyException('NoAvailableProxyIp')

                try:
                    if (datetime.datetime.strptime(proxy_ip.split('@')[-1], '%Y-%m-%d %H:%M:%S'
                                                   ) - datetime.timedelta(seconds=5 * 60)) < datetime.datetime.now():
                        continue
                except:
                    continue

                return_proxy_ip = proxy_ip.split('@')[0]
                return 'http://{}'.format(return_proxy_ip),return_proxy_ip.split(':')[0]
        except Exception as e:
            Logger().herror(e)
            raise ProxyException('NoAvailableProxyIp')

    def proxy_pool_d(self):
        """

        :return:
        """
        first_proxy_ip = None
        try:
            proxy_pool_key = 'PPOOL_D'
            while 1:
                proxy_ip = TBG.redis_conn.redis_pool.brpoplpush(proxy_pool_key, proxy_pool_key, 3)
                # Logger().hdebug('proxy_data %s'%proxy_ip)
                if not proxy_ip:
                    break
                if first_proxy_ip == None:
                    first_proxy_ip = proxy_ip
                elif first_proxy_ip == proxy_ip:
                    # 认为已经轮询过一圈
                    # Logger().debug('first_proxy_ip %s proxy_ip %s'%(first_proxy_ip,proxy_ip))
                    raise ProxyException('NoAvailableProxyIp')

                try:
                    if (datetime.datetime.strptime(proxy_ip.split('@')[-1], '%Y-%m-%d %H:%M:%S'
                                                   ) - datetime.timedelta(seconds=10)) < datetime.datetime.now():
                        continue
                except:
                    continue

                proxy_ip = proxy_ip.split('@')[0]
                return 'http://{}'.format(proxy_ip),proxy_ip.split(':')[0]
        except Exception as e:
            Logger().herror(e)
            raise ProxyException('NoAvailableProxyIp')


    def proxy_pool_e(self):
        """
        E池 用于生单
        特性：IP少，3-5分钟更换，可自定义地区，价格优惠，延迟低
        """
        proxy_pool_key = 'PPOOL_E'
        e_pool_list = [
            'socks5://13461346:13461346@s1.yhtip.com:61777',
            # 'socks5://33291221:33291221@s1.yhtip.com:61777',
            'socks5://33291001:33291001@s1.yhtip.com:61777'
        ]
        proxy_addr = TBG.redis_conn.redis_pool.rpop(proxy_pool_key)
        if not proxy_addr:
            proxy_addr = e_pool_list[-1]
            for e in e_pool_list:
                TBG.redis_conn.redis_pool.lpush(proxy_pool_key, e)
        else:
            TBG.redis_conn.redis_pool.lpush(proxy_pool_key, proxy_addr)
        return proxy_addr, 'N/A'

    # block功能暂时注释掉 后续在开发  2019-01-22 by wxt
    # def block_proxy_ip(self, proxy_ip, provider_channel):
    #     if not provider_channel:
    #         provider_channel = 'public'
    #     if 'http://' in proxy_ip:
    #         block_ip_key = 'block_ip_%s_%s' % (provider_channel, proxy_ip.split('http://')[1])
    #         TBG.redis_conn.insert_value(block_ip_key, 'timeout', ex=1000)

    def proxy_pool_f(self):
        """
        F池
        特性： IP少，可自定义地区，延迟低，5-120分钟
        """
        first_proxy_ip = None
        try:
            proxy_pool_key = 'PPOOL_F'
            while 1:
                proxy_ip = TBG.redis_conn.redis_pool.brpoplpush(
                    proxy_pool_key, proxy_pool_key, 3)
                # Logger().hdebug('proxy_data %s'%proxy_ip)
                if not proxy_ip:
                    break

                if first_proxy_ip == None:
                    first_proxy_ip = proxy_ip
                elif first_proxy_ip == proxy_ip:
                    # 认为已经轮询过一圈
                    # Logger().debug('first_proxy_ip %s proxy_ip %s'%(first_proxy_ip,proxy_ip))
                    raise ProxyException('NoAvailableProxyIp')

                try:
                    if (datetime.datetime.strptime(proxy_ip.split('@')[-1], '%Y-%m-%d %H:%M:%S'
                                                   ) - datetime.timedelta(seconds=2 * 60)) < datetime.datetime.now():
                        continue
                except:
                    continue

                return_proxy_ip = proxy_ip.split('@')[0]
                return 'http://{}'.format(return_proxy_ip), return_proxy_ip.split(':')[0]
        except Exception as e:
            Logger().herror(e)
            raise ProxyException('NoAvailableProxyIp')


    def proxy_pool_g(self):
        """
        G池 用于生单
        特性：IP少，3-5分钟更换，可自定义地区，价格优惠，延迟低
        """
        proxy_pool_key = 'PPOOL_G'
        e_pool_list = [
            'socks5://13461346:13461346@s1.yhtip.com:61777',
            'socks5://33291001:33291001@s1.yhtip.com:61777'
        ]
        proxy_addr = TBG.redis_conn.redis_pool.rpop(proxy_pool_key)
        if not proxy_addr:
            proxy_addr = e_pool_list[-1]
            for e in e_pool_list:
                TBG.redis_conn.redis_pool.lpush(proxy_pool_key, e)
        else:
            TBG.redis_conn.redis_pool.lpush(proxy_pool_key, proxy_addr)
        return proxy_addr, 'N/A'

    def get_proxy_ip(self, proxy_pool, result=None):
        """
        代理IP获取主逻辑
        :return:

        """
        try:
            result.proxy_pool = proxy_pool
            proxy_pool = 'proxy_pool_%s' % proxy_pool.lower()
            ip_info = getattr(self,proxy_pool)()
            if ip_info:
                result.proxy_info = ip_info
                self.http_session.keep_alive = False
                return ip_info
            else:
                return None
        except ProxyException as e:
            if result:
                result.is_proxy_error = True
                result.exception = 'NoAvailableProxyIp'
                result.is_req_success = False
            Logger().hwarn('HTTP_REQUEST.ProxyError.NoAvailableProxyIp')
            return None

    def preset_proxy_ip(self, proxy_pool):
        """
        预置代理ip，不会根据池子来走
        :return:
        """
        proxy_pool = 'proxy_pool_%s' % proxy_pool.lower()

        ip_info = getattr(self,proxy_pool)()
        Logger().hdebug('preset proxy ip %s' % str(ip_info))
        if ip_info:
            return ip_info
        else:
            return None

    def request(self, url, params=None, method='GET', timeout=None,
                data=None, json=None, headers=None,is_direct=False,proxy_pool=None, comment='', print_info=False,  verify=False, proxies=None,**kwargs):
        """

        :param is_direct: 是否直连
        :param params:
        :param method:
        :param timeout:
        :param data:
        :param json:
        :param headers:
        :param proxy_pool: 此处代理池设置优先大于 lock_proxy_pool
        :param comment:  在打印结果的时候显示备注
        :param print_info:  是否直接打印请求url和返回response[:1000]，在RUNMODE=TEST 无效
        :param kwargs:
        :return:
        """
        assert method is not None  # GET, POST
        timeout = timeout or self.timeout
        headers = headers or {}

        result = HttpResult()

        if not is_direct:
            if not proxy_pool and self.lock_proxy_pool:  # 当你设置了代理，代理锁才会生效，否则认为你采用直连
                proxy_pool = self.lock_proxy_pool
                headers["Connection"] = "close"
            TB_PROXY_POOL = proxy_pool
        else:
            pass
        backend_ip = None
        if str(method).upper() == "GET":
            req = requests.Request('GET', url, params=params, headers=headers)
        elif str(method).upper() == "POST":
            req = requests.Request('POST', url, params=params, data=data, json=json, headers=headers)
        else:
            raise Exception("Method: %s not support" % method)
        prepped = self.http_session.prepare_request(req)

        result.req_raw_url = prepped.url
        result.req_raw_data = prepped.body
        result.req_cookie = prepped.headers.get('Cookie', '')
        # 是否将url打印并展示备注
        if print_info == True:
            Logger().hinfo('%s req_url: %s' % (comment, prepped.url))
        retries = 0
        try:
            # retry for 3 times

            for _ in range(self.proxy_error_tries):  # 2019-01-22 by wxt  目前只有超时会进行重试，因为超时问题暂归结于代理
                retries += 1
                req_start_time = Time.timestamp_ms()
                result.response_headers = []
                response = None
                try:
                    if proxies:
                        proxy_url, backend_ip = proxies
                        kwargs["proxies"] = {'http': proxy_url, 'https': proxy_url}
                        Logger().hdebug('parameter proxies %s' % ( kwargs.get('proxies')))
                    elif self.current_proxy_ip:
                            proxy_url, backend_ip = self.current_proxy_ip
                            kwargs["proxies"] = {'http': proxy_url, 'https': proxy_url}
                            Logger().hdebug('proxy_pool  %s proxies %s' % (proxy_pool, kwargs.get('proxies')))
                    elif not is_direct and proxy_pool:

                        __ = self.get_proxy_ip(proxy_pool=proxy_pool, result=result)
                        if __:
                            proxy_url, backend_ip = __
                            kwargs["proxies"] = {'http': proxy_url, 'https': proxy_url}
                            Logger().hdebug('proxy_pool【%s】proxies %s url:%s' % (proxy_pool, kwargs.get('proxies'),url))
                        else:
                            raise ProxyError('No proxy ip')
                    response = self.http_session.send(prepped, timeout=timeout, verify=verify, **kwargs)
                    timeout_flag = False

                    result.exception = ''
                    result.is_req_timeout = False
                    result.is_req_success = True
                except requests.Timeout as e:
                    Logger().hwarn('HTTP_REQUEST.Timeout')
                    result.exception = str(e)
                    result.is_req_timeout = True
                    result.is_req_success = False

                    # # 将当前代理IP删掉，因为大部分原因都可能是代理IP超时引起的
                    # # Logger().hwarn(traceback.format_exc())
                    # if kwargs.get("proxies", ""):
                    #     self.block_proxy_ip(proxy_ip=kwargs["proxies"]['http'])
                    timeout_flag = True
                except requests.RequestException as e:
                    """
                    ('Connection aborted.', BadStatusLine("''",))
                    """
                    import traceback
                    Logger().serror(traceback.format_exc())
                    Logger().hinfo('HTTP_REQUEST.RequestException')
                    result.exception = str(e)
                    result.is_req_success = False
                    # Logger().herror(traceback.format_exc())
                    timeout_flag = True
                    # if kwargs.get("proxies", ""):
                    #     self.block_proxy_ip(proxy_ip=kwargs["proxies"]['http'], provider_channel=provider_channel)

                if response:
                    result.response_status_code = response.status_code
                    if response.history:
                        result.is_redirect = True
                        for rsp in response.history:
                            result.response_headers.append(json_obj.dumps(dict(rsp.headers)))
                    else:
                        result.is_redirect = False

                    if response.headers.get('Content-Type') and 'image' in response.headers.get('Content-Type'):
                        result.content_type = 'image'

                    result.content = response.content if response.content else ''
                    result.response_headers.append(json_obj.dumps(dict(response.headers)))
                    result.current_url = response.url

                if timeout_flag:
                    Logger().hdebug('timeout retry....')
                else:
                    break
            else:
                self.current_proxy_ip = None  # 结束当前预置代理IP
                raise Exception(result.content)

            self.current_proxy_ip = None  # 结束当前预置代理IP
            if response.content:
                result.is_req_success = True
            else:
                result.is_req_success = False


        except ProxyError as e:
            # 代理错误
            result.exception = str(e)
            result.is_req_success = False
            result.is_proxy_error = True
            Logger().hinfo('HTTP_REQUEST.ProxyError reason:%s' % e)

        except Exception as e:
            Logger().herror('HTTP_REQUEST.Exception')
            result.exception = str(e)
            result.is_req_success = False

        if backend_ip:
            result.proxy_backend_ip = backend_ip

        result.latency = Time.timestamp_ms() - req_start_time  # 只记录最后一次请求的延迟
        result.retries = retries

        # metrics

        TBG.tb_metrics.write(
            "HTTP.REQUEST",
            tags=dict(
                is_req_success=result.is_req_success,
                is_req_timeout=result.is_req_timeout,
                is_proxy_error=result.is_proxy_error,
                response_status_code=result.response_status_code,
                exception=result.exception,
                retries=result.retries,
                proxy_pool=proxy_pool
            ),
            fields=dict(
                total_latency=result.latency,
                count=1
            ))

        if print_info == True:
            Logger().hinfo('%s rsp_status: %s rsp_data: %s' % (comment, result.is_req_success, result.sub_content(1000)))

        if TBG.global_config['RUN_MODE'] == 'TEST' and TBG.global_config['ALLOW_PRINT_HTTP_INFO_IN_TEST']:
            # 如果是测试模式输出所有请求响应内容
            Logger().hinfo(result.to_log_json())

        if TBG.global_config['EXCEPTION_HTTP_LOG_OUTPUT']:
            # 是否输出异常记录点http请求日志
            Logger().http_log(http_result=result.to_log_json())
        self.last_http_result = result
        return result


if __name__ == '__main__':
    pass
