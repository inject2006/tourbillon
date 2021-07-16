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
import random
from ..controller.http_request import HttpRequest
from ..utils.exception import *
from ..utils.logger import Logger
from .base import OTABase
from ..dao.models import *
from ..dao.internal import *
from Crypto.Cipher import AES
from app import TBG


class Tuniu(OTABase):
    """
    OTA 接口基类，

    """

    order_to_pay_wait_time = 60 * 28  # 下单到支付最长等待时间 单位 秒
    ticket_process_mode = 'api'  # 票号处理模式-主动推送
    order_detail_process_mode = 'api' # 订单详情同步模式-轮询拉取模式
    ota_name = 'tuniu'  # OTA名称，保证唯一，必须赋值
    ota_env = 'PROD'  # 生产OR测试接口 TODO 暂时无作用
    ota_token = 'pks67r30gvjod5a8'  # ota 访问验证token
    product_type = 0  # 运价类型：0: GDS 私有运价 1:GDS 公布运价 (此场 景下字段 farebasis 不能为空) 2:航司官网产品 3:廉价航司产品 4:特价产品
    cn_ota_name = '途牛OTA'
    aes_key = 'A64K9GE72VBY8NUD'  # 生产环境KEY
    low_price_provider_channel = 'tuniu_customer_common'  # 定义该ota的关联低价看板
    # aes_key = '1234567890123456' # 测试环境KEY
    aes_iv = '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'  # aes iv


    def __init__(self):
        super(Tuniu, self).__init__()

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
            "msg": "无航班",
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
            "status": -1,
            "msg": "验价错误",
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
            "status": -1,
            "msg": "下单错误",
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
        if req_body['tripType'] == 1:
            trip_type = 'OW'
        elif req_body['tripType'] == 2:
            trip_type = 'RT'
        elif req_body['tripType'] == 3:
            trip_type = 'MT'
        else:
            trip_type = 'OW'
        self.search_info.trip_type = trip_type


        if self.search_info.trip_type == 'MT':
            # 多程的处理
            fcl = req_body['fromCity'].split(',')
            fdl = req_body['fromDate'].split(',')
            self.search_info.from_airport = fcl[0].split('/')[0]
            self.search_info.to_airport = fcl[-1].split('/')[1]
            self.search_info.from_date = datetime.datetime.strptime(fdl[0], '%Y%m%d').strftime('%Y-%m-%d')
        else:
            self.search_info.from_airport = req_body['fromCity']
            self.search_info.to_airport = req_body['toCity']
            self.search_info.from_date = datetime.datetime.strptime(req_body['fromDate'], '%Y%m%d').strftime('%Y-%m-%d')
        self.search_info.adt_count = int(req_body['adultNumber'])
        self.search_info.chd_count = int(req_body['childNumber'])

        cg_map = {0:['Y','F','C','S'],1:['Y'],2:['C'],3:['F'],4:['S']}
        self.search_info.cabin_grade_list = cg_map[req_body['cabinClass']]

        self.search_info.inf_count = 0
        self.search_info.ret_date = datetime.datetime.strptime(req_body['retDate'], '%Y%m%d').strftime('%Y-%m-%d') if req_body['retDate'] else None
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
                "status": 0,
                "msg": "成功",
                "routings": []
            }

            log_record = []

            cg_map = {'Y': 1, 'C': 2, 'F': 3, 'S': 4}
            for flight_routing in search_info.assoc_search_routings:
                if flight_routing.child_price:
                    child_flag = 1
                else:
                    child_flag = 0
                output_routing = {
                    "data": flight_routing.routing_key,
                    "adultPrice": flight_routing.adult_price_forsale,
                    "adultTax": flight_routing.adult_tax,
                    "childPrice": flight_routing.child_price_forsale,
                    "childTax": flight_routing.child_tax,
                    "childFlag":child_flag,
                    "infantPrice":flight_routing.child_price,
                    "infantTax":flight_routing.child_tax, # TODO 暂时与儿童票相同
                    "currency": "CNY",
                    "nationalityType": 0,
                    "nationality": "CN",
                    "suitAge":"",
                    "priceType":0,
                    "applyType":0,
                    "adultTaxType":0,
                    "childTaxType":0,
                    "infantTaxType":0,
                    "ticketingCarrier":flight_routing['from_segments'][0].carrier,
                    "fromSegments": [],
                    "rule": {
                        "refund": "不可退票",
                        "endorse": "不可改签",
                        "baggage": "以航司规则为准",
                        "other": ""
                    },
                    "retSegments": []
                }
                if flight_routing.segment_min_cabin_count > 9:
                    cabin_count = 10
                else:
                    cabin_count = flight_routing.segment_min_cabin_count

                for flight_segment in flight_routing['from_segments']:

                    output_segment = {
                        "flightOption": 1,
                        "carrier": flight_segment.carrier,
                        "depAirport": flight_segment.dep_airport,
                        "depTime": datetime.datetime.strptime(flight_segment.dep_time, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'),
                        "arrAirport": flight_segment.arr_airport,
                        "arrTime": datetime.datetime.strptime(flight_segment.arr_time, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'),
                        "stopCities": flight_segment.stop_cities,
                        "codeShare": False,
                        "cabinCode": flight_segment.cabin,
                        "seatCount": cabin_count,
                        "aircraftCode": "",
                        "flightNumber": flight_segment.flight_number,
                        # "operatingCarrier": "",
                        # "operatingFlightNo": "",
                        "departureTerminal": flight_segment.dep_terminal if not re.match(u'[\u4e00-\u9fa5]+',
                                                                            flight_segment.dep_terminal) else '',
                        "arrivingTerminal": flight_segment.arr_terminal if not re.match(u'[\u4e00-\u9fa5]+',
                                                                            flight_segment.arr_terminal) else '',

                        "cabinClass": cg_map[flight_segment.cabin_grade],
                    }
                    output_routing['fromSegments'].append(output_segment)

                for flight_segment in flight_routing['ret_segments']:

                    output_segment = {
                        "flightOption": 1,
                        "carrier": flight_segment.carrier,
                        "depAirport": flight_segment.dep_airport,
                        "depTime": datetime.datetime.strptime(flight_segment.dep_time, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'),
                        "arrAirport": flight_segment.arr_airport,
                        "arrTime": datetime.datetime.strptime(flight_segment.arr_time, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'),
                        "stopCities": flight_segment.stop_cities,
                        "codeShare": False,
                        "cabinCode": flight_segment.cabin,
                        "seatCount": cabin_count,
                        "aircraftCode": "",
                        "flightNumber": flight_segment.flight_number,
                        # "operatingCarrier": "",
                        # "operatingFlightNo": "",
                        "departureTerminal": flight_segment.dep_terminal if not re.match(u'[\u4e00-\u9fa5]+',
                                                                            flight_segment.dep_terminal) else '',
                        "arrivingTerminal": flight_segment.arr_terminal if not re.match(u'[\u4e00-\u9fa5]+',
                                                                            flight_segment.arr_terminal) else '',

                        "cabinClass": cg_map[flight_segment.cabin_grade],
                    }
                    output_routing['retSegments'].append(output_segment)

                ret['routings'].append(output_routing)

            self.final_result = ret
        else:

            self.final_result = self.search_interface_error_output()

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

        if req_body['tripType'] == 1:
            trip_type = 'OW'
        elif req_body['tripType'] == 2:
            trip_type = 'RT'
        elif req_body['tripType'] == 3:
            trip_type = 'MT'
        else:
            trip_type = 'OW'
        self.search_info.trip_type = trip_type
        # TODO 仅适用于单程，多程需考虑ret_segments
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
            "status": 0,
            "msg": "成功",
            "sessionId": self.request_id,
            "routing": {},
            "maxSeats": search_info.routing.segment_min_cabin_count
        }
        cg_map = {'Y': 1, 'C': 2, 'F': 3, 'S': 4}

        if search_info.routing.child_price:
            child_flag = 1
        else:
            child_flag = 0
        output_routing = {
            "data": search_info.verify_routing_key,
            "adultPrice": search_info.routing.adult_price_forsale,
            "adultTax": search_info.routing.adult_tax,
            "childPrice": search_info.routing.child_price_forsale,
            "childTax": search_info.routing.child_tax,
            "childFlag": child_flag,
            "infantPrice": search_info.routing.child_price,
            "infantTax": search_info.routing.child_tax,  # TODO 暂时与儿童票相同
            "currency": "CNY",
            "nationalityType": 0,
            "nationality": "CN",
            "suitAge": "",
            "priceType": 0,
            "applyType": 0,
            "adultTaxType": 0,
            "childTaxType": 0,
            "infantTaxType": 0,
            "ticketingCarrier": search_info.routing.from_segments[0].carrier,
            "fromSegments": [],
            "rule": {
                "refund": "不可退票",
                "endorse": "不可改签",
                "baggage": "以航司规则为准",
                "other": ""
            },
            "retSegments": []
        }
        if search_info.routing.segment_min_cabin_count > 9:
            cabin_count = 10
        else:
            cabin_count = search_info.routing.segment_min_cabin_count
        for flight_segment in search_info.routing.from_segments:

            output_segment = {
                "flightOption": 1,
                "carrier": flight_segment.carrier,
                "depAirport": flight_segment.dep_airport,
                "depTime": datetime.datetime.strptime(flight_segment.dep_time, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'),
                "arrAirport": flight_segment.arr_airport,
                "arrTime": datetime.datetime.strptime(flight_segment.arr_time, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'),
                "stopCities": flight_segment.stop_cities,
                "codeShare": False,
                "cabinCode": flight_segment.cabin,
                "seatCount": cabin_count,
                "aircraftCode": "",
                "flightNumber": flight_segment.flight_number,
                "departureTerminal": flight_segment.dep_terminal if not re.match(u'[\u4e00-\u9fa5]+',
                                                                            flight_segment.dep_terminal) else '',
                "arrivingTerminal": flight_segment.arr_terminal if not re.match(u'[\u4e00-\u9fa5]+',
                                                                            flight_segment.arr_terminal) else '',

                "cabinClass": cg_map[flight_segment.cabin_grade],
            }
            output_routing['fromSegments'].append(output_segment)


        for flight_segment in search_info.routing.ret_segments:

            output_segment = {
                "flightOption": 1,
                "carrier": flight_segment.carrier,
                "depAirport": flight_segment.dep_airport,
                "depTime": datetime.datetime.strptime(flight_segment.dep_time, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'),
                "arrAirport": flight_segment.arr_airport,
                "arrTime": datetime.datetime.strptime(flight_segment.arr_time, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'),
                "stopCities": flight_segment.stop_cities,
                "codeShare": False,
                "cabinCode": flight_segment.cabin,
                "seatCount": cabin_count,
                "aircraftCode": "",
                "flightNumber": flight_segment.flight_number,
                "departureTerminal": flight_segment.dep_terminal if not re.match(u'[\u4e00-\u9fa5]+',
                                                                            flight_segment.dep_terminal) else '',
                "arrivingTerminal": flight_segment.arr_terminal if not re.match(u'[\u4e00-\u9fa5]+',
                                                                            flight_segment.arr_terminal) else '',

                "cabinClass": cg_map[flight_segment.cabin_grade],
            }
            output_routing['retSegments'].append(output_segment)

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

        if req_body['tripType'] == 1:
            trip_type = 'OW'
        elif req_body['tripType'] == 2:
            trip_type = 'RT'
        elif req_body['tripType'] == 3:
            trip_type = 'MT'
        else:
            trip_type = 'OW'
        self.order_info.trip_type = trip_type
        self.order_info.session_id = req_body['sessionId']
        self.order_info.extra_data = req_body
        self.order_info.verify_routing_key = req_body['routing']['data']
        self.order_info.ota_order_id = "%s_%s" % (req_body['tuniuOrderId'] , Random.gen_num(5))
        self.order_info.is_test_order = req_body.get('is_test_order', 0)  # 是否为测试订单

        for pax in req_body['passengers']:
            pax_info = PaxInfo()
            pax_info.passenger_id = pax['cardNum'] # TODO 用卡号暂代
            pax_info.last_name = pax['name'].split('/')[0]
            pax_info.first_name = pax['name'].split('/')[1]
            if int(pax['ageType']) in [1,2]:
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

            if pax['cardExpired']:
                pax_info.card_expired = datetime.datetime.strptime(pax['cardExpired'], '%Y%m%d').strftime('%Y-%m-%d')
            pax_info.card_issue_place = pax.get('cardIssuePlace','')
            pax_info.nationality = pax.get('nationality','')
            pax_info.attr_competion()
            self.order_info.passengers.append(pax_info)

        contact = req_body['contact']
        contact_info = ContactInfo()
        contact_info.address = contact.get('address','')
        contact_info.postcode = contact.get('postcode','')
        contact_info.email = contact.get('email','')
        contact_info.mobile = contact.get('mobile','')
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
            "msg": "成功",
            "sessionId": order_info.session_id,
            "orderNo": order_info.ota_order_id,
            "pnrCode": order_info.pnr_code,
            "routing": {}
        }

        cg_map = {'Y': 1, 'C': 2, 'F': 3, 'S': 4}

        if order_info.routing.child_price:
            child_flag = 1
        else:
            child_flag = 0
        output_routing = {
            "data": order_info.routing.routing_key,
            "adultPrice": order_info.routing.adult_price_forsale,
            "adultTax": order_info.routing.adult_tax,
            "childPrice": order_info.routing.child_price_forsale,
            "childTax": order_info.routing.child_tax,
            "childFlag": child_flag,
            "infantPrice": order_info.routing.child_price,
            "infantTax": order_info.routing.child_tax,  # TODO 暂时与儿童票相同
            "currency": "CNY",
            "nationalityType": 0,
            "nationality": "CN",
            "suitAge": "",
            "priceType": 0,
            "applyType": 0,
            "adultTaxType": 0,
            "childTaxType": 0,
            "infantTaxType": 0,
            "ticketingCarrier": order_info.routing.from_segments[0].carrier,
            "fromSegments": [],
            "rule": {
                "refund": "不可退票",
                "endorse": "不可改签",
                "baggage": "以航司规则为准",
                "other": ""
            },
            "retSegments": []
        }
        if order_info.routing.segment_min_cabin_count > 9:
            cabin_count = 10
        else:
            cabin_count = order_info.routing.segment_min_cabin_count

        for flight_segment in order_info.routing.from_segments:


            output_segment = {
                "flightOption": 1,
                "carrier": flight_segment.carrier,
                "depAirport": flight_segment.dep_airport,
                "depTime": datetime.datetime.strptime(flight_segment.dep_time, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'),
                "arrAirport": flight_segment.arr_airport,
                "arrTime": datetime.datetime.strptime(flight_segment.arr_time, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'),
                "stopCities": flight_segment.stop_cities,
                "codeShare": False,
                "cabinCode": flight_segment.cabin,
                "seatCount": cabin_count,
                "aircraftCode": "",
                "flightNumber": flight_segment.flight_number,
                "departureTerminal": flight_segment.dep_terminal if not re.match(u'[\u4e00-\u9fa5]+',
                                                                            flight_segment.dep_terminal) else '',
                "arrivingTerminal": flight_segment.arr_terminal if not re.match(u'[\u4e00-\u9fa5]+',
                                                                            flight_segment.arr_terminal) else '',

                "cabinClass": cg_map[flight_segment.cabin_grade],
            }
            output_routing['fromSegments'].append(output_segment)

        for flight_segment in order_info.routing.ret_segments:


            output_segment = {
                "flightOption": 1,
                "carrier": flight_segment.carrier,
                "depAirport": flight_segment.dep_airport,
                "depTime": datetime.datetime.strptime(flight_segment.dep_time, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'),
                "arrAirport": flight_segment.arr_airport,
                "arrTime": datetime.datetime.strptime(flight_segment.arr_time, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'),
                "stopCities": flight_segment.stop_cities,
                "codeShare": False,
                "cabinCode": flight_segment.cabin,
                "seatCount": cabin_count,
                "aircraftCode": "",
                "flightNumber": flight_segment.flight_number,
                "departureTerminal": flight_segment.dep_terminal if not re.match(u'[\u4e00-\u9fa5]+',
                                                                            flight_segment.dep_terminal) else '',
                "arrivingTerminal": flight_segment.arr_terminal if not re.match(u'[\u4e00-\u9fa5]+',
                                                                            flight_segment.arr_terminal) else '',

                "cabinClass": cg_map[flight_segment.cabin_grade],
            }
            output_routing['retSegments'].append(output_segment)

        ret['routing'] = output_routing

        ret = self.aes_encrypt(json.dumps(ret))
        Logger().debug('aes_encrypt data %s' % ret)
        self.final_result = ret
        return True

    def _before_notice_issue_interface(self, req_body):
        """
        通知出票（支付取消）接口
        :param req_body:
        :return:
        """
        req_body = self.aes_decrypt(req_body)
        req_body = json.loads(req_body)
        self.order_info.ota_order_id = req_body['orderNo']
        self.order_info.session_id =  req_body['sessionId']
        self.order_info.pnr_code = req_body['pnrCode']
        if req_body['action'] == 'CONFIRM':
            self.order_info.ota_order_status = 'READY_TO_ISSUE'
        elif  req_body['action'] == 'CANCEL':
            self.order_info.ota_order_status = 'ISSUE_FAIL'

    def _after_notice_issue_interface(self, order_info):
        if order_info.notice_issue_status == 'INNER_ERROR_7001':
            ret = json.dumps({'status': 1, 'msg': ERROR_STATUS[order_info.notice_issue_status],
                              'sessionId': order_info.session_id, "orderNo": order_info.ota_order_id,
                            "pnrCode": order_info.pnr_code})
            ret = self.aes_encrypt(ret)
            self.final_result = ret
            return False
        elif order_info.notice_issue_status == 'INNER_ERROR_7002':
            ret = json.dumps({'status': 2, 'msg': ERROR_STATUS[order_info.notice_issue_status],
                              'sessionId': order_info.session_id, "orderNo": order_info.ota_order_id,
                            "pnrCode": order_info.pnr_code})
            ret = self.aes_encrypt(ret)
            self.final_result = ret
            return False
        else:
            ret = {
                "status": 0,
                "msg": "成功",
                "sessionId": order_info.session_id,
                "orderNo": order_info.ota_order_id,
                "pnrCode": order_info.pnr_code
            }
            Logger().info('raw data %s' % ret)
            ret = self.aes_encrypt(json.dumps(ret))
            self.final_result = ret
            return True

    def _before_order_detail_interface(self, req_body):
        """

        :param req_body:
        :return:
        """
        req_body = self.aes_decrypt(req_body)
        req_body = json.loads(req_body)
        self.order_info.ota_order_id = req_body['orderNo']


    def _after_order_detail_interface(self, order_info):
        """

        :param
        :return:
        """
        if order_info.order_detail_status == 'INNER_ERROR_5001':
            ret = json.dumps({'status':order_info.order_detail_status,'msg':ERROR_STATUS[order_info.order_detail_status]})
            ret = self.aes_encrypt(ret)
            self.final_result = self.aes_encrypt(ret)
            return False
        else:

            paxs = []
            for pax_info in order_info.passengers:
                if pax_info.age_type == 'ADT':
                    age_type = 0
                elif pax_info.age_type == 'CHD':
                    age_type = 1
                elif pax_info.age_type == 'INF':
                    age_type = 2
                else:
                    age_type = 0
                if pax_info.card_expired:
                    card_expired = datetime.datetime.strptime(pax_info.birthdate, '%Y-%m-%d').strftime('%Y%m%d')
                else:
                    card_expired = ''
                output_pax = {
                    'name':"%s/%s"%(pax_info.last_name,pax_info.first_name),
                    'gender':pax_info.gender,
                    'ageType':age_type,
                    'birthday':datetime.datetime.strptime(pax_info.birthdate, '%Y-%m-%d').strftime('%Y%m%d'),
                    'cardType':pax_info.used_card_type,
                    'cardNum':pax_info.used_card_no,
                    'pnrCode':order_info.pnr_code,
                    'ticketNo':pax_info.ticket_no.replace('-', ''),
                    'cardIssuePlace':pax_info.card_issue_place,
                    'cardExpired':card_expired,
                    'nationality':pax_info.nationality,
                }
                paxs.append(output_pax)

            if PROVIDERS_STATUS[order_info.providers_status]['status_category']== 'ISSUE_SUCCESS':
                order_status = 1
            elif PROVIDERS_STATUS[order_info.providers_status]['status_category']== 'ISSUE_PROCESS':
                order_status = 2
            elif  PROVIDERS_STATUS[order_info.providers_status]['status_category']== 'ISSUE_CANCEL':
                order_status = 3
            else:
                order_status = 4


            ret = {
                'status':0,
                'msg':'成功',
                'orderNo':order_info.ota_order_id,
                'pnrFlag':0,
                'orderStatus':order_status,
                'passengers':paxs,

            }
            Logger().info('raw data %s' % ret)
            ret = self.aes_encrypt(json.dumps(ret))
            self.final_result = ret
            return True

    def _verify_boost(self):

        http_session = HttpRequest()

        times = int(TBG.redis_conn.redis_pool.get('tuniu_verify_boost_times') or 5)
        for i in xrange(times):
            headers = {
                'Host': 'super.tuniu.com',
                'Pragma': 'no-cache',
                'Cache-Control': 'no-cache',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Origin': 'http://super.tuniu.com',
                'X-Requested-With': 'XMLHttpRequest',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Referer': 'http://super.tuniu.com/flight/200/44759-1/2019-04-18/1-0-1/',
                'Accept-Encoding': 'gzip, deflate',
                'Accept-Language': 'en-GB,en;q=0.9,en-US;q=0.8,zh-CN;q=0.7,zh;q=0.6',
            }

            user_key = '2fqo69jeqp44fmn3vl33{}'.format(random.randint(100000, 999999))
            http_session.update_cookie({
                'user-key': user_key,
                'OLBSESSID': user_key,
                'tuniu_partner': base64.b64encode(
                    '101,0,,9fd82e8ca6d4c019fe5277eb2f{}'.format(random.randint(100000, 999999))),
                'tuniuuser_citycode': 'MjAw',
                'p_phone_400': '4007-999-999',
                'p_phone_level': '0',
                'p_global_phone': '%2B0086-25-8685-9999',
                '__utma': '1.258322028.{}.{}.{}.1'.format(int(time.time()), int(time.time()), int(time.time())),
                '__utmc': '1',
                '__utmz': '1.{}.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none)'.format(int(time.time())),
                '__utmb': '1.1.10.{}'.format(int(time.time())),
                '_tacau': base64.b64encode(
                    '0,208eaf0c-2cbc-95fc-0dcd-e18fab{},'.format(random.randint(100000, 999999))),
                '_tact': base64.b64encode('04b34b8b-8476-c7b6-6c5d-450799{}'.format(random.randint(100000, 999999))),
                '_tacz2': 'taccsr%3D%28direct%29%7Ctacccn%3D%28none%29%7Ctaccmd%3D%28none%29%7Ctaccct%3D%28none%29%7Ctaccrt%3D%28none%29',
                '_taca': '{}.{}.{}.1'.format(int(time.time() * 1000), int(time.time() * 1000), int(time.time() * 1000)),
                '_tacb': base64.b64encode('186dc80d-72fe-67c7-d099-7d63{}'.format(random.randint(10000000, 99999999))),
                '_tacc': '1',
            })

            day_list = [
                    '2019-05-07',
                    '2019-05-23',
                    '2019-05-24',
                    '2019-05-25',
                    '2019-06-03',
                    '2019-06-04',
                    '2019-06-09',
                    '2019-06-10',
            ]

            flight_date = random.choice(day_list)
            flight_date_plus = datetime.datetime.strftime(datetime.datetime.strptime(
                flight_date, '%Y-%m-%d') + datetime.timedelta(days=1), '%Y-%m-%d')

            post_data = {
                "journey": [{
                    "primary": {
                        "departureCityCode": 3104,
                        "departureCity": "阿勒泰",
                        "arrivalCityCode": 1741916,
                        "arrivalCity": "马德里",
                        "departsDate": flight_date,
                        "arrivalNationType": 1,
                        "departureNationType": 2,
                        "nationType": 1
                    }, "journeyRph": 1
                }],
                "adultNumber": 1,
                "childNumber": 0,
                "searchType": 1,
            }
            post_data = {'postData': json.dumps(post_data)}
            url = 'http://super.tuniu.com/tn?r=supdiy/planeAjax/getIndividualFlight'
            result = http_session.request(url=url, method='POST', headers=headers, data=post_data, proxy_pool='A')
            # Logger().info(result.content)
            time.sleep(1)

            result = json.loads(result.content)
            routing_seg = result['data']['rows'][0]['rows'][-1]
            query_id = result['data']['queryId']
            resource_key = routing_seg['prices'][0]['resourceKey']

            post_data = {
                'postData[resType]': 'flight',
                'postData[res][flight][res_{}_{}_{}][resId]'.format(resource_key, flight_date.replace('-', ''),
                                                                    flight_date_plus.replace('-', '')): resource_key,
                'postData[res][flight][res_{}_{}_{}][resType]'.format(resource_key, flight_date.replace('-', ''),
                                                                      flight_date_plus.replace('-', '')):
                    routing_seg['prices'][0]['resourceType'],
                # 'postData[res][flight][res_{}_{}_{}][resType]'.format(resource_key, flight_date.replace('-', ''), flight_date_plus.replace('-', '')): 21,

                'postData[res][flight][res_{}_{}_{}][type]'.format(resource_key, flight_date.replace('-', ''),
                                                                   flight_date_plus.replace('-', '')):
                    routing_seg['prices'][0]['resourceSubType'],
                # 'postData[res][flight][res_{}_{}_{}][type]'.format(resource_key, flight_date.replace('-', ''), flight_date_plus.replace('-', '')): 3,
                'postData[res][flight][res_{}_{}_{}][flightId]'.format(resource_key, flight_date.replace('-', ''),
                                                                       flight_date_plus.replace('-', '')): 'PG866',
                'postData[res][flight][res_{}_{}_{}][id]'.format(resource_key, flight_date.replace('-', ''),
                                                                 flight_date_plus.replace('-', '')): resource_key,
                'postData[res][flight][res_{}_{}_{}][date]'.format(resource_key, flight_date.replace('-', ''),
                                                                   flight_date_plus.replace('-', '')): flight_date,
                'postData[res][flight][res_{}_{}_{}][startDate]'.format(resource_key, flight_date.replace('-', ''),
                                                                        flight_date_plus.replace('-', '')): flight_date,
                'postData[res][flight][res_{}_{}_{}][endDate]'.format(resource_key, flight_date.replace('-', ''),
                                                                      flight_date_plus.replace('-',
                                                                                               '')): flight_date_plus,
                'postData[res][flight][res_{}_{}_{}][departName]'.format(resource_key, flight_date.replace('-', ''),
                                                                         flight_date_plus.replace('-', '')): '阿勒泰',
                'postData[res][flight][res_{}_{}_{}][departCode]'.format(resource_key, flight_date.replace('-', ''),
                                                                         flight_date_plus.replace('-', '')): 3104,
                'postData[res][flight][res_{}_{}_{}][destName]'.format(resource_key, flight_date.replace('-', ''),
                                                                       flight_date_plus.replace('-', '')): '马德里',
                'postData[res][flight][res_{}_{}_{}][destCode]'.format(resource_key, flight_date.replace('-', ''),
                                                                       flight_date_plus.replace('-', '')): 1741916,
                'postData[res][flight][res_{}_{}_{}][adultPrice]'.format(resource_key, flight_date.replace('-', ''),
                                                                         flight_date_plus.replace('-', '')): int(
                    routing_seg['prices'][0]['adultPrice']),
                # 'postData[res][flight][res_{}_{}_{}][adultPrice]'.format(resource_key, flight_date.replace('-', ''), flight_date_plus.replace('-', '')): 184012,
                'postData[res][flight][res_{}_{}_{}][childPrice]'.format(resource_key, flight_date.replace('-', ''),
                                                                         flight_date_plus.replace('-', '')):
                    routing_seg['prices'][0]['childPrice'],
                # 'postData[res][flight][res_{}_{}_{}][childPrice]'.format(resource_key, flight_date.replace('-', ''), flight_date_plus.replace('-', '')): 0,
                'postData[res][flight][res_{}_{}_{}][singleAdultPrice]'.format(resource_key,
                                                                               flight_date.replace('-', ''),
                                                                               flight_date_plus.replace('-', '')): int(
                    routing_seg['prices'][0]['singleAdultPrice']),
                # 'postData[res][flight][res_{}_{}_{}][singleAdultPrice]'.format(resource_key, flight_date.replace('-', ''), flight_date_plus.replace('-', '')): 184012,
                'postData[res][flight][res_{}_{}_{}][singleChildPrice]'.format(resource_key,
                                                                               flight_date.replace('-', ''),
                                                                               flight_date_plus.replace('-', '')):
                    routing_seg['prices'][0]['singleChildPrice'],
                # 'postData[res][flight][res_{}_{}_{}][singleChildPrice]'.format(resource_key, flight_date.replace('-', ''), flight_date_plus.replace('-', '')): 0,
                'postData[res][flight][res_{}_{}_{}][adultDiscount]'.format(resource_key, flight_date.replace('-', ''),
                                                                            flight_date_plus.replace('-', '')): 0,
                'postData[res][flight][res_{}_{}_{}][childDiscount]'.format(resource_key, flight_date.replace('-', ''),
                                                                            flight_date_plus.replace('-', '')): 0,
                'postData[res][flight][res_{}_{}_{}][isInter]'.format(resource_key, flight_date.replace('-', ''),
                                                                      flight_date_plus.replace('-', '')): 1,
                'postData[res][flight][res_{}_{}_{}][cabinName]'.format(resource_key, flight_date.replace('-', ''),
                                                                        flight_date_plus.replace('-', '')): '经济舱',
                'postData[res][flight][res_{}_{}_{}][adultTaxes]'.format(resource_key, flight_date.replace('-', ''),
                                                                         flight_date_plus.replace('-', '')): int(
                    routing_seg['prices'][0]['adultTaxes']),
                # 'postData[res][flight][res_{}_{}_{}][adultTaxes]'.format(resource_key, flight_date.replace('-', ''), flight_date_plus.replace('-', '')): 12852,
                'postData[res][flight][res_{}_{}_{}][childTaxes]'.format(resource_key, flight_date.replace('-', ''),
                                                                         flight_date_plus.replace('-', '')): int(
                    routing_seg['prices'][0]['childTaxes']),
                # 'postData[res][flight][res_{}_{}_{}][childTaxes]'.format(resource_key, flight_date.replace('-', ''), flight_date_plus.replace('-', '')): 0,
                'postData[res][flight][res_{}_{}_{}][inftTaxes]'.format(resource_key, flight_date.replace('-', ''),
                                                                        flight_date_plus.replace('-', '')): int(
                    routing_seg['prices'][0]['inftTaxes']),
                # 'postData[res][flight][res_{}_{}_{}][inftTaxes]'.format(resource_key, flight_date.replace('-', ''), flight_date_plus.replace('-', '')): 0,
                'postData[res][flight][res_{}_{}_{}][queryId]'.format(resource_key, flight_date.replace('-', ''),
                                                                      flight_date_plus.replace('-', '')): query_id,
                'postData[res][flight][res_{}_{}_{}][from][startDate]'.format(resource_key,
                                                                              flight_date.replace('-', ''),
                                                                              flight_date_plus.replace('-',
                                                                                                       '')): flight_date,
                'postData[res][flight][res_{}_{}_{}][from][endDate]'.format(resource_key, flight_date.replace('-', ''),
                                                                            flight_date_plus.replace('-',
                                                                                                     '')): flight_date_plus,
                'postData[res][flight][res_{}_{}_{}][from][departName]'.format(resource_key,
                                                                               flight_date.replace('-', ''),
                                                                               flight_date_plus.replace('-',
                                                                                                        '')): '阿勒泰',
                'postData[res][flight][res_{}_{}_{}][from][departCode]'.format(resource_key,
                                                                               flight_date.replace('-', ''),
                                                                               flight_date_plus.replace('-', '')): 3104,
                'postData[res][flight][res_{}_{}_{}][from][destName]'.format(resource_key, flight_date.replace('-', ''),
                                                                             flight_date_plus.replace('-', '')): '马德里',
                'postData[res][flight][res_{}_{}_{}][from][destCode]'.format(resource_key, flight_date.replace('-', ''),
                                                                             flight_date_plus.replace('-',
                                                                                                      '')): 1741916,
                'postData[res][flight][res_{}_{}_{}][from][startTime]'.format(resource_key,
                                                                              flight_date.replace('-', ''),
                                                                              flight_date_plus.replace('-',
                                                                                                       '')): '10:00',
                'postData[res][flight][res_{}_{}_{}][from][endTime]'.format(resource_key, flight_date.replace('-', ''),
                                                                            flight_date_plus.replace('-', '')): '20:00',
                'postData[res][flight][res_{}_{}_{}][from][departPort]'.format(resource_key,
                                                                               flight_date.replace('-', ''),
                                                                               flight_date_plus.replace('-',
                                                                                                        '')): '阿勒泰机场',
                'postData[res][flight][res_{}_{}_{}][from][destPort]'.format(resource_key, flight_date.replace('-', ''),
                                                                             flight_date_plus.replace('-',
                                                                                                      '')): '马德里机场',
                'postData[res][flight][res_{}_{}_{}][from][company]'.format(resource_key, flight_date.replace('-', ''),
                                                                            flight_date_plus.replace('-', '')): '曼谷航空',
                'postData[res][flight][res_{}_{}_{}][from][flightNo]'.format(resource_key, flight_date.replace('-', ''),
                                                                             flight_date_plus.replace('-',
                                                                                                      '')): 'PG866',
                'postData[res][flight][res_{}_{}_{}][from][isTransit]'.format(resource_key,
                                                                              flight_date.replace('-', ''),
                                                                              flight_date_plus.replace('-', '')): 1,
                'postData[res][flight][res_{}_{}_{}][from][journeyDuration]'.format(resource_key,
                                                                                    flight_date.replace('-', ''),
                                                                                    flight_date_plus.replace('-',
                                                                                                             '')): '40h',
                'postData[res][flight][res_{}_{}_{}][from][moreDays]'.format(resource_key, flight_date.replace('-', ''),
                                                                             flight_date_plus.replace('-', '')): 1,
                'postData[res][flight][res_{}_{}_{}][from][remark]'.format(resource_key, flight_date.replace('-', ''),
                                                                           flight_date_plus.replace('-', '')): '',
                'postData[res][flight][res_{}_{}_{}][from][resourceKey]'.format(resource_key,
                                                                                flight_date.replace('-', ''),
                                                                                flight_date_plus.replace('-',
                                                                                                         '')): resource_key,
                'postData[res][flight][res_{}_{}_{}][from][flightItems][0][flightNo]'.format(resource_key,
                                                                                             flight_date.replace('-',
                                                                                                                 ''),
                                                                                             flight_date_plus.replace(
                                                                                                 '-', '')): 'PG866',
                'postData[res][flight][res_{}_{}_{}][from][flightItems][0][dCityIataCode]'.format(resource_key,
                                                                                                  flight_date.replace(
                                                                                                      '-', ''),
                                                                                                  flight_date_plus.replace(
                                                                                                      '-', '')): '',
                'postData[res][flight][res_{}_{}_{}][from][flightItems][0][aCityIataCode]'.format(resource_key,
                                                                                                  flight_date.replace(
                                                                                                      '-', ''),
                                                                                                  flight_date_plus.replace(
                                                                                                      '-', '')): '',
                'postData[res][flight][res_{}_{}_{}][from][flightItems][1][flightNo]'.format(resource_key,
                                                                                             flight_date.replace('-',
                                                                                                                 ''),
                                                                                             flight_date_plus.replace(
                                                                                                 '-', '')): 'TG973',
                'postData[res][flight][res_{}_{}_{}][from][flightItems][1][dCityIataCode]'.format(resource_key,
                                                                                                  flight_date.replace(
                                                                                                      '-', ''),
                                                                                                  flight_date_plus.replace(
                                                                                                      '-', '')): '',
                'postData[res][flight][res_{}_{}_{}][from][flightItems][1][aCityIataCode]'.format(resource_key,
                                                                                                  flight_date.replace(
                                                                                                      '-', ''),
                                                                                                  flight_date_plus.replace(
                                                                                                      '-', '')): '',
                'postData[res][flight][res_{}_{}_{}][from][flightItems][2][flightNo]'.format(resource_key,
                                                                                             flight_date.replace('-',
                                                                                                                 ''),
                                                                                             flight_date_plus.replace(
                                                                                                 '-', '')): 'SN440',
                'postData[res][flight][res_{}_{}_{}][from][flightItems][2][dCityIataCode]'.format(resource_key,
                                                                                                  flight_date.replace(
                                                                                                      '-', ''),
                                                                                                  flight_date_plus.replace(
                                                                                                      '-', '')): '',
                'postData[res][flight][res_{}_{}_{}][from][flightItems][2][aCityIataCode]'.format(resource_key,
                                                                                                  flight_date.replace(
                                                                                                      '-', ''),
                                                                                                  flight_date_plus.replace(
                                                                                                      '-', '')): '',
                'postData[res][flight][res_{}_{}_{}][from][transitInfo][]'.format(resource_key,
                                                                                  flight_date.replace('-', ''),
                                                                                  flight_date_plus.replace('-',
                                                                                                           '')): '中转:曼谷  停留时长:6小时30分钟',
                'postData[res][flight][res_{}_{}_{}][from][transitInfo][]'.format(resource_key,
                                                                                  flight_date.replace('-', ''),
                                                                                  flight_date_plus.replace('-',
                                                                                                           '')): '中转:布鲁塞尔  停留时长:3小时',
                'postData[res][flight][res_{}_{}_{}][from][stopTip]'.format(resource_key, flight_date.replace('-', ''),
                                                                            flight_date_plus.replace('-', '')): '',
                'postData[res][flight][res_{}_{}_{}][from][flightType]'.format(resource_key,
                                                                               flight_date.replace('-', ''),
                                                                               flight_date_plus.replace('-',
                                                                                                        '')): '机型未定',
                'postData[res][flight][res_{}_{}_{}][from][detail][0][start]'.format(resource_key,
                                                                                     flight_date.replace('-', ''),
                                                                                     flight_date_plus.replace('-',
                                                                                                              '')): '10:00',
                'postData[res][flight][res_{}_{}_{}][from][detail][0][depart]'.format(resource_key,
                                                                                      flight_date.replace('-', ''),
                                                                                      flight_date_plus.replace('-',
                                                                                                               '')): '阿勒泰',
                'postData[res][flight][res_{}_{}_{}][from][detail][0][duration]'.format(resource_key,
                                                                                        flight_date.replace('-', ''),
                                                                                        flight_date_plus.replace('-',
                                                                                                                 '')): '9h',
                'postData[res][flight][res_{}_{}_{}][from][detail][0][end]'.format(resource_key,
                                                                                   flight_date.replace('-', ''),
                                                                                   flight_date_plus.replace('-',
                                                                                                            '')): '18:00',
                'postData[res][flight][res_{}_{}_{}][from][detail][0][dest]'.format(resource_key,
                                                                                    flight_date.replace('-', ''),
                                                                                    flight_date_plus.replace('-',
                                                                                                             '')): '曼谷',
                'postData[res][flight][res_{}_{}_{}][from][detail][0][com]'.format(resource_key,
                                                                                   flight_date.replace('-', ''),
                                                                                   flight_date_plus.replace('-',
                                                                                                            '')): '曼谷航空',
                'postData[res][flight][res_{}_{}_{}][from][detail][0][no]'.format(resource_key,
                                                                                  flight_date.replace('-', ''),
                                                                                  flight_date_plus.replace('-',
                                                                                                           '')): 'PG866',
                'postData[res][flight][res_{}_{}_{}][from][detail][0][type]'.format(resource_key,
                                                                                    flight_date.replace('-', ''),
                                                                                    flight_date_plus.replace('-',
                                                                                                             '')): '机型未定',
                'postData[res][flight][res_{}_{}_{}][from][detail][1][start]'.format(resource_key,
                                                                                     flight_date.replace('-', ''),
                                                                                     flight_date_plus.replace('-',
                                                                                                              '')): '00:30',
                'postData[res][flight][res_{}_{}_{}][from][detail][1][depart]'.format(resource_key,
                                                                                      flight_date.replace('-', ''),
                                                                                      flight_date_plus.replace('-',
                                                                                                               '')): '曼谷',
                'postData[res][flight][res_{}_{}_{}][from][detail][1][duration]'.format(resource_key,
                                                                                        flight_date.replace('-', ''),
                                                                                        flight_date_plus.replace('-',
                                                                                                                 '')): '16h30m',
                'postData[res][flight][res_{}_{}_{}][from][detail][1][end]'.format(resource_key,
                                                                                   flight_date.replace('-', ''),
                                                                                   flight_date_plus.replace('-',
                                                                                                            '')): '11:00',
                'postData[res][flight][res_{}_{}_{}][from][detail][1][dest]'.format(resource_key,
                                                                                    flight_date.replace('-', ''),
                                                                                    flight_date_plus.replace('-',
                                                                                                             '')): '布鲁塞尔',
                'postData[res][flight][res_{}_{}_{}][from][detail][1][com]'.format(resource_key,
                                                                                   flight_date.replace('-', ''),
                                                                                   flight_date_plus.replace('-',
                                                                                                            '')): '泰国航空',
                'postData[res][flight][res_{}_{}_{}][from][detail][1][no]'.format(resource_key,
                                                                                  flight_date.replace('-', ''),
                                                                                  flight_date_plus.replace('-',
                                                                                                           '')): 'TG973',
                'postData[res][flight][res_{}_{}_{}][from][detail][1][type]'.format(resource_key,
                                                                                    flight_date.replace('-', ''),
                                                                                    flight_date_plus.replace('-',
                                                                                                             '')): '机型未定',
                'postData[res][flight][res_{}_{}_{}][from][detail][2][start]'.format(resource_key,
                                                                                     flight_date.replace('-', ''),
                                                                                     flight_date_plus.replace('-',
                                                                                                              '')): '14:00',
                'postData[res][flight][res_{}_{}_{}][from][detail][2][depart]'.format(resource_key,
                                                                                      flight_date.replace('-', ''),
                                                                                      flight_date_plus.replace('-',
                                                                                                               '')): '布鲁塞尔',
                'postData[res][flight][res_{}_{}_{}][from][detail][2][duration]'.format(resource_key,
                                                                                        flight_date.replace('-', ''),
                                                                                        flight_date_plus.replace('-',
                                                                                                                 '')): '5h',
                'postData[res][flight][res_{}_{}_{}][from][detail][2][end]'.format(resource_key,
                                                                                   flight_date.replace('-', ''),
                                                                                   flight_date_plus.replace('-',
                                                                                                            '')): '20:00',
                'postData[res][flight][res_{}_{}_{}][from][detail][2][dest]'.format(resource_key,
                                                                                    flight_date.replace('-', ''),
                                                                                    flight_date_plus.replace('-',
                                                                                                             '')): '马德里',
                'postData[res][flight][res_{}_{}_{}][from][detail][2][com]'.format(resource_key,
                                                                                   flight_date.replace('-', ''),
                                                                                   flight_date_plus.replace('-',
                                                                                                            '')): '布鲁塞尔航空',
                'postData[res][flight][res_{}_{}_{}][from][detail][2][no]'.format(resource_key,
                                                                                  flight_date.replace('-', ''),
                                                                                  flight_date_plus.replace('-',
                                                                                                           '')): 'SN440',
                'postData[res][flight][res_{}_{}_{}][from][detail][2][type]'.format(resource_key,
                                                                                    flight_date.replace('-', ''),
                                                                                    flight_date_plus.replace('-',
                                                                                                             '')): '机型未定',
                'postData[res][flight][res_{}_{}_{}][from][priceInfo][seatCode]'.format(resource_key,
                                                                                        flight_date.replace('-', ''),
                                                                                        flight_date_plus.replace('-',
                                                                                                                 '')): '',
                'postData[res][flight][res_{}_{}_{}][from][priceInfo][seatTypeCode]'.format(resource_key,
                                                                                            flight_date.replace('-',
                                                                                                                ''),
                                                                                            flight_date_plus.replace(
                                                                                                '-', '')): 1,
                'postData[res][flight][res_{}_{}_{}][from][priceInfo][vendorId]'.format(resource_key,
                                                                                        flight_date.replace('-', ''),
                                                                                        flight_date_plus.replace('-',
                                                                                                                 '')):
                    routing_seg['prices'][0]['vendorId'],
                # 'postData[res][flight][res_{}_{}_{}][from][priceInfo][vendorId]'.format(resource_key, flight_date.replace('-', ''), flight_date_plus.replace('-', '')): 93,

                'postData[res][flight][res_{}_{}_{}][from][priceInfo][policyId]'.format(resource_key,
                                                                                        flight_date.replace('-', ''),
                                                                                        flight_date_plus.replace('-',
                                                                                                                 '')): '',
                'postData[res][flight][res_{}_{}_{}][from][priceInfo][externalInfo]'.format(resource_key,
                                                                                            flight_date.replace('-',
                                                                                                                ''),
                                                                                            flight_date_plus.replace(
                                                                                                '-', '')): '',
                'postData[res][flight][res_{}_{}_{}][from][priceInfo][resourceKey]'.format(resource_key,
                                                                                           flight_date.replace('-', ''),
                                                                                           flight_date_plus.replace('-',
                                                                                                                    '')): resource_key,
                'postData[res][flight][res_{}_{}_{}][from][priceInfo][saleControl][minPassengerNum]'.format(
                    resource_key, flight_date.replace('-', ''), flight_date_plus.replace('-', '')): 0,
                'postData[res][flight][res_{}_{}_{}][from][priceInfo][saleControl][maxPassengerNum]'.format(
                    resource_key, flight_date.replace('-', ''), flight_date_plus.replace('-', '')): 0,
                'postData[res][flight][res_{}_{}_{}][from][priceInfo][saleControl][corePassengerNum]'.format(
                    resource_key, flight_date.replace('-', ''), flight_date_plus.replace('-', '')): 0,
                'postData[res][flight][res_{}_{}_{}][from][priceInfo][saleControl][passengerAgeLimit]'.format(
                    resource_key, flight_date.replace('-', ''), flight_date_plus.replace('-', '')): 0,
                'postData[res][flight][res_{}_{}_{}][from][priceInfo][saleControl][acceptableIDCardType]'.format(
                    resource_key, flight_date.replace('-', ''), flight_date_plus.replace('-', '')): '',
                'postData[res][flight][res_{}_{}_{}][from][priceInfo][saleControl][applicableTravelerCategory]'.format(
                    resource_key, flight_date.replace('-', ''), flight_date_plus.replace('-', '')): '',
                'postData[res][flight][res_{}_{}_{}][from][priceInfo][saleControl][maxAdultNum]'.format(resource_key,
                                                                                                        flight_date.replace(
                                                                                                            '-', ''),
                                                                                                        flight_date_plus.replace(
                                                                                                            '-',
                                                                                                            '')): 0,
                'postData[res][flight][res_{}_{}_{}][from][priceInfo][saleControl][minAdultNum]'.format(resource_key,
                                                                                                        flight_date.replace(
                                                                                                            '-', ''),
                                                                                                        flight_date_plus.replace(
                                                                                                            '-',
                                                                                                            '')): 0,
                'postData[res][flight][res_{}_{}_{}][from][priceInfo][saleControl][maxChildNum]'.format(resource_key,
                                                                                                        flight_date.replace(
                                                                                                            '-', ''),
                                                                                                        flight_date_plus.replace(
                                                                                                            '-',
                                                                                                            '')): 0,
                'postData[res][flight][res_{}_{}_{}][from][priceInfo][saleControl][minChildNum]'.format(resource_key,
                                                                                                        flight_date.replace(
                                                                                                            '-', ''),
                                                                                                        flight_date_plus.replace(
                                                                                                            '-',
                                                                                                            '')): 0,
                'postData[res][flight][res_{}_{}_{}][from][priceInfo][saleControl][babyNum]'.format(resource_key,
                                                                                                    flight_date.replace(
                                                                                                        '-', ''),
                                                                                                    flight_date_plus.replace(
                                                                                                        '-', '')): 0,
                'postData[res][flight][res_{}_{}_{}][from][priceInfo][saleControl][passengerRatio]'.format(resource_key,
                                                                                                           flight_date.replace(
                                                                                                               '-', ''),
                                                                                                           flight_date_plus.replace(
                                                                                                               '-',
                                                                                                               '')): '',
                'postData[res][flight][res_{}_{}_{}][from][priceInfo][saleControl][advanceDays]'.format(resource_key,
                                                                                                        flight_date.replace(
                                                                                                            '-', ''),
                                                                                                        flight_date_plus.replace(
                                                                                                            '-',
                                                                                                            '')): 0,
                'postData[res][flight][res_{}_{}_{}][from][priceInfo][saleControl][saleLimitedTime]'.format(
                    resource_key, flight_date.replace('-', ''), flight_date_plus.replace('-', '')): 0,
                'postData[res][flight][res_{}_{}_{}][from][priceInfo][saleControl][acptSpec]'.format(resource_key,
                                                                                                     flight_date.replace(
                                                                                                         '-', ''),
                                                                                                     flight_date_plus.replace(
                                                                                                         '-', '')): '',
                'postData[res][flight][res_{}_{}_{}][from][priceInfo][saleControl][acptPayCardType]'.format(
                    resource_key, flight_date.replace('-', ''), flight_date_plus.replace('-', '')): '',
                'postData[res][flight][res_{}_{}_{}][solutionId]'.format(resource_key, flight_date.replace('-', ''),
                                                                         flight_date_plus.replace('-', '')):
                    routing_seg['prices'][0]['vendorId'],
                # 'postData[res][flight][res_{}_{}_{}][solutionId]'.format(resource_key, flight_date.replace('-', ''), flight_date_plus.replace('-', '')): 93,

                'postData[res][flight][res_{}_{}_{}][adult]'.format(resource_key, flight_date.replace('-', ''),
                                                                    flight_date_plus.replace('-', '')): 1,
                'postData[res][flight][res_{}_{}_{}][child]'.format(resource_key, flight_date.replace('-', ''),
                                                                    flight_date_plus.replace('-', '')): 0,
                'postData[res][flight][res_{}_{}_{}][realId]'.format(resource_key, flight_date.replace('-', ''),
                                                                     flight_date_plus.replace('-',
                                                                                              '')): 'res_{}_{}_{}'.format(
                    resource_key, flight_date.replace('-', ''), flight_date_plus.replace('-', '')),
            }

            url = 'http://super.tuniu.com/tn?r=supdiy/shopCart/AddCartItem'
            result = http_session.request(url=url, method='POST', data=post_data, proxy_pool='A')
            # Logger().info(result.content)

            time.sleep(1)

            url = 'http://super.tuniu.com/tn?r=supdiy/shopCart/GetCartInfo&postData%5Bcheck%5D=true'
            result = http_session.request(url=url, method='GET', proxy_pool='A')
            result = json.loads(result.content)
            for i in result['data']['res']:
                Logger().info("*****************************************")
                Logger().info(result['data']['res'][i]['resId'])
                break


if __name__ == '__main__':
    pass
