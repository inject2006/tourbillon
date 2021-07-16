#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gevent
import json
import datetime
import random
import string
from .base import ProvderAutoBase
from ..dao.internal import *
from ..utils.util import simple_encrypt, RoutingKey
from ..controller.captcha import CaptchaCracker
from app import TBG


class Csair(ProvderAutoBase):
    timeout = 50  # 请求超时时间
    provider = 'CZ_PROVIDER'  # 子类继承必须赋
    provider_channel = 'CZ_PROVIDER_WEB'  # 子类继承必须赋
    operation_product_type = '会员折扣'  # 运价类型：0: GDS公布运价 1:GDS私有运价 2:航司官网产品  3:廉价航司产品 4:特价产品
    operation_product_mode = 'A2B'
    pay_channel = 'ALIPAY'
    is_display = True
    no_flight_ttl = 3600 * 3 # 无航班缓存超时时间设定
    carrier_list = ['CZ']  # 供应商所包含的航司列表，如果包含多个并且无法确定，请不要填写，此处会关联执飞航线判断逻辑


    CACHE_PR_CONFIG = {
        1: {'cabin_expired_time': 3600 * 12, 'cabin_attenuation': 3,'fare_expired_time':86400 * 30},
        2: {'cabin_expired_time': 3600 * 3, 'cabin_attenuation': 2,'fare_expired_time':86400 * 20},
        3: {'cabin_expired_time': 60 * 60 * 1, 'cabin_attenuation': 1,'fare_expired_time':86400 * 10},
        4: {'cabin_expired_time': 60 * 40, 'cabin_attenuation': 1,'fare_expired_time':86400 * 5},
        5: {'cabin_expired_time': 60 * 30, 'cabin_attenuation': 0,'fare_expired_time':86400},

    }
    search_interval_time = 0.2

    def __init__(self):
        super(Csair, self).__init__()

    def _flight_search(self, http_session, search_info):
        """
        航班爬取模块，
        TODO :目前只考虑单程
        :return:
        """

        Logger().debug('search flight')

        url = 'https://b2c.csair.com/B2C40/query/jaxb/interDirect/query.ao'
        post_data = {
            'json': json.dumps({
                'depcity': search_info.from_airport,
                'arrcity': search_info.to_airport,
                'flightdate': search_info.from_date.replace('-', ''),
                'adultnum': search_info.adt_count,
                'childnum': search_info.chd_count if search_info.chd_count else 1,
                'infantnum': search_info.inf_count if search_info.inf_count else 1,
                'cabinorder': '0',
                'airline': '1',
                'flytype': '0',
                'international': '1',
                'action': '0',
                'segtype': '1',
                'cache': '0',
                'preUrl': '',
            })
        }

        result = http_session.request(url=url, method='POST', data=post_data, verify=False).to_json()
        if result.get('needverify') == 'true':
            raise FlightSearchException(err_code='HIGH_REQ_LIMIT')
        if not result.get('segment') or not result['segment'][0].get('dateflight'):
            Logger().warn('csair no flight')
            return search_info

        search_routes = result['segment'][0]['dateflight']
        for route in search_routes:
            for cabin in route['prices']:
                flight_routing = FlightRoutingInfo()
                flight_routing.product_type = 'DEFAULT'

                for index, seg in enumerate(route['flight']):
                    flight_segment = FlightSegmentInfo()
                    flight_segment.carrier = 'CZ'
                    flight_segment.dep_airport = seg['depport']
                    flight_segment.dep_time = datetime.datetime.strptime(
                        seg['deptime'], '%Y-%m-%dT%H:%M').strftime('%Y-%m-%d %H:%M:%S')

                    flight_segment.arr_airport = seg['arrport']
                    flight_segment.arr_time = datetime.datetime.strptime(
                        seg['arrtime'], '%Y-%m-%dT%H:%M').strftime('%Y-%m-%d %H:%M:%S')
                    # 经停
                    # flight_segment.stop_cities = route['stopcity']

                    flight_segment.flight_number = seg['flightNo']
                    flight_segment.dep_terminal = seg['depterm'] if not seg.get('depterm') == '--' else ''
                    flight_segment.arr_terminal = seg['arrTerm'] if not seg.get('arrTerm') == '--' else ''
                    flight_segment.cabin = cabin['adultcabins'][index]['name']
                    cabin_grade_map = {
                        'ECONOMY': 'Y',
                        'BUSINESS': 'C',
                        'PREMIUMECONOMY': 'S',
                        'FIRST': 'F'
                    }
                    flight_segment.cabin_grade = cabin_grade_map[cabin['adultcabins'][index]['type']]
                    flight_segment.cabin_count = int(seg['bookingclassavails'].split(':')[-1])
                    segment_duration = (datetime.datetime.strptime(seg['arrtime'], '%Y-%m-%dT%H:%M') -
                                        datetime.datetime.strptime(seg['deptime'], '%Y-%m-%dT%H:%M')).seconds
                    duration = int(segment_duration / 60)
                    flight_segment.duration = duration
                    flight_segment.routing_number = 1
                    flight_routing.from_segments.append(flight_segment)

                routing_key = RoutingKey.serialize(
                    from_airport=route['flight'][0]['depport'],
                    dep_time=datetime.datetime.strptime(route['flight'][0]['deptime'], '%Y-%m-%dT%H:%M'),
                    to_airport=route['flight'][-1]['arrport'],
                    arr_time=datetime.datetime.strptime(route['flight'][-1]['arrtime'], '%Y-%m-%dT%H:%M'),
                    flight_number='-'.join([f['flightNo'] for f in route['flight']]),
                    cabin='-'.join([c['name'] for c in cabin['adultcabins']]),
                    cabin_grade='-'.join([s.cabin_grade for s in flight_routing.from_segments]),
                    product='COMMON',
                    provider=self.provider,
                    adult_price=float(cabin['adultprice']),
                    adult_tax=float(cabin['adultyq']) + float(cabin['adultcn']) + float(cabin['adultxt']),
                    provider_channel=self.provider_channel,
                    child_price=float(cabin['childprice']),
                    child_tax=float(cabin['childyq']) + float(cabin['childcn']) + float(cabin['childxt']),
                    inf_price=float(cabin['infantprice']),
                    inf_tax=float(cabin['infantyq']) + float(cabin['infantcn']) + float(cabin['infantxt']),
                    search_from_airport=search_info.from_airport,
                    search_to_airport=search_info.to_airport,
                    from_date=search_info.from_date,
                    routing_range=search_info.routing_range,
                    trip_type=search_info.trip_type,
                    is_include_operation_carrier=0,
                    is_multi_segments=1 if len(cabin['adultcabins']) > 1 else 0
                )

                flight_routing.routing_key_detail = routing_key['plain']
                flight_routing.routing_key = routing_key['encrypted']

                flight_routing.adult_price = float(cabin['adultprice'])
                flight_routing.adult_tax = float(cabin['adultyq']) + float(cabin['adultcn']) + float(cabin['adultxt'])
                flight_routing.child_price = float(cabin['childprice'])
                flight_routing.child_tax = float(cabin['childyq']) + float(cabin['childcn']) + float(cabin['childxt'])
                search_info.assoc_search_routings.append(flight_routing)
        return search_info
