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
from ..dao.iata_code import BUDGET_AIRLINE_CODE


class Lvmama(OTABase):
    """
    OTA 接口基类，
    该接口所有子类集成必须自己实现异常捕捉，如果抛出异常则OTA请求会返回500
    """
    ticket_process_mode = 'api'  # 票号处理模式-接口方式
    order_detail_process_mode = 'api'  # 订单详情同步模式-接口模式
    ota_name = 'lvmama'  # OTA名称，保证唯一，必须赋值
    ota_env = 'PROD'  # 生产OR测试接口 TODO 暂时无作用
    ota_token = '8a69427239d7039f'  # ota 访问验证token
    cn_ota_name = '驴妈妈OTA'
    pay_channel = 'ALIPAY'
    call_back_username = 'shyy123'  # 详情导出 回调票号等鉴权
    call_back_password = 'yida1680'  # 详情导出 回调票号等鉴权
    aes_key = 'C5OF3YKENMDD37YH'  # 生产环境KEY
    aes_iv = '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'  # aes iv

    def __init__(self):
        super(Lvmama, self).__init__()

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
            "status": "A100",
            "msg": "no flight",
            "routings": [

            ]
        }
        return ret

    def verify_interface_error_output(self):
        """
        接口报错返回
        :return:
        """
        ret = {
            "status": "B101",
            "msg": "余位不足",
            "routings": [

            ]
        }

        return ret

    def order_interface_error_output(self):
        """
        接口报错返回
        :return:
        """
        ret = {
            "status": "C101",
            "msg": "余位不足",
            "routings": [

            ]
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
        self.search_info.adt_count = int(req_body['adultNum'])
        self.search_info.chd_count = int(req_body['childNum'])
        self.search_info.cabin_grade_list = req_body.get('cabinGrade',[])

        self.search_info.inf_count = 0
        self.search_info.ret_date = datetime.datetime.strptime(req_body['retDate'], '%Y%m%d').strftime('%Y-%m-%d') if req_body['retDate'] else None
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


        routing
        信息
        "data":"3da0a93eba26c6e8f28955fe65f426fadbec03d9",
        "publishPrice":0,  # 公布运价 不用管
        "adultPrice":800,  # 成人价 fareInfoView list 需要限定为paxType=“ADT” fare salePrice
        "adultTax":66,  # 成人税
        "childPublishPrice":0,  # 公布运价 不用管
        "childPrice":400,  # 儿童价  fareInfoView list 需要限定为paxType=“CHD” fare salePrice
        "childTax":66,  # 儿童税
        "currency":"CNY",  # 默认
        "nationanlityType":0,  # 默认返回0
        "nationality":"",  # 默认值 空
        "adultAgeRestriction":"",  # 默认值 空
        "ticketInvoiceType":0,  # 默认为0
        "minPassengerCount":1,  # 默认返回 1
        "maxPassengerCount":9,  # 默认返回 9
        "productType":2,  # 选择2 航司官网产品

          segments 信息

        "carrier":"AA",  # 航司 marketingAirline
        "depAirport":"LAX",  # 起飞机场 departureAirport
        "depTime":"201203140140", # 起飞时间 departureDateTime
        "arrAirport":"PEK", # 到达机场 arrivalAirport
        "arrTime":"201203150530", # 到达时间  arrivalDateTime 需要进行转换
        "stopCities":"",  # 如果有经停，用/分割 三字码  stopLocation cityCode list需遍历
        "stopAirports":"",  # 如果有经停，用/分割 三字码  stopLocation code list需遍历
        "codeShare":false,  # 选择false
        "cabin":"Y",  # 选择 Y  flights bookingClassAvail cabinCode
        "cabinCount":9, # 剩余座位数，没有传9 flights bookingClassAvail cabinStatusCode A: >= 10
        ----"aircraftCode":"777",  #
        "flightNumber":"AA89",  # 航班号 flights flightNumber
        ----"operatingCarrier":"",
        ----"operatingFlightNo":"",
        "originTerminal":"T2",  # 起始航站楼  "terminal":"--"  为空情况
        "destinationTerminal":"T1",  # 到达航站楼  arrivalAirport terminal
        "cabinGrade":"Y",  # 选择Y cabinInfo  baseCabinCode  参考 cabinNames
        "duration":"130",  # 飞行时间 分钟 flights duration

    退订规定

        "refundType":0, # 退票类型 0：客票全部未使用；1：客票部分使用（1仅往返程可使用）

        "refundStatus":"E", # 退票标识 T：不可退 H：有条件退 F：免费退 E：退改签规则以航空公司为准；

        ----------"refundFee":500,  # 退票金额，当refundStatus =H,必须赋值；如果refundStatus =T/F,则此字段可不赋值
        "currency":"CNY",  # 退票费币种，当refundStatus =H，必须赋值。IATA标准币种编码,（目前仅限和Routing报价币种一致）
        "passengerType":0,  # 乘客类型，0 成人/1 儿童
        "refNoshow":"E",  # 是否允许NoShow退票，T：不可退，E：按航司客规为准，H：有条件退，F：免费退
        ----------"refNoShowCondition":24,  # NoShow时限，即起飞前多久算NoShow；单位：小时 ；如不赋值则认为航班起飞时间算NoShow时间节点
        ----------"refNoshowFee":1000,  # NoShow后退票费用，即算上NoShow罚金后的退票费用；当NoShow=H，必须赋值
        ----------"refRemark":""  # 退票备注，最长500个字符长度

    改签规定
        "changeType":0,  # 改期类型 0：客票全部未使用；1：客票部分使用（1仅往返程可使用）
        "changeStatus":"E", # 改期标识 T：不可改期 H：有条件改期 F：免费改期 E：改签规则以航空公司为准；
        ----"changeFee":500, # 改期金额，当changeStatus=H时，必须赋值；如果changeStatus =T/F,则此字段可不赋值
        "currency":"CNY",  # 改期费币种，当changesStatus =H，必须赋值。IATA标准币种编码, （目前仅限和Routing报价币种一致）
        "passengerType":0,  # 乘客类型，0 成人 /1儿童
        "chaNoshow":"E",  # 是否允许NoShow改期，T：不可改，E：按航司客规为准，H：有条件改，F：免费改
        ----"chaNoShowCondition":24,  # NoShow时限，即起飞前多久算NoShow；单位：小时 ；如不赋值则认为航班起飞时间算NoShow时间节点
        ----"chaNoshowFee":1000,   #  NoShow后改期费用，即算上NoShow罚金后的改期费用；当chaNoshow =H，必须赋值
        ----"chaRemark":""  # 改期备注，最长500个字符长度

    包裹规定
        "baggagePieces":1, # 行李件数，1表示1PC
        "baggageAllowance":23, # 行李额限重，1表示单件限重1KG
        "segmentNum":1  # 航段序号：从1至行程总段数的数值

        """

        if search_info.assoc_search_routings:
            ret = {
                "status": "A0",
                "msg": "success",
                "routings": []
            }

            for flight_routing in search_info.assoc_search_routings:

                output_routing = {
                    "data": flight_routing.routing_key,
                    "publishPrice": 0,
                    "adultPrice": flight_routing.adult_price_forsale,
                    "adultTax": flight_routing.adult_tax,
                    "adultFcny":flight_routing.adult_price,
                    "childFcny":flight_routing.child_price,
                    "childPublishPrice": 0,
                    "childPrice": flight_routing.child_price_forsale,
                    "childTax": flight_routing.child_tax,
                    "currency": "CNY",
                    "nationanlityType": 0,
                    "nationality": "",
                    "adultAgeRestriction": "",
                    "ticketInvoiceType": 0,
                    "minPassengerCount": 1,
                    "maxPassengerCount": 9,
                    "productType": self.product_type,
                    "fromSegments": [],
                    "rule": {
                        "refundInfos": [],
                        "changeInfos": [],
                        "baggageInfo": {
                            "hasBaggage": 1,
                            "baggageRules": []
                        }
                    },
                    "retSegments": []
                }
                for flight_segment in flight_routing['from_segments']:

                    output_segment = {
                        "carrier": flight_segment.carrier,
                        "depAirport": flight_segment.dep_airport,
                        "depTime": datetime.datetime.strptime(flight_segment.dep_time, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'),
                        "arrAirport": flight_segment.arr_airport,
                        "arrTime": datetime.datetime.strptime(flight_segment.arr_time, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'),
                        "stopAirports": flight_segment.stop_airports,
                        "codeShare": False,
                        "cabin": flight_segment.cabin,
                        "cabinCount": flight_routing.segment_min_cabin_count,
                        # "aircraftCode": "777",
                        "flightNumber": flight_segment.flight_number,
                        # "operatingCarrier": "",
                        # "operatingFlightNo": "",
                        "depTerminal": flight_segment.dep_terminal,
                        "arrTerminal": flight_segment.arr_terminal,
                        "cabinGrade": flight_segment.cabin_grade,
                        "duration": flight_segment.duration
                    }
                    output_routing['fromSegments'].append(output_segment)
                    refund_info = {
                        "refundType": 0,
                        "refundStatus": "E",
                        "currency": "CNY",
                        "passengerType": 0,
                        "refNoshow": "E",
                    }
                    output_routing['rule']['refundInfos'].append(refund_info)
                    change_info = {
                        "changeType": 0,
                        "changeStatus": "E",
                        "currency": "CNY",
                        "passengerType": 0,
                        "chaNoshow": "E",
                    }
                    output_routing['rule']['changeInfos'].append(change_info)
                    if flight_segment.carrier in BUDGET_AIRLINE_CODE:
                        baggage_info = {
                            "baggagePieces": 0,
                            "baggageAllowance": 0,
                            "segmentNum": flight_segment.routing_number,
                        }
                    else:
                        baggage_info = {
                            "baggagePieces": 1,
                            "baggageAllowance": 23,
                            "segmentNum": flight_segment.routing_number,
                        }
                    output_routing['rule']['baggageInfo']['baggageRules'].append(baggage_info)

                for flight_segment in flight_routing['ret_segments']:
                    output_segment = {
                        "carrier": flight_segment.carrier,
                        "depAirport": flight_segment.dep_airport,
                        "depTime": datetime.datetime.strptime(flight_segment.dep_time, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'),
                        "arrAirport": flight_segment.arr_airport,
                        "arrTime": datetime.datetime.strptime(flight_segment.arr_time, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'),
                        "stopAirports": flight_segment.stop_airports,
                        "codeShare": False,
                        "cabin": flight_segment.cabin,
                        "cabinCount": flight_routing.segment_min_cabin_count,
                        # "aircraftCode": "777",
                        "flightNumber": flight_segment.flight_number,
                        # "operatingCarrier": "",
                        # "operatingFlightNo": "",
                        "depTerminal": flight_segment.dep_terminal,
                        "arrTerminal": flight_segment.arr_terminal,
                        "cabinGrade": flight_segment.cabin_grade,
                        "duration": flight_segment.duration
                    }
                    output_routing['retSegments'].append(output_segment)
                    refund_info = {
                        "refundType": 0,
                        "refundStatus": "E",
                        "currency": "CNY",
                        "passengerType": 0,
                        "refNoshow": "E",
                    }
                    output_routing['rule']['refundInfos'].append(refund_info)
                    change_info = {
                        "changeType": 0,
                        "changeStatus": "E",
                        "currency": "CNY",
                        "passengerType": 0,
                        "chaNoshow": "E",
                    }
                    output_routing['rule']['changeInfos'].append(change_info)
                    if flight_segment.carrier in BUDGET_AIRLINE_CODE:
                        baggage_info = {
                            "baggagePieces": 0,
                            "baggageAllowance": 0,
                            "segmentNum": flight_segment.routing_number,
                        }
                    else:
                        baggage_info = {
                            "baggagePieces": 1,
                            "baggageAllowance": 23,
                            "segmentNum": flight_segment.routing_number,
                        }
                    output_routing['rule']['baggageInfo']['baggageRules'].append(baggage_info)

                ret['routings'].append(output_routing)

            self.final_result = ret
        else:
            self.final_result= self.search_interface_error_output()
    def _before_verify_interface(self, req_body):
        """
        验价接口，
         adt_count, chd_count=0, trip_type='OW', routing={}

    {
    "userName":"admin",
    "tripType":"1",
    "routing":{
        "data":"3da0a93eba26c6e8f28955fe65f426fadbec03d9",
        "fromSegments":[
            {
                "carrier":"AA",
                "depAirport":"LAX",
                "depTime":"201203140140",
                "arrAirport":"PEK",
                "arrTime":"201203150530",
                "stopCities":"",
                "stopAirports":"",
                "codeShare":false,
                "cabin":"B",
                "cabinCount":9,
                "aircraftCode":"777",
                "flightNumber":"AA089",
                "operatingCarrier":"",
                "operatingFlightNo":"",
                "depTerminal":"T2",
                "arrTerminal":"T1",
                "cabinGrade":"Y",
                "duration":"130"
            }
        ],
        "retSegments":[

        ]
    }
}
        根据fromsegments 列表中的第一个segment的depairport 和最后一个的arrairport 确定 出发地和目的地
        根据第一个segment的起飞时间确定 起飞日期
        根据第一个segment的舱位数量确认成人位置

        :param routing:  只含航班信息，不含价格信息和规则信息。
        :return:
        """

        req_body = json.loads(req_body)
        self.search_info.adt_count = req_body['adultNumber']
        self.search_info.chd_count = req_body['childNumber']
        self.search_info.inf_count = 0

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
            "status": "B0",
            "msg": "success",
            "sessionId": self.request_id,
            "routing": {},
            "rule": {
                "refundInfos": [],
                "changeInfos": [],
                "baggageInfo": {
                    "hasBaggage": 1,
                    "baggageRules": []
                }
            }
        }

        output_routing = {
            "data": search_info.verify_routing_key,  # 返回原来的key
            "publishPrice": 0,
            "adultPrice": search_info.routing.adult_price_forsale,
            "adultTax": search_info.routing.adult_tax,
            "adultFcny": search_info.routing.adult_price,
            "childFcny": search_info.routing.child_price,
            "childPublishPrice": 0,
            "childPrice": search_info.routing.child_price_forsale,
            "childTax": search_info.routing.child_tax,
            "currency": "CNY",
            "nationanlityType": 0,
            "nationality": "",
            "adultAgeRestriction": "",
            "ticketInvoiceType": 0,
            "minPassengerCount": 1,
            "maxPassengerCount": 9,
            "productType": self.product_type,
            "fromSegments": [],
            "retSegments": []
        }

        for flight_segment in search_info.routing.from_segments:

            output_segment = {
                "carrier": flight_segment.carrier,
                "depAirport": flight_segment.dep_airport,
                "depTime": datetime.datetime.strptime(flight_segment.dep_time, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'),
                "arrAirport": flight_segment.arr_airport,
                "arrTime": datetime.datetime.strptime(flight_segment.arr_time, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'),
                "stopAirports": flight_segment.stop_airports,
                "codeShare": False,
                "cabin": flight_segment.cabin,
                "cabinCount": search_info.routing.segment_min_cabin_count,
                # "aircraftCode": "777",
                "flightNumber": flight_segment.flight_number,
                # "operatingCarrier": "",
                # "operatingFlightNo": "",
                "depTerminal": flight_segment.dep_terminal,
                "arrTerminal": flight_segment.arr_terminal,
                "cabinGrade": flight_segment.cabin_grade,
                "duration": flight_segment.duration
            }
            output_routing['fromSegments'].append(output_segment)
            refund_info = {
                "refundType": 0,
                "refundStatus": "E",
                "currency": "CNY",
                "passengerType": 0,
                "refNoshow": "E",
            }
            ret['rule']['refundInfos'].append(refund_info)
            change_info = {
                "changeType": 0,
                "changeStatus": "E",
                "currency": "CNY",
                "passengerType": 0,
                "chaNoshow": "E",
            }
            ret['rule']['changeInfos'].append(change_info)
            if flight_segment.carrier in BUDGET_AIRLINE_CODE:
                baggage_info = {
                    "baggagePieces": 0,
                    "baggageAllowance": 0,
                    "segmentNum": flight_segment.routing_number,
                }
            else:
                baggage_info = {
                    "baggagePieces": 1,
                    "baggageAllowance": 23,
                    "segmentNum": flight_segment.routing_number,
                }
            ret['rule']['baggageInfo']['baggageRules'].append(baggage_info)

        # 回程
        for flight_segment in search_info.routing.ret_segments:

            output_segment = {
                "carrier": flight_segment.carrier,
                "depAirport": flight_segment.dep_airport,
                "depTime": datetime.datetime.strptime(flight_segment.dep_time, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'),
                "arrAirport": flight_segment.arr_airport,
                "arrTime": datetime.datetime.strptime(flight_segment.arr_time, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'),
                "stopAirports": flight_segment.stop_airports,
                "codeShare": False,
                "cabin": flight_segment.cabin,
                "cabinCount": search_info.routing.segment_min_cabin_count,
                # "aircraftCode": "777",
                "flightNumber": flight_segment.flight_number,
                # "operatingCarrier": "",
                # "operatingFlightNo": "",
                "depTerminal": flight_segment.dep_terminal,
                "arrTerminal": flight_segment.arr_terminal,
                "cabinGrade": flight_segment.cabin_grade,
                "duration": flight_segment.duration
            }
            output_routing['retSegments'].append(output_segment)
            refund_info = {
                "refundType": 0,
                "refundStatus": "E",
                "currency": "CNY",
                "passengerType": 0,
                "refNoshow": "E",
            }
            ret['rule']['refundInfos'].append(refund_info)
            change_info = {
                "changeType": 0,
                "changeStatus": "E",
                "currency": "CNY",
                "passengerType": 0,
                "chaNoshow": "E",
            }
            ret['rule']['changeInfos'].append(change_info)
            if flight_segment.carrier in BUDGET_AIRLINE_CODE:
                baggage_info = {
                    "baggagePieces": 0,
                    "baggageAllowance": 0,
                    "segmentNum": flight_segment.routing_number,
                }
            else:
                baggage_info = {
                    "baggagePieces": 1,
                    "baggageAllowance": 23,
                    "segmentNum": flight_segment.routing_number,
                }
            ret['rule']['baggageInfo']['baggageRules'].append(baggage_info)

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
        self.order_info.ota_order_id = req_body.get('OtaOrderId', '')  # 获取otaorderid ，如果有的话
        for pax in req_body['passengers']:
            pax_info = PaxInfo()
            pax_info.passenger_id = pax.get('passengerID','')
            pax_info.last_name = pax.get('lastName','')
            pax_info.first_name = pax.get('firstName','')
            pax_info.name = pax.get('name','')
            if int(pax['ageType']) == 1:
                # 儿童
                pax_info.age_type = 'CHD'
                self.order_info.chd_count += 1
            elif int(pax['ageType']) == 0:
                pax_info.age_type = 'ADT'
                self.order_info.adt_count += 1
            else:
                pax_info.age_type = 'ADT'
            if pax.get('birthday',''):
                pax_info.birthdate = datetime.datetime.strptime(pax['birthday'], '%Y%m%d').strftime('%Y-%m-%d')  # 生单接口跟详情导出的格式不一致
            if pax.get('gender',''):
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
            if pax.get('cardExpired',''):
                pax_info.card_expired = datetime.datetime.strptime(pax['cardExpired'], '%Y%m%d').strftime('%Y-%m-%d')
            pax_info.card_issue_place = pax.get('cardIssuePlace','')
            pax_info.nationality = pax.get('nationality','')
            pax_info.attr_competion()
            self.order_info.passengers.append(pax_info)

        for contact in req_body['contacts']:
            contact_info = ContactInfo()
            contact_info.address = contact.get('address','')
            contact_info.postcode = contact.get('postcode','')
            contact_info.email = contact.get('email','')
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
            "status": "C0",
            "msg": "success",
            "sessionId": self.order_info.session_id,
            "orderNo": self.order_info.assoc_order_id,
            "pnrCode": self.order_info.pnr_code,
            "routing": {}
        }

        output_routing = {
            "data": order_info.verify_routing_key,
            "publishPrice": 0,
            "adultPrice": order_info.routing.adult_price_forsale,
            "adultTax": order_info.routing.adult_tax,
            "adultFcny": order_info.routing.adult_price,
            "childFcny": order_info.routing.child_price,
            "childPublishPrice": 0,
            "childPrice": order_info.routing.child_price_forsale,
            "childTax": order_info.routing.child_tax,
            "currency": "CNY",
            "nationanlityType": 0,
            "nationality": "",
            "adultAgeRestriction": "",
            "ticketInvoiceType": 0,
            "minPassengerCount": 1,
            "maxPassengerCount": 9,
            "productType": self.product_type,
            "fromSegments": [],
            "rule": {
                "refundInfos": [],
                "changeInfos": [],
                "baggageInfo": {
                    "hasBaggage": 1,
                    "baggageRules": []
                }
            },
            "retSegments": []
        }
        for flight_segment in order_info.routing.from_segments:

            output_segment = {
                "carrier": flight_segment.carrier,
                "depAirport": flight_segment.dep_airport,
                "depTime": datetime.datetime.strptime(flight_segment.dep_time, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'),
                "arrAirport": flight_segment.arr_airport,
                "arrTime": datetime.datetime.strptime(flight_segment.arr_time, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'),
                "stopAirports": flight_segment.stop_airports,
                "codeShare": False,
                "cabin": flight_segment.cabin,
                "cabinCount": order_info.routing.segment_min_cabin_count,
                # "aircraftCode": "777",
                "flightNumber": flight_segment.flight_number,
                # "operatingCarrier": "",
                # "operatingFlightNo": "",
                "depTerminal": flight_segment.dep_terminal,
                "arrTerminal": flight_segment.arr_terminal,
                "cabinGrade": flight_segment.cabin_grade,
                "duration": flight_segment.duration
            }
            output_routing['fromSegments'].append(output_segment)
            refund_info = {
                "refundType": 0,
                "refundStatus": "E",
                "currency": "CNY",
                "passengerType": 0,
                "refNoshow": "E",
            }
            output_routing['rule']['refundInfos'].append(refund_info)
            change_info = {
                "changeType": 0,
                "changeStatus": "E",
                "currency": "CNY",
                "passengerType": 0,
                "chaNoshow": "E",
            }
            output_routing['rule']['changeInfos'].append(change_info)
            if flight_segment.carrier in BUDGET_AIRLINE_CODE:
                baggage_info = {
                    "baggagePieces": 0,
                    "baggageAllowance": 0,
                    "segmentNum": flight_segment.routing_number,
                }
            else:
                baggage_info = {
                    "baggagePieces": 1,
                    "baggageAllowance": 23,
                    "segmentNum": flight_segment.routing_number,
                }
            output_routing['rule']['baggageInfo']['baggageRules'].append(baggage_info)

        # 回程
        for flight_segment in order_info.routing.ret_segments:

            output_segment = {
                "carrier": flight_segment.carrier,
                "depAirport": flight_segment.dep_airport,
                "depTime": datetime.datetime.strptime(flight_segment.dep_time, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'),
                "arrAirport": flight_segment.arr_airport,
                "arrTime": datetime.datetime.strptime(flight_segment.arr_time, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'),
                "stopAirports": flight_segment.stop_airports,
                "codeShare": False,
                "cabin": flight_segment.cabin,
                "cabinCount": order_info.routing.segment_min_cabin_count,
                # "aircraftCode": "777",
                "flightNumber": flight_segment.flight_number,
                # "operatingCarrier": "",
                # "operatingFlightNo": "",
                "depTerminal": flight_segment.dep_terminal,
                "arrTerminal": flight_segment.arr_terminal,
                "cabinGrade": flight_segment.cabin_grade,
                "duration": flight_segment.duration
            }
            output_routing['retSegments'].append(output_segment)
            refund_info = {
                "refundType": 0,
                "refundStatus": "E",
                "currency": "CNY",
                "passengerType": 0,
                "refNoshow": "E",
            }
            output_routing['rule']['refundInfos'].append(refund_info)
            change_info = {
                "changeType": 0,
                "changeStatus": "E",
                "currency": "CNY",
                "passengerType": 0,
                "chaNoshow": "E",
            }
            output_routing['rule']['changeInfos'].append(change_info)
            if flight_segment.carrier in BUDGET_AIRLINE_CODE:
                baggage_info = {
                    "baggagePieces": 0,
                    "baggageAllowance": 0,
                    "segmentNum": flight_segment.routing_number,
                }
            else:
                baggage_info = {
                    "baggagePieces": 1,
                    "baggageAllowance": 23,
                    "segmentNum": flight_segment.routing_number,
                }
            output_routing['rule']['baggageInfo']['baggageRules'].append(baggage_info)
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
        http_session = HttpRequest()
        data = {
            'userName': self.call_back_username,
            'password': self.call_back_password,
            'orderStatus': ota_order_status,
            'tcOrderNo': ota_order_id
        }
        Logger().debug('_export_order_detail request %s' % data)
        result = http_session.request(method='POST', url=self.export_order_detail_url, json=data, verify=False,
                                      is_direct=True).to_json()

        if result['status'] == 'G0':

            # 请求成功

            oi = OrderInfo()
            oi.ota_pay_price = result['finalPrice']  # TODO 暂时只获取价格返回

            return oi
        else:
            raise ExportOrderDetailException(err=result)

    def _export_order_list(self, ota_order_status='READY_TO_ISSUE', start_time=None, end_time=None):
        """

        :param ota_order_status:
        :param start_time:
        :param end_time:
        :return:
        """
        http_session = HttpRequest()
        data = {
            'userName': self.call_back_username,
            'password': self.call_back_password,
            'orderStatus': ota_order_status,
            'startTime': start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'endTime': end_time.strftime('%Y-%m-%d %H:%M:%S')
        }
        Logger().debug('_export_order_list request %s' % data)

        result = http_session.request(method='POST', url=self.export_order_list_url, json=data, verify=False,
                                      is_direct=True).to_json()
        order_list = []
        if result['status'] == 'F0':

            # 请求成功
            for order in result['orderLists']:
                oi = OrderInfo()
                oi.ota_order_id = order['tcOrderNo']
                oi.assoc_order_id = order['orderNo']
                oi.ota_order_status = order['orderStatus']
                order_list.append(oi)
            return order_list
        else:
            raise ExportOrderListException(result)

    def _set_order_issued(self, order_info):
        """

        :param order_info:
        :return:
        """
        http_session = HttpRequest()
        pax_infos = []
        # TODO 目前没有加入返程和缺口程
        for rn in [segment.routing_number for segment in order_info.routing.from_segments]:
            for pax_info in order_info.passengers:
                pax_infos.append({
                    'passengerId': pax_info.passenger_id,
                    'lastName': pax_info.last_name,
                    'firstName': pax_info.first_name,
                    'pnrCode': order_info.pnr_code,
                    'ticketNo': pax_info.ticket_no,
                    'idNo': pax_info.used_card_no,
                    'segmentIndex': rn  # 航段索引，按照乘坐航班的顺序来走，

                })
        data = {
            'userName': self.call_back_username,
            'password': self.call_back_password,
            'orderNo': order_info.assoc_order_id,
            'tcOrderNo': order_info.ota_order_id,
            'ticketNoItems': pax_infos
        }
        result = http_session.request(method='POST', url=self.set_order_issued_url, json=data, verify=False,
                                      is_direct=True).to_json()
        if result['status'] == 'E0':
            return True
        else:
            raise SetOrderIssuedException(result)


    def _before_notice_pay_interface(self, req_body):
        """

        :param req_body:
        :return:
        """
        req_body = json.loads(req_body)
        self.order_info.assoc_order_id = req_body['orderNo']
        self.order_info.ready_to_pay_price = float(req_body['finalPrice'])


    def _after_notice_pay_interface(self, order_info):
        """

        :param
        :return:
        """
        self.final_result = json.dumps({'status':order_info.notice_pay_status,'msg':ERROR_STATUS[order_info.notice_pay_status]})
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
            segments = []
            segment_index = 0
            for flight_segment in order_info.routing.from_segments:
                segment_index +=1
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
                    "segmentIndex":segment_index
                }
                segments.append(output_segment)

            for flight_segment in order_info.routing.ret_segments:
                segment_index +=1
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
                    "segmentIndex":segment_index
                }
                segments.append(output_segment)

            price_info = []
            price_info.append(
                {
                    'passengerType': 0,
                    'price': order_info.ota_adult_price,
                    'tax': order_info.routing.adult_tax
                }
            )
            if order_info.routing.child_price:
                price_info.append(
                    {
                        'passengerType':1,
                        'price':order_info.ota_child_price,
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
                    'passengerId':pax_info.passenger_id,
                    'lastName':pax_info.last_name,
                    'firstName':pax_info.first_name,
                    'name':pax_info.name,
                    'gender':pax_info.gender,
                    'passengerType':age_type,
                    'birthday':pax_info.birthdate,
                    'cardType':pax_info.used_card_type,
                    'cardNum':pax_info.used_card_no,
                    'pnrCode':order_info.pnr_code,
                    'ticketNo':pax_info.ticket_no
                }
                paxs.append(output_pax)

            if order_info.trip_type == 'OW':
                trip_type = '1'
            elif order_info.trip_type == 'RT':
                trip_type = '2'
            else:
                raise OrderDetailInterfaceException('no available trip type')
            ret = {
                'status':'SUCCESS',
                'msg':'成功',
                'orderNo':order_info.assoc_order_id,
                'flightInfos':[
                    {
                        'travelType':trip_type,
                        'segments':segments
                    }
                ],
                'passengerInfos':paxs,
                'priceInfos':price_info,
                'finalPrice':order_info.ota_pay_price,
                'tripType':'1',
                'orderStatus': PROVIDERS_STATUS[order_info.providers_status]['status_category']  #此处屏蔽具体的状态信息，只显示粗略流程节点。
            }
            self.final_result = json.dumps(ret)
            return True


if __name__ == '__main__':
    pass