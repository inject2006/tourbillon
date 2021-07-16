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
from ..utils.util import cn_name_to_pinyin,RoutingKey
from ..controller.captcha import CaptchaCracker
from ..utils.exception import *
from ..utils.util import Time, Random, md5_hash, convert_utf8,modify_pp,modify_ni, simple_decrypt, simple_encrypt
from ..dao.iata_code import IATA_CODE
from ..dao.models import *
from ..dao.internal import *
from ..utils.triple_des_m import desenc
from ..controller.smser import Smser
from app import TBG
from ..utils.blowfish import Blowfish
from ..controller.thirdparty_aux import DomesticTaxAux

class FakeProvider(ProvderAutoBase):
    """


    # 舱位数量测试
    SHA - HRB（哈尔滨） Y 舱 9 舱位 无特殊
    SHA - XTA（石家庄） Y 舱 3 舱位 无特殊
    SHA - CSX（长沙） Y 舱 0 舱位 无特殊
    SHA - YNT（烟台） F 舱 2 舱位 C 舱 2 舱位 Y 舱 2 舱位 无特殊

    # 特殊条件航班测试
    SHA - XFN（襄阳） Y 舱 2 舱位 其中一舱位无儿童舱
    SHA - CGO（郑州） Y 舱 2 舱位 经停 PEK（北京）/WEH（威海）
    SHA - WNZ（温州） Y 舱 2 舱位 国内 转机 SHA-SYX(三亚)-WNZ 去程经停 HGH（杭州）
    SHA - HSN（舟山） Y 舱 2 舱位 往返 回程经停 HGH（杭州）

    SHA - HGH（杭州）- TLQ （吐鲁番） Y 舱 2 舱位 联程

    # 国际航班测试
    SHA - SIN(新加坡) Y 舱 2 舱位 国内到国际
    SHA - SSV(锡亚西) Y 舱 2 舱位 国内到国际 + 转机 CAN(广州)

    # 搜索变化情况
    SHA - JDZ（景德镇） Y 舱 9 舱位  HIGH_REQ_LIMIT 高频限制
    SHA - TCG（塔城） Y 舱 9 舱位  REQPARAM_ERROR 参数请求限制
    SHA - NTG（南通） Y 舱 9 舱位  ERROR 未知错误
    SHA - YIW（义乌） Y 舱 9 舱位  超时30秒

    # 验价变化情况
    SHA - PZI（攀枝花） Y 舱 9 舱位  HIGH_REQ_LIMIT 高频限制
    SHA - HHA（黄花） Y 舱 9 舱位  NOFLIGHT 无舱位
    SHA - TNA（济南） Y 舱 9 舱位  ERROR 未知错误
    SHA - KHN（南昌） Y 舱 9 舱位  验价价格降低
    SHA - AQG（安庆） Y 舱 9 舱位  验价价格升高
    SHA - NNY（南阳） Y 舱 0 舱位  验价无舱

    # 下单变化情况
    SHA - DZU（大足） Y 舱 9 舱位  HIGH_REQ_LIMIT 高频限制
    SHA - SZV（苏州） Y 舱 9 舱位  NOFLIGHT 无舱位
    SHA - SZX（深圳） Y 舱 9 舱位  ERROR 未知错误

    """
    timeout = 15  # 请求超时时间
    provider = 'fakeprovider'  # 子类继承必须赋
    provider_channel = 'fakeprovider_web'  # 子类继承必须赋
    operation_product_type = '会员折扣'  # 运价类型：0: GDS公布运价 1:GDS私有运价 2:航司官网产品  3:廉价航司产品 4:特价产品
    operation_product_mode = 'A2A'
    pay_channel = '99BILL'
    force_autopay = False # 强制自动支付
    verify_realtime_search_count = 1
    is_include_booking_module = True  # 是否包含下单模块
    trip_type_list = ['OW','RT']
    no_flight_ttl = 1000  # 无航班缓存超时时间设定
    carrier_list = []  # 供应商所包含的航司列表，如果包含多个并且无法确定，请不要填写，此处会关联执飞航线判断逻辑
    is_display = True

    CACHE_PR_CONFIG = {
        1: {'cabin_expired_time': 3600 * 12, 'cabin_attenuation': 3,'fare_expired_time':86400 * 30},
        2: {'cabin_expired_time': 3600 * 3, 'cabin_attenuation': 2,'fare_expired_time':86400 * 20},
        3: {'cabin_expired_time': 60 * 60 * 1, 'cabin_attenuation': 1,'fare_expired_time':86400 * 10},
        4: {'cabin_expired_time': 60 * 40, 'cabin_attenuation': 1,'fare_expired_time':86400 * 5},
        5: {'cabin_expired_time': 60 * 30, 'cabin_attenuation': 0,'fare_expired_time':86400},

    }
    search_interval_time = 3

    FAKER_CONFIG = [

        # SHA - HRB（哈尔滨） Y 舱 9 舱位 无特殊
        {'from_airport': 'SHA', 'to_airport': 'HRB', 'trip_type': 'OW', 'routing_range': 'IN', 'action': [],
         'assoc_search_routings': [
             {'adult_price': 444.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'A', 'cabin_count': 9, "carrier":'MU','stop_airports': '', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00',
                     'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 }
             ],
              'ret_segments': []},
             {'adult_price': 900.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'D', 'cabin_count': 8, 'stop_airports': '', "carrier": 'MU', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00',
                     'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 }
             ],
              'ret_segments': []},

             {'adult_price': 1100.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'B', 'cabin_count': 3, 'stop_airports': '',"carrier":'9C', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00', 'flight_number': '9C222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 }
             ],
              'ret_segments': []},
             {'adult_price': 405.0, 'adult_tax': 60.0, 'child_price': 287.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'H', 'cabin_count': 3, 'stop_airports': '', "carrier": '9C', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00',
                     'flight_number': '9C222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 }
             ],
              'ret_segments': []},
             {'adult_price': 600.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'D', 'cabin_count': 2, 'stop_airports': '', "carrier":'MU','stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00', 'flight_number': 'CZ222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'TAO'
                 },
                 {
                     'cabin_grade': 'Y', 'cabin': 'C', 'cabin_count': 2, 'stop_airports': '',"carrier":'DZ', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00', 'flight_number': 'DZ222',
                     'routing_number': 1,
                     'dep_airport': 'TAO', 'arr_airport': 'HRB'
                 }
             ],
              'ret_segments': []},

             {'adult_price': 3900.0, 'adult_tax': 100.0, 'child_price': 250.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'D', 'cabin_count': 1, 'stop_airports': '', 'stop_cities': '', 'dep_time': '08:20:00', 'arr_time': '11:35:00', 'flight_number': 'MU2121',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 }
             ],
              'ret_segments': []}
         ]
         },

        # SHA - HRB（哈尔滨） Y 舱 9 舱位 往返
        {'from_airport': 'SHA', 'to_airport': 'HRB', 'trip_type': 'RT', 'routing_range': 'I2I', 'action': [],
         'assoc_search_routings': [
             {'adult_price': 2188.0, 'adult_tax': 60.0, 'child_price': 1087.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'A', 'cabin_count': 9, "carrier": 'MU', 'stop_airports': '', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00',
                     'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 }
                 ],
                  'ret_segments': [ {
                     'cabin_grade': 'Y', 'cabin': 'U', 'cabin_count': 9, "carrier": 'MU', 'stop_airports': '', 'stop_cities': '', 'dep_time': '09:00:00', 'arr_time': '11:00:00',
                     'flight_number': 'MU1932',
                     'routing_number': 2,
                     'dep_airport': 'HRB', 'arr_airport': 'SHA'
                 }]},
             {'adult_price': 1655.0, 'adult_tax': 60.0, 'child_price': 822.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'B', 'cabin_count': 3, 'stop_airports': '', "carrier": '9C', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00',
                     'flight_number': '9C222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 }
                 ],
              'ret_segments': [{
                     'cabin_grade': 'Y', 'cabin': 'X', 'cabin_count': 9, "carrier": 'MU', 'stop_airports': '', 'stop_cities': '', 'dep_time': '15:00:00', 'arr_time': '19:00:00',
                     'flight_number': 'MU777',
                     'routing_number': 2,
                     'dep_airport': 'HRB', 'arr_airport': 'SHA'
                 }]},
             {'adult_price': 3020.0, 'adult_tax': 60.0, 'child_price': 1510.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'C', 'cabin_count': 2, 'stop_airports': '', "carrier": 'MU', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00',
                     'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'PEK'
                 },
                 {
                     'cabin_grade': 'Y', 'cabin': 'C', 'cabin_count': 2, 'stop_airports': '', "carrier": 'DZ', 'stop_cities': '', 'dep_time': '15:00:00', 'arr_time': '17:00:00',
                     'flight_number': 'DZ222',
                     'routing_number': 2,
                     'dep_airport': 'PEK', 'arr_airport': 'HRB'
                 }
                 ],
              'ret_segments': [{
                     'cabin_grade': 'Y', 'cabin': 'Z', 'cabin_count': 9, "carrier": 'MU', 'stop_airports': '', 'stop_cities': '', 'dep_time': '15:00:00', 'arr_time': '19:00:00',
                     'flight_number': 'MU817',
                     'routing_number': 3,
                     'dep_airport': 'HRB', 'arr_airport': 'PEK'
                 },{
                     'cabin_grade': 'Y', 'cabin': 'P', 'cabin_count': 9, "carrier": 'MU', 'stop_airports': '', 'stop_cities': '', 'dep_time': '+1|20:00:00', 'arr_time': '+1|22:00:00',
                     'flight_number': 'MU129',
                     'routing_number': 4,
                     'dep_airport': 'PEK', 'arr_airport': 'SHA'
                 }]}
         ]
         },

        # PVG - SIN（新加坡） Y 舱 3 舱位 国际往返
        {'from_airport': 'PVG', 'to_airport': 'SIN', 'trip_type': 'RT', 'routing_range': 'I2O', 'action': [],
         'assoc_search_routings': [
             {'adult_price': 2000.0, 'adult_tax': 568.0, 'child_price': 1000.0, 'child_tax': 200.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'N', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '', 'dep_time': '09:20:00', 'arr_time': '15:00:00',
                     'flight_number': 'MU567',
                     'routing_number': 1,
                     'dep_airport': 'PVG', 'arr_airport': 'SIN'
                 }
             ],
              'ret_segments': [
                  {
                      'cabin_grade': 'Y', 'cabin': 'Y', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '', 'dep_time': '12:20:00', 'arr_time': '16:35:00',
                      'flight_number': 'MU568',
                      'routing_number': 2,
                      'dep_airport': 'SIN', 'arr_airport': 'PVG'
                  }
              ]},
             {'adult_price': 4000.0, 'adult_tax': 123.0, 'child_price': 2000.0, 'child_tax': 200.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'J', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '', 'dep_time': '11:20:00', 'arr_time': '18:00:00',
                     'flight_number': 'MU111',
                     'routing_number': 1,
                     'dep_airport': 'PVG', 'arr_airport': 'SIN'
                 }
             ],
              'ret_segments': [
                  {
                      'cabin_grade': 'Y', 'cabin': 'N', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '', 'dep_time': '09:20:00', 'arr_time': '15:35:00',
                      'flight_number': 'MU123',
                      'routing_number': 2,
                      'dep_airport': 'SIN', 'arr_airport': 'PVG'
                  }
              ]}
         ]
         },

        # PVG - SIN（新加坡） Y 舱 3 舱位 无特殊
        {'from_airport': 'PVG', 'to_airport': 'SIN', 'trip_type': 'OW', 'routing_range': 'OUT', 'action': [],
         'assoc_search_routings': [
             {'adult_price': 2000.0, 'adult_tax': 568.0, 'child_price': 1000.0, 'child_tax': 200.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'N', 'cabin_count': 3, 'stop_airports': '', 'stop_cities': '', 'dep_time': '09:20:00', 'arr_time': '15:00:00', 'flight_number': 'MU567',
                     'routing_number': 1,
                     'dep_airport': 'PVG', 'arr_airport': 'SIN'
                 }
             ],
              'ret_segments': []}
         ]
         },

        # SHA - XTA（石家庄） Y 舱 3 舱位 无特殊
        {'from_airport': 'SHA', 'to_airport': 'XTA', 'trip_type': 'OW', 'routing_range': 'IN', 'action': [],
         'assoc_search_routings': [
             {'adult_price': 1200.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 0.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'N', 'cabin_count': 3, 'stop_airports': '', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00', 'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'XTA'
                 }
             ],
              'ret_segments': []}
         ]
         },

        # SHA - CSX（长沙） Y 舱 0 舱位 无特殊
        {'from_airport': 'SHA', 'to_airport': 'CSX', 'trip_type': 'OW', 'routing_range': 'IN', 'action': [],
         'assoc_search_routings': [
         ]
         },

        # SHA - YNT（烟台） F 舱 2 舱位 C 舱 2 舱位 Y 舱 2 舱位 无特殊
        {'from_airport': 'SHA', 'to_airport': 'YNT', 'trip_type': 'OW', 'routing_range': 'IN', 'action': [],
         'assoc_search_routings': [
             {'adult_price': 1200.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 0.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'N', 'cabin_count': 2, 'stop_airports': '', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00', 'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'YNT'
                 }
             ],
              'ret_segments': []},
             {'adult_price': 1200.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 0.0, 'from_segments': [
                 {
                     'cabin_grade': 'F', 'cabin': 'Z', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00', 'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'YNT'
                 }
             ],
              'ret_segments': []},
             {'adult_price': 1200.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 0.0, 'from_segments': [
                 {
                     'cabin_grade': 'C', 'cabin': 'H', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00', 'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'YNT'
                 }
             ],
              'ret_segments': []}
         ]
         },

        # SHA - XFN（襄阳） Y 舱  其中一routing位无儿童舱
        {'from_airport': 'SHA', 'to_airport': 'XFN', 'trip_type': 'OW', 'routing_range': 'IN', 'action': [],
         'assoc_search_routings': [
             {'adult_price': 1200.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 0.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'N', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00', 'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'XFN'
                 }
             ],
              'ret_segments': []},
             {'adult_price': 1200.0, 'adult_tax': 60.0, 'child_price': 0.0, 'child_tax': 0.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'N', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '', 'dep_time': '15:00:00', 'arr_time': '16:00:00', 'flight_number': 'MU333',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'XFN'
                 }
             ],
              'ret_segments': []}
         ]
         },

        # SHA - CGO（郑州） Y 舱  经停 PEK（北京）/WEH（威海）
        {'from_airport': 'SHA', 'to_airport': 'CGO', 'trip_type': 'OW', 'routing_range': 'IN', 'action': [],
         'assoc_search_routings': [
             {'adult_price': 1200.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'N', 'cabin_count': 9, 'stop_airports': 'PEK/WEH', 'stop_cities': 'PEK/WEH', 'dep_time': '10:00:00', 'arr_time': '14:00:00', 'flight_number': 'MU222',
                     'routing_number': 1, 'dep_airport': 'SHA', 'arr_airport': 'CGO'
                 }
             ],
              'ret_segments': []},
             {'adult_price': 100.0, 'adult_tax': 60.0, 'child_price': 100.0, 'child_tax': 200.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'N', 'cabin_count': 9, 'stop_airports': 'PEK/WEH', 'stop_cities': 'PEK/WEH', 'dep_time': '10:00:00', 'arr_time': '14:00:00', 'flight_number': 'MU222',
                     'routing_number': 1, 'dep_airport': 'SHA', 'arr_airport': 'CGO'
                 }
             ],
              'ret_segments': []}
         ]
         },

        # SHA - WNZ（温州） Y 舱 2 舱位 国内 转机 SHA-SYX(三亚)-WNZ 去程经停 HGH（杭州）
        {'from_airport': 'SHA', 'to_airport': 'WNZ', 'trip_type': 'OW', 'routing_range': 'IN', 'action': [],
         'assoc_search_routings': [
             {'adult_price': 1200.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 0.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'N', 'cabin_count': 9, 'stop_airports': 'HGH', 'stop_cities': 'PEK/WEH', 'dep_time': '10:00:00', 'arr_time': '14:00:00', 'flight_number': 'MU222',
                     'routing_number': 1, 'dep_airport': 'SHA', 'arr_airport': 'SYX'
                 },
                 {
                     'cabin_grade': 'Y', 'cabin': 'X', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': 'PEK/WEH', 'dep_time': '16:00:00', 'arr_time': '18:00:00', 'flight_number': 'MU444',
                     'routing_number': 2, 'dep_airport': 'SYX', 'arr_airport': 'WNZ'
                 }
             ],
              'ret_segments': []}
         ]
         },

        #  SHA - HSN（舟山） Y 舱 2 舱位 往返 回程经停 HGH（杭州）
        {'from_airport': 'SHA', 'to_airport': 'WNZ', 'trip_type': 'RT', 'routing_range': 'IN', 'action': [],
         'assoc_search_routings': [
             {'adult_price': 1200.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 0.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'N', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': 'PEK/WEH', 'dep_time': '10:00:00', 'arr_time': '14:00:00', 'flight_number': 'MU222',
                     'routing_number': 1, 'dep_airport': 'SHA', 'arr_airport': 'HSN'
                 }
             ],
              'ret_segments': [{
                  'cabin_grade': 'Y', 'cabin': 'X', 'cabin_count': 9, 'stop_airports': 'HGH', 'stop_cities': 'PEK/WEH', 'dep_time': '16:00:00', 'arr_time': '18:00:00', 'flight_number': 'MU444',
                  'routing_number': 2, 'dep_airport': 'HSN', 'arr_airport': 'SHA'
              }]}
         ]
         },

        # SHA - SIN(新加坡) Y 舱 2 舱位 国内到国际
        {'from_airport': 'SHA', 'to_airport': 'SIN', 'trip_type': 'OW', 'routing_range': 'OUT', 'action': [],
         'assoc_search_routings': [
             {'adult_price': 1200.0, 'adult_tax': 320.0, 'child_price': 600.0, 'child_tax': 140.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'N', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00', 'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'SIN'
                 }
             ],
              'ret_segments': []}
         ]
         },

        # SHA - SSV(锡亚西) Y 舱 2 舱位 国内到国际 + 转机 CAN(广州) + 去程经停 HGH（杭州）
        {'from_airport': 'SHA', 'to_airport': 'SIN', 'trip_type': 'OW', 'routing_range': 'OUT', 'action': [],
         'assoc_search_routings': [
             {'adult_price': 1200.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 0.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'N', 'cabin_count': 9, 'stop_airports': 'HGH', 'stop_cities': 'PEK/WEH', 'dep_time': '10:00:00', 'arr_time': '14:00:00', 'flight_number': 'MU222',
                     'routing_number': 1, 'dep_airport': 'SHA', 'arr_airport': 'CAN'
                 },
                 {
                     'cabin_grade': 'Y', 'cabin': 'X', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': 'PEK/WEH', 'dep_time': '16:00:00', 'arr_time': '18:00:00', 'flight_number': 'MU444',
                     'routing_number': 2, 'dep_airport': 'CAN', 'arr_airport': 'SSV'
                 }
             ],
              'ret_segments': []}
         ]
         },

        # SHA - KHN（南昌） Y 舱 9 舱位  验价价格降低
        {'from_airport': 'SHA', 'to_airport': 'KHN', 'trip_type': 'OW', 'routing_range': 'IN', 'action': ['verify_price_reduce'],
         'assoc_search_routings': [
             {'adult_price': 1200.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 0.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'N', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00', 'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'KHN'
                 }
             ],
              'ret_segments': []}
         ]
         },

        # SHA - AQG（安庆） Y 舱 9 舱位  验价价格升高
        {'from_airport': 'SHA', 'to_airport': 'AQG', 'trip_type': 'OW', 'routing_range': 'IN', 'action': ['verify_price_rise'],
         'assoc_search_routings': [
             {'adult_price': 1200.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 0.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'N', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00', 'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'AQG'
                 }
             ],
              'ret_segments': []}
         ]
         },

        # SHA - NNY（南阳） Y 舱 0 舱位  验价无舱
        {'from_airport': 'SHA', 'to_airport': 'NNY', 'trip_type': 'OW', 'routing_range': 'IN', 'action': ['verify_no_cabin'],
         'assoc_search_routings': [
             {'adult_price': 1200.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 0.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'N', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00', 'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'NNY'
                 }
             ],
              'ret_segments': []}
         ]
         },

        # 搜索变化情况 SHA - JDZ（景德镇） Y 舱 9 舱位  HIGH_REQ_LIMIT 高频限制
        {'from_airport': 'SHA', 'to_airport': 'JDZ', 'trip_type': 'OW', 'routing_range': 'IN', 'action': [],'search_return':'HIGH_REQ_LIMIT',},

        # 搜索变化情况 SHA - TCG（塔城） Y 舱 9 舱位  REQPARAM_ERROR 参数请求限制
        {'from_airport': 'SHA', 'to_airport': 'TCG', 'trip_type': 'OW', 'routing_range': 'IN', 'action': [],'search_return':'REQPARAM_ERROR'},

        # 搜索变化情况 SHA - NTG（南通） Y 舱 9 舱位  ERROR 未知错误
        {'from_airport': 'SHA', 'to_airport': 'NTG', 'trip_type': 'OW', 'routing_range': 'IN', 'action': [], 'search_return': 'ERROR'},

        # 验价变化情况 SHA - PZI（攀枝花） Y 舱 9 舱位  HIGH_REQ_LIMIT 高频限制
        {'from_airport': 'SHA', 'to_airport': 'PZI', 'trip_type': 'OW', 'routing_range': 'IN', 'action': [],'verify_return': 'HIGH_REQ_LIMIT',
         'assoc_search_routings': [
             {'adult_price': 1200.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 0.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'N', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00', 'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'PZI'
                 }
             ],
              'ret_segments': []}
         ]
         },


        # 验价变化情况 SHA - TNA（济南） Y 舱 9 舱位  ERROR 未知错误
        {'from_airport': 'SHA', 'to_airport': 'TNA', 'trip_type': 'OW', 'routing_range': 'IN', 'action': [],'verify_return': 'ERROR',
         'assoc_search_routings': [
             {'adult_price': 1200.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 0.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'N', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00', 'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'TNA'
                 }
             ],
              'ret_segments': []}
         ]
         },

        # 下单变化情况 SHA - DZU（大足） Y 舱 9 舱位  HIGH_REQ_LIMIT 高频限制
        {'from_airport': 'SHA', 'to_airport': 'DZU', 'trip_type': 'OW', 'routing_range': 'IN', 'action': [], 'order_return': 'HIGH_REQ_LIMIT',
         'assoc_search_routings': [
             {'adult_price': 1200.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 0.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'N', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00', 'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'DZU'
                 }
             ],
              'ret_segments': []}
         ]
         },

        # 下单变化情况 SHA - SZV（苏州） Y 舱 9 舱位  NOFLIGHT 无舱位
        {'from_airport': 'SHA', 'to_airport': 'SZV', 'trip_type': 'OW', 'routing_range': 'IN', 'action': [], 'order_return': 'NOFLIGHT',
         'assoc_search_routings': [
             {'adult_price': 1200.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 0.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'N', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00', 'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'SZV'
                 }
             ],
              'ret_segments': []}
         ]
         },

        # 下单变化情况 SHA - SZX（深圳） Y 舱 9 舱位  ERROR 未知错误
        {'from_airport': 'SHA', 'to_airport': 'SZX', 'trip_type': 'OW', 'routing_range': 'IN', 'action': [], 'order_return': 'ERROR',
         'assoc_search_routings': [
             {'adult_price': 1200.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 0.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'N', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00', 'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'SZX'
                 }
             ],
              'ret_segments': []}
         ]
         },
        # SHA - YIW（义乌） Y 舱 9 舱位  超时30秒
        {'from_airport': 'SHA', 'to_airport': 'YIW', 'trip_type': 'OW', 'routing_range': 'IN', 'action': ['set_latency_30'],
         'assoc_search_routings': [
             {'adult_price': 1200.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 0.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'N', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00', 'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'YIW'
                 }
             ],
              'ret_segments': []}
         ]
         },
        # BJS - SIN Y 舱 9 舱位  超时30秒
        {'from_airport': 'BJS', 'to_airport': 'SIN', 'trip_type': 'OW', 'routing_range': 'OUT',
         'action': ['set_latency_30'],
         'assoc_search_routings': [
             {'adult_price': 1750.0, 'adult_tax': 648.0, 'child_price': 1320.0, 'child_tax': 488.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'N', 'cabin_count': 9, 'stop_airports': '', "carrier": 'MU',
                     'stop_cities': '', 'dep_time': '06:20:00', 'arr_time': '08:35:00', 'flight_number': 'MU9158',
                     'routing_number': 1,
                     'dep_airport': 'BJS', 'arr_airport': 'HGH'
                 },
                 {
                     'cabin_grade': 'Y', 'cabin': 'N', 'cabin_count': 9, 'stop_airports': '', "carrier": 'MU',
                     'stop_cities': '', 'dep_time': '08:10:00', 'arr_time': '14:45:00', 'flight_number': 'MU237',
                     'routing_number': 1,
                     'dep_airport': 'HGH', 'arr_airport': 'SIN'
                 }
             ],
              'ret_segments': []}
         ]
         },
        # BJS - MEL
        {'from_airport': 'BJS', 'to_airport': 'MEL', 'trip_type': 'OW', 'routing_range': 'OUT',
         'action': [],
         'assoc_search_routings': [
             {'adult_price': 5200.0, 'adult_tax': 3900.0, 'child_price': 1000.0, 'child_tax': 840.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'N', 'cabin_count': 9, 'stop_airports': '', "carrier": 'MU',
                     'stop_cities': '', 'dep_time': '07:35:00', 'arr_time': '09:35:00', 'flight_number': 'MU5183',
                     'routing_number': 1,
                     'dep_airport': 'BJS', 'arr_airport': 'SHA'
                 },
                 {
                     'cabin_grade': 'Y', 'cabin': 'J', 'cabin_count': 9, 'stop_airports': '', "carrier": 'MU',
                     'stop_cities': '', 'dep_time': '17:45:00', 'arr_time': '10:00:00', 'flight_number': 'MU737',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'MEL'
                 }
             ],
              'ret_segments': []}
         ]
         },
        # HKG  -  SHA
        {'from_airport': 'HKG', 'to_airport': 'SHA', 'trip_type': 'OW', 'routing_range': 'OUT',
         'action': [],
         'assoc_search_routings': [
             {'adult_price': 770.0, 'adult_tax': 229.0, 'child_price': 770.0, 'child_tax': 123.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'T', 'cabin_count': 9, 'stop_airports': '', "carrier": 'MU',
                     'stop_cities': '', 'dep_time': '07:40:00', 'arr_time': '09:50:00', 'flight_number': 'MU726',
                     'routing_number': 1,
                     'dep_airport': 'HKG', 'arr_airport': 'SHA'
                 }
             ],
              'ret_segments': []}
         ]
         },
        # BKK - BJS
        {'from_airport': 'BKK', 'to_airport': 'BJS', 'trip_type': 'OW', 'routing_range': 'OUT',
         'action': [],
         'assoc_search_routings': [
             {'adult_price': 1340.0, 'adult_tax': 639.0, 'child_price': 1010.0, 'child_tax': 590.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'S', 'cabin_count': 9, 'stop_airports': '', "carrier": 'MU',
                     'stop_cities': '', 'dep_time': '01:20:00', 'arr_time': '07:00:00', 'flight_number': 'MU2072',
                     'routing_number': 1,
                     'dep_airport': 'BKK', 'arr_airport': 'BJS'
                 }
             ],
              'ret_segments': []}
         ]
         },
        # BKK - SHA
        {'from_airport': 'BKK', 'to_airport': 'SHA', 'trip_type': 'OW', 'routing_range': 'OUT',
         'action': [],
         'assoc_search_routings': [
             {'adult_price': 960.0, 'adult_tax': 639.0, 'child_price': 728.0, 'child_tax': 600.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'S', 'cabin_count': 9, 'stop_airports': '', "carrier": 'MU',
                     'stop_cities': '', 'dep_time': '01:55:00', 'arr_time': '07:20:00', 'flight_number': 'MU548',
                     'routing_number': 1,
                     'dep_airport': 'BKK', 'arr_airport': 'SHA'
                 }
             ],
              'ret_segments': []}
         ]
         },
        # BKK - CAN
        {'from_airport': 'BKK', 'to_airport': 'CAN', 'trip_type': 'OW', 'routing_range': 'OUT',
         'action': [],
         'assoc_search_routings': [
             {'adult_price': 1120.0, 'adult_tax': 339.0, 'child_price': 840.0, 'child_tax': 300.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'R', 'cabin_count': 9, 'stop_airports': '', "carrier": 'MU',
                     'stop_cities': '', 'dep_time': '13:30:00', 'arr_time': '17:05:00', 'flight_number': 'MU2078',
                     'routing_number': 1,
                     'dep_airport': 'BKK', 'arr_airport': 'CAN'
                 }
             ],
              'ret_segments': []},
             {'adult_price': 1120.0, 'adult_tax': 339.0, 'child_price': 840.0, 'child_tax': 339.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'R', 'cabin_count': 9, 'stop_airports': '', "carrier": 'MU',
                     'stop_cities': '', 'dep_time': '22:55:00', 'arr_time': '04:15:00', 'flight_number': 'MU252',
                     'routing_number': 1,
                     'dep_airport': 'BKK', 'arr_airport': 'CAN'
                 }
             ],
              'ret_segments': []}
         ]
         },
        # PNH - BJS
        {'from_airport': 'PNH', 'to_airport': 'BJS', 'trip_type': 'OW', 'routing_range': 'OUT',
         'action': [],
         'assoc_search_routings': [
             {'adult_price': 860.0, 'adult_tax': 765.0, 'child_price': 860.0, 'child_tax': 612.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'T', 'cabin_count': 9, 'stop_airports': '', "carrier": 'MU',
                     'stop_cities': '', 'dep_time': '00:15:00', 'arr_time': '05:20:00', 'flight_number': 'MU760',
                     'routing_number': 1,
                     'dep_airport': 'PNH', 'arr_airport': 'PVG'
                 },
                 {
                     'cabin_grade': 'Y', 'cabin': 'T', 'cabin_count': 9, 'stop_airports': '', "carrier": 'MU',
                     'stop_cities': '', 'dep_time': '09:00:00', 'arr_time': '11:25:00', 'flight_number': 'MU5129',
                     'routing_number': 1,
                     'dep_airport': 'PVG', 'arr_airport': 'BJS'
                 }
             ],
              'ret_segments': []}
         ]
         },
        # PNH - Bkk
        {'from_airport': 'PNH', 'to_airport': 'BKK', 'trip_type': 'OW', 'routing_range': 'OUT',
         'action': [],
         'assoc_search_routings': [
             {'adult_price': 2010.0, 'adult_tax': 1265.0, 'child_price': 1510.0, 'child_tax': 1050.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'R', 'cabin_count': 9, 'stop_airports': '', "carrier": 'MU',
                     'stop_cities': '', 'dep_time': '00:15:00', 'arr_time': '05:20:00', 'flight_number': 'MU760',
                     'routing_number': 1,
                     'dep_airport': 'PNH', 'arr_airport': 'PVG'
                 },
                 {
                     'cabin_grade': 'Y', 'cabin': 'T', 'cabin_count': 9, 'stop_airports': '', "carrier": 'MU',
                     'stop_cities': '', 'dep_time': '08:45:00', 'arr_time': '12:20:00', 'flight_number': 'MU541',
                     'routing_number': 1,
                     'dep_airport': 'PVG', 'arr_airport': 'BKK'
                 }
             ],
              'ret_segments': []}
         ]
         },
        # PNH - CAN
        {'from_airport': 'PNH', 'to_airport': 'CAN', 'trip_type': 'OW', 'routing_range': 'OUT',
         'action': [],
         'assoc_search_routings': [
             {'adult_price': 840.0, 'adult_tax': 765.0, 'child_price': 840.0, 'child_tax': 613.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'T', 'cabin_count': 9, 'stop_airports': '', "carrier": 'MU',
                     'stop_cities': '', 'dep_time': '00:15:00', 'arr_time': '05:20:00', 'flight_number': 'MU760',
                     'routing_number': 1,
                     'dep_airport': 'PNH', 'arr_airport': 'PVG'
                 },
                 {
                     'cabin_grade': 'Y', 'cabin': 'T', 'cabin_count': 9, 'stop_airports': '', "carrier": 'FM',
                     'stop_cities': '', 'dep_time': '09:00:00', 'arr_time': '11:40:00', 'flight_number': 'FM9303',
                     'routing_number': 1,
                     'dep_airport': 'PVG', 'arr_airport': 'CAN'
                 }
             ],
              'ret_segments': []}
         ]
         },
        # SHA - CEI
        {'from_airport': 'PNH', 'to_airport': 'CEI', 'trip_type': 'OW', 'routing_range': 'OUT',
         'action': [],
         'assoc_search_routings': [
             {'adult_price': 1260.0, 'adult_tax': 660.0, 'child_price': 1020.0, 'child_tax': 580.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'B', 'cabin_count': 9, 'stop_airports': '', "carrier": 'MU',
                     'stop_cities': '', 'dep_time': '08:35:00', 'arr_time': '14:30:00', 'flight_number': 'MU5437',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'KMG'
                 },
                 {
                     'cabin_grade': 'Y', 'cabin': 'R', 'cabin_count': 9, 'stop_airports': '', "carrier": 'MU',
                     'stop_cities': '', 'dep_time': '13:25:00', 'arr_time': '14:10:00', 'flight_number': 'MU2597',
                     'routing_number': 1,
                     'dep_airport': 'KMG', 'arr_airport': 'CEI'
                 }
             ],
              'ret_segments': []}
         ]
         },

        # GTB - GTC 无舱位信息
        {'from_airport': 'GTB', 'to_airport': 'GTC', 'trip_type': 'OW', 'routing_range': 'O2O',
         'action': [],
         'assoc_search_routings': [
             {'adult_price': 1260.0, 'adult_tax': 660.0, 'child_price': 1020.0, 'child_tax': 580.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'C', 'cabin_count': 9, 'stop_airports': '', "carrier": 'DZ',
                     'stop_cities': '', 'dep_time': '08:35:00', 'arr_time': '14:30:00', 'flight_number': 'DZ5437',
                     'routing_number': 1,
                     'dep_airport': 'GTB', 'arr_airport': 'KMG'
                 },
                 {
                     'cabin_grade': 'Y', 'cabin': 'N/A', 'cabin_count': 9, 'stop_airports': '', "carrier": 'DZ',
                     'stop_cities': '', 'dep_time': '13:25:00', 'arr_time': '14:10:00', 'flight_number': 'DZ2597',
                     'routing_number': 1,
                     'dep_airport': 'KMG', 'arr_airport': 'GTC'
                 }
             ],
              'ret_segments': []}
         ]
         }


    ]

    def __init__(self):
        super(FakeProvider, self).__init__()


    def _pre_order_check(self, http_session, order_info):
        """
        :return:
        """

        return "CHECK_SUCCESS"


    def _simulate_booking(self, order_info):
        """
        传入search_info中并没有乘客信息和账号信息，需要自行添加paxinfo 和 accountinfo
        :return:
        """

        # 判断是否包含routing，包含说明是验价过来指定航班进行测试，不需要自己生成routing，
        if order_info.routing:
            pass
        else:
            # TODO 生成随机routing进行测试，此处后续将用于心跳检测，目前暂时留空
            pass

        # 添加账号
        account_list = [
            {'password':'xxxxxx','username':'tomtom'}
        ]
        account  = account_list[0]
        ffp_account_info_tmp2 = FFPAccountInfo()
        ffp_account_info_tmp2.username = account['username']
        ffp_account_info_tmp2.password = account['password']
        order_info.ffp_account = ffp_account_info_tmp2


        # 添加乘客信息
        pax_info = PaxInfo()
        pax_info.last_name = 'wang'
        pax_info.first_name = 'xiaotian'
        pax_info.age_type = 'ADT'
        pax_info.birthdate = '1990-01-01'
        pax_info.gender = 'M'
        pax_info.used_card_type = 'NI'
        pax_info.used_card_no = '230903199004090819'
        pax_info.attr_competion()

        order_info.passengers = [pax_info]

        # 调用真正下单入库函数
        order_info = self.booking(order_info=order_info)
        Logger().sdebug('order_info  %s'% order_info)
        raise Exception('tetstss')
        return order_info





    def _order_split(self,order_info,passengers):
        """
        国际航班，并且价格大于1000，进行订单分拆
        不能将儿童单独拆分出来,每单一个成年人最多带三个小孩
        :param order_info:
        :return:
        """
        Logger().sdebug('order_info %s'%order_info)
        if order_info.routing.adult_price > 1000 and order_info.routing_range == 'OUT' and len(passengers) > 1:
            rl = []
            adt_list = [x for x in passengers if x.current_age_type(from_date=order_info.from_date,is_aggr_chd_adt=True) =='ADT']
            chd_list = [x for x in passengers if x.current_age_type(from_date=order_info.from_date, is_aggr_chd_adt=True) == 'CHD']

            for adt in adt_list:
                sub_order = [adt]
                for c in range(3):
                    if chd_list:
                        sub_order.append(chd_list.pop())
                rl.append(sub_order)
            return rl
        else:
            return [[x for x in passengers]]

    def _login(self, http_session, ffp_account_info):
        """
        登陆模块
        :return: 登陆成功的httpResult 对象
        """

        gevent.sleep(2)
        return http_session

    def _check_login(self, http_session):
        """
        登录失败
        $.fullLoginCheck({"ipPosition":"SHA","loginModel":"1","message":"false","mobileNo":"","tier":"","time":"2018/07/02 18:01:47","username":"","uuid":"6ae602c3dfb8405d85b0e181b5c93e8b"})
        登陆成功
        $.fullLoginCheck({"ipPosition":"SHA","loginModel":"1","message":"true","mobileNo":"18797240897","tier":"STD","time":"2018/07/02 18:01:30","username":"林雪飞","uuid":"47884c479d7c427986c4ae07f4cbfe64"})
        :return:
        """
        gevent.sleep(1)
        return True

    def _register(self, http_session, pax_info, ffp_account_info):

        modified_card_no = None
        for x in range(0,10):
            # 尝试三次

            try:
                ffp_account_info = self._sub_register(http_session=http_session,pax_info=pax_info,ffp_account_info=ffp_account_info)
                return ffp_account_info
            except RegisterCritical as e:
                Logger().debug('e.err_code %s' %e.err_code)
                if not e.err_code == 'FFP_EXISTS':
                    raise
            # 账号经过无法注册也无法登陆,修改证件号重新注册
            if pax_info.used_card_type == 'NI':
                # 身份证修改
                modified_card_no = modify_ni(pax_info.card_ni)
                pax_info.used_card_no = modified_card_no
                pax_info.card_ni = modified_card_no
            else:
                modified_card_no = modify_pp(pax_info.card_pp)

                modified_card_no = str(random.randint(10000000, 99999999))
                pax_info.used_card_no = modified_card_no
                pax_info.card_pp = modified_card_no
            Logger().sinfo('start modified_card_no %s register' % modified_card_no)
        else:
            raise RegisterException

    def _sub_register(self, http_session, pax_info, ffp_account_info):
        """
        注册模块
        :param pax_info:
        :return: ffp account info


        u'\u5165\u4f1a\u6e20\u9053\u53f7\u4e3a\u7a7a' 曾经报错：入会渠道号为空
        """
        if pax_info.card_ni:
            ffp_account_info.reg_pid = pax_info.card_ni
            ffp_account_info.reg_card_type = 'NI'
            save_card_no = pax_info.card_ni
        else:
            ffp_account_info.reg_passport = pax_info.card_pp
            ffp_account_info.reg_card_type = 'PP'
            save_card_no = pax_info.card_pp

        Logger().info('fake registering wait..... pax_info %s'%pax_info)
        gevent.sleep(2)
        # fake_account = TBG.redis_conn.get_value('fake_account_%s' % (save_card_no))
        # if fake_account:
        #     raise RegisterCritical(err_code='FFP_EXISTS')
        # else:
        ffp_account_info.username = str(Random.gen_num(8))
        ffp_account_info.password = str(Random.gen_num(8))
        ffp_account_info.provider = self.provider

        ffp_account_info.reg_birthdate = pax_info.birthdate
        ffp_account_info.reg_gender = pax_info.gender
        # TBG.redis_conn.insert_value('fake_account_%s' % (save_card_no),'xxx',ex=86400)
        return ffp_account_info

    def _booking(self, http_session, order_info):
        """

        pax_name = '刘志'
        pax_email = 'fdaljrj@tongdun.org'
        pax_mobile = '15216666047'
        pax_pid = '230903199004090819'
        pax_id_type = 'NI'
        contact_name = pax_name
        contact_email = pax_email
        contact_mobile = pax_mobile

        :param http_session:
        :param order_info:
        :return: order_info class
        """

        Logger().info('fake ordering.....wait')
        gevent.sleep(2)
        self.flight_search(search_info=order_info)
        # if not order_info.assoc_search_routings:
        #
        if not order_info.ffp_account:
            # 如果没有账号才需要注册
            try:
                paxs = [x for x in order_info.passengers if x.current_age_type(from_date=order_info.from_date, is_aggr_chd_adt=True) == 'ADT']
                if paxs:
                    order_info.provider_order_status = 'REGISTER_FAIL'
                    ffp_account_info = self.register(http_session=http_session, pax_info=order_info.passengers[0], flight_order_id=order_info.flight_order_id,sub_order_id=order_info.sub_order_id)
                else:
                    raise RegisterCritical('NO ADT FOUND ,CAN NOT REGISTER')
            except Critical as e:
                raise
            order_info.ffp_account = ffp_account_info

        for pax in order_info.passengers:
            Logger().debug('used_card_no %s selected_card_no %s'% (pax.used_card_no,pax.selected_card_no))

        order_info.provider_price = '1333'
        # 增加手机验证码测试环节
        order_id = Random.gen_num(8)
        order_info.provider_order_id = str(order_id)
        order_info.provider_order_status = 'BOOK_SUCCESS_AND_WAITING_PAY'
        Logger().info('orderNo %s' % order_id)
        TBG.redis_conn.insert_value('%s_%s' % (self.provider_channel, order_info.provider_order_id), order_info.provider_order_status,ex=86400)

        # 测试extra_data
        order_info.extra_data = {'xxx':1}

        return order_info




    def _check_order_status(self, http_session, ffp_account_info, order_info):
        """
        检查订单状态
        :param http_session:
        :param order_id:
        :return: 返回订单状态
        航司订单状态
        {10050:{tips:"等待支付",className:"waitPayB"},
        10051:{tips:"支付成功",className:"waitPayG"},
        10052:{tips:"交易处理中",className:"waitPayG"},
        10053:{tips:"差错退款",className:"warning"},
        10054:{tips:"交易成功",className:"success"},
        10055:{tips:"交易异常",className:"error"},
        10056:{tips:"交易取消",className:"cancel"},
        10057:{tips:"等待确认",className:"waitPay"},
        10058:{tips:"预定失败",className:"cancel"},
        10059:{tips:"退票",className:"warning"}，

        """
        Logger().info('fake order status checking ')
        gevent.sleep(2)
        provider_order_status = TBG.redis_conn.get_value('%s_%s' % (self.provider_channel, order_info.provider_order_id))
        if provider_order_status == 'ISSUE_SUCCESS':

            order_info.provider_order_status = 'ISSUE_SUCCESS'
            if order_info.provider_order_status == 'ISSUE_SUCCESS':
                for pax_info in order_info.passengers:
                    pax_info.ticket_no = Random.gen_num(8)
                    order_info.pnr_code = Random.gen_littlepnr()
                    Logger().debug('faker ticket_no %s' % pax_info.ticket_no)
            Logger().debug('faker pnr_code %s' % order_info.pnr_code)
    def _get_coupon(self, http_session, ffp_account_info):
        """
        获取VISA红包
        :return:
        """
        gevent.sleep(2)
        Logger().info('fake visa-coupon has got')
        return True

    def _pre_order_check(self, http_session, order_info):

        selected_data = [routing for routing in self.FAKER_CONFIG if routing['from_airport'] == order_info.from_airport and routing['to_airport'] == order_info.to_airport]
        if selected_data:
            data = selected_data[0]
            order_return = data.get('order_return','')
            if order_return:
                return order_return
            else:
                return 'CHECK_SUCCESS'
        else:
            return 'CHECK_SUCCESS'

    def _flight_search(self, http_session, search_info):
        """
        航班爬取模块，
        TODO :目前只考虑单程

        :return:
        """

        # s = HttpRequest(lock_proxy_pool='E')
        #
        # result = s.request(method='GET',url='https://pv.sohu.com/cityjson',is_direct=False,verify=False,proxy_pool='E').content
        # print result
        # raise Exception(123)
        if not search_info.ota_work_flow:
            search_info.ota_work_flow = 'search'
        Logger().info('fake flight_searching....wait')
        Logger().debug('ota_work_flow %s' % search_info.ota_work_flow)
        gevent.sleep(1)
        Logger().sdebug('search_info.trip_type %s' % search_info.trip_type)
        # result = http_session.request(method='GET', url='http://www.baFDSAFDSAFDSAFDSAFDASFDSAFDFDSFDidu.com/', verify=False).to_json()
        selected_fake_data = [routing for routing in self.FAKER_CONFIG if routing['from_airport'] == search_info.from_airport and routing['to_airport'] == search_info.to_airport and routing['trip_type'] == search_info.trip_type]
        if selected_fake_data:

            Logger().sdebug('selected_fake_data')
            fake_data = selected_fake_data[0]
            for fake_routing in fake_data.get('assoc_search_routings',[]):
                flight_routing = FlightRoutingInfo()
                # flight_routing.routing_key = '32819d9afjdiasoji12'  # 此处需要进行hash
                # 成人价格+税
                flight_routing.adult_price_discount = 86
                flight_routing.adult_price_full_price = 1500.0

                if search_info.ota_work_flow in ['verify', 'order'] and 'verify_price_rise' in fake_data['action'] :
                    fix_adult_price = fake_routing['adult_price'] + 100
                    fix_child_price = fake_routing['child_price'] + 100
                    Logger().debug('price rise')
                elif search_info.ota_work_flow in ['verify', 'order'] and 'verify_price_reduce' in fake_data['action'] :
                    fix_adult_price = fake_routing['adult_price'] - 100
                    fix_child_price = fake_routing['child_price'] - 100
                    Logger().debug('price reduce')
                else:
                    fix_adult_price = fake_routing['adult_price']
                    fix_child_price = fake_routing['child_price']
                    # Logger().debug('price no change')
                flight_routing.adult_price = fix_adult_price
                flight_routing.adult_tax = fake_routing['adult_tax']
                flight_routing.child_price = fix_child_price
                flight_routing.child_tax = fake_routing['child_tax']
                flight_routing.reference_adult_price = fake_routing.get('reference_adult_price',0)
                flight_routing.reference_adult_tax = fake_routing.get('reference_adult_tax',0)
                flight_routing.product_type = 'DEFAULT'

                # 单程无经停非中转 routing_key 生成代码
                from_date = datetime.datetime.strptime(search_info.from_date, '%Y-%m-%d')
                ret_date = ''
                if search_info.trip_type == 'RT':
                    ret_date = datetime.datetime.strptime(search_info.ret_date, '%Y-%m-%d')

                routing_number = 1
                for fake_segment in fake_routing['from_segments']:

                    __ = fake_segment['dep_time'].split('|')
                    if len(__) == 2:
                        dep_delta_day = int(__[0].split('+')[1])
                        dep_time_raw = __[1]
                    else:
                        dep_time_raw = __[0]
                        dep_delta_day = 0

                    __ = fake_segment['arr_time'].split('|')
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
                    flight_segment.carrier = fake_segment.get('carrier','MU')
                    flight_segment.dep_airport = fake_segment['dep_airport']
                    flight_segment.dep_time = dep_time
                    flight_segment.arr_airport = fake_segment['arr_airport']
                    flight_segment.arr_time = arr_time
                    flight_segment.cabin = fake_segment['cabin']
                    flight_segment.cabin_count = fake_segment['cabin_count']
                    flight_segment.flight_number = fake_segment['flight_number']
                    flight_segment.dep_terminal = 'T1'
                    flight_segment.arr_terminal = 'T2'
                    flight_segment.cabin_grade = fake_segment['cabin_grade']
                    duration = 320
                    flight_segment.duration = duration
                    flight_segment.routing_number = routing_number
                    flight_segment.stop_cities = fake_segment['stop_cities']
                    flight_segment.stop_airports = fake_segment['stop_airports']
                    routing_number += 1
                    flight_routing.from_segments.append(flight_segment)

                for fake_segment in fake_routing['ret_segments']:
                    __ = fake_segment['dep_time'].split('|')
                    if len(__) == 2:
                        dep_delta_day = int(__[0].split('+')[1])
                        dep_time_raw = __[1]
                    else:
                        dep_time_raw = __[0]
                        dep_delta_day = 0

                    __ = fake_segment['arr_time'].split('|')
                    if len(__) == 2:
                        arr_delta_day = int(__[0].split('+')[1])
                        arr_time_raw = __[1]
                    else:
                        arr_time_raw = __[0]
                        arr_delta_day = 0

                    dep_time_obj = datetime.datetime.strptime(dep_time_raw, '%H:%M:%S')
                    dep_time_obj = datetime.datetime(ret_date.year, ret_date.month, ret_date.day, dep_time_obj.hour, dep_time_obj.minute, dep_time_obj.second)
                    dep_time_obj = dep_time_obj + datetime.timedelta(days=dep_delta_day)
                    dep_time = dep_time_obj.strftime('%Y-%m-%d %H:%M:%S')

                    arr_time_obj = datetime.datetime.strptime(arr_time_raw, '%H:%M:%S')
                    arr_time_obj = datetime.datetime(ret_date.year, ret_date.month, ret_date.day, arr_time_obj.hour, arr_time_obj.minute, arr_time_obj.second)
                    arr_time_obj = arr_time_obj + datetime.timedelta(days=arr_delta_day)
                    arr_time = arr_time_obj.strftime('%Y-%m-%d %H:%M:%S')

                    flight_segment = FlightSegmentInfo()
                    flight_segment.carrier = fake_segment.get('carrier', 'MU')
                    flight_segment.dep_airport = fake_segment['dep_airport']
                    flight_segment.dep_time = dep_time
                    flight_segment.arr_airport = fake_segment['arr_airport']
                    flight_segment.arr_time = arr_time
                    flight_segment.cabin = fake_segment['cabin']
                    flight_segment.cabin_count = fake_segment['cabin_count']
                    flight_segment.flight_number = fake_segment['flight_number']
                    flight_segment.dep_terminal = 'T1'
                    flight_segment.arr_terminal = 'T2'
                    flight_segment.cabin_grade = fake_segment['cabin_grade']
                    duration = 320
                    flight_segment.duration = duration
                    flight_segment.routing_number = routing_number
                    flight_segment.stop_cities = fake_segment['stop_cities']
                    flight_segment.stop_airports = fake_segment['stop_airports']
                    routing_number += 1
                    flight_routing.ret_segments.append(flight_segment)

                if routing_number > 1:
                    is_multi_segments = 1
                else:
                    is_multi_segments = 0


                __ = fake_routing['from_segments'][-1]['arr_time'].split('|')
                if len(__) == 2:
                    arr_delta_day = int(__[0].split('+')[1])
                    arr_time_raw = __[1]
                else:
                    arr_time_raw = __[0]
                    arr_delta_day = 0

                arr_time_obj = datetime.datetime.strptime(arr_time_raw, '%H:%M:%S')
                arr_time_obj = datetime.datetime(from_date.year, from_date.month, from_date.day, arr_time_obj.hour, arr_time_obj.minute, arr_time_obj.second)
                arr_time_obj = arr_time_obj + datetime.timedelta(days=arr_delta_day)
                arr_time_str = arr_time_obj.strftime('%Y%m%d%H%M')

                __ = fake_routing['from_segments'][0]['dep_time'].split('|')
                if len(__) == 2:
                    dep_delta_day = int(__[0].split('+')[1])
                    dep_time_raw = __[1]
                else:
                    dep_time_raw = __[0]
                    dep_delta_day = 0
                dep_time_obj = datetime.datetime.strptime(dep_time_raw, '%H:%M:%S')
                dep_time_obj = datetime.datetime(from_date.year, from_date.month, from_date.day, dep_time_obj.hour, dep_time_obj.minute, dep_time_obj.second)
                dep_time_obj = dep_time_obj + datetime.timedelta(days=dep_delta_day)
                dep_time_str = dep_time_obj.strftime('%Y%m%d%H%M')


                flight_number = '-'.join([i['flight_number'] for i in fake_routing['from_segments']])
                cabin_grade = '-'.join([i['cabin_grade'] for i in fake_routing['from_segments']])
                cabin = '-'.join([i['cabin'] for i in fake_routing['from_segments']])
                if search_info.trip_type == 'RT':
                    flight_number += ",%s" % '-'.join([i['flight_number'] for i in fake_routing['ret_segments']])
                    cabin_grade += ",%s" % '-'.join([i['cabin_grade'] for i in fake_routing['ret_segments']])
                    cabin += ",%s" % '-'.join([i['cabin'] for i in fake_routing['ret_segments']])

                    # 添加返程到达时间
                    __ = fake_routing['ret_segments'][-1]['arr_time'].split('|')
                    if len(__) == 2:
                        arr_delta_day = int(__[0].split('+')[1])
                        arr_time_raw = __[1]
                    else:
                        arr_time_raw = __[0]
                        arr_delta_day = 0

                    arr_time_obj = datetime.datetime.strptime(arr_time_raw, '%H:%M:%S')
                    arr_time_obj = datetime.datetime(ret_date.year, ret_date.month, ret_date.day, arr_time_obj.hour, arr_time_obj.minute, arr_time_obj.second)
                    arr_time_obj = arr_time_obj + datetime.timedelta(days=arr_delta_day)
                    arr_time_str += ',%s' % arr_time_obj.strftime('%Y%m%d%H%M')

                    # 添加返程起飞时间
                    __ = fake_routing['ret_segments'][0]['dep_time'].split('|')
                    if len(__) == 2:
                        dep_delta_day = int(__[0].split('+')[1])
                        dep_time_raw = __[1]
                    else:
                        dep_time_raw = __[0]
                        dep_delta_day = 0
                    dep_time_obj = datetime.datetime.strptime(dep_time_raw, '%H:%M:%S')
                    dep_time_obj = datetime.datetime(ret_date.year, ret_date.month, ret_date.day, dep_time_obj.hour, dep_time_obj.minute, dep_time_obj.second)
                    dep_time_obj = dep_time_obj + datetime.timedelta(days=dep_delta_day)
                    dep_time_str += ',%s' % dep_time_obj.strftime('%Y%m%d%H%M')


                rk_info = RoutingKey.serialize(from_airport=fake_data['from_airport'], dep_time=dep_time_str, to_airport=fake_data['to_airport'],
                    arr_time=arr_time_str, flight_number=flight_number,
                    product='HYJ', cabin=cabin,
                    cabin_grade=cabin_grade,
                    adult_price=fix_adult_price, adult_tax=fake_routing['adult_tax'],
                    child_price=fix_child_price, child_tax=fake_routing['child_tax'],provider_channel=self.provider_channel,provider=self.provider,
                    search_from_airport=search_info.from_airport,search_to_airport=search_info.to_airport,from_date=from_date,routing_range=search_info.routing_range,
                    is_multi_segments=is_multi_segments,trip_type=search_info.trip_type,ret_date=ret_date,is_include_operation_carrier=0
                                               )

                flight_routing.routing_key_detail = rk_info['plain']
                flight_routing.routing_key = rk_info['encrypted']
                search_info.assoc_search_routings.append(flight_routing)


            if search_info.ota_work_flow == 'verify':
                if 'verify_no_cabin' in fake_data['action']:

                    search_info.assoc_search_routings = []
                    return search_info
                else:
                    verify_return = fake_data.get('verify_return','')
                    if verify_return:
                        search_info.assoc_search_routings = []
                        raise FlightSearchCritical(err_code=verify_return)

            elif search_info.ota_work_flow == 'order':
                if 'verify_no_cabin' in fake_data['action']:
                    search_info.assoc_search_routings = []
                    return search_info
                else:
                    order_return = fake_data.get('order_return','')
                    if order_return:
                        search_info.assoc_search_routings = []
                        raise FlightSearchCritical(err_code=order_return)
            elif search_info.ota_work_flow in ['search','order_by_roll']:
                if 'set_latency_30' in fake_data['action']:
                    gevent.sleep(30)
                search_return = fake_data.get('search_return','')
                if search_return:
                    search_info.assoc_search_routings = []
                    raise FlightSearchCritical(err_code=search_return)
            else:
                pass
        else:
            return search_info
        # Logger().debug('search_info %s'%search_info)
        return search_info

    def _pay(self, order_info, http_session, pay_dict):
        """
        支付
        :param http_session:
        :return:
        """
        provider_order_id = order_info.provider_order_id
        Logger().info('provider_order_id %s' % provider_order_id)
        Logger().info('fake paying ..... waiting')
        TBG.redis_conn.insert_value('%s_%s' % (self.provider_channel, provider_order_id), 'ISSUE_SUCCESS',ex=86400)

        gevent.sleep(2)
        return pay_dict['lqw_c9337']


class FakeProvider1(FakeProvider):

    """
    证件多次注册会提示FPP_EXISTS

    """
    provider = 'fakeproviderxx'  # 子类继承必须赋
    provider_channel = 'fakeproviderxx_test'  # 子类继承必须赋

    def _sub_register(self, http_session, pax_info, ffp_account_info):
        """
        注册模块
        :param pax_info:
        :return: ffp account info


        u'\u5165\u4f1a\u6e20\u9053\u53f7\u4e3a\u7a7a' 曾经报错：入会渠道号为空
        """
        if pax_info.card_ni:
            ffp_account_info.reg_pid = pax_info.card_ni
            ffp_account_info.reg_card_type = 'NI'
            save_card_no = pax_info.card_ni
        else:
            ffp_account_info.reg_passport = pax_info.card_pp
            ffp_account_info.reg_card_type = 'PP'
            save_card_no = pax_info.card_pp

        Logger().info('fake registering wait..... pax_info %s'%pax_info)
        gevent.sleep(2)
        fake_account = TBG.redis_conn.get_value('fake_account_%s' % (save_card_no))
        if fake_account:
            raise RegisterCritical(err_code='FFP_EXISTS')
        else:
            ffp_account_info.username = str(Random.gen_num(8))
            ffp_account_info.password = str(Random.gen_num(8))
            ffp_account_info.provider = self.provider

        ffp_account_info.reg_birthdate = pax_info.birthdate
        ffp_account_info.reg_gender = pax_info.gender
        TBG.redis_conn.insert_value('fake_account_%s' % (save_card_no),'xxx',ex=86400)

        return ffp_account_info

    def _register(self, http_session, pax_info, ffp_account_info):

        modified_card_no = None
        for x in range(0,5):
            # 尝试三次

            try:
                ffp_account_info = self._sub_register(http_session=http_session,pax_info=pax_info,ffp_account_info=ffp_account_info)
                return ffp_account_info
            except RegisterCritical as e:
                Logger().debug('e.err_code %s' %e.err_code)
                if not e.err_code == 'FFP_EXISTS':
                    raise
            # 账号经过无法注册也无法登陆,修改证件号重新注册
            if pax_info.card_type == 'NI':
                # 身份证修改
                modified_card_no = modify_ni(pax_info.card_ni)
                pax_info.used_card_no = modified_card_no
                pax_info.card_ni = modified_card_no
                pax_info.modified_card_no = modified_card_no
            else:
                modified_card_no = modify_pp(pax_info.card_pp)
                modified_card_no = str(random.randint(10000000, 99999999))
                pax_info.used_card_no = modified_card_no
                pax_info.card_pp = modified_card_no
                pax_info.modified_card_no = modified_card_no
            pax_info.attr_competion()
            Logger().sinfo('start modified_card_no %s register' % modified_card_no)
        else:
            raise RegisterException


class FakeProvider2(FakeProvider):

    """
     路由比价测试

    """
    provider = 'fakeprovider2'  # 子类继承必须赋
    provider_channel = 'fakeprovider_test2'  # 子类继承必须赋

    # SHA - SIN(新加坡) Y 舱 9 舱位 国内到国际
    FAKER_CONFIG = [
        {'from_airport': 'SHA', 'to_airport': 'HKG', 'trip_type': 'OW', 'routing_range': 'OUT', 'action': [],
         'assoc_search_routings': [
             {'adult_price': 1200.0, 'adult_tax': 320.0, 'child_price': 600.0, 'child_tax': 140.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'A', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00', 'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HKG'
                 }
             ],
              'ret_segments': []},
             {'adult_price': 1400.0, 'adult_tax': 320.0, 'child_price': 600.0, 'child_tax': 140.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'B', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '', 'dep_time': '15:00:00', 'arr_time': '18:00:00', 'flight_number': 'MU333',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HKG'
                 }
             ],
              'ret_segments': []}
         ]
         },

        {'from_airport': 'SHA', 'to_airport': 'SIN', 'trip_type': 'OW', 'routing_range': 'OUT', 'action': [],
         'assoc_search_routings': [
             {'adult_price': 1100.0, 'adult_tax': 320.0, 'child_price': 600.0, 'child_tax': 140.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'A', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00', 'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'SIN'
                 }
             ],
              'ret_segments': []},
             {'adult_price': 1400.0, 'adult_tax': 320.0, 'child_price': 600.0, 'child_tax': 140.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'B', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '', 'dep_time': '15:00:00', 'arr_time': '18:00:00', 'flight_number': 'MU333',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'SIN'
                 }
             ],
              'ret_segments': []}
         ]
         },
    ]


class FakeProvider3(FakeProvider):

    """
     路由比价测试

    """
    provider = 'fakeprovider3'  # 子类继承必须赋
    provider_channel = 'fakeprovider_test3'  # 子类继承必须赋

    # SHA - SIN(新加坡) Y 舱 2 舱位 国内到国际
    FAKER_CONFIG = [
        {'from_airport': 'SHA', 'to_airport': 'SIN', 'trip_type': 'OW', 'routing_range': 'OUT', 'action': [],
         'assoc_search_routings': [
             {'adult_price': 900.0, 'adult_tax': 320.0, 'child_price': 600.0, 'child_tax': 140.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'A', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00', 'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'SIN'
                 }
             ],
              'ret_segments': []},
             {'adult_price': 1400.0, 'adult_tax': 320.0, 'child_price': 600.0, 'child_tax': 140.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'B', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '', 'dep_time': '15:00:00', 'arr_time': '18:00:00', 'flight_number': 'MU333',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'SIN'
                 }
             ],
              'ret_segments': []}
         ]
         },
    ]


class FakeProvider4(FakeProvider):

    """
    路由比价测试

    """
    provider = 'fakeprovider4'  # 子类继承必须赋
    provider_channel = 'fakeprovider_test4'  # 子类继承必须赋

    # SHA - SIN(新加坡) Y 舱 2 舱位 国内到国际
    FAKER_CONFIG = [
        {'from_airport': 'SHA', 'to_airport': 'SIN', 'trip_type': 'OW', 'routing_range': 'OUT', 'action': [],
         'assoc_search_routings': [
             {'adult_price': 900.0, 'adult_tax': 320.0, 'child_price': 600.0, 'child_tax': 140.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'A', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00', 'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'SIN'
                 }
             ],
              'ret_segments': []},
             {'adult_price': 1500.0, 'adult_tax': 320.0, 'child_price': 600.0, 'child_tax': 140.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'E', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '', 'dep_time': '15:00:00', 'arr_time': '18:00:00', 'flight_number': 'MU333',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'SIN'
                 }
             ],
              'ret_segments': []}
         ]
         },
    ]


class FakeProvider5(FakeProvider):

    """
    报错异常供应商

    """
    provider = 'fakeprovider5'  # 子类继承必须赋
    provider_channel = 'fakeprovider_test5'  # 子类继承必须赋

    # SHA - SIN(新加坡) Y 舱 2 舱位 国内到国际
    FAKER_CONFIG = [
        {'from_airport': 'SHA', 'to_airport': 'SIN', 'trip_type': 'OW', 'routing_range': 'OUT', 'action': [],
         'assoc_search_routings': [
             {'adult_price': 900.0, 'adult_tax': 320.0, 'child_price': 600.0, 'child_tax': 140.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'A', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00', 'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'SIN'
                 }
             ],
              'ret_segments': []},
             {'adult_price': 1500.0, 'adult_tax': 320.0, 'child_price': 600.0, 'child_tax': 140.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'E', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '', 'dep_time': '15:00:00', 'arr_time': '18:00:00', 'flight_number': 'MU333',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'SIN'
                 }
             ],
              'ret_segments': []}
         ]
         },
    ]

    def _flight_search(self, http_session, search_info):
        raise FlightSearchException(err_code='XXX')


class FakeProvider6(FakeProvider):

    """
    超时供应商

    """
    provider = 'fakeprovider6'  # 子类继承必须赋
    provider_channel = 'fakeprovider_test6'  # 子类继承必须赋

    # SHA - SIN(新加坡) Y 舱 2 舱位 国内到国际
    FAKER_CONFIG = [
        {'from_airport': 'SHA', 'to_airport': 'SIN', 'trip_type': 'OW', 'routing_range': 'OUT', 'action': [],
         'assoc_search_routings': [
             {'adult_price': 900.0, 'adult_tax': 320.0, 'child_price': 600.0, 'child_tax': 140.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'A', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00', 'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'SIN'
                 }
             ],
              'ret_segments': []},
             {'adult_price': 1500.0, 'adult_tax': 320.0, 'child_price': 600.0, 'child_tax': 140.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'E', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '', 'dep_time': '15:00:00', 'arr_time': '18:00:00', 'flight_number': 'MU333',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'SIN'
                 }
             ],
              'ret_segments': []}
         ]
         },
    ]

    def _flight_search(self, http_session, search_info):
        gevent.sleep(100)


class FakeProvider7(FakeProvider):

    """
    降舱测试

    """
    provider = 'fakeprovider7'  # 子类继承必须赋
    provider_channel = 'fakeprovider_test7'  # 子类继承必须赋

    # SHA - SIN(新加坡) Y 舱 2 舱位 国内到国际
    FAKER_CONFIG = [
        {'from_airport': 'SHA', 'to_airport': 'SIN', 'trip_type': 'OW', 'routing_range': 'OUT', 'action': [],
         'assoc_search_routings': [
             {'adult_price': 1000.0, 'adult_tax': 320.0, 'child_price': 600.0, 'child_tax': 140.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'A', 'cabin_count': 2, 'stop_airports': '', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00', 'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'SIN'
                 }
             ],
              'ret_segments': []},
             {'adult_price': 900.0, 'adult_tax': 320.0, 'child_price': 600.0, 'child_tax': 140.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'B', 'cabin_count': 3, 'stop_airports': '', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00', 'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'SIN'
                 }
             ],
              'ret_segments': []},
             {'adult_price': 800.0, 'adult_tax': 320.0, 'child_price': 600.0, 'child_tax': 140.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'C', 'cabin_count': 2, 'stop_airports': '', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00','flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'SIN'
                 }
             ],
              'ret_segments': []},
             {'adult_price': 700.0, 'adult_tax': 320.0, 'child_price': 600.0, 'child_tax': 140.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'D', 'cabin_count': 1, 'stop_airports': '', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00', 'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'SIN'
                 }
             ],
              'ret_segments': []}
         ]
         },
    ]


class FakeProvider8(FakeProvider):

    """
    过滤器测试

    """
    provider = 'fakeprovider8'  # 子类继承必须赋
    provider_channel = 'fakeprovider_test8'  # 子类继承必须赋

    # SHA - SIN(新加坡) Y 舱 2 舱位 国内到国际
    FAKER_CONFIG = [
        {'from_airport': 'SHA', 'to_airport': 'SIN', 'trip_type': 'OW', 'routing_range': 'OUT', 'action': [],
         'assoc_search_routings': [
             {'adult_price': 900.0, 'adult_tax': 320.0, 'child_price': 600.0, 'child_tax': 140.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'A', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00', 'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'SIN'
                 }
             ],
              'ret_segments': []}
         ]
         },
        {'from_airport': 'SHA', 'to_airport': 'HKG', 'trip_type': 'OW', 'routing_range': 'OUT', 'action': [],
         'assoc_search_routings': [
             {'adult_price': 999.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 0.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'X', 'cabin_count': 9, 'stop_airports': 'HGH', 'stop_cities': 'PEK/WEH', 'dep_time': '10:00:00', 'arr_time': '14:00:00', 'flight_number': 'MU222',
                     'routing_number': 1, 'dep_airport': 'SHA', 'arr_airport': 'HKG'
                 }
             ],
              'ret_segments': []}
         ]
         },
    ]


class FakeProvider9(FakeProvider):

    """
    过滤器测试

    """
    provider = 'fakeprovider9'  # 子类继承必须赋
    provider_channel = 'fakeprovider_test9'  # 子类继承必须赋

    # SHA - SIN(新加坡) Y 舱 2 舱位 国内到国际
    FAKER_CONFIG = [
        {'from_airport': 'SHA', 'to_airport': 'SIN', 'trip_type': 'OW', 'routing_range': 'OUT', 'action': [],
         'assoc_search_routings': [
             {'adult_price': 900.0, 'adult_tax': 320.0, 'child_price': 600.0, 'child_tax': 140.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'B', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00', 'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'SIN'
                 }
             ],
              'ret_segments': []}
         ]
         },

        {'from_airport': 'SHA', 'to_airport': 'HKG', 'trip_type': 'OW', 'routing_range': 'OUT', 'action': [],
         'assoc_search_routings': [
             {'adult_price': 1555.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 0.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'Y', 'cabin_count': 9, 'stop_airports': 'HGH', 'stop_cities': 'PEK/WEH', 'dep_time': '10:00:00', 'arr_time': '14:00:00', 'flight_number': 'MU222',
                     'routing_number': 1, 'dep_airport': 'SHA', 'arr_airport': 'HKG'
                 }
             ],
              'ret_segments': []}
         ]
         },
    ]

class FakeProvider10(FakeProvider):
    """
    占位透传ota
    """
    provider = 'fakeprovider10'  # 子类继承必须赋
    provider_channel = 'fakeprovider_test10'  # 子类继承必须赋
    # is_order_directly = True
    verify_realtime_search_count = 1

    def _verify(self, http_session, search_info):


        Logger().debug('PROVIDER verify routing')
        gevent.sleep(2)
        # result = http_session.request(method='GET', url='http://www.baFDSAFDSAFDSAFDSAFDASFDSAFDFDSFDidu.com/', verify=False).to_json()
        selected_fake_data = [routing for routing in self.FAKER_CONFIG if routing['from_airport'] == search_info.from_airport and routing['to_airport'] == search_info.to_airport and routing['trip_type'] == search_info.trip_type]
        if selected_fake_data:
            fake_data = selected_fake_data[0]
            for fake_routing in fake_data.get('assoc_search_routings', []):
                flight_routing = FlightRoutingInfo()
                # flight_routing.routing_key = '32819d9afjdiasoji12'  # 此处需要进行hash
                # 成人价格+税
                flight_routing.adult_price_discount = 86
                flight_routing.adult_price_full_price = 1500.0

                if search_info.ota_work_flow in ['verify', 'order'] and 'verify_price_rise' in fake_data['action']:
                    fix_adult_price = fake_routing['adult_price'] + 100
                    fix_child_price = fake_routing['child_price'] + 100
                    Logger().debug('price rise')
                elif search_info.ota_work_flow in ['verify', 'order'] and 'verify_price_reduce' in fake_data['action']:
                    fix_adult_price = fake_routing['adult_price'] - 100
                    fix_child_price = fake_routing['child_price'] - 100
                    Logger().debug('price reduce')
                else:

                    fix_adult_price = fake_routing['adult_price']
                    fix_child_price = fake_routing['child_price']
                    fix_adult_price = fake_routing['adult_price'] - 122
                    fix_child_price = fake_routing['child_price'] - 122
                    Logger().debug('price no change')
                flight_routing.adult_price = fix_adult_price
                flight_routing.adult_tax = fake_routing['adult_tax']
                flight_routing.child_price = fix_child_price
                flight_routing.child_tax = fake_routing['child_tax']
                flight_routing.product_type = 'DEFAULT'

                # 单程无经停非中转 routing_key 生成代码
                from_date = datetime.datetime.strptime(search_info.from_date, '%Y-%m-%d')
                ret_date = ''
                routing_number = 1
                for fake_segment in fake_routing['from_segments']:

                    __ = fake_segment['dep_time'].split('|')
                    if len(__) == 2:
                        dep_delta_day = int(__[0].split('+')[1])
                        dep_time_raw = __[1]
                    else:
                        dep_time_raw = __[0]
                        dep_delta_day = 0

                    __ = fake_segment['arr_time'].split('|')
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
                    flight_segment.carrier = fake_segment.get('carrier', 'MU')
                    flight_segment.dep_airport = fake_segment['dep_airport']
                    flight_segment.dep_time = dep_time
                    flight_segment.arr_airport = fake_segment['arr_airport']
                    flight_segment.arr_time = arr_time
                    flight_segment.cabin = fake_segment['cabin']
                    flight_segment.cabin_count = fake_segment['cabin_count']
                    flight_segment.flight_number = fake_segment['flight_number']
                    flight_segment.dep_terminal = 'T1'
                    flight_segment.arr_terminal = 'T2'
                    flight_segment.cabin_grade = fake_segment['cabin_grade']
                    duration = 320
                    flight_segment.duration = duration
                    flight_segment.routing_number = routing_number
                    flight_segment.stop_cities = fake_segment['stop_cities']
                    flight_segment.stop_airports = fake_segment['stop_airports']
                    routing_number += 1
                    flight_routing.from_segments.append(flight_segment)

                for fake_segment in fake_routing['ret_segments']:
                    __ = fake_segment['dep_time'].split('|')
                    if len(__) == 2:
                        dep_delta_day = int(__[0].split('+')[1])
                        dep_time_raw = __[1]
                    else:
                        dep_time_raw = __[0]
                        dep_delta_day = 0

                    __ = fake_segment['arr_time'].split('|')
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
                    flight_segment.carrier = fake_segment.get('carrier', 'MU')
                    flight_segment.dep_airport = fake_segment['dep_airport']
                    flight_segment.dep_time = dep_time
                    flight_segment.arr_airport = fake_segment['arr_airport']
                    flight_segment.arr_time = arr_time
                    flight_segment.cabin = fake_segment['cabin']
                    flight_segment.cabin_count = fake_segment['cabin_count']
                    flight_segment.flight_number = fake_segment['flight_number']
                    flight_segment.dep_terminal = 'T1'
                    flight_segment.arr_terminal = 'T2'
                    flight_segment.cabin_grade = fake_segment['cabin_grade']
                    duration = 320
                    flight_segment.duration = duration
                    flight_segment.routing_number = routing_number
                    flight_segment.stop_cities = fake_segment['stop_cities']
                    flight_segment.stop_airports = fake_segment['stop_airports']
                    routing_number += 1
                    flight_routing.ret_segments.append(flight_segment)

                if routing_number > 1:
                    is_multi_segments = 1
                else:
                    is_multi_segments = 0

                __ = fake_routing['from_segments'][0]['dep_time'].split('|')
                if len(__) == 2:
                    dep_delta_day = int(__[0].split('+')[1])
                    dep_time_raw = __[1]
                else:
                    dep_time_raw = __[0]
                    dep_delta_day = 0
                dep_time_obj = datetime.datetime.strptime(dep_time_raw, '%H:%M:%S')
                dep_time_obj = datetime.datetime(from_date.year, from_date.month, from_date.day, dep_time_obj.hour, dep_time_obj.minute, dep_time_obj.second)
                dep_time_obj = dep_time_obj + datetime.timedelta(days=dep_delta_day)

                __ = fake_routing['from_segments'][-1]['arr_time'].split('|')
                if len(__) == 2:
                    arr_delta_day = int(__[0].split('+')[1])
                    arr_time_raw = __[1]
                else:
                    arr_time_raw = __[0]
                    arr_delta_day = 0

                arr_time_obj = datetime.datetime.strptime(arr_time_raw, '%H:%M:%S')
                arr_time_obj = datetime.datetime(from_date.year, from_date.month, from_date.day, arr_time_obj.hour, arr_time_obj.minute, arr_time_obj.second)
                arr_time_obj = arr_time_obj + datetime.timedelta(days=arr_delta_day)
                arr_time_str = arr_time_obj.strftime('%Y%m%d%H%M')

                __ = fake_routing['from_segments'][0]['dep_time'].split('|')
                if len(__) == 2:
                    dep_delta_day = int(__[0].split('+')[1])
                    dep_time_raw = __[1]
                else:
                    dep_time_raw = __[0]
                    dep_delta_day = 0
                dep_time_obj = datetime.datetime.strptime(dep_time_raw, '%H:%M:%S')
                dep_time_obj = datetime.datetime(from_date.year, from_date.month, from_date.day, dep_time_obj.hour, dep_time_obj.minute, dep_time_obj.second)
                dep_time_obj = dep_time_obj + datetime.timedelta(days=dep_delta_day)
                dep_time_str = dep_time_obj.strftime('%Y%m%d%H%M')

                if fake_routing['ret_segments']:
                    __ = fake_routing['ret_segments'][-1]['arr_time'].split('|')
                    if len(__) == 2:
                        arr_delta_day = int(__[0].split('+')[1])
                        arr_time_raw = __[1]
                    else:
                        arr_time_raw = __[0]
                        arr_delta_day = 0

                    arr_time_obj = datetime.datetime.strptime(arr_time_raw, '%H:%M:%S')
                    arr_time_obj = datetime.datetime(from_date.year, from_date.month, from_date.day, arr_time_obj.hour, arr_time_obj.minute, arr_time_obj.second)
                    arr_time_obj = arr_time_obj + datetime.timedelta(days=arr_delta_day)
                    arr_time_str = arr_time_obj.strftime('%Y%m%d%H%M')

                flight_number = '-'.join([i['flight_number'] for i in fake_routing['from_segments']])
                cabin_grade = '-'.join([i['cabin_grade'] for i in fake_routing['from_segments']])
                cabin = '-'.join([i['cabin'] for i in fake_routing['from_segments']])
                if search_info.trip_type == 'RT':
                    flight_number += ",%s" % '-'.join([i['flight_number'] for i in fake_routing['ret_segments']])
                    cabin_grade += ",%s" % '-'.join([i['cabin_grade'] for i in fake_routing['ret_segments']])
                    cabin += ",%s" % '-'.join([i['cabin'] for i in fake_routing['ret_segments']])

                    # 添加返程到达时间
                    __ = fake_routing['ret_segments'][-1]['arr_time'].split('|')
                    if len(__) == 2:
                        arr_delta_day = int(__[0].split('+')[1])
                        arr_time_raw = __[1]
                    else:
                        arr_time_raw = __[0]
                        arr_delta_day = 0

                    arr_time_obj = datetime.datetime.strptime(arr_time_raw, '%H:%M:%S')
                    arr_time_obj = datetime.datetime(from_date.year, from_date.month, from_date.day, arr_time_obj.hour, arr_time_obj.minute, arr_time_obj.second)
                    arr_time_obj = arr_time_obj + datetime.timedelta(days=arr_delta_day)
                    arr_time_str += ',%s' % arr_time_obj.strftime('%Y%m%d%H%M')

                    # 添加返程起飞时间
                    __ = fake_routing['ret_segments'][0]['dep_time'].split('|')
                    if len(__) == 2:
                        dep_delta_day = int(__[0].split('+')[1])
                        dep_time_raw = __[1]
                    else:
                        dep_time_raw = __[0]
                        dep_delta_day = 0
                    dep_time_obj = datetime.datetime.strptime(dep_time_raw, '%H:%M:%S')
                    dep_time_obj = datetime.datetime(from_date.year, from_date.month, from_date.day, dep_time_obj.hour, dep_time_obj.minute, dep_time_obj.second)
                    dep_time_obj = dep_time_obj + datetime.timedelta(days=dep_delta_day)
                    dep_time_str += ',%s' % dep_time_obj.strftime('%Y%m%d%H%M')
                    ret_date = datetime.datetime.strptime(search_info.ret_date, '%Y-%m-%d')

                rk_info = RoutingKey.serialize(from_airport=fake_data['from_airport'], dep_time=dep_time_str, to_airport=fake_data['to_airport'],
                                               arr_time=arr_time_str, flight_number=flight_number,
                                               product='HYJ', cabin=cabin,
                                               cabin_grade=cabin_grade,
                                               adult_price=fix_adult_price, adult_tax=fake_routing['adult_tax'],
                                               child_price=fix_child_price, child_tax=fake_routing['child_tax'], provider_channel=self.provider_channel, provider=self.provider,
                                               search_from_airport=search_info.from_airport, search_to_airport=search_info.to_airport, from_date=from_date, routing_range=search_info.routing_range,
                                               is_multi_segments=is_multi_segments, trip_type=search_info.trip_type, ret_date=ret_date
                                               )

                flight_routing.routing_key_detail = rk_info['plain']
                Logger().sinfo('verify !!!!! flight_routing.routing_key_detail %s' % flight_routing.routing_key_detail)
                flight_routing.routing_key = rk_info['encrypted']
                cp_key = RoutingKey.trans_cp_key(flight_routing.routing_key_detail,is_unserialized=False)
                search_info_cp_key = RoutingKey.trans_cp_key(search_info.verify_routing_key, is_unserialized=False,is_encrypted=True)
                Logger().sdebug('search_info.search_info_cp_key %s cp_key %s ' % (search_info_cp_key,cp_key))
                if search_info_cp_key == cp_key:
                    return flight_routing

        raise ProviderVerifyException('TEST')
    # def _booking(self, http_session, order_info):
    #     """
    #
    #     pax_name = '刘志'
    #     pax_email = 'fdaljrj@tongdun.org'
    #     pax_mobile = '15216666047'
    #     pax_pid = '230903199004090819'
    #     pax_id_type = 'NI'
    #     contact_name = pax_name
    #     contact_email = pax_email
    #     contact_mobile = pax_mobile
    #
    #     :param http_session:
    #     :param order_info:
    #     :return: order_info class
    #     """
    #
    #     Logger().info('fake ordering.....wait')
    #     gevent.sleep(2)
    #     raise BookingException('TEST')

class FakeProvider11(FakeProvider):
    """
    动态运价 OTA低价看板爬取模拟
    """
    provider = 'fakeprovider11'  # 子类继承必须赋
    provider_channel = 'fakeprovider_test11'  # 子类继承必须赋
    verify_realtime_search_count = 1

    FAKER_CONFIG = [

        # SHA - HRB（哈尔滨） Y 舱 9 舱位 无特殊
        {'from_airport': 'SHA', 'to_airport': 'HRB', 'trip_type': 'OW', 'routing_range': 'IN', 'action': [],
         'assoc_search_routings': [
             {'adult_price': 1200.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'A', 'cabin_count': 9, "carrier": 'MU', 'stop_airports': '', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00',
                     'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 }
             ],
              'ret_segments': []},
             {'adult_price': 1100.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'B', 'cabin_count': 3, 'stop_airports': '', "carrier": '9C', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00',
                     'flight_number': '9C222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 }
             ],
              'ret_segments': []},
             {'adult_price': 600.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'C', 'cabin_count': 2, 'stop_airports': '', "carrier": 'MU', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00',
                     'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 },
                 {
                     'cabin_grade': 'Y', 'cabin': 'C', 'cabin_count': 2, 'stop_airports': '', "carrier": 'DZ', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00',
                     'flight_number': 'DZ222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 }
             ],
              'ret_segments': []},
             {'adult_price': 900.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'D', 'cabin_count': 1, 'stop_airports': '', "carrier": 'MU', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00',
                     'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 }
             ],
              'ret_segments': []},
             {'adult_price': 300.0, 'adult_tax': 100.0, 'child_price': 250.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'D', 'cabin_count': 1, 'stop_airports': '', 'stop_cities': '', 'dep_time': '08:20:00', 'arr_time': '11:35:00', 'flight_number': 'MU5613',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 }
             ],
              'ret_segments': []},

             {'adult_price': 2200.0, 'adult_tax': 100.0, 'child_price': 250.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'Z', 'cabin_count': 1, 'stop_airports': '', 'stop_cities': '', 'dep_time': '08:20:00', 'arr_time': '11:35:00', 'flight_number': 'MU999',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 }
             ],
              'ret_segments': []}
         ]
         },
        # SHA - HRB（哈尔滨） Y 舱 9 舱位 往返
        {'from_airport': 'SHA', 'to_airport': 'HRB', 'trip_type': 'RT', 'routing_range': 'I2I', 'action': [],
         'assoc_search_routings': [
             {'adult_price': 2177.0, 'adult_tax': 60.0, 'child_price': 1087.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'A', 'cabin_count': 9, "carrier": 'MU', 'stop_airports': '', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00',
                     'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 }
             ],
              'ret_segments': [{
                  'cabin_grade': 'Y', 'cabin': 'U', 'cabin_count': 9, "carrier": 'MU', 'stop_airports': '', 'stop_cities': '', 'dep_time': '+1|09:00:00', 'arr_time': '+1|11:00:00',
                  'flight_number': 'MU1932',
                  'routing_number': 2,
                  'dep_airport': 'HRB', 'arr_airport': 'SHA'
              }]},
             {'adult_price': 1644.0, 'adult_tax': 60.0, 'child_price': 822.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'B', 'cabin_count': 3, 'stop_airports': '', "carrier": '9C', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00',
                     'flight_number': '9C222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 }
             ],
              'ret_segments': [{
                  'cabin_grade': 'Y', 'cabin': 'X', 'cabin_count': 9, "carrier": 'MU', 'stop_airports': '', 'stop_cities': '', 'dep_time': '+1|15:00:00', 'arr_time': '+1|19:00:00',
                  'flight_number': 'MU777',
                  'routing_number': 2,
                  'dep_airport': 'HRB', 'arr_airport': 'SHA'
              }]},
             {'adult_price': 3030.0, 'adult_tax': 60.0, 'child_price': 1510.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'C', 'cabin_count': 2, 'stop_airports': '', "carrier": 'MU', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00',
                     'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'PEK'
                 },
                 {
                     'cabin_grade': 'Y', 'cabin': 'C', 'cabin_count': 2, 'stop_airports': '', "carrier": 'DZ', 'stop_cities': '', 'dep_time': '15:00:00', 'arr_time': '17:00:00',
                     'flight_number': 'DZ222',
                     'routing_number': 2,
                     'dep_airport': 'PEK', 'arr_airport': 'HRB'
                 }
             ],
              'ret_segments': [{
                  'cabin_grade': 'Y', 'cabin': 'Z', 'cabin_count': 9, "carrier": 'MU', 'stop_airports': '', 'stop_cities': '', 'dep_time': '+1|15:00:00', 'arr_time': '+1|19:00:00',
                  'flight_number': 'MU817',
                  'routing_number': 3,
                  'dep_airport': 'HRB', 'arr_airport': 'PEK'
              }, {
                  'cabin_grade': 'Y', 'cabin': 'P', 'cabin_count': 9, "carrier": 'MU', 'stop_airports': '', 'stop_cities': '', 'dep_time': '+1|20:00:00', 'arr_time': '+1|22:00:00',
                  'flight_number': 'MU129',
                  'routing_number': 4,
                  'dep_airport': 'PEK', 'arr_airport': 'SHA'
              }]}
         ]
         },
    ]

    # def _flight_search(self, http_session, search_info):
    #     """
    #     航班爬取模块，
    #     TODO :目前只考虑单程
    #
    #     :return:
    #     """
    #
    #     if not search_info.ota_work_flow:
    #         search_info.ota_work_flow = 'search'
    #     Logger().info('fake flight_searching....wait')
    #     Logger().debug('ota_work_flow %s' % search_info.ota_work_flow)
    #     gevent.sleep(2)
    #
    #     selected_fake_data = [routing for routing in self.FAKER_CONFIG if routing['from_airport'] == search_info.from_airport and routing['to_airport'] == search_info.to_airport]
    #     if selected_fake_data:
    #         fake_data = selected_fake_data[0]
    #         for fake_routing in fake_data.get('assoc_search_routings', []):
    #             flight_routing = FlightRoutingInfo()
    #             # flight_routing.routing_key = '32819d9afjdiasoji12'  # 此处需要进行hash
    #             # 成人价格+税
    #             flight_routing.adult_price_discount = 86
    #             flight_routing.adult_price_full_price = 1500.0
    #
    #             fix_adult_price = fake_routing['adult_price']
    #             fix_child_price = fake_routing['child_price']
    #             Logger().debug('price no change')
    #             flight_routing.adult_price = fix_adult_price - 30
    #             flight_routing.adult_tax = fake_routing['adult_tax']
    #             flight_routing.reference_adult_price = fix_adult_price + 10
    #             flight_routing.reference_adult_tax = fake_routing['adult_tax']
    #             flight_routing.product_type = 'DEFAULT'
    #
    #             # 单程无经停非中转 routing_key 生成代码
    #             from_date = datetime.datetime.strptime(search_info.from_date, '%Y-%m-%d')
    #             dep_time_obj = datetime.datetime.strptime(fake_routing['from_segments'][0]['dep_time'], '%H:%M:%S')
    #             dep_time_obj = datetime.datetime(from_date.year, from_date.month, from_date.day, dep_time_obj.hour, dep_time_obj.minute, dep_time_obj.second)
    #             dep_time = dep_time_obj.strftime('%Y%m%d%H%M')
    #             arr_time_obj = datetime.datetime.strptime(fake_routing['from_segments'][-1]['arr_time'], '%H:%M:%S')
    #             arr_time_obj = datetime.datetime(from_date.year, from_date.month, from_date.day, arr_time_obj.hour, arr_time_obj.minute, arr_time_obj.second)
    #             arr_time = arr_time_obj.strftime('%Y%m%d%H%M')
    #
    #
    #             rk_info = RoutingKey.serialize(from_airport=fake_data['from_airport'], dep_time='N/A', to_airport=fake_data['to_airport'],
    #                                            arr_time='N/A', flight_number='-'.join([i['flight_number'] for i in fake_routing['from_segments']]),
    #                                            product='N/A', cabin='-'.join([i['cabin'] for i in fake_routing['from_segments']]),
    #                                            adult_price=fix_adult_price, adult_tax=fake_routing['adult_tax'],
    #                                            child_price=0, child_tax=0, provider_channel=self.provider_channel, provider=self.provider,
    #                                            search_from_airport=search_info.from_airport, search_to_airport=search_info.to_airport, from_date=from_date, routing_range=search_info.routing_range,
    #                                            is_multi_segments=1
    #                                            )
    #             flight_routing.routing_key_detail = rk_info['plain']
    #             flight_routing.routing_key = rk_info['encrypted']
    #             search_info.assoc_search_routings.append(flight_routing)
    #
    #         if search_info.ota_work_flow == 'verify':
    #             if 'verify_no_cabin' in fake_data['action']:
    #
    #                 search_info.assoc_search_routings = []
    #                 return search_info
    #             else:
    #                 verify_return = fake_data.get('verify_return', '')
    #                 if verify_return:
    #                     search_info.assoc_search_routings = []
    #                     raise FlightSearchCritical(err_code=verify_return)
    #
    #         elif search_info.ota_work_flow == 'order':
    #             if 'verify_no_cabin' in fake_data['action']:
    #                 search_info.assoc_search_routings = []
    #                 return search_info
    #             else:
    #                 order_return = fake_data.get('order_return', '')
    #                 if order_return:
    #                     search_info.assoc_search_routings = []
    #                     raise FlightSearchCritical(err_code=order_return)
    #         elif search_info.ota_work_flow in ['search', 'order_by_roll']:
    #             if 'set_latency_30' in fake_data['action']:
    #                 gevent.sleep(30)
    #             search_return = fake_data.get('search_return', '')
    #             if search_return:
    #                 search_info.assoc_search_routings = []
    #                 raise FlightSearchCritical(err_code=search_return)
    #         else:
    #             pass
    #     else:
    #         return search_info
    #     # Logger().debug('search_info %s'%search_info)
    #     return search_info

class FakeProvider12(FakeProvider):
    """
    占位透传ota
    """
    provider = 'fakeprovider12'  # 子类继承必须赋
    provider_channel = 'fakeprovider_test12'  # 子类继承必须赋
    verify_realtime_search_count = 1

    FAKER_CONFIG = [

        # SHA - HRB（哈尔滨） Y 舱 9 舱位 无特殊
        {'from_airport': 'SHA', 'to_airport': 'HRB', 'trip_type': 'OW', 'routing_range': 'IN', 'action': [],
         'assoc_search_routings': [
             {'adult_price': 1200.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'A', 'cabin_count': 9, "carrier": 'MU', 'stop_airports': '', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00',
                     'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 }
             ],
              'ret_segments': []},
             {'adult_price': 1100.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'B', 'cabin_count': 3, 'stop_airports': '', "carrier": '9C', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00',
                     'flight_number': '9C222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 }
             ],
              'ret_segments': []},
             {'adult_price': 333.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'C', 'cabin_count': 2, 'stop_airports': '', "carrier": 'MU', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00',
                     'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 },
                 {
                     'cabin_grade': 'Y', 'cabin': 'C', 'cabin_count': 2, 'stop_airports': '', "carrier": 'DZ', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00',
                     'flight_number': 'DZ222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 }
             ],
              'ret_segments': []},
             {'adult_price': 900.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'D', 'cabin_count': 1, 'stop_airports': '', "carrier": 'MU', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00',
                     'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 }
             ],
              'ret_segments': []},
             {'adult_price': 3900.0, 'adult_tax': 100.0, 'child_price': 250.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'D', 'cabin_count': 1, 'stop_airports': '', 'stop_cities': '', 'dep_time': '08:20:00', 'arr_time': '11:35:00', 'flight_number': 'MU2121',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 }
             ],
              'ret_segments': []}
         ]
         }]


class FakeProvider13(FakeProvider):
    """
    新模式 多供应商验价 生单测试
    """
    provider = 'fakeprovider13'  # 子类继承必须赋
    provider_channel = 'fakeprovider_test13'  # 子类继承必须赋
    verify_realtime_search_count = 1

    FAKER_CONFIG = [

        # SHA - HRB（哈尔滨） Y 舱 9 舱位 无特殊
        {'from_airport': 'SHA', 'to_airport': 'HRB', 'trip_type': 'OW', 'routing_range': 'IN', 'action': [],
         'assoc_search_routings': [
             {'adult_price': 1270.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'A', 'cabin_count': 9, "carrier": 'MU', 'stop_airports': '', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00',
                     'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 }
             ],
              'ret_segments': []},
             {'adult_price': 1100.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'B', 'cabin_count': 3, 'stop_airports': '', "carrier": '9C', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00',
                     'flight_number': '9C222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 }
             ],
              'ret_segments': []},
             {'adult_price': 333.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'C', 'cabin_count': 2, 'stop_airports': '', "carrier": 'MU', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00',
                     'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 },
                 {
                     'cabin_grade': 'Y', 'cabin': 'C', 'cabin_count': 2, 'stop_airports': '', "carrier": 'DZ', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00',
                     'flight_number': 'DZ222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 }
             ],
              'ret_segments': []},
             {'adult_price': 900.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'D', 'cabin_count': 1, 'stop_airports': '', "carrier": 'MU', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00',
                     'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 }
             ],
              'ret_segments': []},
             {'adult_price': 3900.0, 'adult_tax': 100.0, 'child_price': 250.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'D', 'cabin_count': 1, 'stop_airports': '', 'stop_cities': '', 'dep_time': '08:20:00', 'arr_time': '11:35:00', 'flight_number': 'MU2121',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 }
             ],
              'ret_segments': []}
         ]
         }]


class FakeProvider14(FakeProvider):
    """
    新模式 多供应商验价 生单测试
    """
    provider = 'fakeprovider14'  # 子类继承必须赋
    provider_channel = 'fakeprovider_test14'  # 子类继承必须赋
    verify_realtime_search_count = 1

    FAKER_CONFIG = [

        # SHA - HRB（哈尔滨） Y 舱 9 舱位 无特殊
        {'from_airport': 'SHA', 'to_airport': 'HRB', 'trip_type': 'OW', 'routing_range': 'IN', 'action': [],
         'assoc_search_routings': [
             {'adult_price': 1260.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'A', 'cabin_count': 9, "carrier": 'MU', 'stop_airports': '', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00',
                     'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 }
             ],
              'ret_segments': []},
             {'adult_price': 1100.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'B', 'cabin_count': 3, 'stop_airports': '', "carrier": '9C', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00',
                     'flight_number': '9C222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 }
             ],
              'ret_segments': []},
             {'adult_price': 333.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'C', 'cabin_count': 2, 'stop_airports': '', "carrier": 'MU', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00',
                     'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 },
                 {
                     'cabin_grade': 'Y', 'cabin': 'C', 'cabin_count': 2, 'stop_airports': '', "carrier": 'DZ', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00',
                     'flight_number': 'DZ222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 }
             ],
              'ret_segments': []},
             {'adult_price': 900.0, 'adult_tax': 60.0, 'child_price': 600.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'D', 'cabin_count': 1, 'stop_airports': '', "carrier": 'MU', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00',
                     'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 }
             ],
              'ret_segments': []},
             {'adult_price': 3900.0, 'adult_tax': 100.0, 'child_price': 250.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'D', 'cabin_count': 1, 'stop_airports': '', 'stop_cities': '', 'dep_time': '08:20:00', 'arr_time': '11:35:00', 'flight_number': 'MU2121',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 }
             ],
              'ret_segments': []}
         ]
         }]


class FakeProvider15(FakeProvider):
    """
    新模式 多供应商验价 生单测试
    """
    provider = 'fakeprovider15'  # 子类继承必须赋
    provider_channel = 'fakeprovider_test15'  # 子类继承必须赋
    verify_realtime_search_count = 1

    FAKER_CONFIG = [
        {'from_airport': 'SHA', 'to_airport': 'HRB', 'trip_type': 'OW', 'routing_range': 'IN', 'action': [],
         'assoc_search_routings': [
             {'adult_price': 900.0, 'adult_tax': 60.0, 'reference_adult_price': 990, 'child_price': 600.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'D', 'cabin_count': 6, 'stop_airports': '', "carrier": 'MU', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00',
                     'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 }
             ],
              'ret_segments': []},
             {'adult_price': 777.0, 'adult_tax': 60.0, 'reference_adult_price': 990, 'child_price': 600.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'G', 'cabin_count': 1, 'stop_airports': '', "carrier": 'MU', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00',
                     'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 }
             ],
              'ret_segments': []}

         ]
         },



    ]


class FakeProvider16(FakeProvider):
    """
    模拟低价看板，给出R2价格
    """
    provider = 'fakeprovider16'  # 子类继承必须赋
    provider_channel = 'fakeprovider_test16'  # 子类继承必须赋
    verify_realtime_search_count = 1

    FAKER_CONFIG = [
        {'from_airport': 'SHA', 'to_airport': 'HRB', 'trip_type': 'OW', 'routing_range': 'IN', 'action': [],
         'assoc_search_routings': [
             {'adult_price': 500.0, 'adult_tax': 60.0, 'reference_adult_price': 1200, 'child_price': 600.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'D', 'cabin_count': 6, 'stop_airports': '', "carrier": 'MU', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00',
                     'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 }
             ],
              'ret_segments': []},
             {'adult_price': 910.0, 'adult_tax': 60.0, 'reference_adult_price': 1200, 'child_price': 600.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'G', 'cabin_count': 1, 'stop_airports': '', "carrier": 'MU', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00',
                     'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 }
             ],
              'ret_segments': []}

         ]
         },

]


class FakeProvider17(FakeProvider):
    """

    """
    provider = 'fakeprovider17'  # 子类继承必须赋
    provider_channel = 'fakeprovider_test17'  # 子类继承必须赋
    verify_realtime_search_count = 1
    FAKER_CONFIG = []


class FakeProvider18(FakeProvider):
    """
    模拟C端无舱位航线
    虚拟仓
    """
    provider = 'fakeprovider18'  # 子类继承必须赋
    provider_channel = 'fakeprovider_test18'  # 子类继承必须赋
    verify_realtime_search_count = 2

    FAKER_CONFIG = [
        {'from_airport': 'SHA', 'to_airport': 'HRB', 'trip_type': 'OW', 'routing_range': 'IN', 'action': [],
         'assoc_search_routings': [
             {'adult_price': 920.0, 'adult_tax': 60.0, 'reference_adult_price': 1200, 'child_price': 600.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'N/A', 'cabin_count': 6, 'stop_airports': '', "carrier": 'AK', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00',
                     'flight_number': 'AK222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 }
             ],
              'ret_segments': []},
             {'adult_price': 910.0, 'adult_tax': 60.0, 'reference_adult_price': 1200, 'child_price': 600.0, 'child_tax': 60.0, 'from_segments': [
                 {
                     'cabin_grade': 'Y', 'cabin': 'N/A', 'cabin_count': 1, 'stop_airports': '', "carrier": 'MU', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '14:00:00',
                     'flight_number': 'MU222',
                     'routing_number': 1,
                     'dep_airport': 'SHA', 'arr_airport': 'HRB'
                 }
             ],
              'ret_segments': []}

         ]
         },

]