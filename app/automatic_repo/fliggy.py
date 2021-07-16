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
import re
from .base import ProvderAutoBase
from ..dao.internal import *
from ..utils.util import simple_encrypt, Random,RoutingKey, simple_decrypt
from ..dao.iata_code import CN_CITY_TO_AIRPORT
from ..controller.captcha import CaptchaCracker
from app import TBG
from Crypto.Cipher import AES
from pony.orm import select, db_session
from lxml import etree


class Fliggy(ProvderAutoBase):
    timeout = 50  # 请求超时时间
    provider = 'fliggy'  # 子类继承必须赋
    provider_channel = 'fliggy_web'  # 子类继承必须赋
    operation_product_type = '会员折扣'  # 运价类型：0: GDS公布运价 1:GDS私有运价 2:航司官网产品  3:廉价航司产品 4:特价产品
    operation_product_mode = 'A2B'
    pay_channel = 'ALIPAY'
    provider_token = '5e7ba8bddd7b9648'
    is_display = True
    trip_type_list = ['OW'] #  TODO 暂时只支持单程
    routing_range_list = ['I2O','O2O','O2I']  # 国内不支持
    no_flight_ttl = 3600 * 3 # 无航班缓存超时时间设定
    carrier_list = []  # 供应商所包含的航司列表，如果包含多个并且无法确定，请不要填写，此处会关联执飞航线判断逻辑


    CACHE_PR_CONFIG = {
        1: {'cabin_expired_time': 60 * 10, 'cabin_attenuation': 3,'fare_expired_time':86400 * 30},
        2: {'cabin_expired_time': 60 * 10, 'cabin_attenuation': 2,'fare_expired_time':86400 * 20},
        3: {'cabin_expired_time': 60 * 5, 'cabin_attenuation': 1,'fare_expired_time':86400 * 10},
        4: {'cabin_expired_time': 60 * 5, 'cabin_attenuation': 1,'fare_expired_time':86400 * 5},
        5: {'cabin_expired_time': 60 * 5, 'cabin_attenuation': 0,'fare_expired_time':86400},

    }
    search_interval_time = 0.2

    def __init__(self):
        super(Fliggy, self).__init__()

    def _flight_search(self, http_session, search_info):

        headers = {
            'Referer':'https://sijipiao.fliggy.com/ie/flight_search_result.htm?searchBy=1281&spm=181.7091613.a1z67.1002&_input_charset=utf-8&tripType=0&depCityName=%E6%99%AE%E5%90%89%E5%B2%9B&depCity=HKT&depDate=2019-05-07&arrCityName=%E4%B8%8A%E6%B5%B7&arrCity=SHA&arrDate='
        }

        fliggy_session = TBG.redis_conn.redis_pool.get('fliggy_session')
        if fliggy_session:
            fliggy_session = json.loads(fliggy_session)
            http_session.update_cookie(fliggy_session)
            http_session.update_headers(headers)
            is_search_chd = 0
            if search_info.chd_count:
                is_search_chd = 1
            # from_airport = 'BKK'
            # to_airport = 'SHA'
            # from_date = '2019-05-30'
            url = "https://sijipiao.fliggy.com/ie/flight_search_result_poller.do"
            params = {
                '_ksTS': '1556422549733_753',
                'callback': 'jsonp754',
                'supportMultiTrip': 'true',
                'searchBy': '1281',
                'childPassengerNum': is_search_chd,
                'infantPassengerNum': '0',
                'searchJourney': '[{{"depCityCode":"{from_airport}","arrCityCode":"{to_airport}","depCityName":"%E6%99%AE%E5%90%89%E5%B2%9B","arrCityName":"%E4%B8%8A%E6%B5%B7","depDate":"{from_date}","selectedFlights":[]}}]'.format(
                    from_airport=search_info.from_airport, to_airport=search_info.to_airport, from_date=search_info.from_date),
                'tripType': '0', # 0 单程 1 多程
                'searchCabinType': '0',
                'agentId': '-1',
                'controller': '1',
                'searchMode': '0',
                'b2g': '0',
                'formNo': '-1'

            }
            result = http_session.request(url=url, method='GET', params=params,proxy_pool='E')

            json_data = re.findall(r'^\w+\((.*)\)$', result.content)[0]
            if "https://fourier.alibaba.com" in json_data:
                # 高频
                raise FlightSearchException(err_code='HIGH_REQ_LIMIT')
            elif "https://login.taobao.com/member/login.jhtml" in json_data:
                raise FlightSearchException('Login session expired ，need relogin')
            else:
                json_data = json.loads(json_data)
                if json_data.get('success', 0):
                    # 成功
                    routings = json_data.get('data', {}).get('flightItems', [])
                    for routing in routings:
                        flight_routing = FlightRoutingInfo()
                        flight_routing.product_type = 'DEFAULT'
                        routing_number = 1
                        is_include_operation_carrier = 0
                        flight_info =routing['flightInfo'][0]
                        for seg in flight_info['flightSegments']:
                            flight_segment = FlightSegmentInfo()
                            flight_segment.carrier = seg['marketingAirlineCode']
                            if seg.get('codeShare'):
                                is_include_operation_carrier = 1
                            dep_time = seg['depTimeStr']
                            arr_time = seg['arrTimeStr']
                            flight_segment.dep_airport = seg['depAirportCode']
                            flight_segment.dep_time = dep_time
                            flight_segment.arr_airport = seg['arrAirportCode']
                            flight_segment.arr_time = arr_time
                            flight_segment.flight_number = seg['marketingFlightNo']
                            flight_segment.dep_terminal = seg.get('depTerm','')
                            flight_segment.arr_terminal = seg.get('arrTerm','')
                            stop_cities = CN_CITY_TO_AIRPORT.get(seg['stopCityName'], '')
                            if stop_cities:
                                flight_segment.stop_cities = stop_cities
                            flight_segment.cabin = 'N/A'
                            flight_segment.cabin_grade = 'Y'
                            flight_segment.cabin_count = routing['quantity']
                            flight_segment.duration = seg['duration']
                            flight_segment.routing_number = routing_number
                            routing_number += 1
                            flight_routing.from_segments.append(flight_segment)

                        flight_routing.adult_price = float(routing['adultPrice'] / 100)
                        flight_routing.adult_tax = float(routing['adultTax'] / 100)
                        if routing.get('childPrice', 0):
                            flight_routing.child_price = float(routing['childPrice'] / 100)

                        else:
                            flight_routing.child_price = flight_routing.adult_price

                        if routing.get('childTax', 0) :
                            flight_routing.child_tax = float(routing['childTax'] / 100)
                        else:
                            flight_routing.child_tax = flight_routing.adult_tax

                        flight_number_result = '-'.join([s.flight_number for s in flight_routing.from_segments])
                        cabin_result = '-'.join([s.cabin for s in flight_routing.from_segments])
                        cabin_grade_result = '-'.join([s.cabin_grade for s in flight_routing.from_segments])
                        dep_time_result = datetime.datetime.strptime(flight_info['depTimeStr'],
                                                                     '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M')
                        arr_time_result = datetime.datetime.strptime(flight_info['arrTimeStr'],
                                                                     '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M')

                        rk_info = RoutingKey.serialize(from_airport=flight_routing.from_segments[0].dep_airport,
                                                       dep_time=dep_time_result,
                                                       to_airport=flight_routing.from_segments[-1].arr_airport,
                                                       arr_time=arr_time_result,
                                                       flight_number=flight_number_result,
                                                       cabin=cabin_result,
                                                       cabin_grade=cabin_grade_result,
                                                       product='COMMON',
                                                       adult_price=flight_routing.adult_price,
                                                       adult_tax=flight_routing.adult_tax,
                                                       provider_channel=self.provider_channel,
                                                       child_price=flight_routing.child_price,
                                                       child_tax=flight_routing.child_tax,
                                                       inf_price=0.0,
                                                       inf_tax=0.0,
                                                       provider=self.provider,
                                                       search_from_airport=search_info.from_airport,
                                                       search_to_airport=search_info.to_airport,
                                                       from_date=search_info.from_date,
                                                       ret_date=search_info.ret_date,
                                                       trip_type=search_info.trip_type,
                                                       routing_range=search_info.routing_range,
                                                       is_include_operation_carrier=is_include_operation_carrier,
                                                       is_multi_segments=1 if len(flight_routing.from_segments) > 1 or flight_routing.ret_segments else 0
                                                       )

                        flight_routing.routing_key_detail = rk_info['plain']
                        flight_routing.routing_key = rk_info['encrypted']
                        search_info.assoc_search_routings.append(flight_routing)

                else:
                    msg = json_data.get('msg', 'Unknown error')
                    raise FlightSearchException(msg)
        else:
            raise FlightSearchCritical(err_code='no fliggy session')
