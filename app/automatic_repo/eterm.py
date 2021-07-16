# coding=utf8

import time
import json
import random
import re
import gevent
import datetime
from bs4 import BeautifulSoup
from ..controller.http_request import HttpRequest
from bs4 import BeautifulSoup
from urllib import quote
from .base import ProvderAutoBase
from ..utils.logger import Logger
from ..utils.util import cn_name_to_pinyin,RoutingKey
from ..controller.captcha import CaptchaCracker
from ..utils.exception import *
from ..utils.util import Time, Random, md5_hash, convert_utf8,modify_pp,modify_ni, simple_decrypt, simple_encrypt
from ..dao.iata_code import IATA_CODE
from ..dao.models import *
from ..dao.internal import *
from ..utils.triple_des_m import desenc
from ..controller.smser import Smser
from app import TBG
from ..utils.blowfish import Blowfish
from ..controller.thirdparty_aux import DomesticTaxAux

class Eterm(ProvderAutoBase):

    timeout = 15  # 请求超时时间
    provider = 'eterm'  # 子类继承必须赋
    provider_channel = 'eterm_provider'  # 子类继承必须赋
    operation_product_type = '会员折扣'  # 运价类型：0: GDS公布运价 1:GDS私有运价 2:航司官网产品  3:廉价航司产品 4:特价产品
    operation_product_mode = 'A2A'
    pay_channel = '99BILL'
    force_autopay = False # 强制自动支付
    verify_realtime_search_count = 1
    is_display = True
    is_order_directly = True
    trip_type_list = ['OW', 'RT']
    no_flight_ttl = 3600 * 3 # 无航班缓存超时时间设定


    CACHE_PR_CONFIG = {
        1: {'cabin_expired_time': 3600 * 12, 'cabin_attenuation': 3,'fare_expired_time':86400 * 30},
        2: {'cabin_expired_time': 3600 * 3, 'cabin_attenuation': 2,'fare_expired_time':86400 * 20},
        3: {'cabin_expired_time': 60 * 60 * 1, 'cabin_attenuation': 1,'fare_expired_time':86400 * 10},
        4: {'cabin_expired_time': 60 * 40, 'cabin_attenuation': 1,'fare_expired_time':86400 * 5},
        5: {'cabin_expired_time': 60 * 30, 'cabin_attenuation': 0,'fare_expired_time':86400},

    }
    search_interval_time = 0


    def __init__(self):
        super(Eterm, self).__init__()

    def _register(self, http_session, pax_info, ffp_account_info):

        modified_card_no = None
        for x in range(0,10):
            # 尝试三次

            try:
                ffp_account_info = self._sub_register(http_session=http_session,pax_info=pax_info,ffp_account_info=ffp_account_info)
                return ffp_account_info
            except RegisterCritical as e:
                Logger().debug('e.err_code %s' %e.err_code)
                if not e.err_code == 'FFP_EXISTS':
                    raise
            # 账号经过无法注册也无法登陆,修改证件号重新注册
            if pax_info.used_card_type == 'NI':
                # 身份证修改
                modified_card_no = modify_ni(pax_info.card_ni)
                pax_info.used_card_no = modified_card_no
                pax_info.card_ni = modified_card_no
            else:
                modified_card_no = modify_pp(pax_info.card_pp)

                modified_card_no = str(random.randint(10000000, 99999999))
                pax_info.used_card_no = modified_card_no
                pax_info.card_pp = modified_card_no
            Logger().sinfo('start modified_card_no %s register' % modified_card_no)
        else:
            raise RegisterException

    def _sub_register(self, http_session, pax_info, ffp_account_info):
        """
        注册模块
        :param pax_info:
        :return: ffp account info


        u'\u5165\u4f1a\u6e20\u9053\u53f7\u4e3a\u7a7a' 曾经报错：入会渠道号为空
        """
        if pax_info.card_ni:
            ffp_account_info.reg_pid = pax_info.card_ni
            ffp_account_info.reg_card_type = 'NI'
            save_card_no = pax_info.card_ni
        else:
            ffp_account_info.reg_passport = pax_info.card_pp
            ffp_account_info.reg_card_type = 'PP'
            save_card_no = pax_info.card_pp

        Logger().info('fake registering wait..... pax_info %s'%pax_info)
        gevent.sleep(2)
        # fake_account = TBG.redis_conn.get_value('fake_account_%s' % (save_card_no))
        # if fake_account:
        #     raise RegisterCritical(err_code='FFP_EXISTS')
        # else:
        ffp_account_info.username = str(Random.gen_num(8))
        ffp_account_info.password = str(Random.gen_num(8))
        ffp_account_info.provider = self.provider

        ffp_account_info.reg_birthdate = pax_info.birthdate
        ffp_account_info.reg_gender = pax_info.gender
        # TBG.redis_conn.insert_value('fake_account_%s' % (save_card_no),'xxx',ex=86400)
        return ffp_account_info

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

        Logger().info('eterm booking start')
        gevent.sleep(2)
        if not order_info.assoc_search_routings:
            self.flight_search(search_info=order_info)
        # if not order_info.ffp_account:
        #     # 如果没有账号才需要注册
        #     try:
        #         paxs = [x for x in order_info.passengers if x.current_age_type(from_date=order_info.from_date, is_aggr_chd_adt=True) == 'ADT']
        #         if paxs:
        #             order_info.provider_order_status = 'REGISTER_FAIL'
        #             ffp_account_info = self.register(http_session=http_session, pax_info=order_info.passengers[0], flight_order_id=order_info.flight_order_id,sub_order_id=order_info.sub_order_id)
        #         else:
        #             raise RegisterCritical('NO ADT FOUND ,CAN NOT REGISTER')
        #     except Critical as e:
        #         raise
        #     order_info.ffp_account = ffp_account_info

        order_info.provider_price = 0.0

        for pax in order_info.passengers:
            Logger().debug('used_card_no %s selected_card_no %s'% (pax.used_card_no,pax.selected_card_no))

        # 增加手机验证码测试环节
        order_id = Random.gen_num(8)
        order_info.provider_order_id = str(order_id)
        order_info.provider_order_status = 'BOOK_SUCCESS_AND_WAITING_PAY'
        Logger().info('booking success')
        Logger().info('orderNo %s' % order_id)
        TBG.redis_conn.insert_value('%s_%s' % (self.provider_channel, order_info.provider_order_id), order_info.provider_order_status,ex=86400)
        return order_info

    def _flight_search(self, http_session, search_info):
        """
        航班爬取模块，
        TODO :目前只考虑单程

        :return:
        """

        if search_info.routing:
            search_info.assoc_search_routings.append(search_info.routing)
        return search_info

    def _check_order_status(self, http_session, ffp_account_info, order_info):
        """
        检查订单状态
        :param http_session:
        :param order_id:
        :return: 返回订单状态

        """
        Logger().info('eterm order status checking ')
        gevent.sleep(2)
