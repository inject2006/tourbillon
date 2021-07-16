#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gevent
import json
import datetime
import random
import string
from .base import ProvderAutoBase
from ..dao.internal import *
from ..utils.util import simple_encrypt, RoutingKey
from ..controller.captcha import CaptchaCracker
from app import TBG


class Donghaiair(ProvderAutoBase):
    timeout = 50  # 请求超时时间
    provider = 'donghaiair'  # 子类继承必须赋
    provider_channel = 'donghaiair_web'  # 子类继承必须赋
    operation_product_type = '会员折扣'  # 运价类型：0: GDS公布运价 1:GDS私有运价 2:航司官网产品  3:廉价航司产品 4:特价产品
    operation_product_mode = 'A2B'
    pay_channel = 'ALIPAY'
    is_display = True
    is_include_booking_module = True  # 是否包含下单模块
    no_flight_ttl = 3600 * 3 # 无航班缓存超时时间设定
    carrier_list = ['DZ']  # 供应商所包含的航司列表，如果包含多个并且无法确定，请不要填写，此处会关联执飞航线判断逻辑


    CACHE_PR_CONFIG = {
        1: {'cabin_expired_time': 3600 * 12, 'cabin_attenuation': 3,'fare_expired_time':86400 * 30},
        2: {'cabin_expired_time': 3600 * 3, 'cabin_attenuation': 2,'fare_expired_time':86400 * 20},
        3: {'cabin_expired_time': 60 * 60 * 1, 'cabin_attenuation': 1,'fare_expired_time':86400 * 10},
        4: {'cabin_expired_time': 60 * 40, 'cabin_attenuation': 1,'fare_expired_time':86400 * 5},
        5: {'cabin_expired_time': 60 * 30, 'cabin_attenuation': 0,'fare_expired_time':86400},

    }
    search_interval_time = 0


    def __init__(self):
        super(Donghaiair, self).__init__()

        self.booking_retries = 3
        self.ota_fare_search_tries = 5
        self.flight_search_tries = 5

        self.account_list = [
            {
                'username': '630131222@qq.com',
                'password': 'bigsec@2018',
            },
            {
                'username': 'xp.wang@bigsec.com',
                'password': 'bigsec@2018',
            },
            {'username': 'rest@btbvs.com'   , 'password':  'ljf$V(F<(jfs'},
            {'username': '6613c@btbvs.com'  , 'password':  '1ck30ck2.$)&'},
            {'username': 'coco@btbvs.com'   , 'password':  'comcomcom`22'},
            {'username': 'one@btbvs.com'    , 'password':  'ikmm1221,c12'},
            {'username': 'two@btbvs.com'    , 'password':  '123d19*>^lds'},
            {'username': 'three@btbvs.com'  , 'password':   '283&)^<ldlc'},
            {'username': 'thesky@btbvs.com' , 'password': '2n91,KD&*c1'},
            {'username': 'big@btbvs.com'    , 'password':  'c810`8^<To1s'},
            {'username': 'work@btbvs.com'   , 'password':  '18d(&NTLFqc'},
            {'username': 'start@btbvs.com'  , 'password':  '83m^*JF)JRO'},
            {'username': 'bgs@btbvs.com'    , 'password':  '812kc%$(<FLB'},
            {'username': 'bgm@btbvs.com'    , 'password':  '1297kG%%(<VF'},
            {'username': 'rick@btbvs.com'   , 'password':  '19d938FHLV%D'},
            {'username': 'power@btbvs.com'  , 'password':  '239jbs612O*B'},
            {'username': 'find@btbvs.com'   , 'password':  'di3dbg9^%VTI'},
            {'username': 'gotest@btbvs.com' , 'password':  '1816dk1*%H$F'},
        ]
        if not TBG.redis_conn.redis_pool.llen('donghaiair_account_list') == len(self.account_list):
            TBG.redis_conn.redis_pool.expire('donghaiair_account_list', 0)
            for account in self.account_list:
                TBG.redis_conn.redis_pool.lpush('donghaiair_account_list', account)


    def _pre_order_check(self, http_session, order_info):
        """
        订单预检
        :param http_session:
        :param order_info:
        :return:
        """
        return 'CHECK_SUCCESS'

    def _order_split(self, order_info,passengers):
        """
        拆单原则：一个成年人只能带两个小孩，一单最多可以有五个乘机人
        最多拆三单
        :param order_info:
        :return:
        """


        rl = []
        adt_list = [x for x in passengers if x.current_age_type(from_date=order_info.from_date, is_aggr_chd_adt=True) == 'ADT']
        chd_list = [x for x in passengers if x.current_age_type(from_date=order_info.from_date, is_aggr_chd_adt=True) == 'CHD']


        if not chd_list:
            allow_next = True
        else:
            allow_next = False

        sub_order_set = [[], [], []]
        sub_order_index = 0
        while 1:
            if not chd_list:
                break

            for x in range(2):
                if chd_list and len(sub_order_set[sub_order_index]) < 5:
                    sub_order_set[sub_order_index].append(chd_list.pop())
            sub_order_index += 1
            sub_order_index = sub_order_index % 3

        sub_order_index = 0
        while 1:
            Logger().debug('adt_list %s allow_next %s sub_order_index %s  sub_order_set %s'%(adt_list,allow_next,sub_order_index,sub_order_set))
            if not adt_list:
                break
            if allow_next and adt_list:
                sub_order_set[sub_order_index].append(adt_list.pop())
                allow_next = False
            if len(sub_order_set[sub_order_index]) == 5:
                allow_next = True
            elif sub_order_set[sub_order_index] and adt_list:
                sub_order_set[sub_order_index].append(adt_list.pop())
            sub_order_index += 1
            sub_order_index = sub_order_index % 3

        for s in sub_order_set:
            if s:
                rl.append( s)

        Logger().sdebug('split_order %s' % rl)
        return rl

    def _login(self, http_session, ffp_account_info):
        """
        登陆模块
        :return: 登陆成功的httpResult 对象
        """

        url = 'http://b2capi.donghaiair.cn/mem/loginMem'
        post_data = {
            "num": ffp_account_info.username,
            "password": ffp_account_info.password,
            "verificationCode": "",
            "codeSessionId": ""
        }
        result = http_session.request(url=url, method='POST', json=post_data,
                             provider_channel=self.provider_channel, verify=False).to_json()

        Logger().debug(result)
        if not result.get('status') == '0' or not result.get('data') or not result['data'].get('token'):
            raise LoginException('login failed')
        http_session.update_headers({'b2c-api-user-token': result['data']['token']})

        gevent.sleep(1)
        login_result = self._check_login(http_session)
        if login_result:
            return http_session
        else:
            raise LoginCritical('login failed')

    def _check_login(self, http_session):
        """
        检查登录状态
        :param http_session:
        :return:
        """
        url = 'http://b2capi.donghaiair.cn/torder/getNoTOrderCount'
        post_data= 'language = zh - CN'
        result = http_session.request(url=url, method='POST', json=post_data, provider_channel=self.provider_channel,
                                      verify=False).to_json()

        '''
            {"status":"0","message":"成功！","data":{"orderCount":0}}
        '''

        Logger().debug(result)

        if result.get('status') == '0':
            return True
        else:
            return False

    def _register(self, http_session, pax_info, ffp_account_info):
        """
        注册模块
        """

        account = TBG.redis_conn.redis_pool.rpoplpush('donghaiair_account_list', 'donghaiair_account_list')
        account = eval(account) if account else random.choice(self.account_list)
        ffp_account_info.username = account['username']
        ffp_account_info.password = account['password']
        ffp_account_info.provider = self.provider
        return ffp_account_info

    def _flight_search(self, http_session, search_info):
        """
        航班爬取模块，
        TODO :目前只考虑单程
        :return:
        """

        try:

            gevent.sleep(1)
            Logger().debug('search flight')

            url = 'http://b2capi.donghaiair.cn/ibe/flightSearch'
            post_data = {
                "flightType": "1",
                "orgCode": search_info.from_airport,
                "destCode": search_info.to_airport,
                "departureDateStr": search_info.from_date,
                "returnDateStr": "",
                "adult": str(search_info.adt_count),
                "child": str(search_info.chd_count),
                "infant": str(search_info.inf_count)
            }

            referer = 'http://www.donghaiair.com'
            headers = {'referer': referer}
            http_session.update_headers(headers)

            result = http_session.request(url=url, method='POST', json=post_data,
                                          provider_channel=self.provider_channel, verify=False)
            search_result_data = json.loads(result.content)
            if not search_result_data.get('status') == '0':
                raise FlightSearchException('search flight error!')
            if not search_result_data.get('data'):
                Logger().warn('donghaiair no flight')
                return search_info

            search_routes = search_result_data['data']

            product_list = []
            for route in search_routes:
                if not route.get('cabins'):
                    continue

                cabin_list = []
                def sub_cabin_search(cabin_list, post_data):
                    url = 'http://b2capi.donghaiair.cn/ibe/rankInfos'
                    result = http_session.request(url=url, method='POST', json=post_data,
                                                  provider_channel=self.provider_channel,
                                                  verify=False, timeout=10).to_json()

                    if result.get('status') == '0' and result.get('data'):
                        cabin_list.extend(result['data'])

                cabin_type_list = [0, 1, 2]
                if search_info.cabin_grade == 'F':
                    cabin_type_list = [0]
                elif search_info.cabin_grade == 'Y':
                    cabin_type_list = [1, 2]
                worker_list = [gevent.spawn(sub_cabin_search, cabin_list, {
                        "orgCode": search_info.from_airport,
                        "destCode": search_info.to_airport,
                        "departureDateStr": search_info.from_date,
                        "flightNo": route['flyNo'], "cabinType": cabin_type}) for cabin_type in cabin_type_list]
                gevent.joinall(worker_list, timeout=30)

                for cabin in cabin_list:

                    if cabin["seat"] == "已售罄":
                        continue
                    product = {
                        'segment_info': route,
                        'cabin_info': cabin
                    }

                    flight_routing = FlightRoutingInfo()

                    routing_key = RoutingKey.serialize(
                        from_airport=route['orgAirport3Code'],
                        dep_time=datetime.datetime.strptime(route['depdate'], '%Y-%m-%d %H:%M:%S'),
                        to_airport=route['dstAirport3Code'],
                        arr_time=datetime.datetime.strptime(route['arridate'], '%Y-%m-%d %H:%M:%S'),
                        flight_number=route['flyNo'],
                        cabin=cabin['cabinCode'],
                        cabin_grade=cabin['basicCabin'],
                        product='COMMON',
                        provider = self.provider,
                        adult_price=float(cabin['onewayPrice']),
                        adult_tax=float(cabin['airportTax']) + float(cabin['fuelTax']),
                        provider_channel=self.provider_channel,
                        child_price=float(cabin['childPrice']), child_tax=float(cabin['fuel_ch']),
                        inf_price=float(cabin['infantPrice']), inf_tax=0.0,
                        search_from_airport=search_info.from_airport,
                        search_to_airport=search_info.to_airport,
                        from_date=search_info.from_date,
                        routing_range=search_info.routing_range,
                        trip_type=search_info.trip_type,
                        is_include_operation_carrier=0,
                        is_multi_segments=0
                    )

                    flight_routing.routing_key_detail = routing_key['plain']
                    flight_routing.routing_key = routing_key['encrypted']  # 此处需要进行hash
                    product_list.append(product)
                    flight_routing.product_type = 'DEFAULT'

                    flight_segment = FlightSegmentInfo()
                    flight_segment.carrier = 'DZ'
                    flight_segment.dep_airport = route['orgAirport3Code']
                    flight_segment.dep_time = route['depdate']

                    flight_segment.arr_airport = route['dstAirport3Code']
                    flight_segment.arr_time = route['arridate']

                    # 经停
                    flight_segment.stop_cities = route['stopcity']

                    flight_segment.flight_number = route['flyNo']
                    flight_segment.dep_terminal = route['depTerm'] if route.get('depTerm') else ''
                    flight_segment.arr_terminal = route['arriTerm'] if route.get('arriTerm') else ''
                    flight_segment.cabin = cabin['cabinCode']
                    flight_segment.cabin_grade = cabin['basicCabin']
                    flight_segment.cabin_count = int(cabin['seat']) if not cabin['seat'] == 'A' else 9
                    segment_duration = (datetime.datetime.strptime(route['arridate'], '%Y-%m-%d %H:%M:%S') -
                                        datetime.datetime.strptime(route['depdate'], '%Y-%m-%d %H:%M:%S')).seconds
                    duration = int(segment_duration / 60)
                    flight_segment.duration = duration
                    flight_segment.routing_number = 1
                    flight_routing.from_segments.append(flight_segment)

                    flight_routing.adult_price = float(cabin['onewayPrice'])
                    flight_routing.adult_price_discount = int(float(cabin['discountRate'])*10)
                    flight_routing.adult_full_price = int(float(cabin['onewayPrice'])/int(float(cabin['discountRate'])*10))
                    flight_routing.adult_tax = float(cabin['airportTax']) + float(cabin['fuelTax'])
                    flight_routing.child_price = float(cabin['childPrice'])
                    flight_routing.child_tax = float(cabin['fuel_ch'])
                    search_info.assoc_search_routings.append(flight_routing)


            search_info.product_list = product_list
            return search_info
        except:
            import traceback
            Logger().error(traceback.format_exc())
            raise FlightSearchException('search error!')

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

        order_info.provider_order_status = 'REGISTER_FAIL'
        if not order_info.ffp_account:
            # 如果没有账号才需要注册
            try:
                ffp_account_info = self.register(http_session=http_session, pax_info=order_info.passengers[0],
                                                 sub_order_id=order_info.sub_order_id,
                                                 flight_order_id=order_info.flight_order_id)
            except Critical as e:
                raise
            order_info.ffp_account = ffp_account_info  # 需要将账号信息反馈到order_info

        order_info.provider_order_status = 'LOGIN_FAIL'
        http_session = self.login(http_session, order_info.ffp_account)
        gevent.sleep(1)
        order_info.provider_order_status = 'SEARCH_FAIL'
        search_info = self.flight_search(http_session, order_info)

        order_info.provider_order_status = 'BOOK_FAIL'
        # 确认航班
        gevent.sleep(1)
        Logger().info('confirm flight ')

        routing_info = None
        product_details = None
        for index, flight_routing in enumerate(order_info.assoc_search_routings):
            real_search_un_key = RoutingKey.trans_un_key(flight_routing.routing_key, is_encrypted=True)
            order_un_key = RoutingKey.trans_un_key(order_info.routing.routing_key, is_encrypted=True)
            if real_search_un_key == order_un_key:
                routing_info = flight_routing
                product_details = search_info.product_list[index]
                break
        if not routing_info or not product_details:
            order_info.provider_order_status = 'BOOK_FAIL_NO_CABIN'
            Logger().error("booking no cabin rk:{}".format(order_info.routing.routing_key))
            raise BookingException('routingkey not found')

        adult_num = 0
        children_num = 0
        inf_num = 0
        order_info.passengers = sorted(order_info.passengers,
                                       key=lambda x: datetime.datetime.strptime(x.birthdate, '%Y-%m-%d'))
        for passenger in order_info.passengers:
            age_type = passenger.current_age_type(order_info.from_date)
            if age_type == 'ADT':
                adult_num += 1
            elif age_type == 'CHD':
                children_num += 1
            elif age_type == 'INF':
                inf_num += 1

        age_type_map = {
            'ADT': 'ADULT',
            'CHD': 'CHILD',
            'INF': 'INFANT'
        }

        age_type_price_map = {
            'ADT': int(routing_info.adult_price + routing_info.adult_tax),
            'CHD': int(routing_info.child_price + routing_info.child_tax),
            'INF': int(float(product_details['cabin_info']['infantPrice']))
        }

        fake_age_type_price_map = {
            'ADT': int(routing_info.adult_price + routing_info.adult_tax),
            'CHD': int(routing_info.child_price + float(product_details['cabin_info']['airportTax'])),
            'INF': int(float(product_details['cabin_info']['infantPrice']) + float(product_details['cabin_info']['airportTax']))
        }

        select_adt_list = [p for p in order_info.passengers if p.current_age_type(order_info.from_date) == 'ADT']
        if not select_adt_list:
            raise BookingException('have no adt passengers!')
        select_adt = select_adt_list[0]
        passenger_info_list = []
        for p in order_info.passengers:
            passenger_info = {
                "personType": age_type_map[p.current_age_type(order_info.from_date)],
                "personName": p.last_name + p.first_name,
                "firstName": p.first_name,
                "lastName": p.last_name,
                "personIdtype": p.used_card_type,
                "personIdnum": p.selected_card_no,
                "cabinType": product_details['cabin_info']['cabinCode'],
                "totalmoney": fake_age_type_price_map[p.current_age_type(order_info.from_date)]
            }
            if passenger_info['personType'] == 'INFANT':
                passenger_info.update({
                    "infantBirth": p.birthdate,
		            "carrierName": '{}/{}'.format(select_adt.last_name, select_adt.first_name),
                })
            passenger_info_list.append(passenger_info)

        post_data = {
            "actionCode": 1,
            "flights": [{
                "cabinType": product_details['cabin_info']['cabinCode'],
                "roundTrip": order_info.trip_type,
                "flightNum": product_details['segment_info']['flyNo'],
                "airtype": product_details['segment_info']['planestyle'],
                "orgcity3code": product_details['segment_info']['orgcity'],
                "destcity3code": product_details['segment_info']['dstcity'],
                "stopcity3code": product_details['segment_info']['stopcity'],
                "stopairport3code": product_details['segment_info']['stopcity'],
                "departureDateStr": order_info.from_date
            }],
            "orderPassengers": passenger_info_list,
            "orderContact": {
                "name": order_info.contacts[0].name,
                "firstName": order_info.contacts[0].name[1: ],
                "lastName": order_info.contacts[0].name[: 1],
                "phoneNum": '13305818816',
                "defaultContact": "",
                "email": ""
            },
            "channelType": "B2C",
            "resourceType": "PC"
        }

        url = 'http://b2capi.donghaiair.cn/ibe/flightBooking'
        result = http_session.request(url=url, method='POST', json=post_data, provider_channel=self.provider_channel,
                                      verify=False).to_json()

        if result.get('status') == '0' and result.get('data'):
            order_info.provider_order_status = 'BOOK_SUCCESS_AND_WAITING_PAY'
            order_info.provider_order_id = result['data']
            order_info.provider_price = int(adult_num * age_type_price_map['ADT'] +
                                            children_num * age_type_price_map['CHD'] +
                                            inf_num * age_type_price_map['INF'])
        else:
            Logger().serror("============ booking failed: other result code ======")
            Logger().serror(result)
            raise BookingException('booking failed!')

    def _check_order_status(self, http_session, ffp_account_info, order_info):
        """
        检查订单状态
        :param http_session:
        :param order_id:
        :return: 返回订单状态
        """

        http_session = self.login(ffp_account_info=ffp_account_info)

        url = 'http://b2capi.donghaiair.cn/torder/getIdOrder?orderNumber={}'.format(order_info.provider_order_id)
        result = http_session.request(url=url, method='GET', provider_channel=self.provider_channel,
                                      verify=False).to_json()
        if result.get('status') == '0' and result.get('data') and \
                        result['data']['tOrder']['orderNum'] == order_info.provider_order_id:
            if result['data']['tOrder']['orderStatus'] == '已取消':
                order_info.provider_order_status = 'ISSUE_CANCEL'
                return

            psg_list = result['data']['passengerList']
            for pax_info in order_info.passengers:
                for psg in psg_list:
                    if pax_info.selected_card_no == psg['personIdnum'] and psg.get('ticketno'):
                        pax_info.ticket_no = psg['ticketno']
                        order_info.provider_order_status = 'ISSUE_SUCCESS'
                        Logger().info('psg ticket_no %s' % pax_info.ticket_no)
                        break
            if not order_info.provider_order_status == 'ISSUE_SUCCESS':
                # 如果还未支付，要延时，防止抢占运营人员登录支付
                gevent.sleep(2*60)
        else:
            Logger().error("cannot get order info")
            gevent.sleep(2*60)
            raise CheckOrderStatusException("have no order")

    def _get_coupon(self, http_session, ffp_account_info):
        """
        获取VISA红包
        :return:
        """

        pass

    def _pay(self, order_info, http_session, pay_dict):
        """
        支付
        :param http_session:
        :return:
        """

        order_info.provider_order_status = 'LOGIN_FAIL'
        http_session = self.login(http_session=http_session, ffp_account_info=order_info.ffp_account)

        order_info.provider_order_status = 'PAY_FAIL'
        url = 'http://b2capi.donghaiair.cn/torder/selectOrder'
        post_data = {'orderNum': order_info.provider_order_id}
        result = http_session.request(url=url, method='POST', provider_channel=self.provider_channel,
                                      data=post_data).to_json()
        if not result.get('status') == '0':
            Logger().error(result)
            return PayException('get order info failed')
        member_id = result['data']['order']['memberId']

        url = 'http://b2capi.donghaiair.cn/ibe/checkCabin?orderNum={}'.format(order_info.provider_order_id)
        post_data = 'orderNum={}'.format(order_info.provider_order_id)
        result = http_session.request(url=url, method='POST', provider_channel=self.provider_channel,
                                      data=post_data).to_json()
        if not result.get('status') == '0':
            Logger().error(result)
            raise PayException('check cabin failed')

        url = 'http://b2cpayment.donghaiair.com/aliPayment/getAliPayQR?processType=SYS0701&orderNo={}&memberId={}'.format(
            order_info.provider_order_id, member_id)
        result = http_session.request(url=url, method='GET', provider_channel=self.provider_channel).to_json()
        if not result.get('status') == '0':
            Logger().error(result)
            raise PayException('get qrcode failed')

        qrcode_url = result.get('data')
        # qr.alipay.com    二维码识别后的支付宝地址
        pay_result = self.alipay_qcode(order_info.provider_order_id, qrcode_url)
        if pay_result:
            return pay_dict['alipay_yiyou180']
        else:
            raise PayException('alipay error')


class DonghaiairWantu(Donghaiair):
    timeout = 50  # 请求超时时间
    provider = 'donghaiair'  # 子类继承必须赋
    provider_channel = 'donghaiair_web_wantu'  # 子类继承必须赋
    operation_product_type = '会员折扣'  # 运价类型：0: GDS公布运价 1:GDS私有运价 2:航司官网产品  3:廉价航司产品 4:特价产品
    operation_product_mode = 'A2B'
    pay_channel = 'ALIPAY'
    is_display = True

    def __init__(self):
        super(DonghaiairWantu, self).__init__()

        self.booking_retries = 3
        self.ota_fare_search_tries = 5

        self.account_list = [
            {'username': '13456916062',	'password': 'wt121314'},
            {'username': '18058810238', 'password': 'wt121314'},
            {'username': '15868184810',	'password': 'wt121314'},
            {'username': '15858118293',	'password': 'wt121314'},
            {'username': '15968132645',	'password': 'wt121314'},
            {'username': '13989538577',	'password': 'wt121314'},
            {'username': '15968538767',	'password': 'wt121314'},
            {'username': '15057175825',	'password': 'wt121314'},
            {'username': '15924110617',	'password': 'wt121314'},
            {'username': '18106506851',	'password': 'wt121314'},
            {'username': '18067997975',	'password': 'wt121314'},
            {'username': '18072957353',	'password': 'wt121314'},
            {'username': '18064780321',	'password': 'wt121314'},
            {'username': '17521278569',	'password': 'wt121314'},
            {'username': '15258472930',	'password': 'wt121314'},
            {'username': '17607457819',	'password': 'wt121314'},
            {'username': '13454132363',	'password': 'wt121314'},
            {'username': '13666602915',	'password': 'wt121314'},
            {'username': '18057190276',	'password': 'wt121314'},
            {'username': '13989455982',	'password': 'wt121314'},
            {'username': '13675872069',	'password': 'wt121314'},
            {'username': '17681890305',	'password': 'wt121314'},
        ]
        if not TBG.redis_conn.redis_pool.llen('donghaiair_wantu_account_list') == len(self.account_list):
            TBG.redis_conn.redis_pool.expire('donghaiair_wantu_account_list', 0)
            for account in self.account_list:
                TBG.redis_conn.redis_pool.lpush('donghaiair_wantu_account_list', account)

    def _register(self, http_session, pax_info, ffp_account_info):
        """
        注册模块
        """

        account = TBG.redis_conn.redis_pool.rpoplpush('donghaiair_wantu_account_list', 'donghaiair_wantu_account_list')
        account = eval(account) if account else random.choice(self.account_list)
        ffp_account_info.username = account['username']
        ffp_account_info.password = account['password']
        ffp_account_info.provider = self.provider
        return ffp_account_info

