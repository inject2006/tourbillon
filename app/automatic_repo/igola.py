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
from collections import OrderedDict
from ..dao.internal import *
from ..utils.util import simple_encrypt, Random,RoutingKey, simple_decrypt
from ..controller.captcha import CaptchaCracker
from app import TBG
from ..controller.http_request import HttpRequest
from Crypto.Cipher import AES
from pony.orm import select, db_session
from ..dao.iata_code import BUDGET_AIRLINE_CODE

class Igola(ProvderAutoBase):
    timeout = 50  # 请求超时时间
    provider = 'igola_provider'  # 子类继承必须赋
    provider_channel = 'igola_provider_agent'  # 子类继承必须赋
    operation_product_type = '会员折扣'  # 运价类型：0: GDS公布运价 1:GDS私有运价 2:航司官网产品  3:廉价航司产品 4:特价产品
    operation_product_mode = 'A2B'
    pay_channel = 'ALIPAY'
    provider_token = '40bd2f72c2579b34'
    is_display = True
    verify_realtime_search_count = 1
    is_order_directly = True
    trip_type_list = ['OW', 'RT']
    no_flight_ttl = 1800  # 无航班缓存超时时间设定


    CACHE_PR_CONFIG = {
        1: {'cabin_expired_time': 60 * 30, 'cabin_attenuation': 3, 'fare_expired_time': 86400 * 30},
        2: {'cabin_expired_time': 60 * 30, 'cabin_attenuation': 2, 'fare_expired_time': 86400 * 20},
        3: {'cabin_expired_time': 60 * 20, 'cabin_attenuation': 1, 'fare_expired_time': 86400 * 10},
        4: {'cabin_expired_time': 60 * 20, 'cabin_attenuation': 1, 'fare_expired_time': 86400 * 5},
        5: {'cabin_expired_time': 60 * 20, 'cabin_attenuation': 0, 'fare_expired_time': 86400},

    }

    search_interval_time = 0

    def __init__(self):
        super(Igola, self).__init__()

        self.verify_tries = 3
        # self.partner_id = 'yiyoulvyouuat'  # 测试
        self.partner_id = 'yiyoutravel'  # 生产
        # self.appsecurity = 'c266ad7e-1d93-491d-a341-2c0b491461a9'  # 测试
        self.appsecurity = 'bad90891-8a5e-40f3-bd89-bcdb960be61e'  # 生产
        # self.app_id = 'yiyoulvyouuat'      # 测试
        self.app_id = 'yiyoutravel'  # 生产
        # self.base_url = 'https://uatapib2b.igola.com'   # 测试
        self.base_url = 'https://apib2b.igola.com'  # 生产

    def _flight_search(self, http_session, search_info):
        """
        航班爬取模块，
        TODO :目前只考虑单程
        :return:
        """

        Logger().debug('search flight')

        post_data = {
            "adultNumber": search_info.adt_count,
            "cabinClass": "Economy",
            'childNumber': search_info.chd_count if search_info.chd_count else 1,
            "currency": "CNY",
            'departDate': search_info.from_date.replace('-', ''),
            'departPlace': search_info.from_airport,
            'destination': search_info.to_airport,
            "lang": "ZH",
            "pageIndex": 0,
            "pageSize": 300,
            'partnerId': self.partner_id,
        }

        if search_info.trip_type == 'RT':
            # from_flight_item = OrderedDict()
            # from_flight_item['departDate'] = search_info.from_date.replace('-', '')
            # from_flight_item['departPlace'] = search_info.from_airport
            # from_flight_item['destination'] = search_info.to_airport
            # to_flight_item = OrderedDict()
            # to_flight_item['departDate'] = search_info.ret_date.replace('-', '')
            # to_flight_item['departPlace'] = search_info.to_airport
            # to_flight_item['destination'] = search_info.from_airport

            post_data.update({
                'returnDate': search_info.ret_date.replace('-', ''),
                'childNumber': search_info.chd_count
            })

        post_data = OrderedDict(sorted(post_data.items(), key=lambda x: x[0]))
        post_data = json.dumps(post_data, separators=(',', ':'))
        Logger().info("========= post data: {} ===".format(post_data))
        token = hashlib.md5(post_data + self.appsecurity).hexdigest()
        url = '{}/flight/sync-polling'.format(self.base_url)
        headers = {'Content-Type': 'application/json', 'token': token, 'appid': self.app_id}
        result = http_session.request(url=url, data=post_data, method='POST', headers=headers, is_direct=True).to_json()
        Logger().debug("====== search result:{} ==".format(result))

        if not result.get('resultCode') == 200:
            Logger().error("igola search error  code: {}".format(result.get('resultCode')))
            raise FlightSearchException('igola search error')

        routing_list = result['result']
        if not routing_list:
            Logger().warn('igola provider no flight')
            return search_info

        origin_routing_list = []
        for routing in routing_list:
            seg_list = routing['flightDetails'][0]['segments']
            flight_routing = FlightRoutingInfo()
            flight_routing.product_type = 'DEFAULT'
            routing_number = 1
            is_include_operation_carrier = 0
            # from segments
            for seg in seg_list:
                flight_segment = FlightSegmentInfo()
                flight_segment.carrier = seg['airline']
                if seg.get('codeShare') == 'Y':
                    is_include_operation_carrier = 1
                dep_time = '{}:00'.format(seg['org']['time'])
                arr_time = '{}:00'.format(seg['dst']['time'])
                flight_segment.dep_airport = seg['org']['code']
                flight_segment.dep_time = dep_time
                flight_segment.arr_airport = seg['dst']['code']
                flight_segment.arr_time = arr_time
                if seg.get('stopUnits'):
                    flight_segment.stop_cities = '/'.join(st['cityCode'] for st in seg['stopUnits'])
                    flight_segment.stop_airports = '/'.join(st['airport'] for st in seg['stopUnits'])
                flight_segment.flight_number = seg['flightNo']
                flight_segment.dep_terminal = seg['orgTerminal'] if seg.get('orgTerminal') else ''
                flight_segment.arr_terminal = seg['dstTerminal'] if seg.get('dstTerminal') else ''
                cabin_grade_mapping = {
                    'Economy': 'Y',
                    'PremiumEconomy': 'Y',
                    'Business': 'C',
                    'First': 'F'
                }
                # FIXME 有些航班拿不到仓位
                if flight_segment.carrier in BUDGET_AIRLINE_CODE:
                    flight_segment.cabin = seg['cabinGroup'] if seg['cabinGroup'] else 'Y'
                else:
                    flight_segment.cabin = seg['cabinGroup'] if seg['cabinGroup'] else 'N/A'
                flight_segment.cabin_grade = cabin_grade_mapping[routing['cabinClass']]
                flight_segment.cabin_count = int(routing['seats']) if routing.get('seats') else 9
                flight_segment.duration = int(seg['durationHourMinute'].split('h')[0]) * 60 + \
                                          int(seg['durationHourMinute'].split('h')[1].split('m')[0])
                flight_segment.routing_number = routing_number
                routing_number += 1
                flight_routing.from_segments.append(flight_segment)

            # to segments
            if len(routing['flightDetails']) > 1:
                ret_seg_list = routing['flightDetails'][1]['segments']
                for seg in ret_seg_list:
                    flight_segment = FlightSegmentInfo()
                    flight_segment.carrier = seg['airline']
                    if seg.get('codeShare') == 'Y':
                        is_include_operation_carrier = 1
                    dep_time = '{}:00'.format(seg['org']['time'])
                    arr_time = '{}:00'.format(seg['dst']['time'])
                    flight_segment.dep_airport = seg['org']['code']
                    flight_segment.dep_time = dep_time
                    flight_segment.arr_airport = seg['dst']['code']
                    flight_segment.arr_time = arr_time
                    if seg.get('stopUnits'):
                        flight_segment.stop_cities = '/'.join(st['cityCode'] for st in seg['stopUnits'])
                        flight_segment.stop_airports = '/'.join(st['airport'] for st in seg['stopUnits'])
                    flight_segment.flight_number = seg['flightNo']
                    flight_segment.dep_terminal = seg['orgTerminal'] if seg.get('orgTerminal') else ''
                    flight_segment.arr_terminal = seg['dstTerminal'] if seg.get('dstTerminal') else ''
                    cabin_grade_mapping = {
                        'Economy': 'Y',
                        'PremiumEconomy': 'Y',
                        'Business': 'C',
                        'First': 'F'
                    }
                    # FIXME 有些航班拿不到仓位
                    if flight_segment.carrier in BUDGET_AIRLINE_CODE:
                        flight_segment.cabin = seg['cabinGroup'] if seg['cabinGroup'] else 'Y'
                    else:
                        flight_segment.cabin = seg['cabinGroup'] if seg['cabinGroup'] else 'N/A'
                    flight_segment.cabin_grade = cabin_grade_mapping[routing['cabinClass']]
                    flight_segment.cabin_count = int(routing['seats']) if routing.get('seats') else 9
                    flight_segment.duration = int(seg['durationHourMinute'].split('h')[0]) * 60 + \
                                              int(seg['durationHourMinute'].split('h')[1].split('m')[0])
                    flight_segment.routing_number = routing_number
                    routing_number += 1
                    flight_routing.ret_segments.append(flight_segment)

            # 补充舱位和舱等
            flight_routing.reference_cabin = flight_routing.from_segments[0].cabin
            flight_routing.reference_cabin_grade = flight_routing.from_segments[0].cabin_grade
            flight_routing.adult_price = round(routing['costPrice'], 1)
            flight_routing.adult_tax = round(routing['tax'], 1)
            flight_routing.child_price = round(routing['childCostPrice'] if routing.get('childCostPrice') else routing['costPrice'], 1)
            flight_routing.child_tax = round(routing['childTax'] if routing.get('childTax') else routing['tax'], 1)

            rk_dep_time = datetime.datetime.strptime(flight_routing.from_segments[0].dep_time,
                                                                               '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M')
            rk_arr_time = datetime.datetime.strptime(flight_routing.from_segments[-1].arr_time,
                                                                               '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M')
            rk_flight_number = '-'.join([s.flight_number for s in flight_routing.from_segments])
            rk_cabin = '-'.join([s.cabin for s in flight_routing.from_segments])
            rk_cabin_grade = '-'.join([s.cabin_grade for s in flight_routing.from_segments])

            if len(routing['flightDetails']) > 1:
                rk_dep_time = '{},{}'.format(rk_dep_time, datetime.datetime.strptime(
                    flight_routing.ret_segments[0].dep_time, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'))
                rk_arr_time = '{},{}'.format(rk_arr_time, datetime.datetime.strptime(
                    flight_routing.ret_segments[-1].arr_time, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'))
                rk_flight_number = '{},{}'.format(rk_flight_number, '-'.join(
                    [s.flight_number for s in flight_routing.ret_segments]))

                rk_cabin = '{},{}'.format(rk_cabin, '-'.join([s.cabin for s in flight_routing.ret_segments]))
                rk_cabin_grade = '{},{}'.format(rk_cabin_grade,
                                                '-'.join([s.cabin_grade for s in flight_routing.ret_segments]))

            rk_info = RoutingKey.serialize(from_airport=flight_routing.from_segments[0].dep_airport,
                                           dep_time=rk_dep_time,
                                           to_airport=flight_routing.from_segments[-1].arr_airport,
                                           arr_time=rk_arr_time,
                                           flight_number=rk_flight_number,
                                           cabin=rk_cabin,
                                           cabin_grade=rk_cabin_grade,
                                           product='COMMON',
                                           adult_price=flight_routing.adult_price, adult_tax=flight_routing.adult_tax,
                                           provider_channel=self.provider_channel,
                                           child_price=flight_routing.child_price, child_tax=flight_routing.child_tax,
                                           inf_price=flight_routing.child_price,
                                           inf_tax=flight_routing.child_tax,
                                           provider=self.provider,
                                           search_from_airport=search_info.from_airport,
                                           search_to_airport=search_info.to_airport,
                                           from_date=search_info.from_date,
                                           ret_date=search_info.ret_date,
                                           routing_range=search_info.routing_range,
                                           trip_type=search_info.trip_type,
                                           is_include_operation_carrier=is_include_operation_carrier,
                                           is_multi_segments=1 if len(flight_routing.from_segments) > 1 else 0
                                           )
            flight_routing.routing_key_detail = rk_info['plain']
            flight_routing.routing_key = rk_info['encrypted']
            search_info.assoc_search_routings.append(flight_routing)
            origin_routing_list.append({
                'routing_key': flight_routing.routing_key,
                'flight_id': routing['flightId'],
                'routing_info': flight_routing
            })

        origin_data_key = 'provider_search_origin_routings|{}|{}|{}|{}|{}|{}|{}|{}'.format(
            search_info.from_airport, search_info.to_airport, search_info.from_date, '', '1',
            search_info.adt_count, search_info.chd_count, self.provider_channel
        )
        TBG.redis_conn.redis_pool.set(origin_data_key, json.dumps(origin_routing_list), 25 * 60)

        return search_info

    def _verify_get_session(self, http_session, search_info):

        # 拿出缓存的搜索结果
        origin_routing_data = []
        origin_data_key = 'provider_search_origin_routings|{}|{}|{}|{}|{}|{}|{}|{}'.format(
            search_info.from_airport, search_info.to_airport, search_info.from_date, '', '1',
            search_info.adt_count, search_info.chd_count, self.provider_channel
        )
        no_origin_routing = True
        try:
            origin_routing_data = json.loads(TBG.redis_conn.redis_pool.get(origin_data_key))
            no_origin_routing = False
        except:
            pass
        if no_origin_routing:
            # 如果没有缓存搜索结果，再次搜索
            Logger().info('===== have no origin routings. search_key:{}'.format(origin_data_key))
            self.flight_search(http_session, search_info, cache_mode='REALTIME')
            try:
                origin_routing_data = json.loads(TBG.redis_conn.redis_pool.get(origin_data_key))
            except:
                raise ProviderVerifyFail('NO_ORIGIN_ROUTING')

        # 从搜索结果中选出验价的产品
        routing_info = {}
        if search_info.verify_routing_key:
            verify_un_key = RoutingKey.trans_cp_key(simple_decrypt(search_info.verify_routing_key))
        else:
            verify_un_key = RoutingKey.trans_cp_key(simple_decrypt(search_info.routing.routing_key))
        for o in origin_routing_data:
            try:
                search_un_key = RoutingKey.trans_cp_key(simple_decrypt(o['routing_key']))
                if search_un_key == verify_un_key:
                    routing_info = o
                    break
            except:
                pass
        if not routing_info:
            raise ProviderVerifyFail('NO_VERIFY_ROUTING')

        return routing_info

    def _verify(self, http_session, search_info):

        origin_routing_info = self._verify_get_session(http_session, search_info)

        post_data = {
            "partnerId": self.partner_id,
            "flightId": origin_routing_info['flight_id'],
            "lang": "ZH",
            "currency": "CNY",
            "adultCount": search_info.adt_count,
            "childCount": search_info.chd_count,
        }

        post_data = OrderedDict(sorted(post_data.items(), key=lambda x: x[0]))
        post_data = json.dumps(post_data, separators=(',', ':'))
        Logger().info("========= post data: {} ===".format(post_data))
        token = hashlib.md5(post_data + self.appsecurity).hexdigest()
        url = '{}/flight/verify-price'.format(self.base_url)
        headers = {'Content-Type': 'application/json', 'token': token, 'appid': self.app_id}
        result = http_session.request(url=url, data=post_data, method='POST', headers=headers, is_direct=True).to_json()
        Logger().info("====== verify result:{} ==".format(json.dumps(result)))

        if result.get('resultCode') == 433:
            raise ProviderVerifyFail('cabin count limit !')
        if not result.get('resultCode') == 200:
            raise ProviderVerifyFail('verify failed!')

        verify_result_key = 'provider_verify_result|{}|{}|{}|{}|{}|{}|{}|{}'.format(
            search_info.from_airport, search_info.to_airport, search_info.from_date, '', '1',
            search_info.adt_count, search_info.chd_count, self.provider_channel
        )
        TBG.redis_conn.redis_pool.lpush(verify_result_key, json.dumps({
            'data': {
                'routing_key': origin_routing_info['routing_key'],
                'verify_result': result['result'],
            },
            'create_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }))

        flight_routing = FlightRoutingInfo()
        flight_routing.product_type = 'DEFAULT'
        for seg in origin_routing_info['routing_info']['from_segments']:

            flight_segment = FlightSegmentInfo()
            flight_segment.carrier = seg['carrier']
            flight_segment.dep_airport = seg['dep_airport']
            flight_segment.dep_time = seg['dep_time']
            flight_segment.arr_airport = seg['arr_airport']
            flight_segment.arr_time = seg['arr_time']
            flight_segment.stop_airports = seg['stop_airports']
            flight_segment.flight_number = seg['flight_number']
            flight_segment.dep_terminal = seg['dep_terminal']
            flight_segment.arr_terminal = seg['arr_terminal']
            flight_segment.cabin = seg['cabin']
            flight_segment.cabin_grade = seg['cabin_grade']
            flight_segment.cabin_count = result['result']['remainSeat']
            flight_segment.duration = seg['duration']
            flight_segment.routing_number = seg['routing_number']
            flight_routing.from_segments.append(flight_segment)

        if origin_routing_info['routing_info'].get('ret_segments'):
            for seg in origin_routing_info['routing_info']['ret_segments']:
                flight_segment = FlightSegmentInfo()
                flight_segment.carrier = seg['carrier']
                flight_segment.dep_airport = seg['dep_airport']
                flight_segment.dep_time = seg['dep_time']
                flight_segment.arr_airport = seg['arr_airport']
                flight_segment.arr_time = seg['arr_time']
                flight_segment.stop_airports = seg['stop_airports']
                flight_segment.flight_number = seg['flight_number']
                flight_segment.dep_terminal = seg['dep_terminal']
                flight_segment.arr_terminal = seg['arr_terminal']
                flight_segment.cabin = seg['cabin']
                flight_segment.cabin_grade = seg['cabin_grade']
                flight_segment.cabin_count = result['result']['remainSeat']
                flight_segment.duration = seg['duration']
                flight_segment.routing_number = seg['routing_number']
                flight_routing.ret_segments.append(flight_segment)

        # 补充舱位和舱等
        verify_adult_price = round(result['result']['costPrice'], 1)
        verify_adult_tax = round(result['result']['tax'], 1)
        verify_child_price = round(result['result']['costChildPrice'] if result['result'].get('costChildPrice') else result['result']['costPrice'], 1)
        verify_child_tax = round(result['result']['childTax'] if result['result'].get('childTax') else result['result']['tax'], 1)
        verify_inf_price = round(result['result']['costChildPrice'] if result['result'].get('costChildPrice') else result['result']['costPrice'], 1)
        verify_inf_tax = round(result['result']['childTax'] if result['result'].get('childTax') else result['result']['tax'], 1)

        flight_routing.reference_cabin = origin_routing_info['routing_info']['reference_cabin']
        flight_routing.reference_cabin_grade = origin_routing_info['routing_info']['reference_cabin_grade']
        flight_routing.adult_price = verify_adult_price
        flight_routing.adult_tax = verify_adult_tax
        flight_routing.child_price = verify_child_price
        flight_routing.child_tax = verify_child_tax
        flight_routing.routing_key_detail = origin_routing_info['routing_info']['routing_key_detail']
        flight_routing.routing_key = origin_routing_info['routing_info']['routing_key']

        rk_dep_time = datetime.datetime.strptime(
                                           origin_routing_info['routing_info']['from_segments'][0]['dep_time'],
                                                                           '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M')
        rk_arr_time = datetime.datetime.strptime(
                                           origin_routing_info['routing_info']['from_segments'][-1]['arr_time'],
                                                                           '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M')
        rk_flight_number = '-'.join([s['flight_number'] for s in origin_routing_info['routing_info']['from_segments']])
        rk_cabin = '-'.join([s['cabin'] for s in origin_routing_info['routing_info']['from_segments']])
        rk_cabin_grade = '-'.join([s['cabin_grade'] for s in origin_routing_info['routing_info']['from_segments']])

        if origin_routing_info['routing_info'].get('ret_segments'):
            rk_dep_time = '{},{}'.format(rk_dep_time, datetime.datetime.strptime(
                                           origin_routing_info['routing_info']['ret_segments'][0]['dep_time'],
                                                                           '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'))
            rk_arr_time = '{},{}'.format(rk_arr_time, datetime.datetime.strptime(
                origin_routing_info['routing_info']['ret_segments'][-1]['arr_time'],
                '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'))
            rk_flight_number = '{},{}'.format(rk_flight_number, '-'.join(
                [s['flight_number'] for s in origin_routing_info['routing_info']['ret_segments']]))
            rk_cabin = '{},{}'.format(rk_cabin, '-'.join(
                [s['cabin'] for s in origin_routing_info['routing_info']['ret_segments']]))
            rk_cabin_grade = '{},{}'.format(rk_cabin_grade, '-'.join(
                [s['cabin_grade'] for s in origin_routing_info['routing_info']['ret_segments']]))

        rk_info = RoutingKey.serialize(from_airport=origin_routing_info['routing_info']['from_segments'][0]['dep_airport'],
                                       dep_time=rk_dep_time,
                                       to_airport=origin_routing_info['routing_info']['from_segments'][-1]['arr_airport'],
                                       arr_time=rk_arr_time,
                                       flight_number=rk_flight_number,
                                       cabin=rk_cabin,
                                       cabin_grade=rk_cabin_grade,
                                       product='COMMON',
                                       adult_price=verify_adult_price,
                                       adult_tax=verify_adult_tax,
                                       provider_channel=self.provider_channel,
                                       child_price=verify_child_price,
                                       child_tax=verify_child_tax,
                                       inf_price=verify_inf_price if verify_inf_price else verify_child_price,
                                       inf_tax=verify_inf_tax if verify_inf_tax else verify_child_tax,
                                       provider=self.provider,
                                       search_from_airport=search_info.from_airport,
                                       search_to_airport=search_info.to_airport,
                                       from_date=search_info.from_date,
                                       ret_date=search_info.ret_date,
                                       routing_range=search_info.routing_range,
                                       trip_type=search_info.trip_type,
                                       is_multi_segments=1 if len(origin_routing_info['routing_info']['from_segments']) > 1 else 0
                                       )

        flight_routing.routing_key_detail = rk_info['plain']
        flight_routing.routing_key = rk_info['encrypted']
        Logger().debug("=============== return flight routing :{}=========".format(flight_routing))
        return flight_routing

    def _order_get_session(self, http_session, order_info):

        verify_result_key = 'provider_verify_result|{}|{}|{}|{}|{}|{}|{}|{}'.format(
            order_info.from_airport, order_info.to_airport, order_info.from_date, '', '1',
            order_info.adt_count, order_info.chd_count, self.provider_channel
        )
        verify_result_data = {}
        no_origin_routing = True
        while True:
            verify_result_json = TBG.redis_conn.redis_pool.rpop(verify_result_key)
            Logger().debug("======== verify result cache json: {}===".format(verify_result_json))
            if not verify_result_json:
                break
            verify_data = json.loads(verify_result_json)
            if verify_data['create_time'] and datetime.datetime.now() - datetime.timedelta(seconds=9 * 60) \
                < datetime.datetime.strptime(verify_data['create_time'], '%Y-%m-%d %H:%M:%S'):
                verify_result_data = verify_data['data']
                no_origin_routing = False
                break
            else:
                continue
        if no_origin_routing:
            self._verify(http_session, order_info)
            verify_result_json = TBG.redis_conn.redis_pool.rpop(verify_result_key)
            Logger().debug("======== verify result cache json: {}===".format(verify_result_json))
            if not verify_result_json:
                raise ProviderVerifyException('NO_VERIFY_ROUTING')
            else:
                verify_result_data = json.loads(verify_result_json)['data']

        if not verify_result_data:
            raise ProviderVerifyException('NO_VERIFY_ROUTING')

        return verify_result_data

    def _booking(self, http_session, order_info):

        age_type_mapping = {
            'ADT': 0,
            'CHD': 1,
            'INF': 2,
        }
        contact = order_info.contacts[0]
        verify_result_data = self._order_get_session(http_session, order_info)

        passenger_data = [OrderedDict(sorted({
            'lastName': p.last_name,
            'firstName': p.first_name,
            'type': age_type_mapping[p.current_age_type(order_info.from_date)],
            'birthday': p.birthdate.replace("-", ""),
            'gender': 'Male' if p.gender == 'M' else 'Female',
            'cardNum': p.selected_card_no,
            "cardType": p.used_card_type,
            "cardIssuePlace": p.card_issue_place,
            'cardExpired': p.card_expired.replace('-', ''),
            'nationality': p.nationality,
        }.items(), key=lambda x: x[0])) for p in order_info.passengers]
        contact_data = OrderedDict(sorted({
            "lastName": order_info.passengers[0].last_name,
            "firstName": order_info.passengers[0].first_name,
            "email": TBG.global_config['OPERATION_CONTACT_EMAIL'],
            "mobileNum": TBG.global_config['OPERATION_CONTACT_MOBILE'],
            "mobileCountry": "86",
            "gender": "Male",
        }.items(), key=lambda x: x[0]))

        verify_adult_price = round(verify_result_data['verify_result']['costPrice'], 1)
        verify_adult_tax = round(verify_result_data['verify_result']['tax'], 1)
        verify_child_price = round(verify_result_data['verify_result']['costChildPrice'] if verify_result_data['verify_result'].get('costChildPrice') else 0, 1)
        verify_child_tax = round(verify_result_data['verify_result']['childTax'] if verify_result_data['verify_result'].get('childTax') else 0, 1)
        verify_inf_price = round(verify_result_data['verify_result']['costChildPrice'] if verify_result_data['verify_result'].get('costChildPrice') else 0, 1)
        verify_inf_tax = round(verify_result_data['verify_result']['childTax'] if verify_result_data['verify_result'].get('childTax') else 0, 1)
        total_price = order_info.adt_count * (verify_adult_price + verify_adult_tax) + \
            order_info.chd_count * (verify_child_price + verify_child_tax) + \
            order_info.inf_count * (verify_inf_price + verify_inf_tax)

        post_data = {
            'partnerId': self.partner_id,
            'sessionId': verify_result_data['verify_result']['purchaseId'],
            'price': total_price,
            'contact': contact_data,
            'passengers': passenger_data,
        }

        post_data = OrderedDict(sorted(post_data.items(), key=lambda x: x[0]))
        post_data = json.dumps(post_data, separators=(',', ':'))
        Logger().info("========= order post data: {} ===".format(post_data))
        token = hashlib.md5(post_data + self.appsecurity).hexdigest()
        url = '{}/flight/place-orders-separately'.format(self.base_url)
        headers = {'Content-Type': 'application/json', 'token': token, 'appid': self.app_id}
        result = http_session.request(url=url, data=post_data, method='POST', headers=headers, is_direct=True).to_json()
        Logger().info("========= order result: {} ===".format(result))

        if not result.get('resultCode') == 200:
            Logger().error("===== igola booking error: {}".format(result))
            raise BookingException('igola booking error')

        order_info.provider_order_status = 'BOOK_SUCCESS_AND_WAITING_PAY'
        order_info.provider_order_id = result['result']['orderNo']
        order_info.provider_price = total_price
        order_info.pnr_code = result['result']['pnr']
        order_info.extra_data = json.dumps(result)
        Logger().info('booking success')
        return order_info

    def _pay(self, order_info, http_session, pay_dict):
        """
        支付
        :param http_session:
        :return:
        """

        post_data = {
            'partnerId': self.partner_id,
            'orderNo': order_info.provider_order_id,
        }
        post_data = OrderedDict(sorted(post_data.items(), key=lambda x: x[0]))
        post_data = json.dumps(post_data, separators=(',', ':'))
        Logger().info("========= pay post data: {} ===".format(post_data))
        token = hashlib.md5(post_data + self.appsecurity).hexdigest()
        url = '{}/flight/payment-separately'.format(self.base_url)
        headers = {'Content-Type': 'application/json', 'token': token, 'appid': self.app_id}
        result = http_session.request(url=url, data=post_data, method='POST', headers=headers, is_direct=True).to_json()
        Logger().info("====== pay result:{} ==".format(result))
        if not result.get('resultCode') == 200:
            raise PayException('pay failed!')

        return pay_dict['alipay_yiyou180']

    def _before_notice_issue_interface(self, req_body):
        """

        :param req_body:
        :return:
        """
        try:

            self.final_result = json.dumps({"resultCode": 1})

            Logger().info("=======  notice issue req body: {}".format(req_body))
            data = json.loads(req_body)

            provider_order_id = data['orderNo']
            return data, str(provider_order_id)

        except:
            import traceback
            print traceback.format_exc()
            Logger().serror(traceback.format_exc())
            return None, None

    def _after_notice_issue_interface(self, sub_order, notice_data):
        """

        :param order_info: order_info class
        :return:
        """

        try:

            if notice_data.get('orderStatus') == 'SUCCESS':
                has_ticket = False
                ticket_info_list = None

                url = '{}/flight/query-order-detail'.format(self.base_url)
                post_data = {
                    'partnerId': self.partner_id,
                    'orderNo': notice_data['orderNo']
                }
                post_data = OrderedDict(sorted(post_data.items(), key=lambda x: x[0]))
                post_data = json.dumps(post_data, separators=(',', ':'))
                Logger().info("========= order detail post data: {} ===".format(post_data))
                token = hashlib.md5(post_data + self.appsecurity).hexdigest()
                headers = {'Content-Type': 'application/json', 'token': token, 'appid': self.app_id}
                http_session = HttpRequest()

                for i in xrange(20):
                    result = http_session.request(url=url, data=post_data, method='POST', headers=headers,
                                                  is_direct=True).to_json()
                    if not result['result']['flightOrders']:
                        Logger().error("notice ticket error:{}".format(result))
                        raise NoticeIssueInterfaceException('notice ticket error')
                    ticket_info_list = result['result']['flightOrders'][0]['passengerInfos']
                    sub_has_ticket = True
                    for info in ticket_info_list:
                        if not info['ticketNo']:
                            sub_has_ticket = False
                            break
                    if sub_has_ticket:
                        has_ticket = True
                        break
                    time.sleep(6)

                if not has_ticket:
                    Logger().error("notice ticket error:{}".format(ticket_info_list))
                    raise NoticeIssueInterfaceException('notice issue have no tickets')

                for info in ticket_info_list:
                    # 填入票号
                    Logger().sinfo("============ igola provider start to update ticket and status =======")
                    Logger().sinfo(json.dumps(info))

                    sql = 'UPDATE person_2_flight_order as a inner join person2flightorder_suborder as b on a.id = b.person2flightorder set a.ticket_no = "{}" where b.suborder = {} and a.used_card_no = "{}"'.format(
                        info['ticketNo'], sub_order.id, info['idNumber'])
                    TBG.tourbillon_db.execute(sql)
                    # 变更子订单状态
                    TBG.tourbillon_db.execute(
                        'update sub_order set provider_order_status="%s" where id = %s' % (
                        'ISSUE_SUCCESS', sub_order.id))
                    commit()
                    flush()
            elif notice_data.get('orderStatus') == 'BOOKING':
                Logger().info('igola provider booking..')
            else:
                Logger().error("==== igola notice issue error. result: {}".format(notice_data))
                raise NoticeIssueInterfaceException('notice ticket error')
            self.final_result = json.dumps({"resultCode": 200})
        except:
            import traceback
            print traceback.format_exc()
            Logger().serror(traceback.format_exc())
            self.final_result = json.dumps({"resultCode": 1})

