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
from ..dao.iata_code import BUDGET_AIRLINE_CODE


class TCCustomer(ProvderAutoBase):
    timeout = 50  # 请求超时时间
    provider = 'tc_customer'  # 子类继承必须赋
    provider_channel = 'tc_customer_web'  # 子类继承必须赋
    operation_product_type = '会员折扣'  # 运价类型：0: GDS公布运价 1:GDS私有运价 2:航司官网产品  3:廉价航司产品 4:特价产品
    operation_product_mode = 'A2B'
    pay_channel = 'ALIPAY'
    provider_token = '5e7ba8bddd7b9648'
    is_display = True
    no_flight_ttl = 3600 * 3  # 无航班缓存超时时间设定



    CACHE_PR_CONFIG = {
        1: {'cabin_expired_time': 60 * 10, 'cabin_attenuation': 3,'fare_expired_time':86400 * 30},
        2: {'cabin_expired_time': 60 * 10, 'cabin_attenuation': 2,'fare_expired_time':86400 * 20},
        3: {'cabin_expired_time': 60 * 5, 'cabin_attenuation': 1,'fare_expired_time':86400 * 10},
        4: {'cabin_expired_time': 60 * 5, 'cabin_attenuation': 1,'fare_expired_time':86400 * 5},
        5: {'cabin_expired_time': 60 * 5, 'cabin_attenuation': 0,'fare_expired_time':86400},

    }
    search_interval_time = 0.3

    def __init__(self):
        super(TCCustomer, self).__init__()


    # PC web search

    # def _flight_search(self, http_session, search_info):
    #     """
    #     航班爬取模块，
    #     TODO :目前只考虑单程
    #     :return:
    #     """
    #
    #     Logger().debug('search flight')
    #
    #     device_route = ''
    #     device_td_did = ''
    #     device_td_sid = ''
    #     device_session = self._get_session()
    #     for d in device_session:
    #         if d['name'] == 'route':
    #             device_route = d['value']
    #         if d['name'] == 'td_did':
    #             device_td_did = d['value']
    #         if d['name'] == 'td_sid':
    #             device_td_sid = d['value']
    #     http_session.update_cookie({
    #         'route': device_route,
    #         'td_did': device_td_did,
    #         'td_sid': device_td_sid,
    #     })
    #     headers = {
    #         'Referer': 'https://www.ly.com/iflight/flight-book1.aspx?para=0*SHA*OSA*2019-02-06**YSCF*1*1*1',
    #         'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_{}_{}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/{}.{}'.format(random.randint(10, 99), random.randint(0, 9), random.randint(100, 999), random.randint(10, 99)),
    #     }
    #     url = 'https://www.ly.com/pciflightapi/json/reQuery.html?tdleonid=tdleonid'
    #     post_data = {
    #         'dc': search_info.from_airport,
    #         'ac': search_info.to_airport,
    #         'dt': search_info.from_date,
    #         'an': search_info.adt_count,
    #         'cn': search_info.chd_count if search_info.chd_count else 1,
    #         'cabin': 'Y|S|C|F',
    #         'tit': '1',
    #         'tt': '0',
    #         'at': '',
    #         'dcn': '上海',
    #         'acn': '大阪',
    #         'time': int(time.time() * 1000),
    #     }
    #
    #     result = http_session.request(url=url, data=post_data, method='POST', headers=headers).to_json()
    #     Logger().debug("====== search result:{} ==".format(json.dumps(result)))
    #
    #     if result.get('_leonid___capurl__'):
    #         raise FlightSearchException('HIGH_REQ_LIMIT')
    #     if not result.get('code') == 200 or not result.get('data'):
    #         raise FlightSearchException('HIGH_REQ_LIMIT')
    #
    #     if result['data']['done'] == 1 and not result['data']['res']:
    #         Logger().warn('tc customer no flight')
    #         return search_info
    #
    #     for times in xrange(10):
    #         if result['data']['done'] == 0:
    #             tid = result['data']['tid']
    #             post_data['tid'] = tid
    #             result = http_session.request(url=url, data=post_data, method='POST', headers=headers).to_json()
    #             Logger().debug("====== search result:{} ==".format(json.dumps(result)))
    #         elif result['data']['done'] == 1 and not result['data']['res']:
    #             Logger().warn('tuniu no flight')
    #             return search_info
    #         elif result['data']['done'] == 1:
    #             break
    #         time.sleep(1)
    #
    #     routing_list = result['data']['res']
    #     for routing in routing_list:
    #         cabin_list = routing['pl']
    #         for cabin in cabin_list:
    #             seg_list = routing.get('fl')
    #             if not seg_list:
    #                 continue
    #             flight_routing = FlightRoutingInfo()
    #             flight_routing.product_type = 'DEFAULT'
    #             routing_number = 1
    #             for index, seg in enumerate(seg_list):
    #                 flight_segment = FlightSegmentInfo()
    #                 flight_segment.carrier = seg['opc']
    #                 dep_time = datetime.datetime.strptime(seg['dt'], '%Y-%m-%dT%H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
    #                 arr_time = datetime.datetime.strptime(seg['at'], '%Y-%m-%dT%H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
    #                 flight_segment.dep_airport = seg['dac']
    #                 flight_segment.dep_time = dep_time
    #                 flight_segment.arr_airport = seg['aac']
    #                 flight_segment.arr_time = arr_time
    #
    #                 # 经停
    #                 stop_info = seg.get('stops')
    #                 if stop_info:
    #                     stop_city_code_list = [c['sicc'] for c in stop_info]
    #                     stop_airport_code_list = [a['sic'] for a in stop_info]
    #                     flight_segment.stop_cities = "/".join(stop_city_code_list)
    #                     flight_segment.stop_airports = "/".join(stop_airport_code_list)
    #                 flight_segment.flight_number = seg['fnum']
    #                 flight_segment.dep_terminal = seg['dat'] if seg.get('dat', '').strip() else ''
    #                 flight_segment.arr_terminal = seg['aat'] if seg.get('aat', '').strip() else ''
    #                 flight_segment.cabin = cabin['cc'][index]
    #                 flight_segment.cabin_grade = cabin['bcc']
    #                 flight_segment.cabin_count = cabin['cn']
    #                 segment_duration = (datetime.datetime.strptime(seg['at'], '%Y-%m-%dT%H:%M:%S') -
    #                                     datetime.datetime.strptime(seg['dt'], '%Y-%m-%dT%H:%M:%S')).seconds
    #                 flight_segment.duration = int(segment_duration / 60)
    #                 flight_segment.routing_number = routing_number
    #                 routing_number += 1
    #                 flight_routing.from_segments.append(flight_segment)
    #
    #             # 补充舱位和舱等
    #             flight_routing.reference_cabin = flight_routing.from_segments[0].cabin
    #             flight_routing.reference_cabin_grade = flight_routing.from_segments[0].cabin_grade
    #             flight_routing.adult_price = float(cabin['pi']['asp'])
    #             flight_routing.adult_tax = float(cabin['pi']['atp'])
    #             flight_routing.child_price = float(cabin['pi']['cfsp'])
    #             flight_routing.child_tax = float(cabin['pi']['cftax'])
    #             rk_info = RoutingKey.serialize(from_airport=flight_routing.from_segments[0].dep_airport,
    #                                            dep_time=datetime.datetime.strptime(flight_routing.from_segments[0].dep_time,
    #                                                                                '%Y-%m-%d %H:%M:%S'),
    #                                            to_airport=flight_routing.from_segments[-1].arr_airport,
    #                                            arr_time=datetime.datetime.strptime(flight_routing.from_segments[-1].arr_time,
    #                                                                                '%Y-%m-%d %H:%M:%S'),
    #                                            flight_number='-'.join([s.flight_number for s in flight_routing.from_segments]),
    #                                            cabin='-'.join([s.cabin for s in flight_routing.from_segments]),
    #                                            cabin_grade='-'.join([s.cabin_grade for s in flight_routing.from_segments]),
    #                                            product=cabin['pserial'],
    #                                            adult_price=flight_routing.adult_price, adult_tax=flight_routing.adult_tax,
    #                                            provider_channel=self.provider_channel,
    #                                            child_price=flight_routing.child_price, child_tax=flight_routing.child_tax,
    #                                            inf_price=0.0,
    #                                            inf_tax=0.0,
    #                                            provider=self.provider,
    #                                            search_from_airport=search_info.from_airport,
    #                                            search_to_airport=search_info.to_airport,
    #                                            from_date=search_info.from_date,
    #                                            routing_range=search_info.routing_range,
    #                                            is_multi_segments=1 if len(flight_routing.from_segments) > 1 else 0
    #                                            )
    #
    #             flight_routing.routing_key_detail = rk_info['plain']
    #             flight_routing.routing_key = rk_info['encrypted']
    #             search_info.assoc_search_routings.append(flight_routing)
    #
    #     return search_info

    # H5 search

    # def _flight_search(self, http_session, search_info):
    #     """
    #     航班爬取模块，
    #     TODO :目前只考虑单程
    #     :return:
    #     """
    #
    #     Logger().debug('search flight')
    #
    #     # device_route = ''
    #     # device_td_did = ''
    #     # device_td_sid = ''
    #     # device_session = self._get_session()
    #     # for d in device_session:
    #     #     if d['name'] == 'route':
    #     #         device_route = d['value']
    #     #     if d['name'] == 'td_did':
    #     #         device_td_did = d['value']
    #     #     if d['name'] == 'td_sid':
    #     #         device_td_sid = d['value']
    #     # http_session.update_cookie({
    #     #     'route': device_route,
    #     #     'td_did': device_td_did,
    #     #     'td_sid': device_td_sid,
    #     # })
    #     headers = {
    #         'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 11_0 like Mac OS X) AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Mobile/15A372 Safari/604.1',
    #         'Referer': 'https://m.ly.com/tiflightnfe/book1.html/HRB/FMA/%E5%93%88%E5%B0%94%E6%BB%A8/%E7%A6%8F%E8%8E%AB%E8%90%A8/2019-01-24/1900-01-01/single/1/0?beginCity=%E5%93%88%E5%B0%94%E6%BB%A8&arrCity=%E7%A6%8F%E8%8E%AB%E8%90%A8&arrivaltime=&FlyOffTime=2019-01-24&space=E&iflight_adult=1&iflight_children=0',
    #         'Host': 'm.ly.com',
    #         'Connection': 'keep-alive',
    #         'Content-Length': '137',
    #         'Pragma': 'no-cache',
    #         'Cache-Control': 'no-cache',
    #         'Accept': 'application/json, text/plain, */*',
    #         'Origin': 'https://m.ly.com',
    #         'touch-token': '1',
    #         'Content-Type': 'application/json',
    #         'Accept-Encoding': 'gzip, deflate, br',
    #         'Accept-Language': 'en-GB,en;q=0.9,en-US;q=0.8,zh-CN;q=0.7,zh;q=0.6',
    #     }
    #     url = 'https://m.ly.com/miflightapi/json/search.html?tdleonid=tdleonid'
    #     post_data = {
    #         'dc': search_info.from_airport,
    #         'ac': search_info.to_airport,
    #         'dt': search_info.from_date,
    #         'at': '1900-01-01',
    #         'an': search_info.adt_count,
    #         'cn': search_info.chd_count if search_info.chd_count else 1,
    #         'cabin': 'Y|S|C|F',
    #         'tt': 0,
    #         "g": '',
    #         'tid': 'TH{}LVS51BTQFYK46E3FQROYO4Y3S5NAQ9QRFGWY{}'.format(
    #             datetime.datetime.now().strftime('%Y%m%d%H%M%S'), random.randint(100000, 999999)),
    #         "uniontid": ""
    #     }
    #
    #     result = http_session.request(url=url, json=post_data, method='POST', proxy_pool='D', headers=headers,
    #                                   verify=False).to_json()
    #     Logger().debug("====== search result:{} ==".format(json.dumps(result)))
    #
    #     if result.get('_leonid___capurl__'):
    #         raise FlightSearchException('HIGH_REQ_LIMIT')
    #     if not result.get('code') == 200 or not result.get('data'):
    #         raise FlightSearchException('HIGH_REQ_LIMIT')
    #
    #     if result['data']['done'] == 1 and not result['data']['res']:
    #         Logger().warn('tc customer no flight')
    #         return search_info
    #
    #     for times in xrange(10):
    #         if result['data']['done'] == 0:
    #             tid = result['data']['tid']
    #             post_data['tid'] = tid
    #             result = http_session.request(url=url, json=post_data, method='POST', proxy_pool='D',
    #                                           headers=headers, verify=False).to_json()
    #             Logger().debug("====== search result:{} ==".format(json.dumps(result)))
    #         elif result['data']['done'] == 1 and not result['data']['res']:
    #             Logger().warn('tc customer no flight')
    #             return search_info
    #         elif result['data']['done'] == 1:
    #             break
    #         time.sleep(1)
    #
    #     routing_list = result['data']['res']
    #     for routing in routing_list:
    #         dep_seg_list = routing['dants']
    #         arr_seg_list = routing['aants']
    #         flight_seg_list = routing['acs']
    #         stops_seg_list = [{'dt': routing['dt'], 'at': ''}] + [t for t in routing['stps'] if t['type'] == "t"] + \
    #                          [{'dt': '', 'at': routing['at']}]
    #         dep_date_seg_list = routing['fdate']
    #         arr_date_seg_list = routing['adate']
    #         if not dep_seg_list:
    #             continue
    #         flight_routing = FlightRoutingInfo()
    #         flight_routing.product_type = 'DEFAULT'
    #         routing_number = 1
    #         for index, seg in enumerate(dep_seg_list):
    #             flight_segment = FlightSegmentInfo()
    #             flight_segment.carrier = flight_seg_list[index]['ac']
    #             dep_time = datetime.datetime.strptime(dep_date_seg_list[index] + stops_seg_list[index]['dt'],
    #                                                   '%Y-%m-%d%H:%M').strftime('%Y-%m-%d %H:%M:%S')
    #             arr_time = datetime.datetime.strptime(arr_date_seg_list[index] + stops_seg_list[index + 1]['at'],
    #                                                   '%Y-%m-%d%H:%M').strftime('%Y-%m-%d %H:%M:%S')
    #             flight_segment.dep_airport = dep_seg_list[index]['dac']
    #             flight_segment.dep_time = dep_time
    #             flight_segment.arr_airport = arr_seg_list[index]['aac']
    #             flight_segment.arr_time = arr_time
    #             flight_segment.flight_number = flight_seg_list[index]['an']
    #             flight_segment.dep_terminal = dep_seg_list[index]['dat']
    #             flight_segment.arr_terminal = arr_seg_list[index]['aat']
    #             flight_segment.cabin = 'Y'
    #             flight_segment.cabin_grade = 'Y'
    #             flight_segment.cabin_count = 9
    #             segment_duration = (datetime.datetime.strptime(arr_time, '%Y-%m-%d %H:%M:%S') -
    #                                 datetime.datetime.strptime(dep_time, '%Y-%m-%d %H:%M:%S')).total_seconds()
    #             flight_segment.duration = int(segment_duration / 60)
    #             flight_segment.routing_number = routing_number
    #             routing_number += 1
    #             flight_routing.from_segments.append(flight_segment)
    #
    #         flight_routing.adult_price = float(routing['sp'])
    #         flight_routing.adult_tax = float(routing['tp'] - routing['sp'])
    #         flight_routing.child_price = float(routing['sp'])
    #         flight_routing.child_tax = float(routing['tp'] - routing['sp'])
    #         rk_info = RoutingKey.serialize(from_airport=flight_routing.from_segments[0].dep_airport,
    #                                        dep_time=datetime.datetime.strptime(flight_routing.from_segments[0].dep_time,
    #                                                                            '%Y-%m-%d %H:%M:%S'),
    #                                        to_airport=flight_routing.from_segments[-1].arr_airport,
    #                                        arr_time=datetime.datetime.strptime(flight_routing.from_segments[-1].arr_time,
    #                                                                            '%Y-%m-%d %H:%M:%S'),
    #                                        flight_number='-'.join([s.flight_number for s in flight_routing.from_segments]),
    #                                        cabin='-'.join([s.cabin for s in flight_routing.from_segments]),
    #                                        cabin_grade='-'.join([s.cabin_grade for s in flight_routing.from_segments]),
    #                                        product='COMMON',
    #                                        adult_price=flight_routing.adult_price, adult_tax=flight_routing.adult_tax,
    #                                        provider_channel=self.provider_channel,
    #                                        child_price=flight_routing.child_price, child_tax=flight_routing.child_tax,
    #                                        inf_price=0.0,
    #                                        inf_tax=0.0,
    #                                        provider=self.provider,
    #                                        search_from_airport=search_info.from_airport,
    #                                        search_to_airport=search_info.to_airport,
    #                                        from_date=search_info.from_date,
    #                                        routing_range=search_info.routing_range,
    #                                        is_multi_segments=1 if len(flight_routing.from_segments) > 1 else 0
    #                                        )
    #
    #         flight_routing.routing_key_detail = rk_info['plain']
    #         flight_routing.routing_key = rk_info['encrypted']
    #         search_info.assoc_search_routings.append(flight_routing)
    #
    #     return search_info

    # def _get_session(self):
    #
    #     while True:
    #         device_info = TBG.redis_conn.redis_pool.rpop('tc_customer_device_session')
    #         if not device_info:
    #             # 队列中没有抛异常
    #             raise FlightSearchException('cannot get device session!')
    #         device_info = json.loads(device_info)
    #         if datetime.datetime.now() - datetime.timedelta(seconds=60 * 3) <= datetime.datetime.strptime(device_info['create_time'], '%Y-%m-%d %H:%M:%S'):
    #             # 如果数据没有超过29分钟，使用该数据
    #             TBG.redis_conn.redis_pool.lpush('tc_customer_device_session', json.dumps(device_info))
    #             break
    #
    #
    #     sd = [
    #         {'session_type': 'cookie', 'name': 'route', 'value': device_info['route']},
    #         {'session_type': 'cookie', 'name': 'td_did', 'value': device_info['td_did']},
    #         {'session_type': 'cookie', 'name': 'td_sid', 'value': device_info['td_sid']},
    #     ]
    #     return sd


    # APP search

    def _flight_search(self, http_session, search_info):
        """
        航班爬取模块，
        TODO :目前只考虑单程
        :return:
        """

        Logger().debug('search flight')

        device_id = '12adfa0b67a15ffd'
        random_char = ''
        for i in xrange(6):
            random_char += random.choice(string.uppercase)

        post_data = {
            "request": {
                "body": {
                    "timeStamp": str(int(time.time() * 1000)),
                    "tt": "0",
                    "dt": search_info.from_date,
                    "an": search_info.adt_count,
                    "requestFrom": "NA",
                    "qt": "0",
                    "dc": search_info.from_airport,
                    "cc": "Y|S",
                    "clientInfo": {
                        "versionNumber": "9.1.2",
                        # "clientId": "7d4ecd48d8de896eb46d5b0a50c187e2a8a9bb{}".format(random.randint(100000, 999999)),
                        # "clientId": "7d4ecd48d8de896eb46d5b0a50c187e2a8a9bbb60010",
                        'clientId': 'null',
                        "mac": "ca9c9a9a8ee63141d17492a4d2{}".format(random.randint(100000, 999999)),
                        # "clientIp": "192.168.199.181",
                        "clientIp": "192.168.199.{}".format(random.randint(1, 255)),
                        # "versionType": "iPhone",
                        "versionType": "android",

                        "manufacturer": "Xiaomi",

                        "area": "1|{}|{}".format(random.randint(1, 30), random.randint(100, 325)),
                        "deviceId": device_id,
                        "networkType": "wifi",
                        "pushInfo": "",
                        # "extend": "2^com.tongcheng.iphone,4^12.0.1,5^iPhone9_1,os_v^12.0.1",
                        "extend": "4^12.0.1,5^android5_1,os_v^5.0.1,devicetoken^{}".format(device_id),
                        # "device": "{}|375*667|iPhone9,1".format(device_id),
                        "device": "null",
                        "refId": "5866741",
                        "systemCode": "tc"
                    },
                    "ac": search_info.to_airport,
                    "tid": "AP{}OMJT0TRR47EW0S4V1SSOP2WYFYV2XXO3DL49JBUXK2{}".format(
                        datetime.datetime.now().strftime('%Y%m%d%H%M%S'), random_char),
                    "cn": "0"
                },
                "header": {
                    "accountID": "c26b007f-c89e-431a-b8cc-493becbdd8a2",
                    "serviceName": "search",
                    "reqTime": str(int(time.time() * 1000)),
                    "digitalSign": "",
                    "version": "20111128102912"
                }
            }
        }

        sign_origin_data = [
            'Version={}'.format(post_data['request']['header']['version']),
            'AccountID={}'.format(post_data['request']['header']['accountID']),
            'ServiceName={}'.format(post_data['request']['header']['serviceName']),
            'ReqTime={}'.format(post_data['request']['header']['reqTime'])
        ]
        sign_data = '&'.join(sorted(sign_origin_data)) + '8874d8a8b8b391fbbd1a25bda6ecda11'
        print sign_data
        sign_data = hashlib.md5(sign_data).hexdigest()
        post_data['request']['header']['digitalSign'] = sign_data

        sec_key = '4957CA66-37C3-46CB-B26D-E3D9DCB51535'
        final_post_data = json.dumps(post_data, separators=(',', ':'))
        print final_post_data
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'TongchengRequest',
            'secver': '4',
            'reqdata': hashlib.md5(final_post_data + sec_key).hexdigest()
        }
        url = 'https://tcmobileapi.17usoft.com/interflight/nodehandler.ashx'

        result = http_session.request(url=url, data=final_post_data, method='POST', proxy_pool='A', headers=headers,
                                      verify=False).to_json()
        Logger().debug("====== search result:{} ==".format(json.dumps(result)))

        if result.get('_leonid___capurl__'):
            raise FlightSearchException(err_code='HIGH_REQ_LIMIT')
        if not result['response']['header']['rspCode'] == "0000":
            raise FlightSearchException('ERROR')

        if result['response']['body']['done'] == "1" and not result['response']['body']['res']:
            Logger().warn('tc customer no flight')
            return search_info

        for times in xrange(10):
            if result['response']['body']['done'] == "0":
                tid = result['response']['body']['tid']
                post_data['request']['body']['tid'] = tid

                final_post_data = json.dumps(post_data, separators=(',', ':'))
                print final_post_data
                headers = {
                    'Content-Type': 'application/json',
                    'User-Agent': 'TongchengRequest',
                    'secver': '4',
                    'reqdata': hashlib.md5(final_post_data + sec_key).hexdigest()
                }

                result = http_session.request(url=url, data=final_post_data, method='POST', proxy_pool='A',
                                              headers=headers, verify=False).to_json()
                Logger().debug("====== search result:{} ==".format(json.dumps(result)))
            elif result['response']['body']['done'] == "1" and not result['response']['body']['res']:
                Logger().warn('tc customer no flight')
                return search_info
            elif result['response']['body']['done'] == "1":
                break
            time.sleep(1)

        routing_list = result['response']['body']['res']
        for routing in routing_list:
            dep_seg_list = routing['dants']
            arr_seg_list = routing['aants']
            flight_seg_list = routing['acs']
            stops_seg_list = [{'dt': routing['dt'], 'at': ''}] + [t for t in routing['stps'] if t['type'] == "t"] + \
                             [{'dt': '', 'at': routing['at']}]
            dep_date_seg_list = routing['fdate']
            arr_date_seg_list = routing['adate']
            if not dep_seg_list:
                continue
            flight_routing = FlightRoutingInfo()
            flight_routing.product_type = 'DEFAULT'
            routing_number = 1
            for index, seg in enumerate(dep_seg_list):
                flight_segment = FlightSegmentInfo()
                flight_segment.carrier = flight_seg_list[index]['ac']
                dep_time = datetime.datetime.strptime(dep_date_seg_list[index] + stops_seg_list[index]['dt'],
                                                      '%Y-%m-%d%H:%M').strftime('%Y-%m-%d %H:%M:%S')
                arr_time = datetime.datetime.strptime(arr_date_seg_list[index] + stops_seg_list[index + 1]['at'],
                                                      '%Y-%m-%d%H:%M').strftime('%Y-%m-%d %H:%M:%S')
                flight_segment.dep_airport = dep_seg_list[index]['ac']
                flight_segment.dep_time = dep_time
                flight_segment.arr_airport = arr_seg_list[index]['ac']
                flight_segment.arr_time = arr_time
                flight_segment.flight_number = flight_seg_list[index]['an']
                flight_segment.dep_terminal = dep_seg_list[index]['at']
                flight_segment.arr_terminal = arr_seg_list[index]['at']
                if flight_segment.carrier in BUDGET_AIRLINE_CODE:
                    flight_segment.cabin = 'Y'
                else:
                    flight_segment.cabin = 'N/A'
                flight_segment.cabin_grade = 'Y'
                flight_segment.cabin_count = 9
                segment_duration = (datetime.datetime.strptime(arr_time, '%Y-%m-%d %H:%M:%S') -
                                    datetime.datetime.strptime(dep_time, '%Y-%m-%d %H:%M:%S')).total_seconds()
                flight_segment.duration = int(segment_duration / 60)
                flight_segment.routing_number = routing_number
                routing_number += 1
                flight_routing.from_segments.append(flight_segment)

            flight_routing.adult_price = float(routing['sp'])
            flight_routing.adult_tax = float(routing['tp']) - float(routing['sp'])
            flight_routing.child_price = float(routing['sp'])
            flight_routing.child_tax = float(routing['tp']) - float(routing['sp'])
            rk_info = RoutingKey.serialize(from_airport=flight_routing.from_segments[0].dep_airport,
                                           dep_time=datetime.datetime.strptime(flight_routing.from_segments[0].dep_time,
                                                                               '%Y-%m-%d %H:%M:%S'),
                                           to_airport=flight_routing.from_segments[-1].arr_airport,
                                           arr_time=datetime.datetime.strptime(flight_routing.from_segments[-1].arr_time,
                                                                               '%Y-%m-%d %H:%M:%S'),
                                           flight_number='-'.join([s.flight_number for s in flight_routing.from_segments]),
                                           cabin='-'.join([s.cabin for s in flight_routing.from_segments]),
                                           cabin_grade='-'.join([s.cabin_grade for s in flight_routing.from_segments]),
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
                                           routing_range=search_info.routing_range,
                                           trip_type=search_info.trip_type,
                                           is_include_operation_carrier=0,
                                           is_multi_segments=1 if len(flight_routing.from_segments) > 1 else 0
                                           )

            flight_routing.routing_key_detail = rk_info['plain']
            flight_routing.routing_key = rk_info['encrypted']
            search_info.assoc_search_routings.append(flight_routing)

        return search_info


