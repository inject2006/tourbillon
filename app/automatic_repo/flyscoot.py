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


class Flyscoot(ProvderAutoBase):
    timeout = 50  # 请求超时时间
    provider = 'TR_PROVIDER'  # 子类继承必须赋
    provider_channel = 'TR_PROVIDER_WEB'  # 子类继承必须赋
    operation_product_type = '会员折扣'  # 运价类型：0: GDS公布运价 1:GDS私有运价 2:航司官网产品  3:廉价航司产品 4:特价产品
    operation_product_mode = 'A2B'
    pay_channel = 'ALIPAY'
    provider_token = '5e7ba8bddd7b9648'
    is_display = True
    trip_type_list = ['OW', 'RT']
    no_flight_ttl = 3600 * 3 # 无航班缓存超时时间设定
    carrier_list = ['TR', '5J']


    CACHE_PR_CONFIG = {
        1: {'cabin_expired_time': 60 * 10, 'cabin_attenuation': 3,'fare_expired_time':86400 * 30},
        2: {'cabin_expired_time': 60 * 10, 'cabin_attenuation': 2,'fare_expired_time':86400 * 20},
        3: {'cabin_expired_time': 60 * 5, 'cabin_attenuation': 1,'fare_expired_time':86400 * 10},
        4: {'cabin_expired_time': 60 * 5, 'cabin_attenuation': 1,'fare_expired_time':86400 * 5},
        5: {'cabin_expired_time': 60 * 5, 'cabin_attenuation': 0,'fare_expired_time':86400},

    }
    search_interval_time = 0.1

    def __init__(self):
        super(Flyscoot, self).__init__()


    def _flight_search(self, http_session, search_info):
        """
        航班爬取模块，
        TODO :目前只考虑单程
        :return:
        """

        Logger().debug('search flight')

        flyscoot_airport_mapping = {
            'SEL': 'ICN',
            'TYO': 'NRT',
            'BJS': 'PEK',
            'OSA': 'KIX',
            'PAR': 'CDG',
            'SHA': 'PVG',
            'MOW': 'DME',
        }

        if search_info.trip_type == 'OW':
            post_data = '{"type":"oneway","traveller_count":%s,"journeys":[{"order":1,"origin":"%s","destination":"%s","date":"%s"}]}' % (
                search_info.adt_count + search_info.chd_count,
                flyscoot_airport_mapping.get(search_info.from_airport, search_info.from_airport),
                flyscoot_airport_mapping.get(search_info.to_airport, search_info.to_airport),
                datetime.datetime.strptime(search_info.from_date, '%Y-%m-%d').strftime('%d-%b-%Y')
            )
        elif search_info.trip_type == 'RT':
            post_data = '{"type":"return","traveller_count":%s,"journeys":[{"order":1,"origin":"%s","destination":"%s","date":"%s"},{"order":2,"origin":"%s","destination":"%s","date":"%s"}]}' % (
                search_info.adt_count + search_info.chd_count,
                flyscoot_airport_mapping.get(search_info.from_airport, search_info.from_airport),
                flyscoot_airport_mapping.get(search_info.to_airport, search_info.to_airport),
                datetime.datetime.strptime(search_info.from_date, '%Y-%m-%d').strftime('%d-%b-%Y'),
                flyscoot_airport_mapping.get(search_info.to_airport, search_info.to_airport),
                flyscoot_airport_mapping.get(search_info.from_airport, search_info.from_airport),
                datetime.datetime.strptime(search_info.ret_date, '%Y-%m-%d').strftime('%d-%b-%Y')
            )
        else:
            raise FlightSearchCritical('No available trip_type')

        headers = {
            'Host': 'scoot.api.amber.airblackbox.com',
            'Connection': 'keep-alive',
            'Accept': 'application/json, text/plain, */*',
            'Origin': 'https://valuealliance.flyscoot.com',
            'Abb-Sponsor': 'scoot',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36',
            'Referer': 'https://valuealliance.flyscoot.com/',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-GB,en;q=0.9,en-US;q=0.8,zh-CN;q=0.7,zh;q=0.6',
        }
        http_session.update_headers(headers)

        fixed_proxy = http_session.preset_proxy_ip('A')
        url = 'https://scoot.api.amber.airblackbox.com/v1/token'
        result = http_session.request(url=url, method='GET', verify=False, proxies=fixed_proxy)

        try:
            booking_token = result.to_json()['booking_token']
        except:
            raise FlightSearchException('flyscoot get token failed')

        book_datetime = (datetime.datetime.now() - datetime.timedelta(seconds=60 * 60 * 8)).strftime('%d-%b-%Y %H:%M:%S')
        request_token = hashlib.sha256(post_data + book_datetime + booking_token).hexdigest()

        http_session.update_headers({
            'Abb-Request-Token': request_token,
            'Abb-Date-Time': book_datetime,
            'Abb-Booking-Token': booking_token,
            'Content-Type': 'application/json;charset=UTF-8',
        })
        url = 'https://scoot.api.amber.airblackbox.com/v1/shop'
        result = http_session.request(url=url, method='POST', data=post_data, verify=False, proxies=fixed_proxy)

        # Logger().info("=========== flyscoot search result: {} ".format(result.content))

        try:
            result = result.to_json()
        except:
            Logger().error(result.content)
            raise FlightSearchException(err_code='HIGH_REQ_LIMIT')

        if not result.get('journeys'):
            Logger().warn('flyscoot no flight')
            return search_info

        if not result.get('currency') == 'CNY':
            Logger().warn('flyscoot no flight')
            return search_info

        from_routing_list = []
        ret_routing_list = []
        seg_info_list = result['journey_legs']
        for r in result['journeys']:
            if r['order'] == 1:
                from_routing_list.append(r)
            elif r['order'] == 2:
                ret_routing_list.append(r)
        routing_list = []
        if search_info.trip_type == 'RT':
            for f_r in from_routing_list:
                for r_r in ret_routing_list:
                    routing_list.append([f_r, r_r])
        else:
            for f_r in from_routing_list:
                routing_list.append([f_r])

        for routing in routing_list:
            flight_routing = FlightRoutingInfo()
            flight_routing.product_type = 'DEFAULT'
            routing_number = 1

            from_seg_index_list = routing[0]['journey_leg_lookups']
            ret_seg_index_list = routing[1]['journey_leg_lookups'] if search_info.trip_type == 'RT' else []
            from_cabin_info = sorted(routing[0]['bundles'], key=lambda x: x['adult_price'] + x['adult_tax'])[0]
            ret_cabin_info = sorted(routing[1]['bundles'], key=lambda x: x['adult_price'] + x['adult_tax'])[0] if search_info.trip_type == 'RT' else {}
            valid_routing = True
            for index, s_index in enumerate(from_seg_index_list):
                seg_info = None
                for s_info in seg_info_list:
                    if s_info['key'] == s_index['key']:
                        seg_info = s_info
                        break
                if not seg_info:
                    valid_routing = False
                    break
                for seg in seg_info['segments']:
                    flight_segment = FlightSegmentInfo()
                    flight_segment.carrier = seg['airline_code']
                    dep_time = datetime.datetime.strptime(seg['departure_datetime'],
                                                          '%Y-%m-%dT%H:%M').strftime('%Y-%m-%d %H:%M:%S')
                    arr_time = datetime.datetime.strptime(seg['arrival_datetime'],
                                                          '%Y-%m-%dT%H:%M').strftime('%Y-%m-%d %H:%M:%S')
                    flight_segment.dep_airport = seg['origin']
                    flight_segment.dep_time = dep_time
                    flight_segment.arr_airport = seg['destination']
                    flight_segment.arr_time = arr_time
                    flight_segment.flight_number = '{}{}'.format(seg['airline_code'], seg['flight_num'])
                    flight_segment.dep_terminal = seg['segment_legs'][0]['departure_terminal']
                    flight_segment.arr_terminal = seg['segment_legs'][-1]['arrival_terminal']
                    flight_segment.cabin = from_cabin_info['product_classes'][index]['segments_fares'][seg['key']]['name']
                    flight_segment.cabin_grade = 'Y'
                    flight_segment.cabin_count = from_cabin_info['product_classes'][index]['segments_fares'][seg['key']]['seats_available']
                    segment_duration = (datetime.datetime.strptime(arr_time, '%Y-%m-%d %H:%M:%S') -
                                        datetime.datetime.strptime(dep_time, '%Y-%m-%d %H:%M:%S')).total_seconds()
                    flight_segment.duration = int(segment_duration / 60)
                    flight_segment.routing_number = routing_number
                    routing_number += 1
                    flight_routing.from_segments.append(flight_segment)

            for index, s_index in enumerate(ret_seg_index_list):
                seg_info = None
                for s_info in seg_info_list:
                    if s_info['key'] == s_index['key']:
                        seg_info = s_info
                        break
                if not seg_info:
                    valid_routing = False
                    break
                for seg in seg_info['segments']:
                    flight_segment = FlightSegmentInfo()
                    flight_segment.carrier = seg['airline_code']
                    dep_time = datetime.datetime.strptime(seg['departure_datetime'],
                                                          '%Y-%m-%dT%H:%M').strftime('%Y-%m-%d %H:%M:%S')
                    arr_time = datetime.datetime.strptime(seg['arrival_datetime'],
                                                          '%Y-%m-%dT%H:%M').strftime('%Y-%m-%d %H:%M:%S')
                    flight_segment.dep_airport = seg['origin']
                    flight_segment.dep_time = dep_time
                    flight_segment.arr_airport = seg['destination']
                    flight_segment.arr_time = arr_time
                    flight_segment.flight_number = '{}{}'.format(seg['airline_code'], seg['flight_num'])
                    flight_segment.dep_terminal = seg['segment_legs'][0]['departure_terminal']
                    flight_segment.arr_terminal = seg['segment_legs'][-1]['arrival_terminal']
                    flight_segment.cabin = ret_cabin_info['product_classes'][index]['segments_fares'][seg['key']]['name']
                    flight_segment.cabin_grade = 'Y'
                    flight_segment.cabin_count = ret_cabin_info['product_classes'][index]['segments_fares'][seg['key']]['seats_available']
                    segment_duration = (datetime.datetime.strptime(arr_time, '%Y-%m-%d %H:%M:%S') -
                                        datetime.datetime.strptime(dep_time, '%Y-%m-%d %H:%M:%S')).total_seconds()
                    flight_segment.duration = int(segment_duration / 60)
                    flight_segment.routing_number = routing_number
                    routing_number += 1
                    flight_routing.ret_segments.append(flight_segment)

            if not valid_routing:
                continue

            flight_routing.adult_price = from_cabin_info['adult_price'] + ret_cabin_info['adult_price'] if search_info.trip_type == 'RT' else from_cabin_info['adult_price']
            flight_routing.adult_tax = from_cabin_info['adult_tax'] + ret_cabin_info['adult_tax'] if search_info.trip_type == 'RT' else from_cabin_info['adult_tax']
            flight_routing.child_price = flight_routing.adult_price
            flight_routing.child_tax = flight_routing.adult_tax

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
                cabin_result = '{},{}'.format(cabin_result,
                                              '-'.join([s.cabin for s in flight_routing.ret_segments]))
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
                                           is_include_operation_carrier=0,
                                           is_multi_segments=1 if len(flight_routing.from_segments) > 1 or flight_routing.ret_segments else 0
                                           )

            flight_routing.routing_key_detail = rk_info['plain']
            flight_routing.routing_key = rk_info['encrypted']

            search_info.assoc_search_routings.append(flight_routing)

        return search_info
