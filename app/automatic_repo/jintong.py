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


class JinTong(ProvderAutoBase):
    timeout = 50  # 请求超时时间
    provider = 'jintong_provider'  # 子类继承必须赋
    provider_channel = 'jintong_provider_agent'  # 子类继承必须赋
    operation_product_type = '会员折扣'  # 运价类型：0: GDS公布运价 1:GDS私有运价 2:航司官网产品  3:廉价航司产品 4:特价产品
    operation_product_mode = 'A2B'
    pay_channel = 'ALIPAY'
    provider_token = 'de2556bc76a259a2'
    is_display = True
    verify_realtime_search_count = 1
    is_order_directly = True
    is_include_booking_module = True  # 是否包含下单模块
    trip_type_list = ['OW', 'RT']
    no_flight_ttl = 1800  # 无航班缓存超时时间设定

    CACHE_PR_CONFIG = {
        1: {'cabin_expired_time': 60 * 60 * 1, 'cabin_attenuation': 3, 'fare_expired_time': 86400 * 30},
        2: {'cabin_expired_time': 60 * 45, 'cabin_attenuation': 2, 'fare_expired_time': 86400 * 20},
        3: {'cabin_expired_time': 60 * 30, 'cabin_attenuation': 1, 'fare_expired_time': 86400 * 10},
        4: {'cabin_expired_time': 60 * 25, 'cabin_attenuation': 1, 'fare_expired_time': 86400 * 5},
        5: {'cabin_expired_time': 60 * 20, 'cabin_attenuation': 0, 'fare_expired_time': 86400},

    }

    search_interval_time = 0

    def __init__(self):
        super(JinTong, self).__init__()

        self.verify_tries = 3
        self.cid = 'caigou123'
        self.aes_key = 'c243cf07d0ef730240e9d91b7b9793f2'
        self.aes_iv = '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'  # aes iv
        # self.base_url = 'http://testiapi.jinri.net:6012'   # 测试
        self.base_url = 'http://iapi.jinri.net'  # 生产

    def aes_encrypt(self, data):
        """
        aes 加密
        :param data:
        :return:
        """
        pad = lambda s: s + (16 - len(s) % 16) * chr(16 - len(s) % 16)
        generator = AES.new(self.aes_key, AES.MODE_CBC, self.aes_iv)
        crypt = generator.encrypt(pad(data))
        return base64.b64encode(crypt)

    def aes_decrypt(self, data):
        """
        aes 解密
        :param data:
        :return:
        """
        unpad = lambda s: s[0:-ord(s[-1])]
        data = base64.b64decode(data)
        generator = AES.new(self.aes_key, AES.MODE_CBC, self.aes_iv)
        recovery = unpad(generator.decrypt(data))
        return recovery

    def _flight_search(self, http_session, search_info):
        """
        航班爬取模块，
        TODO :目前只考虑单程
        :return:
        """

        Logger().debug('search flight')

        if search_info.trip_type == 'OW':
            trip_type = 1
        elif search_info.trip_type == 'RT':
            trip_type = 2
        else:
            raise FlightSearchCritical('No available trip_type')

        post_data = {
            "cid": self.cid,
            "tripType": trip_type,
            "fromCity": search_info.from_airport,
            "toCity": search_info.to_airport,
            "fromDate": search_info.from_date.replace('-', ''),
            "cabinClass": "Y",
            "Passengers": {
                "AdultsNum": search_info.adt_count,
                "ChildNum": search_info.chd_count,
                "InfantNum": search_info.inf_count,
            }
        }
        if search_info.trip_type == 'RT':
            post_data.update({'retDate': search_info.ret_date.replace('-', '')})

        # Logger().info("========= post data: {} ===".format(post_data))
        url = '{}/{}/searchplus'.format(self.base_url, self.cid)
        result = http_session.request(url=url, json=post_data, method='POST', is_direct=True)

        Logger().debug("====== search result:{} ==".format(result.content))
        result = json.loads(result.content)
        if not result.get('status') == 0:
            Logger().error(result.get('msg'))
            raise FlightSearchException('jintong flight search error')

        routing_list = result['routings']
        if not routing_list:
            Logger().warn('jintong provider no flight')
            return search_info

        origin_routing_list = []
        for routing in routing_list:
            from_seg_list = routing['fromSegments']
            ret_seg_list = routing['retSegments']
            flight_routing = FlightRoutingInfo()
            flight_routing.product_type = 'DEFAULT'
            routing_number = 1
            is_include_operation_carrier = 0
            for seg in from_seg_list:
                flight_segment = FlightSegmentInfo()
                flight_segment.carrier = seg['carrier']
                if seg.get('codeShare'):
                    is_include_operation_carrier = 1
                dep_time = datetime.datetime.strptime(seg['depTime'], '%Y%m%d%H%M').strftime('%Y-%m-%d %H:%M:%S')
                arr_time = datetime.datetime.strptime(seg['arrTime'], '%Y%m%d%H%M').strftime('%Y-%m-%d %H:%M:%S')
                flight_segment.dep_airport = seg['depAirport']
                flight_segment.dep_time = dep_time
                flight_segment.arr_airport = seg['arrAirport']
                flight_segment.arr_time = arr_time
                if seg.get('stopCities'):
                    flight_segment.stop_cities = seg['stopCities']
                flight_segment.flight_number = seg['flightNumber']
                flight_segment.dep_terminal = seg['departureTerminal'] if seg.get('departureTerminal') else ''
                flight_segment.arr_terminal = seg['arrivingTerminal'] if seg.get('arrivingTerminal') else ''
                cabin_grade_mapping = {
                    1: 'Y',
                    2: 'C',
                    3: 'F',
                    4: 'Y'
                }
                flight_segment.cabin = seg['cabin']
                flight_segment.cabin_grade = cabin_grade_mapping[seg['cabinClass']]
                flight_segment.cabin_count = int(seg['seatCount']) if seg.get('seatCount') else 9
                flight_segment.duration = seg['duration']
                flight_segment.routing_number = routing_number
                routing_number += 1
                flight_routing.from_segments.append(flight_segment)

            for seg in ret_seg_list:
                flight_segment = FlightSegmentInfo()
                flight_segment.carrier = seg['carrier']
                if seg.get('codeShare'):
                    is_include_operation_carrier = 1
                dep_time = datetime.datetime.strptime(seg['depTime'], '%Y%m%d%H%M').strftime('%Y-%m-%d %H:%M:%S')
                arr_time = datetime.datetime.strptime(seg['arrTime'], '%Y%m%d%H%M').strftime('%Y-%m-%d %H:%M:%S')
                flight_segment.dep_airport = seg['depAirport']
                flight_segment.dep_time = dep_time
                flight_segment.arr_airport = seg['arrAirport']
                flight_segment.arr_time = arr_time
                if seg.get('stopCities'):
                    flight_segment.stop_cities = seg['stopCities']
                flight_segment.flight_number = seg['flightNumber']
                flight_segment.dep_terminal = seg['departureTerminal'] if seg.get('departureTerminal') else ''
                flight_segment.arr_terminal = seg['arrivingTerminal'] if seg.get('arrivingTerminal') else ''
                cabin_grade_mapping = {
                    1: 'Y',
                    2: 'C',
                    3: 'F',
                    4: 'Y'
                }
                flight_segment.cabin = seg['cabin']
                flight_segment.cabin_grade = cabin_grade_mapping[seg['cabinClass']]
                flight_segment.cabin_count = int(seg['seatCount']) if seg.get('seatCount') else 9
                flight_segment.duration = seg['duration']
                flight_segment.routing_number = routing_number
                routing_number += 1
                flight_routing.ret_segments.append(flight_segment)

            # 补充舱位和舱等
            flight_routing.reference_cabin = flight_routing.from_segments[0].cabin
            flight_routing.reference_cabin_grade = flight_routing.from_segments[0].cabin_grade

            low_price_policy = sorted(routing['policys'], key=lambda x: x['adultPrice']['price'] + x['adultPrice']['tax'])[0]

            # if low_price_policy:
            #     low_price_policy = low_price_policy[0]
            # else:
            #     low_price_policy = routing['policys'][0]


            flight_routing.adult_price = low_price_policy['adultPrice']['price']
            flight_routing.adult_tax = low_price_policy['adultPrice']['tax']
            flight_routing.child_price = low_price_policy['childPrice']['price'] if low_price_policy.get('childPrice') \
                else flight_routing.adult_price
            flight_routing.child_tax = low_price_policy['childPrice']['tax'] if low_price_policy.get('childPrice') \
                else flight_routing.adult_tax


            rk_dep_time = datetime.datetime.strptime(flight_routing.from_segments[0].dep_time,
                                       '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M')

            rk_arr_time = datetime.datetime.strptime(flight_routing.from_segments[-1].arr_time,
                                       '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M')
            rk_flight_no = '-'.join([s.flight_number for s in flight_routing.from_segments])
            rk_cabin = '-'.join([s.cabin for s in flight_routing.from_segments])
            rk_cabin_grade = '-'.join([s.cabin_grade for s in flight_routing.from_segments])
            if search_info.trip_type == 'RT':

                rk_dep_time = '{},{}'.format(rk_dep_time, datetime.datetime.strptime(flight_routing.ret_segments[0].dep_time,
                                       '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'))
                rk_arr_time = '{},{}'.format(rk_arr_time, datetime.datetime.strptime(flight_routing.ret_segments[-1].arr_time,
                                       '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'))
                rk_flight_no = '{},{}'.format(rk_flight_no, '-'.join([s.flight_number for s in flight_routing.ret_segments]))
                rk_cabin = '{},{}'.format(rk_cabin, '-'.join([s.cabin for s in flight_routing.ret_segments]))
                rk_cabin_grade = '{},{}'.format(rk_cabin_grade, '-'.join([s.cabin_grade for s in flight_routing.ret_segments]))

            rk_info = RoutingKey.serialize(from_airport=flight_routing.from_segments[0].dep_airport,
                                           dep_time=rk_dep_time,
                                           to_airport=flight_routing.from_segments[-1].arr_airport,
                                           arr_time=rk_arr_time,
                                           flight_number=rk_flight_no,
                                           cabin=rk_cabin,
                                           cabin_grade=rk_cabin_grade,
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
                                           ret_date=search_info.ret_date,
                                           routing_range=search_info.routing_range,
                                           trip_type=search_info.trip_type,
                                           is_include_operation_carrier=is_include_operation_carrier,
                                           is_multi_segments=1 if len(flight_routing.from_segments) > 1 or flight_routing.ret_segments else 0
                                           )
            flight_routing.routing_key_detail = rk_info['plain']
            flight_routing.routing_key = rk_info['encrypted']
            search_info.assoc_search_routings.append(flight_routing)
            routing['routing_key'] = flight_routing.routing_key
            routing['segment_info'] = flight_routing
            routing['source_data_key'] = low_price_policy['data']
            origin_routing_list.append(routing)

        origin_data_key = 'provider_search_origin_routings|{}|{}|{}|{}|{}|{}|{}|{}'.format(
            search_info.from_airport, search_info.to_airport, search_info.from_date, '', '1',
            search_info.adt_count, search_info.chd_count, self.provider_channel
        )
        TBG.redis_conn.redis_pool.set(origin_data_key, json.dumps(origin_routing_list), 29 * 60)

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
                # Logger().info("========== verify cp key:{}   search cp key:{} =====".format(verify_un_key, search_un_key))
                if search_un_key == verify_un_key:
                    o.pop('routing_key')
                    routing_info = o
                    break
            except:
                pass
        if not routing_info:
            raise ProviderVerifyFail('NO_VERIFY_ROUTING')

        return routing_info

    def _verify(self, http_session, search_info):

        if search_info.trip_type == 'OW':
            trip_type = 1
        elif search_info.trip_type == 'RT':
            trip_type = 2
        else:
            raise FlightSearchCritical('No available trip_type')

        origin_routing_info = self._verify_get_session(http_session, search_info)
        segment_info = origin_routing_info.pop('segment_info')
        source_data_key = origin_routing_info.pop('source_data_key')
        passengers = []
        for i in xrange(search_info.adt_count):
            passengers.append({
                'name': '{}/{}'.format(''.join([random.choice(string.uppercase) for i in xrange(6)]),
                                       ''.join([random.choice(string.uppercase) for i in xrange(6)])),
                'ageType': 0,
                'birthday': '19740225',
                'gender': 'M',
                'cardType': 'PP',
                'cardNum': Random.gen_passport(),
                'cardExpired': '20240101',
                'cardIssuePlace': 'CN',
                'nationality': 'CN',
            })
        for i in xrange(search_info.chd_count):
            passengers.append({
                'name': '{}/{}'.format(''.join([random.choice(string.uppercase) for i in xrange(6)]),
                                       ''.join([random.choice(string.uppercase) for i in xrange(6)])),
                'ageType': 1,
                'birthday': '20150225',
                'gender': 'M',
                'cardType': 'PP',
                'cardNum': Random.gen_passport(),
                'cardExpired': '20240101',
                'cardIssuePlace': 'CN',
                'nationality': 'CN',
            })
        post_data = {
            'cid': self.cid,
            "tripType": trip_type,
            'routing': {
                'data': source_data_key,
                'fromSegments': origin_routing_info['fromSegments'],
                'retSegments': origin_routing_info['retSegments'],
            },
            'passengers': passengers,
        }
        Logger().info("========= verify post data: {} ===".format(post_data))
        url = '{}/{}/verify'.format(self.base_url, self.cid)
        verify_result = http_session.request(url=url, json=post_data, method='POST', is_direct=True).to_json()
        Logger().info("====== verify result:{} ==".format(json.dumps(verify_result)))

        if not verify_result.get('status') == 0:
            raise ProviderVerifyFail('verify failed!')

        cabin_count = verify_result['maxSeats']
        if search_info.adt_count + search_info.chd_count > cabin_count:
            raise ProviderVerifyFail('cabin count limit !')

        verify_result_key = 'provider_verify_result|{}|{}|{}|{}|{}|{}|{}|{}'.format(
            search_info.from_airport, search_info.to_airport, search_info.from_date, '', '1',
            search_info.adt_count, search_info.chd_count, self.provider_channel
        )
        TBG.redis_conn.redis_pool.lpush(verify_result_key, json.dumps({
            'data': verify_result,
            'create_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }))

        flight_routing = FlightRoutingInfo()
        flight_routing.product_type = 'DEFAULT'
        for seg in segment_info['from_segments']:

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
            flight_segment.cabin_count = verify_result['maxSeats']
            flight_segment.duration = seg['duration']
            flight_segment.routing_number = seg['routing_number']
            flight_routing.from_segments.append(flight_segment)

        for seg in segment_info['ret_segments']:

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
            flight_segment.cabin_count = verify_result['maxSeats']
            flight_segment.duration = seg['duration']
            flight_segment.routing_number = seg['routing_number']
            flight_routing.ret_segments.append(flight_segment)

        # 补充舱位和舱等
        verify_adult_price = verify_result['routing']['adultPrice']
        verify_adult_tax = verify_result['routing']['adultTax']
        verify_child_price = verify_result['routing']['childPrice'] if verify_result['routing'].get('childPrice') else verify_adult_price
        verify_child_tax = verify_result['routing']['childTax'] if verify_result['routing'].get('childTax') else verify_adult_tax

        flight_routing.reference_cabin = segment_info['reference_cabin']
        flight_routing.reference_cabin_grade = segment_info['reference_cabin_grade']
        flight_routing.adult_price = verify_adult_price
        flight_routing.adult_tax = verify_adult_tax
        flight_routing.child_price = verify_child_price
        flight_routing.child_tax = verify_child_tax

        rk_dep_time = datetime.datetime.strptime(flight_routing.from_segments[0].dep_time,
                                                 '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M')

        rk_arr_time = datetime.datetime.strptime(flight_routing.from_segments[-1].arr_time,
                                                 '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M')
        rk_flight_no = '-'.join([s.flight_number for s in flight_routing.from_segments])
        rk_cabin = '-'.join([s.cabin for s in flight_routing.from_segments])
        rk_cabin_grade = '-'.join([s.cabin_grade for s in flight_routing.from_segments])
        if search_info.trip_type == 'RT':
            rk_dep_time = '{},{}'.format(rk_dep_time,
                                         datetime.datetime.strptime(flight_routing.ret_segments[0].dep_time,
                                                                    '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'))
            rk_arr_time = '{},{}'.format(rk_arr_time,
                                         datetime.datetime.strptime(flight_routing.ret_segments[-1].arr_time,
                                                                    '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'))
            rk_flight_no = '{},{}'.format(rk_flight_no,
                                          '-'.join([s.flight_number for s in flight_routing.ret_segments]))
            rk_cabin = '{},{}'.format(rk_cabin, '-'.join([s.cabin for s in flight_routing.ret_segments]))
            rk_cabin_grade = '{},{}'.format(rk_cabin_grade,
                                            '-'.join([s.cabin_grade for s in flight_routing.ret_segments]))

        rk_info = RoutingKey.serialize(from_airport=flight_routing.from_segments[0].dep_airport,
                                       dep_time=rk_dep_time,
                                       to_airport=flight_routing.from_segments[-1].arr_airport,
                                       arr_time=rk_arr_time,
                                       flight_number=rk_flight_no,
                                       cabin=rk_cabin,
                                       cabin_grade=rk_cabin_grade,
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
                                       ret_date=search_info.ret_date,
                                       routing_range=search_info.routing_range,
                                       trip_type=search_info.trip_type,
                                       is_multi_segments=1 if len(
                                           flight_routing.from_segments) > 1 or flight_routing.ret_segments else 0
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
            if verify_data['create_time'] and datetime.datetime.now() - datetime.timedelta(seconds=20 * 60) \
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

        if order_info.trip_type == 'OW':
            trip_type = 1
        elif order_info.trip_type == 'RT':
            trip_type = 2
        else:
            raise FlightSearchCritical('No available trip_type')

        verify_result_data = self._order_get_session(http_session, order_info)

        contact = order_info.contacts[0]
        age_type_mapping = {
            'ADT': 0,
            'CHD': 1,
            'INF': 2,
        }

        verify_routing_data = verify_result_data['routing']
        verify_routing_data['rule'] = verify_result_data['rule']
        post_data = {
            'cid': self.cid,
            "tripType": "1",
            "outOrderNum": order_info.sub_order_id,
            "sessionId": verify_result_data['sessionId'],
            "routing": verify_routing_data,
            "passengers": [{
                               "name": "{}/{}".format(p.last_name, p.first_name),
                               "ageType": age_type_mapping[p.current_age_type(order_info.from_date)],
                               "birthday": p.birthdate.replace("-", ""),
                               "gender": p.gender,
                               "cardType": p.used_card_type,
                               "cardNum": p.selected_card_no,
                               "cardExpired": p.card_expired.replace('-', ''),
                               "cardIssuePlace": p.card_issue_place,
                               "nationality": p.nationality
                           } for p in order_info.passengers],
            "contact": {
                "name": contact.name,
                "address": contact.address,
                "postcode": contact.postcode,
                "email": contact.email,
                "mobile": TBG.global_config['OPERATION_CONTACT_MOBILE'],
            }
        }

        Logger().info("========= order post data: {} ===".format(post_data))
        url = '{}/{}/order'.format(self.base_url, self.cid)
        post_data = self.aes_encrypt(json.dumps(post_data))
        result = http_session.request(url=url, data=post_data, method='POST', is_direct=True)
        order_result = json.loads(self.aes_decrypt(result.content))
        Logger().info("============ order result:{} =======".format(order_result))
        if not order_result.get('status') == 0:
            Logger().error("===== jintong booking error: {}".format(order_result))
            raise BookingException('jintong booking error')
        if order_result['orderStatus'] == 'C':
            order_info.provider_order_status = 'BOOK_SUCCESS_AND_WAITING_PAY'
            order_info.provider_order_id = order_result['orderNo']
            order_info.provider_price = order_result['totalPrice']
            if order_result['routing'].get('platFee'):
                order_info.provider_fee = order_result['routing']['platFee']
            order_info.pnr_code = order_result['pnrCode']
            order_info.extra_data = json.dumps(order_result)
        else:
            Logger().info('jintong booking is waiting')
            # order_info.provider_order_status = 'BOOK_SUCCESS'
            order_info.provider_order_status = 'BOOK_SUCCESS_AND_WAITING_PAY'
            order_info.provider_order_id = order_result['orderNo']
            order_info.provider_price = 0
            order_info.pnr_code = order_result['pnrCode']
            order_info.extra_data = json.dumps(order_result)

        # # 支付校验
        # post_data = {
        #     "cid": self.cid,
        #     "tripType": trip_type,
        #     "sessionId": order_result['sessionId'],
        #     "orderNo": order_info.provider_order_id,
        #     "pnrCode": order_info.pnr_code,
        #     "routing": order_result['routing'],
        # }
        # Logger().info("========= pay verify post data: {} ===".format(post_data))
        # post_data = self.aes_encrypt(json.dumps(post_data))
        # url = '{}/{}/payverify'.format(self.base_url, self.cid)
        # result = http_session.request(url=url, data=post_data, method='POST', is_direct=True)
        # pay_result = json.loads(self.aes_decrypt(result.content))
        # Logger().info("====== pay verify result:{} ==".format(json.dumps(pay_result)))
        # if not pay_result.get('status') == 0:
        #     raise BookingException('pay failed!')

        Logger().info('booking success')
        return order_info

    def _pay(self, order_info, http_session, pay_dict):
        """
        支付
        :param http_session:
        :return:
        """

        if order_info.trip_type == 'OW':
            trip_type = 1
        elif order_info.trip_type == 'RT':
            trip_type = 2
        else:
            raise FlightSearchCritical('No available trip_type')

        order_result = json.loads(order_info.extra_data)

        # 支付校验
        post_data = {
            "cid": self.cid,
            "tripType": trip_type,
            "sessionId": order_result['sessionId'],
            "orderNo": order_info.provider_order_id,
            "pnrCode": order_info.pnr_code,
            "routing": order_result['routing'],
        }
        Logger().info("========= pay verify post data: {} ===".format(post_data))
        post_data = self.aes_encrypt(json.dumps(post_data))
        url = '{}/{}/payverify'.format(self.base_url, self.cid)
        result = http_session.request(url=url, data=post_data, method='POST', is_direct=True)
        pay_result = json.loads(self.aes_decrypt(result.content))
        Logger().info("====== pay verify result:{} ==".format(json.dumps(pay_result)))
        if not pay_result.get('status') == 0:
            raise PayException('pay failed!')

        # 支付确认
        post_data = {
            "cid": self.cid,
            "orderNo": order_info.provider_order_id,
            "pnrCode": order_info.pnr_code,
            "payType": "AliPay",
            "issueType": 1,
            "reason": u"请求出票",
            "totalPrice": order_info.provider_price
        }
        Logger().info("========= pay ticket post data: {} ===".format(post_data))
        post_data = self.aes_encrypt(json.dumps(post_data))
        url = '{}/{}/issueticket'.format(self.base_url, self.cid)
        result = http_session.request(url=url, data=post_data, method='POST', is_direct=True)
        pay_result = json.loads(self.aes_decrypt(result.content))
        Logger().info("====== pay ticket result:{} ==".format(json.dumps(pay_result)))
        if not pay_result.get('status') == 0:
            raise PayException('pay failed!')

        Logger().info('pay success')
        order_info.out_trade_no = pay_result['tradeNo']
        return pay_dict['alipay_yiyou180']

    def _before_notice_issue_interface(self, req_body):
        """

        :param req_body:
        :return:
        """
        try:

            self.final_result = json.dumps({"status": 1, "msg": "failed"})

            Logger().info("======= jintong notice issue req body: {}".format(req_body))
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

            if notice_data.get('orderState'):
                # 占位支付通知
                if notice_data['orderState'] == 'J':
                    # 审核驳回
                    Logger().error("jintong order to pay failed: {}".format(notice_data))
                    # 变更子订单状态
                    TBG.tourbillon_db.execute(
                        'update sub_order set provider_order_status="%s" where id = %s' % (
                        'ISSUE_CANCEL', sub_order.id))
                    commit()
                    flush()
                elif notice_data['orderState'] == 'C':
                    # 占位成功，等待支付
                    Logger().info("jintong order to pay success: {}".format(notice_data))
                    # 变更子订单状态
                    TBG.tourbillon_db.execute(
                        'update sub_order set provider_order_status="%s" where id = %s' % (
                            'BOOK_SUCCESS_AND_WAITING_PAY', sub_order.id))
                    if notice_data.get('totalCost'):
                        total_price = float(notice_data['totalCost'])
                        TBG.tourbillon_db.execute(
                            'update sub_order set provider_price=%s where id = %s' % (
                                total_price, sub_order.id))
                        if notice_data.get('platMoney'):
                            fee = float(notice_data['platMoney'])
                            TBG.tourbillon_db.execute(
                                'update sub_order set provider_fee=%s where id = %s' % (
                                    fee, sub_order.id))
                    else:
                        Logger().error('jintong order to pay have no order price!')
                    commit()
                    flush()
                else:
                    Logger().error("jintong order to pay notice failed: {}".format(notice_data))

            elif notice_data.get('canNotList'):
                provider_order_id = notice_data['orderNo']
                sub_order_id = notice_data['outOrderNo']
                content = u"今通国际采购订单暂不能出票\n订单号【{}】\n系统子订单号【{}】\n原因【{}】".format(
                    provider_order_id,
                    sub_order_id,
                    notice_data['canNotList']
                )
                import requests
                try:
                    r = requests.post("http://139.219.106.96:10000/bpns/event", json={
                        "product": "tourbillon",
                        "team": "dev",
                        "source": "tourbillon",
                        "category": "",
                        "level": "warning",
                        "subject": '采购接口暂不能出票',
                        "content": content,
                        "sendto_wechat": {
                            "agentid": 1000011,
                            "msgtype": "text",
                        }
                    }, timeout=3)
                except Exception as e:
                    Logger().serror(e)
            else:
                # 回填票号
                if not notice_data.get('ticketNoItems'):
                    Logger().error("notice ticket error:{}".format(notice_data))
                    raise NoticeIssueInterfaceException('notice ticket error')
                ticket_info_list = notice_data['ticketNoItems']

                for info in ticket_info_list:
                    # 填入票号
                    Logger().sinfo("============ jintong provider start to update ticket and status =======")
                    Logger().sinfo(json.dumps(info))

                    sql = 'UPDATE person_2_flight_order as a inner join person2flightorder_suborder as b on a.id = b.person2flightorder set a.ticket_no = "{}" where b.suborder = {} and a.used_card_no = "{}"'.format(
                        info['ticketNo'], sub_order.id, info['cardNo'])
                    TBG.tourbillon_db.execute(sql)
                    # 变更子订单状态
                    TBG.tourbillon_db.execute(
                        'update sub_order set provider_order_status="%s" where id = %s' % ('ISSUE_SUCCESS', sub_order.id))
                    commit()
                    flush()

            self.final_result = json.dumps({"status": 0, "msg": "success"})
        except:
            import traceback
            print traceback.format_exc()
            Logger().serror(traceback.format_exc())
            self.final_result = json.dumps({"status": 1, "msg": "failed"})

