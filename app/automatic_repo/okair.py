#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gevent
import json
import datetime
import random
import string
from .base import ProvderAutoBase
from ..dao.internal import *
from ..utils.util import RoutingKey
from ..controller.captcha import CaptchaCracker
from app import TBG


class Okair(ProvderAutoBase):
    timeout = 50  # 请求超时时间
    provider = 'okair'  # 子类继承必须赋
    provider_channel = 'okair_web'  # 子类继承必须赋
    operation_product_type = '会员折扣'  # 运价类型：0: GDS公布运价 1:GDS私有运价 2:航司官网产品  3:廉价航司产品 4:特价产品
    operation_product_mode = 'A2B'
    pay_channel = 'ALIPAY'
    is_display = True
    is_include_booking_module = True  # 是否包含下单模块
    no_flight_ttl = 3600 * 3  # 无航班缓存超时时间设定
    carrier_list = ['BK']  # 供应商所包含的航司列表，如果包含多个并且无法确定，请不要填写，此处会关联执飞航线判断逻辑


    CACHE_PR_CONFIG = {
        1: {'cabin_expired_time': 3600 * 12, 'cabin_attenuation': 3,'fare_expired_time':86400 * 30},
        2: {'cabin_expired_time': 3600 * 3, 'cabin_attenuation': 2,'fare_expired_time':86400 * 20},
        3: {'cabin_expired_time': 60 * 60 * 1, 'cabin_attenuation': 1,'fare_expired_time':86400 * 10},
        4: {'cabin_expired_time': 60 * 40, 'cabin_attenuation': 1,'fare_expired_time':86400 * 5},
        5: {'cabin_expired_time': 60 * 30, 'cabin_attenuation': 0,'fare_expired_time':86400},

    }
    search_interval_time = 0

    def __init__(self):
        super(Okair, self).__init__()

        self.booking_retries = 3
        self.ota_fare_search_tries = 5

        self.account_list = [
            {'username': '17316551656', 'password': '234Bdfdm3'},
            {'username': '18368481562', 'password': '2124dfdBm3'},
            {'username': '18321259556', 'password': 'TMB1m323f'},
            {'username': '17891937371', 'password': 'TMsdf3B1m3'},
            {'username': '13666726614', 'password': 'TMn3B1m3'},
            {'username': '17891930359', 'password': 'vxcGKJ21312'},
            {'username': '17891933179', 'password': 'vcvHGK43957'},
            {'username': '17891930025', 'password': 'Gcz84YcxJBT'},
            {'username': '17891961680', 'password': 'wxfG7585BT'},
            {'username': '17891989285', 'password': 'Gadsa2we23'},
            {'username': '17891955080', 'password': 'sdfGKYJ321BT'},
            {'username': '17891998586', 'password': 'fsfcGsad673'},
            {'username': '17891932885', 'password': 'GKYnos973'},
            {'username': '17891951053', 'password': 'GczK2345BT'},
            {'username': '17891965282', 'password': 'GKYl2jl9ls'},
        ]
        if not TBG.redis_conn.redis_pool.llen('okair_account_list') == len(self.account_list):
            TBG.redis_conn.redis_pool.expire('okair_account_list', 0)
            for account in self.account_list:
                TBG.redis_conn.redis_pool.lpush('okair_account_list', account)


    def _pre_order_check(self, http_session, order_info):
        """
        订单预检
        增加75岁老人检测
        :param http_session:
        :param order_info:
        :return:
        """

        adt_list = [x for x in order_info.passengers if x.current_age_type(from_date=order_info.from_date, is_aggr_chd_adt=True) == 'ADT']
        chd_list = [x for x in order_info.passengers if x.current_age_type(from_date=order_info.from_date, is_aggr_chd_adt=True) == 'CHD']

        if len(adt_list) * 2 < len(chd_list):
            return 'TOO_MANY_CHILD'
        for pax_info in order_info.passengers:
            if pax_info.current_age(from_date=order_info.from_date) >= 75:
                return 'TOO_OLD_TO_BOARDING'
            elif  pax_info.current_age(from_date=order_info.from_date) <= 2:
                return 'TOO_YOUNG_TO_BOARDING'
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
                rl.append(s)

        Logger().sdebug('split_order %s' % rl)
        return rl


    def _login(self, http_session, ffp_account_info):
        """
        登陆模块
        :return: 登陆成功的httpResult 对象
        """

        url = 'https://www.okair.net/login.action'
        http_session.request(url=url, method='GET',
                             provider_channel=self.provider_channel, verify=False)
        gevent.sleep(1)

        url = 'https://www.okair.net/login!doLogin.action'
        post_data = {
            'loginType': 'sale',
            'username': ffp_account_info.username,
            'password': ffp_account_info.password,
        }
        http_session.request(url=url, method='POST', data=post_data,
                             provider_channel=self.provider_channel, verify=False)

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
        url = 'https://www.okair.net/commonajax!getCurrentCityInfo.action'
        post_data = {'param': json.dumps({"currentIp":"139.219.110.107"})}
        result = http_session.request(url=url, method='POST', data=post_data,
                                      provider_channel=self.provider_channel, verify=False).to_json()

        if result.get('userinfo'):
            return True
        else:
            return False

    def _register(self, http_session, pax_info, ffp_account_info):
        """
        注册模块
        """

        account = TBG.redis_conn.redis_pool.rpoplpush('okair_account_list', 'okair_account_list')
        account = eval(account) if account else random.choice(self.account_list)
        ffp_account_info.username = account['username']
        ffp_account_info.password = account['password']
        ffp_account_info.provider = self.provider
        return ffp_account_info

    def generate_routing_key(self, product, search_info):

        segment_list = product['segment_info']

        dep_time = '{} {}00'.format(segment_list[0]['depDate'], segment_list[0]['depTime'])
        arr_time = '{} {}00'.format(segment_list[-1]['arrDate'], segment_list[-1]['arrTime'])

        adult_price = 0.0
        adult_tax = 0.0
        child_price = 0.0
        child_tax = 0.0
        inf_price = 0.0
        inf_tax = 0.0
        for segment in segment_list:
            try:
                adult_price += int(product['cabin_info']['fbcList'][0]['adPrice'])
                adult_tax_list = [i for i in product['cabin_info']['fbcList'][0]['taxList'] if i['taxType'] == 'ADT']
                for t in adult_tax_list:
                    adult_tax += int(t['taxPrice'])

                child_price += int(product['cabin_info']['fbcList'][0]['chPrice'])
                child_tax_list = [i for i in product['cabin_info']['fbcList'][0]['taxList'] if i['taxType'] == 'CHD']
                for t in child_tax_list:
                    child_tax += int(t['taxPrice'])
            except Exception as e:
                Logger().debug(e)

        rk_info = RoutingKey.serialize(from_airport=segment_list[0]['dep'], dep_time=datetime.datetime.strptime(dep_time, '%Y%m%d %H%M%S'),
                                       to_airport=segment_list[-1]['arr'], arr_time=datetime.datetime.strptime(arr_time, '%Y%m%d %H%M%S'),
                                       flight_number=segment_list[0]['fltNo'],
                                       cabin='-'.join([product['cabin_info']['adClass'] for s in segment_list]),
                                       cabin_grade='-'.join([product['cabin_info']['baseCabinCode'] for s in segment_list]),
                                       product='COMMON',
                                       adult_price=adult_price, adult_tax=adult_tax, provider_channel=self.provider_channel,
                                       child_price=child_price, child_tax=child_tax,
                                       inf_price=inf_price, inf_tax=inf_tax,provider=self.provider,
                                       search_from_airport=search_info.from_airport,
                                       search_to_airport=search_info.to_airport,
                                       from_date=search_info.from_date,
                                       routing_range=search_info.routing_range,
                                       trip_type=search_info.trip_type,
                                       is_include_operation_carrier=0,
                                       is_multi_segments=1 if len(segment_list) > 1 else 0
                                       )  # 供应商渠道写死为 奥凯



        return rk_info['plain'],rk_info['encrypted'], adult_price, adult_tax, child_price, child_tax

    def _flight_search(self, http_session, search_info):
        """
        航班爬取模块，
        TODO :目前只考虑单程
        :return:
        """

        gevent.sleep(1)
        Logger().debug('search flight')

        url = 'https://www.okair.net/salePubAjax!queryFare.action'
        request_data = {
            'param': json.dumps({
                'org': search_info.from_airport,
                'dst': search_info.to_airport,
                'fltDate': datetime.datetime.strftime(datetime.datetime.strptime(search_info.from_date, '%Y-%m-%d'),
                                                      '%Y%m%d')
            })
        }

        search_result_data = None
        have_routing = False
        for i in xrange(5):
            result = http_session.request(url=url, method='POST', data=request_data,
                                          provider_channel=self.provider_channel, verify=False)
            search_result_data = json.loads(result.content)
            if not search_result_data['errorCode'] in ['00', '01']:
                raise FlightSearchException('search flight error!')
            elif search_result_data['errorCode'] == '01':
                gevent.sleep(5)
                continue
            else:
                have_routing = True
                break
        if not have_routing:
            Logger().warn('okair no flight')
            return search_info

        search_routes = search_result_data.get('fltList')

        product_list = []
        for route in search_routes:
            if not route['segmentList']:
                continue
            if not route['segmentList'][0]['avCabinInfo']:
                continue
            cabins = route['segmentList'][0]['avCabinInfo']
            for cabin in cabins:
                product = {
                    'segment_info': route['segmentList'],
                    'cabin_info': cabin
                }

                flight_routing = FlightRoutingInfo()
                flight_routing.routing_key_detail,flight_routing.routing_key, adult_price, adult_tax, child_price, child_tax = \
                    self.generate_routing_key(product, search_info)

                product_list.append(product)
                base_price = cabin['baseCabinPrice']
                adult_discount = 0

                flight_routing.product_type = 'DEFAULT'
                routing_number = 1
                for index, segment in enumerate(product['segment_info']):
                    flight_segment = FlightSegmentInfo()
                    flight_segment.carrier = 'BK'
                    dep_time = '{} {}00'.format(segment['depDate'], segment['depTime'])
                    arr_time = '{} {}00'.format(segment['arrDate'], segment['arrTime'])
                    dep_time = datetime.datetime.strftime(datetime.datetime.strptime(dep_time, '%Y%m%d %H%M%S'),
                                                          '%Y-%m-%d %H:%M:%S')
                    arr_time = datetime.datetime.strftime(datetime.datetime.strptime(arr_time, '%Y%m%d %H%M%S'),
                                                          '%Y-%m-%d %H:%M:%S')
                    flight_segment.dep_airport = segment['dep']
                    flight_segment.dep_time = dep_time

                    flight_segment.arr_airport = segment['arr']
                    flight_segment.arr_time = arr_time

                    # 经停
                    stop_city_code_list = []
                    stop_airport_code_list = []
                    for sl in segment['stopList']:
                        stop_city_code_list.append(sl['stopCityInfo']['cityCode'])
                        stop_airport_code_list.append(sl['stopAirportCode'])
                    flight_segment.stop_cities = "/".join(stop_city_code_list)
                    flight_segment.stop_airports = "/".join(stop_airport_code_list)

                    flight_segment.flight_number = segment['fltNo']
                    flight_segment.dep_terminal = segment['depTerm'] if segment.get('depTerm') else ''
                    flight_segment.arr_terminal = segment['arrTerm'] if segment.get('arrTerm') else ''
                    flight_segment.cabin = cabin['adClass']
                    flight_segment.cabin_grade = cabin['baseCabinCode']
                    flight_segment.cabin_count = cabin['adRemain'] if not cabin['adRemain'] == 'A' else 9
                    segment_duration = (datetime.datetime.strptime(arr_time, '%Y-%m-%d %H:%M:%S') -
                                        datetime.datetime.strptime(dep_time, '%Y-%m-%d %H:%M:%S')).seconds
                    duration = int(segment_duration / 60)
                    flight_segment.duration = duration
                    flight_segment.routing_number = routing_number
                    routing_number += 1
                    flight_routing.from_segments.append(flight_segment)

                flight_routing.adult_price = adult_price
                flight_routing.adult_price_discount = int((float(adult_price)/float(base_price))*10)
                flight_routing.adult_full_price = int(base_price)
                flight_routing.adult_tax = adult_tax
                flight_routing.child_price = child_price
                flight_routing.child_tax = child_tax
                search_info.assoc_search_routings.append(flight_routing)
        search_info.product_list = product_list
        return search_info

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

        passenger_info_list = [{
                "ifRegFfp": "Y",
                "firstName": p.last_name if not p.last_name[0] in string.letters else p.first_name,
                "lastName": p.first_name if not p.last_name[0] in string.letters else p.last_name,
                "docNo": p.selected_card_no,
                "ffpTel": '13305818816',
                "birthDay": datetime.datetime.strftime(datetime.datetime.strptime(p.birthdate, '%Y-%m-%d'), '%Y%m%d'),
                "docType": p.used_card_type,
                "psgType": p.current_age_type(order_info.from_date),
                "psgName": u"{}{}".format(p.last_name, p.first_name) if not p.last_name[0] in string.letters else u"{}/{}".format(p.first_name, p.last_name),
                "inlandPsgId": "",
                "memberId": "",
                "gender": u'男' if p.gender == 'M' else u'女',
            } for p in order_info.passengers]

        post_data = {'param': json.dumps({
            "editPsgList": [],
            "delPsgList": [],
            "addPsgList": passenger_info_list
        })}

        url = 'https://www.okair.net/salePriAjax!handleInlandPsgList.action'
        result = http_session.request(url=url, method='POST', data=post_data,
                                      provider_channel=self.provider_channel, verify=False).to_json()
        if not result.get('errorCode') in ['00', '01']:
            raise BookingException('添加乘机人失败！')

        gevent.sleep(1)
        query_string = '?{} GMT+0800 (China Standard Time)'.format(
            datetime.datetime.now().strftime('%a %b %d %Y %H:%M:%S'))
        url = 'https://www.okair.net/salePriAjax!startCaptcha.action{}'.format(query_string)
        result = http_session.request(url=url, method='POST',
                                      provider_channel=self.provider_channel, verify=False).to_json()
        if not result.get('errorCode') == '00':
            raise BookingException('get geetest challenge failed')
        challenge = result['gtJson']['challenge']
        gt = result['gtJson']['gt']

        cracker = CaptchaCracker.select('C2567')
        checked_gee = cracker.crack(geetest_gt=gt, geetest_challenge=challenge)
        geetest_challenge = checked_gee['challenge']
        geetest_validate = checked_gee['validate']
        geetest_seccode = checked_gee['validate'] + '|jordan'

        total_money = int(routing_info.adult_price*adult_num + routing_info.adult_tax*adult_num + \
                          routing_info.child_price*children_num + routing_info.child_tax*children_num + \
                          routing_info.child_price*inf_num + routing_info.child_tax*inf_num)

        url = 'https://www.okair.net/salePriAjax!bookSeat.action'
        post_data = {'param': json.dumps({
            "totalMoney": total_money,
            "org": product_details['segment_info'][0]['dep'],
            "dst": product_details['segment_info'][-1]['arr'],
            "tripType":"OW",
            "departDate": product_details['segment_info'][0]['depDate'],
            "returnDate":"",
            "bookFltLegInfoGo":[{
                "bookTravelerInfo":[{
                    "ifRegFfp": p['ifRegFfp'],
                    "firstName": p['firstName'],
                    "lastName": p['lastName'],
                    "ffpTel": p['ffpTel'],
                    "birthDate": p['birthDay'],
                    "docType": p['docType'],
                    "psgType": p['psgType'],
                    "psgName": p['psgName'],
                    "inlandPsgId": p['inlandPsgId'],
                    "memberId": p['memberId'],
                    "gender": p['gender'],
                    "isFfp": p['ifRegFfp'],
                    "docId": p['docNo'],
                    "baseCabinCode": product_details['cabin_info']['baseCabinCode'],
                    "baseCabinPrice": product_details['cabin_info']['baseCabinPrice'],
                    "ei": product_details['cabin_info']['adEi'],
                    "price": product_details['cabin_info']['fbcList'][0]['adPrice'] if p['psgType'] == 'ADT' else \
                        product_details['cabin_info']['fbcList'][0]['chPrice'],
                    "fbc": product_details['cabin_info']['fbcList'][0]['adFbc'] if p['psgType'] == 'ADT' else \
                        product_details['cabin_info']['fbcList'][0]['chFbc'],
                    "priceType": product_details['cabin_info']['fbcList'][0]['priceType'],
                    "cabin": product_details['cabin_info']['adClass'] if p['psgType'] == 'ADT' else \
                        product_details['cabin_info']['fbcList'][0]['chClass'],
                    "taxList":[i for i in product_details['cabin_info']['fbcList'][0]['taxList'] if i['taxType'] == p['psgType']]
                } for p in passenger_info_list],
                "segIndex": s['segIndex'],
                "org": s['dep'],
                "depAirportInfo": s['depAirportInfo'],
                "depTerm": s['depTerm'] if s.get('depTerm') else '',
                "takeOffDate": s['depDate'],
                "depTime": s['depTime'],
                "dst": s['arr'],
                "arrAirportInfo": s['arrAirportInfo'],
                "arrTerm": s['arrTerm'] if s.get('arrTerm') else '',
                "landDate": s['arrDate'],
                "arrTime": s['arrTime'],
                "fltNo": s['fltNo'],
                "acType": s['acType'],
                "stop": s['stop'],
                "arrad": s['arrad'],
                "avKey": s['avKey'],
                "tpm": s['tpm'],
                "isShare": s['isShare'],
                "ifGo": "GO",
                "duration": '{}小时{}分'.format(
                    int((datetime.datetime.strptime('{} {}00'.format(s['arrDate'], s['arrTime']), '%Y%m%d %H%M%S') -
        datetime.datetime.strptime('{} {}00'.format(s['depDate'], s['depTime']), '%Y%m%d %H%M%S')).seconds/3600),
                    int((datetime.datetime.strptime('{} {}00'.format(s['arrDate'], s['arrTime']), '%Y%m%d %H%M%S') -
        datetime.datetime.strptime('{} {}00'.format(s['depDate'], s['depTime']), '%Y%m%d %H%M%S')).seconds / 60) % 60
                                              )
            } for s in product_details['segment_info']],
            "bookFltLegInfoBack": [],
            "bookArrangerInfo": {"contactName": order_info.contacts[0].name,
                                "contactPhone": '13305818816'},
            "orderHodo": {"postType": "","hodoType": "行程单"},
            "geetest_challenge": geetest_challenge,
            "geetest_validate": geetest_validate,
            "geetest_seccode": geetest_seccode
        })}

        result = http_session.request(url=url, method='POST', data=post_data,
                                      provider_channel=self.provider_channel, verify=False,
                                      timeout=110).to_json()
        if result.get('errorCode') == '00' and result.get('ibeOrderNo'):
            order_info.provider_order_status = 'BOOK_SUCCESS_AND_WAITING_PAY'
            order_info.provider_order_id = result['ibeOrderNo']
            order_info.provider_price = result['param']['totalMoney']

            # #FIXME 测试，直接取消订单
            # gevent.sleep(3)
            # self.cancel_order(http_session, order_info.provider_order_id)

        elif result.get('errorCode') == '01':
            find_order = False
            for t in xrange(3):
                gevent.sleep(7)
                url = 'https://www.okair.net/orderajax!b2cOrderList.action'
                post_data = {
                    'param': json.dumps({"orderStatus": "ALL"})
                }
                result = http_session.request(url=url, method='POST', data=post_data,
                                              provider_channel=self.provider_channel, verify=False).to_json()
                if not result.get('errorCode') == '00' or not result.get('orderList'):
                    continue
                order_list = result['orderList']['orderList']
                passenger_ids = [p['docNo'] for p in passenger_info_list]
                for order in order_list:
                    order_docno_list = order['docNo'].split(',')

                    Logger().sinfo("==================== booking result 01 param ==========")
                    Logger().sinfo(order['org'])
                    Logger().sinfo(product_details['segment_info'][0]['dep'])
                    Logger().sinfo(order['dst'])
                    Logger().sinfo(product_details['segment_info'][0]['arr'])
                    Logger().sinfo(int(order['totalMoney']))
                    Logger().sinfo(total_money)
                    Logger().sinfo(order['fltNo'])
                    Logger().sinfo(product_details['segment_info'][0]['fltNo'])
                    Logger().sinfo(order['fltDate'])
                    Logger().sinfo(product_details['segment_info'][0]['depDate'])
                    Logger().sinfo(order_docno_list)
                    Logger().sinfo(passenger_ids)
                    Logger().sinfo(order['orderStatus'])
                    Logger().sinfo("==================== booking result 01 end ==========")

                    if order['org'] == product_details['segment_info'][0]['dep'] and \
                        order['dst'] == product_details['segment_info'][0]['arr'] and \
                        int(order['totalMoney']) == total_money and \
                        order['fltNo'] == product_details['segment_info'][0]['fltNo'] and \
                        order['fltDate'] == product_details['segment_info'][0]['depDate'] and \
                        sorted(order_docno_list) == sorted(passenger_ids) and order['orderStatus'] == '待支付':
                        order_info.provider_order_status = 'BOOK_SUCCESS_AND_WAITING_PAY'
                        order_info.provider_order_id = order['orderNo']
                        order_info.provider_price = total_money
                        find_order = True
                        break
                if find_order:
                    break
            if not find_order:
                raise BookingException(' check order list and booking failed !')

            # # FIXME 测试，直接取消订单
            # else:
            #     gevent.sleep(3)
            #     self.cancel_order(http_session, order_info.provider_order_id)

        elif result.get('errorCode') == '02':
            # 02: 账号已经存在两个未支付订单，不能下单，需要更换账号
            try:
                ffp_account_info = self.register(http_session=http_session, pax_info=order_info.passengers[0],
                                                 sub_order_id=order_info.sub_order_id,
                                                 flight_order_id=order_info.flight_order_id)
            except Critical as e:
                raise
            order_info.ffp_account = ffp_account_info
            raise BookingException('too many orders!')
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

        post_data = {"param": json.dumps({"orderNo": order_info.provider_order_id, "orderType": order_info.routing_range})}
        url = 'https://www.okair.net/orderajax!b2cOrderInfo.action'

        result = http_session.request(url=url, method='POST', data=post_data,
                                      provider_channel=self.provider_channel, verify=False).to_json()
        if result.get('errorCode') == '00' and result.get('orderInfo') and result['orderInfo']['orderNo'] == order_info.provider_order_id:

            if result['orderInfo']['orderStatus'] == '已取消':
                order_info.provider_order_status = 'ISSUE_CANCEL'
                return

            psg_list = result['orderInfo']['fltList'][0]['psgList']
            for pax_info in order_info.passengers:
                for psg in psg_list:
                    if pax_info.selected_card_no == psg['docNo'] and psg.get('tktNo'):
                        pax_info.ticket_no = psg['tktNo']
                        order_info.provider_order_status = 'ISSUE_SUCCESS'
                        Logger().info('psg ticket_no %s' % pax_info.ticket_no)
                        break
        else:
            Logger().error("cannot get order info")
            raise CheckOrderStatusException("have no order")

    def cancel_order(self, http_session, order_id):

        url = 'https://www.okair.net/orderajax!b2cOrderCancel.action'
        post_data = {'param': json.dumps({"ibeOrderNo": order_id})}
        result = http_session.request(url=url, method='POST', data=post_data,
                                      provider_channel=self.provider_channel, verify=False).to_json()
        if result.get('errorCode') == '00':
            return True
        else:
            return False

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

        url = 'https://www.okair.net/orderajax!b2cOrderPay.action'
        post_data = {'param': json.dumps({"orderNo": order_info.provider_order_id, "orderType": "IN"})}

        result = http_session.request(url=url, method='POST', data=post_data,
                             provider_channel=self.provider_channel, verify=False).to_json()
        pay_url = result.get('payUrl')
        gain_key = pay_url.split('?gainKey=')[-1]

        url = 'https://wx.okair.net/mktpay/aliNativePay.action?{} GMT 0800 (China Standard Time)'.format(datetime.datetime.now().strftime('%a %b %d %Y %H:%M:%S'))
        post_data = {'gainKey': gain_key}
        result = http_session.request(url=url, method='POST', data=post_data, provider_channel=self.provider_channel,
                                      verify=False).to_json()

        if not result.get('errorCode') == '00':
            Logger().error(result)
            raise PayException('get qrcode err')

        qrcode_url = result.get('qrCodeUrl')
        # wx.okair.net/   获取二维码图片的地址
        pay_result = self.alipay_qcode(order_info.provider_order_id, qrcode_url)
        if pay_result:
            return pay_dict['alipay_yiyou180']
        else:
            raise PayException('alipay error')


class OkairWantu(Okair):
    timeout = 50  # 请求超时时间
    provider = 'okair'  # 子类继承必须赋
    provider_channel = 'okair_web_wantu'  # 子类继承必须赋
    operation_product_type = '会员折扣'  # 运价类型：0: GDS公布运价 1:GDS私有运价 2:航司官网产品  3:廉价航司产品 4:特价产品
    operation_product_mode = 'A2B'
    pay_channel = 'ALIPAY'
    is_display = True

    def __init__(self):
        super(OkairWantu, self).__init__()

        self.booking_retries = 3
        self.ota_fare_search_tries = 5

        self.account_list = [
            {
                'username': '15868184810',
                'password': '121314Wpt',
            }, {
                'username': '133461820951',
                'password': '121314Wpt',
            }, {
                'username': '135671944601',
                'password': '121314Wpt',
            }, {
                'username': '133058188163',
                'password': '121314Wpt',
            }, {
                'username': '133361554745',
                'password': '121314Wpt',
            }, {
                'username': '133865193792',
                'password': '121314Wpt',
            }, {
                'username': '133360716635',
                'password': '121314Wpt',
            }, {
                'username': '15157117884',
                'password': '121314Wpt',
            }, {
                'username': '17379337193',
                'password': '121314Wpt',
            }, {
                'username': '18042498323',
                'password': '121314Wpt',
            }, {
                'username': '18094714981',
                'password': '121314Wpt',
            }, {
                'username': '18069433283',
                'password': '121314Wpt',
            }, {
                'username': '15068187085',
                'password': '121314Wpt',
            }, {
                'username': '182680867611',
                'password': '121314Wpt',
            }, {
                'username': '15057175825',
                'password': '121314Wpt',
            }, {
                'username': '158581611274',
                'password': '121314Wpt',
            }, {
                'username': '150687736253',
                'password': '121314Wpt',
            }, {
                'username': '13454132363',
                'password': '121314Wpt',
            }, {
                'username': '159900018482',
                'password': '121314Wpt',
            }, {
                'username': '136058085855',
                'password': '121314Wpt',
            }, {
                'username': '139571361694',
                'password': '121314Wpt',
            }, {
                'username': '189580022682',
                'password': '121314Wpt',
            }, {
                'username': '13777570082',
                'password': '121314Wpt',
            }
        ]
        if not TBG.redis_conn.redis_pool.llen('okair_wantu_account_list') == len(self.account_list):
            TBG.redis_conn.redis_pool.expire('okair_wantu_account_list', 0)
            for account in self.account_list:
                TBG.redis_conn.redis_pool.lpush('okair_wantu_account_list', account)

    def _register(self, http_session, pax_info, ffp_account_info):
        """
        注册模块
        """

        account = TBG.redis_conn.redis_pool.rpoplpush('okair_wantu_account_list', 'okair_wantu_account_list')
        account = eval(account) if account else random.choice(self.account_list)
        ffp_account_info.username = account['username']
        ffp_account_info.password = account['password']
        ffp_account_info.provider = self.provider
        return ffp_account_info
