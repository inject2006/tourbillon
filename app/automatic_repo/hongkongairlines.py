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
import hmac
from .base import ProvderAutoBase
from ..dao.internal import *
from ..utils.util import simple_encrypt, Random,RoutingKey, simple_decrypt
from ..controller.captcha import CaptchaCracker
from app import TBG
from Crypto.Cipher import AES
from pony.orm import select, db_session
from lxml import etree
from ..controller.smser import Smser


class HongKongAirlines(ProvderAutoBase):
    timeout = 50  # 请求超时时间
    provider = 'HX_PROVIDER'  # 子类继承必须赋
    provider_channel = 'HX_PROVIDER_APP'  # 子类继承必须赋
    operation_product_type = '会员折扣'  # 运价类型：0: GDS公布运价 1:GDS私有运价 2:航司官网产品  3:廉价航司产品 4:特价产品
    operation_product_mode = 'A2B'
    pay_channel = 'ALIPAY'
    provider_token = '5e7ba8bddd7b9648'
    is_display = True
    trip_type_list = ['OW', 'RT']
    no_flight_ttl = 3600 * 3 # 无航班缓存超时时间设定
    carrier_list = ['HX']  # 供应商所包含的航司列表，如果包含多个并且无法确定，请不要填写，此处会关联执飞航线判断逻辑


    CACHE_PR_CONFIG = {
        1: {'cabin_expired_time': 60 * 10, 'cabin_attenuation': 3,'fare_expired_time':86400 * 30},
        2: {'cabin_expired_time': 60 * 10, 'cabin_attenuation': 2,'fare_expired_time':86400 * 20},
        3: {'cabin_expired_time': 60 * 5, 'cabin_attenuation': 1,'fare_expired_time':86400 * 10},
        4: {'cabin_expired_time': 60 * 5, 'cabin_attenuation': 1,'fare_expired_time':86400 * 5},
        5: {'cabin_expired_time': 60 * 5, 'cabin_attenuation': 0,'fare_expired_time':86400},

    }
    search_interval_time = 0.1

    def __init__(self):
        super(HongKongAirlines, self).__init__()

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
            Logger().sdebug('hongkongair no flight')
            return search_info
        search_info.assoc_search_routings.extend(self.product_list)
        return search_info


    def _sub_flight_search(self, http_session, search_info, from_airport, to_airport):

        os_version = '{}.{}.{}'.format(random.randint(6, 8), random.randint(0, 3), random.randint(0, 10))
        os_dm = 'OS{}'.format(random.randint(100, 110))
        os_mi = 'NMA6e0f13d5e4924807a544a41a{}'.format(random.randint(10000000, 99999999))

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Host': 'aio.hkairlines.com',
            'Connection': 'Keep-Alive',
            'User-Agent': 'Mozilla/5.0 (Linux; U; Android {}; zh-cn; {} Build/NGI77B) AppleWebKit/{}.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/{}.1'.format(
                os_version, os_dm, random.randint(500, 600), random.randint(500, 600)),
            'Cookie2': '$Version=1',
            'Accept-Encoding': 'gzip',
        }

        http_session.update_headers(headers)

        search_person_count = search_info.adt_count + search_info.chd_count if search_info.adt_count + search_info.chd_count >=3 else 3
        search_child_count = 0

        if search_info.flight_order_id:
            search_person_count = search_info.adt_count
            search_child_count = search_info.chd_count

        origin_post_data = [
            'bi.envs={}'.format('0'),
            'ai.cc={}'.format('2001'),
            'ai.cp={}'.format('2b504aadcc87a325fe190566d96257c0'),
            'ai.store={}'.format('hwsd'),
            'bi.mi={}'.format(os_mi),
            'bi.mFlag={}'.format('01'),
            'bi.ctoken={}'.format(os_mi),
            'bi.dv={}'.format('Android'),
            'bi.ctype={}'.format('app'),
            'bi.lan={}'.format('CN'),
            'bi.ov={}'.format(os_version),
            'bi.dm={}'.format(os_dm),
            'bi.dn={}'.format('SMARTISAN {}'.format(os_dm)),
            'bi.cl={}'.format(
                '({}.{}548,{}.{}715)'.format(random.randint(100, 300), random.randint(300, 600), random.randint(30, 50),
                                             random.randint(300, 600))),
            'bi.cln={}'.format(random.choice(['上海', '北京', '广州', '深圳'])),
            'bi.av={}'.format('7.0.5'),
            'bi.sid={}'.format('d954cabc373aa206e4fac5920e{}'.format(random.randint(100000, 999999))),
            'bi.res={}'.format('1080×2070'),
            'bi.pid={}'.format('866341232350606d{}'.format(random.randint(100000, 999999))),
            'bi.aid={}'.format('329ce9afc3daf214d4de709af0{}'.format(random.randint(100000, 999999))),
            'bi.net={}'.format('WIFI'),
            'orgCity={}'.format(from_airport),
            'dstCity={}'.format(to_airport),
            'tripType={}'.format(search_info.trip_type),
            'takeoffDate={}'.format(search_info.from_date),
            'seatClass={}'.format('Y'),
            'adultNum={}'.format(search_person_count),
            'childNum={}'.format(search_child_count),
            'currencyType={}'.format('CNY'),
        ]

        if search_info.trip_type == 'RT':
            origin_post_data.append('returnDate={}'.format(search_info.ret_date))

        sign_data = '&'.join(sorted(origin_post_data)) + '&'
        sign = base64.b64encode(hmac.new('609999462b15464013cd74f475e8a57ddcd9a74a', sign_data, hashlib.sha1).digest())

        post_data = {}
        for d in origin_post_data:
            post_data[d.split('=')[0]] = d.split('=')[1]

        post_data['sign'] = sign

        url = 'https://aio.hkairlines.com/ac3s/openjaw/flight/query'
        Logger().debug("====== search post data:{}".format(post_data))
        result = http_session.request(url=url, method='POST', data=post_data, verify=False)
        Logger().debug("====== search result: {}".format(result.content))

        try:
            result = json.loads(result.content)
        except:
            self.high_req_limit = True
            raise FlightSearchException(err_code='HIGH_REQ_LIMIT')

        if result['code'] == 'CWIP-0000':
            Logger().sdebug('hongkongair no flight')
            self.search_success = True
            return search_info
        elif not result['code'] == '1000':
            self.high_req_limit = True
            raise FlightSearchException(err_code='HIGH_REQ_LIMIT')

        routing_list = []
        for r in result['oJPricedItineraries']['groupsList']:
            routing_list.extend(r['oJPricedItineraryList'])

        if not routing_list:
            Logger().sdebug('hongkongair no flight')
            self.search_success = True
            return search_info

        for routing in routing_list:
            for cabin in routing['oJAirItineraryPricingInfoList']:
                flight_routing = FlightRoutingInfo()
                flight_routing.product_type = 'DEFAULT'
                routing_number = 1
                is_include_operation_carrier = 0

                from_seg_list = routing['oJAirItinerary']['oJOriginDestinationOptions']['oJOriginDestinationOptionList'][0]['oJFlightSegmentList']
                ret_seg_list = routing['oJAirItinerary']['oJOriginDestinationOptions']['oJOriginDestinationOptionList'][1]['oJFlightSegmentList'] \
                    if search_info.trip_type == 'RT' else []
                for index, seg in enumerate(from_seg_list):
                    flight_segment = FlightSegmentInfo()
                    flight_segment.carrier = seg['oJMarketingAirline']['code']
                    if seg.get('shareAirLine'):
                        is_include_operation_carrier = 1
                    dep_time = datetime.datetime.strptime(seg['departureDateTime'],
                                                          '%Y-%m-%dT%H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
                    arr_time = datetime.datetime.strptime(seg['arrivalDateTime'],
                                                          '%Y-%m-%dT%H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
                    flight_segment.dep_airport = seg['oJDepartureAirport']['locationCode']
                    flight_segment.dep_time = dep_time
                    flight_segment.arr_airport = seg['oJArrivalAirport']['locationCode']
                    flight_segment.arr_time = arr_time
                    flight_segment.flight_number = '{}{}'.format(seg['oJMarketingAirline']['code'],
                                                                 seg['flightNumber'])
                    flight_segment.dep_terminal = seg['oJDepartureAirport']['terminal'] \
                        if seg['oJDepartureAirport'].get('terminal') else ''
                    flight_segment.arr_terminal = seg['oJArrivalAirport']['terminal'] \
                        if seg['oJArrivalAirport'].get('terminal') else ''

                    flight_segment.cabin = cabin['oJFareInfos']['oJFareInfoList'][routing_number - 1]['oJFareReference']['resBookDesigCode']
                    flight_segment.cabin_grade = cabin['oJFareInfos']['oJFareInfoList'][routing_number - 1]['oJFareReference']['cabinCode']
                    flight_segment.cabin_count = 9 if not cabin['oJFareInfos']['oJFareInfoList'][routing_number - 1]['oJFareReference']['cabinNo'] == u'少量余票' else 3
                    segment_duration = (datetime.datetime.strptime(arr_time, '%Y-%m-%d %H:%M:%S') -
                                        datetime.datetime.strptime(dep_time, '%Y-%m-%d %H:%M:%S')).total_seconds()
                    flight_segment.duration = int(segment_duration / 60)
                    flight_segment.routing_number = routing_number

                    routing_number += 1
                    flight_routing.from_segments.append(flight_segment)

                for index, seg in enumerate(ret_seg_list):
                    flight_segment = FlightSegmentInfo()
                    flight_segment.carrier = seg['oJMarketingAirline']['code']
                    if seg.get('shareAirLine'):
                        is_include_operation_carrier = 1
                    dep_time = datetime.datetime.strptime(seg['departureDateTime'],
                                                          '%Y-%m-%dT%H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
                    arr_time = datetime.datetime.strptime(seg['arrivalDateTime'],
                                                          '%Y-%m-%dT%H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
                    flight_segment.dep_airport = seg['oJDepartureAirport']['locationCode']
                    flight_segment.dep_time = dep_time
                    flight_segment.arr_airport = seg['oJArrivalAirport']['locationCode']
                    flight_segment.arr_time = arr_time
                    flight_segment.flight_number = '{}{}'.format(seg['oJMarketingAirline']['code'],
                                                                 seg['flightNumber'])
                    flight_segment.dep_terminal = seg['oJDepartureAirport']['terminal'] \
                        if seg['oJDepartureAirport'].get('terminal') else ''
                    flight_segment.arr_terminal = seg['oJArrivalAirport']['terminal'] \
                        if seg['oJArrivalAirport'].get('terminal') else ''

                    flight_segment.cabin = cabin['oJFareInfos']['oJFareInfoList'][routing_number - 1]['oJFareReference']['resBookDesigCode']
                    flight_segment.cabin_grade = cabin['oJFareInfos']['oJFareInfoList'][routing_number - 1]['oJFareReference']['cabinCode']
                    flight_segment.cabin_count = 9 if not cabin['oJFareInfos']['oJFareInfoList'][routing_number - 1]['oJFareReference']['cabinNo'] == u'少量余票' else 3
                    segment_duration = (datetime.datetime.strptime(arr_time, '%Y-%m-%d %H:%M:%S') -
                                        datetime.datetime.strptime(dep_time, '%Y-%m-%d %H:%M:%S')).total_seconds()
                    flight_segment.duration = int(segment_duration / 60)
                    flight_segment.routing_number = routing_number

                    routing_number += 1
                    flight_routing.ret_segments.append(flight_segment)

                flight_routing.adult_price = float(cabin['oJItinTotalFare']['oJBaseFare']['amount']) / search_person_count
                total_tax = 0.0
                for t in cabin['oJItinTotalFare']['oJTaxes']:
                    total_tax += float(cabin['oJItinTotalFare']['oJTaxes'][t]['amount'])
                flight_routing.adult_tax = total_tax / search_person_count
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
                                               is_include_operation_carrier=is_include_operation_carrier,
                                               is_multi_segments=1 if len(flight_routing.from_segments) > 1 or flight_routing.ret_segments else 0
                                               )

                flight_routing.routing_key_detail = rk_info['plain']
                flight_routing.routing_key = rk_info['encrypted']
                flight_routing.sequence_number = routing['sequenceNumber']
                flight_routing.fare_family_code = cabin['farefamilyCode']
                flight_routing.from_airport = from_airport
                flight_routing.to_airport = to_airport


                self.product_list.append(flight_routing)

        self.search_success = True


    def _booking(self, http_session, order_info):

        order_info.provider_order_status = 'BOOK_FAIL'
        search_result = self.flight_search(http_session, order_info, cache_mode='REALTIME')

        for routing in search_result.assoc_search_routings:
            # Logger().debug(routing)
            if RoutingKey.trans_cp_key(simple_decrypt(routing.routing_key)) == RoutingKey.trans_cp_key(
                simple_decrypt(order_info.routing.routing_key)):
                order_info.routing = routing
                break
        if not order_info.routing.sequence_number or not order_info.routing.fare_family_code:
            raise BookingException('hx sequence number not found')

        os_version = '{}.{}.{}'.format(random.randint(6, 8), random.randint(0, 3), random.randint(0, 10))
        os_dm = 'OS{}'.format(random.randint(100, 110))
        os_mi = 'NMA6e0f13d5e4924807a544a41a{}'.format(random.randint(10000000, 99999999))

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Host': 'aio.hkairlines.com',
            'Connection': 'Keep-Alive',
            'User-Agent': 'Mozilla/5.0 (Linux; U; Android {}; zh-cn; {} Build/NGI77B) AppleWebKit/{}.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/{}.1'.format(
                os_version, os_dm, random.randint(500, 600), random.randint(500, 600)),
            'Cookie2': '$Version=1',
            'Accept-Encoding': 'gzip',
        }

        http_session.update_headers(headers)

        origin_post_data = [
            'bi.envs={}'.format('0'),
            'ai.cc={}'.format('2001'),
            'ai.cp={}'.format('2b504aadcc87a325fe190566d96257c0'),
            'ai.store={}'.format('hwsd'),
            'bi.mi={}'.format(os_mi),
            'bi.mFlag={}'.format('01'),
            'bi.ctoken={}'.format(os_mi),
            'bi.dv={}'.format('Android'),
            'bi.ctype={}'.format('app'),
            'bi.lan={}'.format('CN'),
            'bi.ov={}'.format(os_version),
            'bi.dm={}'.format(os_dm),
            'bi.dn={}'.format('SMARTISAN {}'.format(os_dm)),
            'bi.cl={}'.format(
                '({}.{}548,{}.{}715)'.format(random.randint(100, 300), random.randint(300, 600), random.randint(30, 50),
                                             random.randint(300, 600))),
            'bi.cln={}'.format(random.choice(['上海', '北京', '广州', '深圳'])),
            'bi.av={}'.format('7.0.5'),
            'bi.sid={}'.format('d954cabc373aa206e4fac5920e{}'.format(random.randint(100000, 999999))),
            'bi.res={}'.format('1080×2070'),
            'bi.pid={}'.format('866341232350606d{}'.format(random.randint(100000, 999999))),
            'bi.aid={}'.format('329ce9afc3daf214d4de709af0{}'.format(random.randint(100000, 999999))),
            'bi.net={}'.format('WIFI'),
            'orgCity={}'.format(order_info.routing.from_airport),
            'dstCity={}'.format(order_info.routing.to_airport),
            'tripType={}'.format(order_info.trip_type),
            'takeoffDate={}'.format(order_info.from_date),
            'seatClass={}'.format('Y'),
            'adultNum={}'.format(order_info.adt_count),
            'childNum={}'.format(order_info.chd_count),
            'sequenceNumber={}'.format(order_info.routing.sequence_number),
            'farefamilyCode={}'.format(order_info.routing.fare_family_code),
            'currencyType={}'.format('CNY'),
        ]

        if order_info.trip_type == 'RT':
            origin_post_data.append('returnDate={}'.format(order_info.ret_date))

        sign_data = '&'.join(sorted(origin_post_data)) + '&'
        sign = base64.b64encode(hmac.new('609999462b15464013cd74f475e8a57ddcd9a74a', sign_data, hashlib.sha1).digest())

        post_data = {}
        for d in origin_post_data:
            post_data[d.split('=')[0]] = d.split('=')[1]

        post_data['sign'] = sign

        url = 'https://aio.hkairlines.com/ac3s/openjaw/flight/confirm'
        Logger().info("======== hx confirm flight post data: {}".format(post_data))
        result = http_session.request(url=url, method='POST', data=post_data, verify=False)
        Logger().info("========== hx confirm flight result : {}".format(result.content))

        result = result.to_json()

        if not result['code'] == '1000':
            raise BookingException('hx confirm flight error')

        unique_code = result['uniqueCode']
        flight_no_list = []

        for seg in order_info.routing.from_segments:
            flight_no_list.append(seg.flight_number)
        for seg in order_info.routing.ret_segments:
            flight_no_list.append(seg.flight_number)

        flight_no_str = ';'.format(['{},{}'.format(f[: 2], f[2: ]) for f in flight_no_list])

        contact = order_info.contacts[0]
        origin_post_data.extend([
                'uniqueCode={}'.format(unique_code),
                'isAgreewithAdv=N',
                'isTransit=false',
                'insuranceBuyOpt=0',
                'orderInfo.contactName={}'.format(contact.name),
                'orderInfo.contactMobile={}'.format(TBG.global_config['OPERATION_CONTACT_MOBILE']),
                'orderInfo.contactPhone={}'.format(TBG.global_config['OPERATION_CONTACT_MOBILE']),
                'orderInfo.contactEmail={}'.format(TBG.global_config['OPERATION_CONTACT_EMAIL']),
                'orderInfo.countryCode={}'.format('+86'),
                'orderInfo.currencyCode={}'.format('CNY'),
                'orderInfo.promotion={}'.format('0'),
                'autoCheckFlag={}'.format('1'),
                'isMessage={}'.format('0'),
                'carryFltNo={}'.format(flight_no_str),
        ])

        for index, p in enumerate(order_info.passengers):
            origin_post_data.extend([
                'passengers[{}].lastName={}'.format(index, p.last_name),
                'passengers[{}].firstName={}'.format(index, p.first_name),
                'passengers[{}].birthday={}'.format(index, p.birthdate),
                'passengers[{}].passengerType={}'.format(index, '0' if p.current_age_type() == 'ADT' else '1'),
                'passengers[{}].gender={}'.format(index, p.gender),
                'passengers[{}].idType={}'.format(index, '1'),
                'passengers[{}].idNo={}'.format(index, p.selected_card_no),
                'passengers[{}].effectiveDate={}'.format(index, '2013-11-11'),
                'passengers[{}].expirationDate={}'.format(index, p.card_expired),
                'passengers[{}].nationality={}'.format(index, p.nationality),
                'passengers[{}].docIssueLocation={}'.format(index, p.card_issue_place),
            ])

        sign_data = '&'.join(sorted(origin_post_data)) + '&'
        sign = base64.b64encode(hmac.new('609999462b15464013cd74f475e8a57ddcd9a74a', sign_data, hashlib.sha1).digest())

        post_data = {}
        for d in origin_post_data:
            post_data[d.split('=')[0]] = d.split('=')[1]

        post_data['sign'] = sign
        url = 'https://aio.hkairlines.com/ac3s/openjaw/flight/addOrder'
        Logger().info("======== hx order post data: {}".format(post_data))
        result = http_session.request(url=url, method='POST', data=post_data, verify=False).content
        Logger().info("========== hx order result : {}".format(result))
        result = json.loads(result)

        if not result['code'] == '1000':
            raise BookingException('add order error')

        order_info.provider_order_id = result['orderInfo']['orderNum']
        order_info.provider_price = result['orderInfo']['totalPrice']
        order_info.provider_order_status = 'BOOK_SUCCESS_AND_WAITING_PAY'
        Logger().info('booking success')
        return order_info


    def _check_order_status(self, http_session, ffp_account_info, order_info):

        os_version = '{}.{}.{}'.format(random.randint(6, 8), random.randint(0, 3), random.randint(0, 10))
        os_dm = 'OS{}'.format(random.randint(100, 110))
        os_mi = 'NMA6e0f13d5e4924807a544a41a{}'.format(random.randint(10000000, 99999999))

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Host': 'aio.hkairlines.com',
            'Connection': 'Keep-Alive',
            'User-Agent': 'Mozilla/5.0 (Linux; U; Android {}; zh-cn; {} Build/NGI77B) AppleWebKit/{}.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/{}.1'.format(
                os_version, os_dm, random.randint(500, 600), random.randint(500, 600)),
            'Cookie2': '$Version=1',
            'Accept-Encoding': 'gzip',
        }

        http_session.update_headers(headers)

        origin_post_data = [
            'bi.envs={}'.format('0'),
            'ai.cc={}'.format('2001'),
            'ai.cp={}'.format('2b504aadcc87a325fe190566d96257c0'),
            'ai.store={}'.format('hwsd'),
            'bi.mi={}'.format(os_mi),
            'bi.mFlag={}'.format('01'),
            'bi.ctoken={}'.format(os_mi),
            'bi.dv={}'.format('Android'),
            'bi.ctype={}'.format('app'),
            'bi.lan={}'.format('CN'),
            'bi.ov={}'.format(os_version),
            'bi.dm={}'.format(os_dm),
            'bi.dn={}'.format('SMARTISAN {}'.format(os_dm)),
            'bi.cl={}'.format(
                '({}.{}548,{}.{}715)'.format(random.randint(100, 300), random.randint(300, 600), random.randint(30, 50),
                                             random.randint(300, 600))),
            'bi.cln={}'.format(random.choice(['上海', '北京', '广州', '深圳'])),
            'bi.av={}'.format('7.0.5'),
            'bi.sid={}'.format('d954cabc373aa206e4fac5920e{}'.format(random.randint(100000, 999999))),
            'bi.res={}'.format('1080×2070'),
            'bi.pid={}'.format('866341232350606d{}'.format(random.randint(100000, 999999))),
            'bi.aid={}'.format('329ce9afc3daf214d4de709af0{}'.format(random.randint(100000, 999999))),
            'bi.net={}'.format('WIFI'),
            'orderNum={}'.format(order_info.provider_order_id),
        ]

        sign_data = '&'.join(sorted(origin_post_data)) + '&'
        sign = base64.b64encode(hmac.new('609999462b15464013cd74f475e8a57ddcd9a74a', sign_data, hashlib.sha1).digest())

        post_data = {}
        for d in origin_post_data:
            post_data[d.split('=')[0]] = d.split('=')[1]

        post_data['sign'] = sign
        url = 'https://aio.hkairlines.com/ac3s/openjaw/order/searchOrderDetailNew'
        Logger().info("======== hx check order status post data: {}".format(post_data))
        result = http_session.request(url=url, method='POST', data=post_data, verify=False).to_json()
        Logger().info("========== hx check order status result : {}".format(result))

        if result['code'] == '1000':
            if result['order']["orderStatus"] == '00' and result['order']['payStatus'] == '0':
                order_info.provider_order_status = 'BOOK_SUCCESS_AND_WAITING_PAY'
            elif result['order']['payStatus'] == '1' and result['order']['orderStatus'] == '02':
                issue_success = False
                for p in result['passengers']:
                    for pax_info in order_info.passengers:
                        if p['certNo'] == pax_info.selected_card_no and p.get('tktNum'):
                            pax_info.ticket_no = p['tktNum']
                            issue_success = True
                if issue_success:
                    order_info.provider_order_status = 'ISSUE_SUCCESS'
            elif result['order']['payStatus'] == '1':
                order_info.provider_order_status = 'PAY_SUCCESS'


    def _pay(self, order_info=None, http_session=None, pay_dict={}):

        os_version = '{}.{}.{}'.format(random.randint(6, 8), random.randint(0, 3), random.randint(0, 10))
        os_dm = 'OS{}'.format(random.randint(100, 110))
        os_mi = 'NMA6e0f13d5e4924807a544a41a{}'.format(random.randint(10000000, 99999999))

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Host': 'aio.hkairlines.com',
            'Connection': 'Keep-Alive',
            'User-Agent': 'Mozilla/5.0 (Linux; U; Android {}; zh-cn; {} Build/NGI77B) AppleWebKit/{}.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/{}.1'.format(
                os_version, os_dm, random.randint(500, 600), random.randint(500, 600)),
            'Cookie2': '$Version=1',
            'Accept-Encoding': 'gzip',
        }

        http_session.update_headers(headers)

        origin_post_data = [
            'bi.envs={}'.format('0'),
            'ai.cc={}'.format('2001'),
            'ai.cp={}'.format('2b504aadcc87a325fe190566d96257c0'),
            'ai.store={}'.format('hwsd'),
            'bi.mi={}'.format(os_mi),
            'bi.mFlag={}'.format('01'),
            'bi.ctoken={}'.format(os_mi),
            'bi.dv={}'.format('Android'),
            'bi.ctype={}'.format('app'),
            'bi.lan={}'.format('CN'),
            'bi.ov={}'.format(os_version),
            'bi.dm={}'.format(os_dm),
            'bi.dn={}'.format('SMARTISAN {}'.format(os_dm)),
            'bi.cl={}'.format(
                '({}.{}548,{}.{}715)'.format(random.randint(100, 300), random.randint(300, 600), random.randint(30, 50),
                                             random.randint(300, 600))),
            'bi.cln={}'.format(random.choice(['上海', '北京', '广州', '深圳'])),
            'bi.av={}'.format('7.0.5'),
            'bi.sid={}'.format('d954cabc373aa206e4fac5920e{}'.format(random.randint(100000, 999999))),
            'bi.res={}'.format('1080×2070'),
            'bi.pid={}'.format('866341232350606d{}'.format(random.randint(100000, 999999))),
            'bi.aid={}'.format('329ce9afc3daf214d4de709af0{}'.format(random.randint(100000, 999999))),
            'bi.net={}'.format('WIFI'),
            'orderNum={}'.format(order_info.provider_order_id),
        ]

        sign_data = '&'.join(sorted(origin_post_data)) + '&'
        sign = base64.b64encode(hmac.new('609999462b15464013cd74f475e8a57ddcd9a74a', sign_data, hashlib.sha1).digest())

        post_data = {}
        for d in origin_post_data:
            post_data[d.split('=')[0]] = d.split('=')[1]

        post_data['sign'] = sign
        url = 'https://aio.hkairlines.com/ac3s/flight/paymentOptions'
        Logger().info("======== hx pay option post data: {}".format(post_data))
        result = http_session.request(url=url, method='POST', data=post_data, verify=False).to_json()
        Logger().info("========== hx pay option result : {}".format(result))


        pay_channel = result['otherPayments']
        pay_url = None
        for c in pay_channel:
            if c['paymentChannel'] == '7':
                pay_url = c['url']

        if not pay_url:
            raise PayException('have no yeepay channel')
        customer_no = pay_url.split('/')[-2]
        customer_request_no = pay_url.split('/')[-1]


        origin_post_data.append('payBankId=7')

        sign_data = '&'.join(sorted(origin_post_data)) + '&'
        sign = base64.b64encode(hmac.new('609999462b15464013cd74f475e8a57ddcd9a74a', sign_data, hashlib.sha1).digest())

        post_data = {}
        for d in origin_post_data:
            post_data[d.split('=')[0]] = d.split('=')[1]

        post_data['sign'] = sign
        url = 'https://aio.hkairlines.com/ac3s/openjaw/flight/PaymentApply'
        Logger().info("======== hx pay apply post data: {}".format(post_data))
        result = http_session.request(url=url, method='POST', data=post_data, verify=False).to_json()
        Logger().info("========== hx pay apply result : {}".format(result))
        if not result.get('code') == '1000':
            raise PayException('hx pay apply error')

        headers = {
            'Host': 'cashdesk.yeepay.com',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 11_0 like Mac OS X) AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Mobile/15A372 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Referer': 'https://cashdesk.yeepay.com',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-GB,en;q=0.9,en-US;q=0.8,zh-CN;q=0.7,zh;q=0.6',
        }

        pay_url = 'https://cashdesk.yeepay.com/bc-cashier/bcnewwap/request?customerNo={}&customerRequestNo={}'.format(
            customer_no, customer_request_no)
        http_session.request(url=pay_url, method='GET', verify=False, headers=headers)

        time.sleep(0.5)

        pay_url = 'https://cashdesk.yeepay.com/bc-cashier/bcnewwap/request/first?customerNo={}&customerRequestNo={}'.format(
            customer_no, customer_request_no)
        http_session.request(url=pay_url, method='GET', verify=False, headers=headers)

        time.sleep(0.5)

        pay_source_info = pay_dict['lqw_c9337']
        post_data = {
                'cardNo': base64.b64encode(pay_source_info.credit_card_idno),
                'customerNo': customer_no,
                'customerRequestNo': customer_request_no,
        }

        url = 'https://cashdesk.yeepay.com/bc-cashier/bcnewwap/first/cardInfo'
        http_session.request(url=url, method='POST', data=post_data, verify=False, headers=headers)

        time.sleep(0.5)

        post_data = {
            'bankCode': 'BOC',
            'cardType': 'CREDIT',
            'bankName': '中国银行',
            'name': '',
            'idno': '',
            'pass': '',
            'customerRequestNo': customer_request_no,
            'customerNo': customer_no,
            'cardno': base64.b64encode(pay_source_info.credit_card_idno),
            'valid': base64.b64encode(pay_source_info.credit_card_validthru),
            'cvv2': base64.b64encode(pay_source_info.credit_card_cvv2),
            'phone': base64.b64encode(pay_source_info.reverse_mobile),
        }

        url = 'https://cashdesk.yeepay.com/bc-cashier/bcncpay/firstpay/confirm'

        result = http_session.request(url=url, method='POST', data=post_data, verify=False, headers=headers).to_json()
        Logger().info("================ yeepoy confirm result : {}".format(result))

        Logger().info('send mobile sms code success %s' % pay_source_info.reverse_mobile)
        sms_verify_codes = Smser().get_yeepay_verify_code(provider_price=order_info.provider_price)
        if sms_verify_codes:
            for sms_verify_code in sms_verify_codes:
                gevent.sleep(0.2)
                Logger().info('sms_verify_code %s' % sms_verify_code)
                post_data.update({
                    'token': result['token'],
                    'verifycode': sms_verify_code,
                })

                url = 'https://cashdesk.yeepay.com/bc-cashier/bcncpay/firstpay/smsBackFill'
                Logger().info("======= yeepoy mobile verify post data :{}".format(post_data))
                result = http_session.request(url=url, method='POST', data=post_data, verify=False, headers=headers).to_json()
                Logger().info("======== yeepoy mobile verify result:{}".format(result))

                if result['bizStatus'] == 'success':
                    order_info.out_trade_no = customer_request_no
                    return pay_dict['lqw_c9337']
                else:
                    raise PayException('sms verify error')
        else:
            raise PayException('yeepay get sms code error')



