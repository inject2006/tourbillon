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


class TongCheng(ProvderAutoBase):
    timeout = 50  # 请求超时时间
    provider = 'tc_provider'  # 子类继承必须赋
    provider_channel = 'tc_provider_agent'  # 子类继承必须赋
    operation_product_type = '会员折扣'  # 运价类型：0: GDS公布运价 1:GDS私有运价 2:航司官网产品  3:廉价航司产品 4:特价产品
    operation_product_mode = 'A2B'
    pay_channel = 'API'
    provider_token = '5e7ba8bddd7b9648'
    is_display = True
    verify_realtime_search_count = 1
    is_order_directly = True
    is_include_booking_module = True  # 是否包含下单模块
    trip_type_list = ['OW','RT']
    no_flight_ttl = 1800  # 无航班缓存超时时间设定


    CACHE_PR_CONFIG = {
        1: {'cabin_expired_time': 60 * 25, 'cabin_attenuation': 3,'fare_expired_time':86400 * 30},
        2: {'cabin_expired_time': 60 * 10, 'cabin_attenuation': 2,'fare_expired_time':86400 * 20},
        3: {'cabin_expired_time': 60 * 10, 'cabin_attenuation': 1,'fare_expired_time':86400 * 10},
        4: {'cabin_expired_time': 60 * 5, 'cabin_attenuation': 1,'fare_expired_time':86400 * 5},
        5: {'cabin_expired_time': 60 * 5, 'cabin_attenuation': 0,'fare_expired_time':86400},

    }

    search_interval_time = 0

    def __init__(self):
        super(TongCheng, self).__init__()

        # self.pid = 'd049db68f4dd4631b80bb66872ff8bc0' #测试
        # self.secret_code = '64e24362dd2424e1' #测试
        # self.product_type = 35  #测试

        self.pid = 'c406d23b9f934502a58d22c4814324c5'  # 生产
        self.secret_code = 'd90ddf0f8ed18038'  # 生产
        self.product_type = 51  #生产
        self.product_name = 'COMMON'

        self.url = 'http://tcflightopenapi.17usoft.com/flightdistributeapi/dispatcher/api'  # 国际
        # self.url = "http://tcflightopenapi.17usoft.com/internaldistributeapi/cn/api"   #国内

        # self.aes_key = '64e24362dd2424e1' # 测试环境KEY
        self.aes_key = 'd90ddf0f8ed18038'
        self.aes_iv = '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'  # aes iv

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

    def _login(self, http_session, ffp_account_info):
        """
        登陆模块
        :return: 登陆成功的httpResult 对象
        """

        pass

    def _check_login(self, http_session):
        """
        检查登录状态
        :param http_session:
        :return:
        """
        pass

    def _register(self, http_session, pax_info, ffp_account_info):
        """
        注册模块
        """

        pass




    def generate_routing_key(self, route, search_info):


        cabin_str_total = ''
        cabin_grade_str_total = ''
        flight_no_str_total = ''

        cabin_list = []
        cabin_grade_list = []
        flight_no_list = []
        is_include_operation_carrier = 0
        for seg in route['fromSegments']:
            cabin_list.append(seg['cabin'])
            flight_no_list.append(seg['flightNumber'])
            cabin_grade_list.append(seg['cabinGrade'])
            if seg.get('codeShare'):
                is_include_operation_carrier = 1

        cabin_str_total = '-'.join(cabin_list)
        cabin_grade_str_total = '-'.join(cabin_grade_list)
        flight_no_str_total = '-'.join(flight_no_list)

        dep_time = route['fromSegments'][0]['depTime']
        arr_time = route['fromSegments'][-1]['arrTime']

        if route.get('retSegments'):
            cabin_list = []
            cabin_grade_list = []
            flight_no_list = []
            for seg in route['retSegments']:
                cabin_list.append(seg['cabin'])
                flight_no_list.append(seg['flightNumber'])
                cabin_grade_list.append(seg['cabinGrade'])
                if seg.get('codeShare'):
                    is_include_operation_carrier = 1

            cabin_str_total += ",%s" % '-'.join(cabin_list)
            cabin_grade_str_total += ",%s" % '-'.join(cabin_grade_list)
            flight_no_str_total += ",%s" % '-'.join(flight_no_list)

            dep_time = '{},{}'.format(dep_time, route['retSegments'][0]['depTime'])
            arr_time = '{},{}'.format(arr_time, route['retSegments'][-1]['arrTime'])

        chd_price = route['childPrice'] if route.get('childPrice') else route['adultPrice']
        chd_tax = route['childTax'] if route.get('childTax') else route['adultTax']

        rk_info = RoutingKey.serialize(from_airport=route['fromSegments'][0]['depAirport'], dep_time=dep_time,
                                       to_airport=route['fromSegments'][-1]['arrAirport'], arr_time=arr_time,
                                       flight_number=flight_no_str_total,
                                       cabin=cabin_str_total,
                                       cabin_grade=cabin_grade_str_total,
                                       product=self.product_name,
                                       adult_price=float(route['adultPrice']), adult_tax=float(route['adultTax']),
                                       provider_channel=self.provider_channel,
                                       child_price=float(chd_price), child_tax=float(chd_tax),
                                       inf_price=float(chd_price), inf_tax=float(chd_tax),
                                       provider=self.provider,
                                       search_from_airport=search_info.from_airport,
                                       search_to_airport=search_info.to_airport,
                                       from_date=search_info.from_date,
                                       ret_date=search_info.ret_date,
                                       routing_range=search_info.routing_range,
                                       trip_type = search_info.trip_type,
                                       is_include_operation_carrier=is_include_operation_carrier,
                                       is_multi_segments=1 if len(route['fromSegments']) > 1 or route.get('retSegments') else 0  # 带有返程或者单程多段都认为是多程
                                       )

        return rk_info['plain'],rk_info['encrypted']

    def _handle_request(self, http_session, post_data, encrypt=False):

        # Logger().info("==========origin post data: {}".format(post_data))

        params = post_data['params']

        if encrypt:
            params = self.aes_encrypt(json.dumps(params))
        else:
            params = json.dumps(params)

        buf = StringIO.StringIO()
        gzip_obj = gzip.GzipFile(mode='wb', fileobj=buf)
        gzip_obj.write(params)
        gzip_obj.close()
        params = base64.b64encode(buf.getvalue())

        post_data.update({'params': params})

        # Logger().info("============post data: {}".format(post_data))
        result = http_session.request(url=self.url, method='POST', json=post_data, is_direct=True)

        # Logger().info("=========== result: {}".format(result.content))

        buf = StringIO.StringIO(base64.b64decode(result.content))
        gzip_obj = gzip.GzipFile(fileobj=buf)
        result = gzip_obj.read()
        gzip_obj.close()

        # Logger().info("============= gzip unpack: {}".format(result))

        if encrypt:
            result = self.aes_decrypt(result)
            # Logger().info("===========excr res : {}".format(result))

        result = json.loads(result)
        # Logger().info("============final result: {}".format(result))
        return result

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
        if search_info.ret_date:
            ret_date = datetime.datetime.strptime(search_info.ret_date, '%Y-%m-%d').strftime('%Y%m%d')
        else:
            ret_date = ""

        if trip_type == 1:
            chd_count = search_info.chd_count if search_info.chd_count else 1
        else:
            chd_count = search_info.chd_count

        params = {
            # "adultNumber": search_info.adt_count,
            # "childNumber": search_info.chd_count,
            "adultNumber": search_info.adt_count,
            "childNumber": chd_count,
            "fromCity": search_info.from_airport,
            "fromDate": datetime.datetime.strptime(search_info.from_date, '%Y-%m-%d').strftime('%Y%m%d'),
            "productType": self.product_type,
            "retDate": ret_date,
            "toCity": search_info.to_airport,
            "tripType": trip_type,
            # "carrier": "MU",
            # "cabinGrade": "Y"
        }

        post_timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sign = '{}{}{}{}'.format(json.dumps(params), post_timestamp, self.secret_code, self.pid)
        sign = hashlib.md5(sign).hexdigest()

        post_data = {
            "serviceCode": "Search",
            "pid": self.pid,
            "sign": sign,
            "requestID": Random.gen_request_id(),
            "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "businessType": 1,
            "params": params,
        }

        result = self._handle_request(http_session, post_data)
        # Logger().sdebug('====result==== %s'% json.dumps(result))
        if result.get('code') == 'LY200001':
            raise FlightSearchException(err_code='HIGH_REQ_LIMIT')
        elif not result.get('code') == 'LY000000':
            raise FlightSearchException('search flight error!')

        routings = result.get('routings')
        origin_routing_list = []
        for route in routings:
            flight_routing = FlightRoutingInfo()
            flight_routing.routing_key_detail,flight_routing.routing_key = self.generate_routing_key(route, search_info)

            flight_routing.product_type = 'DEFAULT'
            routing_number = 1
            is_include_operation_carrier = 0

            baggage_info_list = route['rule']['baggageInfoList']
            for segment in route['fromSegments']:
                flight_segment = FlightSegmentInfo()
                flight_segment.carrier = segment['carrier']
                if segment.get('codeShare'):
                    is_include_operation_carrier = 1
                dep_time = datetime.datetime.strptime(segment['depTime'], '%Y%m%d%H%M').strftime('%Y-%m-%d %H:%M:%S')
                arr_time = datetime.datetime.strptime(segment['arrTime'], '%Y%m%d%H%M').strftime('%Y-%m-%d %H:%M:%S')
                flight_segment.dep_airport = segment['depAirport']
                flight_segment.dep_time = dep_time

                flight_segment.arr_airport = segment['arrAirport']
                flight_segment.arr_time = arr_time

                # 经停
                stop_city_code_list = []
                stop_airport_code_list = []
                for sl in segment['stops']:
                    stop_airport_code_list.append(sl)
                # flight_segment.stop_cities = "/".join(stop_city_code_list)
                flight_segment.stop_airports = "/".join(stop_airport_code_list)

                flight_segment.flight_number = segment['flightNumber']
                flight_segment.dep_terminal = segment['depTerminal'] if segment.get('depTerminal') else ''
                flight_segment.arr_terminal = segment['arrTerminal'] if segment.get('arrTerminal') else ''
                flight_segment.cabin = segment['cabin']
                flight_segment.cabin_grade = segment['cabinGrade']
                flight_segment.cabin_count = 9
                flight_segment.duration = int(segment['duration'])
                flight_segment.routing_number = routing_number

                # 通过正则获取行李额信息, 获取失败默认无行李
                try:
                    for b in baggage_info_list:
                        if b['segmentNo'] == routing_number:
                            baggage_kg = re.findall(r'.*(\d\d)公斤.*', b['adultBaggage'].encode('utf8')) or re.findall(r'.*(\d)公斤.*', b['adultBaggage'].encode('utf8'))
                            baggage_pc = re.findall(r'.*(\d)件.*', b['adultBaggage'].encode('utf8'))
                            if baggage_kg or baggage_pc:
                                baggage_kg = int(baggage_kg[0]) if baggage_kg else 23
                                baggage_pc = int(baggage_pc[0]) if baggage_pc else 1
                            else:
                                baggage_kg = 0
                                baggage_pc = 0
                            if baggage_kg == 0 or baggage_pc == 0:
                                baggage_kg = 0
                                baggage_pc = 0
                            baggage_info = {'baggage_pc': baggage_pc, 'baggage_kg': baggage_kg}
                            flight_segment.baggage_info = json.dumps(baggage_info)
                            break
                except:
                    import traceback
                    print traceback.format_exc()
                routing_number += 1
                flight_routing.from_segments.append(flight_segment)

            if not route.get('retSegments'):
                route['retSegments'] = []

            for segment in route['retSegments']:
                flight_segment = FlightSegmentInfo()
                flight_segment.carrier = segment['carrier']
                if segment.get('codeShare'):
                    is_include_operation_carrier = 1
                dep_time = datetime.datetime.strptime(segment['depTime'], '%Y%m%d%H%M').strftime('%Y-%m-%d %H:%M:%S')
                arr_time = datetime.datetime.strptime(segment['arrTime'], '%Y%m%d%H%M').strftime('%Y-%m-%d %H:%M:%S')
                flight_segment.dep_airport = segment['depAirport']
                flight_segment.dep_time = dep_time

                flight_segment.arr_airport = segment['arrAirport']
                flight_segment.arr_time = arr_time

                # 经停
                stop_city_code_list = []
                stop_airport_code_list = []
                for sl in segment['stops']:
                    stop_airport_code_list.append(sl)
                # flight_segment.stop_cities = "/".join(stop_city_code_list)
                flight_segment.stop_airports = "/".join(stop_airport_code_list)

                flight_segment.flight_number = segment['flightNumber']
                flight_segment.dep_terminal = segment['depTerminal'] if segment.get('depTerminal') else ''
                flight_segment.arr_terminal = segment['arrTerminal'] if segment.get('arrTerminal') else ''
                flight_segment.cabin = segment['cabin']
                flight_segment.cabin_grade = segment['cabinGrade']
                flight_segment.cabin_count = 9
                flight_segment.duration = int(segment['duration'])
                flight_segment.routing_number = routing_number

                # 通过正则获取行李额信息, 获取失败默认无行李
                try:
                    for b in baggage_info_list:
                        if b['segmentNo'] == routing_number:
                            baggage_kg = re.findall(r'.*(\d\d)公斤.*', b['adultBaggage'].encode('utf8')) or re.findall(r'.*(\d)公斤.*', b['adultBaggage'].encode('utf8'))
                            baggage_pc = re.findall(r'.*(\d)件.*', b['adultBaggage'].encode('utf8'))
                            if baggage_kg or baggage_pc:
                                baggage_kg = int(baggage_kg[0]) if baggage_kg else 23
                                baggage_pc = int(baggage_pc[0]) if baggage_pc else 1
                            else:
                                baggage_kg = 0
                                baggage_pc = 0
                            if baggage_kg == 0 or baggage_pc == 0:
                                baggage_kg = 0
                                baggage_pc = 0
                            baggage_info = {'baggage_pc': baggage_pc, 'baggage_kg': baggage_kg}
                            flight_segment.baggage_info = json.dumps(baggage_info)
                            break
                except:
                    import traceback
                    print traceback.format_exc()
                routing_number += 1
                flight_routing.ret_segments.append(flight_segment)

            flight_routing.adult_price = float(route['adultPrice'])
            flight_routing.adult_tax = float(route['adultTax'])
            flight_routing.child_price = float(route['childPrice'] if route.get('childPrice') else route['adultPrice'])
            flight_routing.child_tax = float(route['childTax'] if route.get('childTax') else route['adultTax'])
            flight_routing.is_include_operation_carrier = is_include_operation_carrier

            route['routing_key'] = flight_routing.routing_key
            origin_routing_list.append(route)
            search_info.assoc_search_routings.append(flight_routing)
        origin_data_key = 'provider_search_origin_routings|{}|{}|{}|{}|{}|{}'.format(
            search_info.from_airport, search_info.to_airport, search_info.from_date, '', '1', self.provider_channel
        )
        TBG.redis_conn.redis_pool.set(origin_data_key, json.dumps(origin_routing_list), 20 * 60)
        return search_info

    def _verify_get_session(self, http_session, search_info):

        # 拿出缓存的搜索结果
        origin_routing_data = []
        origin_data_key = 'provider_search_origin_routings|{}|{}|{}|{}|{}|{}'.format(
            search_info.from_airport, search_info.to_airport, search_info.from_date, '', '1', self.provider_channel
        )
        no_origin_routing = True
        search_routing_key = ''
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
                    search_routing_key = o['routing_key']
                    o.pop('routing_key')
                    routing_info = o
                    break
            except:
                pass
        if not routing_info:
            raise ProviderVerifyFail('NO_VERIFY_ROUTING')

        if search_info.trip_type == 'OW':
            trip_type = 1
        elif search_info.trip_type == 'RT':
            trip_type = 2
        else:
            raise FlightSearchCritical('No available trip_type')

        params = {
            "adultNumber": search_info.adt_count,
            "childNumber": search_info.chd_count,
            "routing": {
                "data": routing_info['data'],
                "fromSegments": routing_info['fromSegments'],
                "retSegments": routing_info['retSegments'] if routing_info.get('retSegments') else [],
            },
            "tripType": trip_type
        }

        post_timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sign = '{}{}{}{}'.format(json.dumps(params), post_timestamp, self.secret_code, self.pid)
        sign = hashlib.md5(sign).hexdigest()

        post_data = {
            "serviceCode": "Verify",
            "pid": self.pid,
            "sign": sign,
            "requestID": Random.gen_request_id(),
            "timestamp": post_timestamp,
            "businessType": 1,
            "params": params,
        }

        result = self._handle_request(http_session, post_data)
        Logger().info("==== tc provider verify result : {}".format(result))
        if not result.get('code') == 'LY000000':
            raise ProviderVerifyFail('verify failed!')

        cabin_count = int(result['maxSeats'])
        if search_info.adt_count + search_info.chd_count > cabin_count:
            raise ProviderVerifyFail('cabin count limit !')
        result['search_routing_key'] = search_routing_key
        return result

    def _verify(self, http_session, search_info):

        Logger().info('verify routing')
        result = self._verify_get_session(http_session, search_info)
        verify_un_key = RoutingKey.trans_cp_key(simple_decrypt(result['search_routing_key']))
        # 将验价结果推到redis list，等待生单使用
        result['verify_datetime'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        verify_data_key = 'provider_verify_result|{}|{}'.format(
            verify_un_key, self.provider_channel
        )
        TBG.redis_conn.redis_pool.lpush(verify_data_key, json.dumps(result))

        flight_routing = FlightRoutingInfo()
        flight_routing.routing_key_detail = simple_decrypt(result['search_routing_key'])
        flight_routing.routing_key = result['search_routing_key']

        flight_routing.product_type = 'DEFAULT'
        routing_number = 1
        baggage_info_list = result['rule']['baggageInfoList']
        for segment in result['routing']['fromSegments']:
            flight_segment = FlightSegmentInfo()
            flight_segment.carrier = segment['carrier']
            dep_time = datetime.datetime.strptime(segment['depTime'], '%Y%m%d%H%M').strftime('%Y-%m-%d %H:%M:%S')
            arr_time = datetime.datetime.strptime(segment['arrTime'], '%Y%m%d%H%M').strftime('%Y-%m-%d %H:%M:%S')
            flight_segment.dep_airport = segment['depAirport']
            flight_segment.dep_time = dep_time

            flight_segment.arr_airport = segment['arrAirport']
            flight_segment.arr_time = arr_time

            # 经停
            stop_city_code_list = []
            stop_airport_code_list = []
            for sl in segment['stops']:
                stop_airport_code_list.append(sl)
            # flight_segment.stop_cities = "/".join(stop_city_code_list)
            flight_segment.stop_airports = "/".join(stop_airport_code_list)

            flight_segment.flight_number = segment['flightNumber']
            flight_segment.dep_terminal = segment['depTerminal'] if segment.get('depTerminal') else ''
            flight_segment.arr_terminal = segment['arrTerminal'] if segment.get('arrTerminal') else ''
            flight_segment.cabin = segment['cabin']
            flight_segment.cabin_grade = segment['cabinGrade']
            flight_segment.cabin_count = result['maxSeats']
            flight_segment.duration = int(segment['duration'])
            flight_segment.routing_number = routing_number

            # 通过正则获取行李额信息, 获取失败默认无行李
            try:
                for b in baggage_info_list:
                    if b['segmentNo'] == routing_number:
                        baggage_kg = re.findall(r'.*(\d\d)公斤.*', b['adultBaggage'].encode('utf8')) or re.findall(
                            r'.*(\d)公斤.*', b['adultBaggage'].encode('utf8'))
                        baggage_pc = re.findall(r'.*(\d)件.*', b['adultBaggage'].encode('utf8'))
                        if baggage_kg or baggage_pc:
                            baggage_kg = int(baggage_kg[0]) if baggage_kg else 23
                            baggage_pc = int(baggage_pc[0]) if baggage_pc else 1
                        else:
                            baggage_kg = 0
                            baggage_pc = 0
                        if baggage_kg == 0 or baggage_pc == 0:
                            baggage_kg = 0
                            baggage_pc = 0
                        baggage_info = {'baggage_pc': baggage_pc, 'baggage_kg': baggage_kg}
                        flight_segment.baggage_info = json.dumps(baggage_info)
                        break
            except:
                import traceback
                print traceback.format_exc()
            routing_number += 1
            flight_routing.from_segments.append(flight_segment)

        if not result['routing'].get('retSegments'):
            result['routing']['retSegments'] = []

        for segment in result['routing']['retSegments']:
            flight_segment = FlightSegmentInfo()
            flight_segment.carrier = segment['carrier']
            dep_time = datetime.datetime.strptime(segment['depTime'], '%Y%m%d%H%M').strftime('%Y-%m-%d %H:%M:%S')
            arr_time = datetime.datetime.strptime(segment['arrTime'], '%Y%m%d%H%M').strftime('%Y-%m-%d %H:%M:%S')
            flight_segment.dep_airport = segment['depAirport']
            flight_segment.dep_time = dep_time

            flight_segment.arr_airport = segment['arrAirport']
            flight_segment.arr_time = arr_time

            # 经停
            stop_city_code_list = []
            stop_airport_code_list = []
            for sl in segment['stops']:
                stop_airport_code_list.append(sl)
            # flight_segment.stop_cities = "/".join(stop_city_code_list)
            flight_segment.stop_airports = "/".join(stop_airport_code_list)

            flight_segment.flight_number = segment['flightNumber']
            flight_segment.dep_terminal = segment['depTerminal'] if segment.get('depTerminal') else ''
            flight_segment.arr_terminal = segment['arrTerminal'] if segment.get('arrTerminal') else ''
            flight_segment.cabin = segment['cabin']
            flight_segment.cabin_grade = segment['cabinGrade']
            flight_segment.cabin_count = result['maxSeats']
            flight_segment.duration = int(segment['duration'])
            flight_segment.routing_number = routing_number

            # 通过正则获取行李额信息, 获取失败默认无行李
            try:
                for b in baggage_info_list:
                    if b['segmentNo'] == routing_number:
                        baggage_kg = re.findall(r'.*(\d\d)公斤.*', b['adultBaggage'].encode('utf8')) or re.findall(
                            r'.*(\d)公斤.*', b['adultBaggage'].encode('utf8'))
                        baggage_pc = re.findall(r'.*(\d)件.*', b['adultBaggage'].encode('utf8'))
                        if baggage_kg or baggage_pc:
                            baggage_kg = int(baggage_kg[0]) if baggage_kg else 23
                            baggage_pc = int(baggage_pc[0]) if baggage_pc else 1
                        else:
                            baggage_kg = 0
                            baggage_pc = 0
                        if baggage_kg == 0 or baggage_pc == 0:
                            baggage_kg = 0
                            baggage_pc = 0
                        baggage_info = {'baggage_pc': baggage_pc, 'baggage_kg': baggage_kg}
                        flight_segment.baggage_info = json.dumps(baggage_info)
                        break
            except:
                import traceback
                print traceback.format_exc()
            routing_number += 1
            flight_routing.ret_segments.append(flight_segment)

        flight_routing.adult_price = float(result['routing']['adultPrice'])
        flight_routing.adult_tax = float(result['routing']['adultTax'])
        flight_routing.child_price = float(result['routing']['childPrice'] if result['routing'].get('childPrice') else result['routing']['adultPrice'])
        flight_routing.child_tax = float(result['routing']['childTax'] if result['routing'].get('childTax') else result['routing']['adultTax'])

        Logger().debug("=============== return flight routing :{}=========".format(flight_routing))
        return flight_routing

    def _order_get_session(self, http_session, order_info, fresh=None):

        if fresh == 'NEW':
            # 需要最新验价结果，直接返回最新验价
            verify_result = self._verify_get_session(http_session, order_info)
            return verify_result

        # 从验价session池获取验价结果
        if order_info.verify_routing_key:
            unkey = RoutingKey.trans_cp_key(simple_decrypt(order_info.verify_routing_key))
        else:
            unkey = RoutingKey.trans_cp_key(simple_decrypt(order_info.routing.routing_key))
        verify_data_key = 'provider_verify_result|{}|{}'.format(unkey, self.provider_channel)
        verify_result = {}
        while True:
            try:
                verify_result_json = TBG.redis_conn.redis_pool.rpop(verify_data_key)
                Logger().debug("======== verify result cache json: {}===".format(verify_result_json))
                if not verify_result_json:
                    break
                verify_result = json.loads(verify_result_json)
                if verify_result['verify_datetime'] and datetime.datetime.now() - datetime.timedelta(seconds=20*60) \
                    < datetime.datetime.strptime(verify_result['verify_datetime'], '%Y-%m-%d %H:%M:%S'):
                    return verify_result
                else:
                    continue
            except:
                pass
        if not verify_result:
            # 验价session池为空，获取最新验价
            verify_result = self._verify_get_session(http_session, order_info)
            return verify_result

    def _post_to_order(self, http_session, order_info, session_data):

        # 判断单程返程
        if order_info.trip_type == 'OW':
            trip_type = "1"
        elif order_info.trip_type == 'RT':
            trip_type = "2"
        else:
            raise FlightSearchCritical('No available trip_type')

        contact = order_info.contacts[0]
        params = {
            "contract": {
                "address": contact.name,
                "email": contact.email,
                "mobile": TBG.global_config['OPERATION_CONTACT_MOBILE'],
                "name": contact.name,
                "postcode": contact.postcode,
            },
            "passengers": [{
                               "name": "{}/{}".format(p.last_name, p.first_name),
                               "birthday": p.birthdate.replace('-', ''),
                               "cardExpired": p.card_expired.replace('-', ''),
                               "cardIssuePlace": p.card_issue_place,
                               "cardNum": p.selected_card_no,
                               "cardType": p.used_card_type,
                               "gender": p.gender,
                               "mobile": TBG.global_config['OPERATION_CONTACT_MOBILE'],
                               "nationality": p.nationality,
                               "passengerType": p.current_age_type(),
                           } for p in order_info.passengers],
            "routing": {
                "data": session_data['routing']['data'],
                "fromSegments": session_data['routing']['fromSegments'],
                "retSegments": session_data['routing']['retSegments'] if session_data['routing'].get('retSegments') else [],
            },
            "sessionId": session_data['sessionId'],
            "tripType": trip_type,
        }

        post_timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sign = '{}{}{}{}'.format(json.dumps(params), post_timestamp, self.secret_code, self.pid)
        sign = hashlib.md5(sign).hexdigest()

        post_data = {
            "serviceCode": "Order",
            "pid": self.pid,
            "sign": sign,
            "requestID": Random.gen_request_id(),
            "timestamp": post_timestamp,
            "businessType": 1,
            "params": params
        }

        result = self._handle_request(http_session, post_data, encrypt=True)
        Logger().info("==== tc provider order result: {}".format(result))
        order_info.extra_data = json.dumps(result)

        return result

    def _booking(self, http_session, order_info):

        order_info.provider_order_status = 'BOOK_FAIL'
        # 确认航班
        Logger().info('confirm flight ')

        session_data = self._order_get_session(http_session, order_info)

        adult_num = 0
        children_num = 0
        inf_num = 0
        order_info.passengers = sorted(order_info.passengers,
                                       key=lambda x: datetime.datetime.strptime(x.birthdate, '%Y-%m-%d'))
        for passenger in order_info.passengers:
            age_type = passenger.current_age_type(order_info.from_date)
            if age_type == 'ADT':
                adult_num += 1
            elif age_type == 'CHD':
                children_num += 1
            elif age_type == 'INF':
                inf_num += 1

        result = self._post_to_order(http_session, order_info, session_data)

        if result.get('code') == 'LY410004':
            # 如果验价session过期，生成最新验价session，来order
            session_data = self._order_get_session(http_session, order_info, fresh='NEW')
            result = self._post_to_order(http_session, order_info, session_data)

        if not result.get('code') == 'LY000000':
            raise BookingException('booking failed!')

        total_price = (result['routing']['adultPrice'] + result['routing']['adultTax']) * adult_num
        if result['routing'].get('childPrice'):
            total_price += (result['routing']['childPrice'] + result['routing']['childTax']) * children_num

        order_info.provider_order_status = 'BOOK_SUCCESS_AND_WAITING_PAY'
        order_info.provider_order_id = result['orderNo']
        order_info.provider_price = total_price
        order_info.pnr_code = result['pnrCode']

        if order_info.trip_type == 'OW':
            trip_type = "1"
        elif order_info.trip_type == 'RT':
            trip_type = "2"
        else:
            raise FlightSearchCritical('No available trip_type')
        order_rsp_data = json.loads(order_info.extra_data)
        params = {
            'externalOrderNo': order_info.provider_order_id,
            'orderNo': order_info.provider_order_id,
            'pnrCode': order_info.pnr_code,
            'routing': {
                'data': order_rsp_data['routing']['data'],
                'fromSegments': order_rsp_data['routing']['fromSegments'],
                'retSegments':order_rsp_data['routing']['retSegments'] if order_rsp_data['routing'].get(
                    'retSegments') else []
            },
            'sessionId': order_rsp_data['sessionId'],
            "tripType": trip_type,
        }

        post_timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sign = '{}{}{}{}'.format(json.dumps(params), post_timestamp, self.secret_code, self.pid)
        sign = hashlib.md5(sign).hexdigest()

        post_data = {
            "serviceCode": "PayCheck",
            "pid": self.pid,
            "sign": sign,
            "requestID": Random.gen_request_id(),
            "timestamp": post_timestamp,
            "businessType": 1,
            "params": params
        }

        result = self._handle_request(http_session, post_data)
        Logger().info("==== tc provider paycheck result: {}".format(result))

        if not result.get('code') == 'LY000000':
            raise BookingException('paycheck failed !')

        Logger().info('booking success')
        return order_info

    def _check_order_status(self, http_session, ffp_account_info, order_info):
        """
        检查订单状态
        :param http_session:
        :param order_id:
        :return: 返回订单状态
        """

        pass

    def _get_coupon(self, http_session, ffp_account_info):
        """
        获取VISA红包
        :return:
        """

        pass

    def _pay(self, order_info, http_session, pay_dict):
        """
        支付
        :param http_session:
        :return:
        """
        if order_info.trip_type == 'OW':
            trip_type = "1"
        elif order_info.trip_type == 'RT':
            trip_type = "2"
        else:
            raise FlightSearchCritical('No available trip_type')
        order_rsp_data = json.loads(order_info.extra_data)
        params = {
            'externalOrderNo': order_info.provider_order_id,
            'orderNo': order_info.provider_order_id,
            'pnrCode': order_info.pnr_code,
            'routing': {
                'data': order_rsp_data['routing']['data'],
                'fromSegments': order_rsp_data['routing']['fromSegments'],
                'retSegments':order_rsp_data['routing']['retSegments'] if order_rsp_data['routing'].get(
                    'retSegments') else []
            },
            'sessionId': order_rsp_data['sessionId'],
            "tripType": trip_type,
        }

        post_timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sign = '{}{}{}{}'.format(json.dumps(params), post_timestamp, self.secret_code, self.pid)
        sign = hashlib.md5(sign).hexdigest()

        post_data = {
            "serviceCode": "PayCheck",
            "pid": self.pid,
            "sign": sign,
            "requestID": Random.gen_request_id(),
            "timestamp": post_timestamp,
            "businessType": 1,
            "params": params
        }

        result = self._handle_request(http_session, post_data)

        if not result.get('code') == 'LY000000':
            raise PayException('paycheck failed !')

        params = {
            "data": result['routing']['data'],
            'externalOrderNo': order_info.provider_order_id,
            "orderNo": result['orderNo'],
            "pnrCode": result['pnrCode'],
            "price": order_rsp_data['routing']['adultPrice'] + order_rsp_data['routing']['childPrice'] if order_rsp_data['routing'].get('childPrice') else order_rsp_data['routing']['adultPrice'],
            "sessionId": result['sessionId'],
            "tax": order_rsp_data['routing']['adultTax'] + order_rsp_data['routing']['childTax'] if order_rsp_data['routing'].get('childTax') else order_rsp_data['routing']['adultTax'],
        }

        post_timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sign = '{}{}{}{}'.format(json.dumps(params), post_timestamp, self.secret_code, self.pid)
        sign = hashlib.md5(sign).hexdigest()

        post_data = {
            "serviceCode": "Ticket",
            "pid": self.pid,
            "sign": sign,
            "requestID": Random.gen_request_id(),
            "timestamp": post_timestamp,
            "businessType": 1,
            "params": params
        }

        result = self._handle_request(http_session, post_data)

        if not result.get('code') == 'LY000000':
            raise PayException('ticket api error !')

        Logger().info('pay success')
        return pay_dict['api']

    def _before_notice_issue_interface(self, req_body):
        """

        :param req_body:
        :return:
        """
        try:
            # buf = StringIO.StringIO()
            # gzip_obj = gzip.GzipFile(mode='wb', fileobj=buf)
            # gzip_obj.write(json.dumps({"code": 'LY000001', "msg": "failed"}))
            # gzip_obj.close()
            # self.final_result = base64.b64encode(buf.getvalue())

            self.final_result = json.dumps({"code": 'LY000001', "msg": "failed"})

            Logger().info("======= tc notice issue req body: {}".format(req_body))
            data = json.loads(req_body)
            params = data['params']

            # buf = StringIO.StringIO(base64.b64decode(params))
            # gzip_obj = gzip.GzipFile(fileobj=buf)
            # params = json.loads(gzip_obj.read())
            # gzip_obj.close()

            # sign = '{}{}{}{}'.format(json.dumps(params), data['timestamp'], self.secret_code, self.pid)
            # sign = hashlib.md5(sign).hexdigest()
            #
            # provider_order_id = params['orderNo']
            #
            # if sign == data['sign']:
            #     return params, provider_order_id
            # else:
            #     Logger().warn(" tongcheng provider notice issue sign error ======")
            #     Logger().info(sign)
            #     Logger().info(data['sign'])
            #     return None, provider_order_id

            provider_order_id = params['orderNo']
            return params, provider_order_id

        except Exception as e:
            Logger().serror(str(e))
            return None, None

    def _after_notice_issue_interface(self, sub_order, notice_data):
        """

        :param order_info: order_info class
        :return:
        """

        try:
            ticket_info_list = notice_data['ticketNoItems']
            for info in ticket_info_list:
                # 填入票号
                Logger().sinfo("============ tc provider start to update ticket and status =======")
                Logger().sinfo(json.dumps(info))
                sql = 'UPDATE person_2_flight_order as a inner join person2flightorder_suborder as b on a.id = b.person2flightorder set a.ticket_no = "{}" where b.suborder = {} and a.used_card_no = "{}"'.format(
                    info['tktNo'], sub_order.id, info['idNo'])
                TBG.tourbillon_db.execute(sql)
                commit()
                flush()
                # 变更子订单状态
                TBG.tourbillon_db.execute(
                    'update sub_order set provider_order_status="{}" where id={}'.format('ISSUE_SUCCESS', sub_order.id))
                commit()
                flush()

            # buf = StringIO.StringIO()
            # gzip_obj = gzip.GzipFile(mode='wb', fileobj=buf)
            # gzip_obj.write(json.dumps({"code": 'LY000000', "msg": "success"}))
            # gzip_obj.close()
            # self.final_result = base64.b64encode(buf.getvalue())
            self.final_result = json.dumps({"code": 'LY000000', "msg": "success"})
        except Exception as e:

            Logger().serror(str(e))

            # buf = StringIO.StringIO()
            # gzip_obj = gzip.GzipFile(mode='wb', fileobj=buf)
            # gzip_obj.write(json.dumps({"code": 'LY000001', "msg": "failed"}))
            # gzip_obj.close()
            # self.final_result = base64.b64encode(buf.getvalue())

            self.final_result = json.dumps({"code": 'LY000001', "msg": "failed"})


class TongCheng58(TongCheng):
    timeout = 50  # 请求超时时间
    provider = 'tc_provider'  # 子类继承必须赋
    provider_channel = 'tc_provider_agent_58'  # 子类继承必须赋
    operation_product_type = '会员折扣'  # 运价类型：0: GDS公布运价 1:GDS私有运价 2:航司官网产品  3:廉价航司产品 4:特价产品
    operation_product_mode = 'A2B'
    pay_channel = 'API'
    provider_token = '5e7ba8bddd7b9648'
    is_display = True
    verify_realtime_search_count = 1
    is_order_directly = True

    def __init__(self):
        super(TongCheng58, self).__init__()

        # self.pid = 'd049db68f4dd4631b80bb66872ff8bc0' #测试
        # self.secret_code = '64e24362dd2424e1' #测试
        # self.product_type = 35  #测试

        self.pid = 'c406d23b9f934502a58d22c4814324c5'  # 生产
        self.secret_code = 'd90ddf0f8ed18038'  # 生产
        self.product_type = 58  #生产
        self.product_name = 'LOWPRICE'

        self.url = 'http://tcflightopenapi.17usoft.com/flightdistributeapi/dispatcher/api'  # 国际
        # self.url = "http://tcflightopenapi.17usoft.com/internaldistributeapi/cn/api"   #国内

        # self.aes_key = '64e24362dd2424e1' # 测试环境KEY
        self.aes_key = 'd90ddf0f8ed18038'
        self.aes_iv = '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'  # aes iv
