#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, too-many-arguments, broad-except, anomalous-backslash-in-string
# pylint: disable=missing-docstring, line-too-long, too-few-public-methods
"""
# @Author  : wxt
# @Software: PyCharm

同程政策拉取订单模式
万途公司定制
"""

import datetime
import base64
from ..controller.http_request import HttpRequest
from ..utils.exception import *
from ..utils.logger import Logger
from ..utils.util import md5_hash,simple_encrypt,RoutingKey
from .base import OTABase
from ..dao.models import *
from ..dao.internal import *



class OrderPollFaker(OTABase):

    verify_search_timeout = 30
    order_search_timeout = 30
    ticket_process_mode = 'push'  # 票号处理模式-主动推送
    order_process_mode = 'polling'  # 订单同步模式-轮询拉取模式

    ota_name = 'order_poll_faker'  # OTA名称，保证唯一，必须赋值
    ota_env = 'PROD'  # 生产OR测试接口 TODO 暂时无作用
    ota_token = 'iwj69etrnbq1lzcx'  # ota 访问验证token
    cn_ota_name = '测试政策拉单'
    tc_username = 'hzwantu'
    tc_password = 'hzwantu@tcjp'


    order_list_by_poll_url = 'http://tcflightopenapi.17usoft.com/tc/getorderlist.ashx'  # 生产
    order_list_by_poll_url = 'http://127.0.0.1:8899/tc/getorderlist.ashx' # 测试

    order_detail_by_poll_url = 'http://tcflightopenapi.17usoft.com/tc/getorderdetail.ashx'  # 生产
    order_detail_by_poll_url = 'http://127.0.0.1:8899/tc/getorderdetail.ashx' # 测试

    set_order_issued_url = 'http://tcflightopenapi.17usoft.com/tc/ticketnotify.ashx'  # 生产
    set_order_issued_url = 'http://127.0.0.1:8899/tc/ticketnotify.ashx' # 测试


    def __init__(self):
        super(OrderPollFaker, self).__init__()

    def pwd_encrypt(self):
        """
        密码加密模块
        :param pwd:
        :return:
        """
        return md5_hash(self.tc_username+'#'+self.tc_password).lower()

    def _set_order_issued(self, order_info):
        """
        {
            "OrderSerialid":"FP54193AC23A83801392",
            "IsTicketSuccess":"T",
            "Remark":"机建费应该是 100",
            "DifferencePrice":123.45,
            "ticketInfo":[
                {
                    "PassengerName":"杨进龙",
                    "Pnr":"N45PDL",
                    "TicketNo":"2302569874563",
                }
            ],

            "Username":"517na",
            "Password":"8139cfb7818d54b957f768b0a62ddf9d"
        }
        :param order_info:
        :return:
        """
        http_session = HttpRequest()
        pax_infos = []
        # TODO 目前没有加入返程和缺口程
        for pax_info in order_info.passengers:
            pax_infos.append({
                'PassengerName': pax_info.name,
                'Pnr':pax_info.pnr,
                'TicketNo': pax_info.ticket_no,
            })
        data = {
            'Username': self.tc_username,
            'Password': self.pwd_encrypt(),
            'OrderSerialid': order_info.assoc_order_id,
            'ticketInfo': pax_infos,
            'IsTicketSuccess':'T'
        }
        Logger().info('tc_policy_set_issued_request %s'% data)

        result = http_session.request(method='POST', url=self.set_order_issued_url, json=data, verify=False,
                                      is_direct=True).to_json()
        Logger().info('tc_policy_set_issued_response %s' % result)
        if result['ErrorCode'] == '100000':
            return True
        elif result['ErrorCode'] == '100010':
            Logger().info('HASTICKETED')
            return True
        else:
            raise SetOrderIssuedException(result)

    def _order_by_poll(self):
        """
        订单轮询接口
        {
            "OrderList": [
                {
                "OrderInfo": {
                            "BaseInfo":
                                {
                                    "OrderStatus": "N",
                                    "FlightWay": "S", # ￼S: 单程 D: 往返
                                    "OrderDesc": "重庆—三亚",
                                    "OrderCreateTime": "2015-12-01 00:00:00",
                                     "OrderStatusDes": "待付款"
                                },
                            "OrderSerialid": "FP54193AC23A83801392",
                            "UrgeCount": 1,
                            "OpenId": null,
                            "CustomerPay": null,
                            "IsBackfillAgain": 0
                            },
                "FlightInfoList": [
                        {
                        "Sequence": 1,
                        "FlightNo": "PN6211",
                        "Class": "Y",
                        "SubClass": "U",
                        "Dport": "CKG",
                        "Aport": "SYX",
                        "TakeOffTime": "2015-12-01 10:00:00", "PNR": "HF45BS"
                        }
                    ]
                },
            ],
            "ErrorCode": "100000",
             "ErrorMsg": "SUCCESS"
         }

        详情回参
        {
            "OrderSerialid":"FP54193AC23A83801392",
            "BaseInfo":{
                "OrderStatus":"N",
                "FlightWay":"S",
                "OrderDesc":"重庆—三亚",
                "OrderCreateTime":"2015/12/04 00:00:00",
                "PNR":"KHL234",
                "BigPNR":"NKL234",
                "CPNR":"",
                "CBigPNR":"",
                "AllPrice":1050,
                "AllFacePrice":480,
                "AllSalePrice":462.72,
                "AllTaxPrice":100
            },
            "FlightList":[
                {
                    "Sequence":1,
                    "FlightNo":"PN6211",
                    "Class":"Y",
                    "SubClass":"U",
                    "Dport":"SYX",
                    "Aport":"CKG",
                    "TakeOffTime":"2015/12/8 10:05:00",
                    "ArrivalTime":"2015/12/8 12:30:00"
                }
            ],
            "PassengerList":[
                {
                    "PassengerName":"杨进龙",
                    "SubPNR":"NTXREA",
                    "SubBigPNR":"NKL234",
                    "PassengerType":"1",
                    "CertType":"0", # 0:身份证 1:护照 2:军官证 3:回乡证 5:台胞证 9:其 他
                    "CertNO":"320981198812292976",
                    "FacePrice":480,
                    "SalePrice":462.72,
                    "AirPortBuildFee":50,
                    "OileFee":110,
                    "EticketNo":"",
                    "TCabinCode":"U",
                    "Birthday":"1980-01-01"
                }
            ],
            "PolicyInfo":{
                "PolicyId":"",
                "PolicyType":"1",
                "Benefit":"0.0360",
                "PolicyRemark":"政策备注"
            },
            "ContractInfo":{
                "ContractName":"杨进龙",
                "LinkMobiel":"13913541307"
            },
            "ErrorCode":"100000",
            "ErrorMsg":"SUCCESS"
        }
        """
        # http_session = HttpRequest()
        #
        # data = {
        #     'Username': self.username,
        #     'Password': self.pwd_encrypt(),
        #     'OrderSerialid': 'OC4F8RWQC100UQ007004',
        # }
        # result = http_session.request(method='POST', url=self.order_detail_by_poll_url, json=data, verify=False).to_json()
        #
        # Logger().debug('resultxxxxxxxxxxxxxxxxxxxx %s'% json.dumps(result,ensure_ascii=False))

        http_session = HttpRequest()
        start_time = Time.curr_date_obj() - datetime.timedelta(hours=2)
        end_time = Time.curr_date_obj()
        data = {
            'Username': self.tc_username,
            'Password': self.pwd_encrypt(),
            'OrderStatus': 'N',
            'OrderBeginDataTime': start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'orderEndDataTime': end_time.strftime('%Y-%m-%d %H:%M:%S')
        }
        Logger().debug('_order_by_poll request %s' % data)

        ol_result = http_session.request(method='POST', url=self.order_list_by_poll_url, json=data, verify=False,
                                         is_direct=True).to_json()
        order_list = []
        Logger().info("===== poll order list result : {}".format(ol_result))
        if ol_result['ErrorCode'] == '100000':
            ota_order_id_list = []
            for order in ol_result['OrderList']:
                ota_order_id_list.append(order['OrderInfo']['OrderSerialid'])
            to_process_list = self.exists_order_filter(ota_order_id_list)
            Logger().sdebug('to_process_list %s' % to_process_list)
            # 请求成功
            processed_list = []
            for order in ol_result['OrderList']:

                # 对比订单库中是否存在此订单，如果存在代表已经拉取，不再进行拉取
                # 获取价格信息
                ota_order_id = order['OrderInfo']['OrderSerialid']

                # 该接口如果多个乘客会显示多个重复订单，所以逻辑上需要去重
                if ota_order_id in processed_list:
                    continue
                else:
                    processed_list.append(ota_order_id)

                if ota_order_id in to_process_list:
                    if not order['FlightInfoList'][0]['FlightNo'][:2] in ['DZ', 'BK','MU']: # 根据航司筛选
                        continue
                    data = {
                        'Username': self.tc_username,
                        'Password': self.pwd_encrypt(),
                        'OrderSerialid': ota_order_id,
                    }
                    result = http_session.request(method='POST', url=self.order_detail_by_poll_url, json=data,
                                                  verify=False, is_direct=True).to_json()
                    Logger().info("========== poll order detail result : {}".format(result))
                    if result['ErrorCode'] == '100000':

                        order_detail = result
                        if not order_detail['PolicyInfo']['PolicyRemark'] == 'TAGWBK': # 根据指定政策号拉取订单
                            continue
                        Logger().debug('to process detail result %s' % result)
                        oi = OrderInfo()
                        # 允许降舱
                        oi.allow_cabin_downgrade = 1

                        oi.ota_order_id = ota_order_id
                        oi.assoc_order_id = ota_order_id # 为了后续跟踪ota订单状态
                        oi.ota_create_order_time = order['OrderInfo']['BaseInfo']['OrderCreateTime']
                        trip_type = order['OrderInfo']['BaseInfo']['FlightWay']
                        if trip_type == 'S':
                            oi.trip_type = 'OW'
                        elif trip_type == 'D':
                            oi.trip_type = 'RT'
                        else:
                            raise OrderByPollException('trip_type invalid %s' %trip_type)
                        sorted_segments = sorted(order_detail['FlightList'],key=lambda x:x['Sequence'])
                        flight_number_key = "-".join([x['FlightNo'] for x in sorted_segments])
                        cabin_key = "-".join([x['SubClass'] for x in sorted_segments])
                        adt_count = len([x for x in order_detail['PassengerList'] if x['PassengerType'] == "1"])
                        chd_count = len([x for x in order_detail['PassengerList'] if x['PassengerType'] in ["2","3"]])
                        oi.from_date = datetime.datetime.strptime(sorted_segments[0]['TakeOffTime'], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
                        oi.from_airport = sorted_segments[0]['Dport']
                        oi.to_airport = sorted_segments[-1]['Aport']
                        oi.adt_count = adt_count
                        oi.chd_count = chd_count
                        oi.inf_count = 0
                        oi.ret_date = None
                        if sorted_segments:
                            oi.cabin_grade = sorted_segments[0]['Class']

                        # routing_key 拼接
                        # 单程无经停非中转 routing_key 生成代码

                        dep_time_obj = datetime.datetime.strptime(sorted_segments[0]['TakeOffTime'], '%Y-%m-%d %H:%M:%S')
                        arr_time_obj = datetime.datetime.strptime(sorted_segments[-1]['ArrivalTime'], '%Y-%m-%d %H:%M:%S')

                        adult_price = 0
                        adult_tax = 0
                        child_price = 0
                        child_tax = 0
                        oi.ota_pay_price = order_detail['BaseInfo']['AllPrice']
                        for pax in order_detail['PassengerList']:
                            pax_info = PaxInfo()
                            pax_info.passenger_id = pax['CertNO']
                            # pax_info.last_name = pax.get('PassengerName', '')
                            # pax_info.first_name = pax.get('PassengerName', '')
                            pax_info.name = pax.get('PassengerName', '')
                            pax_info.pnr = Random.gen_littlepnr()
                            if int(pax['PassengerType']) in [2,3]:
                                # 儿童
                                pax_info.age_type = 'CHD'
                                child_price = pax['SalePrice']
                                child_tax = pax['AirPortBuildFee'] + pax['OileFee']
                            elif int(pax['PassengerType']) == 1:
                                pax_info.age_type = 'ADT'
                                adult_price = pax['SalePrice']
                                adult_tax = pax['AirPortBuildFee'] + pax['OileFee']
                            else:
                                raise OrderByPollException('age_type invalid %s' % pax['PassengerType'])

                            pax_info.birthdate = pax.get('Birthday', '')

                            # 这里把除了身份证之外的证件一律作为护照处理
                            if pax['CertType'] == '0':
                                pax_info.used_card_type = 'NI'
                                pax_info.card_type = 'NI'
                            else:
                                pax_info.card_type = 'PP'
                                pax_info.used_card_type = 'PP'
                            if pax_info.card_type == 'NI':
                                pax_info.card_ni = pax['CertNO'].upper()
                                pax_info.used_card_no = pax['CertNO'].upper()
                            else:
                                pax_info.used_card_no = pax['CertNO'].upper()
                                pax_info.card_pp = pax['CertNO'].upper()

                            pax_info.attr_competion()
                            oi.passengers.append(pax_info)

                        if order['FlightInfoList'][0]['FlightNo'][:2] == 'DZ':
                            select_provider = 'donghaiair'
                            select_provider_channel = 'donghaiair_web'
                        elif order['FlightInfoList'][0]['FlightNo'][:2] == 'BK':
                            select_provider_channel = 'okair_web'
                            select_provider = 'okair'
                        elif order['FlightInfoList'][0]['FlightNo'][:2] == 'MU':
                            select_provider_channel = 'fakeprovider_web'
                            select_provider = 'fakeprovider'
                        else:
                            select_provider_channel = 'okair_web'
                            select_provider = 'okair'

                        rk_info = RoutingKey.serialize(from_airport=oi.from_airport, dep_time=dep_time_obj,
                                                       to_airport=oi.to_airport, arr_time=arr_time_obj,
                                                       flight_number=flight_number_key, cabin=cabin_key,
                                                       adult_price=adult_price, adult_tax=adult_tax,
                                                       provider_channel=select_provider_channel, child_price=child_price,
                                                       child_tax=child_tax,provider=select_provider)

                        Logger().info("========= routing key : {}".format(rk_info['plain']))
                        oi.verify_routing_key = rk_info['encrypted']

                        contact_info = ContactInfo()
                        contact_info.name = order_detail['ContractInfo']['ContractName']
                        contact_info.mobile = order_detail['ContractInfo']['LinkMobiel']
                        oi.contacts.append(contact_info)

                        # routing信息采集
                        flight_routing = FlightRoutingInfo()

                        flight_routing.adult_price_discount = 100
                        flight_routing.adult_price_full_price = 0
                        flight_routing.adult_price = adult_price
                        flight_routing.adult_price_forsale = adult_price
                        flight_routing.adult_tax = adult_tax
                        flight_routing.child_price = child_price
                        flight_routing.child_price_forsale = child_price
                        flight_routing.child_tax = child_tax
                        flight_routing.product_type = 'DEFAULT'
                        flight_routing.routing_key = rk_info['encrypted']
                        flight_routing.routing_key_detail = rk_info['plain']

                        routing_number = 1
                        for segment in sorted_segments:

                            flight_segment = FlightSegmentInfo()
                            flight_segment.carrier = order['FlightInfoList'][0]['FlightNo'][:2]
                            flight_segment.dep_airport = segment['Dport']
                            flight_segment.dep_time = segment['TakeOffTime']
                            flight_segment.arr_airport = segment['Aport']
                            flight_segment.arr_time = segment['ArrivalTime']
                            flight_segment.cabin = segment['SubClass']
                            flight_segment.cabin_count = 9
                            flight_segment.flight_number = segment['FlightNo']
                            flight_segment.cabin_grade = segment['Class']
                            flight_segment.routing_number = routing_number
                            routing_number += 1
                            flight_routing.from_segments.append(flight_segment)

                        oi.routing = flight_routing
                        order_list.append(oi)
                    else:
                        raise OrderByPollException(result)
                else:
                    Logger().debug('ota_order_id %s exists '% ota_order_id)


            Logger().info("============== filtered order list : {}".format(order_list))
            return order_list
        else:
            raise OrderByPollException(ol_result)


    def _before_order_list_interface(self, req_body):
        """

        :param req_body:
        :return:
        """
        d = json.loads(req_body)
        return {
            'start_time':d.get('startTime'),
            'end_time':d.get('endTime'),
            'order_status':d.get('orderStatus')
        }

    def _after_order_list_interface(self, order_info_list):
        """

        :param
        :return:
        """
        ret_list = []
        for order_info in order_info_list:
            from_segments = []
            segment_index = 0
            if order_info.routing:
                for flight_segment in order_info.routing.from_segments:
                    segment_index += 1
                    output_segment = {
                        "carrier": flight_segment.carrier,
                        "depAirport": flight_segment.dep_airport,
                        "depTime": flight_segment.dep_time,
                        "arrAirport": flight_segment.arr_airport,
                        "arrTime": flight_segment.arr_time,
                        "stopAirports": flight_segment.stop_airports,
                        "stopCities": flight_segment.stop_airports,
                        "cabinCode": flight_segment.cabin,
                        "flightNumber": flight_segment.flight_number,
                        "depTerminal": flight_segment.dep_terminal,
                        "arrTerminal": flight_segment.arr_terminal,
                        "cabinGrade": flight_segment.cabin_grade,
                        "segmentIndex": segment_index
                    }
                    from_segments.append(output_segment)

            price_info = []
            if order_info.routing:
                price_info.append(
                    {
                        'passengerType': 0,
                        'price': order_info.ota_adult_price,
                        'tax': order_info.routing.adult_tax
                    }
                )
            if order_info.routing and order_info.routing.child_price:
                price_info.append(
                    {
                        'passengerType': 1,
                        'price': order_info.ota_child_price,
                        'tax': order_info.routing.child_tax
                    }
                )
            paxs = []
            for pax_info in order_info.passengers:
                if pax_info.age_type == 'ADT':
                    age_type = 0
                elif pax_info.age_type == 'CHD':
                    age_type = 1
                elif pax_info.age_type == 'INF':
                    age_type = 2
                output_pax = {
                    'passengerId': pax_info.passenger_id,
                    'lastName': pax_info.last_name,
                    'firstName': pax_info.first_name,
                    'name': pax_info.name,
                    'gender': pax_info.gender,
                    'passengerType': age_type,
                    'birthday': pax_info.birthdate,
                    'cardType': pax_info.used_card_type,
                    'cardNum': pax_info.used_card_no,
                    'pnrCode': order_info.pnr_code,
                    'ticketNo': pax_info.ticket_no
                }
                paxs.append(output_pax)
            sub = {
                'orderNo': order_info.assoc_order_id,
                'flightInfos': [
                    {
                        'travelType': '1',
                        'segments': from_segments
                    }
                ],
                'passengerInfos': paxs,
                'priceInfos': price_info,
                'finalPrice': order_info.ota_pay_price,
                'tripType': '1',
                'orderStatus': PROVIDERS_STATUS[order_info.providers_status]['status_category'],  # 此处屏蔽具体的状态信息，只显示粗略流程节点。
                'OTADetailStatus':order_info.ota_order_status,
                'account': order_info.ffp_account.username if order_info.ffp_account else '',
                'payType': '网银支付',
                'providerOrderId': order_info.sub_orders[0].provider_order_id if order_info.sub_orders else '',
                'payPrice': order_info.sub_orders[0].provider_price if order_info.sub_orders else 0,
                'remarks': order_info.sub_orders[0].comment if order_info.sub_orders else '',
            }
            ret_list.append(sub)
        ret = {
            'status': 'SUCCESS',
            'msg': '成功',
            'orderList':ret_list
        }
        self.final_result = json.dumps(ret)
        return True

    def _before_order_detail_interface(self, req_body):
        """

        :param req_body:
        :return:
        """
        req_body = json.loads(req_body)
        self.order_info.assoc_order_id = req_body['orderNo']

    def _after_order_detail_interface(self, order_info):
        """

        :param
        :return:
        """
        if order_info.order_detail_status == 'INNER_ERROR_5001':
            self.final_result = json.dumps({'status':order_info.order_detail_status,'msg':ERROR_STATUS[order_info.order_detail_status]})
            return False
        else:
            from_segments = []
            segment_index = 0
            if order_info.routing:
                for flight_segment in order_info.routing.from_segments:
                    segment_index += 1
                    output_segment = {
                        "carrier": flight_segment.carrier,
                        "depAirport": flight_segment.dep_airport,
                        "depTime": flight_segment.dep_time,
                        "arrAirport": flight_segment.arr_airport,
                        "arrTime": flight_segment.arr_time,
                        "stopAirports": flight_segment.stop_airports,
                        "stopCities": flight_segment.stop_airports,
                        "cabinCode": flight_segment.cabin,
                        "flightNumber": flight_segment.flight_number,
                        "depTerminal": flight_segment.dep_terminal,
                        "arrTerminal": flight_segment.arr_terminal,
                        "cabinGrade": flight_segment.cabin_grade,
                        "segmentIndex": segment_index
                    }

                    from_segments.append(output_segment)

            price_info = []
            if order_info.routing:
                price_info.append(
                    {
                        'passengerType': 0,
                        'price': order_info.ota_adult_price,
                        'tax': order_info.routing.adult_tax
                    }
                )
            if order_info.routing and order_info.routing.child_price:
                price_info.append(
                    {
                        'passengerType': 1,
                        'price': order_info.ota_child_price,
                        'tax': order_info.routing.child_tax
                    }
                )
            paxs = []
            for pax_info in order_info.passengers:
                if pax_info.age_type == 'ADT':
                    age_type = 0
                elif pax_info.age_type == 'CHD':
                    age_type = 1
                elif pax_info.age_type == 'INF':
                    age_type = 2
                output_pax = {
                    'passengerId': pax_info.passenger_id,
                    'lastName': pax_info.last_name,
                    'firstName': pax_info.first_name,
                    'name': pax_info.name,
                    'gender': pax_info.gender,
                    'passengerType': age_type,
                    'birthday': pax_info.birthdate,
                    'cardType': pax_info.used_card_type,
                    'cardNum': pax_info.used_card_no,
                    'pnrCode': order_info.pnr_code,
                    'ticketNo': pax_info.ticket_no
                }
                paxs.append(output_pax)
            ret = {
                'status': 'SUCCESS',
                'msg': '成功',
                'orderNo': order_info.assoc_order_id,
                'flightInfos': [
                    {
                        'travelType': '1',
                        'segments': from_segments
                    }
                ],
                'passengerInfos': paxs,
                'priceInfos': price_info,
                'finalPrice': order_info.ota_pay_price,
                'tripType': '1',
                'orderStatus': PROVIDERS_STATUS[order_info.providers_status]['status_category'],  # 此处屏蔽具体的状态信息，只显示粗略流程节点。
                'OTADetailStatus':order_info.ota_order_status,
                'account': order_info.ffp_account.username if order_info.ffp_account else '',
                'payType': '网银支付',
                'providerOrderId': order_info.sub_orders[0].provider_order_id if order_info.sub_orders else '',
                'payPrice': order_info.sub_orders[0].provider_price if order_info.sub_orders else 0,
                'remarks': order_info.sub_orders[0].comment if order_info.sub_orders else '',
            }
            self.final_result = json.dumps(ret)
            return True


if __name__ == '__main__':
    pass