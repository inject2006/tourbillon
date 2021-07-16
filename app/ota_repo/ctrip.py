#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, too-many-arguments, broad-except, anomalous-backslash-in-string
# pylint: disable=missing-docstring, line-too-long, too-few-public-methods
"""
# @Author  : wxt
# @Software: PyCharm
"""

import datetime
import base64
from ..controller.http_request import HttpRequest
from ..utils.exception import *
from ..utils.logger import Logger
from .base import OTABase
from ..dao.models import *
from ..dao.internal import *
from Crypto.Cipher import AES


class Ctrip(OTABase):
    """
    OTA 接口基类，
    该接口所有子类集成必须自己实现异常捕捉，如果抛出异常则OTA请求会返回500
    """

    order_to_pay_wait_time = 60 * 28  # 下单到支付最长等待时间 单位 秒
    ticket_process_mode = 'push'  # 票号处理模式-主动推送
    order_detail_process_mode = 'polling' # 订单详情同步模式-轮询拉取模式
    ota_name = 'ctrip'  # OTA名称，保证唯一，必须赋值
    ota_env = 'PROD'  # 生产OR测试接口 TODO 暂时无作用
    ota_token = '94jenqd7upk5b0va'  # ota 访问验证token
    product_type = 0  # 运价类型：0: GDS 私有运价 1:GDS 公布运价 (此场 景下字段 farebasis 不能为空) 2:航司官网产品 3:廉价航司产品 4:特价产品
    call_back_username = 'shyy123'  # 详情导出 回调票号等鉴权
    call_back_password = 'yida1680'  # 详情导出 回调票号等鉴权
    # aes_key = '1234567890123456'  # 测试环境KEY
    aes_key = 'A64K9GE72VBY8NUD'  # 生产环境KEY
    ctrip_cid = 'ota_ctrip'
    cn_ota_name = '携程OTA'
    aes_iv = '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'  # aes iv


    def __init__(self):
        super(Ctrip, self).__init__()

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

    def search_interface_error_output(self):
        """
        接口报错返回
        :return:
        """
        ret = {
            "status": 0,
            "msg": "success",
            "routings": []
        }
        return ret

    def verify_interface_error_output(self):
        """
        接口报错返回
        :return:
        """
        ret = {
            "status": 3,
            "msg": "舱位不足",
            "routings": []
        }

        return ret

    def order_interface_error_output(self):
        """
        接口报错返回
        :return:
        """
        ret = {
            "status": 3,
            "msg": "舱位不足",
            "routings": []
        }
        ret = self.aes_encrypt(json.dumps(ret))
        return ret

    def _before_search_interface(self, req_body):
        """
        询价接口 入参标准化和自定义设置
        :param req_body:
        :return: from_date, from_airport, to_airport, adt_count=1, chd_count=0, inf_count=0, ret_date='',
                         trip_type='OW', routing_range='IN'

        """
        req_body = json.loads(req_body)
        self.search_info.from_date = datetime.datetime.strptime(req_body['fromDate'], '%Y%m%d').strftime('%Y-%m-%d')
        self.search_info.from_airport = req_body['fromCity']
        self.search_info.to_airport = req_body['toCity']
        self.search_info.adt_count = int(req_body['adultNumber'])
        self.search_info.chd_count = int(req_body['childNumber'])
        self.search_info.inf_count = int(req_body['infantNumber']) if req_body.get('infantNumber') else 0
        self.search_info.cabin_grade_list = req_body.get('cabinGrade',[])
        self.search_info.ret_date = datetime.datetime.strptime(
            req_body['retDate'], '%Y%m%d').strftime('%Y-%m-%d') if req_body.get('retDate') else None
        trip_type = req_body['tripType']
        if trip_type == "1":
            trip_type = 'OW'
        elif trip_type == '2':
            trip_type = 'RT'
        self.search_info.trip_type = trip_type
        self.search_info.extra_data = req_body

    def _after_search_interface(self, search_info):
        """
        询价接口 输出格式为ota所需格式
        :return: 标准格式JSON ，格式参照 routing和 segment

        """
        if not search_info.assoc_search_routings:
            self.final_result = self.search_interface_error_output()
            return

        ret = {
            "status": 0,
            "msg": "success",
            "routings": []
        }

        for flight_routing in search_info.assoc_search_routings:
            output_routing = {
                "data": flight_routing.routing_key,
                "publishPrice": 0,
                "adultPrice": flight_routing.adult_price_forsale,
                "adultTax": flight_routing.adult_tax,
                "childPublishPrice": 0,
                "childPrice": flight_routing.child_price_forsale,
                "childTax": flight_routing.child_tax,
                "infantPublishPrice": 0,
                "infantPrice": flight_routing.inf_price,
                "infantTax": flight_routing.inf_tax,
                "adultTaxType": 0,
                "childTaxType": 0,
                "priceType": 0,
                "applyType": 0,
                # "exchange": "",
                "adultAgeRestriction": "",
                "eligibility": "NOR",
                "nationality": "",
                "forbiddenNationality": "",
                "planCategory": 0,
                "invoiceType": "E",
                "minStay": "",
                "maxStay": "",
                "minPassengerCount": 1,
                "maxPassengerCount": flight_routing.segment_min_cabin_count,
                "bookingOfficeNo": "",
                "ticketingOfficeNo": "",
                "validatingCarrier": "",
                "reservationType": "",
                "productType": "",
                "fareBasis": "",
                "airlineAncillaries": {
                    "baggageService": False,
                    "unFreeBaggage": False,
                },

                "fromSegments": [],
                "rule": {
                    "formatBaggageInfoList": [],
                    "refundInfoList": [],
                    "changesInfoList": [],
                },
                "retSegments": []
            }
            for flight_segment in flight_routing['from_segments']:
                # 航班号,如:CA1234。航班号数字不足 四位,补足四位,如 CZ0006 需返回 CZ6
                flight_suffix = str(int(flight_segment.flight_number[2:]))
                flight_number = flight_segment.flight_number[:2] + flight_suffix

                output_segment = {
                    "carrier": flight_segment.carrier,
                    "flightNumber": flight_number,
                    "depAirport": flight_segment.dep_airport,
                    "depTerminal": flight_segment.dep_terminal,
                    "depTime": datetime.datetime.strptime(flight_segment.dep_time, '%Y-%m-%d %H:%M:%S'
                                                          ).strftime('%Y%m%d%H%M'),
                    "arrAirport": flight_segment.arr_airport,
                    "arrTerminal": flight_segment.arr_terminal,
                    "arrTime": datetime.datetime.strptime(flight_segment.arr_time, '%Y-%m-%d %H:%M:%S'
                                                          ).strftime('%Y%m%d%H%M'),
                    "stopCities": flight_segment.stop_cities,
                    "stopAirports": flight_segment.stop_airports,
                    "codeShare": False,
                    "cabin": flight_segment.cabin,
                    # "cabinCount": flight_routing.segment_min_cabin_count,
                    # "aircraftCode": "777",
                    # "operatingCarrier": "",
                    # "operatingFlightNo": "",
                    "cabinGrade": flight_segment.cabin_grade,
                    "duration": flight_segment.duration
                }
                output_routing['fromSegments'].append(output_segment)
                refund_info = {
                    "refundType": 0,
                    "refundStatus": "T",
                    # "refundFee": 0,
                    # "currency": "CNY",
                    "passengerType": 0,
                    "refNoshow": "T",
                    'refNoShowCondition': 0,
                    # "refNoshowFee": 0,
                }
                output_routing['rule']['refundInfoList'].append(refund_info)
                if search_info.chd_count > 0:
                    output_routing['rule']['refundInfoList'].append({
                        "refundType": 0,
                        "refundStatus": "T",
                        # "refundFee": 0,
                        # "currency": "CNY",
                        "passengerType": 1,
                        "refNoshow": "T",
                        'refNoShowCondition': 0,
                        # "refNoshowFee": 0,
                    })
                if search_info.inf_count > 0:
                    output_routing['rule']['refundInfoList'].append({
                        "refundType": 0,
                        "refundStatus": "T",
                        # "refundFee": 0,
                        # "currency": "CNY",
                        "passengerType": 2,
                        "refNoshow": "T",
                        'refNoShowCondition': 0,
                        # "refNoshowFee": 0,
                    })
                change_info = {
                    "changesType": 0,
                    "changesStatus": "T",
                    # "changesFee": 0,
                    # "currency": "CNY",
                    "passengerType": 0,
                    "revNoshow": "T",
                    "revNoShowCondition": 0,
                    # "revNoshowFee": 0,
                }
                output_routing['rule']['changesInfoList'].append(change_info)
                if search_info.chd_count > 0:
                    output_routing['rule']['changesInfoList'].append({
                        "changesType": 0,
                        "changesStatus": "T",
                        # "changesFee": 0,
                        # "currency": "CNY",
                        "passengerType": 1,
                        "revNoshow": "T",
                        "revNoShowCondition": 0,
                        # "revNoshowFee": 0,
                    })
                if search_info.inf_count > 0:
                    output_routing['rule']['changesInfoList'].append({
                        "changesType": 0,
                        "changesStatus": "T",
                        # "changesFee": 0,
                        # "currency": "CNY",
                        "passengerType": 2,
                        "revNoshow": "T",
                        "revNoShowCondition": 0,
                        # "revNoshowFee": 0,
                    })
                baggage_info = {
                    "segmentNo": flight_segment.routing_number,
                    "passengerType": 0,
                    "baggagePiece": 0,
                    "baggageWeight": 0,
                }
                output_routing['rule']['formatBaggageInfoList'].append(baggage_info)
                if search_info.chd_count > 0:
                    output_routing['rule']['formatBaggageInfoList'].append({
                        "segmentNo": flight_segment.routing_number,
                        "passengerType": 1,
                        "baggagePiece": 0,
                        "baggageWeight": 0,
                    })
                if search_info.inf_count > 0:
                    output_routing['rule']['formatBaggageInfoList'].append({
                        "segmentNo": flight_segment.routing_number,
                        "passengerType": 2,
                        "baggagePiece": 0,
                        "baggageWeight": 0,
                    })

            for flight_segment in flight_routing['ret_segments']:
                # 航班号,如:CA1234。航班号数字不足 四位,补足四位,如 CZ0006 需返回 CZ6
                flight_suffix = str(int(flight_segment.flight_number[2:]))
                flight_number = flight_segment.flight_number[:2] + flight_suffix

                output_segment = {
                    "carrier": flight_segment.carrier,
                    "flightNumber": flight_number,
                    "depAirport": flight_segment.dep_airport,
                    "depTerminal": flight_segment.dep_terminal,
                    "depTime": datetime.datetime.strptime(flight_segment.dep_time, '%Y-%m-%d %H:%M:%S'
                                                          ).strftime('%Y%m%d%H%M'),
                    "arrAirport": flight_segment.arr_airport,
                    "arrTerminal": flight_segment.arr_terminal,
                    "arrTime": datetime.datetime.strptime(flight_segment.arr_time, '%Y-%m-%d %H:%M:%S'
                                                          ).strftime('%Y%m%d%H%M'),
                    "stopCities": flight_segment.stop_cities,
                    "stopAirports": flight_segment.stop_airports,
                    "codeShare": False,
                    "cabin": flight_segment.cabin,
                    # "cabinCount": flight_routing.segment_min_cabin_count,
                    # "aircraftCode": "777",
                    # "operatingCarrier": "",
                    # "operatingFlightNo": "",
                    "cabinGrade": flight_segment.cabin_grade,
                    "duration": flight_segment.duration
                }
                output_routing['retSegments'].append(output_segment)
                baggage_info = {
                    "segmentNo": flight_segment.routing_number,
                    "passengerType": 0,
                    "baggagePiece": 0,
                    "baggageWeight": 0,
                }
                output_routing['rule']['formatBaggageInfoList'].append(baggage_info)
                if search_info.chd_count > 0:
                    output_routing['rule']['formatBaggageInfoList'].append({
                        "segmentNo": flight_segment.routing_number,
                        "passengerType": 1,
                        "baggagePiece": 0,
                        "baggageWeight": 0,
                    })
                if search_info.inf_count > 0:
                    output_routing['rule']['formatBaggageInfoList'].append({
                        "segmentNo": flight_segment.routing_number,
                        "passengerType": 2,
                        "baggagePiece": 0,
                        "baggageWeight": 0,
                    })

            ret['routings'].append(output_routing)

        self.final_result = ret

    def _before_verify_interface(self, req_body):
        """
        验价接口，

        :param routing:  只含航班信息，不含价格信息和规则信息。
        :return:
        """

        req_body = json.loads(req_body)
        self.search_info.adt_count = req_body['adultNumber']
        self.search_info.chd_count = req_body['childNumber']
        self.search_info.inf_count = req_body['infantNumber'] if req_body.get('infantNumber') else 0
        self.search_info.extra_data = req_body
        self.search_info.verify_routing_key = req_body['routing']['data']  # 对于验价环节必须返回

    def _after_verify_interface(self, search_info):
        """
        验价接口，
        返回多增加了  "sessionId":"S12345",会话标识：标记服务接口调用的唯一标识，相应的调用结果中会原值返回。数字或字母，长度小于 50 个字符,且不能为空。
        寻找查询结果中的第一个去程航班的起飞时间、舱位信息、舱位数量、航班号是否相等确认该所属Routing

        :param result: 标准 routing+segments 格式 参考search接口
        :return: 需要返回 True or False
        """
        ret = {
            "status": 0,
            "msg": "success",
            "sessionId": self.request_id,
            "maxSeats": search_info.routing.segment_min_cabin_count,
            "routing": {},
            "rule": {
                "formatBaggageInfoList": [],
                "refundInfoList": [],
                "changesInfoList": [],
            },
        }

        output_routing = {
            "data": search_info.verify_routing_key, # 返回原来的key
            "publishPrice": 0,
            "adultPrice": search_info.routing.adult_price_forsale,
            "adultTax": search_info.routing.adult_tax,
            "childPublishPrice": 0,
            "childPrice": search_info.routing.child_price_forsale,
            "childTax": search_info.routing.child_tax,
            "infantPublishPrice": 0,
            "infantPrice": search_info.routing.inf_price,
            "infantTax": search_info.routing.inf_tax,
            "adultTaxType": 0,
            "childTaxType": 0,
            "priceType": 0,
            "applyType": 0,
            # "exchange": "",
            "adultAgeRestriction": "",
            "eligibility": "NOR",
            "nationality": "",
            "forbiddenNationality": "",
            "planCategory": 0,
            "invoiceType": "E",
            "minStay": "",
            "maxStay": "",
            "minPassengerCount": 1,
            "maxPassengerCount": search_info.routing.segment_min_cabin_count,
            "bookingOfficeNo": "",
            "ticketingOfficeNo": "",
            "validatingCarrier": "",
            "reservationType": "",
            "productType": "",
            "fareBasis": "",
            "airlineAncillaries": {
                "baggageService": False,
                "unFreeBaggage": False,
            },

            "fromSegments": [],
            "retSegments": []
        }

        for flight_segment in search_info.routing.from_segments:
            # 航班号,如:CA1234。航班号数字不足 四位,补足四位,如 CZ6 需返回 CZ0006
            flight_suffix = str(int(flight_segment.flight_number[2:]))
            flight_number = flight_segment.flight_number[:2] + flight_suffix

            output_segment = {
                "carrier": flight_segment.carrier,
                "depAirport": flight_segment.dep_airport,
                "depTime": datetime.datetime.strptime(flight_segment.dep_time, '%Y-%m-%d %H:%M:%S'
                                                      ).strftime('%Y%m%d%H%M'),
                "arrAirport": flight_segment.arr_airport,
                "arrTime": datetime.datetime.strptime(flight_segment.arr_time, '%Y-%m-%d %H:%M:%S'
                                                      ).strftime('%Y%m%d%H%M'),
                "stopAirports": flight_segment.stop_airports,
                "codeShare": False,
                "cabin": flight_segment.cabin,
                "flightNumber": flight_number,
                "depTerminal": flight_segment.dep_terminal,
                "arrTerminal": flight_segment.arr_terminal,
                "cabinGrade": flight_segment.cabin_grade,
                "duration": flight_segment.duration
            }
            output_routing['fromSegments'].append(output_segment)

            refund_info = {
                "refundType": 0,
                "refundStatus": "T",
                # "refundFee": 0,
                # "currency": "CNY",
                "passengerType": 0,
                "refNoshow": "T",
                'refNoShowCondition': 0,
                # "refNoshowFee": 0,
            }
            ret['rule']['refundInfoList'].append(refund_info)
            if search_info.chd_count > 0:
                ret['rule']['refundInfoList'].append({
                    "refundType": 0,
                    "refundStatus": "T",
                    # "refundFee": 0,
                    # "currency": "CNY",
                    "passengerType": 1,
                    "refNoshow": "T",
                    'refNoShowCondition': 0,
                    # "refNoshowFee": 0,
                })
            if search_info.inf_count > 0:
                ret['rule']['refundInfoList'].append({
                    "refundType": 0,
                    "refundStatus": "T",
                    # "refundFee": 0,
                    # "currency": "CNY",
                    "passengerType": 2,
                    "refNoshow": "T",
                    'refNoShowCondition': 0,
                    # "refNoshowFee": 0,
                })
            change_info = {
                "changesType": 0,
                "changesStatus": "T",
                # "changesFee": 0,
                # "currency": "CNY",
                "passengerType": 0,
                "revNoshow": "T",
                "revNoShowCondition": 0,
                # "revNoshowFee": 0,
            }
            ret['rule']['changesInfoList'].append(change_info)
            if search_info.chd_count > 0:
                ret['rule']['changesInfoList'].append({
                    "changesType": 0,
                    "changesStatus": "T",
                    # "changesFee": 0,
                    # "currency": "CNY",
                    "passengerType": 1,
                    "revNoshow": "T",
                    "revNoShowCondition": 0,
                    # "revNoshowFee": 0,
                })
            if search_info.inf_count > 0:
                ret['rule']['changesInfoList'].append({
                    "changesType": 0,
                    "changesStatus": "T",
                    # "changesFee": 0,
                    # "currency": "CNY",
                    "passengerType": 2,
                    "revNoshow": "T",
                    "revNoShowCondition": 0,
                    # "revNoshowFee": 0,
                })
            baggage_info = {
                "segmentNo": flight_segment.routing_number,
                "passengerType": 0,
                "baggagePiece": 0,
                "baggageWeight": 0,
            }
            ret['rule']['formatBaggageInfoList'].append(baggage_info)
            if search_info.chd_count > 0:
                ret['rule']['formatBaggageInfoList'].append({
                    "segmentNo": flight_segment.routing_number,
                    "passengerType": 1,
                    "baggagePiece": 0,
                    "baggageWeight": 0,
                })
            if search_info.inf_count > 0:
                ret['rule']['formatBaggageInfoList'].append({
                    "segmentNo": flight_segment.routing_number,
                    "passengerType": 2,
                    "baggagePiece": 0,
                    "baggageWeight": 0,
                })

        for flight_segment in search_info.routing.ret_segments:
            # 航班号,如:CA1234。航班号数字不足 四位,补足四位,如 CZ6 需返回 CZ0006
            flight_suffix = str(int(flight_segment.flight_number[2:]))
            flight_number = flight_segment.flight_number[:2] + flight_suffix

            output_segment = {
                "carrier": flight_segment.carrier,
                "depAirport": flight_segment.dep_airport,
                "depTime": datetime.datetime.strptime(flight_segment.dep_time, '%Y-%m-%d %H:%M:%S'
                                                      ).strftime('%Y%m%d%H%M'),
                "arrAirport": flight_segment.arr_airport,
                "arrTime": datetime.datetime.strptime(flight_segment.arr_time, '%Y-%m-%d %H:%M:%S'
                                                      ).strftime('%Y%m%d%H%M'),
                "stopAirports": flight_segment.stop_airports,
                "codeShare": False,
                "cabin": flight_segment.cabin,
                "flightNumber": flight_number,
                "depTerminal": flight_segment.dep_terminal,
                "arrTerminal": flight_segment.arr_terminal,
                "cabinGrade": flight_segment.cabin_grade,
                "duration": flight_segment.duration
            }
            output_routing['retSegments'].append(output_segment)

            baggage_info = {
                "segmentNo": flight_segment.routing_number,
                "passengerType": 0,
                "baggagePiece": 0,
                "baggageWeight": 0,
            }
            ret['rule']['formatBaggageInfoList'].append(baggage_info)
            if search_info.chd_count > 0:
                ret['rule']['formatBaggageInfoList'].append({
                    "segmentNo": flight_segment.routing_number,
                    "passengerType": 1,
                    "baggagePiece": 0,
                    "baggageWeight": 0,
                })
            if search_info.inf_count > 0:
                ret['rule']['formatBaggageInfoList'].append({
                    "segmentNo": flight_segment.routing_number,
                    "passengerType": 2,
                    "baggagePiece": 0,
                    "baggageWeight": 0,
                })

        ret['routing'] = output_routing
        self.final_result = ret
        return True

    def _before_order_interface(self, req_body):
        """
        生单接口
        :return:
        """
        req_body = self.aes_decrypt(req_body)
        req_body = json.loads(req_body)
        Logger().debug('aes_decrypt data %s' % req_body)
        self.order_info.session_id = req_body['sessionId']
        self.order_info.extra_data = req_body
        self.order_info.verify_routing_key = req_body['routing']['data']
        self.order_info.is_test_order = req_body.get('is_test_order', 0)  # 是否为测试订单
        for pax in req_body['passengers']:
            pax_info = PaxInfo()
            # pax_info.passenger_id = pax['passengerID']
            pax_info.last_name = pax['name'].split('/')[0]
            pax_info.first_name = pax['name'].split('/')[-1]
            if int(pax['ageType']) == 1:
                # 儿童
                pax_info.age_type = 'CHD'
                self.order_info.chd_count += 1
            elif int(pax['ageType']) == 0:
                pax_info.age_type = 'ADT'
                self.order_info.adt_count += 1
            else:
                pax_info.age_type = 'ADT'
            pax_info.birthdate = datetime.datetime.strptime(pax['birthday'], '%Y%m%d').strftime('%Y-%m-%d')  # 生单接口跟详情导出的格式不一致
            pax_info.gender = pax['gender']

            # 这里把除了身份证之外的证件一律作为护照处理
            pax_info.used_card_type = pax['cardType'].upper()
            pax_info.card_type = pax['cardType'].upper()
            if pax_info.used_card_type == 'NI':
                pax_info.card_ni = pax['cardNum'].upper()
                pax_info.used_card_no = pax['cardNum'].upper()
            else:
                pax_info.used_card_no = pax['cardNum'].upper()
                pax_info.used_card_type = 'PP'
                pax_info.card_pp = pax['cardNum'].upper()

            pax_info.card_expired = datetime.datetime.strptime(pax['cardExpired'], '%Y%m%d').strftime('%Y-%m-%d')
            pax_info.card_issue_place = pax['cardIssuePlace']
            pax_info.nationality = pax['nationality']
            pax_info.attr_competion()
            self.order_info.passengers.append(pax_info)

        contact = req_body['contact']
        contact_info = ContactInfo()
        contact_info.address = contact['address']
        contact_info.postcode = contact['postcode']
        contact_info.email = contact['email']
        contact_info.mobile = contact['mobile']
        contact_info.name = contact['name']
        self.order_info.contacts.append(contact_info)

    def _after_order_interface(self, order_info):
        """

        :param result:
        :return:
        """
        # 无论订票成功和失败都会返回成功，之后转人工
        # Logger().info('fdafdafda order_info %s'% order_info)
        ret = {
            "status": 0,
            "msg": "success",
            "sessionId": self.order_info.session_id,
            "orderNo": self.order_info.assoc_order_id,
            "pnrCode": self.order_info.pnr_code,
            "maxSeats": order_info.routing.segment_min_cabin_count,
            "orderContact": {
                "email": order_info.contacts[0].email,
                "mobile": order_info.contacts[0].mobile,
            },
            "routing": {},
            # "passengerbaggages": [],
        }

        output_routing = {
            "data": order_info.verify_routing_key,
            "publishPrice": 0,
            "adultPrice": order_info.routing.adult_price_forsale,
            "adultTax": order_info.routing.adult_tax,
            "childPublishPrice": 0,
            "childPrice": order_info.routing.child_price_forsale,
            "childTax": order_info.routing.child_tax,
            "infantPublishPrice": 0,
            "infantPrice": order_info.routing.inf_price,
            "infantTax": order_info.routing.inf_tax,
            "adultTaxType": 0,
            "childTaxType": 0,
            "priceType": 0,
            "applyType": 0,
            # "exchange": "",
            "adultAgeRestriction": "",
            "eligibility": "NOR",
            "nationality": "",
            "forbiddenNationality": "",
            "planCategory": 0,
            "invoiceType": "E",
            "minStay": "",
            "maxStay": "",
            "minPassengerCount": 1,
            "maxPassengerCount": order_info.routing.segment_min_cabin_count,
            "bookingOfficeNo": "",
            "ticketingOfficeNo": "",
            "validatingCarrier": "",
            "reservationType": "",
            "productType": "",
            "fareBasis": "",
            "airlineAncillaries": {
                "baggageService": False,
                "unFreeBaggage": False,
            },
            "fromSegments": [],
            "rule": {
                "formatBaggageInfoList": [],
                "refundInfoList": [],
                "changesInfoList": [],
            },
            "retSegments": [],
        }
        for flight_segment in order_info.routing.from_segments:
            flight_suffix = str(int(flight_segment.flight_number[2:]))
            flight_number = flight_segment.flight_number[:2] + flight_suffix

            output_segment = {
                "carrier": flight_segment.carrier,
                "depAirport": flight_segment.dep_airport,
                "depTime": datetime.datetime.strptime(flight_segment.dep_time, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'),
                "arrAirport": flight_segment.arr_airport,
                "arrTime": datetime.datetime.strptime(flight_segment.arr_time, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'),
                "stopAirports": flight_segment.stop_airports,
                "codeShare": False,
                "cabin": flight_segment.cabin,
                "flightNumber": flight_number,
                "depTerminal": flight_segment.dep_terminal,
                "arrTerminal": flight_segment.arr_terminal,
                "cabinGrade": flight_segment.cabin_grade,
                "duration": flight_segment.duration
            }
            output_routing['fromSegments'].append(output_segment)

            refund_info = {
                "refundType": 0,
                "refundStatus": "T",
                # "refundFee": 0,
                # "currency": "CNY",
                "passengerType": 0,
                "refNoshow": "T",
                'refNoShowCondition': 0,
                # "refNoshowFee": 0,
            }
            output_routing['rule']['refundInfoList'].append(refund_info)
            if order_info.chd_count > 0:
                output_routing['rule']['refundInfoList'].append({
                    "refundType": 0,
                    "refundStatus": "T",
                    # "refundFee": 0,
                    # "currency": "CNY",
                    "passengerType": 1,
                    "refNoshow": "T",
                    'refNoShowCondition': 0,
                    # "refNoshowFee": 0,
                })
            if order_info.inf_count > 0:
                output_routing['rule']['refundInfoList'].append({
                    "refundType": 0,
                    "refundStatus": "T",
                    # "refundFee": 0,
                    # "currency": "CNY",
                    "passengerType": 2,
                    "refNoshow": "T",
                    'refNoShowCondition': 0,
                    # "refNoshowFee": 0,
                })
            change_info = {
                "changesType": 0,
                "changesStatus": "T",
                # "changesFee": 0,
                # "currency": "CNY",
                "passengerType": 0,
                "revNoshow": "T",
                "revNoShowCondition": 0,
                # "revNoshowFee": 0,
            }
            output_routing['rule']['changesInfoList'].append(change_info)
            if order_info.chd_count > 0:
                output_routing['rule']['changesInfoList'].append({
                    "changesType": 0,
                    "changesStatus": "T",
                    # "changesFee": 0,
                    # "currency": "CNY",
                    "passengerType": 1,
                    "revNoshow": "T",
                    "revNoShowCondition": 0,
                    # "revNoshowFee": 0,
                })
            if order_info.inf_count > 0:
                output_routing['rule']['changesInfoList'].append({
                    "changesType": 0,
                    "changesStatus": "T",
                    # "changesFee": 0,
                    # "currency": "CNY",
                    "passengerType": 2,
                    "revNoshow": "T",
                    "revNoShowCondition": 0,
                    # "revNoshowFee": 0,
                })
            baggage_info = {
                "segmentNo": flight_segment.routing_number,
                "passengerType": 0,
                "baggagePiece": 0,
                "baggageWeight": 0,
            }
            output_routing['rule']['formatBaggageInfoList'].append(baggage_info)
            if order_info.chd_count > 0:
                output_routing['rule']['formatBaggageInfoList'].append({
                    "segmentNo": flight_segment.routing_number,
                    "passengerType": 1,
                    "baggagePiece": 0,
                    "baggageWeight": 0,
                })
            if order_info.inf_count > 0:
                output_routing['rule']['formatBaggageInfoList'].append({
                    "segmentNo": flight_segment.routing_number,
                    "passengerType": 2,
                    "baggagePiece": 0,
                    "baggageWeight": 0,
                })

        for flight_segment in order_info.routing.ret_segments:
            flight_suffix = str(int(flight_segment.flight_number[2:]))
            flight_number = flight_segment.flight_number[:2] + flight_suffix

            output_segment = {
                "carrier": flight_segment.carrier,
                "depAirport": flight_segment.dep_airport,
                "depTime": datetime.datetime.strptime(flight_segment.dep_time, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'),
                "arrAirport": flight_segment.arr_airport,
                "arrTime": datetime.datetime.strptime(flight_segment.arr_time, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'),
                "stopAirports": flight_segment.stop_airports,
                "codeShare": False,
                "cabin": flight_segment.cabin,
                "flightNumber": flight_number,
                "depTerminal": flight_segment.dep_terminal,
                "arrTerminal": flight_segment.arr_terminal,
                "cabinGrade": flight_segment.cabin_grade,
                "duration": flight_segment.duration
            }
            output_routing['retSegments'].append(output_segment)

            baggage_info = {
                "segmentNo": flight_segment.routing_number,
                "passengerType": 0,
                "baggagePiece": 0,
                "baggageWeight": 0,
            }
            output_routing['rule']['formatBaggageInfoList'].append(baggage_info)
            if order_info.chd_count > 0:
                output_routing['rule']['formatBaggageInfoList'].append({
                    "segmentNo": flight_segment.routing_number,
                    "passengerType": 1,
                    "baggagePiece": 0,
                    "baggageWeight": 0,
                })
            if order_info.inf_count > 0:
                output_routing['rule']['formatBaggageInfoList'].append({
                    "segmentNo": flight_segment.routing_number,
                    "passengerType": 2,
                    "baggagePiece": 0,
                    "baggageWeight": 0,
                })

        ret['routing'] = output_routing
        ret = self.aes_encrypt(json.dumps(ret))
        Logger().debug('aes_encrypt data %s' % ret)
        self.final_result = ret
        return True

    def _export_order_detail(self, ota_order_status='READY_TO_ISSUE', ota_order_id=None):
        """

        :param ota_order_status:
        :param ota_order_id:
        :return:
        """

        pass

    def _export_order_list(self, ota_order_status='READY_TO_ISSUE', start_time=None, end_time=None):
        """

        :param ota_order_status:
        :param start_time:
        :param end_time:
        :return:
        """

        pass

    def _set_order_issued(self, order_info):
        """

        :param order_info:
        :return:
        """

        pass


if __name__ == '__main__':
    pass
