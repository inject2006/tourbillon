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

class PdcFaker(ProvderAutoBase):
    """
    私有数据库
    此库后续将用于扩展私有运价体系。
    """
    timeout = 15  # 请求超时时间
    provider = 'pdc_faker'  # 子类继承必须赋
    provider_channel = 'pdc_faker'  # 子类继承必须赋
    operation_product_type = '会员折扣'  # 运价类型：0: GDS公布运价 1:GDS私有运价 2:航司官网产品  3:廉价航司产品 4:特价产品
    operation_product_mode = 'A2A'
    pay_channel = '99BILL'
    verify_realtime_search_count = 1
    trip_type_list = ['OW', 'RT']
    no_flight_ttl = 3600 * 3  # 无航班缓存超时时间设定


    CACHE_PR_CONFIG = {
        1: {'cabin_expired_time': 3600 * 12, 'cabin_attenuation': 3,'fare_expired_time':86400 * 30},
        2: {'cabin_expired_time': 3600 * 3, 'cabin_attenuation': 2,'fare_expired_time':86400 * 20},
        3: {'cabin_expired_time': 60 * 60 * 1, 'cabin_attenuation': 1,'fare_expired_time':86400 * 10},
        4: {'cabin_expired_time': 60 * 40, 'cabin_attenuation': 1,'fare_expired_time':86400 * 5},
        5: {'cabin_expired_time': 60 * 30, 'cabin_attenuation': 0,'fare_expired_time':86400},

    }
    search_interval_time = 0

    # 暂时先使用配置替代
    PDC_CONFIG = [

        #
        # {'from_airport': 'DLC', 'to_airport': 'FNA', 'trip_type': 'OW', 'routing_range': 'OUT', 'action': [],'pax_limit':{'card_no_prefix':'DDD'},
        #  'assoc_search_routings': [
        #      {'adult_price': 66000.0, 'adult_tax': 2754.0, 'child_price': 66000.0, 'child_tax': 2754.0, 'from_segments': [
        #          {
        #              'cabin_grade': 'Y', 'cabin': 'N', 'cabin_count': 9, 'stop_airports': 'FOC', 'stop_cities': '', 'dep_time': '10:00:00', 'arr_time': '18:00:00', 'flight_number': 'MF866',
        #              'routing_number': 1, 'dep_airport': 'DLC', 'arr_airport': 'BKK', 'duration':445,'carrier':'MF'
        #          },
        #          {
        #              'cabin_grade': 'Y', 'cabin': 'G', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '', 'dep_time': '+1|00:30:00', 'arr_time': '+1|11:00:00', 'flight_number': 'TG973',
        #              'routing_number': 2, 'dep_airport': 'BKK', 'arr_airport': 'BRU', 'duration':660,'carrier':'TG'
        #          },
        #          {
        #              'cabin_grade': 'Y', 'cabin': 'I', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '', 'dep_time': '+1|14:00:00', 'arr_time': '+1|20:00:00', 'flight_number': 'SN440',
        #              'routing_number': 3, 'dep_airport': 'BRU', 'arr_airport': 'FNA', 'duration': 360,'carrier':'SN'
        #          }
        #      ],
        #       'ret_segments': []}
        #  ]
        #  },

        {'from_airport': 'HRB', 'to_airport': 'FMA', 'trip_type': 'RT', 'routing_range': 'OUT', 'action': [],
         'pax_limit': {'card_no_prefix': 'GD02'},
         'assoc_search_routings': [
             {'adult_price': 135000.0, 'adult_tax': 5754.0, 'child_price': 135000.0, 'child_tax': 5754.0,
              'from_segments': [
                  {
                      'cabin_grade': 'Y', 'cabin': 'N', 'cabin_count': 9, 'stop_airports': 'FOC', 'stop_cities': '',
                      'dep_time': '10:00:00', 'arr_time': '18:00:00', 'flight_number': 'PG866',
                      'routing_number': 1, 'dep_airport': 'HRB', 'arr_airport': 'BKK', 'duration': 445, 'carrier': 'PG'
                  },
                  {
                      'cabin_grade': 'Y', 'cabin': 'G', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '',
                      'dep_time': '+1|00:30:00', 'arr_time': '+1|11:00:00', 'flight_number': 'TG973',
                      'routing_number': 2, 'dep_airport': 'BKK', 'arr_airport': 'BRU', 'duration': 660, 'carrier': 'TG'
                  },
                  {
                      'cabin_grade': 'Y', 'cabin': 'I', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '',
                      'dep_time': '+1|14:00:00', 'arr_time': '+1|20:00:00', 'flight_number': 'SN440',
                      'routing_number': 3, 'dep_airport': 'BRU', 'arr_airport': 'FMA', 'duration': 360, 'carrier': 'SN'
                  }
              ],
              'ret_segments': [
                  {
                      'cabin_grade': 'Y', 'cabin': 'I', 'cabin_count': 9, 'stop_airports': 'FOC', 'stop_cities': '',
                      'dep_time': '10:00:00', 'arr_time': '18:00:00', 'flight_number': 'SN540',
                      'routing_number': 4, 'dep_airport': 'FMA', 'arr_airport': 'BRU', 'duration': 360, 'carrier': 'SN'
                  },
                  {
                      'cabin_grade': 'Y', 'cabin': 'G', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '',
                      'dep_time': '+1|00:30:00', 'arr_time': '+1|11:00:00', 'flight_number': 'TG673',
                      'routing_number': 5, 'dep_airport': 'BRU', 'arr_airport': 'BKK', 'duration': 660, 'carrier': 'TG'
                  },
                  {
                      'cabin_grade': 'Y', 'cabin': 'N', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '',
                      'dep_time': '+1|14:00:00', 'arr_time': '+1|20:00:00', 'flight_number': 'PG666',
                      'routing_number': 6, 'dep_airport': 'BKK', 'arr_airport': 'HRB', 'duration': 445, 'carrier': 'PG'
                  }
              ]}
         ]
         },
        {'from_airport': 'HRB', 'to_airport': 'FMA', 'trip_type': 'OW', 'routing_range': 'OUT', 'action': [],
         'pax_limit': {'card_no_prefix': ''},
         'assoc_search_routings': [
             {'adult_price': 65000.0, 'adult_tax': 2754.0, 'child_price': 65000.0, 'child_tax': 2754.0,
              'from_segments': [
                  {
                      'cabin_grade': 'Y', 'cabin': 'N', 'cabin_count': 9, 'stop_airports': 'FOC', 'stop_cities': '',
                      'dep_time': '10:00:00', 'arr_time': '18:00:00', 'flight_number': 'PG866',
                      'routing_number': 1, 'dep_airport': 'HRB', 'arr_airport': 'BKK', 'duration': 445, 'carrier': 'PG'
                  },
                  {
                      'cabin_grade': 'Y', 'cabin': 'G', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '',
                      'dep_time': '+1|00:30:00', 'arr_time': '+1|11:00:00', 'flight_number': 'TG973',
                      'routing_number': 2, 'dep_airport': 'BKK', 'arr_airport': 'BRU', 'duration': 660, 'carrier': 'TG'
                  },
                  {
                      'cabin_grade': 'Y', 'cabin': 'I', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '',
                      'dep_time': '+1|14:00:00', 'arr_time': '+1|20:00:00', 'flight_number': 'SN440',
                      'routing_number': 3, 'dep_airport': 'BRU', 'arr_airport': 'FMA', 'duration': 360, 'carrier': 'SN'
                  }
              ],
              'ret_segments': [

              ]}
         ]
         },
        {'from_airport': 'JMU', 'to_airport': 'DMM', 'trip_type': 'OW', 'routing_range': 'I2O', 'action': [],
         'pax_limit': {'card_no_prefix': 'GD02'},
         'assoc_search_routings': [
             {'adult_price': 99000.0, 'adult_tax': 2754.0, 'child_price': 95000.0, 'child_tax': 2754.0,
              'from_segments': [
                  {
                      'cabin_grade': 'Y', 'cabin': 'N', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '',
                      'dep_time': '10:00:00', 'arr_time': '15:00:00', 'flight_number': 'PG237',
                      'routing_number': 1, 'dep_airport': 'JMU', 'arr_airport': 'PVG', 'duration': 445, 'carrier': 'PG'
                  },
                  {
                      'cabin_grade': 'Y', 'cabin': 'G', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '',
                      'dep_time': '+1|00:50:00', 'arr_time': '+1|11:00:00', 'flight_number': 'TG993',
                      'routing_number': 2, 'dep_airport': 'PVG', 'arr_airport': 'ISB', 'duration': 660, 'carrier': 'TG'
                  },
                  {
                      'cabin_grade': 'Y', 'cabin': 'I', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '',
                      'dep_time': '+1|14:00:00', 'arr_time': '+1|20:00:00', 'flight_number': 'SN219',
                      'routing_number': 3, 'dep_airport': 'ISB', 'arr_airport': 'DMM', 'duration': 360, 'carrier': 'SN'
                  }
              ],
              'ret_segments': [

              ]}
         ]
         },
        {'from_airport': 'JMU', 'to_airport': 'DMM', 'trip_type': 'RT', 'routing_range': 'I2O', 'action': [],
         'pax_limit': {'card_no_prefix': 'GD02'},
         'assoc_search_routings': [
             {'adult_price': 145000.0, 'adult_tax': 5754.0, 'child_price': 145000.0, 'child_tax': 5754.0,
              'from_segments': [
                  {
                      'cabin_grade': 'Y', 'cabin': 'N', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '',
                      'dep_time': '10:00:00', 'arr_time': '15:00:00', 'flight_number': 'PG237',
                      'routing_number': 1, 'dep_airport': 'JMU', 'arr_airport': 'PVG', 'duration': 445, 'carrier': 'PG'
                  },
                  {
                      'cabin_grade': 'Y', 'cabin': 'G', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '',
                      'dep_time': '+1|00:50:00', 'arr_time': '+1|11:00:00', 'flight_number': 'TG993',
                      'routing_number': 2, 'dep_airport': 'PVG', 'arr_airport': 'ISB', 'duration': 660, 'carrier': 'TG'
                  },
                  {
                      'cabin_grade': 'Y', 'cabin': 'I', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '',
                      'dep_time': '+1|14:00:00', 'arr_time': '+1|20:00:00', 'flight_number': 'SN219',
                      'routing_number': 3, 'dep_airport': 'ISB', 'arr_airport': 'DMM', 'duration': 360, 'carrier': 'SN'
                  }
              ],
              'ret_segments': [
                  {
                      'cabin_grade': 'Y', 'cabin': 'I', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '',
                      'dep_time': '10:00:00', 'arr_time': '18:00:00', 'flight_number': 'SN540',
                      'routing_number': 4, 'dep_airport': 'DMM', 'arr_airport': 'ISB', 'duration': 360, 'carrier': 'SN'
                  },
                  {
                      'cabin_grade': 'Y', 'cabin': 'G', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '',
                      'dep_time': '+1|00:30:00', 'arr_time': '+1|11:00:00', 'flight_number': 'TG673',
                      'routing_number': 5, 'dep_airport': 'ISB', 'arr_airport': 'PVG', 'duration': 660, 'carrier': 'TG'
                  },
                  {
                      'cabin_grade': 'Y', 'cabin': 'N', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '',
                      'dep_time': '+1|14:00:00', 'arr_time': '+1|20:00:00', 'flight_number': 'PG666',
                      'routing_number': 6, 'dep_airport': 'PVG', 'arr_airport': 'JMU', 'duration': 445, 'carrier': 'PG'
                  }
              ]}
         ]
         },

        {'from_airport': 'DBC', 'to_airport': 'YEA', 'trip_type': 'OW', 'routing_range': 'I2O', 'action': [],
         'pax_limit': {'card_no_prefix': 'DDD'},
         'assoc_search_routings': [
             {'adult_price': 65300.0, 'adult_tax': 2759.0, 'child_price': 65300.0, 'child_tax': 2759.0,
              'from_segments': [
                  {
                      'cabin_grade': 'Y', 'cabin': 'N', 'cabin_count': 9, 'stop_airports': 'FOC', 'stop_cities': '',
                      'dep_time': '10:00:00', 'arr_time': '18:00:00', 'flight_number': 'PG866',
                      'routing_number': 1, 'dep_airport': 'DBC', 'arr_airport': 'BKK', 'duration': 445, 'carrier': 'PG'
                  },
                  {
                      'cabin_grade': 'Y', 'cabin': 'G', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '',
                      'dep_time': '+1|00:30:00', 'arr_time': '+1|11:00:00', 'flight_number': 'TG973',
                      'routing_number': 2, 'dep_airport': 'BKK', 'arr_airport': 'BRU', 'duration': 660, 'carrier': 'TG'
                  },
                  {
                      'cabin_grade': 'Y', 'cabin': 'I', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '',
                      'dep_time': '+1|14:00:00', 'arr_time': '+1|20:00:00', 'flight_number': 'SN440',
                      'routing_number': 3, 'dep_airport': 'BRU', 'arr_airport': 'YEA', 'duration': 360, 'carrier': 'SN'
                  }
              ],
              'ret_segments': [

              ]}
         ]
         },

        {'from_airport': 'NBS', 'to_airport': 'GVA', 'trip_type': 'OW', 'routing_range': 'I2O', 'action': [],
         'pax_limit': {'card_no_prefix': 'DDD'},
         'assoc_search_routings': [
             {'adult_price': 65800.0, 'adult_tax': 2852.0, 'child_price': 65800.0, 'child_tax': 2852.0,
              'from_segments': [
                  {
                      'cabin_grade': 'Y', 'cabin': 'N', 'cabin_count': 9, 'stop_airports': 'FOC', 'stop_cities': '',
                      'dep_time': '10:00:00', 'arr_time': '18:00:00', 'flight_number': 'PG866',
                      'routing_number': 1, 'dep_airport': 'NBS', 'arr_airport': 'BKK', 'duration': 445, 'carrier': 'PG'
                  },
                  {
                      'cabin_grade': 'Y', 'cabin': 'G', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '',
                      'dep_time': '+1|00:30:00', 'arr_time': '+1|11:00:00', 'flight_number': 'TG973',
                      'routing_number': 2, 'dep_airport': 'BKK', 'arr_airport': 'BRU', 'duration': 660, 'carrier': 'TG'
                  },
                  {
                      'cabin_grade': 'Y', 'cabin': 'I', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '',
                      'dep_time': '+1|14:00:00', 'arr_time': '+1|20:00:00', 'flight_number': 'SN440',
                      'routing_number': 3, 'dep_airport': 'BRU', 'arr_airport': 'GVA', 'duration': 360, 'carrier': 'SN'
                  }
              ],
              'ret_segments': [

              ]}
         ]
         },

        {'from_airport': 'AAT', 'to_airport': 'MAD', 'trip_type': 'OW', 'routing_range': 'I2O', 'action': [],
         'pax_limit': {'card_no_prefix': 'DDD'},
         'assoc_search_routings': [
             {'adult_price': 165800.0, 'adult_tax': 12852.0, 'child_price': 165800.0, 'child_tax': 12852.0,
              'from_segments': [
                  {
                      'cabin_grade': 'Y', 'cabin': 'N', 'cabin_count': 9, 'stop_airports': 'FOC', 'stop_cities': '',
                      'dep_time': '10:00:00', 'arr_time': '18:00:00', 'flight_number': 'PG866',
                      'routing_number': 1, 'dep_airport': 'AAT', 'arr_airport': 'BKK', 'duration': 445, 'carrier': 'PG'
                  },
                  {
                      'cabin_grade': 'Y', 'cabin': 'G', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '',
                      'dep_time': '+1|00:30:00', 'arr_time': '+1|11:00:00', 'flight_number': 'TG973',
                      'routing_number': 2, 'dep_airport': 'BKK', 'arr_airport': 'BRU', 'duration': 660, 'carrier': 'TG'
                  },
                  {
                      'cabin_grade': 'Y', 'cabin': 'I', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '',
                      'dep_time': '+1|14:00:00', 'arr_time': '+1|20:00:00', 'flight_number': 'SN440',
                      'routing_number': 3, 'dep_airport': 'BRU', 'arr_airport': 'MAD', 'duration': 360, 'carrier': 'SN'
                  }
              ],
              'ret_segments': [

              ]}
         ]
         },

        # {'from_airport': 'FMA', 'to_airport': 'HRB', 'trip_type': 'OW', 'routing_range': 'OUT', 'action': [],
        #  'pax_limit': {'card_no_prefix': 'DDD'},
        #  'assoc_search_routings': [
        #      {'adult_price': 58000.0, 'adult_tax': 2754.0, 'child_price': 58000.0, 'child_tax': 2754.0,
        #       'from_segments': [
        #           {
        #               'cabin_grade': 'Y', 'cabin': 'Q', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '',
        #               'dep_time': '14:00:00', 'arr_time': '20:00:00', 'flight_number': 'SN9987',
        #               'routing_number': 1, 'dep_airport': 'FMA', 'arr_airport': 'BRU', 'duration': 360, 'carrier': 'SN'
        #           },
        #           {
        #               'cabin_grade': 'Y', 'cabin': 'H', 'cabin_count': 9, 'stop_airports': '', 'stop_cities': '',
        #               'dep_time': '+1|08:00:00', 'arr_time': '+1|22:00:00', 'flight_number': 'PG730',
        #               'routing_number': 2, 'dep_airport': 'BRU', 'arr_airport': 'HRB', 'duration': 840, 'carrier': 'PG'
        #           }
        #
        #       ],
        #       'ret_segments': []}
        #  ]
        #  }

    ]

    def __init__(self):
        super(PdcFaker, self).__init__()

    def is_exist_flight(self,search_info):
        """
        判断是否具有该航线，用于接口关闭模式的时候露出用于测试（刷验价）
        :param search_info:
        :return:
        """
        Logger().debug('is_exist_flight....wait')
        selected_pdc_data = [routing for routing in self.PDC_CONFIG if routing['from_airport'] == search_info.from_airport and routing['to_airport'] == search_info.to_airport and routing['trip_type'] == search_info.trip_type]
        if selected_pdc_data:
            return True
        else:
            return False
    def _login(self, http_session, ffp_account_info):
        """
        登陆模块
        :return: 登陆成功的httpResult 对象
        """

        gevent.sleep(3)
        return http_session

    def _check_login(self, http_session):
        """
        登录失败
        $.fullLoginCheck({"ipPosition":"SHA","loginModel":"1","message":"false","mobileNo":"","tier":"","time":"2018/07/02 18:01:47","username":"","uuid":"6ae602c3dfb8405d85b0e181b5c93e8b"})
        登陆成功
        $.fullLoginCheck({"ipPosition":"SHA","loginModel":"1","message":"true","mobileNo":"18797240897","tier":"STD","time":"2018/07/02 18:01:30","username":"林雪飞","uuid":"47884c479d7c427986c4ae07f4cbfe64"})
        :return:
        """
        gevent.sleep(3)
        return True

    def _register(self, http_session, pax_info, ffp_account_info):
        """
        注册模块
        :param pax_info:
        :return: ffp account info


        u'\u5165\u4f1a\u6e20\u9053\u53f7\u4e3a\u7a7a' 曾经报错：入会渠道号为空
        """
        Logger().info('registering wait.....')
        gevent.sleep(2)
        ffp_account_info.username = str(Random.gen_num(8))
        ffp_account_info.password = str(Random.gen_num(8))
        ffp_account_info.provider = self.provider
        ffp_account_info.reg_passport = Random.gen_passport()
        ffp_account_info.reg_birthdate = pax_info.birthdate
        ffp_account_info.reg_gender = pax_info.gender
        ffp_account_info.reg_card_type = 'PP'
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

        Logger().info('ordering.....wait')
        gevent.sleep(1)
        order_id = Random.gen_num(8)
        order_info.provider_order_id = str(order_id)
        order_info.provider_order_status = 'BOOK_SUCCESS_AND_WAITING_PAY'
        Logger().info('orderNo %s' % order_id)
        TBG.redis_conn.insert_value('%s_%s' % (self.provider_channel, order_info.provider_order_id), order_info.provider_order_status)
        return order_info


    def _pre_order_check(self, http_session, order_info):
        """
        :return:
        """
        selected_pdc_data = [routing for routing in self.PDC_CONFIG if routing['from_airport'] == order_info.from_airport and routing['to_airport'] == order_info.to_airport and routing['trip_type'] == order_info.trip_type ]
        if selected_pdc_data:
            pdc_data = selected_pdc_data[0]
            if pdc_data['pax_limit']['card_no_prefix'] in order_info.passengers[0].used_card_no:
                return "CHECK_SUCCESS"
        return "PAXINFO_INVALID"

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
        Logger().info('order status checking ')
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

    def _flight_search(self, http_session, search_info):
        """
        航班爬取模块，
        TODO :目前只考虑单程

        :return:
        """

        Logger().info('flight_searching....wait')

        selected_pdc_data = [routing for routing in self.PDC_CONFIG if routing['from_airport'] == search_info.from_airport and routing['to_airport'] == search_info.to_airport and routing['trip_type'] == search_info.trip_type]
        if selected_pdc_data:
            pdc_data = selected_pdc_data[0]
            print pdc_data
            for pdc_routing in pdc_data['assoc_search_routings']:
                flight_routing = FlightRoutingInfo()
                # flight_routing.routing_key = '32819d9afjdiasoji12'  # 此处需要进行hash
                # 成人价格+税
                flight_routing.adult_price_discount = 100
                flight_routing.adult_price_full_price = pdc_routing['adult_price']

                fix_adult_price = pdc_routing['adult_price']
                fix_child_price = pdc_routing['child_price']
                flight_routing.adult_price = fix_adult_price
                flight_routing.adult_tax = pdc_routing['adult_tax']
                flight_routing.child_price = fix_child_price
                flight_routing.child_tax = pdc_routing['child_tax']
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
                                               product='HYJ',
                                               adult_price=fix_adult_price,
                                               adult_tax=pdc_routing['adult_tax'],
                                               provider_channel=self.provider_channel,
                                               child_price=fix_child_price,
                                               child_tax=pdc_routing['child_tax'],
                                               inf_price=fix_child_price, inf_tax=pdc_routing['child_tax'],
                                               provider=self.provider,
                                               search_from_airport=search_info.from_airport,
                                               search_to_airport=search_info.to_airport,
                                               from_date=search_info.from_date,
                                               ret_date=search_info.ret_date,
                                               trip_type=search_info.trip_type,
                                               routing_range=search_info.routing_range,
                                               is_multi_segments=1 if len(pdc_routing['from_segments']) > 1 else 0
                                               )

                flight_routing.routing_key_detail = rk_info['plain']
                flight_routing.routing_key = rk_info['encrypted']

                routing_number = 1
                for pdc_segment in pdc_routing['from_segments']:
                    __ = pdc_segment['dep_time'].split('|')
                    if len(__) ==2:
                        dep_delta_day = int(__[0].split('+')[1])
                        dep_time_raw = __[1]
                    else:
                        dep_time_raw = __[0]
                        dep_delta_day = 0

                    __ = pdc_segment['arr_time'].split('|')
                    if len(__) ==2:
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
                    flight_segment.cabin_count = pdc_segment['cabin_count']
                    flight_segment.flight_number = pdc_segment['flight_number']
                    flight_segment.dep_terminal = 'T1'
                    flight_segment.arr_terminal = 'T2'
                    flight_segment.cabin_grade = pdc_segment['cabin_grade']
                    flight_segment.duration = pdc_segment['duration']
                    flight_segment.routing_number = routing_number
                    flight_segment.stop_cities = pdc_segment['stop_cities']
                    flight_segment.stop_airports = pdc_segment['stop_airports']
                    routing_number += 1
                    flight_routing.from_segments.append(flight_segment)

                if not search_info.trip_type == 'RT':
                    pdc_routing['ret_segments'] = []
                for pdc_segment in pdc_routing['ret_segments']:
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
                    flight_segment.cabin_count = pdc_segment['cabin_count']
                    flight_segment.flight_number = pdc_segment['flight_number']
                    flight_segment.dep_terminal = 'T1'
                    flight_segment.arr_terminal = 'T2'
                    flight_segment.cabin_grade = pdc_segment['cabin_grade']
                    flight_segment.duration = pdc_segment['duration']
                    flight_segment.routing_number = routing_number
                    flight_segment.stop_cities = pdc_segment['stop_cities']
                    flight_segment.stop_airports = pdc_segment['stop_airports']
                    routing_number += 1
                    flight_routing.ret_segments.append(flight_segment)

                search_info.assoc_search_routings.append(flight_routing)

        else:
            return search_info
        Logger().debug('fake provider assoc_search_routings %s' % search_info.assoc_search_routings)

        return search_info

    def _pay(self, order_info, pay_source_info, http_session):
        """
        支付
        :param http_session:
        :return:
        """
        provider_order_id = order_info.provider_order_id
        Logger().info('provider_order_id %s' % provider_order_id)
        Logger().info('paying ..... waiting')
        TBG.redis_conn.insert_value('%s_%s' % (self.provider_channel, provider_order_id), 'ISSUE_SUCCESS')

        gevent.sleep(5)
        return True