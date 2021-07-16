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
from lxml import etree


class Airmacau(ProvderAutoBase):
    timeout = 50  # 请求超时时间
    provider = 'NX_PROVIDER'  # 子类继承必须赋
    provider_channel = 'NX_PROVIDER_WEB'  # 子类继承必须赋
    operation_product_type = '会员折扣'  # 运价类型：0: GDS公布运价 1:GDS私有运价 2:航司官网产品  3:廉价航司产品 4:特价产品
    operation_product_mode = 'A2B'
    pay_channel = 'ALIPAY'
    provider_token = '5e7ba8bddd7b9648'
    is_display = True
    trip_type_list = ['OW', 'RT']
    no_flight_ttl = 3600 * 3 # 无航班缓存超时时间设定
    carrier_list = ['NX']  # 供应商所包含的航司列表，如果包含多个并且无法确定，请不要填写，此处会关联执飞航线判断逻辑

    CACHE_PR_CONFIG = {
        1: {'cabin_expired_time': 60 * 10, 'cabin_attenuation': 3,'fare_expired_time':86400 * 30},
        2: {'cabin_expired_time': 60 * 10, 'cabin_attenuation': 2,'fare_expired_time':86400 * 20},
        3: {'cabin_expired_time': 60 * 5, 'cabin_attenuation': 1,'fare_expired_time':86400 * 10},
        4: {'cabin_expired_time': 60 * 5, 'cabin_attenuation': 1,'fare_expired_time':86400 * 5},
        5: {'cabin_expired_time': 60 * 5, 'cabin_attenuation': 0,'fare_expired_time':86400},

    }
    search_interval_time = 0.3

    def __init__(self):
        super(Airmacau, self).__init__()

    def get_did(self):

        # did 5分钟过期

        while True:
            did_info = TBG.redis_conn.redis_pool.rpop('airmacau_web_did')
            if not did_info:
                raise Exception('airmacau have no did')
            did, last_time = did_info.split('@')

            if datetime.datetime.now() - datetime.timedelta(seconds=60 * 5) > datetime.datetime.strptime(
                last_time, '%Y-%m-%d %H:%M:%S'):
                continue
            else:
                TBG.redis_conn.redis_pool.lpush('airmacau_web_did', did_info)
                return did

    def _flight_search(self, http_session, search_info):
        """
        航班爬取模块，
        TODO :目前只考虑单程
        :return:
        """

        Logger().debug('search flight')

        did = self.get_did()
        print "=============== did: {} ============".format(did)

        airmacau_airport_mapping = {
            'SEL': 'ICN',
            'TYO': 'NRT',
            'BJS': 'PEK',
            'OSA': 'KIX',
        }

        headers = {
            'Origin': 'https://ibe.airmacau.com.cn',
            'Host': 'ibe.airmacau.com.cn',
            'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_{}_{}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/{}.{}".format(
                random.randint(10, 99), random.randint(0, 9), random.randint(100, 999), random.randint(10, 99)),
            'Upgrade-Insecure-Requests': '1',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': 'https://ibe.airmacau.com.cn/cn/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',

        }

        if search_info.trip_type == 'RT':
            # 返程请求两次
            post_data = {
                'tripType': search_info.trip_type,
                'orgcity': airmacau_airport_mapping.get(search_info.from_airport, search_info.from_airport),
                'dstcity': airmacau_airport_mapping.get(search_info.to_airport, search_info.to_airport),
                'takeoffDate': search_info.from_date,
                'returnDate': search_info.ret_date,
                'tmp_takeoffDate': search_info.from_date,
                'tmp_returnDate': search_info.ret_date,
                'cabinType': 'ECONOMY',
                'adultCount': search_info.adt_count,
                'childCount': search_info.chd_count,
                'const_id': did,
                'lang': 'cn',
            }

            url = 'https://ibe.airmacau.com.cn/cn/ibe_date.php'
            result = http_session.request(url=url, method='POST', data=post_data, headers=headers, verify=False)
            html = etree.HTML(result.content)
            amt = html.xpath("//input[@id='amt_{}-{}']/@value".format(
                search_info.from_date.replace('-', ''), search_info.ret_date.replace('-', '')))[0]
            sid = html.xpath("//input[@id='sid_{}-{}']/@value".format(
                search_info.from_date.replace('-', ''), search_info.ret_date.replace('-', '')))[0]
            amt = amt.replace('CNY', '').replace(',', '').strip()

            time.sleep(1)

            post_data = {
                'tripType': search_info.trip_type,
                'orgcity': airmacau_airport_mapping.get(search_info.from_airport, search_info.from_airport),
                'dstcity': airmacau_airport_mapping.get(search_info.to_airport, search_info.to_airport),
                'takeoffDate': search_info.from_date,
                'returnDate': search_info.ret_date,
                'cabinType': 'ECONOMY',
                'adultCount': search_info.adt_count,
                'childCount': search_info.chd_count,
                'vipcode': '',
                'AMOUNT': amt,
                'SID': sid,
                'STARTTIME': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'const_id': did,
                'frompage': 'ibe_date.php',
            }

            url = 'https://ibe.airmacau.com.cn/cn/ibe_flight.php'
            result = http_session.request(url=url, method='POST', data=post_data, headers=headers, verify=False)

            if u'非合法请求'.encode('utf8') in result.content:
                raise FlightSearchException(err_code='HIGH_REQ_LIMIT')

            html = etree.HTML(result.content)
            data_list = []
            data_list.extend(html.xpath('//input[@name="E1s1res"]/@value'))
            data_list.extend(html.xpath('//input[@name="E2s1res"]/@value'))
            data_list.extend(html.xpath('//input[@name="E3s1res"]/@value'))
            data_list.extend(html.xpath('//input[@name="B3s1res"]/@value'))

            # Logger().info("====== search result:{} ==".format(data_list))

        else:
            # 单程请求一次
            post_data = {
                'tripType': search_info.trip_type,
                'orgcity': airmacau_airport_mapping.get(search_info.from_airport, search_info.from_airport),
                'dstcity': airmacau_airport_mapping.get(search_info.to_airport, search_info.to_airport),
                'takeoffDate': search_info.from_date,
                'tmp_takeoffDate': search_info.from_date,
                'tmp_returnDate': '',
                'cabinType': 'ECONOMY',
                'adultCount': search_info.adt_count,
                'childCount': search_info.chd_count,
                'const_id': did,
                'lang': 'cn',
            }

            url = 'https://ibe.airmacau.com.cn/cn/ibe_flight.php'
            result = http_session.request(url=url, method='POST', data=post_data, headers=headers, verify=False)

            if u'非合法请求'.encode('utf8') in result.content:
                raise FlightSearchException(err_code='HIGH_REQ_LIMIT')

            html = etree.HTML(result.content)
            data_list = []
            data_list.extend(html.xpath('//input[@name="E1s1res"]/@value'))
            data_list.extend(html.xpath('//input[@name="E2s1res"]/@value'))
            data_list.extend(html.xpath('//input[@name="E3s1res"]/@value'))
            data_list.extend(html.xpath('//input[@name="B3s1res"]/@value'))

            # Logger().info("====== search result:{} ==".format(data_list))

        search_info.origin_data_list = data_list

        for index, data in enumerate(data_list):
            origin_data = json.loads(data)
            routing_list = origin_data['result']['solutions']
            origin_seg_list = origin_data['result']['flights']

            flight_dict = {}
            for f in origin_seg_list:
                flight_dict[f['id']] = f

            for routing in routing_list:
                flight_routing = FlightRoutingInfo()
                flight_routing.product_type = 'DEFAULT'
                routing_number = 1
                from_seg_index_list = routing['requestSegments'][0]['flights']
                ret_seg_index_list = routing['requestSegments'][1]['flights'] if search_info.trip_type == 'RT' else []

                from_cabin_info = routing['tickets'][0]['fares'][0]['flights']
                ret_cabin_info = routing['tickets'][0]['fares'][1]['flights'] if search_info.trip_type == 'RT' else []

                is_include_operation_carrier = 0
                for i in from_seg_index_list:
                    from_seg = flight_dict[i]
                    flight_segment = FlightSegmentInfo()
                    flight_segment.carrier = from_seg['carrier'].strip()

                    operation_carrier = from_seg['operatingCarrier'].strip()
                    if not operation_carrier == 'NX':
                        is_include_operation_carrier = 1

                    dep_time = datetime.datetime.strptime(
                        str(from_seg['departureDate']['year']).zfill(4) + \
                        str(from_seg['departureDate']['month']).zfill(2) + \
                        str(from_seg['departureDate']['day']).zfill(2) + \
                        str(from_seg['departureTime']['hour']).zfill(2) + \
                        str(from_seg['departureTime']['minutes']).zfill(2),
                        '%Y%m%d%H%M').strftime('%Y-%m-%d %H:%M:%S')
                    arr_time = datetime.datetime.strptime(
                        str(from_seg['arrivalDate']['year']).zfill(4) + \
                        str(from_seg['arrivalDate']['month']).zfill(2) + \
                        str(from_seg['arrivalDate']['day']).zfill(2) + \
                        str(from_seg['arrivalTime']['hour']).zfill(2) + \
                        str(from_seg['arrivalTime']['minutes']).zfill(2),
                        '%Y%m%d%H%M').strftime('%Y-%m-%d %H:%M:%S')
                    flight_segment.dep_airport = from_seg['departureAirport'].strip()
                    flight_segment.dep_time = dep_time
                    flight_segment.arr_airport = from_seg['arrivalAirport'].strip()
                    flight_segment.arr_time = arr_time
                    flight_segment.flight_number = '{}{}'.format(flight_segment.carrier, from_seg['flightNumber'].strip())
                    flight_segment.dep_terminal = from_seg['departureTerminal'].strip()
                    flight_segment.arr_terminal = from_seg['arrivalTerminal'].strip()
                    seg_cabin_info = [c for c in from_cabin_info if c['flightId'] == i][0]
                    flight_segment.cabin = seg_cabin_info['passengers']['rbdInfos'][0]['rbd'].strip()
                    flight_segment.cabin_grade = seg_cabin_info['passengers']['cabin'].strip()
                    flight_segment.cabin_count = seg_cabin_info['passengers']['seats']
                    segment_duration = (datetime.datetime.strptime(arr_time, '%Y-%m-%d %H:%M:%S') -
                                        datetime.datetime.strptime(dep_time, '%Y-%m-%d %H:%M:%S')).total_seconds()
                    flight_segment.duration = int(segment_duration / 60)
                    flight_segment.routing_number = routing_number
                    routing_number += 1
                    flight_routing.from_segments.append(flight_segment)

                for i in ret_seg_index_list:
                    ret_seg = flight_dict[i]
                    flight_segment = FlightSegmentInfo()
                    flight_segment.carrier = ret_seg['carrier'].strip()

                    operation_carrier = ret_seg['operatingCarrier'].strip()
                    if not operation_carrier == 'NX':
                        is_include_operation_carrier = 1

                    dep_time = datetime.datetime.strptime(
                        str(ret_seg['departureDate']['year']).zfill(4) + \
                        str(ret_seg['departureDate']['month']).zfill(2) + \
                        str(ret_seg['departureDate']['day']).zfill(2) + \
                        str(ret_seg['departureTime']['hour']).zfill(2) + \
                        str(ret_seg['departureTime']['minutes']).zfill(2),
                        '%Y%m%d%H%M').strftime('%Y-%m-%d %H:%M:%S')
                    arr_time = datetime.datetime.strptime(
                        str(ret_seg['arrivalDate']['year']).zfill(4) + \
                        str(ret_seg['arrivalDate']['month']).zfill(2) + \
                        str(ret_seg['arrivalDate']['day']).zfill(2) + \
                        str(ret_seg['arrivalTime']['hour']).zfill(2) + \
                        str(ret_seg['arrivalTime']['minutes']).zfill(2),
                        '%Y%m%d%H%M').strftime('%Y-%m-%d %H:%M:%S')
                    flight_segment.dep_airport = ret_seg['departureAirport'].strip()
                    flight_segment.dep_time = dep_time
                    flight_segment.arr_airport = ret_seg['arrivalAirport'].strip()
                    flight_segment.arr_time = arr_time
                    flight_segment.flight_number = '{}{}'.format(flight_segment.carrier, ret_seg['flightNumber'].strip())
                    flight_segment.dep_terminal = ret_seg['departureTerminal'].strip()
                    flight_segment.arr_terminal = ret_seg['arrivalTerminal'].strip()
                    seg_cabin_info = [c for c in ret_cabin_info if c['flightId'] == i][0]
                    flight_segment.cabin = seg_cabin_info['passengers']['rbdInfos'][0]['rbd'].strip()
                    flight_segment.cabin_grade = seg_cabin_info['passengers']['cabin'].strip()
                    flight_segment.cabin_count = seg_cabin_info['passengers']['seats']
                    segment_duration = (datetime.datetime.strptime(arr_time, '%Y-%m-%d %H:%M:%S') -
                                        datetime.datetime.strptime(dep_time, '%Y-%m-%d %H:%M:%S')).total_seconds()
                    flight_segment.duration = int(segment_duration / 60)
                    flight_segment.routing_number = routing_number
                    routing_number += 1
                    flight_routing.ret_segments.append(flight_segment)

                flight_routing.adult_price = float(routing['tickets'][0]['agencies'][0]['passengers'][0]['price']['totalBase']['amount'])
                flight_routing.adult_tax = float(routing['tickets'][0]['agencies'][0]['passengers'][0]['price']['totalTaxIata']['amount'] + \
                                                 routing['tickets'][0]['agencies'][0]['passengers'][0]['price'][
                                                     'totalTaxYQYR']['amount'])
                if len(routing['tickets'][0]['agencies'][0]['passengers']) > 1:
                    child_price = float(routing['tickets'][0]['agencies'][0]['passengers'][1]['price']['totalBase']['amount'])
                    child_tax = float(routing['tickets'][0]['agencies'][0]['passengers'][1]['price']['totalTaxIata']['amount'] + \
                                                 routing['tickets'][0]['agencies'][0]['passengers'][1]['price'][
                                                     'totalTaxYQYR']['amount'])
                else:
                    child_price = flight_routing.adult_price
                    child_tax = flight_routing.adult_tax
                    # child_price = 0.0
                    # child_tax = 0.0

                flight_routing.child_price = child_price
                flight_routing.child_tax = child_tax

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
                                               ret_date=search_info.ret_date,
                                               trip_type=search_info.trip_type,
                                               routing_range=search_info.routing_range,
                                               is_include_operation_carrier=is_include_operation_carrier,
                                               is_multi_segments=1 if len(flight_routing.from_segments) > 1 else 0
                                               )

                flight_routing.routing_key_detail = rk_info['plain']
                flight_routing.routing_key = rk_info['encrypted']

                flight_routing.sid = routing['sId']
                if index == 0:
                    flight_routing.rule_id = 'E1'
                elif index == 1:
                    flight_routing.rule_id = 'E2'
                elif index == 2:
                    flight_routing.rule_id = 'E3'
                else:
                    flight_routing.rule_id = 'B3'

                search_info.assoc_search_routings.append(flight_routing)

        return search_info


    def _booking(self, http_session, order_info):

        airmacau_airport_mapping = {
            'SEL': 'ICN',
            'TYO': 'NRT',
            'BJS': 'PEK',
            'OSA': 'KIX',
        }

        search_result = self.flight_search(http_session=http_session, search_info=order_info, cache_mode='REALTIME')
        origin_data_list = search_result.origin_data_list

        for routing in search_result.assoc_search_routings:
            Logger().debug(routing)
            if RoutingKey.trans_cp_key(simple_decrypt(routing.routing_key)) == RoutingKey.trans_cp_key(
                simple_decrypt(order_info.routing.routing_key)):
                order_info.routing = routing
                break
        if not order_info.routing.sid or not order_info.routing.rule_id:
            raise BookingException('airmacau sid  not found')

        headers = {
            'Origin': 'https://ibe.airmacau.com.cn',
            'Host': 'ibe.airmacau.com.cn',
            'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_{}_{}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/{}.{}".format(
                random.randint(10, 99), random.randint(0, 9), random.randint(100, 999), random.randint(10, 99)),
            'Upgrade-Insecure-Requests': '1',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': 'https://ibe.airmacau.com.cn/cn/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',

        }

        post_data = {
                'tripType': order_info.trip_type,
                'orgcity': airmacau_airport_mapping.get(order_info.from_airport, order_info.from_airport),
                'dstcity': airmacau_airport_mapping.get(order_info.to_airport, order_info.to_airport),
                'takeoffDate': order_info.from_date,
                'returnDate': order_info.ret_date if order_info.trip_type == 'RT' else '',
                'cabinType': 'ECONOMY',
                'adultCount': order_info.adt_count,
                'childCount': order_info.chd_count,
                'vipcode': '',
                'sid': order_info.routing.sid,
                'rule': order_info.routing.rule_id,
                'E1s1res': origin_data_list[0],
                'E2s1res': origin_data_list[1],
                'E3s1res': origin_data_list[2],
                'B3s1res': origin_data_list[3],
                'reqtime': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'STARTTIME': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }

        url = 'https://ibe.airmacau.com.cn/cn/ibe_flight_detail.php'
        result = http_session.request(url=url, method='POST', data=post_data, verify=False)

        print "================ flight detail ============"
        print result.content

        html = etree.HTML(result.content)

        post_data = {
                'tripType':	html.xpath("//input[@name='tripType']/@value")[0],
                'orgcity': html.xpath("//input[@name='orgcity']/@value")[0],
                'dstcity': html.xpath("//input[@name='dstcity']/@value")[0],
                'takeoffDate': html.xpath("//input[@name='takeoffDate']/@value")[0],
                'returnDate': html.xpath("//input[@name='returnDate']/@value")[0],
                'cabinType': html.xpath("//input[@name='cabinType']/@value")[0],
                'adultCount': html.xpath("//input[@name='adultCount']/@value")[0],
                'childCount': html.xpath("//input[@name='childCount']/@value")[0],
                'vipcode': html.xpath("//input[@name='vipcode']/@value")[0],
                'STARTTIME': html.xpath("//input[@name='STARTTIME']/@value")[0],
                's1res': html.xpath("//input[@name='s1res']/@value")[0],
                'sid': html.xpath("//input[@name='sid']/@value")[0],
                'reqtime': html.xpath("//input[@name='reqtime']/@value")[0],
                'currency': html.xpath("//input[@name='currency']/@value")[0],
                'farebasis': html.xpath("//input[@name='farebasis']/@value")[0],
                'flights': html.xpath("//input[@name='flights']/@value")[0],
                'depdate': html.xpath("//input[@name='depdate']/@value")[0],
                'arrdate': html.xpath("//input[@name='arrdate']/@value")[0],
                'plane': html.xpath("//input[@name='plane']/@value")[0],
                'depcity': html.xpath("//input[@name='depcity']/@value")[0],
                'arrcity': html.xpath("//input[@name='arrcity']/@value")[0],
                'ttlamount': html.xpath("//input[@name='ttlamount']/@value")[0],
                'tktprice_adt': html.xpath("//input[@name='tktprice_adt']/@value")[0],
                'tktprice_cnn': html.xpath("//input[@name='tktprice_cnn']/@value")[0],
                'tax_adt': html.xpath("//input[@name='tax_adt']/@value")[0],
                'tax_cnn': html.xpath("//input[@name='tax_cnn']/@value")[0],
                'surcharges_adt': html.xpath("//input[@name='surcharges_adt']/@value")[0],
                'surcharges_cnn': html.xpath("//input[@name='surcharges_cnn']/@value")[0],
                'rule': html.xpath("//input[@name='rule']/@value")[0],
                'change': html.xpath("//input[@name='change']/@value")[0],
                'refund': html.xpath("//input[@name='refund']/@value")[0],
                'bginfo': html.xpath("//input[@name='bginfo']/@value")[0],
                'noshow': html.xpath("//input[@name='noshow']/@value")[0],
        }

        url = 'https://ibe.airmacau.com.cn/cn/ibe_passenger.php'
        result = http_session.request(url=url, method='POST', data=post_data, verify=False)

        print "================= first passenger ==============="
        print result.content

        adt_passengers = []
        chd_passengers = []
        for p in order_info.passengers:
            if p.current_age_type() == 'ADT':
                adt_passengers.append(p)
            else:
                chd_passengers.append(p)

        post_data.pop('s1res')
        post_data.update({
                'last_nameA1': '',
                'first_nameA1': '',
                'genderA1': 'M',
                'nationalityA1': 'CN',
                'idtypeA1': 'W',
                'idnoA1': '',
                'EffectiveDate_A1': '',
                'Birthday_A1': '',
                'cardNo_A1': '',
                'last_nameA2': '',
                'first_nameA2': '',
                'genderA2': 'M',
                'nationalityA2': 'CN',
                'idtypeA2': 'W',
                'idnoA2': '',
                'EffectiveDate_A2': '',
                'Birthday_A2': '',
                'cardNo_A2': '',
                'last_nameA3': '',
                'first_nameA3': '',
                'genderA3': 'M',
                'nationalityA3': 'CN',
                'idtypeA3': 'W',
                'idnoA3': '',
                'EffectiveDate_A3': '',
                'Birthday_A3': '',
                'cardNo_A3': '',
                'last_nameA4': '',
                'first_nameA4': '',
                'genderA4': 'M',
                'nationalityA4': 'CN',
                'idtypeA4': 'W',
                'idnoA4': '',
                'EffectiveDate_A4': '',
                'Birthday_A4': '',
                'cardNo_A4': '',
                'last_nameA5': '',
                'first_nameA5': '',
                'genderA5': 'M',
                'nationalityA5': 'CN',
                'idtypeA5': 'W',
                'idnoA5': '',
                'EffectiveDate_A5': '',
                'Birthday_A5': '',
                'cardNo_A5': '',
                'last_nameA6': '',
                'first_nameA6': '',
                'genderA6': 'M',
                'nationalityA6': 'CN',
                'idtypeA6': 'W',
                'idnoA6': '',
                'EffectiveDate_A6': '',
                'Birthday_A6': '',
                'cardNo_A6': '',
                'last_nameA7': '',
                'first_nameA7': '',
                'genderA7': 'M',
                'nationalityA7': 'CN',
                'idtypeA7': 'W',
                'idnoA7': '',
                'EffectiveDate_A7': '',
                'Birthday_A7': '',
                'cardNo_A7': '',
                'last_nameA8': '',
                'first_nameA8': '',
                'genderA8': 'M',
                'nationalityA8': 'CN',
                'idtypeA8': 'W',
                'idnoA8': '',
                'EffectiveDate_A8': '',
                'Birthday_A8': '',
                'cardNo_A8': '',
                'last_nameA9': '',
                'first_nameA9': '',
                'genderA9': 'M',
                'nationalityA9': 'CN',
                'idtypeA9': 'W',
                'idnoA9': '',
                'EffectiveDate_A9': '',
                'Birthday_A9': '',
                'cardNo_A9': '',
                'last_nameC1': '',
                'first_nameC1': '',
                'genderC1': 'M',
                'nationalityC1': 'CN',
                'idtypeC1': 'W',
                'idnoC1': '',
                'EffectiveDate_C1': '',
                'Birthday_C1': '',
                'cardNo_C1': '',
                'last_nameC2': '',
                'first_nameC2': '',
                'genderC2': 'M',
                'nationalityC2': 'CN',
                'idtypeC2': 'W',
                'idnoC2': '',
                'EffectiveDate_C2': '',
                'Birthday_C2': '',
                'cardNo_C2': '',
                'last_nameC3': '',
                'first_nameC3': '',
                'genderC3': 'M',
                'nationalityC3': 'CN',
                'idtypeC3': 'W',
                'idnoC3': '',
                'EffectiveDate_C3': '',
                'Birthday_C3': '',
                'cardNo_C3': '',
                'last_nameC4': '',
                'first_nameC4': '',
                'genderC4': 'M',
                'nationalityC4': 'CN',
                'idtypeC4': 'W',
                'idnoC4': '',
                'EffectiveDate_C4': '',
                'Birthday_C4': '',
                'cardNo_C4': '',
                'last_nameC5': '',
                'first_nameC5': '',
                'genderC5': 'M',
                'nationalityC5': 'CN',
                'idtypeC5': 'W',
                'idnoC5': '',
                'EffectiveDate_C5': '',
                'Birthday_C5': '',
                'cardNo_C5': '',
                'last_nameC6': '',
                'first_nameC6': '',
                'genderC6': 'M',
                'nationalityC6': 'CN',
                'idtypeC6': 'W',
                'idnoC6': '',
                'EffectiveDate_C6': '',
                'Birthday_C6': '',
                'cardNo_C6': '',
                'last_nameC7': '',
                'first_nameC7': '',
                'genderC7': 'M',
                'nationalityC7': 'CN',
                'idtypeC7': 'W',
                'idnoC7': '',
                'EffectiveDate': 'C7',
                'Birthday_C7': '',
                'cardNo_C7': '',
                'last_nameC8': '',
                'first_nameC8': '',
                'genderC8': 'M',
                'nationalityC8': 'CN',
                'idtypeC8': 'W',
                'idnoC8': '',
                'EffectiveDate_C8': '',
                'Birthday_C8': '',
                'cardNo_C8': '',
                'name_contact': '',
                'mobile': '86',
                'mobile_contact': '',
                'mail_contact': '',
                'Confirm': 'on',
                'Collection': 'on',
        })

        for index, p in enumerate(adt_passengers):
            post_data['last_nameA{}'.format(index + 1)] = p.last_name
            post_data['first_nameA{}'.format(index + 1)] = p.first_name
            post_data['genderA{}'.format(index + 1)] = p.gender
            post_data['nationalityA{}'.format(index + 1)] = p.nationality
            post_data['idtypeA{}'.format(index + 1)] = 'P'
            post_data['idnoA{}'.format(index + 1)] = p.selected_card_no
            post_data['EffectiveDate_A{}'.format(index + 1)] = p.card_expired
            post_data['Birthday_A{}'.format(index + 1)] = p.birthdate
            post_data['cardNo_A{}'.format(index + 1)] = ''

        for index, p in enumerate(chd_passengers):
            post_data['last_nameC{}'.format(index + 1)] = p.last_name
            post_data['first_nameC{}'.format(index + 1)] = p.first_name
            post_data['genderC{}'.format(index + 1)] = p.gender
            post_data['nationalityC{}'.format(index + 1)] = p.nationality
            post_data['idtypeC{}'.format(index + 1)] = 'P'
            post_data['idnoC{}'.format(index + 1)] = p.selected_card_no
            post_data['EffectiveDate_C{}'.format(index + 1)] = p.card_expired
            post_data['Birthday_C{}'.format(index + 1)] = p.birthdate
            post_data['cardNo_C{}'.format(index + 1)] = ''

        contact = order_info.contacts[0]
        post_data['name_contact'] = adt_passengers[0].last_name
        post_data['mobile_contact'] = TBG.global_config['OPERATION_CONTACT_MOBILE']
        post_data['mail_contact'] = contact.email

        url = 'https://ibe.airmacau.com.cn/cn/ibe_passenger.php'
        result = http_session.request(url=url, method='POST', data=post_data, verify=False)

        print "===================== second passenger ===================="
        print result.content

        # alipay

        result = http_session.request(url='https://ibe.airmacau.com.cn/geetest/StartCaptchaServlet.php?t={}'.format(
            int(time.time() * 1000)), method='GET', verify=False).to_json()

        print "==================== get gee gt =============="
        print result

        gt = result['gt']
        challenge = result['challenge']
        if not gt or not challenge:
            raise BookingException('cannot get geetest gt and challenge!')

        cracker = CaptchaCracker.select('C2567')
        checked_gee = cracker.crack(geetest_gt=gt, geetest_challenge=challenge)
        geetest_challenge = checked_gee['challenge']
        geetest_validate = checked_gee['validate']
        geetest_seccode = checked_gee['validate'] + '|jordan'

        result = http_session.request(url='https://ibe.airmacau.com.cn/geetest/geeCHK.php', data={
            'geetest_challenge': geetest_challenge,
            'geetest_validate': geetest_validate,
            'geetest_seccode': geetest_seccode,
        }, method='POST', verify=False)

        print "=================== check gee ============="
        print result.content

        if not int(result.content) == 1:
            raise BookingException('geetest check failed! ')


        post_data['mobile_contact'] = '{}-{}'.format(post_data['mobile'], post_data['mobile_contact'])
        post_data['Collection'] = '1'
        post_data['paycur'] = 'CNY'
        post_data['payway'] = 'ALIP'
        post_data['geetest_challenge'] = geetest_challenge
        post_data['geetest_validate'] = geetest_validate
        post_data['geetest_seccode'] = geetest_seccode

        url = 'https://ibe.airmacau.com.cn/cn/ibe_pay.php'
        result = http_session.request(url=url, method='POST', data=post_data, verify=False)

        print "==================== pay html -------------"
        print result.content
