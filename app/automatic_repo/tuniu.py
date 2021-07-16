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
from ..controller.pokeman import Pokeman


class Tuniu(ProvderAutoBase):
    timeout = 50  # 请求超时时间
    provider = 'tuniu_provider'  # 子类继承必须赋
    provider_channel = 'tuniu_provider_agent'  # 子类继承必须赋
    operation_product_type = '会员折扣'  # 运价类型：0: GDS公布运价 1:GDS私有运价 2:航司官网产品  3:廉价航司产品 4:特价产品
    operation_product_mode = 'A2B'
    pay_channel = 'ALIPAY'
    provider_token = '5e7ba8bddd7b9648'
    is_display = True
    verify_realtime_search_count = 1
    is_order_directly = True
    is_include_booking_module = True  # 是否包含下单模块
    no_flight_ttl = 1800  # 无航班缓存超时时间设定



    CACHE_PR_CONFIG = {
        1: {'cabin_expired_time': 60 * 10, 'cabin_attenuation': 3,'fare_expired_time':86400 * 30},
        2: {'cabin_expired_time': 60 * 10, 'cabin_attenuation': 2,'fare_expired_time':86400 * 20},
        3: {'cabin_expired_time': 60 * 5, 'cabin_attenuation': 1,'fare_expired_time':86400 * 10},
        4: {'cabin_expired_time': 60 * 5, 'cabin_attenuation': 1,'fare_expired_time':86400 * 5},
        5: {'cabin_expired_time': 60 * 5, 'cabin_attenuation': 0,'fare_expired_time':86400},

    }

    search_interval_time = 0

    def __init__(self):
        super(Tuniu, self).__init__()

        self.verify_tries = 3
        self.purchase_id = 22643
        self.cust_id = '84098424'  #生产
        # self.cust_id = '51613061'  #测试
        self.secret_key = 'MIIBVAIBADANBgkqhkiG9w0BAQEFAASCAT4wggE6AgEAAkEApkhk2pv2i+bhFBSHIFiLtEFuHI2Qts+2/5XloBxSpv/JTWaf5glgjf1xceurIpcNeFeEUp5GOHeRqsmj7GXbJwIDAQABAkBy8cI91+gjJ5NZZSNPecYA8eXi+P0bUhTnMsBL4KhF5ZRfVnYkPkpoVCJiR9jN5Bsg+R6X3VPvIz+kAKaWBqoJAiEA8jIYQXAUbw07nAShw7e04xKurGLJ5gHVBfvsMVlW0vMCIQCvwqU4PXrY/1asPE/B/OJ801F+yg3eXaRDxlNfIblb/QIgEcDiTkms9cb+i507TmF0/QAtla1YJ2gS+XFSCvwFhUkCIHZUyt25bqsIBfeBx4ToWCgIMdb1/C5Yx04mCV2EHAKVAiEApfrLHzw8sfnwINDwNBggOR+iI3OWuZabFsend3HwgNA='

        # self.base_url = 'http://ats-atd-api.tuniu-sit.com/atd/intl/'  # 测试
        self.base_url = 'http://silkroad.tuniu.com/atd/intl/'   # 生产


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

    def _flight_search(self, http_session, search_info):
        """
        航班爬取模块，
        TODO :目前只考虑单程
        :return:
        """

        Logger().debug('search flight')

        have_routing_result = None

        data = {
            "systemId": 93,
            "direct": "0",
            "adultQuantity": search_info.adt_count,
            "childQuantity": search_info.chd_count if search_info.chd_count != 0 else 1,
            # "babyQuantity": search_info.inf_count if search_info.inf_count != 0 else 1,
            "babyQuantity": search_info.inf_count,
            "cabinClass": "0",
            "segmentList":[{
                "dCityIataCode": search_info.from_airport,
                "aCityIataCode": search_info.to_airport,
                "departDate": search_info.from_date
            }],
            "channelCount": 0,
            "pollTag": 0,
            "topGroupName" : ""
        }

        sign = hashlib.md5('{}{}{}'.format(self.secret_key, json.dumps(data, separators=(',', ':')), self.secret_key)).hexdigest()

        origin_post_data = {
            'purchaseId': self.purchase_id,
            'data': data,
            'sign': sign,
        }
        post_data = json.dumps(origin_post_data, separators=(',', ':'))
        Logger().debug("========= post data: {} ===".format(post_data))
        url = '{}search'.format(self.base_url)
        headers = {'Content-Type': 'application/json;charset=utf-8'}
        result = http_session.request(url=url, data=post_data, method='POST', headers=headers, is_direct=True)
        high_req_limit = False
        try:
            if json.loads(base64.b64decode(result.content))['errorCode'] == 899058:
                high_req_limit = True
        except:
            pass
        if high_req_limit:
            raise FlightSearchException(err_code='HIGH_REQ_LIMIT')

        Logger().debug("====== search result:{} ==".format(result.content))
        result = json.loads(result.content)
        if result.get('errorCode') == 101203:
            Logger().warn('tuniu no flight')
            return search_info

        if not result.get('errorCode') == 895000:
            Logger().error(result.get('msg'))
            raise FlightSearchException('tuniu flight search error')

        if result['data'].get('fareList'):
            have_routing_result = dict(result)

        for times in xrange(10):
            if result['data']['needQueryMore'] == 0:
                # 还需要轮询
                origin_post_data['data']['channelCount'] = result['data']['channelCount']
                origin_post_data['data']['polltag'] = 1
                data = origin_post_data['data']
                sign = hashlib.md5('{}{}{}'.format(self.secret_key, json.dumps(data, separators=(',', ':')),
                                                   self.secret_key)).hexdigest()
                origin_post_data['sign'] = sign
                post_data = json.dumps(origin_post_data, separators=(',', ':'))
                Logger().debug("========= post data: {} ===".format(post_data))
                result = http_session.request(url=url, data=post_data, method='POST', headers=headers, is_direct=True)
                try:
                    if json.loads(base64.b64decode(result.content))['errorCode'] == 899058:
                        high_req_limit = True
                except:
                    pass
                if high_req_limit:
                    raise FlightSearchException(err_code='HIGH_REQ_LIMIT')
                Logger().debug("====== search result:{} ==".format(result.content))
                result = json.loads(result.content)
            elif result.get('errorCode') == 101203:
                # 明确无航班
                Logger().warn('tuniu no flight')
                return search_info
            else:
                # 不需要继续轮询
                break

            if result['data'].get('fareList'):
                have_routing_result = dict(result)
            time.sleep(1)

        if not have_routing_result:
            Logger().warn('tuniu no flight')
            return search_info
        result = have_routing_result
        routing_list = result['data']['fareList']
        flight_segment_info_list = result['data']['flightOptionList']
        base_segment_info_list = result['data']['flightList']
        origin_routing_list = []

        for routing in routing_list:
            flight_number = routing['flightOptions'][0]['flightNos']
            flight_segment_info = flight_segment_info_list.get(flight_number)
            if not flight_segment_info:
                continue
            # if not routing['flightPriceList'][0]['solutionId'] in [8594, 41363]:
            #     continue
            seg_list = flight_segment_info['flightItems']
            flight_routing = FlightRoutingInfo()
            flight_routing.product_type = 'DEFAULT'
            routing_number = 1
            is_include_operation_carrier = 0
            for seg in seg_list:
                segment = base_segment_info_list.get(seg['flightNo'])
                if not segment:
                    break

                flight_segment = FlightSegmentInfo()
                flight_segment.carrier = routing['flightPriceList'][0]['mainAirCom']

                if segment.get('codeShare'):
                    is_include_operation_carrier = 1

                dep_time = datetime.datetime.strptime(segment['departureDate'] + segment['departureTime'],
                                                      '%Y-%m-%d%H:%M').strftime('%Y-%m-%d %H:%M:%S')
                arr_time = datetime.datetime.strptime(segment['arrivalDate'] + segment['arrivalTime'],
                                                      '%Y-%m-%d%H:%M').strftime('%Y-%m-%d %H:%M:%S')
                flight_segment.dep_airport = segment['dCityIataCode']
                flight_segment.dep_time = dep_time

                flight_segment.arr_airport = segment['aPortIataCode']
                flight_segment.arr_time = arr_time

                # 经停
                # stop_city_code_list = []
                # stop_airport_code_list = []
                # for sl in segment['stops']:
                #     stop_airport_code_list.append(sl)
                # flight_segment.stop_cities = "/".join(stop_city_code_list)
                flight_segment.stop_airports = "/".join(segment['stopPoints'])
                flight_segment.flight_number = segment['flightNo']
                flight_segment.dep_terminal = segment['dTerminal'] if segment.get('dTerminal', '').strip() else ''
                flight_segment.arr_terminal = segment['aTerminal'] if segment.get('aTerminal', '').strip() else ''
                selected_cabin_seg = [
                seg_cabin for seg_cabin in routing['flightPriceList'][0]['priceJourneyCabinList'][0]['priceFlightCabinList'] if seg_cabin['flightNo'] == segment['flightNo']][0]
                cabin_grade_mapping = {
                    1: 'Y',
                    2: 'C',
                    3: 'F',
                    4: 'Y'
                }
                flight_segment.cabin = selected_cabin_seg['cabinClass']
                flight_segment.cabin_grade = cabin_grade_mapping[selected_cabin_seg['seatTypeCode']]
                flight_segment.cabin_count = int(selected_cabin_seg['seatStatus'])
                duration = segment['duration']
                if len(duration.split(':')) == 2:
                    duration = int(duration.split(':')[0]) * 60 + int(duration.split(':')[1])
                elif len(duration.split(':')) == 1:
                    duration = int(duration)
                flight_segment.duration = duration
                flight_segment.routing_number = routing_number
                routing_number += 1
                flight_routing.from_segments.append(flight_segment)

            adult_price = 0.0
            adult_tax = 0.0
            child_price = 0.0
            child_tax = 0.0
            inf_price = 0.0
            inf_tax = 0.0
            for p in routing['flightPriceList'][0]['fareBreakdownList']:
                if p['adultQuantity'] == 1:
                    adult_price += p['baseFare']
                    adult_tax += p['taxes']
                elif p['childQuantity'] == 1:
                    child_price += p['baseFare']
                    child_tax += p['taxes']
                elif p['babyQuantity'] == 1:
                    inf_price += p['baseFare']
                    inf_tax += p['taxes']
            flight_routing.adult_price = adult_price
            flight_routing.adult_tax = adult_tax
            flight_routing.child_price = child_price
            flight_routing.child_tax = child_tax
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
                                           adult_price=adult_price, adult_tax=adult_tax,
                                           provider_channel=self.provider_channel,
                                           child_price=child_price, child_tax=child_tax,
                                           inf_price=inf_price if inf_price else child_price,
                                           inf_tax=inf_tax if inf_tax else child_tax,
                                           provider=self.provider,
                                           search_from_airport=search_info.from_airport,
                                           search_to_airport=search_info.to_airport,
                                           from_date=search_info.from_date,
                                           routing_range=search_info.routing_range,
                                           trip_type=search_info.trip_type,
                                           is_include_operation_carrier=is_include_operation_carrier,
                                           is_multi_segments=1 if len(flight_routing.from_segments) > 1 else 0
                                           )

            flight_routing.routing_key_detail = rk_info['plain']
            flight_routing.routing_key = rk_info['encrypted']

            routing['routing_key'] = flight_routing.routing_key
            routing['queryId'] = result['data']['queryId']
            routing['segment_info'] = flight_routing
            origin_routing_list.append(routing)
            search_info.assoc_search_routings.append(flight_routing)

        origin_data_key = 'provider_search_origin_routings|{}|{}|{}|{}|{}|{}|{}|{}'.format(
            search_info.from_airport, search_info.to_airport, search_info.from_date, '', '1',
            search_info.adt_count, search_info.chd_count, self.provider_channel
        )
        exist_data_set = TBG.redis_conn.redis_pool.get(origin_data_key)
        exist_data_set = json.loads(exist_data_set) if exist_data_set else []
        exist_data_set = [e for e in exist_data_set if (datetime.datetime.now() - datetime.datetime.strptime(
            e['create_time'], '%Y-%m-%d %H:%M:%S')).total_seconds() < 4 * 60]
        exist_data_set.append({
            'data': origin_routing_list,
            'create_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        TBG.redis_conn.redis_pool.set(origin_data_key, json.dumps(exist_data_set), 4 * 60)
        Logger().debug('assoc_search_routings:{}'.format(search_info.assoc_search_routings))
        return search_info

    def _verify_get_session(self, http_session, search_info):

        origin_data_key = 'provider_search_origin_routings|{}|{}|{}|{}|{}|{}|{}|{}'.format(
            search_info.from_airport, search_info.to_airport, search_info.from_date, '', '1',
            search_info.adt_count, search_info.chd_count, self.provider_channel
        )

        exist_data_set = TBG.redis_conn.redis_pool.get(origin_data_key)
        Logger().debug("======== search result cache json: {}===".format(exist_data_set))
        if not exist_data_set:
            # 如果没有缓存过的搜索结果，实时搜索获取routing
            Logger().info('===== have no origin routings. search_key:{}'.format(origin_data_key))
            self.flight_search(http_session, search_info, cache_mode='REALTIME')
            exist_data_set = TBG.redis_conn.redis_pool.get(origin_data_key)
            if not exist_data_set:
                raise ProviderVerifyFail('NO_ORIGIN_ROUTING')
            else:
                origin_routing_data = json.loads(exist_data_set)[0]['data']
                TBG.redis_conn.redis_pool.delete(origin_data_key)
        else:
            exist_data_set = json.loads(exist_data_set)
            exist_data_set = [e for e in exist_data_set if (datetime.datetime.now() - datetime.datetime.strptime(
                e['create_time'], '%Y-%m-%d %H:%M:%S')).total_seconds() < 4 * 60]
            origin_routing_data = exist_data_set[0]['data']
            if exist_data_set[1:]:
                TBG.redis_conn.redis_pool.set(origin_data_key, json.dumps(exist_data_set[1:]), 4 * 60)
            else:
                TBG.redis_conn.redis_pool.delete(origin_data_key)

        routing_info = {}
        if search_info.verify_routing_key:
            verify_un_key = RoutingKey.trans_cp_key(simple_decrypt(search_info.verify_routing_key))
        else:
            verify_un_key = RoutingKey.trans_cp_key(simple_decrypt(search_info.routing.routing_key))
        for o in origin_routing_data:
            try:
                search_un_key = RoutingKey.trans_cp_key(simple_decrypt(o['routing_key']))
                if search_un_key == verify_un_key:
                    # o.pop('routing_key')
                    routing_info = o
                    break
            except:
                pass
        if not routing_info:
            raise ProviderVerifyFail('NO_ORIGIN_ROUTING')

        return routing_info

    def _verify(self, http_session, search_info):

        origin_routing_info = self._verify_get_session(http_session, search_info)

        data = {
            "systemId": 93,
            "channelId": origin_routing_info['flightPriceList'][0]['vendorId'],
            "queryId": origin_routing_info['queryId'],
            "flightNos": origin_routing_info['flightOptions'][0]['flightNos'],
            "fareBreakdownList": [{
                                      'baseFare': b['baseFare'],
                                      'taxes': b['taxes'],
                                      'adultQuantity': b['adultQuantity'],
                                      'childQuantity': b['childQuantity'],
                                      'babyQuantity': b['babyQuantity'],
                                  } for b in origin_routing_info['flightPriceList'][0]['fareBreakdownList']],
            "type": 3,
        }
        sign = hashlib.md5('{}{}{}'.format(self.secret_key, json.dumps(data, separators=(',', ':')),
                                           self.secret_key)).hexdigest()
        origin_post_data = {
            "purchaseId": self.purchase_id,
            "sign": sign,
            "data": data
        }

        post_data = json.dumps(origin_post_data, separators=(',', ':'))
        Logger().info("========= verify post data: {} ===".format(post_data))
        url = '{}checkCabinAndPriceNew'.format(self.base_url)
        headers = {'Content-Type': 'application/json;charset=utf-8'}
        verify_result = http_session.request(url=url, data=post_data, method='POST', headers=headers, is_direct=True)
        verify_result = json.loads(base64.b64decode(verify_result.content))
        Logger().info("====== verify result:{} ==".format(json.dumps(verify_result)))

        if not verify_result.get('errorCode') == 895000:
            raise ProviderVerifyFail('verify failed!')

        cabin_count = verify_result['data']['vendorList'][0]['jouneyList'][0]['priceList'][0]['seatStatus']
        if search_info.adt_count + search_info.chd_count > cabin_count:
            raise ProviderVerifyFail('cabin count limit !')

        verify_result_key = 'provider_verify_result|{}|{}|{}|{}|{}|{}|{}|{}'.format(
            search_info.from_airport, search_info.to_airport, search_info.from_date, '', '1',
            search_info.adt_count, search_info.chd_count, self.provider_channel
        )
        TBG.redis_conn.redis_pool.lpush(verify_result_key, json.dumps({
            'data': origin_routing_info,
            'create_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }))

        flight_routing = FlightRoutingInfo()
        flight_routing.product_type = 'DEFAULT'
        for seg in origin_routing_info['segment_info']['from_segments']:

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
            flight_segment.cabin_count = verify_result['data']['vendorList'][0]['jouneyList'][0]['priceList'][0]['seatStatus']
            flight_segment.duration = seg['duration']
            flight_segment.routing_number = seg['routing_number']
            flight_routing.from_segments.append(flight_segment)

        # 补充舱位和舱等
        verify_adult_price = verify_result['data']['vendorList'][0]['jouneyList'][0]['priceList'][0]['adultPrice'] - \
                             verify_result['data']['vendorList'][0]['jouneyList'][0]['priceList'][0]['adultTax']
        verify_adult_tax = verify_result['data']['vendorList'][0]['jouneyList'][0]['priceList'][0]['adultTax']
        verify_child_price = verify_result['data']['vendorList'][0]['jouneyList'][0]['priceList'][0]['childPrice'] - \
                             verify_result['data']['vendorList'][0]['jouneyList'][0]['priceList'][0]['childTax']
        verify_child_tax = verify_result['data']['vendorList'][0]['jouneyList'][0]['priceList'][0]['childTax']
        verify_inf_price = verify_result['data']['vendorList'][0]['jouneyList'][0]['priceList'][0]['babyPrice'] - \
                           verify_result['data']['vendorList'][0]['jouneyList'][0]['priceList'][0]['babyTax']
        verify_inf_tax = verify_result['data']['vendorList'][0]['jouneyList'][0]['priceList'][0]['babyTax']

        flight_routing.adult_price = verify_adult_price
        flight_routing.adult_tax = verify_adult_tax
        flight_routing.child_price = verify_child_price
        flight_routing.child_tax = verify_child_tax
        flight_routing.routing_key_detail = origin_routing_info['segment_info']['routing_key_detail']
        flight_routing.routing_key = origin_routing_info['segment_info']['routing_key']
        rk_info = RoutingKey.serialize(from_airport=origin_routing_info['segment_info']['from_segments'][0]['dep_airport'],
                                       dep_time=datetime.datetime.strptime(
                                           origin_routing_info['segment_info']['from_segments'][0]['dep_time'],
                                                                           '%Y-%m-%d %H:%M:%S'),
                                       to_airport=origin_routing_info['segment_info']['from_segments'][-1]['arr_airport'],
                                       arr_time=datetime.datetime.strptime(
                                           origin_routing_info['segment_info']['from_segments'][-1]['arr_time'],
                                                                           '%Y-%m-%d %H:%M:%S'),
                                       flight_number='-'.join([s['flight_number'] for s in origin_routing_info['segment_info']['from_segments']]),
                                       cabin='-'.join([s['cabin'] for s in origin_routing_info['segment_info']['from_segments']]),
                                       cabin_grade='-'.join([s['cabin_grade'] for s in origin_routing_info['segment_info']['from_segments']]),
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
                                       routing_range=search_info.routing_range,
                                       is_multi_segments=1 if len(origin_routing_info['segment_info']['from_segments']) > 1 else 0
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
        origin_routing_data = {}
        no_origin_routing = True
        while True:
            verify_result_json = TBG.redis_conn.redis_pool.rpop(verify_result_key)
            Logger().debug("======== verify result cache json: {}===".format(verify_result_json))
            if not verify_result_json:
                break
            verify_data = json.loads(verify_result_json)
            if verify_data['create_time'] and datetime.datetime.now() - datetime.timedelta(seconds=4 * 60) \
                < datetime.datetime.strptime(verify_data['create_time'], '%Y-%m-%d %H:%M:%S'):
                origin_routing_data = verify_data['data']
                no_origin_routing = False
                break
            else:
                continue
        if no_origin_routing:
            self._verify(http_session, order_info)
            print "============ verify result key: {}".format(verify_result_key)
            verify_result_json = TBG.redis_conn.redis_pool.rpop(verify_result_key)
            Logger().debug("======== verify result cache json: {}===".format(verify_result_json))
            if not verify_result_json:
                raise ProviderVerifyException('NO_VERIFY_ROUTING')
            else:
                origin_routing_data = json.loads(verify_result_json)['data']

        if not origin_routing_data:
            raise ProviderVerifyException('NO_VERIFY_ROUTING')
        return origin_routing_data

    def _booking(self, http_session, order_info):

        order_info.provider_order_status = 'BOOK_FAIL'

        origin_routing_info = self._order_get_session(http_session, order_info)

        contact = order_info.contacts[0]
        age_type_mapping = {
            'ADT': 0,
            'CHD': 1,
            'INF': 7,
        }

        post_price_list = []
        for p in origin_routing_info['flightPriceList'][0]['fareBreakdownList']:
            if p['adultQuantity'] and order_info.adt_count:
                post_price_list.append({
                    "type": 1,
                    "price": p['baseFare'],
                    "tax": p['taxes']
                })
            elif p['childQuantity'] and order_info.chd_count:
                post_price_list.append({
                    "type": 2,
                    "price": p['baseFare'],
                    "tax": p['taxes']
                })
            elif p['babyQuantity'] and order_info.inf_count:
                post_price_list.append({
                    "type": 3,
                    "price": p['baseFare'],
                    "tax": p['taxes']
                })
        data = {
            "order": {
                "memberId": self.cust_id,
                "level": 1,
                "isNewOrder": 1,
                "orderFlightType": 1,
                "distribute": 1,
            },
            "product": {"productClassId": 31},
            "contactList": [{
                'fabContactName': contact.name,
                'tel': TBG.global_config['OPERATION_CONTACT_MOBILE'],
                'email': contact.email,
            }],
            "touristList": [{
                "name": "{}/{}".format(p.last_name, p.first_name),
                "firstname": p.first_name,
                "lastname": p.last_name,
                "psptType": "2",
                "psptId": p.selected_card_no,
                "birthday": p.birthdate,
                "tel": TBG.global_config['OPERATION_CONTACT_MOBILE'],
                "touristType": age_type_mapping[p.current_age_type(order_info.from_date)],
                "psptEndDate": p.card_expired,
                "sex": 1 if p.gender == 'M' else 0,
                "issueOrgan": p.card_issue_place,
                "destAddress": None,
                "destPostcode": None,
                "country": p.nationality
            } for p in order_info.passengers],
            "requirement": {
                "adultCount": order_info.adt_count,
                "childCount": order_info.chd_count,
                "babyCount": order_info.inf_count,
                "startDate": order_info.from_date
            },
            "distributeInfo": {
                "systemId": 93,
                "channelId": origin_routing_info['flightPriceList'][0]['vendorId'],
                "queryId": origin_routing_info['queryId'],
                "flightNos": origin_routing_info['flightOptions'][0]['flightNos'],
                "priceList": [{
                    "flightNos": origin_routing_info['flightOptions'][0]['flightNos'],
                    "prices": post_price_list
                }]
            }
        }

        sign = hashlib.md5('{}{}{}'.format(self.secret_key, json.dumps(data, separators=(',', ':')),
                                           self.secret_key)).hexdigest()
        post_data = {
            "purchaseId": self.purchase_id,
            "sign": sign,
            "data": data
        }
        post_data = json.dumps(post_data, separators=(',', ':'))
        Logger().info("========= order post data: {} ===".format(post_data))
        url = '{}book'.format(self.base_url)
        headers = {'Content-Type': 'application/json;charset=utf-8'}
        result = http_session.request(url=url, data=post_data, method='POST', headers=headers, is_direct=True)
        result = json.loads(base64.b64decode(result.content))
        Logger().info("====== order result:{} ==".format(json.dumps(result)))

        if not result.get('errorCode') == 5000:
            Logger().error("==== booking create order error: {}".format(result))
            raise BookingException('create order error')

        provider_order_id = result.get('data')
        data = {
            "orderId": provider_order_id,
            "orderType": 61
        }
        sign = hashlib.md5('{}{}{}'.format(self.secret_key, json.dumps(data, separators=(',', ':')),
                                           self.secret_key)).hexdigest()
        post_data = {
            "purchaseId": self.purchase_id,
            "sign": sign,
            "data": data
        }
        post_data = json.dumps(post_data, separators=(',', ':'))
        Logger().info("========= order post data: {} ===".format(post_data))
        url = '{}getOrderStatus'.format(self.base_url)
        headers = {'Content-Type': 'application/json;charset=utf-8'}

        booking_success = False
        for times in xrange(10):
            result = http_session.request(url=url, data=post_data, method='POST', headers=headers, is_direct=True)
            result = json.loads(base64.b64decode(result.content))
            Logger().info("====== order result:{} ==".format(json.dumps(result)))
            if not result.get('errorCode') == 0:
                Logger().error("======= get order status not success ===")
            elif result.get('errorCode') == 0 and result['data']['orderStatusCode'] == 'OS003':
                booking_success = True
                break
            elif result.get('errorCode') == 0 and result['data']['orderStatusCode'] == 'OS001':
                Logger().info("===== get order status is processing ===========")
            elif result.get('errorCode') == 0 and result['data']['orderStatusCode'] == 'OS011':
                raise BookingException('order canceled!')
            else:
                Logger().error("====== get order status: other status =====")
            time.sleep(2)

        if booking_success:
            url = '{}queryOrderDetail'.format(self.base_url)
            get_order_detail = False
            result = None
            for times in xrange(3):
                result = http_session.request(url=url, data=post_data, method='POST', headers=headers, is_direct=True)
                result = json.loads(base64.b64decode(result.content))
                if result.get('errorCode') == 900:
                    get_order_detail = True
                    break
                else:
                    Logger().error("============= get order details error: {}".format(result))
                time.sleep(1)
            # 没有正确获得订单详情，订票失败
            if not get_order_detail:
                raise BookingException('get order details failed!')

            # 如果订单详情不是【待付款】状态，订票失败
            if not result['data']['orderStatus'] == 1002:
                Logger().error('get order details order status incorrect: {}'.format(result))
                raise BookingException('get order details order status incorrect')

            # 如果验价的金额与订单详情金额不一致，订票失败
            verify_total_price = 0
            for p in post_price_list:
                if p['type'] == 1:
                    verify_total_price += order_info.adt_count * (p['price'] + p['tax'])
                elif p['type'] == 2:
                    verify_total_price += order_info.chd_count * (p['price'] + p['tax'])
                elif p['type'] == 3:
                    verify_total_price += order_info.inf_count * (p['price'] + p['tax'])
            if not verify_total_price == result['data']['price']:
                Logger().error("order detail total price error. verify_price: {}  order_price: {}".format(
                    verify_total_price, result['data']['price']))

            order_info.provider_order_status = 'BOOK_SUCCESS_AND_WAITING_PAY'
            order_info.provider_order_id = provider_order_id
            order_info.provider_price = result['data']['price']
            order_info.pnr_code = 'AAAAAA'
            Logger().info('booking success')
            return order_info
        else:
            raise BookingException('last step booking failed')


    def _check_order_status(self, http_session, ffp_account_info, order_info):
        """
        检查订单状态
        :param http_session:
        :param order_id:
        :return: 返回订单状态
        """

        pass

    def _pay(self, order_info, http_session, pay_dict):
        """
        支付
        :param http_session:
        :return:
        """

        data = {
            'orderId': int(order_info.provider_order_id)
        }
        sign = hashlib.md5('{}{}{}'.format(self.secret_key, json.dumps(data, separators=(',', ':')),
                                           self.secret_key)).hexdigest()
        post_data = {
            "purchaseId": self.purchase_id,
            "sign": sign,
            "data": data
        }
        post_data = json.dumps(post_data, separators=(',', ':'))
        Logger().info("========= pay post data: {} ===".format(post_data))
        url = '{}payOrder'.format(self.base_url)
        headers = {'Content-Type': 'application/json;charset=utf-8'}
        result = http_session.request(url=url, data=post_data, method='POST', headers=headers, is_direct=True)
        result = json.loads(base64.b64decode(result.content))
        Logger().info("====== pay result:{} ==".format(json.dumps(result)))

        if not result.get('success') == True or not result.get('errorCode') == 0:
            Logger().error("==== pay error: {}".format(result))
            raise PayException('pay failed!')

        Logger().info('pay success')
        order_info.out_trade_no = result['data']['collectionId']
        return pay_dict['alipay_yiyou180']

    def _before_notice_issue_interface(self, req_body):
        """

        :param req_body:
        :return:
        """
        try:

            self.final_result = json.dumps({"success": False})

            Logger().info("======= tuniu notice issue req body: {}".format(req_body))
            data = json.loads(req_body)

            provider_order_id = data['orderId']
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
            if notice_data['orderStatus'] == 'OS003':
                pnr_list = notice_data['pnrList']
                for pnr in pnr_list:
                    TBG.tourbillon_db.execute(
                        'update person_2_flight_order set pnr="{}" where sub_order = {} and used_card_no="{}"'.format(
                            pnr['pnr'], sub_order.id, pnr['psptId']))
                    commit()
                    flush()
                self.final_result = json.dumps({"success": True})
                return
            ticket_info_list = notice_data['ticketCodeList']
            for info in ticket_info_list:
                # 填入票号
                Logger().sinfo("============ tuniu provider start to update ticket and status =======")
                Logger().sinfo(json.dumps(info))

                TBG.tourbillon_db.execute(
                    'update person_2_flight_order set ticket_no="{}" where id in (select person2flightorder from person2flightorder_suborder where suborder = {}) and person in (select id from person where name="{}")'.format(
                    info['ticketCode'].replace(' ', ''), sub_order.id, '{}/{}'.format(info['name'].split('/')[-1], info['name'].split('/')[0])))
                # 变更子订单状态
                TBG.tourbillon_db.execute(
                    'update sub_order set provider_order_status="%s" where id = %s' % ('ISSUE_SUCCESS', sub_order.id))
                commit()
                flush()

            self.final_result = json.dumps({"success": True})
        except:
            import traceback
            print traceback.format_exc()
            Logger().serror(traceback.format_exc())
            self.final_result = json.dumps({"success": False})

    def _before_notice_flight_change_interface(self, req_body):
        try:
            self.final_result = json.dumps({
                "success": False,
                "data": False,
                "errorMsg": "",
            })
            Logger().info("======= tuniu notice flight change req body: {}".format(req_body))
            data = json.loads(req_body)
            return data
        except:
            import traceback
            print traceback.format_exc()
            Logger().serror(traceback.format_exc())
            return None, None

    def _after_notice_flight_change_interface(self, notice_data):

        try:
            flight_change_status_mapping = {
                0: '延误',
                1: '提前',
                3: '变更',
                4: '取消',
            }
            for notice_info in notice_data:
                ota_order_id = notice_info['orderId']
                flight_change_status = flight_change_status_mapping[notice_info['changeType']]
                origin_flight = notice_info['flight']
                change_flight = notice_info['flightNew']

                content = u"途牛采购航班发生航变\n途牛订单号【{}】\n航变类型【{}】\n原始航班信息：{}\n变更航班信息：{}".format(
                    ota_order_id,
                    flight_change_status,
                    origin_flight,
                    change_flight,
                )
                subject = '采购接口航班发生航变'
                Pokeman.send_wechat(content=content,subject=subject,agentid=1000011,level='warning')

            self.final_result = json.dumps({
                "success": True,
                "errorMsg": "",
                "data": True,
            })
        except:
            import traceback
            print traceback.format_exc()
            Logger().serror(traceback.format_exc())
            self.final_result = json.dumps({
                "success": False,
                "errorMsg": "",
                "data": False,
            })
