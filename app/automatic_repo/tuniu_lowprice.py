#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gevent
import json
import datetime
import random
import string
import hashlib
import base64
import StringIO
import gzip
from .base import ProvderAutoBase
from ..dao.internal import *
from ..utils.util import simple_encrypt, Random,RoutingKey, simple_decrypt
from ..controller.captcha import CaptchaCracker
from app import TBG
from Crypto.Cipher import AES
from pony.orm import select, db_session


class TuniuLowPrice(ProvderAutoBase):
    timeout = 50  # 请求超时时间
    provider = 'tuniu_lowprice'  # 子类继承必须赋
    provider_channel = 'tuniu_lowprice_web'  # 子类继承必须赋
    operation_product_type = '会员折扣'  # 运价类型：0: GDS公布运价 1:GDS私有运价 2:航司官网产品  3:廉价航司产品 4:特价产品
    operation_product_mode = 'A2B'
    pay_channel = 'ALIPAY'
    provider_token = '5e7ba8bddd7b9648'
    is_display = True
    assoc_ota_name = 'tuniu'
    is_include_cabin = False
    no_flight_ttl = 1800  # 无航班缓存超时时间设定


    CACHE_PR_CONFIG = {
        1: {'cabin_expired_time': 60 * 10, 'cabin_attenuation': 3,'fare_expired_time':86400 * 30},
        2: {'cabin_expired_time': 60 * 10, 'cabin_attenuation': 2,'fare_expired_time':86400 * 20},
        3: {'cabin_expired_time': 60 * 5, 'cabin_attenuation': 1,'fare_expired_time':86400 * 10},
        4: {'cabin_expired_time': 60 * 5, 'cabin_attenuation': 1,'fare_expired_time':86400 * 5},
        5: {'cabin_expired_time': 60 * 5, 'cabin_attenuation': 0,'fare_expired_time':86400},

    }
    search_interval_time = 0.3

    def __init__(self):
        super(TuniuLowPrice, self).__init__()

        self.account_list = [
            {'username': '66040', 'password': 'yiyou806'},
        ]

        if not TBG.redis_conn.redis_pool.llen('tuniu_lowprice_account_list') == len(self.account_list):
            TBG.redis_conn.redis_pool.expire('tuniu_lowprice_account_list', 0)
            for account in self.account_list:
                TBG.redis_conn.redis_pool.lpush('tuniu_lowprice_account_list', account)

    def _get_fix_account(self):

        account = TBG.redis_conn.redis_pool.rpoplpush('tuniu_lowprice_account_list', 'tuniu_lowprice_account_list')
        account = eval(account) if account else random.choice(self.account_list)
        return account

    def _login(self, http_session, ffp_account_info):
        """
        登陆模块
        :return: 登陆成功的httpResult 对象
        """

        post_data = {
            "r": '0.033587492345{}'.format(random.randint(100000, 999999)),
            "requestResourceFlag": 1,
            "loginName": ffp_account_info.username,
            "password": hashlib.md5(ffp_account_info.password).hexdigest(),
            "security": "",
            "deviceInfoFlag": True,
            "screenInfo": "{}60*{}40".format(random.randint(15, 25), random.randint(10, 15)),
            "browserInfo": "{}35*{}50".format(random.randint(13, 16), random.randint(9, 13))
        }
        post_data = base64.b64encode(json.dumps(post_data, separators=(',', ':')))
        url = 'https://www.tuniu.cn/restful/login/logon'
        cookies = http_session.get_cookies()
        if 'JSESSIONIDNB' not in cookies:
            http_session.update_cookie({'JSESSIONIDNB': '2894E5C0A9D1C8DDB83B6436779A13668aa8b2a1687a43be01696c01f80439bf'})
        result = http_session.request(url=url, method='POST', data=post_data, proxy_pool='A')
        result = json.loads(base64.b64decode(result.content))

        Logger().info("======== login result : {}".format(result))

        if result['success'] == True:
            jsession = result['data']['JSESSIONIDADMIT']
            http_session.update_cookie({'JSESSIONIDNB': jsession})
            return http_session
        else:
            raise LoginCritical('登陆失败')

    def _check_login(self, http_session, **kwargs):
        post_data = {
            "r": '0.41464579712{}'.format(random.randint(100000, 999999)),
        }

        url = 'https://www.tuniu.cn/restful/login/agency-info?{}'.format(
            base64.b64encode(json.dumps(post_data, separators=(',', ':'))))
        result = http_session.request(url=url, method='GET', proxy_pool='A')
        result = json.loads(base64.b64decode(result.content))
        Logger().info("============ check login result:{}".format(result))
        if result['success'] == True:
            return True
        else:
            return False

    def _flight_search(self, http_session, search_info):
        """
        航班爬取模块，
        TODO :目前只考虑单程
        :return:
        """

        Logger().debug('search flight')

        ffp = FFPAccountInfo()
        account = self._get_fix_account()
        ffp.username = account['username']
        ffp.password = account['password']
        http_session = self.login(http_session, ffp)
        time.sleep(1)

        if search_info.trip_type == 'RT':
            trip_type = '2'
        else:
            trip_type = '1'

        post_data = {
            "r": '0.3348078781{}'.format(random.randint(100000, 999999)),
            "flightType": trip_type,
            "departCity": search_info.from_airport,
            "destCity": search_info.to_airport,
            "addedTax": "1",
            "airlineCompany": "",
            "departureDate": search_info.from_date,
            "backDate": "",
            "cabinClass": "0",
            "adultCount": search_info.adt_count,
            "childCount": search_info.chd_count,
            "babyCount": search_info.inf_count,
            "channelId": 0,
            "channelCount": 0,
            "sessionId": int(time.time() * 1000),
            "currentTime": int(time.time() * 1000),
            "isFirst": True,
            "url": "/itp/nb/itppolicy/front/vendorFlightSearchNew",
            "type": "1",
            "sysFlag": "ITP",
            "method": "POST"
        }

        url = 'https://www.tuniu.cn/restful/common/api?{}'.format(
            base64.b64encode(json.dumps(post_data, separators=(',', ':'))))
        result = http_session.request(url=url, method='GET', proxy_pool='A')
        result = json.loads(base64.b64decode(result.content))
        Logger().debug("====== search result:{} ==".format(result))

        for times in xrange(10):
            if not result['data'].has_key('needQueryMore'):
                Logger().warn('tuniu lowprice no flight')
                return search_info

            elif result['data']['needQueryMore'] == 0:
                post_data['channelCount'] = result['data']['channelCount']
                post_data['sessionId'] = result['data']['sessionId']
                post_data['queryId'] = result['data']['queryId']
                Logger().info("========= post data: {} ===".format(post_data))

                url = 'https://www.tuniu.cn/restful/common/api?{}'.format(
                    base64.b64encode(json.dumps(post_data, separators=(',', ':'))))
                result = http_session.request(url=url, method='GET', proxy_pool='A')

                Logger().debug("====== search result:{} ==".format(result.content))
                result = json.loads(base64.b64decode(result.content))

            else:
                break
            time.sleep(1)

        if not result['data']['flightsList']:
            Logger().warn('tuniu lowprice no flight')
            return search_info

        routing_list = result['data']['flightsList']

        if result['data']['flightCount'] > 20:
            post_data = {
                "r": '0.0836535103{}'.format(random.randint(100000, 999999)),
                "limit": 400,
                "isAddedTax": 1,
                "queryId": result['data']['queryId'],
                "start": "20",
                "url": "/itp/nb/itppolicy/front/flightPageRequest",
                "type": "1",
                "sysFlag": "ITP",
                "method": "GET"
            }

            url = 'https://www.tuniu.cn/restful/common/api?{}'.format(
                base64.b64encode(json.dumps(post_data, separators=(',', ':'))))
            result = http_session.request(url=url, method='GET', proxy_pool='A')
            result = json.loads(base64.b64decode(result.content))
            Logger().debug("====== search result:{} ==".format(result))
            routing_list.extend(result['data']['flightsList'])

        for routing in routing_list:
            flight_routing = FlightRoutingInfo()
            flight_routing.product_type = 'DEFAULT'
            routing_number = 1
            from_seg_list = routing['calcPriceParamMap'].get('go', [])
            ret_seg_list = routing['calcPriceParamMap'].get('back', [])
            for index, seg in enumerate(from_seg_list):
                flight_segment = FlightSegmentInfo()
                flight_segment.carrier = seg['airlineIataCode']
                dep_time = datetime.datetime.strptime(seg['departureDate'] + seg['departureTime'],
                                                      '%Y-%m-%d%H:%M').strftime('%Y-%m-%d %H:%M:%S')
                arr_time = datetime.datetime.strptime(seg['arrivalDate'] + seg['arrivalTime'],
                                                      '%Y-%m-%d%H:%M').strftime('%Y-%m-%d %H:%M:%S')
                flight_segment.dep_airport = seg['dPort']
                flight_segment.dep_time = dep_time
                flight_segment.arr_airport = seg['aPort']
                flight_segment.arr_time = arr_time
                flight_segment.flight_number = seg['flightNo']
                flight_segment.dep_terminal = ''
                flight_segment.arr_terminal = ''
                flight_segment.cabin = seg['cabinClass']
                flight_segment.cabin_grade = 'Y'
                flight_segment.cabin_count = 9
                segment_duration = (datetime.datetime.strptime(arr_time, '%Y-%m-%d %H:%M:%S') -
                                    datetime.datetime.strptime(dep_time, '%Y-%m-%d %H:%M:%S')).total_seconds()
                flight_segment.duration = int(segment_duration / 60)
                flight_segment.routing_number = routing_number
                routing_number += 1
                flight_routing.from_segments.append(flight_segment)

            for index, seg in enumerate(ret_seg_list):
                flight_segment = FlightSegmentInfo()
                flight_segment.carrier = seg['airlineIataCode']
                dep_time = datetime.datetime.strptime(seg['departureDate'] + seg['departureTime'],
                                                      '%Y-%m-%d%H:%M').strftime('%Y-%m-%d %H:%M:%S')
                arr_time = datetime.datetime.strptime(seg['arrivalDate'] + seg['arrivalTime'],
                                                      '%Y-%m-%d%H:%M').strftime('%Y-%m-%d %H:%M:%S')
                flight_segment.dep_airport = seg['dPort']
                flight_segment.dep_time = dep_time
                flight_segment.arr_airport = seg['aPort']
                flight_segment.arr_time = arr_time
                flight_segment.flight_number = seg['flightNo']
                flight_segment.dep_terminal = ''
                flight_segment.arr_terminal = ''
                flight_segment.cabin = seg['cabinClass']
                flight_segment.cabin_grade = 'Y'
                flight_segment.cabin_count = 9
                segment_duration = (datetime.datetime.strptime(arr_time, '%Y-%m-%d %H:%M:%S') -
                                    datetime.datetime.strptime(dep_time, '%Y-%m-%d %H:%M:%S')).total_seconds()
                flight_segment.duration = int(segment_duration / 60)
                flight_segment.routing_number = routing_number
                routing_number += 1
                flight_routing.ret_segments.append(flight_segment)

            flight_routing.adult_price = float(routing['adultOrgPrice'])
            flight_routing.adult_tax = float(routing['adultTax'])
            flight_routing.child_price = float(routing['childOrgPrice'])
            flight_routing.child_tax = float(routing['childTax'])

            flight_number_result = '-'.join([s.flight_number for s in flight_routing.from_segments])
            cabin_result = '-'.join([s.cabin for s in flight_routing.from_segments])
            cabin_grade_result = '-'.join([s.cabin_grade for s in flight_routing.from_segments])
            dep_time_result = datetime.datetime.strptime(flight_routing.from_segments[0].dep_time,
                                                                '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M')
            arr_time_result = datetime.datetime.strptime(flight_routing.from_segments[-1].arr_time,
                                                                '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M')

            if search_info.trip_type == 'RT':
                flight_number_result = '{},{}'.format(flight_number_result, '-'.join(
                    [s.flight_number for s in flight_routing.ret_segments]))
                cabin_result = '{},{}'.format(cabin_result, '-'.join([s.cabin for s in flight_routing.ret_segments]))
                cabin_grade_result = '{},{}'.format(cabin_grade_result, '-'.join(
                    [s.cabin_grade for s in flight_routing.ret_segments]))
                dep_time_result = '{},{}'.format(dep_time_result, datetime.datetime.strptime(
                    flight_routing.ret_segments[0].dep_time, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'))
                arr_time_result = '{},{}'.format(arr_time_result, datetime.datetime.strptime(
                    flight_routing.ret_segments[-1].arr_time, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'))


            rk_info = RoutingKey.serialize(from_airport=flight_routing.from_segments[0].dep_airport,
                                           dep_time=dep_time_result,
                                           to_airport=flight_routing.from_segments[-1].arr_airport,
                                           arr_time=arr_time_result,
                                           flight_number=flight_number_result,
                                           cabin=cabin_result,
                                           cabin_grade=cabin_grade_result,
                                           product='COMMON',
                                           adult_price=flight_routing.adult_price, adult_tax=flight_routing.adult_tax,
                                           provider_channel=self.provider_channel,
                                           child_price=flight_routing.child_price, child_tax=flight_routing.child_tax,
                                           inf_price=0.0,
                                           inf_tax=0.0,
                                           provider=self.provider,
                                           search_from_airport=search_info.from_airport,
                                           search_to_airport=search_info.to_airport,
                                           from_date=search_info.from_date,
                                           trip_type=search_info.trip_type,
                                           routing_range=search_info.routing_range,
                                           is_include_operation_carrier=0,
                                           is_multi_segments=1 if len(flight_routing.from_segments) > 1 else 0
                                           )

            flight_routing.routing_key_detail = rk_info['plain']
            flight_routing.routing_key = rk_info['encrypted']
            search_info.assoc_search_routings.append(flight_routing)

        return search_info
