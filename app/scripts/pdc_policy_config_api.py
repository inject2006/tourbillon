#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, too-many-arguments, broad-except, anomalous-backslash-in-string
# pylint: disable=missing-docstring, line-too-long, too-few-public-methods
"""
# @Author  : wxt
# @Software: PyCharm
"""

import requests

# {"priority": 2, "price_calc": -77, "rule": "fakeprovider_test15","title":"我是测试运价"}

# j = {"is_force_hold_seat": 1, "order_provider_channels": ["ceair_web_2", "tc_provider_agent"], "freq_info": {"search": "3000,-1,-1,-1,-1"}, "ota_fare_search_timeout": 20,
#      "search_interface_status": "turn_on", "open_hours": [[6, 21]], "switch_mode": "manual", "is_allow_operation_carrier": 0, "min_cabin_count_limit": {"fakeprovider_web": 1},
#      "is_include_nonworking_day": 0, "max_pax_count_limit": {"fakeprovider_web": 4}, "is_allow_child": 0, "cabin_grade": ["Y", "F", "C", "S"], "trip_type": ["OW"], "carrier_filter": [],
#      "within_days": [3, 0], "route_strategy": [{"provider_channels": [{"filter": [], "expired_mode": "FARE", "cache_mode": "MIX", "provider_channel": "ceair_web_2"}],
#                                                 "stop_flag": {"filtered": "true", "noflight": "true", "error": "false"}}], "verify_stop_loss": -200, "routing_range": ["O2I", "O2O", "I2O", "I2I"],
#      "from_to_routings": [], "fare_strategy": [{"priority": 2, "price_calc": "x-66", "rule": "fakeprovider_web","title":"xx"}]}
#
# j = {"verify_stop_profit":23,"fare_linkage":{"enable":1,"bidding_diff_price":-2,"ttl":300},"pdc_faker_always_online":1, "ota_carrier_filter":['MU'],"is_only_return_vaild_cabin_routing":1,"is_ba_virtual_cabin_mapping":1,"is_nba_virtual_cabin_mapping":1,"is_force_hold_seat": 0,'is_simulate_booking_test': 0,
#      "order_provider_channels": [{"provider_channel":"fakeprovider_web","filter":[]},{"provider_channel":"fakeprovider_test17","filter":[]}], "freq_info": {"search": "3000,-1,-1,-1,-1"}, "ota_fare_search_timeout": 20,
#      "search_interface_status": "turn_on", "open_hours": [[6, 21]], "switch_mode": "manual", "is_allow_operation_carrier": 0, "min_cabin_count_limit": {"fakeprovider_web": 1},
#      "is_include_nonworking_day": 0, "max_pax_count_limit": {"fakeprovider_web": 10}, "is_allow_child": 0, "cabin_grade": ["Y", "F", "C", "S"], "trip_type": ["OW","RT"], "carrier_filter": ['MU'],
#      "within_days": [0, 0], "route_strategy": [{"provider_channels": [{"filter": [], "expired_mode": "FARE", "cache_mode": "MIX", "provider_channel": "fakeprovider_web"}],
#                                                 "stop_flag": {"filtered": "true", "noflight": "true", "error": "false"}}], "verify_stop_loss": -300, "routing_range": ["O2I", "O2O", "I2O", "I2I"],
#      "from_to_routings": [], "fare_strategy": [{"priority": 2, "price_calc": "x-66", "rule": "fakeprovider_web","title":"xx"}]}
#
# jj = {'operation_config': j, 'ota_name': 'tc_policy_nb'}
#
# header = {'Zeus-Token': 'eyJhbGciOiJIUzI1NiIsImV4cCI6MTU3NTY5NjM4NywiaWF0IjoxNTQ0MTYwMzg3fQ.eyJ1c2VyX2lkIjoiYWRtaW4ifQ.mnDt6l7g78K9VFJbGyK1oHYFuOQCpIM_wXOqvz2nDNU'}
# req = requests.post(url='http://127.0.0.1:9801/misc/ota_config/', json=jj, headers=header)
# print req.content
#

j = [

        {'policy_name': 'xxxxxxxxxxxxxxxxxxxxxxxx', 'from_airport': 'SHA', 'to_airport': 'BKK', 'routing_range': 'I2O', 'action': [],
         'assoc_search_routings': [
             {'fare': {'2019-05-11': {'adult_price': 66.0,'adult_price_calc':'x', 'adult_tax': 66.0, 'child_price': 135000.0,'child_price_calc':'x', 'child_tax': 5754.0, 'cabin_count': 8},
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

jj = {'pdc_policy_config': j,}

header = {'Zeus-Token': 'eyJhbGciOiJIUzI1NiIsImV4cCI6MTU3NTY5NjM4NywiaWF0IjoxNTQ0MTYwMzg3fQ.eyJ1c2VyX2lkIjoiYWRtaW4ifQ.mnDt6l7g78K9VFJbGyK1oHYFuOQCpIM_wXOqvz2nDNU'}
req = requests.post(url='http://127.0.0.1:9801/misc/pdc_policy_config/', json=jj, headers=header)
#
req = requests.get(url='http://127.0.0.1:9801/misc/pdc_policy_config/', json=jj, headers=header)
# # req = requests.get(url='http://127.0.0.1:9801/misc/ota_config/fakeota', json=jj, headers=header)
print req.content


if __name__ == '__main__':
    pass
