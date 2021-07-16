#!/usr/bin/env python
# -*- coding: utf-8 -*-


import time
import json
import random
import re
import gevent
import base64
import datetime
import requests
from copy import deepcopy
from bs4 import BeautifulSoup
from ..controller.http_request import HttpRequest
from bs4 import BeautifulSoup
from lxml import etree
from urllib import quote
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
from .base import ProvderAutoBase
from ..utils.logger import Logger
from ..utils.util import cn_name_to_pinyin
from ..controller.captcha import CaptchaCracker
from ..utils.exception import *
from ..utils.util import Time, Random, md5_hash, convert_utf8,RoutingKey, simple_decrypt
from ..dao.iata_code import IATA_CODE
from ..dao.models import *
from ..dao.internal import *
from ..utils.triple_des_m import desenc
from ..controller.smser import Smser
from app import TBG
from ..utils.blowfish import Blowfish


class Ch(ProvderAutoBase):
    timeout = 50  # 请求超时时间
    provider = 'ch'  # 子类继承必须赋
    provider_channel = 'ch_web'  # 子类继承必须赋
    operation_product_type = '会员折扣'  # 运价类型：0: GDS公布运价 1:GDS私有运价 2:航司官网产品  3:廉价航司产品 4:特价产品
    operation_product_mode = 'A2A'
    pay_channel = 'YEEPAY'
    is_display = True
    ch_public_key_pem = '-----BEGIN PUBLIC KEY-----\nMIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCJI6hXHl9opVoUlZ8cPRlBNCoT\nDpCr2B3X6dAZzgwhuXLJRDzBdt4/12NcHZHV7oJE3FvDMc7zTyjaY5Z4FN+1cpRt\nGpWbgNdXcwzEQDb9GMwE5YpKzZ6TKBhLX3USkQqbNOv3bgsvkiCuHinmRAJYv3kz\nbX8sqvWVffsziYDviwIDAQAB\n-----END PUBLIC KEY-----\n'
    is_include_booking_module = True  # 是否包含下单模块
    no_flight_ttl = 3600 * 3 # 无航班缓存超时时间设定
    carrier_list = ['9C']  # 供应商所包含的航司列表，如果包含多个并且无法确定，请不要填写，此处会关联执飞航线判断逻辑

    # is_order_directly = True


    CACHE_PR_CONFIG = {
        1: {'cabin_expired_time': 3600 * 12, 'cabin_attenuation': 3,'fare_expired_time':86400 * 30},
        2: {'cabin_expired_time': 3600 * 3, 'cabin_attenuation': 2,'fare_expired_time':86400 * 20},
        3: {'cabin_expired_time': 60 * 60 * 1, 'cabin_attenuation': 1,'fare_expired_time':86400 * 10},
        4: {'cabin_expired_time': 60 * 40, 'cabin_attenuation': 1,'fare_expired_time':86400 * 5},
        5: {'cabin_expired_time': 60 * 30, 'cabin_attenuation': 0,'fare_expired_time':86400},

    }
    search_interval_time = 0.3

    def __init__(self):
        super(Ch, self).__init__()

        self.account_list = [
            {'username': 'jun108650@tongdun.org',        'password': 'bigsec@2018', 'birthdate': '1990-10-02', 'gender': 'F',},
            {'username': 'li622622@tongdun.org',         'password': 'bigsec@2018', 'birthdate': '1970-04-09', 'gender': 'M',},
            {'username': 'shengang7853@tongdun.org',     'password': 'bigsec@2018', 'birthdate': '1970-04-09', 'gender': 'M',},
            {'username': 'yuanyan4771@tongdun.org',      'password': 'bigsec@2018', 'birthdate': '1995-01-10', 'gender': 'M',},
            {'username': 'oyang5812@tongdun.org',        'password': 'bigsec@2018', 'birthdate': '1983-10-28', 'gender': 'M',},
            {'username': 'fang481950@tongdun.org',       'password': 'bigsec@2018', 'birthdate': '1973-01-24', 'gender': 'F',},
            {'username': 'ping835412@tongdun.org',       'password': 'bigsec@2018', 'birthdate': '1994-06-17', 'gender': 'F',},
            {'username': 'guiyingzhao3126@tongdun.org',  'password': 'bigsec@2018', 'birthdate': '1989-02-26', 'gender': 'F',},
            {'username': 'jinlei5799@btbvs.com',         'password': 'bigsec@2018', 'birthdate': '1982-07-09', 'gender': 'M',},
            {'username': 'qinxiulan7752@btbvs.com',      'password': 'bigsec@2018', 'birthdate': '1982-07-09', 'gender': 'M',},
            {'username': 'ldu9600@btbvs.com',            'password': 'bigsec@2018', 'birthdate': '1992-04-24', 'gender': 'F',},
            {'username': 'yuanyong5903@btbvs.com',       'password': 'bigsec@2018', 'birthdate': '1984-10-17', 'gender': 'F',},
            {'username': 'guiyingyang7610@btbvs.com',    'password': 'bigsec@2018', 'birthdate': '1987-10-26', 'gender': 'F',},

            {'username': 'yang461019@btbvs.com', 'password': 'bigsec@2018', 'birthdate': '1970-04-09',
             'gender': 'M', },
            {'username': 'yangzhou8258@btbvs.com', 'password': 'bigsec@2018', 'birthdate': '1970-04-09',
             'gender': 'M', },
            {'username': 'min424392@btbvs.com', 'password': 'bigsec@2018', 'birthdate': '1987-08-19',
             'gender': 'F', },
            {'username': 'tangjuan4090@btbvs.com', 'password': 'bigsec@2018', 'birthdate': '1968-01-12',
             'gender': 'F', },
            {'username': 'mingcao1275@btbvs.com', 'password': 'bigsec@2018', 'birthdate': '1988-10-29',
             'gender': 'F', },
        ]

        if not TBG.redis_conn.redis_pool.llen('ch_account_list') == len(self.account_list):
            TBG.redis_conn.redis_pool.expire('ch_account_list', 0)
            for account in self.account_list:
                TBG.redis_conn.redis_pool.lpush('ch_account_list', account)

    def init_cookies(self, http_session):

        gr_session_id_key = '9683d26dac5{}'.format(random.randint(10000, 99999))
        gr_session_id_value = '38111f90-3f6f-42ed-a6d4-5fae56f{}'.format(random.randint(10000, 99999))

        cookie_dict = {
            'PcPopAd_VisitWebSite': '2018-07-30 21:14:06',
            'PcPopAd_XRL1531807581658': '',
            'gr_user_id': '56cd0a56-2567-4cd8-bb56-cb36b68{}'.format(random.randint(10000, 99999)),
            '_ga': 'GA1.2.79118168.1532956452',
            'IsShowTaxprice': 'false',
            'c1': 'edmin_zn_sys_active_active',
            'PcPopAd_LoginMark': '2018-08-02 15:12:53',
            'hasProcessIP': '1',
            '__pointstatus__': 'MA==',
            '_gid': 'GA1.2.1358741534.{}'.format(int(time.time())),
            'preloadJs': '.js%3Fvs%3Dv2018080305',
            'PcPopAd_BJA1533261908639': '',
            'PcPopAd_BJC1533262064671': '',
            'loginTime': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'g_refresh': '0',
            'gr_session_id_{}'.format(gr_session_id_key): gr_session_id_value,
            'hideQRCount': '0',
            'qrCount': '0',
            'count': '3',
            's1': 'Mac',
            's2': 'WEB',
            's3': 'zh-cn',
            's4': '6e823de713264794bff71b8649d{}'.format(random.randint(10000, 99999)),
            's5': '2',
            's6': 'c0facd20e97e468d9dc65c63a5d{}'.format(random.randint(10000, 99999)),
            'gr_session_id_{}_{}'.format(gr_session_id_key, gr_session_id_value): 'true',
            '_gat': '1',
            'acw_tc': 'AQAAAPbO1DgB8gIAHArii5GyF7FdNtOI',
        }

        http_session.update_cookie(cookie_dict=cookie_dict)

        return http_session

    def get_tokenid(self, http_session):

        query_str = '?t={}'.format('0.{}145502{}'.format(random.randint(10000, 99999), random.randint(10000, 99999)))
        url = 'https://passport.ch.com/LimitTest/Captcha{}'.format(query_str)
        result = http_session.request(url=url, method='GET', verify=False)

        Logger().debug('get tokenid result cookies: {}'.format(json.dumps(http_session.get_cookies())))
        jar = http_session.get_cookies()
        tokenid = jar.get('_tokenId_')
        if not tokenid:
            raise LoginCritical('have no tokenid')
        else:
            return http_session

    def convert_unicode_char_to_byte(self, input_unicode):

        if not input_unicode:
            return ''
        if not isinstance(input_unicode, unicode):
            return ''

        result = '%u'
        for index, char in enumerate(input_unicode.encode('utf-16be')):
            hex_char = hex(ord(char))
            if len(hex_char) < 4:
                hex_char = hex_char[-1].zfill(2)
            else:
                hex_char = hex_char[-2:]
            result += hex_char.upper()
            if index > 0 and index % 2 == 1:
                result += '%u'

        if result.endswith('%u'):
            result = result[: -2]
        return result

    def _login(self, http_session, ffp_account_info):
        """
        登陆模块
        :return: 登陆成功的httpResult 对象
        """

        http_session = self.init_cookies(http_session)
        http_session = self.get_tokenid(http_session)

        username = ffp_account_info.username
        password = ffp_account_info.password
        public_key = RSA.importKey(self.ch_public_key_pem)
        public_key = PKCS1_v1_5.new(public_key)
        if isinstance(username, unicode):
            username = username.encode('utf8')
        if isinstance(password, unicode):
            password = password.encode('utf8')
        encrypt_username = base64.b64encode(public_key.encrypt(username))
        encrypt_password = base64.b64encode(public_key.encrypt(password))

        url = 'https://passport.ch.com/zh_cn/Login/DoLogin'
        post_data = {
            'UserNameInput': encrypt_username,
            'undefined': '0',
            'PasswordInput': encrypt_password,
            'IsKeepLoginState': False,
            'loginType': 'PC',
        }
        result = http_session.request(url=url, method='POST', data=post_data, verify=False)

        success = False
        for jar_key in http_session.get_cookies().keys():
            if jar_key.startswith('CZYSTS'):
                success = True
                break

        if not success:
            raise LoginCritical('login have no CZYSTS cookies!')

        query_str = '?wa=wsignin1.0&wtrealm=https%3A%2F%2Fwww.ch.com%2F&wctx=rm%3D0%26id%3Dpassive%26ru%3Dhttps%253A%252F%252Fwww.ch.com%252FauthClient%252FAuthHepler%252FLoginTempIndex%253Fstrcmd%253Dwindow.parent.parent.%2524.fn.head.updateUser(%252522level%252522)%253B%2526parentUrl%253Dhttps%253A%252F%252Fwww.ch.com%252F&wct=2018-7-2T8%3A59%3A0Z&wreply=https%3A%2F%2Fwww.ch.com%2F'
        result = http_session.request(url='https://passport.ch.com/{}'.format(query_str), method='GET',
                                      verify=False)
        html = etree.HTML(result.content)
        wa = html.xpath('//input[@name="wa"]/@value')
        if wa:
            wa = wa[0]
        else:
            raise LoginCritical('have no wa!')
        wresult = html.xpath('//input[@name="wresult"]/@value')
        if wresult:
            wresult = wresult[0].replace("&lt;", "<")
        else:
            raise LoginCritical('have no wresult')
        wctx = html.xpath('//input[@name="wctx"]/@value')
        if wctx:
            wctx = wctx[0]
        else:
            raise LoginCritical('have no wctx')

        post_data = {
            'wa': wa,
            'wresult': wresult,
            'wctx': wctx,
        }
        result = http_session.request(url='https://www.ch.com/', method='POST', data=post_data,
                                      verify=False, allow_redirects=False)

        fedauth = http_session.get_cookies().get('FedAuth')
        if not fedauth:
            raise LoginCritical('have no fedauth!')
        return http_session

    def _check_login(self, http_session):
        """
        检查登录状态
        :param http_session:
        :return:
        """
        url = 'https://account.ch.com/order/flights'
        result = http_session.request(url=url, method='GET', verify=False)

        if not result.response_status_code == 200:
            return False

        html = etree.HTML(result.content)
        title_text = html.xpath('//title/text()')

        if title_text and title_text[0] == 'Working...':
            wa = html.xpath('//input[@name="wa"]/@value')
            if wa:
                wa = wa[0]
            else:
                return False
            wresult = html.xpath('//input[@name="wresult"]/@value')
            if wresult:
                wresult = wresult[0].replace("&lt;", "<")
            else:
                return False
            wctx = html.xpath('//input[@name="wctx"]/@value')
            if wctx:
                wctx = wctx[0]
            else:
                return False

            post_data = {
                'wa': wa,
                'wresult': wresult,
                'wctx': wctx,
            }
            gevent.sleep(0.8)
            result = http_session.request(url='https://account.ch.com/', method='POST', data=post_data,
                                          verify=False, allow_redirects=False)

            fedauth = http_session.get_cookies().get('FedAuth')
            if not fedauth:
                return False
            return True
        elif title_text:
            return True
        else:
            return False

    # def _register(self, http_session, pax_info, ffp_account_info):
    #     """
    #     注册模块
    #     """
    #     password = 'bigsec@2018'
    #     http_session = self.init_cookies(http_session)
    #     http_session = self.get_tokenid(http_session)
    #     now_timestamp_ms = int(time.time() * 1000)
    #     url = 'https://account.ch.com/default/initValidate?t={}&_={}'.format(
    #         str(now_timestamp_ms)[-3:], now_timestamp_ms)
    #     result = http_session.request(url=url, method="GET", verify=False)
    #
    #     challenge_body = json.loads(result.content)
    #     challenge_body = json.loads(challenge_body)
    #
    #     gt = challenge_body.get('gt')
    #     if not gt:
    #         raise RegisterException('have no geetest gt!')
    #     challenge = challenge_body.get('challenge')
    #     if not challenge:
    #         raise RegisterException('have no geetest challenge')
    #
    #     cracker = CaptchaCracker.select('C2567')
    #     checked_gee = cracker.crack(geetest_gt=gt, geetest_challenge=challenge)
    #     geetest_challenge = checked_gee['challenge']
    #     geetest_validate = checked_gee['validate']
    #     geetest_seccode = checked_gee['validate'] + '|jordan'
    #
    #     public_key = RSA.importKey(self.ch_public_key_pem)
    #     public_key = PKCS1_v1_5.new(public_key)
    #
    #     encrypt_password = base64.b64encode(public_key.encrypt(password))
    #     email_address = Random.gen_email(domain='btbvs.com')
    #     Logger().debug("register email address : {}".format(email_address))
    #
    #     result = http_session.request(url='https://account.ch.com/Regist/DoRegist', data={
    #         'RegAccount': email_address,
    #         'Password': encrypt_password,
    #         'RepeatPassword': encrypt_password,
    #         'geetest_challenge': geetest_challenge,
    #         'geetest_validate': geetest_validate,
    #         'geetest_seccode': geetest_seccode,
    #         'RegistType': 3,
    #     }, method="POST", verify=False)
    #
    #     load_data = json.loads(result.content)
    #     CustomText = load_data.get('CustomText')
    #
    #     if not CustomText:
    #         raise RegisterException("regist post result have no CustomText")
    #
    #     # 发送邮件
    #     result = http_session.request('https://account.ch.com/regist/RegistrationSuccessMail?p={}'.format(CustomText),
    #                                   method="GET", verify=False)
    #
    #     if not result.response_status_code == 200:
    #         raise RegisterException("send email failure!")
    #     mails = TBG.mailer.get_mail_via_receiver(receiver=email_address)
    #     element = etree.HTML(mails)
    #     regist_active_path = element.xpath(
    #         '//a[@style="color:#fff;background:#f9a701;padding:5px 15px;margin:0 5px;border-radius:5px;text-decoration:none;"]/@href')
    #     if regist_active_path:
    #         regist_active_path = regist_active_path[0]
    #         result = requests.get(regist_active_path, verify=False)
    #         if result.status_code == 200:
    #             ffp_account_info.username = email_address
    #             ffp_account_info.password = password
    #             ffp_account_info.provider = self.provider
    #             # ffp_account_info.reg_passport = random_passport
    #             ffp_account_info.reg_birthdate = pax_info.birthdate
    #             ffp_account_info.reg_gender = pax_info.gender
    #             # ffp_account_info.reg_card_type = 'PP'
    #             return ffp_account_info
    #         else:
    #             raise RegisterException("register active email failure!")
    #     else:
    #         raise RegisterException("register have no active email path!")

    def _register(self, http_session, pax_info, ffp_account_info):

        account = self._get_fix_account()
        ffp_account_info.username = account['username']
        ffp_account_info.password = account['password']
        ffp_account_info.provider = self.provider
        ffp_account_info.reg_birthdate = account['birthdate']
        ffp_account_info.reg_gender = account['gender']
        return ffp_account_info

    def _get_fix_account(self):

        account = TBG.redis_conn.redis_pool.rpoplpush('ch_account_list', 'ch_account_list')
        account = eval(account) if account else random.choice(self.account_list)

        return account

    def elem_combination(self, src_data, targ_data):

        tmp_data = []

        if not src_data:
            for i in targ_data:
                tmp_data.append([i])
        else:
            for i in src_data:
                for j in targ_data:
                    src = deepcopy(i)
                    src.append(j)
                    tmp_data.append(src)
        return tmp_data

    def format_products(self, http_session, search_routes):
        '''
        将春秋route格式化成标准products
        :return:
        '''

        product_list = []

        '''
            product_list = [
                {
                    route_id_list: []
                    segment_info: [
                        {},
                        {},
                    ],
                    cabin_info: [
                        {},
                        {},
                    ]
                },
                {},
                {},
            ]
        '''
        for routing in search_routes:
            route_id_list = []
            segment_id_list = []
            segment_dict = {}
            route_seg_type = 1 if len(routing) == 1 else 3
            for segment in routing:
                segment_id_list.append(segment['SegmentId'])
                gevent.sleep(0.5)
                # 查询仓位详情
                post_data = {
                    u'ActId': None,
                    u'AircraftCabins': segment['AircraftCabins'],
                    u'ArrivalAirportCode': segment['DepartureAirportCode'],
                    u'Currency': 0,
                    u'DepartureAirportCode': segment['ArrivalAirportCode'],
                    u'FDate': segment['DepartureTimeBJ'],
                    u'FlightsNo': segment['No'],
                    u'IfRet': False,
                    u'IsBg': False,
                    u'IsIJFlight': False,
                    u'IsLittleGroupFlight': False,
                    u'RouteArea': segment['RouteArea'],
                    u'RouteSegType': route_seg_type,
                    u'SType': 0,
                    u'Segment': segment['DepartureCode'] + segment['ArrivalCode'],
                    u'SegmentId': segment_id_list,
                    u'SegmentPart': 10,
                    u'isEmployee': False
                }

                result = http_session.request(url='https://flights.ch.com/Flights/CabinDetails', data={
                    'param': json.dumps(post_data)
                }, method='POST', verify=False)

                cabin_details = json.loads(result.content)
                segment['AircraftCabin'] = cabin_details['AircraftCabin']

                if segment['RouteId'] in route_id_list:
                    segment_dict[segment['RouteId']].append(segment)
                else:
                    route_id_list.append(segment['RouteId'])
                    segment_dict[segment['RouteId']] = [segment]

            format_segment_list = []
            for route_id in route_id_list:
                format_segment_list = self.elem_combination(format_segment_list, segment_dict[route_id])

            for i in format_segment_list:
                for j in xrange(len(i[0]['AircraftCabin'])):
                    cabin_list = []
                    for seg in i:
                        cabin_list.append(seg['AircraftCabin'][j])
                    product_info = {
                        'segment_info': i,
                        'cabin_info': cabin_list,
                    }

                    product_list.append(product_info)

        return product_list

    def generate_routing_key(self, product, search_info):

        segment_list = product['segment_info']

        # routing key:
        #   起飞城市code + 13位起飞时间戳 + 到达城市 + 13位到达时间戳 + flight no + cabin level + 成人价格 + 成人税 + 儿童价格 + 儿童税 + 婴儿价格 + 婴儿税
        start_time = datetime.datetime.strptime(segment_list[0]['DepartureTime'], '%Y-%m-%d %H:%M:%S')
        end_time = datetime.datetime.strptime(segment_list[-1]['ArrivalTime'], '%Y-%m-%d %H:%M:%S')

        adult_price = 0.0
        adult_tax = 0.0
        child_price = 0.0
        child_tax = 0.0
        inf_price = 0.0
        inf_tax = 0.0
        for index, segment in enumerate(segment_list):
            adult_price += product['cabin_info'][index]['AircraftCabinInfos'][0]['Price']
            adult_tax += product['cabin_info'][index]['AircraftCabinInfos'][0]['AirportConstructionFees']
            adult_tax += product['cabin_info'][index]['AircraftCabinInfos'][0]['FuelSurcharge']
            if product['cabin_info'][index]['AircraftCabinInfos'][0].get('OtherFees'):
                adult_tax += product['cabin_info'][index]['AircraftCabinInfos'][0]['OtherFees']
            if product['cabin_info'][index]['AircraftCabinInfos'][0].get('AbroadFee'):
                adult_tax += product['cabin_info'][index]['AircraftCabinInfos'][0]['AbroadFee']['Fee']

            child_price += product['cabin_info'][index]['AircraftCabinInfos'][1]['Price']
            child_tax += product['cabin_info'][index]['AircraftCabinInfos'][1]['AirportConstructionFees']
            child_tax += product['cabin_info'][index]['AircraftCabinInfos'][1]['FuelSurcharge']
            if product['cabin_info'][index]['AircraftCabinInfos'][1].get('OtherFees'):
                child_tax += product['cabin_info'][index]['AircraftCabinInfos'][1]['OtherFees']
            if product['cabin_info'][index]['AircraftCabinInfos'][1].get('AbroadFee'):
                child_tax += product['cabin_info'][index]['AircraftCabinInfos'][1]['AbroadFee']['Fee']

            inf_price += product['cabin_info'][index]['AircraftCabinInfos'][2]['Price']
            inf_tax += product['cabin_info'][index]['AircraftCabinInfos'][2]['AirportConstructionFees']
            inf_tax += product['cabin_info'][index]['AircraftCabinInfos'][2]['FuelSurcharge']
            if product['cabin_info'][index]['AircraftCabinInfos'][2].get('OtherFees'):
                inf_tax += product['cabin_info'][index]['AircraftCabinInfos'][2]['OtherFees']
            if product['cabin_info'][index]['AircraftCabinInfos'][2].get('AbroadFee'):
                inf_tax += product['cabin_info'][index]['AircraftCabinInfos'][2]['AbroadFee']['Fee']

        rk_info = RoutingKey.serialize(
            from_airport=segment_list[0]['DepartureAirportCode'],
            dep_time=start_time,
            to_airport=segment_list[-1]['ArrivalAirportCode'],
            arr_time=end_time,
            flight_number='-'.join([s['No'] for s in segment_list]),
            cabin='-'.join([c['AircraftCabinInfos'][0]['Name'] for c in product['cabin_info']]),
            cabin_grade='-'.join(['Y' for c in product['cabin_info']]),
            product='COMMON',
            adult_price=adult_price,
            adult_tax=adult_tax,
            provider_channel=self.provider_channel,
            provider=self.provider,
            child_price=child_price,
            child_tax=child_tax,
            inf_price=inf_price,
            inf_tax=inf_tax,
            search_from_airport=search_info.from_airport,
            search_to_airport=search_info.to_airport,
            from_date=search_info.from_date,
            trip_type=search_info.trip_type,
            routing_range=search_info.routing_range,
            is_include_operation_carrier=0,
            is_multi_segments=1 if len(segment_list) > 1 else 0
        )

        return rk_info['plain'], rk_info['encrypted']

    def _flight_search(self, http_session, search_info):
        """
        航班爬取模块，
        TODO :目前只考虑单程
        :return:
        """

        # 搜索上海到深圳 2018-11-02 1个成人
        """
        没有航班

        {"adtNum":"0","airResultDto":null,"blockPrice":0,"cabinNames":{"business":null,"economy":null,"first":null,"lowest":null,"luxury":null,"more":null},"chdNum":"0","currency":"CNY","fareType":null,"infNum":"0","intervalTime":"180","itemType":"2","pageNumber":"0","pageSize":"0","resultCode":"OTR11002","resultMsg":"æ¨éæ©çèªçº¿æ²¡æèªç­è®¡åï¼è¯·åèä»·æ ¼æ¥åï¼éæ°éæ©åºåæ¥æ OTR11002","resultType":"05","sessionId":"","shopLandFlightResultNum":"0","taxCurrency":"CNY","timeStamp":null,"travelType":null,"uuid":""}
        """

        # gevent.sleep(1)
        Logger().debug('search flight')

        cn_city_mapping = {
            '香港': '香港(中国香港)',
            '澳门': '澳门(中国澳门)',
            '高雄': '高雄(中国台湾)',
            '台北': '台北(中国台湾)',
            '东京成田': '东京(成田)',
            '东京羽田': '东京(羽田)',
            '东京': '茨城(东京)',
            '佐贺': '佐贺(福冈)',
            '亚庇': '亚庇(哥打基纳巴卢)',
            '茨城': '茨城(东京)',
        }

        # if not http_session.get_cookies().get('FedAuth'):
        #     http_session = self.init_cookies(http_session)

        if search_info.adt_count == 0 or search_info.adt_count is None:
            adt_count = 1
        else:
            adt_count = search_info.adt_count

        if cn_city_mapping.get(IATA_CODE[search_info.from_airport]['cn_city']):
            dep_cn_city = cn_city_mapping[IATA_CODE[search_info.from_airport]['cn_city']]
        else:
            dep_cn_city = IATA_CODE[search_info.from_airport]['cn_city']
        if cn_city_mapping.get(IATA_CODE[search_info.to_airport]['cn_city']):
            arr_cn_city = cn_city_mapping[IATA_CODE[search_info.to_airport]['cn_city']]
        else:
            arr_cn_city = IATA_CODE[search_info.to_airport]['cn_city']

        depart_place = dep_cn_city.decode('utf8')
        arrive_place = arr_cn_city.decode('utf8')
        # depart_place_short = search_info.from_airport
        # arrive_place_short = search_info.to_airport
        # flight_date = search_info.from_date
        # depart_place_encode = self.convert_unicode_char_to_byte(depart_place)
        # arrive_place_encode = self.convert_unicode_char_to_byte(arrive_place)
        # searchhis = u'zh-cn%26{}%26{}%26{}%26{}%26{}%26'.format(depart_place_short, depart_place_encode,
        #                                                         arrive_place_short, arrive_place_encode,
        #                                                         flight_date)
        # http_session.update_cookie(cookie_dict={'SearchHis': searchhis})

        # TODO 返程请求两次
        ifret = False
        return_date = ''
        first_segment_id = ''
        data = {
            'Active9s': '',
            'IsJC': False,
            'IsShowTaxprice': False,
            'Currency': 0,
            'SType': 0,
            'Departure': depart_place.encode('utf8'),
            'Arrival': arrive_place.encode('utf8'),
            'DepartureDate': search_info.from_date,
            'ReturnDate': None,
            'IsIJFlight': False,
            'IsBg': False,
            'IsEmployee': False,
            'IsLittleGroupFlight': False,
            'SeatsNum': adt_count,
            'ActId': 0,
            'IfRet': ifret,
            'IsUM': False,
            'CabinActId': None,
            'isdisplayold': False,
        }

        # if ifret:
        #     data.update({'first_segment_id': first_segment_id})

        headers = {
            # ':authority': 'flights.ch.com',
            # ':scheme': 'https',
            # ':path': '/Flights/SearchByTime',
            'accept': '*/*',
            'origin': 'https://flights.ch.com',
            'x-requested-with': 'XMLHttpRequest',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'referer': 'https://flights.ch.com/SHA-BKK.html?Departure=%E4%B8%8A%E6%B5%B7&Arrival=%E6%9B%BC%E8%B0%B7&FDate=2019-03-28&ANum=1&CNum=0&INum=0&IfRet=false&SType=012&MType=0&IsNew=1',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-GB,en;q=0.9,en-US;q=0.8,zh-CN;q=0.7,zh;q=0.6',
        }

        result = http_session.request(url='https://flights.ch.com/Flights/SearchByTime', data=data, method='POST',
                                      headers=headers, verify=False)

        try:
            search_result_data = json.loads(result.content)
            search_routes = search_result_data.get('Route')
        except:
            # Logger().error(result.content)
            raise FlightSearchException(err_code='HIGH_REQ_LIMIT')

        if not search_routes:
            Logger().debug('ch no flight')
            return search_info

        product_list = self.format_products(http_session, search_routes)
        search_info.product_list = product_list
        for product in product_list:
            flight_routing = FlightRoutingInfo()
            flight_routing.routing_key_detail, flight_routing.routing_key = self.generate_routing_key(product, search_info)

            adult_price = 0
            adult_tax = 0
            child_price = 0
            child_tax = 0
            inf_price = 0
            inf_tax = 0
            adult_discount = 0

            flight_routing.product_type = 'DEFAULT'
            routing_number = 1
            is_trn_transport = False
            for index, segment in enumerate(product['segment_info']):
                if segment['Transport'] == 1:
                    is_trn_transport = True
                    break
                flight_segment = FlightSegmentInfo()
                flight_segment.carrier = '9C'
                flight_segment.dep_airport = segment['DepartureAirportCode']
                flight_segment.dep_time = segment['DepartureTime']

                flight_segment.arr_airport = segment['ArrivalAirportCode']
                flight_segment.arr_time = segment['ArrivalTime']

                # 价格
                adult_price += float(product['cabin_info'][index]['AircraftCabinInfos'][0]['Price'])
                adult_discount += float(product['cabin_info'][index]['AircraftCabinInfos'][0]['Discount'])
                adult_tax += float(product['cabin_info'][index]['AircraftCabinInfos'][0]['AirportConstructionFees'])
                adult_tax += float(product['cabin_info'][index]['AircraftCabinInfos'][0]['FuelSurcharge'])
                if product['cabin_info'][index]['AircraftCabinInfos'][0].get('OtherFees'):
                    adult_tax += float(product['cabin_info'][index]['AircraftCabinInfos'][0]['OtherFees'])
                if product['cabin_info'][index]['AircraftCabinInfos'][0].get('AbroadFee'):
                    adult_tax += float(product['cabin_info'][index]['AircraftCabinInfos'][0]['AbroadFee']['Fee'])

                child_price += float(product['cabin_info'][index]['AircraftCabinInfos'][1]['Price'])
                child_tax += float(product['cabin_info'][index]['AircraftCabinInfos'][1]['AirportConstructionFees'])
                child_tax += float(product['cabin_info'][index]['AircraftCabinInfos'][1]['FuelSurcharge'])
                if product['cabin_info'][index]['AircraftCabinInfos'][1].get('OtherFees'):
                    child_tax += float(product['cabin_info'][index]['AircraftCabinInfos'][1]['OtherFees'])
                if product['cabin_info'][index]['AircraftCabinInfos'][1].get('AbroadFee'):
                    child_tax += float(product['cabin_info'][index]['AircraftCabinInfos'][1]['AbroadFee']['Fee'])

                inf_price += float(product['cabin_info'][index]['AircraftCabinInfos'][2]['Price'])
                inf_tax += float(product['cabin_info'][index]['AircraftCabinInfos'][2]['AirportConstructionFees'])
                inf_tax += float(product['cabin_info'][index]['AircraftCabinInfos'][2]['FuelSurcharge'])
                if product['cabin_info'][index]['AircraftCabinInfos'][2].get('OtherFees'):
                    inf_tax += float(product['cabin_info'][index]['AircraftCabinInfos'][2]['OtherFees'])
                if product['cabin_info'][index]['AircraftCabinInfos'][2].get('AbroadFee'):
                    inf_tax += float(product['cabin_info'][index]['AircraftCabinInfos'][2]['AbroadFee']['Fee'])

                # 经停
                stop_city_code_list = []
                stop_airport_code_list = []
                for sl in segment['Stopovers']:
                    stop_city_code_list.append(sl['DepartureCode'])
                    stop_airport_code_list.append(sl['DepartureAirportCode'])
                flight_segment.stop_cities = "/".join(stop_city_code_list)
                flight_segment.stop_airports = "/".join(stop_airport_code_list)

                flight_segment.flight_number = segment['No']
                flight_segment.dep_terminal = segment['DepartureStation']
                flight_segment.arr_terminal = segment['ArrivalStation']

                # TODO
                # ch_cabin_grade = product['cabin_info'][index]['CabinLevel']
                # ch_cabin_map = {
                #     5: 'Y',  # 官网专享
                #     3: 'Y',  # 经济座
                #     0: 'C',  # 商务经济座
                #     # 4: 'F', # 商务座
                #     4: 'C'
                # }
                flight_segment.cabin = product['cabin_info'][index]['AircraftCabinInfos'][0]['Name']
                # flight_segment.cabin_grade = ch_cabin_map[ch_cabin_grade]
                flight_segment.cabin_grade = 'Y'
                flight_segment.cabin_count = product['cabin_info'][index]['AircraftCabinInfos'][0]['Remain']
                segment_duration = (datetime.datetime.strptime(segment['ArrivalTime'], '%Y-%m-%d %H:%M:%S') -
                                    datetime.datetime.strptime(segment['DepartureTime'], '%Y-%m-%d %H:%M:%S')).seconds
                duration = int(segment_duration / 60)
                flight_segment.duration = duration
                flight_segment.routing_number = routing_number
                routing_number += 1
                flight_routing.from_segments.append(flight_segment)


            # 是否为共享航班


            flight_routing.adult_price = adult_price
            flight_routing.adult_price_discount = int(adult_discount)
            flight_routing.adult_tax = adult_tax
            flight_routing.child_price = child_price
            flight_routing.child_tax = child_tax

            if not is_trn_transport:
                search_info.assoc_search_routings.append(flight_routing)
        return search_info

    def _verify(self, http_session, search_info):

        search_info = self.flight_search(http_session, search_info, cache_mode='REALTIME')
        routing_info = None
        product_details = None
        for index, flight_routing in enumerate(search_info.assoc_search_routings):
            real_search_cp_key = RoutingKey.trans_cp_key(simple_decrypt(flight_routing.routing_key))
            order_cp_key = RoutingKey.trans_cp_key(simple_decrypt(search_info.verify_routing_key))
            if real_search_cp_key == order_cp_key:
                routing_info = flight_routing
                product_details = search_info.product_list[index]
                break
        if not routing_info or not product_details:
            raise ProviderVerifyFail('no routing info')

        segment_list = product_details['segment_info']
        post_segment_list = []
        for index, segment in enumerate(segment_list):
            dep_time = segment['DepartureTimeBJ']
            arr_time = segment['ArrivalTimeBJ']
            dep_time = datetime.datetime.strptime(dep_time, '%Y-%m-%d %H:%M:%S')
            arr_time = datetime.datetime.strptime(arr_time, '%Y-%m-%d %H:%M:%S')
            cross_days = (arr_time - dep_time).days
            dur_total_seconds = int((arr_time - dep_time).total_seconds())
            dur_days = int(dur_total_seconds / 86400.0)
            dur_hour = int(dur_total_seconds / 3600.0)
            dur_min = int(dur_total_seconds / 60.0 - dur_hour * 60)

            cabin_info = {
                u'AircraftCabins': {
                    u'ActivityCheck': None,
                    u'AircraftCabinInfos': product_details['cabin_info'][index]['AircraftCabinInfos'],
                    u'CabinActId': product_details['cabin_info'][index]['CabinActId'],
                    u'CabinLevel': product_details['cabin_info'][index]['CabinLevel'],
                    u'CabinLevelName': product_details['cabin_info'][index]['CabinLevelName'],
                    u'CabinPrice': product_details['cabin_info'][index]['CabinPrice'],
                    u'CombId': product_details['cabin_info'][index]['CombId'],
                    u'CombType': product_details['cabin_info'][index]['CombType'],
                    u'Guest': product_details['cabin_info'][index]['Guest'],
                    u'IsActivity': product_details['cabin_info'][index]['IsActivity'],
                    u'IsJC': product_details['cabin_info'][index]['IsJC'],
                    u'SortNo': product_details['cabin_info'][index]['SortNo'],
                    u'cabinName': product_details['cabin_info'][index]['CabinLevelName'],
                    u'currency': 0,
                    u'flightDate': segment['FlightDateBJ'],
                    u'flightNo': segment['No'],
                    u'flightSeg': segment['DepartureCode'] + segment['ArrivalCode'],
                    u'hasScomb': False,
                    u'refund': {
                        u'Code': 0,
                        u'Enabled': True,
                        u'Guest': u'无',
                        u'Highlight': False,
                        u'Id': u'8e39fd4b-15fe-43be-a181-242d6fc031f0',
                        u'Name': u'退改政策'
                    },
                    u'routeArea': segment['RouteArea'],
                    u'sType': segment['SegType'],
                    u'segmentId': segment['SegmentId'],
                    u'transport': segment['Transport']
                }
            }

            route_info = {
                u'companyId': 0,
                u'companyName': u'春秋航空',
                u'currency': 0,
                u'displayArrivalTime': segment['ArrivalTimeBJ'].split(' ')[-1].replace(':00', ''),
                u'displayDepartureTime': segment['DepartureTimeBJ'].split(' ')[-1].replace(':00', ''),
                u'duringTime': {
                    u'crossDay': {u'day': cross_days},
                    u'day': {u'day': dur_days, u'hour': dur_hour, u'minute': dur_min, u'second': 60},
                    u'hour': {u'hour': dur_hour, u'minute': dur_min, u'second': 60},
                    u'minute': {u'minute': dur_hour * 60 + dur_min, u'second': 0},
                    u'second': {u'second': dur_total_seconds}
                },
                u'priceDisplay': u'&yen; <em>830</em>'
            }

            route_info.update(segment)
            route_info.update(cabin_info)
            post_segment_list.append(route_info)

        post_data = {
            'param': json.dumps({
                "Currency": 0,
                "Route": post_segment_list,
            })
        }

        result = http_session.request(url='https://flights.ch.com/Default/PrepareData', data=post_data, method='POST',
                                      verify=False).to_json()
        if not int(result['Code']) == 0:
            Logger().error(result)
            raise ProviderVerifyFail('price invalid')

        return routing_info


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

        # 注册逻辑 遍历里面的乘机人，直至注册成功
        order_info.provider_order_status = 'REGISTER_FAIL'

        # 测试固定账号，跳过注册
        # ffp_account_info = FFPAccountInfo()0............

        # ffp_account_info.username = 'gli5186@tongdun.org'
        # ffp_account_info.password = 'bigsec@2018'
        # ffp_account_info.provider = self.provider
        # # ffp_account_info.reg_passport = random_passport
        # ffp_account_info.reg_birthdate = '1970-04-09'
        # ffp_account_info.reg_gender = 'M'
        # order_info.ffp_account = ffp_account_info

        if not order_info.ffp_account:
            # 如果没有账号才需要注册
            try:
                ffp_account_info = self.register(http_session=http_session, pax_info=order_info.passengers[0],
                                                 sub_order_id=order_info.sub_order_id,flight_order_id=order_info.flight_order_id)
            except Critical as e:
                raise
            order_info.ffp_account = ffp_account_info  # 需要将账号信息反馈到order_info
            # gevent.sleep(1)

        order_info.provider_order_status = 'LOGIN_FAIL'
        http_session = self.login(http_session, order_info.ffp_account)

        # gevent.sleep(1)
        order_info.provider_order_status = 'SEARCH_FAIL'
        search_info = self.flight_search(http_session, order_info, cache_mode='REALTIME')

        order_info.provider_order_status = 'BOOK_FAIL'
        # 确认航班
        # gevent.sleep(1)
        Logger().info('confirm flight ')

        routing_info = None
        product_details = None
        for index, flight_routing in enumerate(order_info.assoc_search_routings):
            real_search_cp_key = RoutingKey.trans_cp_key(simple_decrypt(flight_routing.routing_key))
            order_cp_key = RoutingKey.trans_cp_key(simple_decrypt(order_info.routing.routing_key))
            # order_cp_key = RoutingKey.trans_cp_key(simple_decrypt(order_info.verify_routing_key))
            if real_search_cp_key == order_cp_key:
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

        agetype_map = {
            'ADT': 0,
            'CHD': 1,
            'INF': 2,
        }

        price = 0

        contact = order_info.contacts[0]

        segment_list = product_details['segment_info']
        post_segment_list = []
        close_sub_prod_segment_data = []
        for index, segment in enumerate(segment_list):
            dep_time = segment['DepartureTimeBJ']
            arr_time = segment['ArrivalTimeBJ']
            dep_time = datetime.datetime.strptime(dep_time, '%Y-%m-%d %H:%M:%S')
            arr_time = datetime.datetime.strptime(arr_time, '%Y-%m-%d %H:%M:%S')
            cross_days = (arr_time - dep_time).days
            dur_total_seconds = int((arr_time - dep_time).total_seconds())
            dur_days = int(dur_total_seconds / 86400.0)
            dur_hour = int(dur_total_seconds / 3600.0)
            dur_min = int(dur_total_seconds / 60.0 - dur_hour * 60)

            price += adult_num * int(product_details['cabin_info'][index]['AircraftCabinInfos'][0]['Price'])
            price += adult_num * int(product_details['cabin_info'][index]['AircraftCabinInfos'][0]['AirportConstructionFees'])
            price += adult_num * int(product_details['cabin_info'][index]['AircraftCabinInfos'][0]['FuelSurcharge'])
            price += adult_num * int(product_details['cabin_info'][index]['AircraftCabinInfos'][0]['OtherFees'])
            if product_details['cabin_info'][index]['AircraftCabinInfos'][0].get('AbroadFee'):
                price += adult_num * int(product_details['cabin_info'][index]['AircraftCabinInfos'][0]['AbroadFee']['Fee'])
            price += children_num * int(product_details['cabin_info'][index]['AircraftCabinInfos'][1]['Price'])
            price += children_num * int(product_details['cabin_info'][index]['AircraftCabinInfos'][1]['AirportConstructionFees'])
            price += children_num * int(product_details['cabin_info'][index]['AircraftCabinInfos'][1]['FuelSurcharge'])
            price += children_num * int(product_details['cabin_info'][index]['AircraftCabinInfos'][1]['OtherFees'])
            if product_details['cabin_info'][index]['AircraftCabinInfos'][1].get('AbroadFee'):
                price += children_num * int(product_details['cabin_info'][index]['AircraftCabinInfos'][1]['AbroadFee']['Fee'])
            price += inf_num * int(product_details['cabin_info'][index]['AircraftCabinInfos'][2]['Price'])
            price += inf_num * int(
                product_details['cabin_info'][index]['AircraftCabinInfos'][2]['AirportConstructionFees'])
            price += inf_num * int(product_details['cabin_info'][index]['AircraftCabinInfos'][2]['FuelSurcharge'])
            price += inf_num * int(product_details['cabin_info'][index]['AircraftCabinInfos'][2]['OtherFees'])
            if product_details['cabin_info'][index]['AircraftCabinInfos'][2].get('AbroadFee'):
                price += inf_num * int(product_details['cabin_info'][index]['AircraftCabinInfos'][2]['AbroadFee']['Fee'])

            cabin_info = {
                u'AircraftCabins': {
                    u'ActivityCheck': None,
                    u'AircraftCabinInfos': product_details['cabin_info'][index]['AircraftCabinInfos'],
                    u'CabinActId': product_details['cabin_info'][index]['CabinActId'],
                    u'CabinLevel': product_details['cabin_info'][index]['CabinLevel'],
                    u'CabinLevelName': product_details['cabin_info'][index]['CabinLevelName'],
                    u'CabinPrice': product_details['cabin_info'][index]['CabinPrice'],
                    u'CombId': product_details['cabin_info'][index]['CombId'],
                    u'CombType': product_details['cabin_info'][index]['CombType'],
                    u'Guest': product_details['cabin_info'][index]['Guest'],
                    u'IsActivity': product_details['cabin_info'][index]['IsActivity'],
                    u'IsJC': product_details['cabin_info'][index]['IsJC'],
                    u'SortNo': product_details['cabin_info'][index]['SortNo'],
                    u'cabinName': product_details['cabin_info'][index]['CabinLevelName'],
                    u'currency': 0,
                    u'flightDate': segment['FlightDateBJ'],
                    u'flightNo': segment['No'],
                    u'flightSeg': segment['DepartureCode'] + segment['ArrivalCode'],
                    u'hasScomb': False,
                    u'refund': {
                        u'Code': 0,
                        u'Enabled': True,
                        u'Guest': u'无',
                        u'Highlight': False,
                        u'Id': u'8e39fd4b-15fe-43be-a181-242d6fc031f0',
                        u'Name': u'退改政策'
                    },
                    u'routeArea': segment['RouteArea'],
                    u'sType': segment['SegType'],
                    u'segmentId': segment['SegmentId'],
                    u'transport': segment['Transport']
                }
            }

            route_info = {
                u'companyId': 0,
                u'companyName': u'春秋航空',
                u'currency': 0,
                u'displayArrivalTime': segment['ArrivalTimeBJ'].split(' ')[-1].replace(':00', ''),
                u'displayDepartureTime': segment['DepartureTimeBJ'].split(' ')[-1].replace(':00', ''),
                u'duringTime': {
                    u'crossDay': {u'day': cross_days},
                    u'day': {u'day': dur_days, u'hour': dur_hour, u'minute': dur_min, u'second': 60},
                    u'hour': {u'hour': dur_hour, u'minute': dur_min, u'second': 60},
                    u'minute': {u'minute': dur_hour * 60 + dur_min, u'second': 0},
                    u'second': {u'second': dur_total_seconds}
                },
                u'priceDisplay': u'&yen; <em>830</em>'
            }

            route_info.update(segment)
            route_info.update(cabin_info)
            post_segment_list.append(route_info)

            close_sub_prod_segment_data.append({
                'SegmentId': segment['SegmentId'],
                'CabinName': product_details['cabin_info'][index]['AircraftCabinInfos'][0]['Name'],
                'CabinPrice': segment['Price'],
                'CabinLevel': product_details['cabin_info'][index]['CabinLevel'],
                'RouteType': segment['RouteType'],
            })

        certificate_type_map = {
            'PP': 2,
            'GA': 13,
            'TW': 17,
            'TB': 3,
            'HX': 10,
            'HY': 18,
            'NI': 1,
            'HK': 5
        }
        certificate_name_map = {
            'PP': '护照',
            'GA': '港澳通行证',
            'TW': '大陆居民往来台湾通行证',
            'TB': '台湾居民来往大陆通行证（台胞证）',
            'HX': '港澳居民来往内地通行证（回乡证）',
            'HY': '海员证',
            'NI': '身份证',
            'HK': '户口薄',
        }

        passenger_info = [{
                              u'Birthday': passenger.birthdate,
                              u'CertificateCountryOfIssue': None if passenger.used_card_type == 'NI' else u'CHN',
                              u'CertificateExpireDate': None if passenger.used_card_type == 'NI' else passenger.card_expired,
                              u'CertificateNo': passenger.selected_card_no if passenger.selected_card_no else '',
                              u'CertificateType': certificate_type_map[passenger.used_card_type],
                              u"CertificateTypeValue": certificate_name_map[passenger.used_card_type],
                              u'FamilyName': passenger.name if passenger.used_card_type == 'NI' else passenger.last_name,
                              u'FrequentFlyer': False,
                              u'Gender': None if passenger.used_card_type == 'NI' else 1,
                              u'Index': index,
                              u'IsLinkMan': False,
                              u'IsSetContact': False,
                              u'IsSetFrequentFlyer': False,
                              u'Mobile': TBG.global_config['OPERATION_CONTACT_MOBILE'],
                              u'Nationality': None if passenger.used_card_type == 'NI' else u'CHN',
                              u'PersonalName': u'' if passenger.used_card_type == 'NI' else passenger.first_name,
                              u'Type': agetype_map[passenger.current_age_type(order_info.from_date)],
                          } for index, passenger in enumerate(order_info.passengers)]

        '''
                    child passenger
                    {
                         "Index":1,
                         "IsLinkMan":false,
                         "FrequentFlyer":false,
                         "Nationality":null,
                         "Gender":null,
                         "FamilyName":"王小",
                         "PersonalName":"",
                         "Birthday":"2013-03-11",
                         "Mobile":"17521504321",
                         "CertificateType":"5",
                         "CertificateTypeValue":"户口薄",
                         "CertificateNo":"",
                         "CertificateExpireDate":null,
                         "CertificateCountryOfIssue":null,
                         "IsSetFrequentFlyer":true,
                         "IsSetContact":false,
                         "Type":1
                      }
                '''

        post_data = {
            u'ACode': product_details['segment_info'][-1]['ArrivalCode'],
            u'ANum': adult_num,
            u'ActId': None,
            u'Arrival': product_details['segment_info'][-1]['Arrival'],
            u'CNum': children_num,
            u'Contacts': [{
                u'LinkManEmail': order_info.ffp_account.username,
                u'LinkManMobile': TBG.global_config['OPERATION_CONTACT_MOBILE'],
                u'LinkManName': order_info.passengers[0].last_name + order_info.passengers[0].first_name,
                u"LinkCountryCode": u"86",
                u"LinkCountryCodeName": u"中国大陆 86",
            }],
            u'Currency': 0,
            u'DCode': product_details['segment_info'][0]['DepartureCode'],
            u'Departure': product_details['segment_info'][0]['Departure'],
            u'DepartureDate': product_details['segment_info'][0]['FlightDateBJ'],
            u'INum': inf_num,
            u'IfRet': False,
            u"InsuranceDiscountBizInputParam": {
                u"AccidentInsurancePrice": 30,
                u"SinglePersonDiscountAmount": 10,
                u"IsEnableInsDiscountModule": True,
                u"IsInsuranceDiscountGo": False,
                u"IsInsuranceDiscountReturn": False
            },
            u'IsBg': False,
            u'IsContain9C': True,
            u'IsEmployee': False,
            u'IsIJFlight': False,
            u'IsLittleGroupFlight': False,
            u'IsOnlyValidate': False,
            u'Passengers': passenger_info,
            u'Price': price,
            u'ReturnDate': u'',
            u'Route': post_segment_list,
            u'SType': 0
        }

        post_data = {
            'param': json.dumps(post_data, ensure_ascii=False)
        }

        # gevent.sleep(1)

        # TODO 后续整理cookie
        s6 = 'c0facd20e97e468d9dc65c63a5d{}'.format(random.randint(10000, 99999))
        gr_user_id = '56cd0a56-2567-4cd8-bb56-cb36b68{}'.format(random.randint(10000, 99999))
        _ga = 'GA1.2.79118168.1532956452'
        PcPopAd_LoginMark = '2018-08-02 15:12:53'
        _gid = 'GA1.2.1358741534.{}'.format(int(time.time()))
        loginTime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        gr_session_id_key = '9683d26dac5{}'.format(random.randint(10000, 99999))
        gr_session_id_value = '38111f90-3f6f-42ed-a6d4-5fae56f{}'.format(random.randint(10000, 99999))
        s4 = '6e823de713264794bff71b8649d{}'.format(random.randint(10000, 99999))
        search_his = http_session.get_cookies().get('SearchHis')
        __ppa__ = http_session.get_cookies().get('__ppa__')
        fedauth = http_session.get_cookies().get('FedAuth')

        UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36'

        cookies = 'PcPopAd_VisitWebSite=2018-07-30 21:14:06; PcPopAd_XRL1531807581658=; s6={}; gr_user_id={}; _ga={}; IsShowTaxprice=false; c1=edmin_zn_sys_active_active; PcPopAd_LoginMark={}; hasProcessIP=1; __pointstatus__=MA==; acw_tc=AQAAAGxHQ1ONnAAAoERAcNiRWcGw6cR2; ASP.NET_SessionId=Online.420g2hblox5lsvioobksb51z; DomainType=ChunHang; preloadJs=.js%3Fvs%3Dv2018081005; grwng_uid={}; _st=b68f46123afa056421781cf4815fed16; c_source=; c2=secondkill_flight_HKTSWA; _gid={}; PcPopAd_CSC{}096=; hideQRCount=0; qrCount=0; SearchHis={}; s1=Mac; s2=WEB; s3=zh-cn; s4={}; {}_gr_session_id={}; {}_gr_session_id_{}=true; u1=SjhVSHZWR2FBMzZNL0lva0hvQmNwZz09; count=1; loginTime={}; __ppa__={}; FedAuth={}; g_refresh=0; s5=8; _gat=1'.format(
            s6, gr_user_id, _ga, PcPopAd_LoginMark, gr_user_id, _gid, int(time.time()) - 1, search_his, s4,
            gr_session_id_key, gr_session_id_value, gr_session_id_key, gr_session_id_value, loginTime, __ppa__, fedauth
        )

        headers = {
            'Cookie': cookies,
            'User-Agent': UA,
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        }

        result = http_session.request(url='https://flights.ch.com/Flights/BookingSave', data=post_data, method='POST',
                                      headers=headers, verify=False)

        book_key = json.loads(result.content)
        key = book_key['Url'].split('?key=')[-1]

        # ========== save close sub prod ====================

        post_data = {
            "Language": 0,
            "Currency": 0,
            "Company": 0,
            "Segments": close_sub_prod_segment_data
        }

        # gevent.sleep(0.8)
        result = http_session.request(url='https://flights.ch.com/Order/SaleClosedSubProdList', method='POST',
                                      headers=headers, data=post_data, verify=False)

        # ======================= save increase data ===========
        post_data = {
            # u'IsActivity': 1,
            u'IsActivity': 0,
            u'IsIJFlight': False,
            u'Key': key,
            u'OrderNo': None,
            u'PassengerWithPros': [{
                                       u'Age': 0,
                                       u'AgentType': agetype_map[passenger.current_age_type(order_info.from_date)],
                                       u'AircraftCabins': None,
                                       # u'AllIncreases': [{
                                       #     u'Id': u'976183',
                                       #     u'Products': [{
                                       #         u'Address': None,
                                       #         u'BeginTime': u'',
                                       #         u'BuyType': 0,
                                       #         u'CanBuyNumber': 1,
                                       #         u'Category': 1,
                                       #         u'ClientMessages': None,
                                       #         u'CompanyId': None,
                                       #         u'DepartureTime': None,
                                       #         u'Duration': 0,
                                       #         u'EndTime': u'',
                                       #         u'FourGAddress': None,
                                       #         u'FourGCity': None,
                                       #         u'FourGMobile': None,
                                       #         u'FourGProvince': None,
                                       #         u'FourGReceiver': None,
                                       #         u'Id': 32,
                                       #         u'Info': None,
                                       #         u'InsuranceType': u'',
                                       #         u'IsComb': False,
                                       #         u'Lat': None,
                                       #         u'Lng': None,
                                       #         u'MinBuyNumber': 0,
                                       #         u'Must': False,
                                       #         u'Name': u'网上值机服务',
                                       #         u'PassengersNumber': 0,
                                       #         u'PaymentStatus': 0,
                                       #         u'Price': 0,
                                       #         u'PriceOfAirportCounter': -1,
                                       #         u'ProdDetailID': None,
                                       #         u'ProductNum': 0,
                                       #         u'ProductOrderDetailId': None,
                                       #         u'ProductUnique': None,
                                       #         u'RemarkStr1': None,
                                       #         u'RemarkStr2': None,
                                       #         u'SeatId': None,
                                       #         u'SeatNo': None,
                                       #         u'SecondType': 0,
                                       #         u'Segment': None,
                                       #         u'Type': 10
                                       #     }]
                                       # }],

                                       u'AllIncreases': [{u'Id': u'1159257', u'Products': []}],
                                       u'Baggage': 0,
                                       # u'Baggages': {u'976183': 0},
                                       u'Baggages': {u'1159257': 0},
                                       u'Birthday': passenger.birthdate,
                                       u'CanBuyProducts': [],
                                       u'CanUpdate': True,
                                       u'CertificateCountryOfIssue': None if passenger.used_card_type == 'NI' else u'CHN',
                                       u'CertificateExpireDate': u'/Date(-62135596800000)/' if passenger.used_card_type == 'NI' else u'/Date({})/'.format(
                                           int(time.mktime(time.strptime(passenger.card_expired, '%Y-%m-%d')) * 1000)),
                                       u'CertificateExpireDateFormart': u'/Date(-62135596800000)/',
                                       u'CertificateNo': passenger.selected_card_no,
                                       u'CertificateType': certificate_type_map[passenger.used_card_type],
                                       u'CertificateTypeValue': certificate_name_map[passenger.used_card_type],
                                       u'CheckInId': None,
                                       u'DetailId': None,
                                       u'DetailIds': {u'976183': None},
                                       u'Email': None,
                                       u'FamilyName': passenger.name if passenger.used_card_type == 'NI' else passenger.last_name,
                                       u'FrequentFlyer': False,
                                       u'Gender': None if passenger.used_card_type == 'NI' else 1,
                                       u'HadBuyIncreaseProducts': [],
                                       u'Index': index,
                                       u'IsLinkMan': False,
                                       u'IsOldMan': False,
                                       u'Mobile': TBG.global_config['OPERATION_CONTACT_MOBILE'],
                                       u'Nationality': None if passenger.used_card_type == 'NI' else u'CHN',
                                       u'OutOrderNo': None,
                                       u'PersonId': u'{}{}{}{}'.format(passenger.selected_card_no,
                                                                       passenger.name if passenger.used_card_type == 'NI' else passenger.last_name,
                                                                       index, passenger.birthdate),
                                       u'PersonalName': u'' if passenger.used_card_type == 'NI' else passenger.first_name,
                                       u'UserFlag': None,
                                       u'UserId': None} for index, passenger in enumerate(order_info.passengers)],
            u'Route': [{
                           u'Arrival': seg['Arrival'],
                           u'ArrivalAirportCode': seg['ArrivalAirportCode'],
                           u'ArrivalCode': seg['ArrivalCode'],
                           u'ArrivalStation': seg['ArrivalStation'],
                           u'ArrivalTime': seg['ArrivalTime'],
                           u'Departure': seg['Departure'],
                           u'DepartureAirportCode': seg['DepartureAirportCode'],
                           u'DepartureCode': seg['DepartureCode'],
                           u'DepartureStation': seg['DepartureStation'],
                           u'DepartureTime': seg['DepartureTime'],
                           u'RouteArea': seg['RouteArea'],
                           u'RouteId': seg['RouteId'],
                           u'RouteType': seg['RouteType'],
                           u'SegmentId': seg['SegmentId'],
                           u'Transport': seg['Transport'],
                       } for seg in segment_list]
        }

        # gevent.sleep(0.8)
        post_data = {'increasedata': json.dumps(post_data, ensure_ascii=False)}
        result = http_session.request(url='https://flights.ch.com/Increase/SaveIncreaseOrderData', method="POST",
                                      headers=headers, data=post_data, verify=False)

        # gevent.sleep(1)
        post_data = {
            'key': key,
            'cancelRecommandInsuranceFlightNo=': '',
            'buyInsuranceFlightNo=': '',
        }
        result = http_session.request(url='https://flights.ch.com/order/CreateOrder/', data=post_data, method="POST",
                                      headers=headers, verify=False)

        order_body = json.loads(result.content)
        success = order_body.get('IfSuccess')
        order_id = order_body.get('OrderNo')

        if not success == 'Y' or not order_id:
            raise BookingException('can not get order id')

            # #FIXME 订不到会员价舱位逻辑，直接检查订单列表最新订单，获取订单号以及价格
            # gevent.sleep(2)
            # result = http_session.request(url='https://account.ch.com/order/flights',
            #                               method='GET', verify=False)
            # order_html = etree.HTML(result.content)
            # order_info_tr = order_html.xpath('//tr[@class="active J-order return"]')[0]
            # extract_order_id = order_info_tr.xpath('td[@class="operation last"]/ul/li[1]/a/@data-id')
            # if not extract_order_id:
            #     raise BookingException('order verify failed!')
            # order_id = extract_order_id[0]
            # order_price = order_info_tr.xpath('td[@class="price"]/em/text()')
            # if not order_price:
            #     raise BookingException('order verify failed!')
            # re_order_price = re.compile(r'[0-9]+').findall(order_price[0])
            # if re_order_price:
            #     order_price = int(''.join(re_order_price))
            #     if order_price == price:
            #         order_info.provider_order_status = 'BOOK_SUCCESS_AND_WAITING_PAY'
            #         order_info.provider_order_id = order_id
            #         order_info.provider_price = order_price
            #         Logger().info('booking success')
            #         Logger().info('orderNo %s' % order_id)
            #         return order_info
            # raise BookingException('order verify failed!')

        # gevent.sleep(2)
        result = http_session.request(url='https://account.ch.com/order/flights',
                                      method='GET', verify=False)
        order_html = etree.HTML(result.content)
        order_info_tr_list = order_html.xpath('//tr[@class="active J-order return"]')
        order_tr_info = None
        for tr in order_info_tr_list:
            extract_order_id = tr.xpath('td[@class="operation last"]/ul/li[1]/a/@data-id')
            if extract_order_id and extract_order_id[0] == order_id:
                order_tr_info = tr
                break
        if order_tr_info is None:
            raise BookingException('order verify failed!')
        order_price = order_tr_info.xpath('td[@class="price"]/em/text()')
        if not order_price:
            raise BookingException('order verify failed!')
        re_order_price = re.compile(r'[0-9]+').findall(order_price[0])
        if re_order_price:
            order_price = int(''.join(re_order_price))

            if not order_price == price:
                Logger().error(
                    'order price not match. booking price: {}  order page price: {}'.format(price, order_price))

            order_info.provider_order_status = 'BOOK_SUCCESS_AND_WAITING_PAY'
            order_info.provider_order_id = order_id
            order_info.provider_price = order_price
            Logger().info('booking success')
            Logger().info('orderNo %s' % order_id)
            return order_info
        else:
            Logger().error('cannot get order price after booking ')
        raise BookingException('order verify failed!')

    def _check_order_status(self, http_session, ffp_account_info, order_info):
        """
        检查订单状态
        :param http_session:
        :param order_id:
        :return: 返回订单状态
        """

        if order_info.provider_order_status == 'PAY_SUCCESS':

            try:
                order_info.provider_order_status = 'LOGIN_FAIL'
                http_session = self.login(ffp_account_info=ffp_account_info)

                order_info.provider_order_status = 'ISSUE_FAIL'
                result = http_session.request(url='https://account.ch.com/order/flights',
                                              method='GET', verify=False)
                html = etree.HTML(result.content)
                order_element = html.xpath('//tr[@class="active J-order return"]')

                order_info_element = None
                payment_finish = False
                for e in order_element:
                    order_id_li = e.xpath('td[@class="operation last"]/ul/li/a/@href')
                    have_order_id_li = [l for l in order_id_li if order_info.provider_order_id in l]
                    print_order_li = [l for l in order_id_li if 'https://account.ch.com/order/XingCheng' in l]
                    if have_order_id_li:
                        order_info_element = e
                        if print_order_li:
                            payment_finish = True
                        break
                if order_info_element is None or not payment_finish:
                    order_info.provider_order_status = 'ISSUE_FAIL'
                    raise CheckOrderStatusException('cannot get order details. payment failed')

                # flight_no = order_info_element.xpath('td[@class="no"]/p/text()')
                pnr_code = order_info_element.xpath('td[@class="order"]/text()')
                if not pnr_code:
                    order_info.provider_order_status = 'ISSUE_FAIL'
                    raise CheckOrderStatusException('cannot get pnr code. payment failed')
                pnr_code = pnr_code[0]

                for pax_info in order_info.passengers:
                    pax_info.ticket_no = pnr_code
                order_info.pnr_code = pnr_code
                order_info.provider_order_status = 'ISSUE_SUCCESS'

            except Exception as e:
                raise CheckOrderStatusException(e)


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

        post_data = {
            'orderNo': order_info.provider_order_id,
            'IsLyOrder': 'false',
        }
        cookies = 'PcPopAd_VisitWebSite=2018-07-30 21:14:06; PcPopAd_XRL1531807581658=; s6=c0facd20e97e468d9dc65c63a5d470c1; gr_user_id=56cd0a56-2567-4cd8-bb56-cb36b6882d45; _ga=GA1.2.79118168.1532956452; IsShowTaxprice=false; c1=edmin_zn_sys_active_active; PcPopAd_LoginMark=2018-08-02 15:12:53; hasProcessIP=1; __pointstatus__=MA==; acw_tc=AQAAAGxHQ1ONnAAAoERAcNiRWcGw6cR2; ASP.NET_SessionId=Online.420g2hblox5lsvioobksb51z; DomainType=ChunHang; preloadJs=.js%3Fvs%3Dv2018081005; grwng_uid=824490ad-893a-4d89-a971-f10b7ed3920a; _st=b68f46123afa056421781cf4815fed16; c_source=; c2=secondkill_flight_HKTSWA; _gid=GA1.2.1512475848.1534328894; PcPopAd_CSC1534387392096=; hideQRCount=0; qrCount=0; count=1; loginTime=2018-08-16 15:22:56; __ppa__={}; g_refresh=0; 9683d26dac59f3e8_gr_session_id=123c1efc-6547-429d-bdf4-ee042425782a; s4=19e2236217d841f9b1eb312eab1e8282; s1=Mac; s2=WEB; s3=zh-cn; 9683d26dac59f3e8_gr_session_id_123c1efc-6547-429d-bdf4-ee042425782a=true; SearchHis={}; u1=SjhVSHZWR2FBMzZNL0lva0hvQmNwZz09; FedAuth={}; _gat=1; s5=8'.format(
            http_session.get_cookies().get('__ppa__'), http_session.get_cookies().get('SearchHis'),
            http_session.get_cookies().get('FedAuth')
        )
        UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36'
        headers = {
            'Cookie': cookies,
            'User-Agent': UA,
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        }
        result = http_session.request(url='https://flights.ch.com/Order/GetPayGetTradeIdNew/',
                                      data=post_data, headers=headers, method='POST',
                                      verify=False)

        if not result.response_status_code == 200:
            raise PayException('get trade id failed!')
        pay_info = json.loads(result.content)
        success = pay_info.get('IfSuccess')
        trade_id = pay_info.get('TradeId')

        if not success == 'Y' or not trade_id:
            raise PayException('get trade id failed!')

        provider_trade_id = trade_id

        gevent.sleep(1)
        url = 'https://bpayment.ch.com/flights/choose-channel/{}'.format(provider_trade_id)
        result = http_session.request(url=url, method='GET', verify=False)

        if not result.response_status_code == 200:
            raise PayException('no choose channel page by trade id')

        html = etree.HTML(result.content)
        query_str_dict = {
            'BankTypeID': html.xpath('//input[@id="BankTypeID"]/@value')[0] if html.xpath(
                '//input[@id="BankTypeID"]/@value') else '',
            'BankCode': html.xpath('//input[@id="BankCode"]/@value')[0] if html.xpath(
                '//input[@id="BankCode"]/@value') else '',
            'TradeId': html.xpath('//input[@id="Key"]/@value')[0] if html.xpath('//input[@id="Key"]/@value') else '',
            'Language': html.xpath('//input[@id="Language"]/@value')[0] if html.xpath(
                '//input[@id="Language"]/@value') else '',
            'Company': html.xpath('//input[@id="Company"]/@value')[0] if html.xpath(
                '//input[@id="Company"]/@value') else '',
            'OrderAmount': html.xpath('//input[@id="OrderAmount"]/@value')[0] if html.xpath(
                '//input[@id="OrderAmount"]/@value') else '',
            'UserID': html.xpath('//input[@id="UserID"]/@value')[0] if html.xpath(
                '//input[@id="UserID"]/@value') else '',
            'EncryptUserId': html.xpath('//input[@id="EncryptUserId"]/@value')[0] if html.xpath(
                '//input[@id="EncryptUserId"]/@value') else '',
            'CustID': html.xpath('//input[@id="CustID"]/@value')[0] if html.xpath(
                '//input[@id="CustID"]/@value') else '',
            'OrderNo': html.xpath('//input[@id="OrderNo"]/@value')[0] if html.xpath(
                '//input[@id="OrderNo"]/@value') else '',
            'OtherNo': html.xpath('//input[@id="OtherNo"]/@value')[0] if html.xpath(
                '//input[@id="OtherNo"]/@value') else '',
            'Currency': html.xpath('//input[@id="Currency"]/@value')[0] if html.xpath(
                '//input[@id="Currency"]/@value') else '',
            'OrderType': html.xpath('//input[@id="OrderType"]/@value')[0] if html.xpath(
                '//input[@id="OrderType"]/@value') else '',
            'Memo': html.xpath('//input[@id="Memo"]/@value')[0] if html.xpath('//input[@id="Memo"]/@value') else '',
            'LinkName': html.xpath('//input[@id="LinkName"]/@value')[0] if html.xpath(
                '//input[@id="LinkName"]/@value') else '',
            'IsFirstDG': html.xpath('//input[@id="IsFirstDG"]/@value')[0] if html.xpath(
                '//input[@id="IsFirstDG"]/@value') else '',
            'MultiFlag': html.xpath('//input[@id="MultiFlag"]/@value')[0] if html.xpath(
                '//input[@id="MultiFlag"]/@value') else '',
            'IsLedgerPay': html.xpath('//input[@id="IsLedgerPay"]/@value')[0] if html.xpath(
                '//input[@id="IsLedgerPay"]/@value') else '',
            'ExpreTime': html.xpath('//input[@id="ExpreTime"]/@value')[0] if html.xpath(
                '//input[@id="ExpreTime"]/@value') else '',
            'YHJInfo': html.xpath('//input[@id="YHJInfo"]/@value')[0] if html.xpath(
                '//input[@id="YHJInfo"]/@value') else '',
            'IntegralChecked': html.xpath('//input[@id="IntegralChecked"]/@value')[0] if html.xpath(
                '//input[@id="IntegralChecked"]/@value') else '',
            'IntegralInfo': html.xpath('//input[@id="IntegralInfo"]/@value')[0] if html.xpath(
                '//input[@id="IntegralInfo"]/@value') else '',
            'IsContinuePay': html.xpath('//input[@id="IsContinuePay"]/@value')[0] if html.xpath(
                '//input[@id="IsContinuePay"]/@value') else '',
            'TerminalId': html.xpath('//input[@id="TerminalId"]/@value')[0] if html.xpath(
                '//input[@id="TerminalId"]/@value') else '',
            'Periods': html.xpath('//input[@id="Periods"]/@value')[0] if html.xpath(
                '//input[@id="Periods"]/@value') else '',
            'Payer': html.xpath('//input[@id="Payer"]/@value')[0] if html.xpath('//input[@id="Payer"]/@value') else '',
            'BtB': html.xpath('//input[@id="BtB"]/@value')[0] if html.xpath('//input[@id="BtB"]/@value') else '',
            'PayLimitTime': html.xpath('//input[@id="PayLimitTime"]/@value')[0] if html.xpath(
                '//input[@id="PayLimitTime"]/@value') else '',
            'GAT': html.xpath('//input[@id="GAT"]/@value')[0] if html.xpath('//input[@id="GAT"]/@value') else '',
            'isCounpon': html.xpath('//input[@id="isCounpon"]/@value')[0] if html.xpath(
                '//input[@id="isCounpon"]/@value') else '',
            'isOpenNewIntegral': html.xpath('//input[@id="isOpenNewIntegral"]/@value')[0] if html.xpath(
                '//input[@id="isOpenNewIntegral"]/@value') else '',
            'isLyOrder': html.xpath('//input[@id="isLyOrder"]/@value')[0] if html.xpath(
                '//input[@id="isLyOrder"]/@value') else '',
            'encryptOrderNo': html.xpath('//input[@id="encryptOrderNo"]/@value')[0] if html.xpath(
                '//input[@id="encryptOrderNo"]/@value') else '',
            'isIj': html.xpath('//input[@id="isIj"]/@value')[0] if html.xpath('//input[@id="isIj"]/@value') else '',
            'ActivityCode': html.xpath('//input[@id="ActivityCode"]/@value')[0] if html.xpath(
                '//input[@id="ActivityCode"]/@value') else '',
            'IsNeed3DVerification': html.xpath('//input[@id="IsNeed3DVerification"]/@value')[0] if html.xpath(
                '//input[@id="IsNeed3DVerification"]/@value') else '',
            'IsHideHeadAndFoot': html.xpath('//input[@name="IsHideHeadAndFoot"]/@value')[0] if html.xpath(
                '//input[@name="IsHideHeadAndFoot"]/@value') else '',
        }
        if self.pay_channel == 'ALIPAY':
            query_str_dict['PayChannel'] = 1

            query_str_list = []
            for k, v in query_str_dict.items():
                query_str_list.append('{}={}'.format(k, v))
            query_str = '&'.join(query_str_list)

            gevent.sleep(1)
            result = http_session.request(url='https://bpayment.ch.com/ToPay/Default?{}'.format(query_str), method='GET',
                                          verify=False)

            if not result.response_status_code == 200:
                raise PayException('get alipay form tmpl error')

            if self.alipay(provider_trade_id, result.content):
                return pay_dict['alipay_yiyou180']
            else:
                raise PayException('alipay error')

        elif self.pay_channel == 'YEEPAY':
            query_str_dict['PayChannel'] = 11

            query_str_list = []
            for k, v in query_str_dict.items():
                query_str_list.append('{}={}'.format(k, v))
            query_str = '&'.join(query_str_list)

            gevent.sleep(1)
            result = http_session.request(url='https://bpayment.ch.com/ToPay/Default?{}'.format(query_str),
                                          method='GET',
                                          verify=False)

            if not result.response_status_code == 200:
                raise PayException('get yeepay form tmpl error')

            html = etree.HTML(result.content)

            post_data = {
                'p0_Cmd': html.xpath('//input[@name="p0_Cmd"]/@value')[0] if html.xpath(
                '//input[@name="p0_Cmd"]/@value') else '',
                'p1_MerId': html.xpath('//input[@name="p1_MerId"]/@value')[0] if html.xpath(
                '//input[@name="p1_MerId"]/@value') else '',
                'p2_Order': html.xpath('//input[@name="p2_Order"]/@value')[0] if html.xpath(
                '//input[@name="p2_Order"]/@value') else '',
                'p3_Amt': html.xpath('//input[@name="p3_Amt"]/@value')[0] if html.xpath(
                '//input[@name="p3_Amt"]/@value') else '',
                'p4_Cur': html.xpath('//input[@name="p4_Cur"]/@value')[0] if html.xpath(
                '//input[@name="p4_Cur"]/@value') else '',
                'p5_Pid': html.xpath('//input[@name="p5_Pid"]/@value')[0] if html.xpath(
                '//input[@name="p5_Pid"]/@value') else '',
                'p8_Url': html.xpath('//input[@name="p8_Url"]/@value')[0] if html.xpath(
                '//input[@name="p8_Url"]/@value') else '',
                'pa_MP': html.xpath('//input[@name="pa_MP"]/@value')[0] if html.xpath(
                '//input[@name="pa_MP"]/@value') else '',
                'pd_FrpId': html.xpath('//input[@name="pd_FrpId"]/@value')[0] if html.xpath(
                '//input[@name="pd_FrpId"]/@value') else '',
                'pm_Period': html.xpath('//input[@name="pm_Period"]/@value')[0] if html.xpath(
                '//input[@name="pm_Period"]/@value') else '',
                'pn_Unit': html.xpath('//input[@name="pn_Unit"]/@value')[0] if html.xpath(
                '//input[@name="pn_Unit"]/@value') else '',
                'pr_NeedResponse': html.xpath('//input[@name="pr_NeedResponse"]/@value')[0] if html.xpath(
                '//input[@name="pr_NeedResponse"]/@value') else '',
                'hmac': html.xpath('//input[@name="hmac"]/@value')[0] if html.xpath(
                '//input[@name="hmac"]/@value') else '',
            }
            url = 'https://www.yeepay.com/app-merchant-proxy/node'

            result = http_session.request(url=url, data=post_data, method='POST', verify=False)

            Logger().info("======== turn to post yeepay:{}".format(result.content))

            customer_no = post_data['p1_MerId']
            customer_request_no = post_data['p2_Order']
            pay_source_info = pay_dict['lqw_c9337']
            total_price = post_data['p3_Amt']

            post_data = {
                'token': None,
                'cardno': base64.b64encode(pay_source_info.credit_card_idno),
                'valid': base64.b64encode(pay_source_info.credit_card_validthru),
                'cvv2': base64.b64encode(pay_source_info.credit_card_cvv2),
                'phone': base64.b64encode(pay_source_info.reverse_mobile),
                'bankCode': 'BOC',
                'bankName': '中国银行',
                'cardType': 'CREDIT',
                'isBindpayFlag': False,
                'customerNo': customer_no,
                'customerRequestNo': customer_request_no,
            }

            Logger().info("====== yeepoy confirm post data:{}".format(post_data))

            query_str_list = []
            for k, v in post_data.items():
                query_str_list.append('{}={}'.format(k, v))
            query_str = '&'.join(query_str_list)
            url = 'https://cashdesk.yeepay.com/bc-cashier/bcncpay/firstpay/confirm?{}'.format(query_str)

            result = http_session.request(url=url, method='GET', verify=False).to_json()
            Logger().info("================ yeepoy confirm result : {}".format(result))

            Logger().info('send mobile sms code success %s' % pay_source_info.reverse_mobile)
            sms_verify_codes = Smser().get_yeepay_verify_code(provider_price=total_price)
            if sms_verify_codes:
                for sms_verify_code in sms_verify_codes:
                    gevent.sleep(0.2)
                    Logger().info('sms_verify_code %s' % sms_verify_code)
                    post_data.update({
                        'token': result['token'],
                        'verifycode': sms_verify_code,
                    })
                    query_str_list = []
                    for k, v in post_data.items():
                        query_str_list.append('{}={}'.format(k, v))
                    query_str = '&'.join(query_str_list)
                    url = 'https://cashdesk.yeepay.com/bc-cashier/bcncpay/firstpay/smsBackFill?{}'.format(query_str)

                    Logger().info("======= yeepoy mobile verify post data :{}".format(post_data))
                    result = http_session.request(url=url, method='GET', verify=False).to_json()
                    Logger().info("======== yeepoy mobile verify result:{}".format(result))

                    if result['bizStatus'] == 'success':
                        order_info.out_trade_no = customer_request_no
                        return pay_dict['lqw_c9337']
                    else:
                        raise PayException('sms verify error')
            else:
                raise PayException('yeepay get sms code error')

        else:
            raise PayException('ch have no pay channel!')
