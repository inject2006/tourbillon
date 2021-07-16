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


class Shenzhenair(ProvderAutoBase):
    timeout = 50  # 请求超时时间
    provider = 'ZH_PROVIDER'  # 子类继承必须赋
    provider_channel = 'ZH_PROVIDER_WEB'  # 子类继承必须赋
    operation_product_type = '会员折扣'  # 运价类型：0: GDS公布运价 1:GDS私有运价 2:航司官网产品  3:廉价航司产品 4:特价产品
    operation_product_mode = 'A2B'
    pay_channel = 'ALIPAY'
    provider_token = '5e7ba8bddd7b9648'
    is_display = True
    trip_type_list = ['OW', 'RT']
    no_flight_ttl = 3600 * 3 # 无航班缓存超时时间设定
    carrier_list = ['ZH']  # 供应商所包含的航司列表，如果包含多个并且无法确定，请不要填写，此处会关联执飞航线判断逻辑


    CACHE_PR_CONFIG = {
        1: {'cabin_expired_time': 60 * 10, 'cabin_attenuation': 3,'fare_expired_time':86400 * 30},
        2: {'cabin_expired_time': 60 * 10, 'cabin_attenuation': 2,'fare_expired_time':86400 * 20},
        3: {'cabin_expired_time': 60 * 5, 'cabin_attenuation': 1,'fare_expired_time':86400 * 10},
        4: {'cabin_expired_time': 60 * 5, 'cabin_attenuation': 1,'fare_expired_time':86400 * 5},
        5: {'cabin_expired_time': 60 * 5, 'cabin_attenuation': 0,'fare_expired_time':86400},

    }
    search_interval_time = 1

    def __init__(self):
        super(Shenzhenair, self).__init__()

    def get_sign(self):

        # sign 30s过期

        while True:
            sign_info = TBG.redis_conn.redis_pool.rpop('shenzhenair_web_sign')
            if not sign_info:
                raise Exception('shenzhenair have no web sign')
            sign_info = json.loads(sign_info)

            if datetime.datetime.now() - datetime.timedelta(seconds=30) > datetime.datetime.strptime(
                sign_info['create_time'], '%Y-%m-%d %H:%M:%S'):
                continue
            else:
                TBG.redis_conn.redis_pool.lpush('shenzhenair_web_sign', json.dumps(sign_info))
                return sign_info['_g_sign'], sign_info['CoreSessionId']

    def _flight_search(self, http_session, search_info):
        """
        航班爬取模块，
        TODO :目前只考虑单程
        :return:
        """

        Logger().debug('search flight')

        shenzhenair_airport_mapping = {
            'SEL': 'ICN',
            'TYO': 'NRT',
            'BJS': 'PEK',
            'OSA': 'KIX',
        }

        route_list = []
        if search_info.from_airport == 'SHA':
            route_list.append(['SHA', shenzhenair_airport_mapping.get(search_info.to_airport, search_info.to_airport)])
            route_list.append(['PVG', shenzhenair_airport_mapping.get(search_info.to_airport, search_info.to_airport)])
        elif search_info.to_airport == 'SHA':
            route_list.append([shenzhenair_airport_mapping.get(search_info.from_airport, search_info.from_airport),
                              'SHA'])
            route_list.append([shenzhenair_airport_mapping.get(search_info.from_airport, search_info.from_airport),
                              'PVG'])
        else:
            route_list.append([shenzhenair_airport_mapping.get(search_info.from_airport, search_info.from_airport),
                              shenzhenair_airport_mapping.get(search_info.to_airport, search_info.to_airport)])

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
            Logger().warn('shenzhenair no flight')
            return search_info
        search_info.assoc_search_routings.extend(self.product_list)
        return search_info


    def _sub_flight_search(self, http_session, search_info, from_airport, to_airport):

        _g_sign, CoreSessionId = self.get_sign()

        headers = {
            'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_{}_{}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/{}.{}".format(
                random.randint(10, 99), random.randint(0, 9), random.randint(100, 999), random.randint(10, 99)),
            'Host': 'm.shenzhenair.com',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Origin': 'http://m.shenzhenair.com',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'http://m.shenzhenair.com/webresource-micro/queryFlights.html',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-GB,en;q=0.9,en-US;q=0.8,zh-CN;q=0.7,zh;q=0.6',
            # 'Cookie': 'JSESSIONID=2A84F39DC06BBD2E9EFD5911{}-n1;'.format(random.randint(10000000, 99999999)),
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        device_id = '169c7b6{}-0620c246df5066-2d604637-304704-169c7b676b0617'.format(random.randint(100000, 999999))

        http_session.update_cookie({
            'JSESSIONID': '2A84F39DC06BBD2E9EFD5911{}-n1;'.format(random.randint(10000000, 99999999)),
            # 'JSESSIONID': '8351E2771D3BD15A1925A80EF177AFF7-n1',
            # 'sensorsdata2015jssdkcross': '%7B%22distinct_id%22%3A%22dd4cac06-18ae-34b9-9883-0a6ba8{}%22%2C%22%24device_id%22%3A%221699fe3d533308-02041617b6844f-36{}-3686400-1699fe3d53468f%22%2C%22props%22%3A%7B%22%24latest_traffic_source_type%22%3A%22%E7%9B%B4%E6%8E%A5%E6%B5%81%E9%87%8F%22%2C%22%24latest_referrer%22%3A%22%22%2C%22%24latest_referrer_host%22%3A%22%22%2C%22%24latest_search_keyword%22%3A%22%E6%9C%AA%E5%8F%96%E5%88%B0%E5%80%BC_%E7%9B%B4%E6%8E%A5%E6%89%93%E5%BC%80%22%2C%22nowStatus%22%3A%22%E6%9C%AA%E7%99%BB%E5%BD%95%22%2C%22site%22%3A%22%E4%B8%AD%E5%9B%BD%22%2C%22language%22%3A%22%E7%AE%80%E4%BD%93%E4%B8%AD%E6%96%87%22%2C%22platform%22%3A%22WAP%22%2C%22loginid%22%3A%22%22%7D%2C%22first_id%22%3A%221699fe3d533308-02041617b6844f-36677902-3{}-1699fe3d53468f%22%7D'.format(
            #     random.randint(100000, 999999), random.randint(100000, 999999), random.randint(100000, 999999)),
            # 'sensorsdata2015jssdkcross': '%7B%22distinct_id%22%3A%22169c78653c6352-04361dab062013-36677902-3686400-169c78653c74f5%22%2C%22%24device_id%22%3A%22169c78653c6352-04361dab062013-36677902-3686400-169c78653c74f5%22%2C%22props%22%3A%7B%22nowStatus%22%3A%22%E6%9C%AA%E7%99%BB%E5%BD%95%22%2C%22platform%22%3A%22WAP%22%2C%22loginid%22%3A%22%22%7D%7D',
            # 'CoreSessionId': '72cd4e2c73e090b77ee1a17d1f371a316a36c61e4cd0832a',

            # 'CoreSessionId': 'b8d5cfbcb9047754bf369f7875fdc622cc266da88f{}'.format(random.randint(100000, 999999)),
            # '_g_sign': 'ce7e3db9d3ea83e029108f3abd{}'.format(random.randint(100000, 999999)),
            # '_g_sign': '7db81cb67ad4b6c582562eb053b90eef',
            # '_gscu_1330024767': '531674760jewe015',
            # '_gscbrs_1330024767': '1',
            # '_gscs_1330024767': '53830576f13lwm15|pv:3',
            # 'sajssdk_2015_cross_new_user': '1',


            # 'JSESSIONID': 'D9BED583964B1C068E64B856A019B123-n1',
            # 'sajssdk_2015_cross_new_user': '1',
            # 'CoreSessionId': '7f5b0e038ff1a3ad75ed881fc27ac2dfbe8efb07ae05759f',
            # '_g_sign': 'bad72ead66456834ca9307ebebb3f78f',
            'sensorsdata2015jssdkcross': '%7B%22distinct_id%22%3A%22{}%22%2C%22%24device_id%22%3A%22{}%22%2C%22props%22%3A%7B%22nowStatus%22%3A%22%E6%9C%AA%E7%99%BB%E5%BD%95%22%2C%22platform%22%3A%22WAP%22%2C%22loginid%22%3A%22%22%7D%7D;'.format(device_id, device_id),
            # '_gscu_1330024767': '53833819cpe7l515',
            # '_gscbrs_1330024767': '1',
            # '_gscs_1330024767': '538338198hpoxm15|pv:2',

            # 'JSESSIONID': '31D7431BC174824A6A3D8793811CF4D3-n1',
            'sajssdk_2015_cross_new_user': '1',
            'CoreSessionId': CoreSessionId,
            '_g_sign': _g_sign,
            # 'sensorsdata2015jssdkcross': '%7B%22distinct_id%22%3A%22169c7d84697f2-040808c5835922-2d604637-304704-169c7d846984f4%22%2C%22%24device_id%22%3A%22169c7d84697f2-040808c5835922-2d604637-304704-169c7d846984f4%22%2C%22props%22%3A%7B%22nowStatus%22%3A%22%E6%9C%AA%E7%99%BB%E5%BD%95%22%2C%22platform%22%3A%22WAP%22%2C%22loginid%22%3A%22%22%7D%7D',
            '_gscu_1330024767': '53836035cerjfr15',
            '_gscbrs_1330024767': '1',
            '_gscs_1330024767': 't57024798n1hh0n15|pv:6',

        })

        http_session.update_headers(headers)

        if search_info.trip_type == 'OW':
            trip_type = 'DC'
        elif search_info.trip_type == 'RT':
            trip_type = 'WF'
        else:
            raise FlightSearchCritical('No available trip_type')

        post_data = {
            'ORGDATE': search_info.from_date,
            'ORGCITY': search_info.from_airport,
            'HCTYPE': trip_type,
            'DSTCITY': search_info.to_airport,
            'BACKDATE': search_info.ret_date if search_info.ret_date else '',
        }

        url = 'http://m.shenzhenair.com/weixin_front/bookit.do?method=queryInterNationalFlightsView'
        result = http_session.request(url=url, method='POST', data=post_data, proxy_pool='A')

        Logger().debug("========== result:{}".format(result.content))
        try:
            result = json.loads(result.content)
        except:
            self.high_req_limit = True
            raise FlightSearchException(err_code='HIGH_REQ_LIMIT')

        if not result['flights'] or result['flights'] == 'no_result':
            Logger().warn('shenzhenair no flight')
            self.search_success = True
            return search_info

        routing_list = result['flights']

        cabin_grade_map = {
            '2': 'Y',
            '1': 'C',
            '0': 'F',
        }

        for routing in routing_list:
            for cabin_info in routing['flight_prices']:

                flight_routing = FlightRoutingInfo()
                flight_routing.product_type = 'DEFAULT'
                routing_number = 1
                is_include_operation_carrier = 0
                cabin_list = cabin_info['class_name'].split('+')
                for seg in routing['flight_go_segments']:
                    flight_segment = FlightSegmentInfo()
                    flight_segment.carrier = 'ZH'
                    if seg.get('is_share') == 'yes':
                        is_include_operation_carrier = 1
                    dep_time = datetime.datetime.strptime(seg['flight_date'] + seg['org_time'],
                                                          '%Y-%m-%d%H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
                    arr_time = datetime.datetime.strptime(seg['arrive_date'] + seg['dst_time'],
                                                          '%Y-%m-%d%H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
                    flight_segment.dep_airport = seg['org_airport']
                    flight_segment.dep_time = dep_time
                    flight_segment.arr_airport = seg['dst_airport']
                    flight_segment.arr_time = arr_time
                    flight_segment.flight_number = seg['flight_no']
                    flight_segment.dep_terminal = ''
                    flight_segment.arr_terminal = ''
                    if seg['stop_city_code'].strip():
                        flight_segment.stop_cities = seg['stop_city_code'].strip()
                    flight_segment.cabin = cabin_list[routing_number - 1]
                    flight_segment.cabin_grade = cabin_grade_map[cabin_info['class_type'].strip()] if cabin_grade_map.get(
                        cabin_info['class_type'].strip()) else 'Y'
                    flight_segment.cabin_count = int(cabin_info['class_storge'])
                    segment_duration = (datetime.datetime.strptime(arr_time, '%Y-%m-%d %H:%M:%S') -
                                        datetime.datetime.strptime(dep_time, '%Y-%m-%d %H:%M:%S')).total_seconds()
                    flight_segment.duration = int(segment_duration / 60)
                    flight_segment.routing_number = routing_number
                    routing_number += 1
                    flight_routing.from_segments.append(flight_segment)

                for seg in routing['flight_back_segments']:
                    flight_segment = FlightSegmentInfo()
                    flight_segment.carrier = 'ZH'
                    if seg.get('is_share') == 'yes':
                        is_include_operation_carrier = 1
                    dep_time = datetime.datetime.strptime(seg['flight_date'] + seg['org_time'],
                                                          '%Y-%m-%d%H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
                    arr_time = datetime.datetime.strptime(seg['arrive_date'] + seg['dst_time'],
                                                          '%Y-%m-%d%H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
                    flight_segment.dep_airport = seg['org_airport']
                    flight_segment.dep_time = dep_time
                    flight_segment.arr_airport = seg['dst_airport']
                    flight_segment.arr_time = arr_time
                    flight_segment.flight_number = seg['flight_no']
                    flight_segment.dep_terminal = ''
                    flight_segment.arr_terminal = ''
                    if seg['stop_city_code'].strip():
                        flight_segment.stop_cities = seg['stop_city_code'].strip()
                    flight_segment.cabin = cabin_list[routing_number - 1]
                    flight_segment.cabin_grade = cabin_grade_map[cabin_info['class_type'].strip()] if cabin_grade_map.get(
                        cabin_info['class_type'].strip()) else 'Y'
                    flight_segment.cabin_count = int(cabin_info['class_storge'])
                    segment_duration = (datetime.datetime.strptime(arr_time, '%Y-%m-%d %H:%M:%S') -
                                        datetime.datetime.strptime(dep_time, '%Y-%m-%d %H:%M:%S')).total_seconds()
                    flight_segment.duration = int(segment_duration / 60)
                    flight_segment.routing_number = routing_number
                    routing_number += 1
                    flight_routing.ret_segments.append(flight_segment)

                flight_routing.adult_price = float(cabin_info['class_cheng_price'])
                flight_routing.adult_tax = float(cabin_info['class_cheng_tax'])

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

                self.product_list.append(flight_routing)

        self.search_success = True