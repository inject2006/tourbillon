# coding=utf8

import datetime
import base64
import requests
from app import TBG
from ..controller.http_request import HttpRequest
from ..utils.exception import *
from ..utils.logger import Logger
from ..utils.util import md5_hash, simple_encrypt, RoutingKey
from .base import OTABase
from ..dao.models import *
from ..dao.internal import *


class TcPolicyNb(OTABase):
    verify_search_timeout = 30
    order_search_timeout = 30
    ticket_process_mode = 'push'  # 票号处理模式-主动推送
    order_process_mode = 'polling'  # 订单同步模式-轮询拉取模式

    ota_name = 'tc_policy_nb'  # OTA名称，保证唯一，必须赋值
    ota_env = 'PROD'  # 生产OR测试接口 TODO 暂时无作用
    ota_token = 'iwj69etrnbq1lzcx'  # ota 访问验证token
    cn_ota_name = '南呗政策拉单'

    tc_username = 'nanbash1'
    tc_password = 'nanbash1'

    tc_main_username = 'shyy123'
    tc_main_password = 'yida1680'

    def __init__(self):
        super(TcPolicyNb, self).__init__()

    def _set_order_issued(self, order_info):

        http_session = requests.Session()
        url = 'http://ebk.17u.cn/iflightcrmapi/nonTcplApi/issueticket'
        token = self._get_token()
        headers = {
            'X-LY-Authentication': 'LY-{}'.format(token)
        }
        http_session.headers = headers
        pax_infos = []
        # TODO 目前没有加入返程和缺口程
        for pax_info in order_info.passengers:
            seg_index = json.loads(pax_info.passenger_id.split('@')[1])
            pax_id = pax_info.passenger_id.split('@')[0]
            for i in seg_index:
                pax_infos.append({
                    'passengerId': pax_id,
                    'lastName': pax_info.last_name,
                    'firstName': pax_info.first_name,
                    'pnr': pax_info.pnr,
                    'certificateNo': pax_info.used_card_no,
                    'certificateType': pax_info.used_card_type,
                    'ticketNo': pax_info.ticket_no,
                    'segmentIndex': i,
                })
        post_data = {
            'tcSerialNo': order_info.ota_order_id,
            'engineSerialNo': order_info.assoc_order_id,
            'issueTicketItems': pax_infos
        }
        Logger().info('tc_policy_set_issued_request %s' % post_data)
        result = http_session.post(url=url, json=post_data).json()
        Logger().info('tc_policy_set_issued_response %s' % result)
        if not result:
            raise SetOrderIssuedException(result)
        else:
            return True

    def _get_token(self):

        url = 'http://ebk.17u.cn/iflightcrmapi/supplierapi/token'
        http_session = requests.Session()
        # headers = {
        #     'Content-Type': 'application/json'
        # }
        post_data = {
            'loginName': self.tc_main_username,
            'password': self.tc_main_password,
            # 'loginName': self.tc_username,
            # 'password': self.tc_password,
        }

        result = http_session.post(url=url, json=post_data).json()
        if not result['result']:
            Logger().error('tc_policy_nb get token error:{}'.format(result))
            raise OrderByPollException(json.dumps(result))
        return result['data']

    def _order_by_poll(self):

        http_session = requests.Session()
        url = 'http://ebk.17u.cn/iflightcrmapi/nonTcplApi/orderlist'
        token = self._get_token()
        headers = {
            'X-LY-Authentication': 'LY-{}'.format(token)
        }
        http_session.headers = headers
        start_time = Time.curr_date_obj() - datetime.timedelta(hours=6)
        end_time = Time.curr_date_obj()
        data = {
            'orderStatus': 'READY_TO_ISSUE',
            # 'orderStatus': 'ISSUE_FINISH',
            'startDate': start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'endDate': end_time.strftime('%Y-%m-%d %H:%M:%S')
        }
        Logger().debug('_order_by_poll request %s' % data)

        ol_result = http_session.post(url=url, json=data).json()
        # ol_result = {u'traceId': u'NT20190322182557N6A21YV3HOKJH8CDVGBOFBW5BEFORE', u'obj': None, u'code': None, u'result': True, u'message': None, u'data': [
        #     {u'remark': None, u'depAirportCode': u'PVG', u'resourceType': 3, u'otherSerialNo': u'', u'arrAirportCode': u'AKL', u'amount': 2342, u'orderStatus': u'ISSUE_FINISH', u'tripType': u'OW',
        #      u'tcSerialNo': u'IT3PPK190322LJGG9213', u'engineSerialNo': u'BJ1903221135126508409363618750464', u'currencyCode': u'CNY', u'depDatetime': u'2019-04-15 11:55'}]}
        Logger().info("===== poll order list result : {}".format(ol_result))
        if not ol_result['result']:
            raise OrderByPollException(ol_result)

        order_list = []
        processed_list = []
        for order in ol_result['data']:
            ota_order_id = order['tcSerialNo']
            if not self.exists_order_filter([ota_order_id]):
                continue
            if ota_order_id in processed_list:
                continue
            else:
                processed_list.append(ota_order_id)
            if not order['orderStatus'] == 'READY_TO_ISSUE' or \
                    datetime.datetime.strptime(order['depDatetime'], '%Y-%m-%d %H:%M') < datetime.datetime.now():
                continue

            url = 'http://ebk.17u.cn/iflightcrmapi/nonTcplApi/orderdetail'
            data = {
                'tcSerialNo': order['tcSerialNo'],
                'engineSerialNo': order['engineSerialNo'],
            }
            result = http_session.post(url=url, json=data).json()
            # result = {u'traceId': u'BJ1903221135126508409363618750464', u'obj': None, u'code': None, u'result': True, u'message': None, u'data': {u'passengers': [
            #     {u'certificateNo': u'EA1685706', u'totalPrice': 1581.0, u'bigCode': None, u'firstName': u'JUNYU', u'lastName': u'SHANG', u'pnr': u'KFXN2S', u'cardExpired': u'2027-05-07',
            #      u'totalTax': 761.0, u'birthday': u'1996-01-23', u'gender': u'F', u'nationality': u'CN', u'certificateType': u'PP', u'passengerId': u'1ad30e8b-71ca-47f0-a862-f01c2005bdd6',
            #      u'passengerType': u'ADT'}], u'remark': u'', u'priceInfo': {u'price': 1581, u'tax': 761, u'amount': 2342, u'currencyCode': u'CNY'}, u'resourceType': 3, u'otherSerialNo': u'',
            #                                                                                                                                       u'officeNo': u'SZV122', u'passengerRule': {
            #         u'refChaRule': {u'changeDesc': u'\u4e0d\u5141\u8bb8\u6539\u671f',
            #                         u'refundDesc': u' \u6210\u4eba\uff1a\u4e0d\u53ef\u9000\u7968\uff0c\u53ef\u9000\u7a0e\u8d39420CNY \u513f\u7ae5\uff1a\u4e0d\u53ef\u9000\u7968\uff0c\u53ef\u9000\u7a0e\u8d39330CNY \u5a74\u513f\uff1a\u4e0d\u53ef\u9000\u7968\uff0c\u53ef\u9000\u7a0e\u8d39180CNY\u3002 ',
            #                         u'ticketDesc': u'\u9000\u7968\u5907\u6ce8\uff1a\u9700\u6263\u9664\u5df2\u4f7f\u7528\u822a\u6bb5\u673a\u7968\u8d39\u7528\u3002<br/>'},
            #         u'baggageRules': [{u'baggageDesc': u'\u6210\u4eba:\u4e00\u51712\u4ef6;\u513f\u7ae5:\u4e00\u51712\u4ef6', u'itinerary': u'\u6d66\u4e1c\u673a\u573a-\u9999\u6e2f\u673a\u573a'},
            #                           {u'baggageDesc': u'\u6210\u4eba:\u4e00\u51712\u4ef6;\u513f\u7ae5:\u4e00\u51712\u4ef6',
            #                            u'itinerary': u'\u9999\u6e2f\u673a\u573a-\u5965\u514b\u5170\u673a\u573a'}]}, u'segments': [
            #         {u'segmentIndex': 1, u'depAirportCode': u'SHA', u'cabinCode': u'D', u'arrDatetime': u'2019-04-15 14:00', u'arrAirportCode': u'HRB', u'airline': u'MU', u'segmentType': u'GO',
            #          u'depDatetime': u'2019-04-15 10:00', u'flightNo': u'MU222'}], u'policyInfos': [{u'dateInfo': [u'\u9500\u552e\u65e5\u671f:2019-03-21\u81f32019-06-30',
            #                                                                                                        u'\u53bb\u7a0b\u65c5\u884c\u65e5\u671f:2019-04-01\u81f32019-06-30',
            #                                                                                                        u'\u56de\u7a0b\u65c5\u884c\u65e5\u671f:2019-04-01\u81f32019-06-30',
            #                                                                                                        u'\u63d0\u524d\u51fa\u7968\u5929\u6570:3\u5929',
            #                                                                                                        u'\u9002\u7528\u65c5\u5ba2:\u666e\u901a\u6210\u4eba'],
            #                                                                                          u'priceInfo': [u'\u4ee3\u7406\u8d39:0%', u'\u6210\u4eba\u8fd4\u70b9:7%',
            #                                                                                                         u'\u6210\u4eba\u7559\u94b1:-10',
            #                                                                                                         u'1/2RT\u4f63\u91d1\u8ba1\u7b97\u53d6\u4e25\u903b\u8f91:\u53d6\u5c11',
            #                                                                                                         u'\u5f00\u7968\u8d39:0', u'\u662f\u5426\u8f6c\u79c1\u6709:\u662f',
            #                                                                                                         u'\u9000\u6539\u8d39\u7528(\u767e\u5206\u6bd4):50', u'\u5e01\u79cd:CNY'],
            #                                                                                          u'otherInfo': [u'\u8fd0\u4ef7\u7c7b\u578b:\u516c\u5e03\u8fd0\u4ef7',
            #                                                                                                         u'\u662f\u5426\u4ec5\u9650\u76f4\u8fbe\u8fd0\u4ef7:\u4e0d\u9650',
            #                                                                                                         u'farebasis\u9650\u5236:\u4e0d\u9650', u'\u81ea\u52a8\u51fa\u7968:\u5426',
            #                                                                                                         u'\u62a5\u9500\u51ed\u8bc1:\u884c\u7a0b\u5355',
            #                                                                                                         u'\u9884\u8ba2\u914d\u7f6e:\u540c\u7a0b\u9884\u8ba2', u'\u6388\u6743office:SHA255'],
            #                                                                                          u'lineInfo': [u'\u5f00\u7968\u822a\u53f8:HX', u'\u51fa\u53d1\u5730:SHA',
            #                                                                                                        u'\u76ee\u7684\u5730:NZ,AU,TNOA',
            #                                                                                                        u'\u9002\u7528\u8231\u4f4d:\u5168\u90e8\u4ed3\u4f4d',
            #                                                                                                        u'\u662f\u5426\u9002\u7528\u4e8e\u8054\u8fd0:\u5426',
            #                                                                                                        u'\u662f\u5426\u9002\u7528\u4e8e\u5171\u4eab\u822a\u73ed:\u975e\u5171\u4eab',
            #                                                                                                        u'\u662f\u5426\u9002\u7528\u4e8e\u4e2d\u8f6c:\u4e0d\u9650',
            #                                                                                                        u'\u53ef\u552e\u822a\u73ed:\u65e0\u9650\u5236',
            #                                                                                                        u'\u7981\u552e\u822a\u73ed:\u65e0\u9650\u5236',
            #                                                                                                        u'\u662f\u5426\u7f3a\u53e3:\u4e0d\u9650'],
            #                                                                                          u'baseInfo': [u'\u653f\u7b56\u5e8f\u53f7:01650810677294819328000432',
            #                                                                                                        u'\u8fd0\u884c\u72b6\u6001:\u6295\u653e\u4e2d', u'\u51fa\u7968PCC:SZV122',
            #                                                                                                        u'GDS:IBE', u'\u6587\u4ef6\u7f16\u53f7:YyouSHASSYING',
            #                                                                                                        u'\u9002\u7528\u884c\u7a0b\u7c7b\u578b:\u5355\u7a0b&\u5f80\u8fd4',
            #                                                                                                        u'\u662f\u5426\u5141\u8bb81/2RT\u7ec4\u5408:\u662f',
            #                                                                                                        u'\u53ef\u7ec4\u5408\u6587\u4ef6\u7f16\u53f7:ZHAOSHANG1',
            #                                                                                                        u'\u4ea7\u54c1\u7c7b\u578b:\u666e\u901a\u4ea7\u54c1'],
            #                                                                                          u'policyId': u'01650810677294819328000432', u'refInfo': []}], u'orderStatus': u'ISSUE_FINISH',
            #                                                                                                                                       u'tripType': u'OW',
            #                                                                                                                                       u'tcSerialNo': u'IT3PPK190322LJGG9213',
            #                                                                                                                                       u'engineSerialNo': u'BJ1903221135126508409363618750464',
            #                                                                                                                                       u'issueTickets': [{u'segmentIndex': 2,
            #                                                                                                                                                          u'passengerId': u'1ad30e8b-71ca-47f0-a862-f01c2005bdd6',
            #                                                                                                                                                          u'ticketNo': u'851-3677811802'},
            #                                                                                                                                                         {u'segmentIndex': 1,
            #                                                                                                                                                          u'passengerId': u'1ad30e8b-71ca-47f0-a862-f01c2005bdd6',
            #                                                                                                                                                          u'ticketNo': u'851-3677811802'}],
            #                                                                                                                                       u'createTime': u'2019-03-22 11:57:00'}}

            Logger().info("========== poll order detail result : {}".format(result))
            if not result['result']:
                raise OrderByPollException(result)

            order_detail = result['data']
            # 检查是否是投放的政策
            policy_info = order_detail['policyInfos']
            Logger().info("============== policy info :{}======".format(policy_info))
            have_policy = False
            for p in policy_info:
                for b in p['baseInfo']:
                    if 'YyouSHASSYING' in b or 'YYOUSHASSYING' in b:
                        have_policy = True
                        break
            if not have_policy:
                continue

            Logger().debug('to process detail result %s' % result)
            oi = OrderInfo()
            # 允许降舱
            oi.allow_cabin_downgrade = 0

            oi.ota_order_id = ota_order_id
            oi.assoc_order_id = order['engineSerialNo']
            oi.ota_create_order_time = order_detail['createTime']
            oi.trip_type = order_detail['tripType']

            sorted_segments = sorted(order_detail['segments'], key=lambda x: x['segmentIndex'])
            go_segments = [s for s in sorted_segments if s['segmentType'] == 'GO']
            back_segments = [s for s in sorted_segments if s['segmentType'] == 'BACK']
            oi.from_date = datetime.datetime.strptime(go_segments[0]['depDatetime'],
                                                      '%Y-%m-%d %H:%M').strftime('%Y-%m-%d')
            oi.from_airport = go_segments[0]['depAirportCode']
            oi.to_airport = go_segments[-1]['arrAirportCode']
            oi.ret_date = datetime.datetime.strptime(back_segments[0]['depDatetime'],
                                                      '%Y-%m-%d %H:%M').strftime('%Y-%m-%d') if back_segments else None

            # TODO 获取不到舱等，暂时写死
            oi.cabin_grade = 'Y'

            adult_price = 0
            adult_tax = 0
            child_price = 0
            child_tax = 0
            adult_count = 0
            child_count = 0
            oi.ota_pay_price = order_detail['priceInfo']['amount']
            for pax in order_detail['passengers']:
                pax_info = PaxInfo()
                pax_info.passenger_id = '{}@{}'.format(pax['passengerId'],
                                                       json.dumps([i['segmentIndex'] for i in order_detail['issueTickets'] if i['passengerId'] == pax['passengerId']]))
                pax_info.last_name = pax['lastName']
                pax_info.first_name = pax['firstName']
                # pax_info.name = pax.get('PassengerName', '')
                pax_info.pnr = pax['pnr']
                pax_info.age_type = pax['passengerType']
                if pax_info.age_type == 'ADT':
                    adult_price = pax['totalPrice']
                    adult_tax = pax['totalTax']
                    adult_count += 1
                elif pax_info.age_type == 'CHD':
                    child_price = pax['totalPrice']
                    child_tax = pax['totalTax']
                    child_count += 1
                else:
                    raise OrderByPollException('age_type invalid %s' % pax['PassengerType'])

                pax_info.birthdate = pax['birthday']
                # 这里一律作为护照处理
                pax_info.card_type = pax['certificateType']
                pax_info.used_card_type = pax['certificateType']
                pax_info.used_card_no = pax['certificateNo']
                pax_info.card_pp = pax['certificateNo']
                pax_info.gender = pax['gender']
                pax_info.card_expired = pax['cardExpired']
                pax_info.nationality = pax['nationality']
                # TODO 暂时给国籍国家
                pax_info.card_issue_place = pax['nationality']
                pax_info.attr_competion()
                oi.passengers.append(pax_info)
            oi.adt_count = adult_count
            oi.chd_count = child_count
            oi.inf_count = 0

            contact_info = ContactInfo()
            contact_info.name = Random.gen_full_name()
            contact_info.mobile = TBG.global_config['OPERATION_CONTACT_MOBILE']
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

            routing_number = 1

            for segment in go_segments:
                flight_segment = FlightSegmentInfo()
                flight_segment.carrier = segment['flightNo'][:2]
                flight_segment.dep_airport = segment['depAirportCode']
                flight_segment.dep_time = datetime.datetime.strptime(segment['depDatetime'], '%Y-%m-%d %H:%M'
                                                                     ).strftime('%Y-%m-%d %H:%M:%S')
                flight_segment.arr_airport = segment['arrAirportCode']
                flight_segment.arr_time = datetime.datetime.strptime(segment['arrDatetime'], '%Y-%m-%d %H:%M'
                                                                     ).strftime('%Y-%m-%d %H:%M:%S')
                flight_segment.cabin = segment['cabinCode']
                flight_segment.cabin_count = 9
                flight_segment.flight_number = segment['flightNo']
                # TODO 获取不到舱等，暂时写死
                flight_segment.cabin_grade = 'Y'
                flight_segment.routing_number = routing_number
                routing_number += 1
                flight_routing.from_segments.append(flight_segment)

            for segment in back_segments:
                flight_segment = FlightSegmentInfo()
                flight_segment.carrier = segment['flightNo'][:2]
                flight_segment.dep_airport = segment['depAirportCode']
                flight_segment.dep_time = datetime.datetime.strptime(segment['depDatetime'], '%Y-%m-%d %H:%M'
                                                                     ).strftime('%Y-%m-%d %H:%M:%S')
                flight_segment.arr_airport = segment['arrAirportCode']
                flight_segment.arr_time = datetime.datetime.strptime(segment['arrDatetime'], '%Y-%m-%d %H:%M'
                                                                     ).strftime('%Y-%m-%d %H:%M:%S')
                flight_segment.cabin = segment['cabinCode']
                flight_segment.cabin_count = 9
                flight_segment.flight_number = segment['flightNo']
                # TODO 获取不到舱等，暂时写死
                flight_segment.cabin_grade = 'Y'
                flight_segment.routing_number = routing_number
                routing_number += 1
                flight_routing.ret_segments.append(flight_segment)

            # 补充舱位和舱等
            select_provider = 'N/A'
            select_provider_channel = 'N/A'

            rk_dep_time = datetime.datetime.strptime(go_segments[0]['depDatetime'], '%Y-%m-%d %H:%M').strftime('%Y%m%d%H%M')
            rk_arr_time = datetime.datetime.strptime(go_segments[-1]['arrDatetime'], '%Y-%m-%d %H:%M').strftime('%Y%m%d%H%M')
            rk_flight_no = '-'.join([s.flight_number for s in flight_routing.from_segments])
            rk_cabin = '-'.join([s.cabin for s in flight_routing.from_segments])
            rk_cabin_grade = '-'.join([s.cabin_grade for s in flight_routing.from_segments])

            if flight_routing.ret_segments:
                rk_dep_time = '{},{}'.format(rk_dep_time, datetime.datetime.strptime(
                    back_segments[0]['depDatetime'], '%Y-%m-%d %H:%M').strftime('%Y%m%d%H%M'))
                rk_arr_time = '{},{}'.format(rk_arr_time, datetime.datetime.strptime(
                    back_segments[-1]['arrDatetime'], '%Y-%m-%d %H:%M').strftime('%Y%m%d%H%M'))
                rk_flight_no = '{},{}'.format(rk_flight_no, '-'.join(
                    [s.flight_number for s in flight_routing.ret_segments]))
                rk_cabin = '{},{}'.format(rk_cabin, '-'.join(
                    [s.cabin for s in flight_routing.ret_segments]))
                rk_cabin_grade = '{},{}'.format(rk_cabin_grade, '-'.join(
                    [s.cabin_grade for s in flight_routing.ret_segments]))



            rk_info = RoutingKey.serialize(
                from_airport=oi.from_airport, dep_time=rk_dep_time,
                to_airport=oi.to_airport, arr_time=rk_arr_time,
                flight_number=rk_flight_no, cabin=rk_cabin,
                cabin_grade=rk_cabin_grade, product='COMMON',
                adult_price=adult_price, adult_tax=adult_tax,
                provider_channel=select_provider_channel,
                child_price=child_price,
                child_tax=child_tax, provider=select_provider,
                inf_price=child_price, inf_tax=child_tax,
                search_from_airport=oi.from_airport,
                search_to_airport=oi.to_airport,
                from_date=oi.from_date,
                ret_date=oi.ret_date,
                routing_range=oi.routing_range,
                trip_type=oi.trip_type,
                is_multi_segments=1 if len(flight_routing.from_segments) > 1 or flight_routing.ret_segments else 0
            )

            Logger().info("========= routing key : {}".format(rk_info['plain']))
            oi.verify_routing_key = rk_info['encrypted']
            flight_routing.routing_key = rk_info['encrypted']
            flight_routing.routing_key_detail = rk_info['plain']
            oi.routing = flight_routing

            order_list.append(oi)

        Logger().info("============== filtered order list : {}".format(order_list))
        return order_list
        # return []


if __name__ == '__main__':
    pass
