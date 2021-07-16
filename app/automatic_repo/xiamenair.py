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


class Xiamenair(ProvderAutoBase):
    timeout = 50  # 请求超时时间
    provider = 'MF_PROVIDER'  # 子类继承必须赋
    provider_channel = 'MF_PROVIDER_WEB'  # 子类继承必须赋
    operation_product_type = '会员折扣'  # 运价类型：0: GDS公布运价 1:GDS私有运价 2:航司官网产品  3:廉价航司产品 4:特价产品
    operation_product_mode = 'A2B'
    pay_channel = 'ALIPAY'
    provider_token = '5e7ba8bddd7b9648'
    is_display = True
    trip_type_list = ['OW', 'RT']
    no_flight_ttl = 3600 * 3 # 无航班缓存超时时间设定
    carrier_list = ['MF']  # 供应商所包含的航司列表，如果包含多个并且无法确定，请不要填写，此处会关联执飞航线判断逻辑


    CACHE_PR_CONFIG = {
        1: {'cabin_expired_time': 60 * 10, 'cabin_attenuation': 3,'fare_expired_time':86400 * 30},
        2: {'cabin_expired_time': 60 * 10, 'cabin_attenuation': 2,'fare_expired_time':86400 * 20},
        3: {'cabin_expired_time': 60 * 5, 'cabin_attenuation': 1,'fare_expired_time':86400 * 10},
        4: {'cabin_expired_time': 60 * 5, 'cabin_attenuation': 1,'fare_expired_time':86400 * 5},
        5: {'cabin_expired_time': 60 * 5, 'cabin_attenuation': 0,'fare_expired_time':86400},

    }
    search_interval_time = 0.1

    def __init__(self):
        super(Xiamenair, self).__init__()

    def _flight_search(self, http_session, search_info):
        """
        航班爬取模块，
        TODO :目前只考虑单程
        :return:
        """

        Logger().debug('search flight')

        xiamen_airport_mapping = {
            'SEL': 'ICN',
            'TYO': 'NRT',
            'BJS': 'PEK',
            'OSA': 'KIX',
            'PAR': 'CDG',
        }

        route_list = []
        if search_info.from_airport == 'SHA':
            route_list.append(['SHA', xiamen_airport_mapping.get(search_info.to_airport, search_info.to_airport)])
            route_list.append(['PVG', xiamen_airport_mapping.get(search_info.to_airport, search_info.to_airport)])
        elif search_info.to_airport == 'SHA':
            route_list.append([xiamen_airport_mapping.get(search_info.from_airport, search_info.from_airport),
                              'SHA'])
            route_list.append([xiamen_airport_mapping.get(search_info.from_airport, search_info.from_airport),
                              'PVG'])
        else:
            route_list.append([xiamen_airport_mapping.get(search_info.from_airport, search_info.from_airport),
                               xiamen_airport_mapping.get(search_info.to_airport, search_info.to_airport)])

        self.product_list = []
        self.search_success = False
        self.high_req_limit = False
        task_list = []
        for r in route_list:
            task_list.append(gevent.spawn(self._sub_flight_search, http_session, search_info, r[0], r[1]))
        gevent.joinall(task_list)

        if not self.search_success:
            if self.high_req_limit:
                raise FlightSearchException(err_code='HIGH_REQ_LIMIT')
            else:
                raise FlightSearchException()
        if not self.product_list:
            Logger().warn('xiamenair no flight')
            return search_info
        search_info.assoc_search_routings.extend(self.product_list)
        return search_info


    def _sub_flight_search(self, http_session, search_info, from_airport, to_airport):

        os_verison = '12.0.{}'.format(random.randint(0, 4))
        app_version = '4.0.1'
        headers = {
            'Host': 'mobileapi.xiamenair.com',
            'TO': 'C9DA503E91D640A2BF0FC301{}'.format(''.join([random.choice(string.uppercase) for i in xrange(8)])),
            'X-Tingyun-Id': 'cfQjS{};c=2;r=2059105928'.format(
                ''.join([random.choice(string.lowercase) for i in xrange(6)])),
            'OV': os_verison,
            'Accept': 'application/json',
            'plat': 'APP',
            'Content-Encoding': 'gzip',
            'OS': 'ios',
            'Accept-Language': 'en-CN;q=1, zh-Hans-CN;q=0.9',
            'Accept-Encoding': 'br, gzip, deflate',
            'Content-Type': 'application/json;charset=utf-8',
            'CH': 'appstore',
            'User-Agent': 'EgretFly/{} (iPhone; iOS {}; Scale/2.00)'.format(app_version, os_verison),
            'x-auth-token': 'cc7de964-c81c-43da-a572-0066{}'.format(random.randint(10000000, 99999999)),
            'PL': 'iphone',
            'Connection': 'keep-alive',
            'AV': app_version,
        }

        http_session.update_headers(headers)

        post_data = {
            "itineraries": [{
                "destination": {
                    "airport": {
                        "code": to_airport,
                    }
                },
                "departureDate": search_info.from_date,
                "origin": {
                    "airport": {
                        "code": from_airport,
                    }
                }
            }],
            "preBusiness": "0",
            "cabinClasses": ["Economy", "Business", "First"],
            "shoppingPreference": {
                "connectionPreference": {
                    "maxConnectionQuantity": 2
                },
                "flightPreference": {
                    "cabinCombineMode": "Cabin",
                    "lowestFare": True
                }
            },
            "passengerCount": {
                "adult": search_info.adt_count,
                "child": search_info.chd_count,
            },
            "dOrI": "I"
        }

        if search_info.trip_type == 'RT':
            post_data['itineraries'].append({
                "destination": {
                    "airport": {
                        "code": from_airport,
                    }
                },
                "departureDate": search_info.ret_date,
                "origin": {
                    "airport": {
                        "code": to_airport,
                    }
                }
            })

        url = 'https://mobileapi.xiamenair.com/mobile-starter/api/v1/Offer/shopping?preBusiness=0&type=I'
        result = http_session.request(url=url, method='POST', json=post_data, proxy_pool='A')

        try:
            result = json.loads(result.content)
        except:
            self.high_req_limit = True
            Logger().error(result)
            raise FlightSearchException(err_code='HIGH_REQ_LIMIT')

        if result['code'] == 0 and result['errStr'] == 'NO_OFFER_FOR_YOUR_REQUEST':
            Logger().warn('xiamenair no flight')
            self.search_success = True
            return search_info
        elif result['code'] == 0 and result['data'].get('exData') and result['data']['exData'].get('code') and result['data']['exData']['code'] == 400:
            Logger().warn('xiamenair no flight')
            self.search_success = True
            return search_info
        elif not result['code'] == 1:
            self.high_req_limit = True
            Logger().error(result)
            raise FlightSearchException(err_code='HIGH_REQ_LIMIT')

        from_line = '{}-{}'.format(from_airport, to_airport)
        ret_line = '{}-{}'.format(to_airport, from_airport)
        all_line = [from_line]
        if search_info.trip_type == 'RT':
            all_line.append(ret_line)
        all_line = ','.join(all_line)
        routing_list = result['data']['odData'][all_line]

        if not routing_list:
            Logger().warn('xiamenair no flight')
            self.search_success = True
            return search_info

        cabin_grade_map = {
            'Economy': 'Y',
            'Business': 'C',
            'First': 'F',
        }

        for routing in routing_list:
            cabin_list = routing['offers']['[ADT1]']
            for cabin in cabin_list:
                flight_routing = FlightRoutingInfo()
                flight_routing.product_type = 'DEFAULT'
                routing_number = 1
                is_include_operation_carrier = 0

                from_seg_list = routing['segments'][from_line]
                ret_seg_list = routing['segments'][ret_line] if search_info.trip_type == 'RT' else []
                for index, seg in enumerate(from_seg_list):
                    flight_segment = FlightSegmentInfo()
                    flight_segment.carrier = seg['marketingCarrier']['carrier']['code']
                    if not seg['operatingCarrier']['carrier']['code'] == seg['marketingCarrier']['carrier']['code']:
                        is_include_operation_carrier = 1
                    dep_time = datetime.datetime.strptime(seg['departure']['aircraftScheduledDateTime'],
                                                          '%Y-%m-%dT%H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
                    arr_time = datetime.datetime.strptime(seg['arrival']['aircraftScheduledDateTime'],
                                                          '%Y-%m-%dT%H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
                    flight_segment.dep_airport = seg['departure']['iataLocationCode']
                    flight_segment.dep_time = dep_time
                    flight_segment.arr_airport = seg['arrival']['iataLocationCode']
                    flight_segment.arr_time = arr_time
                    flight_segment.flight_number = '{}{}'.format(seg['marketingCarrier']['carrier']['code'],
                                                                 seg['marketingCarrier']['flightNumber'])
                    flight_segment.dep_terminal = seg['departure']['terminalName'] if seg['departure'].get('terminalName') else ''
                    flight_segment.arr_terminal = seg['arrival']['terminalName'] if seg['arrival'].get('terminalName') else ''

                    if seg.get('flightLegs'):
                        stop_list = []
                        for stop in seg['flightLegs']:
                            if stop['arrival']['iataLocationCode'] not in from_line:
                                stop_list.append(stop['arrival']['iataLocationCode'])
                        flight_segment.stop_airports = '/'.join(stop_list)

                    flight_segment.cabin = cabin['paxSegments'][from_line][index]['sellingClass']['code']
                    flight_segment.cabin_grade = cabin_grade_map[cabin['paxSegments'][from_line][index]['sellingClass']['cabinType']] \
                        if cabin_grade_map.get(
                        cabin['paxSegments'][from_line][index]['sellingClass']['cabinType']) else 'Y'
                    flight_segment.cabin_count = int(cabin['items'][0]['inventory']) if not cabin['items'][0]['inventory'] == 'A' else 9
                    segment_duration = (datetime.datetime.strptime(arr_time, '%Y-%m-%d %H:%M:%S') -
                                        datetime.datetime.strptime(dep_time, '%Y-%m-%d %H:%M:%S')).total_seconds()
                    flight_segment.duration = int(segment_duration / 60)
                    flight_segment.routing_number = routing_number
                    try:
                        if cabin.get('baggageAllowances'):
                            flight_segment.baggage_info = json.dumps({
                                'baggage_pc': cabin['baggageAllowances'][0]['pieceAllowances'][0]['totalQty'],
                                'baggage_kg': cabin['baggageAllowances'][0]['pieceAllowances'][0]['weightAllowances'][0]['value'],
                            })
                    except:
                        pass

                    routing_number += 1
                    flight_routing.from_segments.append(flight_segment)

                for index, seg in enumerate(ret_seg_list):
                    flight_segment = FlightSegmentInfo()
                    flight_segment.carrier = seg['marketingCarrier']['carrier']['code']
                    if not seg['operatingCarrier']['carrier']['code'] == seg['marketingCarrier']['carrier']['code']:
                        is_include_operation_carrier = 1
                    dep_time = datetime.datetime.strptime(seg['departure']['aircraftScheduledDateTime'],
                                                          '%Y-%m-%dT%H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
                    arr_time = datetime.datetime.strptime(seg['arrival']['aircraftScheduledDateTime'],
                                                          '%Y-%m-%dT%H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
                    flight_segment.dep_airport = seg['departure']['iataLocationCode']
                    flight_segment.dep_time = dep_time
                    flight_segment.arr_airport = seg['arrival']['iataLocationCode']
                    flight_segment.arr_time = arr_time
                    flight_segment.flight_number = '{}{}'.format(seg['marketingCarrier']['carrier']['code'],
                                                                 seg['marketingCarrier']['flightNumber'])
                    flight_segment.dep_terminal = seg['departure']['terminalName'] if seg['departure'].get(
                        'terminalName') else ''
                    flight_segment.arr_terminal = seg['arrival']['terminalName'] if seg['arrival'].get(
                        'terminalName') else ''

                    if seg.get('flightLegs'):
                        stop_list = []
                        for stop in seg['flightLegs']:
                            if stop['arrival']['iataLocationCode'] not in ret_line:
                                stop_list.append(stop['arrival']['iataLocationCode'])
                        flight_segment.stop_airports = '/'.join(stop_list)

                    flight_segment.cabin = cabin['paxSegments'][ret_line][index]['sellingClass']['code']
                    flight_segment.cabin_grade = cabin_grade_map[cabin['paxSegments'][ret_line][index]['sellingClass']['cabinType']] \
                        if cabin_grade_map.get(
                        cabin['paxSegments'][ret_line][index]['sellingClass']['cabinType']) else 'Y'
                    flight_segment.cabin_count = int(cabin['items'][0]['inventory']) if not cabin['items'][0]['inventory'] == 'A' else 9
                    segment_duration = (datetime.datetime.strptime(arr_time, '%Y-%m-%d %H:%M:%S') -
                                        datetime.datetime.strptime(dep_time, '%Y-%m-%d %H:%M:%S')).total_seconds()
                    flight_segment.duration = int(segment_duration / 60)
                    flight_segment.routing_number = routing_number

                    try:
                        if cabin.get('baggageAllowances'):
                            flight_segment.baggage_info = json.dumps({
                                'baggage_pc': cabin['baggageAllowances'][0]['pieceAllowances'][0]['totalQty'],
                                'baggage_kg': cabin['baggageAllowances'][0]['pieceAllowances'][0]['weightAllowances'][0]['value'],
                            })
                    except:
                        pass

                    routing_number += 1
                    flight_routing.ret_segments.append(flight_segment)

                flight_routing.adult_price = cabin['items'][0]['price']['baseAmount']
                flight_routing.adult_tax = cabin['items'][0]['price']['taxSummary']['totalAmount']
                flight_routing.child_price = flight_routing.adult_price
                flight_routing.child_tax = flight_routing.adult_tax

                if routing['offers'].get('[CHD1]'):
                    chd_cabin_list = routing['offers']['[CHD1]']
                    for chd_cabin in chd_cabin_list:
                        chd_from_seg_list = chd_cabin['paxSegments'][from_line]
                        all_match = True
                        for index, seg in enumerate(chd_from_seg_list):
                            if not seg['sellingClass']['code'] == flight_routing.from_segments[index].cabin:
                                all_match = False
                                break
                        if all_match:
                            flight_routing.child_price = chd_cabin['items'][0]['price']['baseAmount']
                            flight_routing.child_tax = chd_cabin['items'][0]['price']['taxSummary']['totalAmount']
                            break

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
                                               is_include_operation_carrier=is_include_operation_carrier,
                                               is_multi_segments=1 if len(flight_routing.from_segments) > 1 or flight_routing.ret_segments else 0
                                               )

                flight_routing.routing_key_detail = rk_info['plain']
                flight_routing.routing_key = rk_info['encrypted']

                self.product_list.append(flight_routing)

        self.search_success = True
