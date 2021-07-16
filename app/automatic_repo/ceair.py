#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, too-many-arguments, broad-except, anomalous-backslash-in-string
# pylint: disable=missing-docstring, line-too-long, too-few-public-methods
"""
# @Author  : wxt
# @Software: PyCharm
"""

import time
import json
import random
import re
import string
import gevent
import base64
import datetime
from bs4 import BeautifulSoup
from ..controller.http_request import HttpRequest
from bs4 import BeautifulSoup
from urllib import quote
from Crypto.Cipher import DES
from .base import ProvderAutoBase
from ..utils.logger import Logger
from ..utils.util import cn_name_to_pinyin,modify_ni,modify_pp,RoutingKey
from ..controller.captcha import CaptchaCracker
from ..controller.emailer import Mailer
from ..controller.thirdparty_aux import DomesticTaxAux
from ..utils.exception import *
from ..utils.util import Time, Random, md5_hash, convert_utf8, simple_decrypt, simple_encrypt
from ..dao.iata_code import IATA_CODE
from ..dao.models import *
from ..dao.internal import *
from pony.orm import select
from ..utils.triple_des_m import desenc
from ..controller.smser import Smser,sms_lock
from app import TBG
from lxml import etree
from ..utils.blowfish import Blowfish


class Ceair(ProvderAutoBase):
    """
    自动化基类
    """
    timeout = 15  # 请求超时时间
    provider = 'ceair'  # 子类继承必须赋
    provider_channel = 'ceair_web'  # 子类继承必须赋
    operation_product_type = '会员折扣'
    operation_product_mode = 'A2A'
    pay_channel = '99BILL'
    is_include_booking_module = True # 是否包含下单模块
    trip_type_list = ['OW', 'RT']
    no_flight_ttl = 3600 * 3 # 无航班缓存超时时间设定
    carrier_list = ['MU','FM']  # 供应商所包含的航司列表，如果包含多个并且无法确定，请不要填写，此处会关联执飞航线判断逻辑


    CACHE_PR_CONFIG = {
        1: {'cabin_expired_time': 3600 * 12, 'cabin_attenuation': 3,'fare_expired_time':86400 * 30},
        2: {'cabin_expired_time': 3600 * 3, 'cabin_attenuation': 2,'fare_expired_time':86400 * 20},
        3: {'cabin_expired_time': 60 * 60 * 1.5, 'cabin_attenuation': 1,'fare_expired_time':86400 * 10},
        4: {'cabin_expired_time': 60 * 60, 'cabin_attenuation': 1,'fare_expired_time':86400 * 5},
        5: {'cabin_expired_time': 60 * 30, 'cabin_attenuation': 0,'fare_expired_time':86400},

    }
    search_interval_time = 0.01


    def __init__(self):
        super(Ceair, self).__init__()
        self.checkcode_exp_list = {
            'ceair': re.compile(r'<font color="red">(\d*)</font>'),
            'ceair_hk': re.compile(r'Captcha:Verification Code : (\d*)')
        }
        self.booking_retries = 3

    # def _order_split(self, order_info,passengers):
    #     """
    #     国际航班，并且价格大于1000，进行订单分拆
    #     不能将儿童单独拆分出来,每单一个成年人最多带三个小孩
    #     :param order_info:
    #     :return:
    #     """
    #     Logger().sdebug('order_info %s' % order_info)
    #     if order_info.routing.adult_price > 1000 and order_info.routing_range == 'OUT' and len(passengers) > 1:
    #         rl = []
    #         adt_list = [x for x in passengers if x.current_age_type(from_date=order_info.from_date, is_aggr_chd_adt=True) == 'ADT']
    #         chd_list = [x for x in passengers if x.current_age_type(from_date=order_info.from_date, is_aggr_chd_adt=True) == 'CHD']
    #
    #         for adt in adt_list:
    #             sub_order = [adt]
    #             for c in range(3):
    #                 if chd_list:
    #                     sub_order.append(chd_list.pop())
    #             rl.append(sub_order)
    #         return rl
    #     else:
    #         return [[x for x in order_info.passengers]]

    def _login(self, http_session, ffp_account_info):
        """
        登陆模块
        :return: 登陆成功的httpResult 对象
        """

        username = ffp_account_info.username
        password = ffp_account_info.password
        # result = http_session.request(url='https://passport.ceair.com/cesso/kaptcha.servlet?_0.29527411249554447', method='GET', stream=True).content
        # cracker = CaptchaCracker.select('Fateadm')
        # captcha_code = cracker.crack(result)
        # url = 'https://passport.ceair.com/cesso/login-static!auth.shtml'
        # data = {
        #     'user': username,
        #     'password': password,
        #     'validcode': captcha_code
        # }
        #
        # raw_response = http_session.request(url=url, method='POST', data=data, verify=False).content


        url = 'https://passport.ceair.com/cesso/geet!geetInit.shtml'
        result = http_session.request(url=url, method='POST', verify=False).to_json()

        # post_data = {
        #     'user': username,
        #     'password': password,
        #     'token': 'APDIDJS_donghang_{}aa9e9be23dfdf26493b1{}'.format(random.randint(100000, 999999),
        #                                                                 random.randint(100000, 999999)),
        #     'ltv': '1',
        #     'at': '1',
        # }
        # result = http_session.request(url='https://passport.ceair.com/cesso/login-static!auth.shtml',
        #                               method='POST', data=post_data, verify=False).to_json()
        challenge = result['challenge']
        gt = result['gt']

        cracker = CaptchaCracker.select('C2567')
        checked_gee = cracker.crack(geetest_gt=gt, geetest_challenge=challenge)
        geetest_challenge = checked_gee['challenge']
        geetest_validate = checked_gee['validate']
        geetest_seccode = checked_gee['validate'] + '|jordan'

        post_data = {
            'user': username,
            'password': password,
            'token': 'APDIDJS_donghang_{}aa9e9be23dfdf26493b1{}'.format(random.randint(100000, 999999),
                                                                        random.randint(100000, 999999)),
            'ltv': '1',
            'at': '1',
            'geetest_challenge': geetest_challenge,
            'geetest_validate': geetest_validate,
            'geetest_seccode': geetest_seccode,
            'validateType': 'geek',
        }
        result = http_session.request(url='https://passport.ceair.com/cesso/login-static!auth.shtml',
                             method='POST', data=post_data, verify=False).to_json()

        # if '验证码错误' in raw_response:
        #     cracker.justice()
        #     raise CaptchaCrackResultWrongException
        # elif 'SUCCESS' in raw_response:
        #     Logger().sinfo('Login success')
        #     return http_session
        # elif 'LET0001' in raw_response:
        #     # 密码 错误
        #     raise LoginCritical('password is incorrect')
        # elif 'LET0002' in raw_response:
        #     raise LoginCritical('locked')
        # else:
        #     Logger().warn('login fail result')
        #     raise LoginException

        if result['resultMessage'] == 'SUCCESS':
            Logger().sinfo('Login success')
            return http_session
        else:
            Logger().error('ceair login failed ! result:{}'.format(result))
            raise  LoginException

    def _check_login(self, http_session):
        """
        登录失败
        $.fullLoginCheck({"ipPosition":"SHA","loginModel":"1","message":"false","mobileNo":"","tier":"","time":"2018/07/02 18:01:47","username":"","uuid":"6ae602c3dfb8405d85b0e181b5c93e8b"})
        登陆成功
        $.fullLoginCheck({"ipPosition":"SHA","loginModel":"1","message":"true","mobileNo":"18797240897","tier":"STD","time":"2018/07/02 18:01:30","username":"林雪飞","uuid":"47884c479d7c427986c4ae07f4cbfe64"})
        :return:
        """
        url = 'http://www.ceair.com/member/auth!fullLoginCheck.shtml?_=%s' % Time.timestamp_ms()
        content = http_session.request(method='GET', url=url).content
        Logger().info('check_login %s' % content)
        if not content or '"username":""' in content:
            return False
        else:
            referer = 'http://ecrm.ceair.com/order/list.html?orderType=01'
            headers = {'Referer': referer}
            url = 'http://ecrm.ceair.com/traveller/side-bar!getInfo.shtml?callback=jQuery18305184980395053196_1532337792964&_=%s' % Time.timestamp_ms()
            content = http_session.request(method='GET', url=url, headers=headers).content
            Logger().info('check_login 2 %s' % content)
            if 'customName' in content:
                return True
            else:
                return False

    def extract_checkcode(self, content, provider):
        """
        提取验证码
        :param content:
        :return:
        """
        result = self.checkcode_exp_list[provider].findall(content)
        if result:
            return result[0]
        else:
            return None

    def _email_register(self,http_session,pax_info,ffp_account_info):

        Logger().info('email register start...')
        http_session = HttpRequest()
        modified_card_no = None
        retries_count = 2
        for x in range(0, retries_count):
            # 尝试5次
            err_code = None
            try:
                ffp_account_info = self._email_sub_register(http_session=http_session,pax_info=pax_info,ffp_account_info=ffp_account_info)
                return ffp_account_info
            except RegisterCritical as e:
                Logger().debug('e.err_code %s' %e.err_code)
                if x == retries_count - 1:
                    raise
                elif e.err_code == 'FFP_EXISTS':
                    err_code = 'FFP_EXISTS'
            except Exception as e:
                Logger().error(e)

            # 账号经过无法注册也无法登陆,修改证件号重新注册
            if err_code == 'FFP_EXISTS':
                if pax_info.card_type == 'NI':
                    # 身份证修改
                    modified_card_no = modify_ni(pax_info.card_ni)
                    pax_info.used_card_no = modified_card_no
                    pax_info.card_ni = modified_card_no
                    pax_info.modified_card_no = modified_card_no
                else:
                    modified_card_no = modify_pp(pax_info.card_pp)
                    pax_info.used_card_no = modified_card_no
                    pax_info.card_pp = modified_card_no
                    pax_info.modified_card_no = modified_card_no
                pax_info.attr_competion()
                Logger().sinfo('start modified_card_no %s register' % modified_card_no)

        else:
            raise RegisterException

    def _email_sub_register(self, http_session, pax_info, ffp_account_info):
        """
        注册模块
        :param pax_info:
        :return: ffp account info


        u'\u5165\u4f1a\u6e20\u9053\u53f7\u4e3a\u7a7a' 曾经报错：入会渠道号为空
        """
        self.change_email()
        # 请求注册页面
        url = 'https://m.ceair.com/mobile/user/user-ffp!toReg.shtml?channel=login&area=null'
        http_session.request(url=url, method='GET', verify=False)

        # 获取第一步极验challenge
        url = 'https://m.ceair.com/mobile/geetest/geetest!jyValidateDoGet.shtml?t=%s' % Time.timestamp_ms()
        http_conn = http_session.request(url=url, method='GET')
        geetest_body = http_conn.to_json()
        geetest_gt = geetest_body['gt']
        geetest_challenge = geetest_body['challenge']

        # 破解第一步极验验证码
        Logger().info('Crack First Gee')
        cracker = CaptchaCracker.select('C2567')
        """
        checked_gee = {u'status': u'ok', u'challenge': u'22e78dc84fe555b1b67b202a1effccabka', u'validate': u'a650d3d1b54f3de731c8796563d00a22'}

        """
        checked_gee = cracker.crack(geetest_gt=geetest_gt, geetest_challenge=geetest_challenge)
        # 发送邮箱验证码


        url = 'https://m.ceair.com/mobile/ffpuser/reg-ancestral!getSecurityCode.shtml?timestamp=0.9532313978693812'
        data = {
            'geetest_challenge': checked_gee['challenge'],
            'geetest_validate': checked_gee['validate'],
            'geetest_seccode': checked_gee['validate'] + '|jordan',
            'type': 'passport',
            'address': self.email_info['address']
        }
        http_conn = http_session.request(method='POST', url=url, data=data)
        result = http_conn.content

        if result == 'succ':
            Logger().info('Send Email Success')

            # # 获取极验第二步challenge
            # url = 'https://api.geetest.com/reset.php?gt=%s&challenge=%s&lang=zh-cn&w=iRYTnf9e1Zev7cVZ0XV42yUgk0HXBl8baqknfVmx3RYJmGKaemLwTYJcocC0xZ8Mrg9C)KGVt66q04T9iuFB(A96KWMImmDxcBEUD9G3Lft(3kjKC0J5NAg0fTXASkaWM4(Vtw5JiVMSeD2xQJPBv2UQbnjrvMdxHEiDbITnouxAMdtBFVeTwFpdRWpmnXX4jdIuH7lmcuVqf66aEja9QeXbnGq736UAvRVDTuDvBPg67qO17QSmnRgNxXa41YvB1b5fQ2CVhDQSNz2K(H1xa5hrlskCx4Bg2Whf0uXTvSBcJcpzjhH5L3ldFsc7EgE5)YmobUHBA937A4c(9Fip2d7mdtTlPOBSXA2ztQBWdWLuu3VtTLzhtE(7DoxrCzqKDuUe(nbSrju7fU0wOZ8xER1((ZNRgXdnH7HhAT91pMXc9w97ZafI9Q8T(BOcBTE2Q5vG7I5tXp6i)PzJrBvaHk312L3KugVvZTXI4cT41S7d7qspiLe63EvYg0xePquKNChwkjGhzSbaqwDfNieZkpEjY8so0oxCYXwZse3mgsjT6Xomm)Igyyp18)x7GJydCPr80Dm4NhDVGcS)ftX3BWjYCtPIHZ6XsgSndNG2R(FMH98vdOKkNNOmoQta5OQ3BuJX3ePNr89R2Y1S(ag78Y2VFVbFHZ3jhTGtljV9SncybLgseWLCGAd3GwjSpYMdbmr464m0oEO2nDLNYYkaqwINLlII2Mdae8ELno871O3YCX8agfqhmy2n)U0pRIYLx6c2QUvHnj62Y9v(bbwPdtvX23dLogK8AMJsMzs6J89zn)UWHDR5l07WH4DIPzW04gQjQeGYizl53CvGvCQzid6Tq0F2a5f0DPAEpHaD0)9HZDtROIokXJ)fzqXF4RRkBlj0l2fSm32)jdSUM95z7BIjhgZD)NxiQJS3PQX3fLJQfIU8lgmFYQdg7YT3HdJJTs(sB4XbIgAi)SX8v6wWf7R)0xnAHh8)tJXxW18Lgvh72uIvz6BGShLaEF0VGT9ucqIrNpWFOL4dxP4GdgMno0Sqq7yf5xQMltcY3XHfWq(2LN)yMNhxSZNX2wX4P1lJejfOmLwL67wWehSIzkksSNVgQqHh)DB)lkCaReuAd3WVjkfIOgMx1d)OiYFgWjpQ9vW9wkghoDln9lh39UxsHqaFpIpFdZk32cRFHtCNOl9Ax3kMmeYIPNg6M1vHeLPlxB5Fo5cC4llB35qb1Z06Qu1xlW63UFnjKmuj(JJaixZFq)RDZEwQ)10cWdYfS6cw9ViGa9PitV1h)bFOV0Bvsu4u1qK9YbXu2JO)oztWCqPzJQi8ltH3Dn0aPs4U2nAi(Gy5xAyxQV0nSS6YdITclQEPujLvHjRFpCbv09FENypC(Z4CjeWKjCMt7KukFQWGRZV2nSdZ(EJ0NpllnimxIpVlCj3eUMZQuSnQGOcKxmbV61yFXArzmxdnX9CPavu6Kz5Yt5Gt4qfJwP6EKJe1OHt(jfhAnDr7nylbh44paif4h8PBKtBgeEm(HY7OcLeucNQv5n6OrXID(XlSwf(KwXXRtmAQz)C2f6tQhzYAIfuqtbg2DVnuOeQObAG5uDPu4Ro71ZBVk1MkOysNY)picW0s(y)U4N5qabrZYiePJLvws7VRyhSkZfJxLfAh)bvS0cd1bf574fb4a8d6433b90c60022190acc3e62a18115f74ed5000206b30772e88434563e7dd2ede885517854aaccdfdb33d896ab959355fedb55cd464781626d6c0ec8a7846d169a7c9402b4266db221b5b50aa0dda3e5a73f55eac24cb30067d8b2d350a5ed5f1378e883b14e8f6eba3ec70d910bd67d3672b6731e014192a2&callback=geetest_1529491706272' % (
            # geetest_gt, geetest_challenge)
            #
            # http_conn = requests.get(url)
            # content = http_conn.content
            # print 'challenge_2'
            # print content
            # challenge_exp = re.compile(r'"challenge": "(.*)"')
            # challenge_2 = challenge_exp.findall(content)

            # 获取第一步极验challenge
            url = 'https://m.ceair.com/mobile/geetest/geetest!jyValidateDoGet.shtml?t=%s' % int(time.time())
            http_conn = http_session.request(method='GET', url=url, verify=False)
            geetest_body = http_conn.to_json()
            geetest_gt = geetest_body['gt']
            geetest_challenge = geetest_body['challenge']

            if geetest_body:
                # challenge_2 = challenge_2[0]
                # 破解第二步极验验证码
                Logger().info('Crack First Gee Success')
                checked_gee_2 = cracker.crack(geetest_gt=geetest_gt, geetest_challenge=geetest_challenge)

                mailer_obj = Mailer(user=self.email_info['user'], password=self.email_info['password'],
                                server=self.email_info['pop3_server'])
                register_email = mailer_obj.get_mail_via_receiver(receiver=self.email_info['address'])
                Logger().debug("========================== register mail content {}==============".format(register_email))
                checkcode = self.extract_checkcode(register_email, self.provider)
                if checkcode:
                    # 注册账号
                    Logger().info('Email Code Fetch Success')
                    url = 'https://m.ceair.com/mobile/ffpuser/reg-ancestral!doReg.shtml'
                    random_password = Random.gen_password()
                    # random_passport = Random.gen_passport()

                    if pax_info.card_type == 'NI':
                        card_no = pax_info.card_ni
                    else:
                        card_no = pax_info.card_pp


                    eng_exp = re.compile(r'^[A-Za-z]*$')
                    if eng_exp.match(pax_info.last_name + pax_info.first_name):
                        data = {
                            'geetest_challenge': checked_gee_2['challenge'],
                            'geetest_validate': checked_gee_2['validate'],
                            'geetest_seccode': checked_gee_2['validate'] + '|jordan',
                            'address': self.email_info['address'],
                            'random': '0.0838052%s' % Random.gen_num(10),
                            'cardNo': 'undefined',
                            'passportNo': card_no,
                            'nationality': pax_info.nationality,
                            'birthday': pax_info.birthdate,
                            'adultNo': '',
                            'adultPwd': '',
                            'sexs': '男' if pax_info.gender == 'M' else '女',
                            'sex': pax_info.gender,
                            'email': self.email_info['address'],
                            'checkNum': checkcode,
                            '': '已阅读并同意',
                            'membershipPassword': random_password,
                            'firstName': pax_info.first_name,
                            'lastName': pax_info.last_name,
                            'xiangNo': '',
                            'ApdidToken': 'APDIDJS_donghang_%s' % Random.gen_hash()

                        }
                    else:
                        data = {
                            'geetest_challenge': checked_gee_2['challenge'],
                            'geetest_validate': checked_gee_2['validate'],
                            'geetest_seccode': checked_gee_2['validate'] + '|jordan',
                            'address': self.email_info['address'],
                            'random': '0.0838052%s' % Random.gen_num(10),
                            'cardNo': 'undefined',
                            'passportNo': card_no,
                            'nationality': pax_info.nationality,
                            'birthday': pax_info.birthdate,
                            'adultNo': '',
                            'adultPwd': '',
                            'sexs': '男' if pax_info.gender == 'M' else '女',
                            'sex': pax_info.gender,
                            'email': self.email_info['address'],
                            'checkNum': checkcode,
                            '': '已阅读并同意',
                            'membershipPassword': random_password,
                            'firstName': Random.gen_full_name_3(),
                            'lastName': Random.gen_last_name(),
                            'xiangNo': '',
                            'ApdidToken': 'APDIDJS_donghang_%s' % Random.gen_hash()

                        }
                    http_conn = http_session.request(method='POST', url=url, data=data, verify=False)
                    register_result = http_conn.to_json()
                    """
                    {"cardId":"623021177138","cardPic":"iVBxxxxx","errorCode":"_2000","errorMsg":"注册成功!"}
                    """
                    Logger().info('register_result %s' % register_result)
                    if register_result.get('errorMsg') and register_result['errorMsg'] == '注册成功!':
                        ffp_account_info.username = register_result['cardId']
                        ffp_account_info.password = random_password
                        ffp_account_info.provider = self.provider
                        ffp_account_info.reg_passport = card_no
                        ffp_account_info.reg_birthdate = pax_info.birthdate
                        ffp_account_info.reg_gender = pax_info.gender
                        ffp_account_info.reg_card_type = pax_info.card_type
                        return ffp_account_info
                    elif register_result.get('errorMsg') and register_result['errorMsg'] == 'passport.exist' :
                        # {u'errorCode': u'3', u'errorMsg': u'passport.exist', u'cardPic': u'', u'cardId': u''}
                        raise RegisterCritical('ffp has already exists', err_code='FFP_EXISTS')
                    elif register_result.get('errorMsg') and register_result['errorMsg'] == 'program.member.DuplicateMemberProfilesExistsAsPerAlgorithm':
                        raise RegisterCritical('ffp profile already exist', err_code='FFP_EXISTS')
                    else:
                        raise RegisterException('email register unknown error result %s'% register_result)

                else:
                    raise RegisterException('Email Code Fetch Failed')

            else:
                raise RegisterException('Crack First Gee Failed')

        else:
            Logger().warn('RegisterException %s' % result)
            raise RegisterException('failed')

    def _booking_without_register(self, http_session, order_info):

        order_info.provider_order_status = 'LOGIN_FAIL'
        http_session = self.login(http_session, order_info.ffp_account)

        gevent.sleep(0.2)
        order_info.provider_order_status = 'SEARCH_FAIL'
        search_result = self.flight_search(http_session, order_info, cache_mode='REALTIME')  # booking前必须search

        order_info.provider_order_status = 'BOOK_FAIL'
        # 确认航班
        gevent.sleep(0.2)
        Logger().info('confirm flight ')
        # Logger().debug(order_info.assoc_search_routings)
        # frs = [flight_routing for flight_routing in order_info.assoc_search_routings if flight_routing.routing_key == order_info.routing.routing_key]
        # if frs:
        #     order_info.routing = frs[0]
        # else:
        #     order_info.provider_order_status = 'BOOK_FAIL_NO_CABIN'
        #     raise BookingException(err_code='BOOK_FAIL_NO_CABIN')

        # fscKey, snk, airPriceUnitIndex = self._flight_search_web(http_session, order_info)
        # if not fscKey or not snk:
        #     raise BookingException('ceair_session_id not found')

        for routing in search_result.assoc_search_routings:
            # Logger().debug(routing)
            if RoutingKey.trans_cp_key(simple_decrypt(routing.routing_key)) == RoutingKey.trans_cp_key(
                simple_decrypt(order_info.routing.routing_key)):
                order_info.routing = routing
                break
        if not order_info.routing.fsc_key or not order_info.routing.snk:
            raise BookingException('ceair_session_id not found')

        """
        post
        单程
        selectConds={"fscKey":"OW:1:0:0:zh:CNY:a:/SHA:SZX:2018-11-02:,:NEWOTA",
        "selcon":[{"airPriceUnitIndex":0,"snk":"SHA1541118000000SZX1541127300000FM9331HYJ_ECB1470.0"}]}&sessionId=1529663033735
        往返
        ={"fscKey":"RT:1:0:0:zh:CNY:a:/SHA:SIN:2018-11-02:,SIN:SHA:2018-11-04:,:NEWOTA","selcon":[{"airPriceUnitIndex":6,"snk":"SHA1541088300000SIN1541107500000SIN1541264100000SHA1541283900000MU543/MU544HYZJ_SHA_GJS/S1060/1060"}]}&sessionId=1530517061061
        return
        /flight/flight_booking_passenger.html;3b4de196dd3d45df8b6ebdd76527f343
        """
        # if order_info.extra_data_2:
        #     ceair_session_id = int(order_info.extra_data_2)
        #     fsc_key = order_info.extra_data_3
        #     Logger().debug('ceair_session_id %s ' % ceair_session_id)
        #     Logger().debug('fsc_key %s ' % fsc_key)
        # else:
        #     raise BookingException('ceair_session_id not found')

        # select_conds = {
        #     'fscKey':fsc_key,
        #     'selcon': [{"airPriceUnitIndex": order_info.routing.air_price_unit_index, "snk": order_info.routing.snk}]
        # }
        select_conds = {
            'fscKey': order_info.routing.fsc_key,
            'selcon': [{"airPriceUnitIndex": order_info.routing.product_index, "snk": order_info.routing.snk}]
        }

        Logger().debug('select_conds %s ' % select_conds)
        data = {
            'selectConds': json.dumps(select_conds),
            # 'sessionId': ceair_session_id
        }
        url = 'http://www.ceair.com/otabooking/flight-confirm!flightConfirm.shtml'
        http_conn = http_session.request(method="post", url=url, data=data, verify=False)
        result = http_conn.content
        all_check_token = result.split(';')[1]
        all_check_token = all_check_token.split('|')[0]

        # 获取信息更新session
        gevent.sleep(0.2)
        Logger().info('paxinfo init')
        url = 'http://www.ceair.com/otabooking/paxinfo-input!init.shtml?_=%s&' % Time.timestamp_ms()
        http_conn = http_session.request(method='GET', url=url, verify=False)
        # result = http_conn.content
        # session_version_exp = re.compile(r'var sessionVersion = "(.*?)";')
        # search_result = session_version_exp.findall(result)

        # if search_result:
        #     session_version = int(search_result[0])
        # else:
        #     raise BookingException('search_version fetch error')
        search_result = http_conn.to_json()
        session_version = search_result.get('sessionVersion')
        if not session_version:
            raise BookingException('search_version fetch error')

        # 更新乘机人信息
        gevent.sleep(0.2)
        Logger().info('update paxinfo')
        url = 'http://www.ceair.com/otabooking/paxinfo-input!checkDataNew.shtml'

        pax_data = []
        for pax_info in order_info.passengers:

            # 如果是INF 需要填写监护人
            inf_carrier_name = ''
            inf_carrier_idno = ''
            age_type = pax_info.current_age_type(order_info.from_date)
            if age_type == 'INF':
                for __ in order_info.paxs:
                    if not __.has_inf:
                        __age_type = __.current_age_type()
                        if __age_type == 'ADT':
                            if __.used_card_type == 'PP':
                                inf_carrier_name = '%s/%s' % (__.last_name, __.first_name)
                            elif __.used_card_type == 'NI':
                                inf_carrier_name = __.name
                        __.has_inf = True
                    break
            # 根据卡类型
            if pax_info.used_card_type == 'NI':

                pax_data.append({"uuid": 0,
                                 "benePaxListIndex": "",
                                 "birthday": '',
                                 "docaCity": "Park",
                                 "docaNationCode": "",
                                 "docaPostCode": "19019",
                                 "docaState": "PA",
                                 "docaStreet": "Shinfield Road Reading RG2 7ED",
                                 'email': '',
                                 "ffpAirline": "",
                                 "ffpLevel": "",
                                 "ffpNo": "",
                                 "gender": pax_info.gender,
                                 "idNo": pax_info.selected_card_no,
                                 "idType": 'NI',
                                 "id": "",
                                 "idValidDt": "",
                                 "idIssueNation": "",
                                 "nationality": "",
                                 "infCarrierName": inf_carrier_name,
                                 "insurance": False,
                                 "insureInfos": [],
                                 "mobile": TBG.global_config['OPERATION_CONTACT_MOBILE'],
                                 "contactInfo": "",
                                 "contacts": "mobile",
                                 "cardId": "",
                                 "paxType": age_type,
                                 "paxNameCn": "",
                                 "paxName": pax_info.name,
                                 "paxNameFirst": "",
                                 "paxNameLast": "",
                                 "isBeneficariesAssigned": False,
                                 "isBeneficiary": "",
                                 "paxOrigin": "0",
                                 "idDetails": [
                                     {"id": "", "idNo": pax_info.selected_card_no, "idType": pax_info.used_card_type}]})
            else:  # 暂时认为是护照类型
                pax_data.append({"uuid": 0,
                                 "benePaxListIndex": "",
                                 "birthday": pax_info.birthdate,
                                 "docaCity": "Park",
                                 "docaNationCode": "",
                                 "docaPostCode": "19019",
                                 "docaState": "PA",
                                 "docaStreet": "Shinfield Road Reading RG2 7ED",
                                 "email": TBG.global_config['OPERATION_CONTACT_EMAIL'],
                                 "ffpAirline": "",
                                 "ffpLevel": "",
                                 "ffpNo": "",
                                 "gender": pax_info.gender,
                                 "idNo": pax_info.selected_card_no,
                                 "idType": pax_info.used_card_type,
                                 "id": "",
                                 "idValidDt": pax_info.card_expired,
                                 "idIssueNation": 'CN',
                                 "nationality": pax_info.nationality if pax_info.nationality else 'CN',
                                 "infCarrierName": inf_carrier_name,
                                 "infCarrierIdNo": inf_carrier_idno,
                                 "insurance": False,
                                 "insureInfos": [],
                                 "mobile": TBG.global_config['OPERATION_CONTACT_MOBILE'],
                                 "contactInfo": "",
                                 "contacts": "mobile",
                                 "cardId": "",
                                 "paxType": pax_info.age_type,
                                 "paxName": "",
                                 "paxNameCn": Random.gen_full_name(),
                                 "paxNameFirst": pax_info.first_name,
                                 "paxNameLast": pax_info.last_name,
                                 "isBeneficariesAssigned": False,
                                 "isBeneficiary": "",
                                 "paxOrigin": "",
                                 "idDetails": [
                                     {"id": "", "idNo": pax_info.selected_card_no, "idType": pax_info.used_card_type,
                                      "idValidDt": pax_info.card_expired,
                                      "idIssueNation": 'CN', }]})
        data = {
            'allPaxInfo': json.dumps(pax_data),
            'sessionVersion': session_version
        }
        Logger().info('pax_info request %s' % data)
        http_conn = http_session.request(method='POST', url=url, data=data, verify=False)
        result = http_conn.content

        # # 获取联系人信息
        # url = 'http://ecrm.ceair.com/traveller/optmember/contact-pax!queryContactPax.shtml?callback=jQuery18308554527412052562_1529664152265&_=1529664153043&_=1529664153043'
        # http_conn = s.get(url)
        # result = http_conn.content
        # contact_exp = re.compile(r'jQuery18308554527412052562_1529664152265(.*)')
        # contact_info = json.loads(contact_exp.findall(result)[0])
        # # TODO:需要容错 返回失败的情况 status  != SUCCESS
        # contact_pax = contact_info['contactPaxDtos'][0]
        # contact_pax.pop('priority')
        # contact_pax.pop('remark')
        # logger.info(contact_pax)

        # 更新联系人信息
        """
        在不存储联系人的情况下自己构造请求
        {"contactName":"刘志","contactMobile":"15216666047","contactEmail":"fdaljrj@tongdun.org","id":""}
        """
        gevent.sleep(0.2)
        Logger().info('update contactinfo')
        url = 'http://www.ceair.com/otabooking/paxinfo-input!checkContactInfo.shtml'
        # 带有ID需要先获取ID

        # TODO 此处写死为指定手机号码
        contact = order_info.contacts[0]
        contact_pax = {
            "contactName": contact.name,
            "contactMobile": TBG.global_config['OPERATION_CONTACT_MOBILE'],
            "contactEmail": TBG.global_config['OPERATION_CONTACT_EMAIL'], "id": ""
        }
        data = {
            'contactInfo': json.dumps(contact_pax),
            'sessionVersion': session_version
        }
        http_conn = http_session.request(method='POST', url=url, data=data, verify=False)
        result = http_conn.content

        # 确认订票信息
        gevent.sleep(0.2)
        Logger().info('showBookingInfoNew')
        url = 'http://www.ceair.com/otabooking/paxinfo-input!showBookingInfoNew.shtml'
        data = {
            'allPaxInfo': json.dumps(pax_data),
            'contactInfo': json.dumps(contact_pax),
            'sessionVersion': session_version
        }
        http_conn = http_session.request(method='POST', url=url, data=data, verify=False)
        result = http_conn.content
        Logger().info('confirm booking result %s' % result)

        if result == 'success':
            Logger().info('confirm booking success')

            # 查看订票信息
            gevent.sleep(0.2)
            url = 'http://www.ceair.com/otabooking/paxinfo-input!getBooingInfojsonView.shtml?_=%s' % Time.timestamp_ms()
            http_conn = http_session.request(method='GET', url=url, verify=False,
                                             comment='paxinfo-input!getBooingInfojsonView.shtml', print_info=True)
            result_1 = http_conn.to_json()
            order_info.provider_price = float(
                [x for x in result_1[0]['totalPriceList'] if x['currency'] == 'CNY'][0]['price'])

            # 仅获取一次红包
            try:
                self.get_coupon(ffp_account_info=order_info.ffp_account)

                # 使用红包
                # 获取红包信息
                gevent.sleep(0.2)
                Logger().info('get hongbao info')
                url = 'http://www.ceair.com/otabooking/paxinfo-input!loadDiscountDetailNew.shtml?_=1529927885876'
                http_conn = http_session.request(method='GET', url=url)
                result = http_conn.to_json()
                hongbao_json = result
                Logger().info('discount detail %s' % hongbao_json)

                hongbao_info = None
                for hongbao in hongbao_json['couponList']:
                    if hongbao.get('couponType') == 'VISA18_HONGBAO_100':
                        hongbao_info = hongbao
                        break
                if not hongbao_info:
                    raise Exception('have no visa hongbao')

                """
                {"couponDetail":[{"couponNum":1,"couponNo":"HB15299208613579754","couponType":"VISA18_HONGBAO_100","avaliableNode":"01#01#01"}],"couponCate":"HB","checked":true}
                """
                gevent.sleep(0.2)
                Logger().info('use hongbao ')
                hongbao_data = {
                    'couponDetail': [
                        {
                            'couponNum': 1,
                            'couponNo': hongbao_info['couponNo'],
                            'couponType': hongbao_info['couponType'],
                            # 'avaliableNode': hongbao_info['avaliableList'][0],

                        }
                    ],
                    'couponCate': hongbao_info['couponCate'],
                    'checked': True
                }
                """
                {"checked":true,"couponCate":"HB","couponDisplay":"面值100元Visa专属红包",
                "couponRuleContent":"[{\"couponType\":\"VISA18_HONGBAO_100\",\"rule\":
                [\"1、本活动仅限“东方万里行”会员参与\",\"2、领红包日期：2018年1月1日- 2018年12月31日\",\"3、红包有效期：自领取入账之日起一个月内使用有效
                。\",\"4、Visa红包每日十点开抢，数量有限，先到先得，领完即止。\",\"5、每个账户单次最多可领取一张机票红包券，
                每月限成功领取一次。\",\"6、Visa红包仅限在东航官网（www.ceair.com）使用，东方航空APP、手机M网站仅支持领取不支持使用。\",
                \"7、票价满1000元可用100元券。\",\"8、领取的红包券仅限会员为其本人（每个订单限一人）购买所有航段均由东航或上航实际承运的国际或港澳台地区航线客票时使用，
                部分特价产品可不支持使用本红包券抵扣，具体以产品自身规则为准，购买时请仔细确认后再支付。\",\"9、会员一经使用Visa红包扣减订单金额后，
                支付时仅限使用Visa指定信用卡（中国大陆发行的Visa双标白金卡、无限卡） 并通过 支付通道完成付款。\",\"10、使用红包券购买的客票不可签转，
                发生改期或升舱除按规则收取变更手续费外，还需补足优惠部分差价；客票退票将按规则收取相应手续费，退票成功将返还该订单红包但不延长有效期。\"]}]",
                "couponType":"VISA18_HONGBAO_100","currency":"CNY","discountInfoList":[
                {"arriveAirport":"SIN","couponNo":"HB1536926716871230","couponNum":1,"departAirport":"PVG","discountAmt":100,"discountAmtFmt":100,"discountRate":0,"idNo":"DDD23213","segId":0,"segPriceNew":0,"segPriceOld":0}],"exception":"","exceptionCode":"","payReduceAmt":100,"payTotalAmtAft":6188,"payTotalAmtBef":6288,"payTotalPointAft":0,"payTotalPointBef":0}
                """
                url = 'http://www.ceair.com/otabooking/paxinfo-input!getTalentInfoNew.shtml'
                params = {
                    'drList': json.dumps(hongbao_data),
                    '_': Time.timestamp_ms()
                }
                http_conn = http_session.request(method='GET', url=url, params=params)
                result = http_conn.content
                try:
                    hbresult_json = json.loads(result)
                    discountamt = hbresult_json['payReduceAmt']
                    order_info.provider_price -= discountamt  # 计算加入红包后的金额
                except Exception as e:
                    raise
                Logger().info('use hongbao result %s' % result)


            except Exception as e:
                Logger().error('hongbao error %s' % e)

            if result_1[0]['verificationCode'] == True and result_1[0]['verify'] == 'scheckCode':
                Logger().info('Crack Gee')
                gee_tries_count = 3
                gee_tries = 0
                for x in range(0, 5):
                    url = 'http://www.ceair.com/otabooking/validate-geek-check!startCaptcha.shtml'
                    http_conn = http_session.request(method='POST', url=url)
                    result = http_conn.to_json()
                    geetest_gt = result['gt']
                    geetest_challenge = result['challenge']

                    # 破解第一步极验验证码

                    cracker = CaptchaCracker.select('C2567')
                    """
                    checked_gee = {u'status': u'ok', u'challenge': u'22e78dc84fe555b1b67b202a1effccabka', u'validate': u'a650d3d1b54f3de731c8796563d00a22'}

                    """
                    checked_gee = cracker.crack(geetest_gt=geetest_gt, geetest_challenge=geetest_challenge)

                    url = 'http://www.ceair.com/otabooking/validate-geek-check!verifyLogin.shtml'
                    data = {
                        'geetest_challenge': checked_gee['challenge'],
                        'geetest_validate': checked_gee['validate'],
                        'geetest_seccode': checked_gee['validate'] + '|jordan'
                    }
                    http_conn = http_session.request(method='POST', url=url, data=data)
                    result = http_conn.to_json()
                    if result['status'] == 'success':
                        Logger().info('gee crack success')
                        break
                    else:
                        if gee_tries >= gee_tries_count:
                            raise BookingException('gee crack error')
                        else:
                            Logger().warn('gee crack err try again')
                            gee_tries += 1

                # 发送手机验证码

                url = 'http://www.ceair.com/booking/verification-code!sendVerificationCode.shtml?_=%s&telNum=%s' % (
                Time.timestamp_ms(), self.mobile_info['mobile'])
                http_conn = http_session.request(method='GET', url=url)
                result = http_conn.content
                if result == 'success':
                    # 获取手机计算题验证码
                    sms_verify_codes = Smser().get_ceair_booking_verify_code(mobile_info=self.mobile_info)
                    Logger().info('sms codes list %s' % sms_verify_codes)
                    sms_success = False
                    for sms_verify_code in sms_verify_codes:
                        url = 'http://www.ceair.com/booking/verification-code!checkValidationCode.shtml?checkCode=%s&telNum=%s&_=%s' % (
                            sms_verify_code, self.mobile_info['mobile'], Time.timestamp_ms())
                        http_conn = http_session.request(method='GET', url=url)
                        result = http_conn.content
                        if result == 'success':
                            sms_success = True
                            Logger().info('sms code recieved and crack success')
                            break
                        else:
                            Logger().info('sms code crack result failed: {}'.format(result))
                    if sms_success:
                        pass
                    else:
                        raise BookingException('sms code wrong')

                else:
                    raise BookingException('sms code send failed')

            # 获取订票验证码
            gevent.sleep(0.2)
            Logger().info('getBookingVerficationCode')
            url = 'http://www.ceair.com/booking/verification-code!getBookingVerficationCode.shtml?_=1528967934908'
            http_conn = http_session.request(url=url, method='GET')
            check_token = http_conn.content
            Logger().info('check_token %s' % check_token)

            # 提交并订票
            """
            失信人员
            1.根据中国最高人民法院不得向失信人提供运输服务的要求，您的订单中有旅客为失信被执行人，故无法购买机票。请将订单中的失信被执行人与普通旅客分开后，再为普通旅客购票，若有疑问请联系执行法院，谢谢配合! IBE16210,IBE16210|20-1-121377
            {"airOrderResList":[],"airResultCode":"IBE16210","airResultMsg":"根据中国最高人民法院不得向失信人提供运输服务的要求，您的订单中有旅客为失信被执行人，故无法购买机票。请将订单中的失信被执行人与普通旅客分开后，再为普通旅客购票，若有疑问请联系执行法院，谢谢配合! IBE16210",
            "crossFailXOrderList":[],"crossSucessXOrderList":[],"errorMessageList":[],"language":null,"needRebooking":false,"nextUrl":null,"orderNo":null,"resultCode":"20-1-121377",
            "resultMessage":"根据中国最高人民法院不得向失信人提供运输服务的要求，您的订单中有旅客为失信被执行人，故无法购买机票。请将订单中的失信被执行人与普通旅客分开后，再为普通旅客购票，若有疑问请联系执行法院，谢谢配合! IBE16210",
            "shoppingType":null,"timeStamp":null,"transactionId":null,"version":null,"waringMessageList":[]}

            success
            {"airOrderResList":[{"airOrderType":"D_DI_MU_HYZJ_SHA","couponOrderNo":""}],"airResultCode":"1001","airResultMsg":null,"crossFailXOrderList":[],"crossSucessXOrderList":[{"orderXNo":null,"orderXType":"AIR","resultCode":"1001"}],"errorMessageList":[],"language":null,"needRebooking":false,"nextUrl":"https://unipay.ceair.com/unipay/preparepay/pay!payInit.shtml?parameter=jvgJa3ZKo2LIZXo8liB3D20OM37tvgA75DnNJvhdUWqiYrI2JelYyRGsBrupou8lvpKN62K5bmcTTA3WsfGWJUb8Z/SdkGpsTuJ%2B%2BL0XGZ5OoR1kvpkzrDSaLbj2pCEwMaxd8toAnnYPJwSXVw6fRlkYsqrb9AiFczjTZHxdFTdbeULco3206YV%2BvgJRzYI8vZTjJUyLqecylm7gjHf0XA==","orderNo":71180614274920,"resultCode":"1001","resultMessage":null,"shoppingType":null,"timeStamp":null,"transactionId":null,"version":null,"waringMessageList":[]}
            failed
            {"airOrderResList":[],"airResultCode":null,"airResultMsg":null,"crossFailXOrderList":[],"crossSucessXOrderList":[],"errorMessageList":[],"language":null,"needRebooking":false,"nextUrl":null,"orderNo":null,"resultCode":"19-8-298619","resultMessage":"您的机票信息可能已被更改，请重新查询预订","shoppingType":null,"timeStamp":null,"transactionId":null,"version":null,"waringMessageList":[]}
            """
            gevent.sleep(0.2)
            Logger().info('booking')
            url = 'http://www.ceair.com/otabooking/booking!booking.shtml?checkToken=%s&allCheckToken=%s' % (
                check_token, all_check_token)
            http_conn = http_session.request(url=url, method='GET')
            result = http_conn.to_json()
            if result.get('orderNo'):
                order_id = result['orderNo']
                order_info.provider_order_id = str(order_id)
                order_info.provider_order_status = 'BOOK_SUCCESS_AND_WAITING_PAY'
                Logger().info('orderNo %s' % order_id)
                return order_info
            else:
                """
                如果 getBooingInfojsonView 中字段 "verificationCode":true,"verify":"scheckCode" 则需要弹出极验验证码
                [2018-07-23 11:25:32,722][order_worker][DEBUG]After data: url{"airOrderResList":[],"airResultCode":null,"airResultMsg":null,"crossFailXOrderList":[],"crossSucessXOrderList":[],"errorMessageList":[],"language":null,"needRebooking":false,"nextUrl":null,"orderNo":null,"resultCode":"23-3-958675","resultMessage":"您的验证未能通过，无法继续为您提供订票服务！","shoppingType":null,"timeStamp":null,"transactionId":null,"version":null,"waringMessageList":[]}

                """
                Logger().warn('last step result %s' % result)
                raise BookingException('last step error')

        elif 'success|CHANGELOGIN:{"' in result:
            # login session expired
            query_params = {'username': order_info.ffp_account.username, 'password': order_info.ffp_account.password}
            TBG.cache_access_object.insert(cache_type='login_headers', provider=self.provider, ret_data='',
                                       param_model=query_params, expired_time=1)
            TBG.cache_access_object.insert(cache_type='login_session', provider=self.provider, ret_data='',
                                       param_model=query_params, expired_time=1)
            gevent.sleep(10)
            order_info.ffp_account.username = order_info.ffp_account.reg_pid if order_info.ffp_account.reg_pid else order_info.ffp_account.reg_passport
            http_session = self.login(http_session, order_info.ffp_account)
            raise BookingException('confirm booking login session expired')
        else:
            gevent.sleep(2)
            raise BookingException('confirm error')

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

        if not order_info.ffp_account:
            # 如果没有账号才需要注册
            try:
                paxs = [x for x in order_info.passengers if x.current_age_type(from_date=order_info.from_date, is_aggr_chd_adt=True) == 'ADT']
                if paxs:

                    ffp_account_info = self.register(http_session=http_session, pax_info=paxs[0], flight_order_id=order_info.flight_order_id, sub_order_id=order_info.sub_order_id)
                else:
                    raise RegisterCritical('NO ADT FOUND ,CAN NOT REGISTER')
            except Critical as e:
                raise
            order_info.ffp_account = ffp_account_info  # 需要将账号信息反馈到order_info
            gevent.sleep(0.2)

        self._booking_without_register(http_session, order_info)



    def _get_fix_account(self):

        static_account = {
            'username': '663023042516',
            'password': '66281672',
            'passport': 'C70931163',
            'birthdate': '1983-10-22',
            'gender': 'M',

        }
        account = TBG.redis_conn.redis_pool.rpoplpush('ceair_account_list', 'ceair_account_list')
        account = eval(account) if account else static_account
        return account

    @db_session
    def _simulate_booking(self, order_info):

        try:
            if not order_info.routing_range in ['I2O', 'O2I']:
                return order_info

            single_segment_trigger_price = 1000
            multi_segment_trigger_price = 0
            trigger_price = single_segment_trigger_price
            routing_info = RoutingKey.unserialize(order_info.verify_routing_key, is_encrypted=True)
            total_price = (float(routing_info['adult_price']) + float(routing_info['adult_tax'])) * order_info.adt_count + \
                          (float(routing_info['child_price']) + float(routing_info['child_tax'])) * order_info.chd_count
            cabin_list = routing_info['cabin'].split('-')
            if len(cabin_list) > 1:
                trigger_price = multi_segment_trigger_price
            if total_price <= trigger_price:
                return order_info

            order_info.is_simulate_booking = 1

            account = self._get_fix_account()
            order_info.ffp_account = FFPAccountInfo()
            order_info.ffp_account.username = account['username']
            order_info.ffp_account.password = account['password']

            pax_info = PaxInfo()
            pax_info.passenger_id = 'TC128926'
            pax_info.last_name = 'G'
            pax_info.first_name = 'MARS'
            pax_info.name = 'MARS/G'
            pax_info.age_type = 'ADT'
            order_info.adt_count += 1
            pax_info.birthdate = account['birthdate']
            pax_info.gender = account['gender']
            # 这里把除了身份证之外的证件一律作为护照处理
            pax_info.used_card_type = 'PP'
            pax_info.card_type = 'PP'
            pax_info.used_card_no = account['passport']
            pax_info.card_pp = account['passport']
            pax_info.card_expired = '2028-02-20'
            pax_info.card_issue_place = 'CN'
            pax_info.nationality = 'CN'
            order_info.passengers = [pax_info]

            contact_info = ContactInfo()
            contact_info.address = 'road'
            contact_info.postcode = '200000'
            contact_info.email = TBG.global_config['OPERATION_CONTACT_EMAIL']
            contact_info.mobile = TBG.global_config['OPERATION_CONTACT_MOBILE']
            contact_info.name = '南运'
            order_info.contacts = [contact_info]

            order_info.routing = FlightRoutingInfo()
            order_info.routing.routing_key_detail = RoutingKey.decrypted(order_info.verify_routing_key)
            order_info.routing.routing_key = order_info.verify_routing_key

            http_session = HttpRequest()
            self._booking_without_register(http_session, order_info)
        except Exception as e:
            err_list = [
                'ceair_session_id not found',
                'search_version fetch error',
                'confirm error',
                'last step error',
            ]
            for err in err_list:
                if err in str(e):
                    raise BookingException(e)
            else:
                order_info.provider_order_status = 'BOOK_SUCCESS_AND_WAITING_PAY'
                return order_info

    def _check_order_status(self, http_session, ffp_account_info, order_info):
        """
        检查订单状态
        :param http_session:
        :param order_id:
        :return: 返回订单状态
        航司订单状态
        {10050:{tips:"等待支付",className:"waitPayB"},
        10051:{tips:"支付成功",className:"waitPayG"},
        10052:{tips:"交易处理中",className:"waitPayG"},
        10053:{tips:"差错退款",className:"warning"},
        10054:{tips:"交易成功",className:"success"},
        10055:{tips:"交易异常",className:"error"},
        10056:{tips:"交易取消",className:"cancel"},
        10057:{tips:"等待确认",className:"waitPay"},
        10058:{tips:"预定失败",className:"cancel"},
        10059:{tips:"退票",className:"warning"}，

        """
        status_map = {
            '10050': 'BOOK_SUCCESS_AND_WAITING_PAY',
            '10051': 'PAY_SUCCESS',
            '10052': 'PAY_SUCCESS',
            '10053': 'ISSUE_FAIL',
            '10054': 'ISSUE_SUCCESS',
            '10055': 'ISSUE_FAIL',
            '10056': 'ISSUE_CANCEL',
            # '10057': 'BOOK_SUCCESS_AND_WAITING_PAY',
            '10057': 'PAY_SUCCESS',
            '10058': 'ISSUE_FAIL',
            '10059': 'MANUAL_RERUND',

        }
        order_info.provider_order_status = 'LOGIN_FAIL'
        http_session = self.login(ffp_account_info=ffp_account_info)
        # 检查订单状态
        url = 'http://ecrm.ceair.com/traveller/optmember/order-query!queryOrderDetails.shtml'
        data = {
            'orderNo': order_info.provider_order_id,
            'orderType': 'AIR'
        }
        headers = {'Referer': 'http://ecrm.ceair.com/order/detail.html'}
        http_conn = http_session.request(method='POST', url=url, data=data, verify=False, headers=headers)
        encrypt_content = http_conn.content
        content_key = json.loads(http_conn.response_headers[0]).get('Content-Key')
        Logger().info("========== order detail content key:{}".format(content_key))
        des_key, des_iv = content_key.split(',')
        des_obj = DES.new(des_key, DES.MODE_CBC, des_iv)
        decrypt_content = des_obj.decrypt(base64.b64decode(encrypt_content))
        Logger().info("========== encrypt content:{}".format(encrypt_content))
        Logger().info("========== decrypt content:{}".format(decrypt_content))
        result = json.loads(re.findall(r'{.*}', decrypt_content)[0])
        err = result['errorResult']
        if err:
            raise CheckOrderStatusException(json.dumps(err))
        else:
            order_status = result['orderInfoDto']['orderStatus']
            order_info.provider_order_status = status_map[order_status]
            if order_info.provider_order_status == 'ISSUE_SUCCESS':
                # 需要将票号、PNRCODE 存入
                for pax in result['paxInfoDtoList']:
                    for pax_info in order_info.passengers:
                        if pax_info.used_card_type == pax['paxDetailDto']['paxIdInfoList'][0]['idType'] and pax_info.selected_card_no == pax['paxDetailDto']['paxIdInfoList'][0]['idNo']:
                            pax_info.ticket_no = pax['tripInfoDtoList'][0]['airSegInfoDto']['tktNo']
                        order_info.pnr_code = pax['tripInfoDtoList'][0]['airSegInfoDto']['relPnrNo']
                # 存入交易流水号
                if result['orderPayInfoDtoList'] and result['orderPayInfoDtoList'][0].get('bankSerial'):
                    order_info.out_trade_no = result['orderPayInfoDtoList'][0]['bankSerial']
        Logger().debug('order status %s' % result)



    def _get_coupon(self, http_session, ffp_account_info):
        """
        获取VISA红包
        :return:
        """

        http_session = self.login(http_session=http_session, ffp_account_info=ffp_account_info)

        url = 'http://ecrm.ceair.com/traveller/optmember/coupon-visa!present.shtml?_=1232321321'
        referer = 'http://ecrm.ceair.com/a/visa_hongbao2018.html'
        headers = {'referer': referer}
        http_conn = http_session.request(method='GET', url=url, verify=False, headers=headers)
        content = http_conn.content
        try:
            result = json.loads(content)
            if result['code'] == 'SUCCESS':
                Logger().info('visa-coupon get success')

                return True
            elif result['errorResult']['resultMsg'] == u"您本月已领取Visa红包，请下月再试":
                Logger().info('visa-coupon has got')
                return True
            else:
                Logger().warn('visa-coupon failed')
        except Exception as e:
            Logger().error('visa-coupon failed')
        raise GetCouponException

    def to_format(self, data):
        """
        将数据标准化
        :param kwargs:
        :return:
        """
        pass

    def _flight_search_web(self, http_session, search_info):

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

        gevent.sleep(0.1)
        Logger().debug('search flight')

        # search_cond = {"adtCount":search_info.adt_count ,
        #                "chdCount": search_info.chd_count ,
        #                "infCount": search_info.inf_count ,
        if search_info.adt_count == 0 or search_info.adt_count is None:
            adt_count = 1
        else:
            adt_count = search_info.adt_count

        # 因为东航查询必须输入机场名字，在这里对部分机场名字进行mapping


        search_cond = {"adtCount": adt_count,
                       "chdCount": search_info.chd_count,
                       "infCount": search_info.inf_count,
                       # "version":"A.1.0",  # 东航搜索改版
                       "currency": "CNY",
                       "tripType": search_info.trip_type,
                       "recommend": False,
                       "reselect": "",
                       "page": "0",
                       "sortType": "a",
                       "sortExec": "a",
                       "segmentList": [
                           {"deptCd": self.iata_code_mapping(search_info.from_airport),
                            "arrCd": self.iata_code_mapping(search_info.to_airport),
                            "deptDt": search_info.from_date,
                            "deptAirport": "", "arrAirport": "",
                            "deptCdTxt": IATA_CODE[search_info.from_airport]['cn_city'],
                            "arrCdTxt": IATA_CODE[search_info.to_airport]['cn_city'],
                            "deptCityCode": search_info.from_airport,
                            "arrCityCode": search_info.to_airport}]}
        data = {
            '_': Time.timestamp_ms(),  # 随机字串
            'searchCond': json.dumps(search_cond, ensure_ascii=False),
        }
        url = 'http://www.ceair.com/otabooking/flight-search!doFlightSearch.shtml'
        Logger().debug('search request %s' % data)
        http_conn = http_session.request(method='POST', url=url, data=data)
        result = http_conn.to_json()
        # 转换为标准格式

        fscKey = result.get('fscKey')
        snk = None
        airPriceUnitIndex = None
        product_list = result.get('searchProduct')
        if not product_list:
            Logger().error('================= flight search web no flight ==============')
            Logger().error(result)
            raise FlightSearchException('ceair search web no flight')
        order_snk = None
        for product in product_list:
            order_snk = RoutingKey.unserialize(search_info.routing.routing_key_detail)
            web_snk = product.get('snk')
            from_airport = order_snk['from_airport']
            from_airport = self.iata_code_mapping_reverse(from_airport)
            to_airport = order_snk['to_airport']
            to_airport = self.iata_code_mapping_reverse(to_airport)
            dep_ts = int(time.mktime(datetime.datetime.strptime(order_snk['dep_time'],'%Y%m%d%H%M').timetuple())*1000)
            arr_ts = int(time.mktime(datetime.datetime.strptime(order_snk['arr_time'],'%Y%m%d%H%M').timetuple())*1000)
            order_snk = '{}{}{}{}{}{}{}'.format(from_airport,dep_ts,to_airport,arr_ts,order_snk['flight_number'],order_snk['product'],order_snk['cabin'])

            Logger().debug("========================= ceair product order snk:{}   web_snk:{} ===============".format(
                order_snk, web_snk))

            if order_snk in web_snk:
                snk = product.get('snk')
                airPriceUnitIndex = product.get('index')
                break

        Logger().debug("================== order snk: {} ========".format(order_snk))

        return fscKey, snk, airPriceUnitIndex


        # search_info.provider_search_raw_code = result['resultCode']
        # if result['resultCode'] == '':
        #     # 存在航班
        #     pass
        # elif result['resultCode'] in ['SYS11207', 'OTR20000', 'RSD10004','SYS11002']:
        #     # 访问频繁
        #     # http_session.log_block_ip()
        #     raise FlightSearchException(err_code='HIGH_REQ_LIMIT')
        # elif result['resultCode'] == 'SYS11013':
        #     # 请求参数错误
        #     raise FlightSearchCritical(err_code='REQPARAM_ERROR')
        # elif result['resultCode'] in ['OTR11002', 'OTR11010', 'OTR11004', 'OTR20001','SYS11025']:
        #     # 明确无航班
        #     pass
        #     # raise FlightSearchCritical(err_code='NOFLIGHT')
        # else:
        #     # 未知错误
        #     raise FlightSearchException(err_code='ERROR')
        #
        # if result.get('airResultDto', None):
        #     # 代表搜索到航班
        #
        #     search_info.extra_data_2 = result['sessionId']
        #     search_info.extra_data_3 = result['airResultDto']['fscKey']
        #
        #     product_units = result['airResultDto']['productUnits']
        #     for units in product_units:
        #         # if units['productInfo']['type'] == "4":  # 是否为会员产品
        #         if units['productInfo']['productCode'] not in  ['Y_E','BJK'] :  # Y_E 代表青老年特惠，目前暂时不收录此产品，因为有年龄限制 BJK 目前无法申请，只能是白金卡会员申请 禁售提示：该舱位目前暂未开放兑换，仅支持白金卡会员进行申请。请尝试预订其他航班
        #             valid_rouing = True # 航班是否有效
        #             flight_routing = FlightRoutingInfo()
        #             flight_routing.product_type = units['productInfo']['productCode']
        #             # flight_routing.routing_key = md5_hash(units['snk'])  # 此处需要进行hash
        #             flight_routing.air_price_unit_index = units['index']  # 东航特有，在订票时候需要用
        #             flight_routing.snk = units['snk']  # 东航特有，在订票时候需要用
        #             # 成人价格+税
        #             adt_fare_info = [x for x in units['fareInfoView'] if x['paxType'] == 'ADT'][0]
        #             flight_routing.adult_price = float(adt_fare_info['fare']['salePrice'])
        #             if adt_fare_info['fare']['discount']:
        #                 flight_routing.adult_price_discount = adt_fare_info['fare']['discount']
        #             try:
        #                 # 此处加上异常处理是因为有些价格显示的是一个区间  类似  1070-800
        #                 if adt_fare_info['fare']['baseClassFullPrice']:
        #                     # 国际票可能没有全价显示
        #                     flight_routing.adult_price_full_price = float(adt_fare_info['fare']['baseClassFullPrice'])
        #             except Exception as e:
        #                 Logger().sdebug(e)
        #             if search_info.routing_range == 'IN':
        #                 flight_routing.adult_tax = 80
        #             else:
        #                 if adt_fare_info['fare']['referenceTax']:
        #                     flight_routing.adult_tax = float(adt_fare_info['fare']['referenceTax'])
        #                 else:
        #                     # 有些舱位没有税费显示，所以不进行预订。
        #                     continue
        #
        #             # 儿童价格+税
        #             if [x for x in units['fareInfoView'] if x['paxType'] == 'CHD']:
        #                 chd_fare_info = [x for x in units['fareInfoView'] if x['paxType'] == 'CHD'][0]
        #                 flight_routing.child_price = float(chd_fare_info['fare']['salePrice'])
        #                 if search_info.routing_range == 'IN':
        #                     flight_routing.child_tax = 0
        #                 else:
        #                     if chd_fare_info['fare']['referenceTax']:
        #                         flight_routing.child_tax = float(chd_fare_info['fare']['referenceTax'])
        #                     else:
        #                         continue
        #
        #             # 将routing_key 格式化，并将价格相加
        #             a = list(units['snk'])
        #             for x in range(len(a) - 1, 0, -1):
        #                 if a[x].isalpha():
        #                     a.insert(x + 1, '|')
        #                     break
        #
        #             snk, price_str = ''.join(a).split('|')
        #             price_str = '%s|%s||%s|%s||%s|%s' % (flight_routing.adult_price, flight_routing.adult_tax, flight_routing.child_price, flight_routing.child_tax, '0.0', '0.0')  # 婴儿价格暂定为0
        #             flight_routing.routing_key_detail = '%s|||%s' % (snk, price_str)
        #             flight_routing.routing_key = simple_encrypt(flight_routing.routing_key_detail)  # 必须进行加密存储
        #             routing_number = 1
        #             for segment in units['oriDestOption'][0]['flights']:
        #
        #                 if segment.get('specialSegType','') == 'TRN':
        #                     # 空铁联运航线，暂时过滤掉
        #                     valid_rouing = False
        #                     # Logger().debug('specialSegType TRN')
        #                 flight_segment = FlightSegmentInfo()
        #                 flight_segment.carrier = segment['marketingAirline']['code']
        #                 flight_segment.dep_airport = segment['departureAirport']['code']
        #                 flight_segment.dep_time = datetime.datetime.strptime(segment['departureDateTime'], '%Y-%m-%d %H:%M').strftime('%Y-%m-%d %H:%M:%S')
        #                 flight_segment.arr_airport = segment['arrivalAirport']['code']
        #                 flight_segment.arr_time = datetime.datetime.strptime(segment['arrivalDateTime'], '%Y-%m-%d %H:%M').strftime('%Y-%m-%d %H:%M:%S')
        #                 sc_code_list = []
        #                 sa_code_list = []
        #                 for sl in segment['stopLocation']:
        #                     sa_code_list.append(sl['code'])
        #                     sc_code_list.append(sl['cityCode'])
        #
        #                 flight_segment.stop_cities = "/".join(sc_code_list)
        #                 flight_segment.stop_airports = "/".join(sa_code_list)
        #                 flight_segment.cabin = segment['bookingClassAvail']['cabinCode']
        #                 if segment['bookingClassAvail']['cabinStatusCode'] in ['A','L']:
        #                     cabin_count = 9
        #                 elif 1 <= int(segment['bookingClassAvail']['cabinStatusCode']) <= 9:
        #                     cabin_count = int(segment['bookingClassAvail']['cabinStatusCode'])
        #                 flight_segment.cabin_count = cabin_count
        #                 flight_segment.flight_number = segment['flightNumber']
        #                 if segment['departureAirport']['terminal'] == '--' or not segment['departureAirport']['terminal']:
        #                     dep_terminal = ''
        #                 else:
        #                     dep_terminal = segment['departureAirport']['terminal']
        #                 flight_segment.dep_terminal = dep_terminal
        #                 if segment['arrivalAirport']['terminal'] == '--' or not segment['arrivalAirport']['terminal']:
        #                     arr_terminal = ''
        #                 else:
        #                     arr_terminal = segment['arrivalAirport']['terminal']
        #                 flight_segment.arr_terminal = arr_terminal
        #
        #                 # TODO:不确定 more 是否就是经济舱
        #                 ceair_cabin_grade = units['cabinInfo']['baseCabinCode']
        #                 ceair_cabin_map = {
        #                     'economy%economy':'Y',
        #                     'economy': 'Y',
        #                     'business': 'C',
        #                     'business%luxury':'C',
        #                     'first': 'F',
        #                     'lowest': 'Y',
        #                     'luxury': 'F',
        #                     'more': 'Y'
        #                 }
        #                 flight_segment.cabin_grade = ceair_cabin_map.get(ceair_cabin_grade,'F')
        #                 ceair_duration = segment['duration']
        #                 hour, minute = ceair_duration.split(':')
        #                 duration = int(hour) * 60 + int(minute)
        #                 flight_segment.duration = duration
        #                 flight_segment.routing_number = routing_number
        #                 routing_number += 1
        #                 flight_routing.from_segments.append(flight_segment)
        #             if valid_rouing:
        #                 search_info.assoc_search_routings.append(flight_routing)
        # else:
        #     Logger().warn('ceair no flight %s' % json.dumps(result, ensure_ascii=False))
        # return search_info

    def _pre_register(self, http_session, search_info):
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

        gevent.sleep(0.2)
        Logger().debug('search flight')

        # search_cond = {"adtCount":search_info.adt_count ,
        #                "chdCount": search_info.chd_count ,
        #                "infCount": search_info.inf_count ,
        if search_info.adt_count == 0 or search_info.adt_count is None:
            adt_count = 1
        else:
            adt_count = search_info.adt_count

        # 因为东航查询必须输入机场名字，在这里对部分机场名字进行mapping


        search_cond = {"adtCount": adt_count,
                       "chdCount": search_info.chd_count,
                       "infCount": search_info.inf_count,
                       # "version":"A.1.0",  # 东航搜索改版
                       "currency": "CNY",
                       "tripType": search_info.trip_type,
                       "recommend": False,
                       "reselect": "",
                       "page": "0",
                       "sortType": "a",
                       "sortExec": "a",
                       "segmentList": [
                           {"deptCd": self.iata_code_mapping(search_info.from_airport), "arrCd": self.iata_code_mapping(search_info.to_airport),
                            "deptDt": search_info.from_date,
                            "deptAirport": "", "arrAirport": "",
                            "deptCdTxt": IATA_CODE[search_info.from_airport]['cn_city'],
                            "arrCdTxt": IATA_CODE[search_info.to_airport]['cn_city'],
                            "deptCityCode": search_info.from_airport,
                            "arrCityCode": search_info.to_airport}]}
        data = {
            '_': Time.timestamp_ms(),  # 随机字串
            'searchCond': json.dumps(search_cond, ensure_ascii=False),
        }
        url = 'http://www.ceair.com/otabooking/flight-search!doFlightSearch.shtml'
        Logger().debug('search request %s' % data)
        http_conn = http_session.request(method='POST', url=url, data=data)
        result = http_conn.to_json()
        # Logger().debug('result xxxxxxxxxxxxxx %s' % json.dumps(result))
        # 转换为标准格式

        fscKey = result.get('fscKey')
        snk = None
        airPriceUnitIndex = None
        product_list = result.get('searchProduct')
        for product in product_list:
            if product.get('productCode') == 'HYJ_EC':
                snk = product.get('snk')
                airPriceUnitIndex = product.get('index')
                break

        return fscKey, snk, airPriceUnitIndex


        # search_info.provider_search_raw_code = result['resultCode']
        # if result['resultCode'] == '':
        #     # 存在航班
        #     pass
        # elif result['resultCode'] in ['SYS11207', 'OTR20000', 'RSD10004','SYS11002']:
        #     # 访问频繁
        #     # http_session.log_block_ip()
        #     raise FlightSearchException(err_code='HIGH_REQ_LIMIT')
        # elif result['resultCode'] == 'SYS11013':
        #     # 请求参数错误
        #     raise FlightSearchCritical(err_code='REQPARAM_ERROR')
        # elif result['resultCode'] in ['OTR11002', 'OTR11010', 'OTR11004', 'OTR20001','SYS11025']:
        #     # 明确无航班
        #     pass
        #     # raise FlightSearchCritical(err_code='NOFLIGHT')
        # else:
        #     # 未知错误
        #     raise FlightSearchException(err_code='ERROR')
        #
        # if result.get('airResultDto', None):
        #     # 代表搜索到航班
        #
        #     search_info.extra_data_2 = result['sessionId']
        #     search_info.extra_data_3 = result['airResultDto']['fscKey']
        #
        #     product_units = result['airResultDto']['productUnits']
        #     for units in product_units:
        #         # if units['productInfo']['type'] == "4":  # 是否为会员产品
        #         if units['productInfo']['productCode'] not in  ['Y_E','BJK'] :  # Y_E 代表青老年特惠，目前暂时不收录此产品，因为有年龄限制 BJK 目前无法申请，只能是白金卡会员申请 禁售提示：该舱位目前暂未开放兑换，仅支持白金卡会员进行申请。请尝试预订其他航班
        #             valid_rouing = True # 航班是否有效
        #             flight_routing = FlightRoutingInfo()
        #             flight_routing.product_type = units['productInfo']['productCode']
        #             # flight_routing.routing_key = md5_hash(units['snk'])  # 此处需要进行hash
        #             flight_routing.air_price_unit_index = units['index']  # 东航特有，在订票时候需要用
        #             flight_routing.snk = units['snk']  # 东航特有，在订票时候需要用
        #             # 成人价格+税
        #             adt_fare_info = [x for x in units['fareInfoView'] if x['paxType'] == 'ADT'][0]
        #             flight_routing.adult_price = float(adt_fare_info['fare']['salePrice'])
        #             if adt_fare_info['fare']['discount']:
        #                 flight_routing.adult_price_discount = adt_fare_info['fare']['discount']
        #             try:
        #                 # 此处加上异常处理是因为有些价格显示的是一个区间  类似  1070-800
        #                 if adt_fare_info['fare']['baseClassFullPrice']:
        #                     # 国际票可能没有全价显示
        #                     flight_routing.adult_price_full_price = float(adt_fare_info['fare']['baseClassFullPrice'])
        #             except Exception as e:
        #                 Logger().sdebug(e)
        #             if search_info.routing_range == 'IN':
        #                 flight_routing.adult_tax = 80
        #             else:
        #                 if adt_fare_info['fare']['referenceTax']:
        #                     flight_routing.adult_tax = float(adt_fare_info['fare']['referenceTax'])
        #                 else:
        #                     # 有些舱位没有税费显示，所以不进行预订。
        #                     continue
        #
        #             # 儿童价格+税
        #             if [x for x in units['fareInfoView'] if x['paxType'] == 'CHD']:
        #                 chd_fare_info = [x for x in units['fareInfoView'] if x['paxType'] == 'CHD'][0]
        #                 flight_routing.child_price = float(chd_fare_info['fare']['salePrice'])
        #                 if search_info.routing_range == 'IN':
        #                     flight_routing.child_tax = 0
        #                 else:
        #                     if chd_fare_info['fare']['referenceTax']:
        #                         flight_routing.child_tax = float(chd_fare_info['fare']['referenceTax'])
        #                     else:
        #                         continue
        #
        #             # 将routing_key 格式化，并将价格相加
        #             a = list(units['snk'])
        #             for x in range(len(a) - 1, 0, -1):
        #                 if a[x].isalpha():
        #                     a.insert(x + 1, '|')
        #                     break
        #
        #             snk, price_str = ''.join(a).split('|')
        #             price_str = '%s|%s||%s|%s||%s|%s' % (flight_routing.adult_price, flight_routing.adult_tax, flight_routing.child_price, flight_routing.child_tax, '0.0', '0.0')  # 婴儿价格暂定为0
        #             flight_routing.routing_key_detail = '%s|||%s' % (snk, price_str)
        #             flight_routing.routing_key = simple_encrypt(flight_routing.routing_key_detail)  # 必须进行加密存储
        #             routing_number = 1
        #             for segment in units['oriDestOption'][0]['flights']:
        #
        #                 if segment.get('specialSegType','') == 'TRN':
        #                     # 空铁联运航线，暂时过滤掉
        #                     valid_rouing = False
        #                     # Logger().debug('specialSegType TRN')
        #                 flight_segment = FlightSegmentInfo()
        #                 flight_segment.carrier = segment['marketingAirline']['code']
        #                 flight_segment.dep_airport = segment['departureAirport']['code']
        #                 flight_segment.dep_time = datetime.datetime.strptime(segment['departureDateTime'], '%Y-%m-%d %H:%M').strftime('%Y-%m-%d %H:%M:%S')
        #                 flight_segment.arr_airport = segment['arrivalAirport']['code']
        #                 flight_segment.arr_time = datetime.datetime.strptime(segment['arrivalDateTime'], '%Y-%m-%d %H:%M').strftime('%Y-%m-%d %H:%M:%S')
        #                 sc_code_list = []
        #                 sa_code_list = []
        #                 for sl in segment['stopLocation']:
        #                     sa_code_list.append(sl['code'])
        #                     sc_code_list.append(sl['cityCode'])
        #
        #                 flight_segment.stop_cities = "/".join(sc_code_list)
        #                 flight_segment.stop_airports = "/".join(sa_code_list)
        #                 flight_segment.cabin = segment['bookingClassAvail']['cabinCode']
        #                 if segment['bookingClassAvail']['cabinStatusCode'] in ['A','L']:
        #                     cabin_count = 9
        #                 elif 1 <= int(segment['bookingClassAvail']['cabinStatusCode']) <= 9:
        #                     cabin_count = int(segment['bookingClassAvail']['cabinStatusCode'])
        #                 flight_segment.cabin_count = cabin_count
        #                 flight_segment.flight_number = segment['flightNumber']
        #                 if segment['departureAirport']['terminal'] == '--' or not segment['departureAirport']['terminal']:
        #                     dep_terminal = ''
        #                 else:
        #                     dep_terminal = segment['departureAirport']['terminal']
        #                 flight_segment.dep_terminal = dep_terminal
        #                 if segment['arrivalAirport']['terminal'] == '--' or not segment['arrivalAirport']['terminal']:
        #                     arr_terminal = ''
        #                 else:
        #                     arr_terminal = segment['arrivalAirport']['terminal']
        #                 flight_segment.arr_terminal = arr_terminal
        #
        #                 # TODO:不确定 more 是否就是经济舱
        #                 ceair_cabin_grade = units['cabinInfo']['baseCabinCode']
        #                 ceair_cabin_map = {
        #                     'economy%economy':'Y',
        #                     'economy': 'Y',
        #                     'business': 'C',
        #                     'business%luxury':'C',
        #                     'first': 'F',
        #                     'lowest': 'Y',
        #                     'luxury': 'F',
        #                     'more': 'Y'
        #                 }
        #                 flight_segment.cabin_grade = ceair_cabin_map.get(ceair_cabin_grade,'F')
        #                 ceair_duration = segment['duration']
        #                 hour, minute = ceair_duration.split(':')
        #                 duration = int(hour) * 60 + int(minute)
        #                 flight_segment.duration = duration
        #                 flight_segment.routing_number = routing_number
        #                 routing_number += 1
        #                 flight_routing.from_segments.append(flight_segment)
        #             if valid_rouing:
        #                 search_info.assoc_search_routings.append(flight_routing)
        # else:
        #     Logger().warn('ceair no flight %s' % json.dumps(result, ensure_ascii=False))
        # return search_info

#     def _flight_search(self, http_session, search_info):
#
#         """
#                 航班爬取模块，
#                 TODO :目前只考虑单程
#                 :return:
#                 """
#
#         # 搜索上海到深圳 2018-11-02 1个成人
#         """
#         没有航班
#
# {"adtNum":"0","airResultDto":null,"blockPrice":0,"cabinNames":{"business":null,"economy":null,"first":null,"lowest":null,"luxury":null,"more":null},"chdNum":"0","currency":"CNY","fareType":null,"infNum":"0","intervalTime":"180","itemType":"2","pageNumber":"0","pageSize":"0","resultCode":"OTR11002","resultMsg":"æ¨éæ©çèªçº¿æ²¡æèªç­è®¡åï¼è¯·åèä»·æ ¼æ¥åï¼éæ°éæ©åºåæ¥æ OTR11002","resultType":"05","sessionId":"","shopLandFlightResultNum":"0","taxCurrency":"CNY","timeStamp":null,"travelType":null,"uuid":""}
#         """
#         gevent.sleep(0.1)
#         Logger().debug('search flight')
#
#         # search_cond = {"adtCount":search_info.adt_count ,
#         #                "chdCount": search_info.chd_count ,
#         #                "infCount": search_info.inf_count ,
#         if search_info.adt_count == 0 or search_info.adt_count is None:
#             adt_count = 1
#         else:
#             adt_count = search_info.adt_count
#
#         # 因为东航查询必须输入机场名字，在这里对部分机场名字进行mapping
#
#         query_str = '?tripTypeFlag=0&tripType={}&deptCode={}&arrvCode={}&deptDate={}&backDate=&payType=RMB&goCodeType=1&backCodeType=1&channel=M'.format(
#             search_info.trip_type, self.iata_code_mapping_reverse(search_info.from_airport),
#             self.iata_code_mapping_reverse(search_info.to_airport), search_info.from_date
#         )
#         url = 'https://m.ceair.com/mobile/book/flight-search!flight.shtml{}'.format(query_str)
#         http_conn = http_session.request(method='GET', url=url, verify=False)
#         result = http_conn.to_json()
#
#         # 转换为标准格式
#         """
#
# {"sessionId":"","uuid":"","adtNum":"0","chdNum":"0","infNum":"0","timeStamp":null,"pageSize":"0","shopLandFlightResultNum":"0","pageNumber":"0","travelType":null,"fareType":null,"resultType":"09","resultCode":"SYS11207","resultMsg":"请访问不要太频繁 SYS11207","airResultDto":null,"blockPrice":0,"itemType":"2","intervalTime":"180","taxCurrency":"CNY","currency":"CNY","searchType":"","cabinNames":{"first":null,"business":null,"economy":null,"lowest":null,"more":null,"luxury":null}}
#         """
#
#         search_info.provider_search_raw_code = result.get('resultCode')
#         if result['resultCode'] == '0':
#             # 存在航班
#             pass
#         elif result['resultCode'] == '4':
#             # 访问频繁
#             # http_session.log_block_ip()
#             raise FlightSearchException(err_code='HIGH_REQ_LIMIT')
#         elif result['resultCode'] == '3':
#             # 请求参数错误
#             raise FlightSearchCritical(err_code='REQPARAM_ERROR')
#         elif result['resultCode'] == '1' and result['error'] == '很抱歉，暂无通航该城市的航班。':
#             # 明确无航班
#             pass
#             # raise FlightSearchCritical(err_code='NOFLIGHT')
#         elif result['resultCode'] == '1' and result['error'] == '对应IP超过同时查询次数！':
#             raise FlightSearchException(err_code='HIGH_REQ_LIMIT')
#         else:
#             # 未知错误
#             raise FlightSearchException(err_code='ERROR')
#
#         if result.get('flightInfo', None):
#             # 代表搜索到航班
#             product_units = []
#             for route in result['flightInfo']:
#                 segment_list = route['frontFlightInfos']
#                 if not segment_list:
#                     continue
#                 for cabin in segment_list[0]['frontCabinInfos']:
#                     product_units.append({
#                         'segment_info': segment_list,
#                         'cabin_info': cabin
#                     })
#
#             for units in product_units:
#                 # if units['productInfo']['type'] == "4":  # 是否为会员产品
#                 if units['cabin_info']['productInfo']['productCode'] not in ['Y_E',
#                                                                'BJK']:  # Y_E 代表青老年特惠，目前暂时不收录此产品，因为有年龄限制 BJK 目前无法申请，只能是白金卡会员申请 禁售提示：该舱位目前暂未开放兑换，仅支持白金卡会员进行申请。请尝试预订其他航班
#                     valid_rouing = True  # 航班是否有效
#                     flight_routing = FlightRoutingInfo()
#                     flight_routing.product_type = units['cabin_info']['productInfo']['productCode']
#                     flight_routing.air_price_unit_index = units['cabin_info']['index']  # 东航特有，在订票时候需要用
#                     # 成人价格+税
#                     adt_fare_info = [x for x in units['cabin_info']['frontFareInfos'] if x['paxType'] == 'ADT'][0]
#                     if '-' in adt_fare_info['fare']['salePrice']:
#                         adult_price = 0.0
#                         adult_price_list = adt_fare_info['fare']['salePrice'].split('-')
#                         for p in adult_price_list:
#                             adult_price += float(p)
#                     else:
#                          adult_price = float(adt_fare_info['fare']['salePrice'])
#                     flight_routing.adult_price = adult_price
#                     flight_routing.adult_tax = 0.0
#                     flight_routing.child_price = 0.0
#                     flight_routing.child_tax = 0.0
#                     flight_routing.inf_price = 0.0
#                     flight_routing.inf_tax = 0.0
#                     if units['cabin_info']['productInfo']['discount']:
#                         flight_routing.adult_price_discount = units['cabin_info']['productInfo']['discount']
#                     try:
#                         # 此处加上异常处理是因为有些价格显示的是一个区间  类似  1070-800
#                         if adt_fare_info['fare']['baseClassFullPrice']:
#                             # 国际票可能没有全价显示
#                             if '-' in adt_fare_info['fare']['baseClassFullPrice']:
#                                 base_full_price = 0.0
#                                 base_full_price_list = adt_fare_info['fare']['baseClassFullPrice'].split('-')
#                                 for p in base_full_price_list:
#                                     base_full_price += float(p)
#                             else:
#                                 base_full_price = float(adt_fare_info['fare']['baseClassFullPrice'])
#                             flight_routing.adult_price_full_price = base_full_price
#                     except Exception as e:
#                         Logger().sdebug(e)
#                     if search_info.routing_range == 'I2I':
#                         flight_routing.adult_tax = DomesticTaxAux.query(from_airport=search_info.from_airport,to_airport=search_info.to_airport,age_type='ADT') * len(units['segment_info'])
#                     else:
#                         if adt_fare_info['fare']['referenceTax']:
#                             if '-' in adt_fare_info['fare']['referenceTax']:
#                                 refer_tax = 0.0
#                                 refer_tax_list = adt_fare_info['fare']['referenceTax'].split('-')
#                                 for p in refer_tax_list:
#                                     refer_tax += float(p)
#                             else:
#                                 refer_tax = float(adt_fare_info['fare']['referenceTax'])
#                             flight_routing.adult_tax = refer_tax
#                         else:
#                             # 有些舱位没有税费显示，所以不进行预订。
#                             continue
#
#                     # 儿童价格+税
#                     if [x for x in units['cabin_info']['frontFareInfos'] if x['paxType'] == 'CHD']:
#                         chd_fare_info = [x for x in units['cabin_info']['frontFareInfos'] if x['paxType'] == 'CHD'][0]
#                         if '-' in chd_fare_info['fare']['salePrice']:
#                             child_price = 0.0
#                             child_price_list = chd_fare_info['fare']['salePrice'].split('-')
#                             for p in child_price_list:
#                                 child_price += float(p)
#                         else:
#                             child_price = float(chd_fare_info['fare']['salePrice'])
#                         flight_routing.child_price = child_price
#                         if search_info.routing_range == 'I2I':
#                             flight_routing.child_tax = DomesticTaxAux.query(from_airport=search_info.from_airport,to_airport=search_info.to_airport,age_type='CHD') * len(units['segment_info'])
#                         else:
#                             if chd_fare_info['fare']['referenceTax']:
#                                 if '-' in chd_fare_info['fare']['referenceTax']:
#                                     child_tax = 0.0
#                                     child_tax_list = chd_fare_info['fare']['referenceTax'].split('-')
#                                     for p in child_tax_list:
#                                         child_tax += float(p)
#                                 else:
#                                     child_tax = float(chd_fare_info['fare']['referenceTax'])
#                                 flight_routing.child_tax = child_tax
#                             else:
#                                 continue
#                     # 婴儿价格+税
#                     if [x for x in units['cabin_info']['frontFareInfos'] if x['paxType'] == 'INF']:
#                         inf_fare_info = [x for x in units['cabin_info']['frontFareInfos'] if x['paxType'] == 'INF'][0]
#                         if '-' in inf_fare_info['fare']['salePrice']:
#                             inf_price = 0.0
#                             inf_price_list = inf_fare_info['fare']['salePrice'].split('-')
#                             for p in inf_price_list:
#                                 inf_price += float(p)
#                         else:
#                             inf_price = float(inf_fare_info['fare']['salePrice'])
#                         flight_routing.inf_price = inf_price
#                         if search_info.routing_range == 'I2I':
#                             flight_routing.inf_price = 0
#                         else:
#                             if inf_fare_info['fare']['referenceTax']:
#                                 if '-' in inf_fare_info['fare']['referenceTax']:
#                                     inf_tax = 0.0
#                                     inf_tax_list = inf_fare_info['fare']['referenceTax'].split('-')
#                                     for p in inf_tax_list:
#                                         inf_tax += float(p)
#                                 else:
#                                     inf_tax = float(inf_fare_info['fare']['referenceTax'])
#                                 flight_routing.inf_tax = inf_tax
#                             else:
#                                 continue
#
#                     routing_number = 1
#                     cabin_valid = True
#                     is_include_operation_carrier = 0
#                     have_other_carrier = False
#                     for segment in units['segment_info']:
#
#                         if segment.get('specialSegType', '') == 'TRN':
#                             # 空铁联运航线，暂时过滤掉
#                             valid_rouing = False
#                             # Logger().debug('specialSegType TRN')
#                         if segment['isCodeShareAirline'] == True:
#                             is_include_operation_carrier = 1
#                         if segment['operatingAirline']['code'] not in ['MU', 'FM']:
#                             have_other_carrier = True
#                         flight_segment = FlightSegmentInfo()
#                         flight_segment.carrier = segment['marketingAirline']['code']
#                         flight_segment.dep_airport = segment['departureAirport']['code']
#                         flight_segment.dep_time = segment['departureDateTime']
#                         flight_segment.arr_airport = segment['arrivalAirport']['code']
#                         flight_segment.arr_time = segment['arrivalDateTime']
#                         sc_code_list = []
#                         sa_code_list = []
#                         for sl in segment['stopLocations']:
#                             sa_code_list.append(sl['code'])
#                             sc_code_list.append(sl['cityCode'])
#
#                         flight_segment.stop_cities = "/".join(sc_code_list)
#                         flight_segment.stop_airports = "/".join(sa_code_list)
#                         try:
#                             seg_cabin_code = units['cabin_info']['cabinCode'].split('-')[routing_number - 1]
#                             flight_segment.cabin = seg_cabin_code
#                         except:
#                             cabin_valid = False
#                             break
#                         if units['cabin_info']['cabinStatusCodeCount'] in string.letters:
#                             cabin_count = 9
#                         else:
#                             cabin_count = int(units['cabin_info']['cabinStatusCodeCount'])
#                         flight_segment.cabin_count = cabin_count
#                         flight_segment.flight_number = segment['flightNumber']
#                         if segment['departureAirport']['terminal'] == '--' or not segment['departureAirport'][
#                             'terminal']:
#                             dep_terminal = ''
#                         else:
#                             dep_terminal = segment['departureAirport']['terminal']
#                         flight_segment.dep_terminal = dep_terminal
#                         if segment['arrivalAirport']['terminal'] == '--' or not segment['arrivalAirport']['terminal']:
#                             arr_terminal = ''
#                         else:
#                             arr_terminal = segment['arrivalAirport']['terminal']
#                         flight_segment.arr_terminal = arr_terminal
#
#                         # TODO:不确定 more 是否就是经济舱
#                         ceair_cabin_grade = units['cabin_info']['cabinFlag']
#                         ceair_cabin_map = {
#                             'ECONOMY%ECONOMY': 'Y',
#                             'ECONOMY': 'Y',
#                             'BUSINESS': 'C',
#                             'BUSINESS%LUXURY': 'C',
#                             'FIRST': 'F',
#                             'LOWEST': 'Y',
#                             'LUXURY': 'F',
#                             'MORE': 'Y'
#                         }
#                         flight_segment.cabin_grade = ceair_cabin_map.get(ceair_cabin_grade, 'F')
#                         ceair_duration = (datetime.datetime.strptime(segment['arrivalDateTime'], '%Y-%m-%d %H:%M:%S') -
#                                           datetime.datetime.strptime(segment['departureDateTime'], '%Y-%m-%d %H:%M:%S')
#                                           ).total_seconds()
#                         duration = int(ceair_duration/60)
#                         flight_segment.duration = duration
#                         flight_segment.routing_number = routing_number
#                         routing_number += 1
#                         flight_routing.from_segments.append(flight_segment)
#
#                     flight_routing.is_include_operation_carrier = is_include_operation_carrier
#                     if not have_other_carrier:
#                         flight_routing.is_include_operation_carrier = 0
#
#                     rk_info = RoutingKey.serialize(from_airport=units['segment_info'][0]['departureAirport']['code'],
#                                                    dep_time=datetime.datetime.strptime(
#                                                        units['segment_info'][0]['departureDateTime'],
#                                                        '%Y-%m-%d %H:%M:%S'),
#                                                    to_airport=units['segment_info'][-1]['arrivalAirport']['code'],
#                                                    arr_time=datetime.datetime.strptime(
#                                                        units['segment_info'][-1]['arrivalDateTime'],
#                                                        '%Y-%m-%d %H:%M:%S'),
#                                                    flight_number='-'.join(
#                                                        [s['flightNumber'] for s in units['segment_info']]),
#                                                    cabin=units['cabin_info']['cabinCode'],
#                                                    cabin_grade='-'.join([s.cabin_grade for s in flight_routing.from_segments]),
#                                                    product=units['cabin_info']['productInfo']['productCode'],
#                                                    adult_price=flight_routing.adult_price,
#                                                    adult_tax=flight_routing.adult_tax,
#                                                    provider_channel=self.provider_channel,
#                                                    child_price=flight_routing.child_price,
#                                                    child_tax=flight_routing.child_tax,
#                                                    inf_price=flight_routing.inf_price, inf_tax=flight_routing.inf_tax,
#                                                    provider=self.provider,
#                                                    search_from_airport=search_info.from_airport,
#                                                    search_to_airport=search_info.to_airport,
#                                                    from_date=search_info.from_date,
#                                                    routing_range=search_info.routing_range,
#                                                    is_multi_segments=1 if len(units['segment_info']) > 1 else 0
#                                                    )  # 供应商渠道写死为 奥凯
#
#                     flight_routing.routing_key_detail = rk_info['plain']
#                     flight_routing.routing_key = rk_info['encrypted']
#
#                     if valid_rouing and cabin_valid:
#                         search_info.assoc_search_routings.append(flight_routing)
#         else:
#             Logger().debug('ceair no flight %s' % json.dumps(result, ensure_ascii=False))
#         return search_info

    def _flight_search(self, http_session, search_info):

        Logger().debug('search flight')

        if search_info.adt_count == 0 or search_info.adt_count is None:
            adt_count = 1
        else:
            adt_count = search_info.adt_count

        # 因为东航查询必须输入机场名字，在这里对部分机场名字进行mapping
        search_cond = {"adtCount": adt_count,
                       "chdCount": search_info.chd_count,
                       "infCount": search_info.inf_count,
                       # "version":"A.1.0",  # 东航搜索改版
                       "currency": "CNY",
                       "tripType": search_info.trip_type,
                       "recommend": False,
                       "reselect": "",
                       "page": "0",
                       "sortType": "a",
                       "sortExec": "a",
                       "segmentList": [
                           {"deptCd": self.iata_code_mapping(search_info.from_airport),
                            "arrCd": self.iata_code_mapping(search_info.to_airport),
                            "deptDt": search_info.from_date,
                            "deptAirport": "", "arrAirport": "",
                            "deptCdTxt": IATA_CODE[search_info.from_airport]['cn_city'],
                            "arrCdTxt": IATA_CODE[search_info.to_airport]['cn_city'],
                            "deptCityCode": search_info.from_airport,
                            "arrCityCode": search_info.to_airport}]}
        if search_info.trip_type == 'RT':
            search_cond['segmentList'].append({
                "deptCd": self.iata_code_mapping(search_info.to_airport),
                "arrCd": self.iata_code_mapping(search_info.from_airport),
                "deptDt": search_info.ret_date,
                "deptAirport": "", "arrAirport": "",
                "deptCdTxt": IATA_CODE[search_info.to_airport]['cn_city'],
                "arrCdTxt": IATA_CODE[search_info.from_airport]['cn_city'],
                "deptCityCode": search_info.to_airport,
                "arrCityCode": search_info.from_airport
            })
        data = {
            '_': Time.timestamp_ms(),  # 随机字串
            'searchCond': json.dumps(search_cond, ensure_ascii=False),
        }
        url = 'http://www.ceair.com/otabooking/flight-search!doFlightSearch.shtml'
        Logger().debug('search request %s' % data)
        http_conn = http_session.request(method='POST', url=url, data=data)
        if not http_conn.content:
            raise FlightSearchException(err_code='HIGH_REQ_LIMIT')

        result = http_conn.to_json()
        # Logger().debug('result xxxxxxxxxxxxxx %s' % json.dumps(result))
        # 转换为标准格式

        if result.get('resultCode'):
            raise FlightSearchException(err_code='HIGH_REQ_LIMIT')

        fscKey = result.get('fscKey')
        product_list = result.get('searchProduct')
        flight_list = result.get('flightInfo')
        if not product_list or not flight_list:
            Logger().debug('================= flight search web no flight ==============')
            return search_info
            # Logger().error(result)
            # raise FlightSearchException('ceair search web no flight')
        # flight_list = sorted(flight_list, key=lambda x: x['index'])

        flight_dict = {}
        for f in flight_list:
            flight_dict[f['index']] = f

        for product in product_list:
            flight_routing = FlightRoutingInfo()
            flight_routing.product_type = 'DEFAULT'
            routing_number = 1

            cabin_valid = True  # 舱位是否有效
            valid_rouing = True  # 航班是否有效
            is_include_operation_carrier = 0  # 是否是共享航班
            have_other_carrier = False

            flight_index_list = product['productGroupIndex'].split('/')
            cabin_list = product['cabin']['cabinCode'].split('/')
            cabin_count_list = product['cabin']['cabinStatus'].replace('A', '9').replace('S', '0').split('/')
            if (len(flight_index_list) < 2 or len(cabin_list) < 2 or len(cabin_count_list) < 2
                ) and search_info.trip_type == 'RT':
                continue

            from_seg_index_list = flight_index_list[0].split('-')
            ret_seg_index_list = flight_index_list[1].split('-') if search_info.trip_type == 'RT' else []
            from_cabin_list = cabin_list[0].split('-')
            ret_cabin_list = cabin_list[1].split('-') if search_info.trip_type == 'RT' else []
            from_cabin_count_list = cabin_count_list[0].split('-')
            ret_cabin_count_list = cabin_count_list[1].split('-') if search_info.trip_type == 'RT' else []

            for index, fs in enumerate(from_seg_index_list):
                seg_info = flight_dict[int(fs)]

                if seg_info.get('specialSegType', '') == 'TRN':
                    # 空铁联运航线，暂时过滤掉
                    valid_rouing = False
                if seg_info.get('isCodeShareAirline') == True:
                    is_include_operation_carrier = 1
                if seg_info['operatingAirline']['code'] not in ['MU', 'FM']:
                    have_other_carrier = True

                flight_segment = FlightSegmentInfo()
                flight_segment.carrier = seg_info['marketingAirline']['code']
                dep_time = '{}:00'.format(seg_info['departDateTime'])
                arr_time = '{}:00'.format(seg_info['arrivalDateTime'])
                flight_segment.dep_airport = seg_info['departAirport']['code']
                flight_segment.dep_time = dep_time
                flight_segment.arr_airport = seg_info['arrivalAirport']['code']
                flight_segment.arr_time = arr_time

                sc_code_list = []
                sa_code_list = []
                for sl in seg_info['stopLocation']:
                    sa_code_list.append(sl['code'])
                    sc_code_list.append(sl['cityCode'])
                flight_segment.stop_cities = "/".join(sc_code_list)
                flight_segment.stop_airports = "/".join(sa_code_list)
                flight_segment.flight_number = seg_info['flightNo']
                flight_segment.dep_terminal = seg_info['departAirport']['terminal'].strip().replace(
                    '--', '') if seg_info['departAirport'].get('terminal') else ''
                flight_segment.arr_terminal = seg_info['arrivalAirport']['terminal'].strip().replace(
                    '--', '') if seg_info['arrivalAirport'].get('terminal') else ''
                cabin_grade_mapping = {
                    'economy': 'Y',
                    'premiumEconomy': 'Y',
                    'business': 'C',
                    'first': 'F'
                }
                flight_segment.cabin = from_cabin_list[index]
                flight_segment.cabin_grade = cabin_grade_mapping.get(product['cabin']['baseCabinCode'], 'Y')
                try:
                    flight_segment.cabin_count = int(from_cabin_count_list[index])
                except:
                    flight_segment.cabin_count = 9
                segment_duration = (datetime.datetime.strptime(arr_time, '%Y-%m-%d %H:%M:%S') -
                                    datetime.datetime.strptime(dep_time, '%Y-%m-%d %H:%M:%S')).total_seconds()
                flight_segment.duration = int(segment_duration / 60)
                flight_segment.routing_number = routing_number
                routing_number += 1
                flight_routing.from_segments.append(flight_segment)

            for index, fs in enumerate(ret_seg_index_list):
                seg_info = flight_dict[int(fs)]

                if seg_info.get('specialSegType', '') == 'TRN':
                    # 空铁联运航线，暂时过滤掉
                    valid_rouing = False
                if seg_info.get('isCodeShareAirline') == True:
                    is_include_operation_carrier = 1
                if seg_info['operatingAirline']['code'] not in ['MU', 'FM']:
                    have_other_carrier = True

                flight_segment = FlightSegmentInfo()
                flight_segment.carrier = seg_info['marketingAirline']['code']
                dep_time = '{}:00'.format(seg_info['departDateTime'])
                arr_time = '{}:00'.format(seg_info['arrivalDateTime'])
                flight_segment.dep_airport = seg_info['departAirport']['code']
                flight_segment.dep_time = dep_time
                flight_segment.arr_airport = seg_info['arrivalAirport']['code']
                flight_segment.arr_time = arr_time

                sc_code_list = []
                sa_code_list = []
                for sl in seg_info['stopLocation']:
                    sa_code_list.append(sl['code'])
                    sc_code_list.append(sl['cityCode'])
                flight_segment.stop_cities = "/".join(sc_code_list)
                flight_segment.stop_airports = "/".join(sa_code_list)
                flight_segment.flight_number = seg_info['flightNo']
                flight_segment.dep_terminal = seg_info['departAirport']['terminal'].strip().replace(
                    '--', '') if seg_info['departAirport'].get('terminal') else ''
                flight_segment.arr_terminal = seg_info['arrivalAirport']['terminal'].strip().replace(
                    '--', '') if seg_info['arrivalAirport'].get('terminal') else ''
                cabin_grade_mapping = {
                    'economy': 'Y',
                    'premiumEconomy': 'Y',
                    'business': 'C',
                    'first': 'F'
                }
                flight_segment.cabin = ret_cabin_list[index]
                flight_segment.cabin_grade = cabin_grade_mapping.get(product['cabin']['baseCabinCode'], 'Y')
                try:
                    flight_segment.cabin_count = int(ret_cabin_count_list[index])
                except:
                    flight_segment.cabin_count = 9
                segment_duration = (datetime.datetime.strptime(arr_time, '%Y-%m-%d %H:%M:%S') -
                                    datetime.datetime.strptime(dep_time, '%Y-%m-%d %H:%M:%S')).total_seconds()
                flight_segment.duration = int(segment_duration / 60)
                flight_segment.routing_number = routing_number
                routing_number += 1
                flight_routing.ret_segments.append(flight_segment)

            flight_routing.is_include_operation_carrier = is_include_operation_carrier
            if not have_other_carrier:
                flight_routing.is_include_operation_carrier = 0

            # 补充舱位和舱等
            flight_routing.reference_cabin = flight_routing.from_segments[0].cabin
            flight_routing.reference_cabin_grade = flight_routing.from_segments[0].cabin_grade

            # TODO 国内税费
            flight_routing.adult_price = product['salePrice']
            flight_routing.child_price = product['salePrice']
            if search_info.routing_range == 'I2I':
                flight_routing.adult_tax = DomesticTaxAux.query(from_airport=search_info.from_airport,
                                                                to_airport=search_info.to_airport,age_type='ADT'
                                                                ) * (len(from_seg_index_list) + len(ret_seg_index_list))
                flight_routing.child_tax = DomesticTaxAux.query(from_airport=search_info.from_airport,
                                                                to_airport=search_info.to_airport,age_type='CHD'
                                                                ) * (len(from_seg_index_list) + len(ret_seg_index_list))
            flight_routing.adult_tax = float(product['referenceTax']) if product.get('referenceTax') else 0
            flight_routing.child_tax = float(product['referenceTax']) if product.get('referenceTax') else 0

            rk_dep_time = datetime.datetime.strptime(flight_routing.from_segments[0].dep_time,
                                                     '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M')
            rk_arr_time = datetime.datetime.strptime(flight_routing.from_segments[-1].arr_time,
                                                     '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M')
            rk_flight_number = '-'.join([s.flight_number for s in flight_routing.from_segments])
            rk_cabin = '-'.join([s.cabin for s in flight_routing.from_segments])
            rk_cabin_grade = '-'.join([s.cabin_grade for s in flight_routing.from_segments])

            if ret_seg_index_list:
                rk_dep_time = '{},{}'.format(rk_dep_time, datetime.datetime.strptime(
                    flight_routing.ret_segments[0].dep_time, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'))
                rk_arr_time = '{},{}'.format(rk_arr_time, datetime.datetime.strptime(
                    flight_routing.ret_segments[-1].arr_time, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'))
                rk_flight_number = '{},{}'.format(rk_flight_number, '-'.join(
                    [s.flight_number for s in flight_routing.ret_segments]))

                rk_cabin = '{},{}'.format(rk_cabin, '-'.join([s.cabin for s in flight_routing.ret_segments]))
                rk_cabin_grade = '{},{}'.format(rk_cabin_grade,
                                                '-'.join([s.cabin_grade for s in flight_routing.ret_segments]))

            rk_info = RoutingKey.serialize(from_airport=flight_routing.from_segments[0].dep_airport,
                                           dep_time=rk_dep_time,
                                           to_airport=flight_routing.from_segments[-1].arr_airport,
                                           arr_time=rk_arr_time,
                                           flight_number=rk_flight_number,
                                           cabin=rk_cabin,
                                           cabin_grade=rk_cabin_grade,
                                           product=product['productCode'],
                                           adult_price=flight_routing.adult_price,
                                           adult_tax=flight_routing.adult_tax,
                                           provider_channel=self.provider_channel,
                                           child_price=flight_routing.child_price,
                                           child_tax=flight_routing.child_tax,
                                           inf_price=flight_routing.child_price,
                                           inf_tax=flight_routing.child_tax,
                                           provider=self.provider,
                                           search_from_airport=search_info.from_airport,
                                           search_to_airport=search_info.to_airport,
                                           from_date=search_info.from_date,
                                           ret_date=search_info.ret_date,
                                           routing_range=search_info.routing_range,
                                           trip_type=search_info.trip_type,
                                           is_include_operation_carrier=flight_routing.is_include_operation_carrier,
                                           is_multi_segments=1 if len(flight_routing.from_segments) > 1 or flight_routing.ret_segments else 0
                                           )
            flight_routing.routing_key_detail = rk_info['plain']
            flight_routing.routing_key = rk_info['encrypted']

            flight_routing.snk = product['snk']
            flight_routing.product_index = product['index']
            flight_routing.fsc_key = fscKey

            if valid_rouing and cabin_valid:
                search_info.assoc_search_routings.append(flight_routing)

        return search_info

    # def _verify(self, http_session=None, search_info=None):
    #
    #     verify_account_username = '613022433644'
    #     verify_account_password = '19671007'
    #
    #     ffp_account = FFPAccountInfo()
    #     ffp_account.username = verify_account_username
    #     ffp_account.password = verify_account_password
    #
    #     http_session = self.login(http_session, ffp_account)
    #     Logger().debug("ceair verify after login")
    #     gevent.sleep(0.2)
    #     search_result = self.flight_search(http_session, search_info, cache_mode='REALTIME')
    #
    #     # 确认航班
    #     gevent.sleep(0.2)
    #     Logger().info('confirm flight ')
    #
    #     for routing in search_result.assoc_search_routings:
    #         # Logger().debug(routing)
    #         if RoutingKey.trans_cp_key(simple_decrypt(routing.routing_key)) == RoutingKey.trans_cp_key(
    #             simple_decrypt(search_info.verify_routing_key)):
    #             search_info.routing = routing
    #             break
    #     if not search_info.routing.fsc_key or not search_info.routing.snk:
    #         raise ProviderVerifyFail('ceair_session_id not found')
    #
    #     select_conds = {
    #         'fscKey': search_info.routing.fsc_key,
    #         'selcon': [{"airPriceUnitIndex": search_info.routing.product_index, "snk": search_info.routing.snk}]
    #     }
    #
    #     Logger().debug('select_conds %s ' % select_conds)
    #     data = {
    #         'selectConds': json.dumps(select_conds),
    #         # 'sessionId': ceair_session_id
    #     }
    #     url = 'http://www.ceair.com/otabooking/flight-confirm!flightConfirm.shtml'
    #     http_conn = http_session.request(method="POST", url=url, data=data, verify=False)
    #
    #     # 获取信息更新session
    #     gevent.sleep(0.2)
    #     Logger().info('paxinfo init')
    #     url = 'http://www.ceair.com/otabooking/paxinfo-input!init.shtml?_=%s&' % Time.timestamp_ms()
    #     http_conn = http_session.request(method='GET', url=url, verify=False)
    #     search_result = http_conn.to_json()
    #     Logger().debug(search_result)
    #     session_version = search_result.get('sessionVersion')
    #     if not session_version:
    #         raise ProviderVerifyFail('search_version fetch error')
    #
    #
    #     price_list = search_result['flightInfoDto']['prices']['paxPriceList']
    #     routing_list = search_result['flightInfoDto']['routingInfoList']
    #
    #     flight_routing = FlightRoutingInfo()
    #     flight_routing.product_type = 'DEFAULT'
    #     routing_number = 1
    #     from_seg_list = routing_list[0]['airSegInfoList']
    #     ret_seg_list = routing_list[1]['airSegInfoList'] if search_info.trip_type == 'RT' else []
    #
    #     is_include_operation_carrier = 0
    #     have_other_carrier = False
    #
    #     for seg_info in from_seg_list:
    #
    #         if seg_info.get('isShare') == 1:
    #             is_include_operation_carrier = 1
    #         if seg_info['operCarrier'] not in ['MU', 'FM']:
    #             have_other_carrier = True
    #
    #         flight_segment = FlightSegmentInfo()
    #         flight_segment.carrier = seg_info['marketCarrier']
    #         dep_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(seg_info['departDate']['time'] / 1000)))
    #         arr_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(seg_info['arriveDate']['time'] / 1000)))
    #         flight_segment.dep_airport = seg_info['departAirport']
    #         flight_segment.dep_time = dep_time
    #         flight_segment.arr_airport = seg_info['arriveAirport']
    #         flight_segment.arr_time = arr_time
    #
    #         sc_code_list = []
    #         sa_code_list = []
    #         for sl in seg_info['stopLocation']:
    #             sa_code_list.append(sl['code'])
    #             sc_code_list.append(sl['cityCode'])
    #         flight_segment.stop_cities = "/".join(sc_code_list)
    #         flight_segment.stop_airports = "/".join(sa_code_list)
    #         flight_segment.flight_number = seg_info['marketFltNo']
    #         flight_segment.dep_terminal = seg_info['departTerm'].strip().replace(
    #             '--', '') if seg_info.get('departTerm') else ''
    #         flight_segment.arr_terminal = seg_info['arriveTerm'].strip().replace(
    #             '--', '') if seg_info.get('arriveTerm') else ''
    #         cabin_grade_mapping = {
    #             'economy': 'Y',
    #             'premiumEconomy': 'Y',
    #             'business': 'C',
    #             'first': 'F'
    #         }
    #         flight_segment.cabin = seg_info['cabinCode']
    #         flight_segment.cabin_grade = cabin_grade_mapping.get(seg_info['cabinLevel'], 'Y')
    #         try:
    #             flight_segment.cabin_count = int(seg_info['seatNum'])
    #         except:
    #             flight_segment.cabin_count = 9
    #         segment_duration = (datetime.datetime.strptime(arr_time, '%Y-%m-%d %H:%M:%S') -
    #                             datetime.datetime.strptime(dep_time, '%Y-%m-%d %H:%M:%S')).total_seconds()
    #         flight_segment.duration = int(segment_duration / 60)
    #         flight_segment.routing_number = routing_number
    #         routing_number += 1
    #         flight_routing.from_segments.append(flight_segment)
    #
    #     for seg_info in ret_seg_list:
    #         if seg_info.get('isShare') == 1:
    #             is_include_operation_carrier = 1
    #         if seg_info['operCarrier'] not in ['MU', 'FM']:
    #             have_other_carrier = True
    #
    #         flight_segment = FlightSegmentInfo()
    #         flight_segment.carrier = seg_info['marketCarrier']
    #         dep_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(seg_info['departDate']['time'] / 1000)))
    #         arr_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(seg_info['arriveDate']['time'] / 1000)))
    #         flight_segment.dep_airport = seg_info['departAirport']
    #         flight_segment.dep_time = dep_time
    #         flight_segment.arr_airport = seg_info['arriveAirport']
    #         flight_segment.arr_time = arr_time
    #
    #         sc_code_list = []
    #         sa_code_list = []
    #         for sl in seg_info['stopLocation']:
    #             sa_code_list.append(sl['code'])
    #             sc_code_list.append(sl['cityCode'])
    #         flight_segment.stop_cities = "/".join(sc_code_list)
    #         flight_segment.stop_airports = "/".join(sa_code_list)
    #         flight_segment.flight_number = seg_info['marketFltNo']
    #         flight_segment.dep_terminal = seg_info['departTerm'].strip().replace(
    #             '--', '') if seg_info.get('departTerm') else ''
    #         flight_segment.arr_terminal = seg_info['arriveTerm'].strip().replace(
    #             '--', '') if seg_info.get('arriveTerm') else ''
    #         cabin_grade_mapping = {
    #             'economy': 'Y',
    #             'premiumEconomy': 'Y',
    #             'business': 'C',
    #             'first': 'F'
    #         }
    #         flight_segment.cabin = seg_info['cabinCode']
    #         flight_segment.cabin_grade = cabin_grade_mapping.get(seg_info['cabinLevel'], 'Y')
    #         try:
    #             flight_segment.cabin_count = int(seg_info['seatNum'])
    #         except:
    #             flight_segment.cabin_count = 9
    #         segment_duration = (datetime.datetime.strptime(arr_time, '%Y-%m-%d %H:%M:%S') -
    #                             datetime.datetime.strptime(dep_time, '%Y-%m-%d %H:%M:%S')).total_seconds()
    #         flight_segment.duration = int(segment_duration / 60)
    #         flight_segment.routing_number = routing_number
    #         routing_number += 1
    #         flight_routing.ret_segments.append(flight_segment)
    #
    #     flight_routing.is_include_operation_carrier = is_include_operation_carrier
    #     if not have_other_carrier:
    #         flight_routing.is_include_operation_carrier = 0
    #
    #     # 补充舱位和舱等
    #     flight_routing.reference_cabin = flight_routing.from_segments[0].cabin
    #     flight_routing.reference_cabin_grade = flight_routing.from_segments[0].cabin_grade
    #
    #     # TODO 国内税费
    #     flight_routing.adult_price = float(price_list[0]['tktprice']['price'])
    #     flight_routing.child_price = float(price_list[1]['tktprice']['price'])
    #     if search_info.routing_range == 'I2I':
    #         flight_routing.adult_tax = DomesticTaxAux.query(from_airport=search_info.from_airport,
    #                                                         to_airport=search_info.to_airport, age_type='ADT'
    #                                                         ) * (len(from_seg_list) + len(ret_seg_list))
    #         flight_routing.child_tax = DomesticTaxAux.query(from_airport=search_info.from_airport,
    #                                                         to_airport=search_info.to_airport, age_type='CHD'
    #                                                         ) * (len(from_seg_list) + len(ret_seg_list))
    #     flight_routing.adult_tax = float(price_list[0]['fee']['price']) + float(price_list[0]['tax']['price'])
    #     flight_routing.child_tax = float(price_list[1]['fee']['price']) + float(price_list[1]['tax']['price'])
    #
    #     rk_dep_time = datetime.datetime.strptime(flight_routing.from_segments[0].dep_time,
    #                                              '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M')
    #     rk_arr_time = datetime.datetime.strptime(flight_routing.from_segments[-1].arr_time,
    #                                              '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M')
    #     rk_flight_number = '-'.join([s.flight_number for s in flight_routing.from_segments])
    #     rk_cabin = '-'.join([s.cabin for s in flight_routing.from_segments])
    #     rk_cabin_grade = '-'.join([s.cabin_grade for s in flight_routing.from_segments])
    #
    #     if search_info.trip_type == 'RT':
    #         rk_dep_time = '{},{}'.format(rk_dep_time, datetime.datetime.strptime(
    #             flight_routing.ret_segments[0].dep_time, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'))
    #         rk_arr_time = '{},{}'.format(rk_arr_time, datetime.datetime.strptime(
    #             flight_routing.ret_segments[-1].arr_time, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M'))
    #         rk_flight_number = '{},{}'.format(rk_flight_number, '-'.join(
    #             [s.flight_number for s in flight_routing.ret_segments]))
    #
    #         rk_cabin = '{},{}'.format(rk_cabin, '-'.join([s.cabin for s in flight_routing.ret_segments]))
    #         rk_cabin_grade = '{},{}'.format(rk_cabin_grade,
    #                                         '-'.join([s.cabin_grade for s in flight_routing.ret_segments]))
    #
    #     rk_info = RoutingKey.serialize(from_airport=flight_routing.from_segments[0].dep_airport,
    #                                    dep_time=rk_dep_time,
    #                                    to_airport=flight_routing.from_segments[-1].arr_airport,
    #                                    arr_time=rk_arr_time,
    #                                    flight_number=rk_flight_number,
    #                                    cabin=rk_cabin,
    #                                    cabin_grade=rk_cabin_grade,
    #                                    product=routing_list[0]['productCodeList'][0],
    #                                    adult_price=flight_routing.adult_price,
    #                                    adult_tax=flight_routing.adult_tax,
    #                                    provider_channel=self.provider_channel,
    #                                    child_price=flight_routing.child_price,
    #                                    child_tax=flight_routing.child_tax,
    #                                    inf_price=flight_routing.child_price,
    #                                    inf_tax=flight_routing.child_tax,
    #                                    provider=self.provider,
    #                                    search_from_airport=search_info.from_airport,
    #                                    search_to_airport=search_info.to_airport,
    #                                    from_date=search_info.from_date,
    #                                    ret_date=search_info.ret_date,
    #                                    routing_range=search_info.routing_range,
    #                                    trip_type=search_info.trip_type,
    #                                    is_include_operation_carrier=is_include_operation_carrier,
    #                                    is_multi_segments=1 if len(
    #                                        flight_routing.from_segments) > 1 or flight_routing.ret_segments else 0
    #                                    )
    #     flight_routing.routing_key_detail = rk_info['plain']
    #     flight_routing.routing_key = rk_info['encrypted']
    #
    #     return flight_routing


    def _pay(self, order_info, http_session,pay_dict):
        """
        支付
        :param http_session:
        :return:
        支付宝
        <form accept-charset='UTF-8' name='paysubmit' id='paysubmit' method='post' action='https://mapi.alipay.com/gateway.
do?_input_charset=utf-8' autocomplete='off'><input type='hidden' name='_input_charset' value='utf-8'><input type='hidden'
name='body' value='春秋航空机票'><input type='hidden' name='extra_common_param' value='0^0^0^2018091234119974^SUGHMO^1^171570429'><
input type='hidden' name='it_b_pay' value='29m'><input type='hidden' name='notify_url' value='https://bpayment.ch.com/
AsyncResponse/Alipay'><input type='hidden' name='out_trade_no' value='2018091234119974'><input type='hidden' name='partner'
value='2088101909164661'><input type='hidden' name='payment_type' value='1'><input type='hidden' name='paymethod'
value='creditPay'><input type='hidden' name='return_url' value='https://bpayment.ch.com/SyncResponse/Alipay'><input
type='hidden' name='seller_id' value='2088101909164661'><input type='hidden' name='service' value='create_direct_pay_by_user'>
<input type='hidden' name='sign' value='01a6e0e9248b8ef1c56f270abd77b5a2'><input type='hidden' name='sign_type' value='MD5'>
<input type='hidden' name='subject' value='春秋航空机票'><input type='hidden' name='total_fee' value='350'></form><script
language="javascript">setTimeout("document.getElementById('paysubmit').submit();",1);</script>
        """
        provider_order_id = order_info.provider_order_id

        order_info.provider_order_status = 'LOGIN_FAIL'
        http_session = self.login(http_session=http_session, ffp_account_info=order_info.ffp_account)

        order_info.provider_order_status = 'PAY_FAIL'
        url = 'http://ecrm.ceair.com/traveller/optmember/order-query!queryOrderDetails.shtml'
        data = {
            'orderNo': order_info.provider_order_id,
            'orderType': 'AIR'
        }
        headers = {'Referer': 'http://ecrm.ceair.com/order/detail.html'}
        http_conn = http_session.request(method='POST', url=url, data=data, verify=False, headers=headers)
        encrypt_content = http_conn.content
        content_key = json.loads(http_conn.response_headers[0]).get('Content-Key')
        Logger().info("========== order detail content key:{}".format(content_key))
        des_key, des_iv = content_key.split(',')
        des_obj = DES.new(des_key, DES.MODE_CBC, des_iv)
        decrypt_content = des_obj.decrypt(base64.b64decode(encrypt_content))
        Logger().info("========== encrypt content:{}".format(encrypt_content))
        Logger().info("========== decrypt content:{}".format(decrypt_content))
        result = json.loads(re.findall(r'{.*}', decrypt_content)[0])
        err = result['errorResult']
        if err:
            raise PayException()
        else:
            order_status = result['orderInfoDto']['orderStatus']
            if order_status == '10050':
                if result['orderInfoDto']['operationInfoDtoList'][0]['name'] == '支付超时':
                    order_info.provider_order_status = 'TIMEOUT'
                    return False
                pay_url = result['orderInfoDto']['operationInfoDtoList'][0]['url']
                provider_price = [x for x in result['orderInfoDto']['payAmtList'] if x['currency'] == 'CNY'][0]['price']
                Logger().debug('provider_price %s' % provider_price)
                http_conn = http_session.request(method='GET', url=pay_url, verify=False)

                if 'payType=20072' in pay_url:
                    # visa白金支付通道
                    # Logger().debug('pay_url content%s'%http_conn.content)
                    """
                    bankname=UNI_CC004_HONGBAO&
                    card_no=&card_no=&month=01&year=2018&cvv_code=&owner_name=&id_type=0&id_no=&owner_mobile=&email=
                    &pay_password=&payBank.bankCode=UNI_CC004_HONGBAO&payBank.bankSubCode=SUB99Bill053&payBank.bankGate=BILL99PAY_BANK&payBank.promoId=
                    &payBank.couponNo=&payBank.cardBin=&payBank.effectMonth=&payBank.effectYear=&payBank.idType=&payBank.idNo=&payBank.cvvNo=&
                    payBank.ownerName=&payBank.ownerMobile=&payBank.payType=&payBank.email=&payBank.pointPass=&dynamicPointPay=20063&payInfo.payType=20072&
                    countDown=004238&accountId=&assignBank=&user_lastBank=&user_usedBank=&broker_ecard_bin=092032,092039&
                    ecard_bin=092011,092021,092016,092026,092018,092028,092019,092029,092035,092036,092037,092038&ecoupon_bin=092033&new_broker_bin=092057,092058&
                    score_bin=092075&score_kong_bin=092076&score_coupon_bin=092077&pay_page_noamount=[ESTORE_TP]&
                    payInfo.payAmount=1400.0&internal_flag=zh
                    """
                    pay_source_info = pay_dict['zl2385']
                    url = 'https://unipay.ceair.com/unipay/preparepay/pay!doPayFl.shtml'
                    data = {
                        'bankname': 'UNI_CC004_HONGBAO',
                        'card_no': '',
                        'month': '01',
                        'year': '2018',
                        'cvv_code': '',
                        'owner_name': '',
                        'id_type': '0',
                        'id_no': '',
                        'owner_mobile': '',
                        'email': '',
                        'pay_password': '',
                        'payBank.bankCode': 'UNI_CC004_HONGBAO',
                        'payBank.bankSubCode': 'SUB99Bill053',
                        'payBank.bankGate': 'BILL99PAY_BANK',
                        'payBank.promoId': '',
                        'payBank.couponNo': '',
                        'payBank.cardBin': '',
                        'payBank.effectMonth': '',
                        'payBank.effectYear': '',
                        'payBank.idType': '',
                        'payBank.idNo': '',
                        'payBank.cvvNo': '',
                        'payBank.ownerName': '',
                        'payBank.ownerMobile': '',
                        'payBank.payType': '',
                        'payBank.email': '',
                        'payBank.pointPass': '',
                        'dynamicPointPay': '20063',
                        'payInfo.payType': '20072',
                        'countDown': '004238',
                        'accountId': '',
                        'assignBank': '',
                        'user_lastBank': '',
                        'user_usedBank': '',
                        'broker_ecard_bin': '092032,092039',
                        'ecard_bin': '092011,092021,092016,092026,092018,092028,092019,092029,092035,092036,092037,092038',
                        'ecoupon_bin': '092033',
                        'new_broker_bin': '092057,092058',
                        'score_bin': '092075',
                        'score_kong_bin': '092076',
                        'score_coupon_bin': '092077',
                        'pay_page_noamount': '[ESTORE_TP]',
                        'payInfo.payAmount': '760.0',  # 价格要注意
                        'internal_flag': 'zh',
                        'credit_back_no': '信用卡背面签名条处的末三位数字。',
                        'credit_phone_no': '请在此处填写您在银行申请信用卡时留存的手机号码。',
                        'credit_regist_id_no': '请填写您申请信用卡时，提交给银行的相关证件号码，如身份证、护照、军官证等。',
                        'card_no_null': '卡号不能为空',
                        'card_length_err': '卡号为 15~19 位数字',
                        'verify_code_null': '验证码不能为空',
                        'verify_code_err': '验证码为3位数字',
                        'phone_no_err': '手机号码为11位数字',
                        'email_addr_err': '邮箱地址格式不正确',
                        'name_null': '真实姓名不能为空',
                        'name_err': '姓名为中文',
                        'id_no_null': '证件号码不能为空',
                        'id_no_err': '请输入正确的证件号码',
                        'password_length_notice': '请输入积分支付密码，密码不足8位请在原密码前加0补足8位',
                        'pay_as_total': '您好，您的订单不满足产品促销规则，是否按照原价支付？',
                        'choose_a_bank': '请您选择支付的银行。',
                        'order_expired': '您的订单已超过支付时限，无法继续支付，请重新预定。',
                        'timeout_notice': '已超时，无法支付',
                        'hour_set': '小时',
                        'minute_set': '分',
                        'second_set': '秒',
                        'credit_card_no_null': '请输入信用卡卡号！',
                        'credit_bin_support': '本产品仅支持以下卡BIN支付：',
                        'validate_fail': '校验卡号/帐户失败',
                        'unseccess_payment': '您好，该订单未支付成功，请重新支付！',
                        'unsure_payment': '您好，查询订单支付状态失败，请稍后再查！',
                        'announcement': '请确保您已阅读旅客须知全部内容，并同意购买。'

                    }
                    http_conn = http_session.request(method='POST', url=url, data=data, verify=False)
                    result = http_conn.content
                    soup = BeautifulSoup(result, 'lxml')
                    form = soup.find('form')
                    fields = form.findAll('input')
                    formdata = dict((field.get('name'), field.get('value')) for field in fields)
                    action_url = form['action']
                    Logger().debug('pay1redirect %s' % action_url)

                    # pay 2 跳转
                    gevent.sleep(0.2)
                    Logger().info('pay redirect 2')
                    url = action_url
                    data = formdata
                    http_conn = http_session.request(method='POST', url=url, data=data, verify=False)
                    result = http_conn.content
                    soup = BeautifulSoup(result, 'lxml')
                    form = soup.find('form')
                    fields = form.findAll('input')
                    formdata = dict((field.get('name'), field.get('value')) for field in fields)
                    action_url = form['action']
                    url = action_url
                    data = formdata

                    http_session = HttpRequest()
                    http_conn = http_session.request(method='POST', url=url, data=data, verify=False)
                    Logger().info('pay_source_info %s' % pay_source_info)

                    # 选择信用卡支付
                    gevent.sleep(0.2)
                    url = 'https://www.99bill.com/gateway/gateway.htm?method=selectPayType&payType=15'
                    http_conn = http_session.request(method='GET', url=url, verify=False)

                    # 选择中国银行支付
                    gevent.sleep(0.2)
                    url = 'https://www.99bill.com/gateway/creditCardQuickPayV3.htm?method=selectBank&bankId=CEB&selectPan='
                    data = {
                        'historySelPayWay': '#kuaijie',
                        'keyword': '',
                        'bankId': 'CEB',
                        '': ''
                    }
                    http_conn = http_session.request(method='POST', url=url, data=data, verify=False)

                    # # 加载中国银行页面
                    # gevent.sleep(0.2)
                    # url = 'https://www.99bill.com/seashell/html/website/quotaMsg/creditCard/quota_boc_18701.html'
                    # http_conn = http_session.request(method='GET', url=url, verify=False, print_info=True, comment='loading boc html').content

                    # 发送短信验证码
                    gevent.sleep(0.2)
                    Logger().info('send mobile code')

                    # 此处双quote 是因为99bill的请求也是这样的，并不是BUG
                    url = 'https://www.99bill.com/gateway/creditCardQuickPayV3.htm?method=postDynaCode&quickPay=N&bankId=CEB&quickPan={bank_card}&quickcvv2={cvv}&quickcardHoldName={name}&quickcardHolderId={pid}&quickphoneNo={mobile}&quickexpiredDate={expired_date}&quickHoldIdType=0&savePci=0&rad=&period='.format(
                        bank_card=pay_source_info.credit_card_idno, cvv=pay_source_info.credit_card_cvv2, name=quote(quote(pay_source_info.owner_name.encode('utf8'))), pid=pay_source_info.owner_pid,
                        mobile=pay_source_info.reverse_mobile, expired_date=pay_source_info.credit_card_validthru
                    )
                    http_conn = http_session.request(method='GET', url=url, verify=False)
                    result = http_conn.to_json()
                    Logger().info(result)
                    if result['errorCode'] == 0:
                        Logger().info('send mobile sms code success %s' % pay_source_info.reverse_mobile)
                        sms_verify_codes = Smser().get_99bill_verify_code(provider_price=provider_price, bank_card=pay_source_info.credit_card_idno)
                        if sms_verify_codes:
                            for sms_verify_code in sms_verify_codes:
                                gevent.sleep(0.2)
                                Logger().info('sms_verify_code %s' % sms_verify_code)
                                """
                                成功返回
                                <script>
                                location.href='/gateway/creditCardQuery.htm?method=getOrderStatus';
                                </script>

                                """
                                url = 'https://www.99bill.com/gateway/creditCardQuickPayV3.htm?method=selectCreditCardPay&bankId=CEB&quickOrCnp=1'
                                data = {
                                    'bankId': 'CEB',
                                    'instalmentTimes': '',
                                    'quickPan': pay_source_info.credit_card_idno,
                                    'quickexpiredMonth': pay_source_info.credit_card_validthru_month,
                                    'quickexpiredYear': pay_source_info.credit_card_validthru_year,
                                    'quickcvv2': pay_source_info.credit_card_cvv2,
                                    'quickcardHoldName': pay_source_info.owner_name,
                                    'quickHoldIdType': '0',
                                    'quickcardHolderId': pay_source_info.owner_pid,
                                    'quickphoneNo': pay_source_info.reverse_mobile,
                                    'creditCardQuickPayValidateCode': sms_verify_code,
                                    'savePci': '0'
                                }
                                data = """bankId=CEB&instalmentTimes=&quickPan={credit_card_idno}&quickexpiredMonth={credit_card_validthru_month}&quickexpiredYear={credit_card_validthru_year}&quickcvv2={credit_card_cvv2}&quickcardHoldName=罗启武&quickHoldIdType=0&quickcardHolderId={owner_pid}&quickphoneNo={reverse_mobile}&creditCardQuickPayValidateCode={sms_verify_code}&savePci=0&""".format(
                                    credit_card_idno=pay_source_info.credit_card_idno, credit_card_validthru_month=pay_source_info.credit_card_validthru_month,
                                    credit_card_validthru_year=pay_source_info.credit_card_validthru_year, credit_card_cvv2=pay_source_info.credit_card_cvv2,
                                    owner_pid=pay_source_info.owner_pid, reverse_mobile=pay_source_info.reverse_mobile, sms_verify_code=sms_verify_code
                                )
                                headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
                                Logger().debug('last step request %s' % data)
                                http_conn = http_session.request(method='POST', url=url, data=data, verify=False, headers=headers)

                                result = http_conn.content
                                Logger().debug('last step result %s' % result)
                                if '/gateway/creditCardQuery.htm?method=getOrderStatus' in result:
                                    return pay_dict['zl2385']
                                else:
                                    raise PayException('pay unknown error')
                            # 如果循环跑过后走到此说明验证码均为错误，抛出异常
                            raise PayException('sms code wrong')

                        else:
                            raise PayException('sms verify code not recieved')
                    else:
                        raise PayException('send mobile sms code error result %s' % result)

                elif self.pay_channel == '99BILL':
                    # 快钱信用卡支付（中国银行）

                    Logger().info("============== 99bill pay request ===========")
                    pay_source_info = pay_dict['lqw_c9337']
                    url = 'https://unipay.ceair.com/unipay/preparepay/pay!doPayFl.shtml'
                    data = {
                        'bankname': 'UNI_CC004_009',
                        'chk_promote': 'on',
                        'promotion_iconUrl': '',
                        'card_no': '',
                        'month': '01',
                        'year':	'2019',
                        'cvv_code': '',
                        'owner_name': '',
                        'id_type': 0,
                        'id_no': '',
                        'owner_mobile': '',
                        'email': '',
                        'pay_password': '',
                        'payBank.bankCode':	'UNI_CC004_009',
                        'payBank.bankSubCode': 'SUB99Bill009',
                        'payBank.bankGate':	'BILL99PAY',
                        'payBank.promoId': '',
                        'payBank.couponNo': '',
                        'payBank.cardBin': '',
                        'payBank.effectMonth': '',
                        'payBank.effectYear': '',
                        'payBank.idType': '',
                        'payBank.idNo': '',
                        'payBank.cvvNo': '',
                        'payBank.ownerName': '',
                        'payBank.ownerMobile': '',
                        'payBank.payType': '',
                        'payBank.email': '',
                        'payBank.pointPass': '',
                        'dynamicPointPay': '20063',
                        'payInfo.payType': '20061',
                        'countDown': '000942',
                        'accountId': '',
                        'assignBank': '',
                        'user_lastBank': '',
                        'user_usedBank': '',
                        'broker_ecard_bin': '092032,092039',
                        'ecard_bin': '092011,092021,092016,092026,092018,092028,092019,092029,092035,092036,092037,092038',
                        'ecoupon_bin': '092033',
                        'new_broker_bin': '092057,092058',
                        'score_bin': '092075',
                        'score_kong_bin': '092076',
                        'score_coupon_bin': '092077',
                        'pay_page_noamount': '[ESTORE_TP]',
                        'payInfo.payAmount': '2462.0',
                        'payInfo.walletAccount': 'NO',
                        'internal_flag': 'zh',
                        'credit_back_no': '信用卡背面签名条处的末三位数字。',
                        'credit_phone_no': '请在此处填写您在银行申请信用卡时留存的手机号码。',
                        'credit_regist_id_no': '请填写您申请信用卡时，提交给银行的相关证件号码，如身份证、护照、军官证等。',
                        'card_no_null': '卡号不能为空',
                        'card_length_err': '卡号为 15~19 位数字',
                        'verify_code_null': '验证码不能为空',
                        'verify_code_err': '验证码为3位数字',
                        'phone_no_err': '手机号码为11位数字',
                        'email_addr_err': '邮箱地址格式不正确',
                        'name_null': '真实姓名不能为空',
                        'name_err': '姓名为中文',
                        'id_no_null': '证件号码不能为空',
                        'id_no_err': '请输入正确的证件号码',
                        'password_length_notice': '请输入积分支付密码，密码不足8位请在原密码前加0补足8位',
                        'password_length_notice_wallet': '请输入积分钱包密码，密码不足6位请在原密码前加0补足6位',
                        'pay_as_total': '您好，您的订单不满足产品促销规则，是否按照原价支付？',
                        'choose_a_bank': '请您选择支付的银行。',
                        'order_expired': '您的订单已超过支付时限，无法继续支付，请重新预定。',
                        'timeout_notice': '已超时，无法支付',
                        'hour_set': '小时',
                        'minute_set': '分',
                        'second_set': '秒',
                        'credit_card_no_null': '请输入信用卡卡号！',
                        'credit_bin_support': '本产品仅支持以下卡BIN支付：',
                        'validate_fail': '校验卡号/帐户失败',
                        'unseccess_payment': '您好，该订单未支付成功，请重新支付！',
                        'unsure_payment': '您好，查询订单支付状态失败，请稍后再查！',
                        'announcement': '请确保您已阅读旅客须知全部内容，并同意购买。',
                    }

                    form = None
                    fields = None
                    for times in xrange(5):
                        http_conn = http_session.request(method='POST', url=url, data=data, verify=False, timeout=15)
                        result = http_conn.content
                        try:
                            soup = BeautifulSoup(result, 'lxml')
                            form = soup.find('form')
                            fields = form.findAll('input')
                            break
                        except Exception as e:
                            Logger().error('get pay page err:{}'.format(e))
                            time.sleep(2)

                    if not form or not fields:
                        raise PayException('get pay page failed!')

                    formdata = dict((field.get('name'), field.get('value')) for field in fields)
                    action_url = form['action']
                    Logger().debug('pay1redirect %s' % action_url)

                    # pay 2 跳转
                    gevent.sleep(0.2)
                    Logger().info('pay redirect 2')
                    url = action_url
                    data = formdata
                    http_conn = http_session.request(method='POST', url=url, data=data, verify=False)
                    result = http_conn.content
                    soup = BeautifulSoup(result, 'lxml')
                    form = soup.find('form')
                    fields = form.findAll('input')
                    formdata = dict((field.get('name'), field.get('value')) for field in fields)
                    action_url = form['action']
                    url = action_url
                    data = formdata

                    http_session = HttpRequest()
                    http_conn = http_session.request(method='POST', url=url, data=data, verify=False)
                    Logger().info('pay_source_info %s' % pay_source_info)

                    # 选择信用卡支付
                    gevent.sleep(0.2)
                    url = 'https://www.99bill.com/gateway/gateway.htm?method=selectPayType&payType=15'
                    http_conn = http_session.request(method='GET', url=url, verify=False)

                    # 选择中国银行支付
                    gevent.sleep(0.2)
                    url = 'https://www.99bill.com/gateway/creditCardQuickPayV3.htm?method=selectBank&bankId=BOC&selectPan='
                    data = {
                        'bankId': 'BOC',
                    }
                    http_conn = http_session.request(method='POST', url=url, data=data, verify=False)

                    # # 加载中国银行页面
                    # gevent.sleep(0.2)
                    # url = 'https://www.99bill.com/seashell/html/website/quotaMsg/creditCard/quota_boc_18701.html'
                    # http_conn = http_session.request(method='GET', url=url, verify=False, print_info=True, comment='loading boc html').content

                    # 发送短信验证码
                    gevent.sleep(0.2)
                    Logger().info('send mobile code')

                    # 此处双quote 是因为99bill的请求也是这样的，并不是BUG
                    url = 'https://www.99bill.com/gateway/creditCardQuickPayV3.htm?method=postDynaCode&quickPay=N&bankId=BOC&quickPan={bank_card}&quickcvv2={cvv}&quickcardHoldName={name}&quickcardHolderId={pid}&quickphoneNo={mobile}&quickexpiredDate={expired_date}&quickHoldIdType=0&savePci=0&rad=&period='.format(
                        bank_card=pay_source_info.credit_card_idno, cvv=pay_source_info.credit_card_cvv2, name=quote(quote(pay_source_info.owner_name.encode('utf8'))), pid=pay_source_info.owner_pid,
                        mobile=pay_source_info.reverse_mobile, expired_date=pay_source_info.credit_card_validthru
                    )
                    http_conn = http_session.request(method='GET', url=url, verify=False)
                    result = http_conn.to_json()
                    Logger().info(result)
                    if result['errorCode'] == 0:
                        Logger().info('send mobile sms code success %s' % pay_source_info.reverse_mobile)
                        sms_verify_codes = Smser().get_99bill_verify_code(provider_price=provider_price, bank_card=pay_source_info.credit_card_idno)
                        if sms_verify_codes:
                            for sms_verify_code in sms_verify_codes:
                                gevent.sleep(0.2)
                                Logger().info('sms_verify_code %s' % sms_verify_code)
                                """
                                成功返回
                                <script>
                                location.href='/gateway/creditCardQuery.htm?method=getOrderStatus';
                                </script>

                                """
                                url = 'https://www.99bill.com/gateway/creditCardQuickPayV3.htm?method=selectCreditCardPay&bankId=BOC&quickOrCnp=1'
                                data = {
                                    'bankId': 'BOC',
                                    'instalmentTimes': '',
                                    'quickPan': pay_source_info.credit_card_idno,
                                    'quickexpiredMonth': pay_source_info.credit_card_validthru_month,
                                    'quickexpiredYear': pay_source_info.credit_card_validthru_year,
                                    'quickcvv2': pay_source_info.credit_card_cvv2,
                                    'quickcardHoldName': pay_source_info.owner_name,
                                    'quickHoldIdType': '0',
                                    'quickcardHolderId': pay_source_info.owner_pid,
                                    'quickphoneNo': pay_source_info.reverse_mobile,
                                    'creditCardQuickPayValidateCode': sms_verify_code,
                                    'savePci': '0'
                                }
                                data = """bankId=BOC&instalmentTimes=&quickPan={credit_card_idno}&quickexpiredMonth={credit_card_validthru_month}&quickexpiredYear={credit_card_validthru_year}&quickcvv2={credit_card_cvv2}&quickcardHoldName=罗启武&quickHoldIdType=0&quickcardHolderId={owner_pid}&quickphoneNo={reverse_mobile}&creditCardQuickPayValidateCode={sms_verify_code}&savePci=0&""".format(
                                    credit_card_idno=pay_source_info.credit_card_idno, credit_card_validthru_month=pay_source_info.credit_card_validthru_month,
                                    credit_card_validthru_year=pay_source_info.credit_card_validthru_year, credit_card_cvv2=pay_source_info.credit_card_cvv2,
                                    owner_pid=pay_source_info.owner_pid, reverse_mobile=pay_source_info.reverse_mobile, sms_verify_code=sms_verify_code
                                )
                                headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
                                Logger().debug('last step request %s' % data)
                                http_conn = http_session.request(method='POST', url=url, data=data, verify=False, headers=headers)

                                result = http_conn.content
                                Logger().debug('last step result %s' % result)
                                if '/gateway/creditCardQuery.htm?method=getOrderStatus' in result:
                                    return pay_dict['lqw_c9337']
                                else:
                                    raise PayException('pay unknown error')
                            # 如果循环跑过后走到此说明验证码均为错误，抛出异常
                            raise PayException('sms code wrong')

                        else:
                            raise PayException('sms verify code not recieved')
                    else:
                        raise PayException('send mobile sms code error result %s' % result)

                else:
                    # 支付宝通道
                    Logger().info('ali pay post 1')
                    url = 'https://unipay.ceair.com/unipay/preparepay/pay!doPayFl.shtml'
                    data = {
                        'bankname': 'UNI_ALIPAY_002',
                        'card_no': '',
                        'month': '01',
                        'year': '2018',
                        'cvv_code': '',
                        'owner_name': '',
                        'id_type': '',
                        'id_no': '',
                        'owner_mobile': '',
                        'email': '',
                        'pay_password': '',
                        'payBank.bankCode': 'UNI_ALIPAY_002',
                        'payBank.bankSubCode': 'SUBALIPAY002',
                        'payBank.bankGate': 'ALIPAY',
                        'payBank.promoId': '',
                        'payBank.couponNo': '',
                        'payBank.cardBin': '',
                        'payBank.effectMonth': '',
                        'payBank.effectYear': '',
                        'payBank.idType': '',
                        'payBank.idNo': '',
                        'payBank.cvvNo': '',
                        'payBank.ownerName': '',
                        'payBank.ownerMobile': '',
                        'payBank.payType': '',
                        'payBank.email': '',
                        'payBank.pointPass': '',
                        'dynamicPointPay': '20063',
                        'payInfo.payType': '20061',
                        'countDown': '001733',
                        'accountId': '',
                        'assignBank': '',
                        'user_lastBank': '',
                        'user_usedBank': '',
                        'broker_ecard_bin': '092032,092039',
                        'ecard_bin': '092011,092021,092016,092026,092018,092028,092019,092029,092035,092036,092037,092038',
                        'ecoupon_bin': '092033',
                        'new_broker_bin': '092057,092058',
                        'score_bin': '092075',
                        'score_kong_bin': '092076',
                        'score_coupon_bin': '092077',
                        'pay_page_noamount': '[ESTORE_TP]',
                        'payInfo.payAmount': '760.0',  # 价格要注意
                        'internal_flag': 'zh',
                        'credit_back_no': '信用卡背面签名条处的末三位数字。',
                        'credit_phone_no': '请在此处填写您在银行申请信用卡时留存的手机号码。',
                        'credit_regist_id_no': '请填写您申请信用卡时，提交给银行的相关证件号码，如身份证、护照、军官证等。',
                        'card_no_null': '卡号不能为空',
                        'card_length_err': '卡号为 15~19 位数字',
                        'verify_code_null': '验证码不能为空',
                        'verify_code_err': '验证码为3位数字',
                        'phone_no_err': '手机号码为11位数字',
                        'email_addr_err': '邮箱地址格式不正确',
                        'name_null': '真实姓名不能为空',
                        'name_err': '姓名为中文',
                        'id_no_null': '证件号码不能为空',
                        'id_no_err': '请输入正确的证件号码',
                        'password_length_notice': '请输入积分支付密码，密码不足8位请在原密码前加0补足8位',
                        'pay_as_total': '您好，您的订单不满足产品促销规则，是否按照原价支付？',
                        'choose_a_bank': '请您选择支付的银行。',
                        'order_expired': '您的订单已超过支付时限，无法继续支付，请重新预定。',
                        'timeout_notice': '已超时，无法支付',
                        'hour_set': '小时',
                        'minute_set': '分',
                        'second_set': '秒',
                        'credit_card_no_null': '请输入信用卡卡号！',
                        'credit_bin_support': '本产品仅支持以下卡BIN支付：',
                        'validate_fail': '校验卡号/帐户失败',
                        'unseccess_payment': '您好，该订单未支付成功，请重新支付！',
                        'unsure_payment': '您好，查询订单支付状态失败，请稍后再查！',
                        'announcement': '请确保您已阅读旅客须知全部内容，并同意购买。'

                    }

                    http_conn = http_session.request(method='POST', url=url, data=data, verify=False)
                    result = http_conn.content
                    soup = BeautifulSoup(result, 'lxml')
                    form = soup.find('form')
                    fields = form.findAll('input')
                    formdata = dict((field.get('name'), field.get('value')) for field in fields)
                    action_url = form['action']
                    Logger().info('pay1redirect %s' % action_url)

                    # pay 2 跳转
                    gevent.sleep(0.2)
                    Logger().info('ali pay redirect 2')
                    url = action_url
                    data = formdata
                    http_conn = http_session.request(method='POST', url=url, data=data, verify=False)
                    alipay_form_result = http_conn.content
                    html = etree.HTML(alipay_form_result)
                    out_trade_no = html.xpath('//input[@id="out_trade_no"]/@value')
                    if out_trade_no:
                        order_info.out_trade_no = out_trade_no[0]
                    Logger().debug('alipay_form_result %s' % alipay_form_result)
                    if TBG.global_config['RUN_MODE'] == 'PROD':
                        if self.alipay(provider_order_id, alipay_form_result):
                            Logger().info('return pay_dict alipay_yiyou180 %s'%pay_dict['alipay_yiyou180'])
                            return pay_dict['alipay_yiyou180']
                        else:
                            raise PayException('alipay pay error')
                    else:
                        return False
            else:
                raise PayException('no pay status')


class CeairGroup(Ceair):
    timeout = 15  # 请求超时时间
    provider = 'ceair'  # 子类继承必须赋
    provider_channel = 'ceair_web_b2g'  # 子类继承必须赋
    operation_product_type = 'VISA100+会员'
    operation_product_mode = 'A2A'

    def _register(self, http_session, pax_info, ffp_account_info):

        Logger().info('login')
        url = 'http://kas.ceair.com/v4/Ajax/Account/LoginIn.ashx'
        data = {
            'Name': 'C01608000476',
            'Password': 'ddd8588',
            'ReturnUrl': 'http://kas.ceair.com/v4/Account/Login',
            'CheckCode': '3436',
            'RemeberMe': 1,
            'v': 1
        }

        http_conn = http_session.request(method='POST', url=url, data=data, is_direct=True)
        result = http_conn.content

        # Logger().info('get codeimage')
        # time.sleep(1)
        # url = 'http://kas.ceair.com/v4/B2G/MyTravelE/CalCodeImage?1529993303419'
        # ir = http_session.request(method='GET',url=url, stream=True).content

        # 获取计算题答案
        time.sleep(1)
        url = 'http://kas.ceair.com/v4/Ajax/Shopping/MemberHandler.ashx'
        data = {
            'ACT': 'CheckCalCodeImage'
        }

        http_conn = http_session.request(method='POST', url=url, data=data, is_direct=True)
        result = http_conn.content
        calc_result = result.replace('"', '')
        Logger().info('jisuanti result %s' % calc_result)

        # 获取手机验证码
        time.sleep(1)
        url = 'http://kas.ceair.com/v4/Ajax/Shopping/MemberHandler.ashx'
        data = {
            'ACT': 'SendMessageCode',
            'Mobile': pax_info.mobile,
            'inputCodeNo': calc_result
        }
        http_conn = http_session.request(method='POST', url=url, data=data, is_direct=True)
        result = http_conn.to_json()
        Logger().info('send mobile input code result %s' % result)
        input_code = result['Extend5']
        Logger().info('input_code %s' % input_code)

        # 注册表单
        """
        ACT=ToBeMember&CnFName=%E5%BC%A0&CnGName=%E5%88%86%E5%8F%91&EnFName=ZHANG&EnGName=FENFA&SexType=M&cardMsgs=%5B%7B%22cardTp%22%3A%22PP%22%2C%22cardNo%22%3A%22G99382319%22%7D%5D&BirthDate=1986-06-11&Mobile=13004680247&Email=fdsajew%40tongdun.org&InputCode=8458
        """
        time.sleep(1)
        url = 'http://kas.ceair.com/v4/Ajax/Shopping/MemberHandler.ashx'
        data = {
            'ACT': 'ToBeMember',
            'CnFName': pax_info.cn_last_name,
            'CNGName': pax_info.cn_first_name,
            'EnFName': pax_info.last_name,
            'EnGName': pax_info.first_name,
            'SexType': pax_info.gender,
            'cardMsgs': json.dumps([{"cardTp": "PP", "cardNo": pax_info.card_pp}]),
            'BirthDate': pax_info.birthdate,
            'Mobile': pax_info.mobile,
            'Email': pax_info.email,
            'InputCode': input_code

        }

        http_conn = http_session.request(method='POST', url=url, data=data, is_direct=True)
        result = http_conn.to_json()
        Logger().info('register result %s' % result)
        ffp_no = result['ffpNo']
        if ffp_no:
            # 注册成功
            ffp_account_info.username = ffp_no
            ffp_account_info.password = pax_info.birthdate.replace('-', '')
            ffp_account_info.provider = self.provider
            ffp_account_info.reg_passport = pax_info.card_pp
            ffp_account_info.reg_birthdate = pax_info.birthdate
            ffp_account_info.reg_gender = pax_info.gender
            ffp_account_info.reg_card_type = 'PP'
            return ffp_account_info
        else:
            raise RegisterException('no ffp no')

class CeairHk(Ceair):
    timeout = 15  # 请求超时时间
    provider = 'ceair'  # 子类继承必须赋
    provider_channel = 'ceair_web_hk'  # 子类继承必须赋
    operation_product_type = 'VISA100+会员'
    operation_product_mode = 'A2A'

    def _register(self, http_session, pax_info, ffp_account_info):
        # TODO: 目前注册逻辑已经失效，需要重新review

        Logger().info('login')

        url = 'https://easternmiles.ceair.com/mpf/register/initTW/zh_CN?locale=tw&v=1532484851125'
        result = http_session.request(method='GET', url=url, verify=False).to_json()

        gevent.sleep(0.2)
        url = 'https://easternmiles.ceair.com/mpf/register/sendCode?locale=tw'
        """
        data = {
            'geetest_challenge': checked_gee_2['challenge'],
            'geetest_validate': checked_gee_2['validate'],
            'geetest_seccode': checked_gee_2['validate'] + '|jordan',
            'address': email,
            'random': '0.0838052%s'% Random.gen_num(10) ,
            'cardNo': 'undefined',
            'passportNo': random_passport,
            'nationality': pax_info.nationality,
            'birthday': pax_info.birthdate,
            'adultNo': '',
            'adultPwd': '',
            'sexs': '男' if pax_info.gender == 'M' else '女',
            'sex': pax_info.gender,
            'email': email,
            'checkNum': checkcode,
            '': '已阅读并同意',
            'membershipPassword': random_password,
            'firstName': pax_info.last_name,
            'lastName': pax_info.first_name,
            'xiangNo': '',
            'ApdidToken': 'APDIDJS_donghang_%s' % Random.gen_hash()

        }
        """
        email = Random.gen_email()
        address = 'adfdafew'
        if pax_info.birthdate:
            birthdate = pax_info.birthdate
        else:
            birthdate = '1990-04-09'
        if pax_info.is_en_name():
            nationality = 'TW'
            data = {
                "cardType": "EXTENTPRMT",
                "nationality": nationality,
                "contactLanguage": "ZH",
                "billSendWay": "NON",
                "sex": pax_info.gender,
                "birthday": birthdate,
                "adultType": 2,
                "email": email,
                "homeAdress": address,
                "firstEnName": pax_info.first_name,
                "lastEnName": pax_info.last_name,
                "locale": "zh-TW"
            }
            # data = """{{"cardType":"EXTENTPRMT","nationality":"TW","contactLanguage":"ZH","billSendWay":"NON","firstCnName":"","firstEnName":"{first_enname}","lastEnName":"{last_enname}","birthday":"{birthdate}","adultType":2,"sex":"{gender}","email":"{email}","homeAdress":"fdaeeeew","locale":"zh-TW"}}""".format(
            #     first_enname=pax_info.first_name,last_enname=pax_info.last_name,birthdate=birthdate,gender=pax_info.gender,email=email
            # )
        else:
            nationality = 'TW'
            data = {
                "cardType": "EXTENTPRMT",
                "nationality": nationality,
                "contactLanguage": "ZH",
                "billSendWay": "NON",
                "sex": pax_info.gender,
                "birthday": birthdate,
                "adultType": 2,
                "email": email,
                "homeAdress": address,
                "firstCnName": pax_info.first_name,
                "lastCnName": pax_info.last_name,
                "locale": "zh-HK"
            }

        gevent.sleep(0.2)
        Logger().debug('send code data %s' % data)
        http_conn = http_session.request(method='POST', url=url, json=data, verify=False)
        result = http_conn.to_json()
        Logger().debug('resykt %s' % json.dumps(result))
        post_id = result['id']
        if post_id:
            checkcode = TBG.mailer.get_checkcode_via_reciver(reciever=email, provider=self.provider)
            if checkcode:
                random_password = Random.gen_password()
                passport = Random.gen_passport()
                url = 'https://easternmiles.ceair.com/mpf/register/registerMember?locale=tw'
                if pax_info.is_en_name():
                    # data ={"cardType":"EXTENTPRMT",
                    #        "nationality":nationality,
                    #        "contactLanguage":"ZH",
                    #        "billSendWay":"NON",
                    #        "sex":pax_info.gender,
                    #        "birthday":desenc(birthdate,'111','222','333'),
                    #        "adultType":2,
                    #        "email":desenc(email,'111','222','333'),
                    #        "homeAdress":address,
                    #        "firstEnName":pax_info.first_name,
                    #        "lastEnName":pax_info.last_name,
                    #        "locale":"zh-HK",
                    #        "id":post_id,
                    #        "code":checkcode,
                    #        "idCard":None,
                    #        "passport":desenc(passport,'111','222','333'),
                    #        "militaryCard":None,
                    #        "extEnterPermits":None,
                    #        "otherCard":None,
                    #        "queryPassword":desenc(random_password,'111','222','333')}
                    data = """{{"cardType":"EXTENTPRMT","nationality":"TW","contactLanguage":"ZH","billSendWay":"NON","sex":"{sex}","birthday":"{birthdate}","adultType":2,"email":"{email}","homeAdress":"{address}","firstEnName":"{first_enname}","lastEnName":"{last_enname}","locale":"zh-TW","id":{post_id},"code":"{code}","idCard":null,"passport":"{passport}","militaryCard":null,"extEnterPermits":null,"otherCard":null,"queryPassword":"{password}"}}""".format(
                        email=desenc(email, '111', '222', '333'), post_id=post_id, passport=desenc(passport, '111', '222', '333'), address=address,
                        password=desenc(random_password, '111', '222', '333'), birthdate=birthdate,
                        first_enname=pax_info.first_name.upper(),
                        last_enname=pax_info.last_name.upper(),
                        sex=pax_info.gender, code=checkcode
                    )
                else:
                    # data ={"cardType":"EXTENTPRMT",
                    #        "nationality":nationality,
                    #        "contactLanguage":"ZH",
                    #        "billSendWay":"NON",
                    #        "sex":pax_info.gender,
                    #        "birthday":desenc(birthdate,'111','222','333'),
                    #        "adultType":2,
                    #        "email":desenc(email,'111','222','333'),
                    #        "homeAdress":address,
                    #        "firstEnName": 'YANG',
                    #        "lastEnName": 'LIU',
                    #        "firstCnName":'扬',
                    #        "lastCnName":'刘',
                    #        # "firstEnName": cn_name_to_pinyin(convert_unicode(pax_info.first_name)).upper(),
                    #        # "lastEnName": cn_name_to_pinyin(convert_unicode(pax_info.last_name)).upper(),
                    #        # "firstCnName":pax_info.first_name,
                    #        # "lastCnName":pax_info.last_name,
                    #        "locale":"zh-HK",
                    #        "id":post_id,
                    #        "code":checkcode,
                    #        "idCard":None,
                    #        "passport":desenc(passport,'111','222','333'),
                    #        "militaryCard":None,
                    #        "extEnterPermits":None,
                    #        "otherCard":None,
                    #        "queryPassword":desenc(random_password,'111','222','333')}
                    data = """{{"cardType":"EXTENTPRMT","nationality":"TW","contactLanguage":"ZH","billSendWay":"NON","sex":"{sex}","birthday":"{birthdate}","adultType":2,"email":"{email}","homeAdress":"{address}","firstCnName":"{first_cnname}","firstEnName":"{first_enname}","lastCnName":"{last_cnname}","lastEnName":"{last_enname}","locale":"zh-TW","id":{post_id},"code":"{code}","idCard":null,"passport":"{passport}","militaryCard":null,"extEnterPermits":null,"otherCard":null,"queryPassword":"{password}"}}""".format(
                        email=desenc(email, '111', '222', '333'), post_id=post_id, passport=desenc(passport, '111', '222', '333'), address=address,
                        password=desenc(random_password, '111', '222', '333'), birthdate=birthdate,
                        first_cnname=pax_info.first_name, first_enname=cn_name_to_pinyin(convert_unicode(pax_info.first_name)).upper(),
                        last_cnname=pax_info.last_name, last_enname=cn_name_to_pinyin(convert_unicode(pax_info.last_name)).upper(),
                        sex=pax_info.gender, code=checkcode
                    )

                Logger().debug('register send data %s' % data)
                Logger().debug('data %s' % data)
                headers = {'Content-Type': 'application/json;charset=UTF-8'}
                http_conn = http_session.request(method='POST', url=url, data=data, verify=False, headers=headers)
                result = http_conn.content

                Logger().info('register result %s' % result)
                result = http_conn.to_json()
                ffp_no = result['memberId']
                if ffp_no:
                    # 注册成功
                    ffp_account_info.username = ffp_no
                    ffp_account_info.password = random_password
                    ffp_account_info.provider = self.provider
                    ffp_account_info.reg_passport = pax_info.card_pp
                    ffp_account_info.reg_birthdate = pax_info.birthdate
                    ffp_account_info.reg_gender = pax_info.gender
                    ffp_account_info.reg_card_type = 'PP'
                    return ffp_account_info
                else:
                    raise RegisterException('no ffp no')
            else:
                raise RegisterException('Email Code Fetch Failed')
        else:
            raise RegisterException('postid Fetch Failed')


class Ceair2(Ceair):
    timeout = 15  # 请求超时时间
    provider = 'ceair'  # 子类继承必须赋
    provider_channel = 'ceair_web_2'  # 子类继承必须赋
    operation_product_type = 'VISA100+会员'
    operation_product_mode = 'A2A'
    is_display = True

    def _register(self,http_session, pax_info, ffp_account_info):

        # TODO 此处逻辑混乱，等稳定后重构

        if pax_info.card_type == 'NI':

            try:
                first_check_exists_ffp = False
                if pax_info.card_type == 'NI':
                    # 身份证修改
                    card_no = pax_info.card_ni

                else:
                    card_no = pax_info.card_pp
                data = {'passengerJsonStr': json.dumps(["|{card_type}|{card_no}|".format(card_type=pax_info.card_type, card_no=card_no)])}
                result = http_session.request(method='POST',url='https://m.ceair.com/mobile/book/flight-ffp-pax!findFfp.shtml',
                                              data=data).to_json()
                if result['resultCode'] == "0" and result['result'][0].split('|')[4] == '1':
                    # 账户存在

                    # 尝试登陆 只有身份证才知道默认密码，护照不知道默认密码，所以无法尝试登陆
                    if pax_info.card_type == 'NI':
                        Logger().info('try to login card_ni %s ' % card_no)
                        ffp_account_info_tmp2 = FFPAccountInfo()
                        ffp_account_info_tmp2.username = card_no  # 任意指定一个会员账号
                        ffp_account_info_tmp2.password = pax_info.birthdate.replace('-', '')
                        try:
                            self.login(ffp_account_info=ffp_account_info_tmp2)
                            ffp_account_info.username = card_no

                            ffp_account_info.provider = self.provider
                            ffp_account_info.reg_pid = pax_info.card_ni
                            ffp_account_info.reg_card_type = 'NI'
                            ffp_account_info.password = pax_info.card_ni[6:14]
                            ffp_account_info.reg_birthdate = pax_info.birthdate
                            ffp_account_info.reg_gender = pax_info.gender
                            Logger().info('try to login success ')
                            return ffp_account_info
                        except Exception as e:
                            Logger().error('default pwd login error')


                    # 更换证件
                    Logger().info('findFfp api return ffp exists')
                    if pax_info.card_type == 'NI':
                        # 身份证修改
                        modified_card_no = modify_ni(pax_info.card_ni)
                        pax_info.used_card_no = modified_card_no
                        pax_info.card_ni = modified_card_no
                        pax_info.modified_card_no = modified_card_no
                    else:
                        modified_card_no = modify_pp(pax_info.card_pp)
                        pax_info.used_card_no = modified_card_no
                        pax_info.card_pp = modified_card_no
                        pax_info.modified_card_no = modified_card_no
                    pax_info.attr_competion()
                    Logger().info('FFP_EXISTS change id %s' % modified_card_no)
                    first_check_exists_ffp = True
                else:
                    Logger().info('findFfp api return no ffp')
            except Exception as e:
                Logger().error('findFfp api error ')


            err_code = None
            # try:
            #     ffp_account_info = self._mobile_register(http_session=http_session, pax_info=pax_info, ffp_account_info=ffp_account_info)
            #     return ffp_account_info
            # except RegisterCritical as e:
            #     Logger().info('e.err_code %s' % e.err_code)
            #     if e.err_code == 'FFP_EXISTS':
            #         err_code = 'FFP_EXISTS'
            #
            #         # 更换证件
            #
            #         if pax_info.card_type == 'NI':
            #             # 身份证修改
            #             modified_card_no = modify_ni(pax_info.card_ni)
            #             pax_info.used_card_no = modified_card_no
            #             pax_info.card_ni = modified_card_no
            #             pax_info.modified_card_no = modified_card_no
            #         else:
            #             modified_card_no = modify_pp(pax_info.card_pp)
            #             pax_info.used_card_no = modified_card_no
            #             pax_info.card_pp = modified_card_no
            #             pax_info.modified_card_no = modified_card_no
            #         pax_info.attr_competion()
            #         Logger().info('FFP_EXISTS change id %s'%modified_card_no)
            # except Exception as e:
            #     Logger().error(e)

            try:
                ffp_account_info = self._h5_register(http_session=http_session, pax_info=pax_info, ffp_account_info=ffp_account_info)
                return ffp_account_info
            except Exception as e:
                Logger().error(e)

            # 走邮箱注册
            ffp_account_info = self._email_register(http_session=http_session, pax_info=pax_info, ffp_account_info=ffp_account_info)
            return ffp_account_info

        else:
            # FIXME 国际注册暂时不可用，进行固定账号注册逻辑

            account = self._get_fix_account()
            ffp_account_info.username = account['username']
            ffp_account_info.password = account['password']
            ffp_account_info.provider = self.provider
            ffp_account_info.reg_card_type = 'PP'
            ffp_account_info.reg_birthdate = account['birthdate']
            ffp_account_info.reg_gender = account['gender']
            ffp_account_info.reg_passport = pax_info.card_pp
            return ffp_account_info

    def _mobile_register(self, http_session, pax_info, ffp_account_info):

        """
        _ga=GA1.2.1376342331.1529660753;
        _gscu_1605927201=29660753ps4swz70;
        Webtrends=f54a7c39.56f37e6caf01d;
         language=zh_CN;
         ecrmWebtrends=183.195.33.248.1529660893511;
          UM_distinctid=1643609bb9867-0d779e8c8671f6-6119227d-fa000-1643609bb9a224;
           _pk_id.1.89af=3cff14fa81474fe0.1530610701.1.1530610701.1530610701.;
            __utma=101442195.1376342331.1529660753.1529660770.1531731154.2;
             __utmz=101442195.1531731154.2.2.utmcsr=ecrm.ceair.com|utmccn=(referral)|utmcmd=referral|utmcct=/myceair/coupon.html;
              user_cookie=true;
               ABRecommend=RecommendB;
               _pzfxoinf=1534441547066;
                alipay_apdid_token=Lx%2B02uhZd0W538eCSfhWu35JoURwscK2%2F5My4npot8bFbBY8Dfo5QhfJuApzzhe7;
                 Hm_lvt_eda21611a285cee9ace5f238b3947548=1536806441;
                  _gid=GA1.2.506753914.1539577830;
                   ffpno=663022880578;
                    passportId=D72CD421010D8507461DD322613BD740;
                     _gscbrs_1605927201=1;
                      UUID=DD8D4BC14F89467D8518D3970AA583CB;
                      JSESSIONID=-cmjlDdXkqhTjsX8-ocBU3nL.laputaServer4;
                       apdid_data=%7B%22time%22%3A1539679920069%2C%22token%22%3A%22APDIDJS_donghang_36a3ea010a6292245804dfcdcca43ffb%22%7D;
                        _pzfxuvpc=1529660752937%7C2332710687105559419%7C2044%7C1539679953629%7C194%7C1027773063169449409%7C4108789416751967803;
                         _pzfxsvpc=4108789416751967803%7C1539679920711%7C5%7Chttp%3A%2F%2Fwww.ceair.com%2Fbooking%2Fsha-kmg-181016_CNY.html;
                          _gat=1
        """

        Logger().info('mobile register start...')
        cookie_dict = {
            '_ga':'GA1.2.1376342331.1529660753',
            '_gscu_1605927201':'29660753ps4swz70',
            'Webtrends':'f54a7c39.56f37e6caf01d',
            'language':'zh_CN',
            'ecrmWebtrends':'183.195.33.248.1529660893511',
            'UM_distinctid':'1643609bb9867-0d779e8c8671f6-6119227d-fa000-1643609bb9a224',
            '_pk_id.1.89af':'3cff14fa81474fe0.1530610701.1.1530610701.1530610701.',
            '__utma':'101442195.1376342331.1529660753.1529660770.1531731154.2',
            '__utmz':'101442195.1531731154.2.2.utmcsr=ecrm.ceair.com|utmccn=(referral)|utmcmd=referral|utmcct=/myceair/coupon.html',
            'user_cookie':'true',
            'ABRecommend':'RecommendB',
            '_pzfxoinf':'1534441547066',
            'alipay_apdid_token':'Lx%2B02uhZd0W538eCSfhWu35JoURwscK2%2F5My4npot8bFbBY8Dfo5QhfJuApzzhe7',
            'Hm_lvt_eda21611a285cee9ace5f238b3947548':'1536806441',
            '_gid':'GA1.2.506753914.1539577830',
            '_gscbrs_1605927201':'1',
            'apdid_data':'%7B%22time%22%3A{ts}%2C%22token%22%3A%22APDIDJS_donghang_36a3ea010a6292245804dfcdcca43ffb%22%7D'.format(ts=Time.timestamp_ms()),
            '_pzfxuvpc':'1529660752937%7C2332710687105559419%7C2044%7C1539679953629%7C194%7C1027773063169449409%7C4108789416751967803',
            '_pzfxsvpc':'4108789416751967803%7C1539679920711%7C5%7Chttp%3A%2F%2Fwww.ceair.com%2Fbooking%2Fsha-kmg-181016_CNY.html',
            '_gat':'1'
        }
        http_session.update_cookie(cookie_dict=cookie_dict)

        search_try_count = 4
        search_tries = 0
        start_day = 7

        fscKey = None
        snk = None
        airPriceUnitIndex = None

        while 1:
            gevent.sleep(0.2)
            order_info = OrderInfo()
            order_info.from_date = (Time.curr_date_obj() + datetime.timedelta(days=start_day)).strftime('%Y-%m-%d')  # 三天后的航班
            Logger().debug('order_info.from_date %s' % order_info.from_date)
            order_info.from_airport = 'PVG'  # 搜索hot航班，提高成功率
            order_info.to_airport = 'CAN'  #
            order_info.adt_count = 1
            order_info.trip_type = 'OW'
            order_info.attr_competion()

            self.flight_search(http_session, order_info)

            # 确认航班
            gevent.sleep(0.2)
            fscKey, snk, airPriceUnitIndex = self._pre_register(http_session, order_info)
            if fscKey and snk:
                Logger().info('confirm flight ')
                break
            else:
                if search_tries > search_try_count:
                    raise RegisterException('no flight to register')
                else:
                    search_tries += 1
                    start_day += 1

        """
        post
        单程
        selectConds={"fscKey":"OW:1:0:0:zh:CNY:a:/SHA:SZX:2018-11-02:,:NEWOTA",
        "selcon":[{"airPriceUnitIndex":0,"snk":"SHA1541118000000SZX1541127300000FM9331HYJ_ECB1470.0"}]}&sessionId=1529663033735
        往返
        ={"fscKey":"RT:1:0:0:zh:CNY:a:/SHA:SIN:2018-11-02:,SIN:SHA:2018-11-04:,:NEWOTA","selcon":[{"airPriceUnitIndex":6,"snk":"SHA1541088300000SIN1541107500000SIN1541264100000SHA1541283900000MU543/MU544HYZJ_SHA_GJS/S1060/1060"}]}&sessionId=1530517061061
        return
        /flight/flight_booking_passenger.html;3b4de196dd3d45df8b6ebdd76527f343
        """
        if not fscKey or not snk:
            raise BookingException('ceair_session_id not found')

        select_conds = {
            'fscKey': fscKey,
            'selcon': [{"airPriceUnitIndex": airPriceUnitIndex, "snk": snk}]
        }
        Logger().debug('select_conds %s ' % select_conds)
        data = {
            'selectConds': json.dumps(select_conds, ensure_ascii=False)
        }
        url = 'http://www.ceair.com/otabooking/flight-confirm!flightConfirm.shtml'
        http_conn = http_session.request(method="POST", url=url, data=data)
        result = http_conn.content
        Logger().debug('confirm result %s' % result)
        # all_check_token = result.split(';')[1]
        # all_check_token = all_check_token.split('|')[0]

        # 获取信息更新session
        gevent.sleep(0.2)
        Logger().info('paxinfo init')
        url = 'http://www.ceair.com/otabooking/paxinfo-input!init.shtml?_=%s' % Time.timestamp_ms()
        http_conn = http_session.request(method='GET', url=url, verify=False)
        # result = http_conn.content
        # Logger().debug("========== session version: {} ==========".format(http_conn.content))
        # session_version_exp = re.compile(r'var sessionVersion = "(.*?)";')
        # search_result = session_version_exp.findall(result)
        # if search_result:
        #     Logger().debug("================ paxinfo input re result {} ===========".format(search_result))
        #     # session_version = int(search_result[0])
        #     session_version = search_result[0]
        # else:
        #     raise BookingException('search_version fetch error')
        search_result = http_conn.to_json()
        session_version = search_result.get('sessionVersion')
        if not session_version:
            raise BookingException('search_version fetch error')

        modified_card_no = None
        retries_count = 3
        for x in range(0, retries_count):
            # 尝试三次
            err_code = None
            try:
                ffp_account_info = self._sub_register(http_session=http_session,pax_info=pax_info,ffp_account_info=ffp_account_info,session_version=session_version)
                return ffp_account_info
            except RegisterCritical as e:
                Logger().debug('e.err_code %s' %e.err_code)
                if x == retries_count - 1:
                    # 如果判断是最后一次，则直接raise，不再走下面修改证件的逻辑
                    raise
                elif e.err_code == 'FFP_EXISTS':
                    err_code = 'FFP_EXISTS'
            except Exception as e:
                Logger().error(e)

            # 账号经过无法注册也无法登陆,修改证件号重新注册
            if err_code == 'FFP_EXISTS':
                if pax_info.card_type == 'NI':
                    # 身份证修改
                    modified_card_no = modify_ni(pax_info.card_ni)
                    pax_info.used_card_no = modified_card_no
                    pax_info.card_ni = modified_card_no
                    pax_info.modified_card_no = modified_card_no
                else:
                    modified_card_no = modify_pp(pax_info.card_pp)
                    pax_info.used_card_no = modified_card_no
                    pax_info.card_pp = modified_card_no
                    pax_info.modified_card_no = modified_card_no
                pax_info.attr_competion()
                Logger().sinfo('start modified_card_no %s register' % modified_card_no)
        else:
            raise RegisterException

    def _h5_register(self,http_session, pax_info, ffp_account_info ):

        Logger().info('h5_sub_register start')

        retries_count = 3
        for x in range(0, retries_count):
            # 尝试三次
            err_code = None
            try:
                http_session = HttpRequest()
                ffp_account_info = self._h5_sub_register(http_session=http_session, pax_info=pax_info, ffp_account_info=ffp_account_info)
                return ffp_account_info
            except RegisterCritical as e:
                Logger().debug('e.err_code %s' % e.err_code)
                if x == retries_count - 1:
                    # 如果判断是最后一次，则直接raise，不再走下面修改证件的逻辑
                    raise
                elif e.err_code == 'FFP_EXISTS':
                    err_code = 'FFP_EXISTS'
                elif e.err_code == 'RRV2003':
                    raise
            except Exception as e:
                Logger().error(e)


            # 账号经过无法注册也无法登陆,修改证件号重新注册
            if err_code == 'FFP_EXISTS':
                if pax_info.card_type == 'NI':
                    # 身份证修改
                    modified_card_no = modify_ni(pax_info.card_ni)
                    pax_info.used_card_no = modified_card_no
                    pax_info.card_ni = modified_card_no
                    pax_info.modified_card_no = modified_card_no
                else:
                    modified_card_no = modify_pp(pax_info.card_pp)
                    pax_info.used_card_no = modified_card_no
                    pax_info.card_pp = modified_card_no
                    pax_info.modified_card_no = modified_card_no
                pax_info.attr_competion()
                Logger().sinfo('start modified_card_no %s register' % modified_card_no)
        else:
            raise RegisterException

    def _h5_sub_register(self,http_session, pax_info, ffp_account_info):
        """
        H5 注册渠道，目前可以注册官网提示手机实名的账号,只能注册身份证，不能注册护照
        cookie 仅仅需要继承ffpSendCode的JSESSION即可
        :param http_session:
        :param pax_info:
        :param ffp_account_info:
        :return:
        """

        self.change_mobile()
        Logger().info('h5_sub_register start')

        Logger().info('send mobile code')
        mobile = Random.gen_mobile()
        name = Random.gen_full_name_4()

        # 接收短信逻辑需要加锁
        @sms_lock()
        def send_mobile_code(mobile_info,sms_func):
            url = 'http://m.ceair.com/mobile/book/flight-ffp-pax!ffpSendCode.shtml'
            data = {
                'contactMobile':mobile_info['mobile']
            }
            result = http_session.request(method='POST',url=url,data=data).to_json()
            if result['resultCode'] == '0':
                Logger().info('mobile code send success')

                # mobile = "18477741519"
                return Smser().get_ceair_h5_register_verify_code(mobile_info=mobile_info)
            else:
                raise RegisterException('mobile code operation fail')

        checkcodes = send_mobile_code(mobile_info=self.mobile_info,sms_func='get_ceair_h5_register_verify_code')
        for checkcode in checkcodes:
            # 验证手机验证码
            Logger().info('sms verify code %s' % checkcode)
            """

            未知错误
            {
              "resultCode": "1",
              "errorInfo": "Unrecognized field \"errCode\" (Class com.uni.webservice.mode.base.bean.ffp.mufly.member.FastEnrollResultBean), not marked as ignorable\n at [Source: java.io.StringReader@1f421900; line: 1, column: 30] (through reference chain: com.uni.webservice.mode.base.bean.ffp.mufly.member.FastEnrollResultBean[\"errCode\"])"
            }

            手机绑定数量超过3个
            {
              "resultCode": "1",
              "errorInfo": "program.member.MobileNumAlreadyUsed 3"
            }
            证件号已存在
            {
              "resultCode": "1",
              "errorInfo": "id.card.exist"
            }
            手机验证码错误
            {
              "resultCode": "2",
              "errorInfo": "手机验证码输入错误！"
            }

            性别不一致
            {
              "resultCode": "1",
              "errorInfo": "customer.profile.InvalidIdNumberWithGender"
            }

            请求成功
            {
                  "resultCode": "0",
                  "errorInfo": "",
                  "result": {
                    "account": "643022896942",
                    "accountType": "FFP",
                    "birthDate": "1986-05-07",
                    "ffpNo": "643022896942",
                    "gender": "M",
                    "identificationList": [
                      {
                        "identificationType": 1,
                        "identificationValue": "360121198605075212",
                        "isConfirm": false,
                        "name": "分即可大"
                      }
                    ],
                    "lastTime": "2018-10-16 19:49:12",
                    "name": "分即可大",
                    "nameCn": "分即可大",
                    "nameEn": "FEN/DA",
                    "passportId": 665712360,
                    "passwordType": "E",
                    "phone": "18477741519",
                    "registerTime": "2018-10-16T19:49:12+08:00",
                    "tier": "STD",
                    "tokenKey": "8880AF2E349948ADDCCEF68156BE8ECBBD74B885BCF6CA0B22457BAD917E4180",
                    "transactionId": "1539690552767",
                    "transactionPasswordStatus": 0
                  }
                }
            success
            """

            url = 'http://m.ceair.com/mobile/book/flight-ffp-pax!initiation.shtml'

            if pax_info.card_type == 'NI':

                jsonstr = {"id":"70",
                           "paxName":pax_info.name,
                           "paxNameLast":"",
                           "paxNameFirst":"",
                           "gender":pax_info.gender,
                           "birthday":pax_info.birthdate.replace('-', ''),
                           "nationality":"CN",
                           "mobile":mobile,
                           "email":"",
                           "jcIdNo1":"",
                           "jcId1":"",
                           "jcIdNo2":"",
                           "jcId2":"",
                           "ffpAirline":"",
                           "ffpNo":"",
                           "undefined":"",
                           "uniPaxIdentificationJson":"[{\"favorPaxId\":\"895\",\"id\":\"\",\"idType\":\"NI\",\"idNo\":\"%s\",\"idValidDt\":\"\",\"idIssueNation\":\"\",\"selected\":1}]"%pax_info.card_ni,
                           "paxType":"ADT",
                           "favorPaxIdDtoList":[{"favorPaxId":"895","id":"","idType":"NI","idNo":pax_info.card_ni,"idValidDt":"","idIssueNation":"","selected":1}],
                           "phoneNumber":mobile,
                           "name":pax_info.name,
                           "passengerType":"ADT",
                           "idType":"NI",
                           "idNo":pax_info.card_ni,
                           "cardPkey":"",
                           "paxIdNatnCd":"",
                           "notAllInfo":0,
                           "idTypeCN":"*屏蔽的关键字*",
                           "idType2":"",
                           "idTypeCN2":"",
                           "cardPkey2":"",
                           "idNo2":"",
                           "_paxName":pax_info.name,
                           "selected":1,
                           "userId":"",
                           "versionNum":0,
                           "contactInfo":"",
                           "isvip":"0",
                           "vipGrade":"N",
                           "nameInput":0
                           }
                raw_str = """{{"id":"","paxName":"{name}","paxNameLast":"","paxNameFirst":"","gender":"{gender}","birthday":"{birthdate}","nationality":"CN","mobile":"{mobile}","email":"","jcIdNo1":"","jcId1":"","jcIdNo2":"","jcId2":"","ffpAirline":"","ffpNo":"","undefined":"","uniPaxIdentificationJson":"[{{\\"favorPaxId\\":\\"895\\",\\"id\\":\\"\\",\\"idType\\":\\"NI\\",\\"idNo\\":\\"{card_ni}\\",\\"idValidDt\\":\\"\\",\\"idIssueNation\\":\\"\\",\\"selected\\":1}}]","paxType":"ADT","favorPaxIdDtoList":[{{"favorPaxId":"895","id":"","idType":"NI","idNo":"{card_ni}","idValidDt":"","idIssueNation":"","selected":1}}],"phoneNumber":"{mobile}","name":"{name}","passengerType":"ADT","idType":"NI","idNo":"{card_ni}","cardPkey":"","paxIdNatnCd":"","notAllInfo":0,"idTypeCN":"*屏蔽的关键字*","idType2":"","idTypeCN2":"","cardPkey2":"","idNo2":"","_paxName":"{name}","selected":1,"userId":"","versionNum":0,"contactInfo":"","isvip":"0","vipGrade":"N","nameInput":0}}""".format(
                    name=pax_info.name,card_ni=pax_info.card_ni,gender=pax_info.gender,birthdate=pax_info.birthdate.replace('-', ''),mobile=mobile
                )
                # data = {
                #     'passengerJsonStr':quote(raw_str),
                #     'vacode':checkcode
                # }
                post_data = """passengerJsonStr=%7b%22id%22%3a%2270%22%2c%22paxName%22%3a%22{name}%22%2c%22paxNameLast%22%3a%22%22%2c%22paxNameFirst%22%3a%22%22%2c%22gender%22%3a%22{gender}%22%2c%22birthday%22%3a%22{birthdate}%22%2c%22nationality%22%3a%22CN%22%2c%22mobile%22%3a%22{mobile}%22%2c%22email%22%3a%22%22%2c%22jcIdNo1%22%3a%22%22%2c%22jcId1%22%3a%22%22%2c%22jcIdNo2%22%3a%22%22%2c%22jcId2%22%3a%22%22%2c%22ffpAirline%22%3a%22%22%2c%22ffpNo%22%3a%22%22%2c%22undefined%22%3a%22%22%2c%22uniPaxIdentificationJson%22%3a%22%5b%7b%5c%22favorPaxId%5c%22%3a%5c%22895%5c%22%2c%5c%22id%5c%22%3a%5c%22%5c%22%2c%5c%22idType%5c%22%3a%5c%22NI%5c%22%2c%5c%22idNo%5c%22%3a%5c%22{card_ni}%5c%22%2c%5c%22idValidDt%5c%22%3a%5c%22%5c%22%2c%5c%22idIssueNation%5c%22%3a%5c%22%5c%22%2c%5c%22selected%5c%22%3a1%7d%5d%22%2c%22paxType%22%3a%22ADT%22%2c%22favorPaxIdDtoList%22%3a%5b%7b%22favorPaxId%22%3a%22895%22%2c%22id%22%3a%22%22%2c%22idType%22%3a%22NI%22%2c%22idNo%22%3a%22{card_ni}%22%2c%22idValidDt%22%3a%22%22%2c%22idIssueNation%22%3a%22%22%2c%22selected%22%3a1%7d%5d%2c%22phoneNumber%22%3a%22{mobile}%22%2c%22name%22%3a%22{name}%22%2c%22passengerType%22%3a%22ADT%22%2c%22idType%22%3a%22NI%22%2c%22idNo%22%3a%22{card_ni}%22%2c%22cardPkey%22%3a%22%22%2c%22paxIdNatnCd%22%3a%22%22%2c%22notAllInfo%22%3a0%2c%22idTypeCN%22%3a%22*%e5%b1%8f%e8%94%bd%e7%9a%84%e5%85%b3%e9%94%ae%e5%ad%97*%22%2c%22idType2%22%3a%22%22%2c%22idTypeCN2%22%3a%22%22%2c%22cardPkey2%22%3a%22%22%2c%22idNo2%22%3a%22%22%2c%22_paxName%22%3a%22{name}%22%2c%22selected%22%3a1%2c%22userId%22%3a%22%22%2c%22versionNum%22%3a0%2c%22contactInfo%22%3a%22%22%2c%22isvip%22%3a%220%22%2c%22vipGrade%22%3a%22N%22%2c%22nameInput%22%3a0%7d&vacode={checkcode}""".format(
                    name=quote(name.encode('utf-8')).lower(), card_ni=pax_info.card_ni, gender=pax_info.gender, birthdate=pax_info.birthdate.replace('-', ''), mobile=mobile,checkcode=checkcode
                )
                data = "passengerJsonStr=%s&vacode=%s"%(quote(raw_str),checkcode)

            else:
                pax_data = {
                    "id": "70",
                    # "paxName": pax_info.name,
                    "paxName": "",
                    "paxNameLast": pax_info.last_name,
                    "paxNameFirst": pax_info.first_name,
                    "gender": pax_info.gender,
                    "birthday": pax_info.birthdate.replace('-', ''),
                    "nationality": pax_info.nationality,
                    "contactInfo": mobile,
                    "email": Random.gen_email(),
                    "jcIdNo1": "",
                    "jcId1": "",
                    "jcIdNo2": "",
                    "jcId2": "",
                    "ffpAirline": "",
                    "ffpNo": "",
                    "mobile": "",
                    "uniPaxIdentificationJson": json.dumps([{
                        'favorPaxId': '',
                        'id': '',
                        'idIssueNation': pax_info.card_issue_place,
                        'idNo': pax_info.card_pp,
                        # 'idNo': 'EA2917611',
                        'idType': 'PP',
                        'idValidDt': pax_info.card_expired.replace('-', ''),
                        'selected': 1
                    }]),
                    "paxType": "ADT",
                    "favorPaxIdDtoList": [{
                        "favorPaxId": "",
                        "id": "",
                        "idType": "PP",
                        "idNo": pax_info.card_pp,
                        # "idNo": 'EA2917611',
                        "idValidDt": pax_info.card_expired.replace('-', ''),
                        "idIssueNation": pax_info.card_issue_place,
                        "selected": 1
                    }],
                    "phoneNumber": "",
                    # "name": pax_info.name,
                    "name": "",
                    "passengerType": "ADT",
                    "idType": "PP",
                    "idNo": pax_info.card_pp,
                    # "idNo": 'EA2917611',
                    "cardPkey": "",
                    "paxIdNatnCd": pax_info.card_issue_place,
                    "notAllInfo": 0,
                    "idTypeCN": "护照",
                    "idType2": "",
                    "idTypeCN2": "",
                    "cardPkey2": "",
                    "idNo2": "",
                    "_paxName": pax_info.name,
                    "selected": 1,
                    "userId": "",
                    "versionNum": 0,
                    "isvip": "0",
                    "vipGrade": "N",
                    "nameInput": 0
                }

                pax_data_json = json.dumps(pax_data)
                pax_data.pop('nameInput')
                pax_data_list = json.dumps([pax_data])

                post_data = {
                    'vacode': checkcode,
                    'paxNameCn': "",
                    'passengerJsonStr': pax_data_json,
                    'passengerListJsonStr': pax_data_list,
                }

            headers = {'Referer': 'https://m.ceair.com/pages/booking/placeorder.html','Content-Type': 'application/x-www-form-urlencoded'}
            http_conn = http_session.request(method='POST', url=url,data=post_data, headers=headers)
            result = http_conn.to_json()
            if result['resultCode'] == "0":
                if pax_info.card_type == 'NI':
                    ffp_account_info.username = result['result']['account']
                    ffp_account_info.provider = self.provider
                    ffp_account_info.reg_pid = pax_info.card_ni
                    ffp_account_info.reg_card_type = 'NI'
                    ffp_account_info.password = pax_info.card_ni[6:14]
                    ffp_account_info.reg_birthdate = pax_info.birthdate
                    ffp_account_info.reg_gender = pax_info.gender
                    ffp_account_info.mobile = mobile
                else:
                    ffp_account_info.username = result['result']['account']
                    ffp_account_info.provider = self.provider
                    ffp_account_info.reg_pid = pax_info.card_pp
                    ffp_account_info.reg_card_type = 'PP'
                    ffp_account_info.password = pax_info.birthdate.replace('-', '')
                    ffp_account_info.reg_birthdate = pax_info.birthdate
                    ffp_account_info.reg_gender = pax_info.gender
                    ffp_account_info.mobile = mobile
                return ffp_account_info
            elif result['errorInfo'] == 'id.card.exist':
                # 卡号已经存在
                raise RegisterCritical('ffp has already exists', err_code='FFP_EXISTS')
            elif result['errorInfo'] == 'program.member.DuplicateMemberProfilesExistsAsPerAlgorithm':
                raise RegisterCritical('ffp has already exists', err_code='FFP_EXISTS')
            elif result['errorInfo'] == 'passport.exist':
                raise RegisterCritical('ffp has already exists', err_code='FFP_EXISTS')
            else:
                Logger().warn('h5 register result not expected %s' % result)
            Logger().info('multi mobile verify code retry...')


        raise RegisterException('h5 register error')

    def _sub_register(self, http_session, pax_info, ffp_account_info,session_version):

        self.change_mobile()

        # 更新乘机人信息
        gevent.sleep(0.2)
        Logger().info('_mobile_sub_register')
        Logger().info('update paxinfo')
        url = 'http://www.ceair.com/otabooking/paxinfo-input!checkDataNew.shtml'

        pax_data = []

        email = Random.gen_email()
        mobile = Random.gen_mobile()

        """
        datanew

        [{"uuid":0,"benePaxListIndex":"","birthday":"",
        "docaCity":"Park","docaNationCode":"",
        "docaPostCode":"19019","docaState":"PA",
        "docaStreet":"Shinfield Road Reading RG2 7ED",
        "email":"","ffpAirline":"","ffpLevel":"","ffpNo":"",
        "gender":"M","idNo":"110101197903074756","idType":"NI","id":"",
        "idValidDt":"","idIssueNation":"","nationality":"",
        "infCarrierName":"","insurance":false,"insureInfos":[],
        "mobile":"13544474741","contactInfo":"",
        "contacts":"mobile","cardId":"","paxType":"ADT","paxName":"范加尔",
        "paxNameCn":"","paxNameFirst":"","paxNameLast":"","isBeneficariesAssigned":false,
        "isBeneficiary":"","paxOrigin":"0",
        "idDetails":[{"id":"","idNo":"110101197903074756","idType":"NI"}]}]

        showbooking
        [{"uuid":0,"benePaxListIndex":"","birthday":"","docaCity":"Park","docaNationCode":"",
        "docaPostCode":"19019","docaState":"PA","docaStreet":"Shinfield Road Reading RG2 7ED",
        "email":"","ffpAirline":"","ffpLevel":"","ffpNo":"",
        "gender":"M","idNo":"110101197903074756","idType":"NI","id":"","idValidDt":"",
        "idIssueNation":"","nationality":"","infCarrierName":"","insurance":false,"insureInfos":[],
        "mobile":"13544474741","contactInfo":"",
        "contacts":"mobile","cardId":"","paxType":"ADT","paxName":"范加尔",
        "paxNameCn":"","paxNameFirst":"","paxNameLast":"","isBeneficariesAssigned":false,
        "isBeneficiary":"","paxOrigin":"0",
        "idDetails":[{"id":"","idNo":"110101197903074756","idType":"NI"}]}]
        """
        if not pax_info.is_en_name() and pax_info.card_ni:
            # 身份证不能随机，必须指定，否则无法享受会员价
            pax_data.append({"uuid": 0,
                             "benePaxListIndex": "",
                             "birthday": '',
                             "docaCity": "Park",
                             "docaNationCode": "",
                             "docaPostCode": "19019",
                             "docaState": "PA",
                             "docaStreet": "Shinfield Road Reading RG2 7ED",
                             "email": "",
                             "ffpAirline": "",
                             "ffpLevel": "",
                             "ffpNo": "",
                             "gender": pax_info.gender, # ！！！如果性别错误，东航会报错
                             "idNo": pax_info.card_ni,
                             "idType": 'NI',
                             "id": "",
                             "idValidDt": "",
                             "idIssueNation": "",
                             "nationality": "",
                             "infCarrierName": '',
                             "infCarrierIdNo": '',
                             "insurance": False,
                             "insureInfos": [],
                             "mobile": mobile,
                             "contactInfo": "",
                             "contacts": "mobile",
                             "cardId": "",
                             "paxType": 'ADT',
                             "paxName": pax_info.name,
                             "paxNameCn":"",
                             "paxNameFirst": "",
                             "paxNameLast": "",
                             "isBeneficariesAssigned": False,
                             "isBeneficiary": "",
                             "paxOrigin": "0",
                             "idDetails": [{"id": "", "idNo": pax_info.card_ni, "idType": 'NI'}]})
        else:

            pax_data.append({"uuid": 0,
                             "benePaxListIndex": "",
                             "birthday": pax_info.birthdate,
                             "docaCity": "Park",
                             "docaNationCode": "",
                             "docaPostCode": "19019",
                             "docaState": "PA",
                             "docaStreet": "Shinfield Road Reading RG2 7ED",
                             "email": email,
                             "ffpAirline": "",
                             "ffpLevel": "",
                             "ffpNo": "",
                             "gender": pax_info.gender,
                             "idNo": pax_info.card_pp,
                             "idType": 'PP',
                             "id": "",
                             "idValidDt": '2020-05-21',
                             "idIssueNation": pax_info.card_issue_place,
                             "nationality": pax_info.nationality,
                             "infCarrierName": '',
                             "infCarrierIdNo": '',
                             "insurance": False,
                             "insureInfos": [],
                             "mobile": mobile,
                             "contactInfo": "",
                             "contacts": "mobile",
                             "cardId": "",
                             "paxType": 'ADT',
                             "paxName": "",
                             "paxNameCn": Random.gen_full_name(),
                             "paxNameFirst": pax_info.first_name,
                             "paxNameLast": pax_info.last_name,
                             "isBeneficariesAssigned": False,
                             "isBeneficiary": "",
                             "paxOrigin": "",
                             "idDetails": [{"id": "", "idNo": pax_info.card_pp, "idType": 'PP', "idValidDt": '2020-05-21',
                                            "idIssueNation": pax_info.card_issue_place, }]})
        data = {
            'allPaxInfo': json.dumps(pax_data,ensure_ascii=False),
            'sessionVersion': session_version

        }
        Logger().debug('allpaxinfo %s' % pax_data)
        http_conn = http_session.request(method='POST', url=url, data=data, verify=False)
        result = http_conn.content

        Logger().info("================== session version request {}= =============".format(result))

        # 更新联系人信息
        """
        在不存储联系人的情况下自己构造请求
        {"contactName":"刘志","contactMobile":"15216666047","contactEmail":"fdaljrj@tongdun.org","id":""}
        """
        gevent.sleep(0.2)
        Logger().info('update contactinfo')
        url = 'http://www.ceair.com/otabooking/paxinfo-input!checkContactInfo.shtml'
        # 带有ID需要先获取ID

        # TODO 此处写死为指定手机号码

        contact_pax = {
            "contactName": Random.gen_full_name(),
            "contactMobile": TBG.global_config['OPERATION_CONTACT_MOBILE'],
            "contactEmail": email, "id": ""
        }
        data = {
            'contactInfo': json.dumps(contact_pax),
            'sessionVersion': session_version
        }
        http_conn = http_session.request(method='POST', url=url, data=data, verify=False)
        result = http_conn.content
        Logger().info('update contactinfo result %s' % result)

        # 确认订票信息
        gevent.sleep(0.2)
        Logger().info('showBookingInfoNew')
        url = 'http://www.ceair.com/otabooking/paxinfo-input!showBookingInfoNew.shtml'
        data = {
            'allPaxInfo': json.dumps(pax_data,ensure_ascii=False),
            'contactInfo': json.dumps(contact_pax,ensure_ascii=False),
            'sessionVersion': session_version,
            'nonmember': 0
        }
        http_conn = http_session.request(method='POST', url=url, data=data, verify=False)
        result = http_conn.content
        Logger().info('confirm booking result %s' % result)
        """
        您所填写的乘机人手机号并非本人实名认证的手机号，请修改。
        register result {u'resultCode': u'RRV2003', u'resultMsg': u'\u60a8\u6240\u586b\u5199\u7684\u4e58\u673a\u4eba\u624b\u673a\u53f7\u5e76\u975e\u672c\u4eba\u5b9e\u540d\u8ba4\u8bc1\u7684\u624b\u673a\u53f7\uff0c\u8bf7\u4fee\u6539\u3002', u'ffpNo': None}
        """
        if result == 'success|CHANGELOGIN':
            Logger().info('success|CHANGELOGIN')
            need_verify_mobile = False
            if not pax_info.is_en_name() and pax_info.card_ni:
                # 国内注册
                gevent.sleep(0.2)
                Logger().info('chinese register logic ')
                url = 'http://www.ceair.com/member/auth!register.shtml'
                pax_no = pax_info.card_ni
                data = {
                    'paxNo': pax_no,
                    'mobile': mobile,
                    'paxName': pax_info.name,
                    'token':"APDIDJS_donghang_5a6bf0a612678cc1ff4f7111ed8e0c52"
                }
                http_conn = http_session.request(method='POST', url=url, data=data, verify=False)
                result = http_conn.to_json()
                Logger().info('register result %s' % result)

                if result['resultCode'] == '005':
                    need_verify_mobile = True
                elif result['resultCode'] == 'RRV2003':
                    # 手机实名认证失败，此处是跟东航自己的库进行对比，并非对接接口
                    # 2018-10-18 此处赞认为更换证件号也无效，仅注册一次
                    raise RegisterCritical('ffp has already exists', err_code='RRV2003')
            else:
                need_verify_mobile = True

            if need_verify_mobile:
                # 国际证件注册
                # 发送手机验证码
                """
                http://www.ceair.com/booking/verification-code!sendVerificationCode.shtml?_=1532583510175&telNum=15216666047
                success
                """
                @sms_lock()
                def send_mobile_code(mobile_info,sms_func):
                    """
                    本函数必须传递两个参数，mobile_info和sms_func，否则会报错
                    :param mobile_info:
                    :return:
                    """

                    url = 'http://www.ceair.com/booking/verification-code!sendVerificationCode.shtml?_=%s&telNum=%s' % (Time.timestamp_ms(), mobile_info['mobile'])
                    http_conn = http_session.request(method='GET', url=url)
                    result = http_conn.content

                    if result == 'success':

                        Logger().info('mobile verify code send success %s ' % mobile_info['mobile'])
                        # 接收手机短信
                        return Smser().get_ceair_booking_verify_code(mobile_info=mobile_info)
                    else:
                        raise RegisterException('mobile code operation fail')

                checkcodes = send_mobile_code(mobile_info=self.mobile_info,sms_func='get_ceair_booking_verify_code')
                sms_success = False
                for checkcode in checkcodes:
                    # 验证手机验证码
                    Logger().info('sms verify code %s' % checkcode)
                    """
                    http://www.ceair.com/booking/verification-code!checkValidationCode.shtml?_=1532583540174&telNum=15216666047&checkCode=95
                    success
                    """

                    url = 'http://www.ceair.com/booking/verification-code!checkValidationCode.shtml?_=%s&telNum=%s&checkCode=%s' % (
                        Time.timestamp_ms(), self.mobile_info['mobile'], checkcode)
                    http_conn = http_session.request(method='GET', url=url)
                    result = http_conn.content

                    if result == 'success':
                        sms_success = True
                        Logger().info('sms code recieved and crack success')
                        break

                if sms_success:
                    Logger().info('mobile verify code verify success')
                else:
                    raise RegisterException('sms code wrong')

                # 注册会员
                gevent.sleep(0.2)

                url = 'http://www.ceair.com/member/auth!register.shtml'
                if not pax_info.is_en_name() and pax_info.card_ni:
                    pax_no = pax_info.card_ni
                else:
                    pax_no = pax_info.card_pp
                data = {
                    'paxNo': pax_no,
                    'mobile': mobile,
                    'paxName': pax_info.name,
                }
                Logger().info('auth!register.shtml result %s' % data)
                http_conn = http_session.request(method='POST', url=url, data=data, verify=False)
                result = http_conn.to_json()
                Logger().info('register result %s' % result)

            if result['resultCode'] == '001':
                Logger().info('register success')
                # 查看ffp_no
                """
                http://ecrm.ceair.com/traveller/optmember/member-info!QueryMemberInfo.shtml?_=1532583867575&
                {"message":"","memberSource":1,"ecUser":{"address1":"","address2":"","addressCode1":"","addressCode2":"","birthDate":"1978-05-03","country1":"","country2":"","county1":"","county2":"","crtDt":{"date":26,"day":4,"hours":13,"minutes":39,"month":6,"nanos":0,"seconds":15,"time":1532583555000,"timezoneOffset":-480,"year":118},"ecUserExtention":{"enrolmentDate":"26-Jul-2018 12:00:00"},"email":"","ffpNo":653021617616,"headPic":"","historyPid":"","id":606540290,"identificationSet":[],"mobileNo":"13588854458","name":"EQFDSAFD/EQFDSAF","nameCn":"","nameEn":"EQFDSAF","namePy":"","nationcode":"","passportId":606540289,"points":0,"preferenceDtoSet":[],"province1":"","province2":"","remark":"","sex":"M","surnameCn":"","surnameEn":"EQFDSAFD","telephone":"","tier":"STD","title":"","transactionPasswordStatus":0,"userPoints":0,"userStatus":1,"username":"653021617616"}}
                """
                gevent.sleep(0.2)
                url = 'http://ecrm.ceair.com/traveller/optmember/member-info!QueryMemberInfo.shtml?_=%s&' % Time.timestamp_ms()
                headers = {'Referer': 'http://ecrm.ceair.com/myceair/myinfo.html'}
                http_conn = http_session.request(method='GET', url=url, headers=headers)
                Logger().debug('last step result %s' % http_conn.content)
                result = http_conn.to_json()
                if result['ecUser']['ffpNo']:
                    ffp_no = result['ecUser']['ffpNo']
                    ffp_account_info.username = str(ffp_no)

                    ffp_account_info.provider = self.provider
                    if not pax_info.is_en_name() and pax_info.card_ni:
                        ffp_account_info.reg_pid = pax_info.card_ni
                        ffp_account_info.reg_card_type = 'NI'
                        ffp_account_info.password = pax_info.card_ni[6:14]
                    else:
                        ffp_account_info.reg_passport = pax_info.card_pp
                        ffp_account_info.reg_card_type = 'PP'
                        ffp_account_info.password = pax_info.birthdate.replace('-', '')
                    ffp_account_info.reg_birthdate = pax_info.birthdate
                    ffp_account_info.reg_gender = pax_info.gender
                    ffp_account_info.mobile = mobile
                    return ffp_account_info

            else:
                raise RegisterException('last step error')

        elif 'success|CHANGELOGIN:{"' in result:
            # 代表已经注册过，无法继续注册,本分支用于尝试是否默认密码可以登录，如果不能登录则更换证件进行注册
            # 护照，更换护照后一位，身份证更换身份证后两位
            Logger().info('changelogin try login ')
            ffp_no_exp = re.compile(r'"ffpNo":"(\d*)"')
            exp_result = ffp_no_exp.findall(result)
            if exp_result:

                ffp_no = exp_result[0]
                Logger().info('changelogin ffp_no %s' % ffp_no)
                ffp_account_info_tmp2 = FFPAccountInfo()
                ffp_account_info_tmp2.username = str(ffp_no)  # 任意指定一个会员账号
                ffp_account_info_tmp2.password = pax_info.birthdate.replace('-', '')
                try:
                    self.login(ffp_account_info=ffp_account_info_tmp2)
                    ffp_account_info.username = str(ffp_no)

                    ffp_account_info.provider = self.provider
                    if not pax_info.is_en_name() and pax_info.card_ni:
                        ffp_account_info.reg_pid = pax_info.card_ni
                        ffp_account_info.reg_card_type = 'NI'
                        ffp_account_info.password = pax_info.card_ni[6:14]
                    else:
                        ffp_account_info.reg_passport = pax_info.card_pp
                        ffp_account_info.reg_card_type = 'PP'
                        ffp_account_info.password = pax_info.birthdate.replace('-', '')
                    ffp_account_info.reg_birthdate = pax_info.birthdate
                    ffp_account_info.reg_gender = pax_info.gender
                    ffp_account_info.mobile = mobile
                    return ffp_account_info
                except LoginException as e:
                    pass
                except Exception as e:
                    Logger().error('default pwd login error')
            raise RegisterCritical('ffp has already exists',err_code='FFP_EXISTS')
        else:
            raise RegisterException('success|CHANGELOGIN error')


class Ceair2Fake(Ceair2):
    """
    非真实支付的供应商
    """
    timeout = 15  # 请求超时时间
    provider = 'ceair'  # 子类继承必须赋
    provider_channel = 'ceair_web_2_fake'  # 子类继承必须赋
    operation_product_type = 'VISA100+会员'
    operation_product_mode = 'A2A'
    force_autopay = False

    def _pay(self, order_info, http_session,pay_dict):

        provider_order_id = order_info.provider_order_id
        Logger().info('provider_order_id %s' % provider_order_id)
        Logger().info('paying ..... waiting')
        TBG.redis_conn.insert_value('%s_%s' % (self.provider_channel, provider_order_id), 'ISSUE_SUCCESS')

        gevent.sleep(2)
        return None

    def _check_order_status(self, http_session, ffp_account_info, order_info):
        """
        检查订单状态
        :param http_session:
        :param order_id:
        :return: 返回订单状态
        航司订单状态
        {10050:{tips:"等待支付",className:"waitPayB"},
        10051:{tips:"支付成功",className:"waitPayG"},
        10052:{tips:"交易处理中",className:"waitPayG"},
        10053:{tips:"差错退款",className:"warning"},
        10054:{tips:"交易成功",className:"success"},
        10055:{tips:"交易异常",className:"error"},
        10056:{tips:"交易取消",className:"cancel"},
        10057:{tips:"等待确认",className:"waitPay"},
        10058:{tips:"预定失败",className:"cancel"},
        10059:{tips:"退票",className:"warning"}，

        """
        status_map = {
            '10050': 'BOOK_SUCCESS_AND_WAITING_PAY',
            '10051': 'PAY_SUCCESS',
            '10052': 'PAY_SUCCESS',
            '10053': 'ISSUE_FAIL',
            '10054': 'ISSUE_SUCCESS',
            '10055': 'ISSUE_FAIL',
            '10056': 'MANUAL_CANCEL',
            '10057': 'BOOK_SUCCESS_AND_WAITING_PAY',
            '10058': 'ISSUE_FAIL',
            '10059': 'MANUAL_RERUND',

        }
        order_info.provider_order_status = 'LOGIN_FAIL'
        http_session = self.login(ffp_account_info=ffp_account_info)
        # 检查订单状态
        url = 'http://ecrm.ceair.com/traveller/optmember/order-query!queryOrderDetails.shtml'
        data = {
            'orderNo': order_info.provider_order_id,
            'orderType': 'AIR'
        }
        headers = {'Referer': 'http://ecrm.ceair.com/order/detail.html'}
        http_conn = http_session.request(method='POST', url=url, data=data, verify=False, headers=headers)
        encrypt_content = http_conn.content
        content_key = json.loads(http_conn.response_headers[0]).get('Content-Key')
        Logger().info("========== order detail content key:{}".format(content_key))
        des_key, des_iv = content_key.split(',')
        des_obj = DES.new(des_key, DES.MODE_CBC, des_iv)
        decrypt_content = des_obj.decrypt(base64.b64decode(encrypt_content))
        Logger().info("========== encrypt content:{}".format(encrypt_content))
        Logger().info("========== decrypt content:{}".format(decrypt_content))
        result = json.loads(re.findall(r'{.*}', decrypt_content)[0])
        err = result['errorResult']
        if err:
            raise CheckOrderStatusException(json.dumps(err))
        else:

            gevent.sleep(2)
            provider_order_status = TBG.redis_conn.get_value('%s_%s' % (self.provider_channel, order_info.provider_order_id))
            if provider_order_status == 'ISSUE_SUCCESS':

                order_info.provider_order_status = 'ISSUE_SUCCESS'
                if order_info.provider_order_status == 'ISSUE_SUCCESS':
                    for pax_info in order_info.passengers:
                        pax_info.ticket_no = Random.gen_num(8)
                        order_info.pnr_code = Random.gen_littlepnr()
                        Logger().info('faker ticket_no %s' % pax_info.ticket_no)
                Logger().info('faker pnr_code %s' % order_info.pnr_code)




class CeairH5(Ceair2):
    """
    不该证件号的注册
    """
    timeout = 15  # 请求超时时间
    provider = 'ceair'  # 子类继承必须赋
    provider_channel = 'ceair_web_h5'  # 子类继承必须赋
    operation_product_type = 'VISA100+会员'
    operation_product_mode = 'A2A'

    def _register(self, http_session, pax_info, ffp_account_info):
        self._h5_register()