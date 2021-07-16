#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, too-many-arguments, broad-except, anomalous-backslash-in-string
# pylint: disable=missing-docstring, line-too-long, too-few-public-methods
"""
# @Author  : wxt
# @Software: PyCharm
"""

import time
import json
import random
import re
import gevent
import datetime
from bs4 import BeautifulSoup
from ..controller.http_request import HttpRequest
from bs4 import BeautifulSoup
from urllib import quote
from .base import ProvderAutoBase
from ..utils.logger import Logger
from ..utils.util import cn_name_to_pinyin, RoutingKey
from ..controller.captcha import CaptchaCracker
from ..utils.exception import *
from ..utils.util import Time, Random, md5_hash, convert_utf8, simple_encrypt, simple_decrypt
from ..dao.iata_code import IATA_CODE
from ..dao.models import *
from ..dao.internal import *
from ..utils.triple_des_m import desenc
from ..controller.smser import Smser
from app import TBG
from ..utils.blowfish import Blowfish


@TBG.fcache.cached(10,key_prefix='get_pdc_policy')
def get_pdc_policy():
    """
    预读取pdc政策
    :return:
    """
    cache = {}
    pdc_policy = TBG.config_redis.get_value('pdc_policy')
    if pdc_policy:
        return json.loads(pdc_policy)
    else:
        return {}


class Pdc(ProvderAutoBase):
    """
    私有数据库
    此库后续将用于扩展私有运价体系。
    """
    timeout = 15  # 请求超时时间
    provider = 'pdc'  # 子类继承必须赋
    provider_channel = 'pdc_manual_policy'  # 子类继承必须赋
    operation_product_type = '会员折扣'  # 运价类型：0: GDS公布运价 1:GDS私有运价 2:航司官网产品  3:廉价航司产品 4:特价产品
    operation_product_mode = 'A2A'
    pay_channel = '99BILL'
    verify_realtime_search_count = 1
    trip_type_list = ['OW', 'RT']
    no_flight_ttl = 3600 * 3  # 无航班缓存超时时间设定

    CACHE_PR_CONFIG = {
        1: {'cabin_expired_time': 3600 * 12, 'cabin_attenuation': 3, 'fare_expired_time': 86400 * 30},
        2: {'cabin_expired_time': 3600 * 3, 'cabin_attenuation': 2, 'fare_expired_time': 86400 * 20},
        3: {'cabin_expired_time': 60 * 60 * 1, 'cabin_attenuation': 1, 'fare_expired_time': 86400 * 10},
        4: {'cabin_expired_time': 60 * 40, 'cabin_attenuation': 1, 'fare_expired_time': 86400 * 5},
        5: {'cabin_expired_time': 60 * 30, 'cabin_attenuation': 0, 'fare_expired_time': 86400},

    }
    search_interval_time = 0

    # 暂时先使用配置替代
    PDC_CONFIG = [

        {'policy_name': 'xxxxxxxxxxxxxxxxxxxxxxxx', 'from_airport': 'SHA', 'to_airport': 'BKK', 'routing_range': 'I2O', 'action': [],
         'assoc_search_routings': [
             {'fare': {'2019-05-11': {'adult_price': 135000.0,'adult_price_calc':'x', 'adult_tax': 5754.0, 'child_price': 135000.0,'child_price_calc':'x', 'child_tax': 5754.0, 'cabin_count': 8},
                       '2019-05-12': {'adult_price': 5555.0, 'adult_price_calc':'x','adult_tax': 3333.0, 'child_price': 2222.0,'child_price_calc':'x', 'child_tax': 1111.0, 'cabin_count': 2},
                       '2019-05-12|2019-05-15': {'adult_price': 99.0, 'adult_price_calc': 'x', 'adult_tax': 99.0, 'child_price': 99.0, 'child_price_calc': 'x', 'child_tax': 99.0, 'cabin_count': 1},

                       },
              'from_segments': [
                  {
                      'cabin_grade': 'Y', 'cabin': 'N', 'stop_airports': 'FOC', 'stop_cities': '','dep_terminal':'T1','arr_terminal':'T1',
                      'dep_time': '10:00:00', 'arr_time': '18:00:00', 'flight_number': 'PG866',
                       'dep_airport': 'HRB', 'arr_airport': 'BKK', 'duration': 445, 'carrier': 'PG'
                  },
                  {
                      'cabin_grade': 'Y', 'cabin': 'G', 'stop_airports': '', 'stop_cities': '','dep_terminal':'T1','arr_terminal':'T1',
                      'dep_time': '+1|00:30:00', 'arr_time': '+1|11:00:00', 'flight_number': 'TG973',
                       'dep_airport': 'BKK', 'arr_airport': 'BRU', 'duration': 660, 'carrier': 'TG'
                  },
                  {
                      'cabin_grade': 'Y', 'cabin': 'I', 'stop_airports': '', 'stop_cities': '','dep_terminal':'T1','arr_terminal':'T1',
                      'dep_time': '+1|14:00:00', 'arr_time': '+1|20:00:00', 'flight_number': 'SN440',
                      'dep_airport': 'BRU', 'arr_airport': 'FMA', 'duration': 360, 'carrier': 'SN'
                  }
              ],
              'ret_segments': [
                  {
                      'cabin_grade': 'Y', 'cabin': 'I', 'stop_airports': 'FOC', 'stop_cities': '','dep_terminal':'T1','arr_terminal':'T1',
                      'dep_time': '10:00:00', 'arr_time': '18:00:00', 'flight_number': 'SN540',
                       'dep_airport': 'FMA', 'arr_airport': 'BRU', 'duration': 360, 'carrier': 'SN'
                  },
                  {
                      'cabin_grade': 'Y', 'cabin': 'G', 'stop_airports': '', 'stop_cities': '','dep_terminal':'T1','arr_terminal':'T1',
                      'dep_time': '+1|00:30:00', 'arr_time': '+1|11:00:00', 'flight_number': 'TG673',
                       'dep_airport': 'BRU', 'arr_airport': 'BKK', 'duration': 660, 'carrier': 'TG'
                  },
                  {
                      'cabin_grade': 'Y', 'cabin': 'N', 'stop_airports': '', 'stop_cities': '','dep_terminal':'T1','arr_terminal':'T1',
                      'dep_time': '+1|14:00:00', 'arr_time': '+1|20:00:00', 'flight_number': 'PG666',
                       'dep_airport': 'BKK', 'arr_airport': 'HRB', 'duration': 445, 'carrier': 'PG'
                  }
              ]}
         ]
         }

    ]

    def __init__(self):
        super(Pdc, self).__init__()

    def _flight_search(self, http_session, search_info):
        """
        航班爬取模块，
        TODO :目前只考虑单程

        :return:
        """

        # Logger().info('flight_searching....wait')
        pdc_policy_repo = get_pdc_policy()
        selected_pdc_data = [routing for routing in pdc_policy_repo if
                             routing['from_airport'] == search_info.from_airport and routing['to_airport'] == search_info.to_airport ]
        if selected_pdc_data:
            pdc_data = selected_pdc_data[0]
            for pdc_routing in pdc_data['assoc_search_routings']:
                flight_routing = FlightRoutingInfo()
                if  search_info.trip_type == 'OW':
                    sdate = search_info.from_date
                else:
                    sdate = '%s|%s' % (search_info.from_date,search_info.ret_date)
                if sdate in pdc_routing['fare']:
                    fare = pdc_routing['fare'][sdate]
                    fix_adult_price = fare['adult_price']
                    fix_child_price = fare['child_price']
                    flight_routing.adult_price = int(eval(fare['adult_price_calc'].replace('x', str(fare['adult_price'] ))))
                    flight_routing.adult_tax = fare['adult_tax']
                    flight_routing.child_price = int(eval(fare['child_price_calc'].replace('x', str(fare['child_price'] ))))
                    flight_routing.child_tax = fare['child_tax']
                    flight_routing.product_type = 'DEFAULT'

                    # 单程无经停非中转 routing_key 生成代码
                    from_date = datetime.datetime.strptime(search_info.from_date, '%Y-%m-%d')
                    __ = pdc_routing['from_segments'][0]['dep_time'].split('|')
                    if len(__) == 2:
                        dep_delta_day = int(__[0].split('+')[1])
                        dep_time_raw = __[1]
                    else:
                        dep_time_raw = __[0]
                        dep_delta_day = 0
                    dep_time_obj = datetime.datetime.strptime(dep_time_raw, '%H:%M:%S')
                    dep_time_obj = datetime.datetime(from_date.year, from_date.month, from_date.day, dep_time_obj.hour, dep_time_obj.minute, dep_time_obj.second)
                    dep_time_obj = dep_time_obj + datetime.timedelta(days=dep_delta_day)
                    total_dep_time_obj = dep_time_obj.strftime('%Y%m%d%H%M')

                    __ = pdc_routing['from_segments'][-1]['arr_time'].split('|')
                    if len(__) == 2:
                        arr_delta_day = int(__[0].split('+')[1])
                        arr_time_raw = __[1]
                    else:
                        arr_time_raw = __[0]
                        arr_delta_day = 0
                    arr_time_obj = datetime.datetime.strptime(arr_time_raw, '%H:%M:%S')
                    arr_time_obj = datetime.datetime(from_date.year, from_date.month, from_date.day, arr_time_obj.hour,
                                                     arr_time_obj.minute, arr_time_obj.second)
                    arr_time_obj = arr_time_obj + datetime.timedelta(days=arr_delta_day)
                    total_arr_time_obj = arr_time_obj.strftime('%Y%m%d%H%M')

                    cabin_list = '-'.join([f['cabin'] for f in pdc_routing['from_segments']])
                    cabin_grade_list = '-'.join([f['cabin_grade'] for f in pdc_routing['from_segments']])
                    flight_number_list = '-'.join([f['flight_number'] for f in pdc_routing['from_segments']])

                    if search_info.trip_type == 'RT':
                        ret_date = datetime.datetime.strptime(search_info.ret_date, '%Y-%m-%d')
                        __ = pdc_routing['ret_segments'][0]['dep_time'].split('|')
                        if len(__) == 2:
                            dep_delta_day = int(__[0].split('+')[1])
                            dep_time_raw = __[1]
                        else:
                            dep_time_raw = __[0]
                            dep_delta_day = 0
                        dep_time_obj = datetime.datetime.strptime(dep_time_raw, '%H:%M:%S')
                        dep_time_obj = datetime.datetime(ret_date.year, ret_date.month, ret_date.day, dep_time_obj.hour,
                                                         dep_time_obj.minute, dep_time_obj.second)
                        dep_time_obj = dep_time_obj + datetime.timedelta(days=dep_delta_day)
                        total_dep_time_obj = '{},{}'.format(total_dep_time_obj, dep_time_obj.strftime('%Y%m%d%H%M'))

                        __ = pdc_routing['ret_segments'][-1]['arr_time'].split('|')
                        if len(__) == 2:
                            arr_delta_day = int(__[0].split('+')[1])
                            arr_time_raw = __[1]
                        else:
                            arr_time_raw = __[0]
                            arr_delta_day = 0
                        arr_time_obj = datetime.datetime.strptime(arr_time_raw, '%H:%M:%S')
                        arr_time_obj = datetime.datetime(ret_date.year, ret_date.month, ret_date.day, arr_time_obj.hour,
                                                         arr_time_obj.minute, arr_time_obj.second)
                        arr_time_obj = arr_time_obj + datetime.timedelta(days=arr_delta_day)
                        total_arr_time_obj = '{},{}'.format(total_arr_time_obj, arr_time_obj.strftime('%Y%m%d%H%M'))

                        cabin_list = '{},{}'.format(cabin_list, '-'.join([f['cabin'] for f in pdc_routing['ret_segments']]))
                        cabin_grade_list = '{},{}'.format(cabin_grade_list, '-'.join(
                            [f['cabin_grade'] for f in pdc_routing['ret_segments']]))
                        flight_number_list = '{},{}'.format(flight_number_list, '-'.join(
                            [f['flight_number'] for f in pdc_routing['ret_segments']]))

                    rk_info = RoutingKey.serialize(from_airport=pdc_data['from_airport'],
                                                   dep_time=total_dep_time_obj,
                                                   to_airport=pdc_data['to_airport'],
                                                   arr_time=total_arr_time_obj,
                                                   flight_number=flight_number_list,
                                                   cabin=cabin_list,
                                                   cabin_grade=cabin_grade_list,
                                                   product='COMMON',
                                                   adult_price=fix_adult_price,
                                                   adult_tax=flight_routing.adult_tax,
                                                   provider_channel=self.provider_channel,
                                                   child_price=fix_child_price,
                                                   child_tax=flight_routing.child_tax,
                                                   inf_price=fix_child_price, inf_tax=flight_routing.child_tax,
                                                   provider=self.provider,
                                                   search_from_airport=search_info.from_airport,
                                                   search_to_airport=search_info.to_airport,
                                                   from_date=search_info.from_date,
                                                   ret_date=search_info.ret_date,
                                                   trip_type=search_info.trip_type,
                                                   routing_range=search_info.routing_range,
                                                   is_include_operation_carrier=0,
                                                   is_multi_segments=1 if len(pdc_routing['from_segments']) > 1 else 0,

                                                   )  # 供应商渠道写死为 奥凯

                    flight_routing.routing_key_detail = rk_info['plain']
                    flight_routing.routing_key = rk_info['encrypted']

                    routing_number = 1
                    for pdc_segment in pdc_routing['from_segments']:
                        __ = pdc_segment['dep_time'].split('|')
                        if len(__) == 2:
                            dep_delta_day = int(__[0].split('+')[1])
                            dep_time_raw = __[1]
                        else:
                            dep_time_raw = __[0]
                            dep_delta_day = 0

                        __ = pdc_segment['arr_time'].split('|')
                        if len(__) == 2:
                            arr_delta_day = int(__[0].split('+')[1])
                            arr_time_raw = __[1]
                        else:
                            arr_time_raw = __[0]
                            arr_delta_day = 0

                        dep_time_obj = datetime.datetime.strptime(dep_time_raw, '%H:%M:%S')
                        dep_time_obj = datetime.datetime(from_date.year, from_date.month, from_date.day, dep_time_obj.hour, dep_time_obj.minute, dep_time_obj.second)
                        dep_time_obj = dep_time_obj + datetime.timedelta(days=dep_delta_day)
                        dep_time = dep_time_obj.strftime('%Y-%m-%d %H:%M:%S')

                        arr_time_obj = datetime.datetime.strptime(arr_time_raw, '%H:%M:%S')
                        arr_time_obj = datetime.datetime(from_date.year, from_date.month, from_date.day, arr_time_obj.hour, arr_time_obj.minute, arr_time_obj.second)
                        arr_time_obj = arr_time_obj + datetime.timedelta(days=arr_delta_day)
                        arr_time = arr_time_obj.strftime('%Y-%m-%d %H:%M:%S')

                        flight_segment = FlightSegmentInfo()
                        flight_segment.carrier = pdc_segment['carrier']
                        flight_segment.dep_airport = pdc_segment['dep_airport']
                        flight_segment.dep_time = dep_time
                        flight_segment.arr_airport = pdc_segment['arr_airport']
                        flight_segment.arr_time = arr_time
                        flight_segment.cabin = pdc_segment['cabin']
                        flight_segment.cabin_count = fare['cabin_count']
                        flight_segment.flight_number = pdc_segment['flight_number']
                        flight_segment.dep_terminal = pdc_segment['dep_terminal']
                        flight_segment.arr_terminal = pdc_segment['arr_terminal']
                        flight_segment.cabin_grade = pdc_segment['cabin_grade']
                        flight_segment.duration = pdc_segment['duration']
                        flight_segment.routing_number = routing_number
                        flight_segment.stop_cities = pdc_segment['stop_cities']
                        flight_segment.stop_airports = pdc_segment['stop_airports']
                        routing_number += 1
                        flight_routing.from_segments.append(flight_segment)
                    if search_info.trip_type == 'RT':
                        for pdc_segment in pdc_routing['ret_segments']:
                            __ = pdc_segment['dep_time'].split('|')
                            if len(__) == 2:
                                dep_delta_day = int(__[0].split('+')[1])
                                dep_time_raw = __[1]
                            else:
                                dep_time_raw = __[0]
                                dep_delta_day = 0

                            __ = pdc_segment['dep_time'].split('|')
                            if len(__) == 2:
                                arr_delta_day = int(__[0].split('+')[1])
                                arr_time_raw = __[1]
                            else:
                                arr_time_raw = __[0]
                                arr_delta_day = 0

                            ret_date = datetime.datetime.strptime(search_info.ret_date, '%Y-%m-%d')

                            dep_time_obj = datetime.datetime.strptime(dep_time_raw, '%H:%M:%S')
                            dep_time_obj = datetime.datetime(ret_date.year, ret_date.month, ret_date.day, dep_time_obj.hour, dep_time_obj.minute, dep_time_obj.second)
                            dep_time_obj = dep_time_obj + datetime.timedelta(days=dep_delta_day)
                            dep_time = dep_time_obj.strftime('%Y-%m-%d %H:%M:%S')

                            arr_time_obj = datetime.datetime.strptime(arr_time_raw, '%H:%M:%S')
                            arr_time_obj = datetime.datetime(ret_date.year, ret_date.month, ret_date.day, arr_time_obj.hour, arr_time_obj.minute, arr_time_obj.second)
                            arr_time_obj = arr_time_obj + datetime.timedelta(days=arr_delta_day)
                            arr_time = arr_time_obj.strftime('%Y-%m-%d %H:%M:%S')

                            flight_segment = FlightSegmentInfo()
                            flight_segment.carrier = pdc_segment['carrier']
                            flight_segment.dep_airport = pdc_segment['dep_airport']
                            flight_segment.dep_time = dep_time
                            flight_segment.arr_airport = pdc_segment['arr_airport']
                            flight_segment.arr_time = arr_time
                            flight_segment.cabin = pdc_segment['cabin']
                            flight_segment.cabin_count = fare['cabin_count']
                            flight_segment.flight_number = pdc_segment['flight_number']
                            flight_segment.dep_terminal = pdc_segment['dep_terminal']
                            flight_segment.arr_terminal = pdc_segment['arr_terminal']
                            flight_segment.cabin_grade = pdc_segment['cabin_grade']
                            flight_segment.duration = pdc_segment['duration']
                            flight_segment.routing_number = routing_number
                            flight_segment.stop_cities = pdc_segment['stop_cities']
                            flight_segment.stop_airports = pdc_segment['stop_airports']
                            routing_number += 1
                            flight_routing.ret_segments.append(flight_segment)

                    search_info.assoc_search_routings.append(flight_routing)
                else:
                    Logger().sdebug('no from_date %s fare' % search_info.from_date)

        else:
            return search_info
        Logger().debug('fake provider assoc_search_routings %s' % search_info.assoc_search_routings)

        return search_info