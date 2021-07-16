#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, too-many-arguments, broad-except, anomalous-backslash-in-string
# pylint: disable=missing-docstring, line-too-long, too-few-public-methods
"""
# @Author  : wxt
# @Software: PyCharm
"""

import redis
from itertools import izip_longest


# 生产
REDIS_HOST = '42.159.91.248'
REDIS_PORT = 26371
REDIS_PASSWORD = 'ZIDZGPZPYpd6nTk2zCwLni3K1zvd2ChPkztTcO1HsnM='
FLIGHT_FARE_CACHE_REDIS_DB = 3
COMMON_REDIS_DB = 4
CONFIG_REDIS_DB = 5


REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_PASSWORD = ''
FLIGHT_FARE_CACHE_REDIS_DB = 3
COMMON_REDIS_DB = 4
CONFIG_REDIS_DB = 5

r = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=5,password=REDIS_PASSWORD)

# # iterate a list in batches of size n
# def batcher(iterable, n):
#     args = [iter(iterable)] * n
#     return izip_longest(*args)
#
#
#
# # in batches of 500 delete keys matching user:*
# for keybatch in batcher(r.scan_iter('fare_cache_ch*'),50000):
#     print 'batch-loop'
#     print len(keybatch)
#     import time
#
#     s = time.time()
#     r.delete(*keybatch)
#     print time.time() - s

data = [

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
import json
r.set('pdc_policy',json.dumps(data))
if __name__ == '__main__':
    pass