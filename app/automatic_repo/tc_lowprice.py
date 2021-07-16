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


class TCLowPrice(ProvderAutoBase):
    timeout = 50  # 请求超时时间
    provider = 'tc_lowprice'  # 子类继承必须赋
    provider_channel = 'tc_lowprice_web'  # 子类继承必须赋
    operation_product_type = '会员折扣'  # 运价类型：0: GDS公布运价 1:GDS私有运价 2:航司官网产品  3:廉价航司产品 4:特价产品
    operation_product_mode = 'A2B'
    pay_channel = 'ALIPAY'
    provider_token = '5e7ba8bddd7b9648'
    is_display = True
    verify_realtime_search_count = 1
    no_flight_ttl = 1800  # 无航班缓存超时时间设定
    trip_type_list = ['OW', 'RT']




    CACHE_PR_CONFIG = {
        1: {'cabin_expired_time': 60 * 10, 'cabin_attenuation': 3,'fare_expired_time':86400 * 30},
        2: {'cabin_expired_time': 60 * 10, 'cabin_attenuation': 2,'fare_expired_time':86400 * 20},
        3: {'cabin_expired_time': 60 * 5, 'cabin_attenuation': 1,'fare_expired_time':86400 * 10},
        4: {'cabin_expired_time': 60 * 5, 'cabin_attenuation': 1,'fare_expired_time':86400 * 5},
        5: {'cabin_expired_time': 60 * 5, 'cabin_attenuation': 0,'fare_expired_time':86400},

    }
    search_interval_time = 0

    def __init__(self):
        super(TCLowPrice, self).__init__()

        self.verify_tries = 3
        self.username = 'shyy123'
        self.password = 'yida1680'
        self.account_list = [
            {'username': 'shyy123', 'password': 'yida1680'},
            # {'username': 'shyy123', 'password': 'yida1680'},
            # {'username': 'shyy123', 'password': 'yida1680'},
            # {'username': 'shyy123', 'password': 'yida1680'},
            # {'username': 'nbuser1', 'password': 'bigsec@2018'},
            # {'username': 'nbuser2', 'password': 'bigsec@2018'},
            # {'username': 'nbuser3', 'password': 'bigsec@2018'},
            {'username': 'SHAYY', 'password': '123456'},
        ]

        if not TBG.redis_conn.redis_pool.llen('tc_lowprice_account_list') == len(self.account_list):
            TBG.redis_conn.redis_pool.expire('tc_lowprice_account_list', 0)
            for account in self.account_list:
                TBG.redis_conn.redis_pool.lpush('tc_lowprice_account_list', account)

    def _get_fix_account(self):

        account = TBG.redis_conn.redis_pool.rpoplpush('tc_lowprice_account_list', 'tc_lowprice_account_list')
        account = eval(account) if account else random.choice(self.account_list)
        return account

    def _login(self, http_session, ffp_account_info):
        """
        登陆模块
        :return: 登陆成功的httpResult 对象
        """

        post_data = {
            "loginName": ffp_account_info.username,
            "password": ffp_account_info.password
        }

        url = 'http://ebk.17u.cn/iflightcrmapi/login'
        result = http_session.request(url=url, method='POST', json=post_data, is_direct=True).to_json()
        http_session.update_headers({
            'x-ly-authentication': 'LY-{}'.format(result['data']['userToken'])
        })
        http_session.update_cookie({
            'tc_supplier_token': result['data']['userToken']
        })
        return http_session

    def _check_login(self, http_session, **kwargs):
        post_data = {
            "departureCity": "SHA",
            "arrivalCity": "BKK",
            "travelType": "OW",
            "bookingClass": "Y",
            "product": "",
            "departureDate": (datetime.datetime.now() + datetime.timedelta(days=10)).strftime('%Y-%m-%d'),
            "returnDate": "",
            "adultPassengerCount": 1,
            "childPassengerCount": 0,
            "airline": "MU"
        }

        url = 'http://ebk.17u.cn/iflightcrmapi/lowprice/search'
        result = http_session.request(url=url, method='POST', json=post_data, is_direct=True).to_json()

        if result['code'] in ['LY0512001005', 'LY0512001001']:
            return False
        else:
            return True

    def _flight_search(self, search_info=None, http_session=None):

        ffp = FFPAccountInfo()
        account = self._get_fix_account()
        ffp.username = account['username']
        ffp.password = account['password']
        http_session = self.login(http_session, ffp)
        time.sleep(2)

        self.product_list = []
        # cabin_grade_list = ['Y', 'S', 'C', 'F']
        cabin_grade_list = ['Y']
        task_list = []
        for c in cabin_grade_list:
            task_list.append(gevent.spawn(self._sub_flight_search, http_session, search_info, c))
        gevent.joinall(task_list)

        if not self.product_list:
            Logger().warn('tc_lowprice no flight')
            return search_info
        search_info.assoc_search_routings.extend(self.product_list)
        Logger().debug("============== tc lowprice search routings: {} ========".format(search_info.assoc_search_routings))
        return search_info

    def _sub_flight_search(self, http_session, search_info, cabin_grade):

        post_data = {
            "departureCity": search_info.from_airport,
            "arrivalCity": search_info.to_airport,
            "travelType": search_info.trip_type,
            "bookingClass": cabin_grade,
            "product": "",
            "departureDate": search_info.from_date,
            "returnDate": search_info.ret_date if search_info.ret_date else '',
            "adultPassengerCount": search_info.adt_count,
            "childPassengerCount": search_info.chd_count,
            "airline": ""
        }

        url = 'http://ebk.17u.cn/iflightcrmapi/lowprice/search'
        result = http_session.request(url=url, method='POST', json=post_data, is_direct=True).to_json()
        Logger().debug("========== tc lowprice search result: {} ==========".format(result))

        if result['code'] == 'LY0501331008':
            raise FlightSearchException(err_code='HIGH_REQ_LIMIT')

        if result['code'] == 'LY0502101209' or not result['data']:
            # Logger().warn('tc_lowprice no flight')
            # return search_info
            return

        flight_routings = result['data']
        for route in flight_routings:
            flight_routing = FlightRoutingInfo()

            rk_flight_number = '-'.join([r.split('(')[0] for r in route['departureSegment']['flightNumbers'].split('+')])
            rk_cabin = '-'.join(route['departureSegment']['cabinCode'].split('+'))
            rk_cabin_grade = '-'.join([cabin_grade for s in route['departureSegment']['cabinCode'].split('+')])

            if search_info.trip_type == 'RT':
                rk_flight_number = '{},{}'.format(rk_flight_number,
                                                  '-'.join([r.split('(')[0] for r in
                                                            route['returnSegment']['flightNumbers'].split('+')]))
                rk_cabin = '{},{}'.format(rk_cabin, '-'.join(route['returnSegment']['cabinCode'].split('+')))
                rk_cabin_grade = '{},{}'.format(rk_cabin_grade,
                                                '-'.join([cabin_grade for s in route['returnSegment']['cabinCode'].split('+')]))

            rk_info = RoutingKey.serialize(
                from_airport=route['departureSegment']['segments'].split('-')[0],
                dep_time='N/A',
                to_airport=route['departureSegment']['segments'].split('-')[-1],
                arr_time='N/A',
                flight_number=rk_flight_number,
                cabin=rk_cabin,
                cabin_grade=rk_cabin_grade,
                product='COMMON',
                adult_price=float(route['price']['salePrice']), adult_tax=float(route['price']['tax']),
                provider_channel=self.provider_channel,
                child_price=float(route['price']['salePrice']), child_tax=float(route['price']['tax']),
                inf_price=float(route['price']['salePrice']),
                inf_tax=float(route['price']['tax']),
                provider=self.provider,
                search_from_airport=search_info.from_airport,
                search_to_airport=search_info.to_airport,
                from_date=search_info.from_date,
                routing_range=search_info.routing_range,
                trip_type=search_info.trip_type,
                is_include_operation_carrier=0,
                is_multi_segments=1 if len(route['departureSegment']['segments'].split('-')) > 1 else 0
            )

            flight_routing.routing_key_detail = rk_info['plain']
            flight_routing.routing_key = rk_info['encrypted']

            flight_routing.product_type = 'DEFAULT'
            routing_number = 1
            for index, segment in enumerate([r.split('(')[0] for r in route['departureSegment']['flightNumbers'].split('+')]):
                flight_segment = FlightSegmentInfo()
                flight_segment.carrier = route['departureSegment']['airline'].split('+')[index]
                flight_segment.dep_airport = route['departureSegment']['segments'].split('-')[index]
                flight_segment.dep_time = 'N/A'
                flight_segment.arr_airport = route['departureSegment']['segments'].split('-')[index + 1]
                flight_segment.arr_time = 'N/A'

                # 经停
                # stop_city_code_list = []
                # stop_airport_code_list = []
                # for sl in segment['stops']:
                #     stop_airport_code_list.append(sl)
                # flight_segment.stop_cities = "/".join(stop_city_code_list)
                # flight_segment.stop_airports = "/".join(stop_airport_code_list)

                flight_segment.flight_number = segment
                flight_segment.dep_terminal = 'N/A'
                flight_segment.arr_terminal = 'N/A'
                flight_segment.cabin = route['departureSegment']['cabinCode'].split('+')[index]
                flight_segment.cabin_grade = cabin_grade
                flight_segment.cabin_count = 9
                flight_segment.duration = 'N/A'
                flight_segment.routing_number = routing_number
                routing_number += 1
                flight_routing.from_segments.append(flight_segment)

            if search_info.trip_type == 'RT':

                for index, segment in enumerate([r.split('(')[0] for r in route['returnSegment']['flightNumbers'].split('+')]):
                    flight_segment = FlightSegmentInfo()
                    flight_segment.carrier = route['returnSegment']['airline'].split('+')[index]
                    flight_segment.dep_airport = route['returnSegment']['segments'].split('-')[index]
                    flight_segment.dep_time = 'N/A'
                    flight_segment.arr_airport = route['returnSegment']['segments'].split('-')[index + 1]
                    flight_segment.arr_time = 'N/A'

                    # 经停
                    # stop_city_code_list = []
                    # stop_airport_code_list = []
                    # for sl in segment['stops']:
                    #     stop_airport_code_list.append(sl)
                    # flight_segment.stop_cities = "/".join(stop_city_code_list)
                    # flight_segment.stop_airports = "/".join(stop_airport_code_list)

                    flight_segment.flight_number = segment
                    flight_segment.dep_terminal = 'N/A'
                    flight_segment.arr_terminal = 'N/A'
                    flight_segment.cabin = route['returnSegment']['cabinCode'].split('+')[index]
                    flight_segment.cabin_grade = cabin_grade
                    flight_segment.cabin_count = 9
                    flight_segment.duration = 'N/A'
                    flight_segment.routing_number = routing_number
                    routing_number += 1
                    flight_routing.ret_segments.append(flight_segment)

            flight_routing.reference_adult_price = float(route['subPrice']['salePrice']) if route['subPrice']['salePrice'] else float(route['price']['salePrice'])
            flight_routing.reference_adult_tax = float(route['subPrice']['tax']) if route['subPrice']['tax'] else float(route['price']['tax'])
            flight_routing.adult_price = float(route['price']['salePrice'])
            flight_routing.adult_tax = float(route['price']['tax'])
            flight_routing.child_price = float(route['price']['salePrice'])
            flight_routing.child_tax = float(route['price']['tax'])

            self.product_list.append(flight_routing)
