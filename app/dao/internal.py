#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, too-many-arguments, broad-except, anomalous-backslash-in-string
# pylint: disable=missing-docstring, line-too-long, too-few-public-methods
"""
# @Author  : wxt
# @Software: PyCharm
"""

import copy
import re
import datetime
from .models import *
from pony.orm import db_session,flush,commit
from ..dao.iata_code import IATA_CODE
from ..utils.util import Random,Time,convert_unicode,md5_hash,RoutingKey
from ..controller.order_status_manager import OrderStatusManager
from ..utils.exception import *
from ..utils.logger import Logger

class MixInfo(dict):
    # TODO 带参数创建实例功能
    # 时间格式无法序列化
    def __setattr__(self, name, value):
        self[name] = value

    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            raise AttributeError("No such attribute: " + name)

    def to_dict(self):
        # TODO 序列化功能需要加强，
        pass



class SearchInfo(MixInfo):
    """
    整合 FlightRouting 和 FlightOrder 两个模型

    provider_search_result
    HIGH_REQ_LIMIT  频率限制
    NOFLIGHT 无航班
    REQPARAM_ERROR 请求参数错误
    ERROR 未知错误
    """
    def __init__(self,**kwargs):
        self.assoc_search_routings = []  # 关联查询航班
        self.assoc_order_routing_key = ''  # 用于订单的关联key
        self.extra_data = None  # 存储额外信息
        self.extra_data_2 = None # 存储额外信息
        self.extra_data_3 = None # 存储额外信息
        self.search_time = None #搜索时间
        self.ota_name = None
        self.pr = 0
        self.return_details = ''
        self.return_status = ''
        self.is_already_competion = False
        self.task_id = None
        self.total_latency = 0
        self.fare_operation = ''
        self.search_finished = False  # 是否完成搜索结果的填充
        self.flight_order_id = ''
        self.verify_routing_key = ''
        self.ota_work_flow = ''
        self.notice_pay_status = ''
        self.notice_issue_status = ''
        self.order_detail_status = ''
        self.cache_source = ''
        self.is_modified_card_no = 0
        self.cabin_grade = ''
        self.allow_cabin_downgrade = 0
        self.request_id = ''

        self.crawl_primary_task_id = None  # 爬虫主任务ID

        #涉及爬虫、权重
        self.task_id = None

        self.pnr_code = ''
        self.ota_order_id = ''

        # 支付宝订单id
        self.out_trade_no = ''
        # 供应商手续费
        self.provider_fee = 0.0

        self.ota_custom_route_strategy = []
        self.rts_search_tries = 0

        self.flight_order_instance = None
        object.__setattr__(self, "flight_order_keys", [])
        # self.flight_order_keys = []
        if kwargs:
            if kwargs.has_key('assoc_search_routings'):
                asr_list = []
                for asr in kwargs['assoc_search_routings']:
                    asr_list.append(FlightRoutingInfo(**asr))
                setattr(self, 'assoc_search_routings', asr_list)

            if kwargs.has_key('notice_pay_status'):
                self.notice_pay_status = kwargs['notice_pay_status']

            if kwargs.has_key('notice_issue_status'):
                self.notice_pay_status = kwargs['notice_issue_status']

            if kwargs.has_key('order_detail_status'):
                self.order_detail_status = kwargs['order_detail_status']
            if kwargs.has_key('task_id'):
                self.task_id = kwargs['task_id']
            if kwargs.has_key('pr'):
                self.pr = kwargs['pr']
            if kwargs.has_key('fare_operation'): # 运价所采用规则
                self.fare_operation = kwargs['fare_operation']
            if kwargs.has_key('return_details'):
                self.return_details = kwargs['return_details']
            if kwargs.has_key('ota_work_flow'):
                self.ota_work_flow = kwargs['ota_work_flow']
            if kwargs.has_key('verify_routing_key'):
                self.verify_routing_key = kwargs['verify_routing_key']

            if kwargs.has_key('total_latency'):
                self.total_latency = kwargs['total_latency']

            if kwargs.has_key('provider_search_raw_code'):
                self.provider_search_raw_code = kwargs['provider_search_raw_code']

            if kwargs.has_key('cache_source'):
                self.cache_source = kwargs['cache_source']

            if kwargs.has_key('is_modified_card_no'):
                self.is_modified_card_no = kwargs['is_modified_card_no']

            if kwargs.has_key('out_trade_no'):
                self.out_trade_no = kwargs['out_trade_no']

            if kwargs.has_key('create_time'):
                self.create_time = kwargs['create_time']

            if kwargs.has_key('allow_cabin_downgrade'):
                self.allow_cabin_downgrade = kwargs['allow_cabin_downgrade']

            if kwargs.has_key('crawl_primary_task_id'):
                self.crawl_primary_task_id = kwargs['crawl_primary_task_id']

            if kwargs.has_key('ota_custom_route_strategy'):
                self.ota_custom_route_strategy = kwargs['ota_custom_route_strategy']

            if kwargs.has_key('rk_info'):
                self.rk_info = copy.deepcopy(kwargs['rk_info'])

            if kwargs.has_key('ota_name'):
                self.ota_name = kwargs['ota_name']

            if kwargs.has_key('request_id'):
                self.request_id = kwargs['request_id']

        for k,v in dictobj(FlightOrder).iteritems():
            setattr(self,k,v)
            if kwargs.has_key(k):
                if str(type(kwargs[k])) == "<type 'datetime.date'>" :
                    setattr(self, k, kwargs[k].strftime('%Y-%m-%d'))
                elif str(type(kwargs[k])) == "<type 'datetime.datetime'>" :
                    setattr(self, k, kwargs[k].strftime('%Y-%m-%d %H:%M:%S'))

                else:
                    setattr(self, k, kwargs[k])
            self.flight_order_keys.append(k)
        self.is_saved = False


    def attr_competion(self):
        """
        属性补全，需要显式调用
        :return:
        """

        # 补全是否为国际航班
        # Logger().sdebug('attr_competion')
        if not self.is_already_competion:
            from_air_info = None
            if IATA_CODE.has_key(self.from_airport.upper()):
                from_air_info = IATA_CODE[self.from_airport.upper()]
                self.from_country = from_air_info['cn_country']
                self.from_city = from_air_info['cn_city']

            to_air_info = None
            if IATA_CODE.has_key(self.to_airport.upper()):
                to_air_info = IATA_CODE[self.to_airport.upper()]

                self.to_country = to_air_info['cn_country']
                self.to_city = to_air_info['cn_city']

            if to_air_info and from_air_info:
                if not from_air_info['cn_country'] == '中国' and not to_air_info['cn_country'] == '中国':
                    self.routing_range = 'O2O'
                elif from_air_info['cn_country'] == '中国' and not to_air_info['cn_country'] == '中国':
                    self.routing_range = 'I2O'
                elif not from_air_info['cn_country'] == '中国' and to_air_info['cn_country'] == '中国':
                    self.routing_range = 'O2I'
                elif from_air_info['cn_country'] == '中国' and to_air_info['cn_country'] == '中国':
                    self.routing_range = 'I2I'

            if self.trip_type == 'OW':
                self.ret_date = ''
            self.is_already_competion = True

    def save(self,lazy_flush=False):
        if not self.is_saved:
            __ = {k:convert_unicode(getattr(self,k)) for k in self.flight_order_keys}
            self.flight_order_instance = FlightOrder(**__)
            if not lazy_flush:
                flush()
                self.flight_order_id = self.flight_order_instance.id
            self.is_saved = True
        return self.flight_order_instance

class FlightRoutingInfo(MixInfo):
    def __init__(self,**kwargs):
        self.flight_routing_instance = None
        object.__setattr__(self, "flight_routing_keys", [])
        # self.flight_routing_keys = []
        self.flight_routing_id = ''
        self.data_source = ''
        self.reference_adult_price = 0  # 参考成人价（次低价），如果没有次低价，不要赋值
        self.reference_adult_tax = 0  # 参考成人价（次低价），如果没有次低价，不要赋值
        self.is_include_operation_carrier = 0
        for k,v in dictobj(FlightRouting).iteritems():
            setattr(self,k,v)
            self.flight_routing_keys.append(k)
            if kwargs.has_key(k):
                if str(type(kwargs[k])) == "<type 'datetime.date'>" :
                    setattr(self, k, kwargs[k].strftime('%Y-%m-%d'))
                elif str(type(kwargs[k])) == "<type 'datetime.datetime'>" :
                    setattr(self, k, kwargs[k].strftime('%Y-%m-%d %H:%M:%S'))
                elif k == 'from_segments':
                    fs_list = []
                    for fs in kwargs[k]:
                        fs_list.append(FlightSegmentInfo(**fs))
                    setattr(self, k, fs_list)
                elif k == 'ret_segments':
                    rs_list = []
                    for rs in kwargs[k]:
                        rs_list.append(FlightSegmentInfo(**rs))
                    setattr(self, k, rs_list)
                else:
                    setattr(self,k,kwargs[k])
        if kwargs:
            if kwargs.has_key('data_source'): # 运价所采用规则
                self.data_source = kwargs['data_source']

            if kwargs.has_key('reference_adult_price'):
                self.reference_adult_price = kwargs['reference_adult_price']

            if kwargs.has_key('reference_adult_tax'):
                self.reference_adult_tax = kwargs['reference_adult_tax']

            if kwargs.has_key('is_valid_cabin'):
                self.is_valid_cabin = kwargs['is_valid_cabin']

        self.is_saved = False

    def save(self,lazy_flush=False):
        if not self.is_saved:
            __ = {k: (getattr(self,k)) for k in self.flight_routing_keys}
            __['from_segments'] = [segment.save(lazy_flush=False) for segment in __['from_segments']]
            __['ret_segments'] = [segment.save(lazy_flush=False) for segment in __['ret_segments']]
            self.flight_routing_instance = FlightRouting(**__)
            if not lazy_flush:
                flush()
                self.flight_routing_id = self.flight_routing_instance.id
            self.is_saved = True
        return self.flight_routing_instance

class FlightSegmentInfo(MixInfo):
    def __init__(self,**kwargs):
        self.flight_segment_instance = None
        object.__setattr__(self, "flight_segment_keys", [])
        # self.flight_segment_keys = []
        self.flight_segment_id = ''
        self.baggage_info = "{}"
        self.change_info = "{}"
        self.refund_info = "{}"
        for k, v in dictobj( FlightSegment).iteritems():
            setattr(self, k, v)
            if kwargs.has_key(k):

                if str(type(kwargs[k])) == "<type 'datetime.date'>" :
                    setattr(self, k, kwargs[k].strftime('%Y-%m-%d'))
                elif str(type(kwargs[k])) == "<type 'datetime.datetime'>" :
                    setattr(self, k, kwargs[k].strftime('%Y-%m-%d %H:%M:%S'))
                else:
                    setattr(self,k,kwargs[k])
            self.flight_segment_keys.append(k)

        self.is_saved = False

    def save(self, lazy_flush=False):
        if not self.is_saved:
            __ = {k: getattr(self, k) for k in self.flight_segment_keys}
            self.flight_segment_instance =  FlightSegment(**__)
            if not lazy_flush:
                flush()
                self.flight_segment_id = self.flight_segment_instance.id
            self.is_saved = True
        return self.flight_segment_instance

    @property
    def selected_cabin(self):
        """
        如果有虚拟仓则输出虚拟仓舱位
        :return:
        """
        if self.virtual_cabin:
            return self.virtual_cabin
        else:
            return self.cabin


class OrderInfo(SearchInfo):
    """
    order 输入 输出都放在此class
    """

    def __init__(self,**kwargs):
        self.save_disabled =  False  # 如果通过load的方式加载的数据就不能再save了
        self.pnr_code = ''
        self.ota_order_id = ''
        self.cabin_grade = ''
        self.provider_order_status = ''
        super(OrderInfo, self).__init__(**kwargs)

        if not kwargs:
            self.assoc_order_id = Random.gen_hash()[:16].upper()

    def check_providers_status(self):
        if OrderStatusManager.verify_format(self.providers_status):
            OrderStatusManager.manual_intervention(self.providers_status,self)
        else:
            raise OrderStatusException

    def gen_rkey_pax_hash(self):
        # 生成hash provider + un_key + pax_used_card_no list ascii asc
        card_str = "|".join(sorted([pax.used_card_no for pax in self.passengers]))
        un_key = RoutingKey.trans_un_key(self.verify_routing_key,is_unserialized=False,is_encrypted=True)
        self.rkey_pax_hash = md5_hash('%s|%s|%s' % (self.provider, un_key, card_str))
        return self.rkey_pax_hash


    def save(self,lazy_flush=False):
        if not self.save_disabled :
            if not self.is_saved:

                if not self.rkey_pax_hash:
                    self.gen_rkey_pax_hash()
                # 存储 order
                __ = {k:convert_unicode(getattr(self,k)) for k in self.flight_order_keys}
                __.pop('sub_order',None)
                __['passengers'] = [pax.save(lazy_flush=True)[1] for pax in __['passengers'] if pax.save(lazy_flush=True)[1] != None]
                __['contacts'] = [contact.save(lazy_flush=True) for contact in __['contacts']]
                if __['routing'] and isinstance(__['routing'],FlightRoutingInfo) :
                    __['routing'] = __['routing'].save(lazy_flush=True)
                if __['ffp_account']:
                    __['ffp_account'] = __['ffp_account'].save(lazy_flush=True)
                if __.has_key('ret_date') and (not __['ret_date'] or __['ret_date'] == 'None'):
                    __.pop('ret_date', None)
                self.flight_order_instance = FlightOrder(**__)
                # 存储账号关系
                if not lazy_flush:
                    flush()
                    commit()
                    self.flight_order_id = self.flight_order_instance.id
                self.is_saved = True
            return self.flight_order_instance

class SubOrderInfo(SearchInfo):
    def __init__(self,**kwargs):
        """
        传入的routing\pax\contact\等只能是ID或者是model实例，这里不会进行实例化，只做绑定id的操作
        :param kwargs:
        """
        self.sub_order_instance = None
        object.__setattr__(self, "sub_order_keys", [])
        # self.sub_order_keys = []
        self.sub_order_id = ''
        self.out_trade_no = ''
        self.provider_order_id = ''
        self.provider_price = 0
        self.comment = ''
        self.create_time = Time.time_str()  # 初始化默认值，如果本类在初始化参数中包含此参数，则会被更新为入参值
        self.issue_success_time = None
        self.provider_order_status = ''
        self.flight_order = None
        self.provider_fee = 0.0
        self.extra_data = ''
        super(SubOrderInfo, self).__init__(**kwargs)
        self.save_disabled = False
        self.is_saved = False

        self.cabin_grade = ''
        self.raw_routing = None




        # 这里的字段可能会跟flightorder的冲突
        for k, v in dictobj( SubOrder).iteritems():
            self.sub_order_keys.append(k)
            if kwargs.has_key(k):
                if str(type(kwargs[k])) == "<type 'datetime.date'>" :
                    setattr(self, k, kwargs[k].strftime('%Y-%m-%d'))
                elif str(type(kwargs[k])) == "<type 'datetime.datetime'>" :
                    setattr(self, k, kwargs[k].strftime('%Y-%m-%d %H:%M:%S'))

                else:
                    setattr(self, k, kwargs[k])
    def check_provider_order_status(self):
        if OrderStatusManager.verify_format(self.provider_order_status):
            OrderStatusManager.manual_intervention(self.provider_order_status,self)
        else:
            raise OrderStatusException


    def save(self,lazy_flush=False):
        if not self.save_disabled :
            if not self.is_saved:

                # 存储 order
                if self.extra_data is None:
                    self.extra_data = ''
                elif type(self.extra_data) == dict:
                    self.extra_data = json.dumps(self.extra_data)
                __ = {k:convert_unicode(getattr(self,k)) for k in self.sub_order_keys }
                if __['routing'] and isinstance(__['routing'],FlightRoutingInfo) :
                    __['routing'] = __['routing'].save(lazy_flush=True)
                if __['ffp_account']:
                    __['ffp_account'] = __['ffp_account'].save(lazy_flush=True)
                if __.has_key('ret_date') and (not __['ret_date'] or __['ret_date'] == 'None'):
                    __.pop('ret_date', None)

                self.sub_order_instance = SubOrder(**__)
                # 存储账号关系
                if not lazy_flush:
                    flush()
                    commit()
                    self.sub_order_id = self.sub_order_instance.id
                self.is_saved = True
            return self.sub_order_instance


class PaxInfo(MixInfo):
    """
    注意 此类的save 将返回两个对象
    """
    def __init__(self,**kwargs):
        self.person_instance = None
        self.p2fo_instance = None
        self.has_inf = False  #  是否已经作为某一个婴儿的监护人
        self.p2fo_id = ''
        object.__setattr__(self, "person_keys", [])
        # self.person_keys = []

        self.person_id = ''
        for k, v in dictobj(Person).iteritems():
            setattr(self, k, v)
            if kwargs.has_key(k):
                if str(type(kwargs[k])) == "<type 'datetime.date'>" :
                    setattr(self, k, kwargs[k].strftime('%Y-%m-%d'))
                elif str(type(kwargs[k])) == "<type 'datetime.datetime'>" :
                    setattr(self, k, kwargs[k].strftime('%Y-%m-%d %H:%M:%S'))
                else:
                    setattr(self,k,kwargs[k])
            self.person_keys.append(k)

        self.p2fo_keys = []
        for k, v in dictobj(Person2FlightOrder).iteritems():
            setattr(self, k, v)
            self.p2fo_keys.append(k)

        self.is_saved = False

    @property
    def selected_card_no(self):
        if self.modified_card_no:
            Logger().sdebug('modified_card_no return ')
            return self.modified_card_no
        else:
            Logger().sdebug('used_card_no return ')
            return self.used_card_no

    def current_age_type(self,from_date=None,is_aggr_chd_adt = False):
        """
        current_age_type 是否聚合 chd和inf 只显示 chd
        from_date  出发日期 如果不填写按照当前日期进行判断
        根据证件或者生日返回实际日期
        研究了东航，发现是根据行程日期那天你是否成年来决定你是的年龄段
        :return:
        """
        adt_tag = 'ADT'
        chd_tag = 'CHD'
        if is_aggr_chd_adt:
            inf_tag = 'CHD'
        else:
            inf_tag = 'INF'
        if from_date:
            from_date_obj = datetime.datetime.strptime(from_date, '%Y-%m-%d')
        else:
            from_date_obj = Time.curr_date_obj_2()
        if self.card_ni:
            card_date_obj = datetime.datetime.strptime(self.card_ni[6:14],"%Y%m%d")
            if ( from_date_obj - card_date_obj).days < 365*2:
                return inf_tag
            elif 365*2 < (from_date_obj - card_date_obj).days < 365*12:
                return chd_tag
            elif 365*12 < (from_date_obj - card_date_obj).days :
                return adt_tag
        elif self.birthdate:
            birthdate_obj = datetime.datetime.strptime(self.birthdate,'%Y-%m-%d')
            if (from_date_obj - birthdate_obj).days < 365*2:
                return inf_tag
            elif 365*2 < (from_date_obj - birthdate_obj).days < 365*12:
                return chd_tag
            elif 365*12 < (from_date_obj - birthdate_obj).days :
                return adt_tag
        else:
            return 'ADT'



    def current_age(self,from_date=None):
        """
        根据登机时间计算当前年龄
        :return:
        """
        if from_date:
            from_date_obj = datetime.datetime.strptime(from_date, '%Y-%m-%d')
        else:
            from_date_obj = datetime.datetime.now()
        if self.card_ni:
            birthdate_obj = datetime.datetime.strptime(self.card_ni[6:14],"%Y%m%d")

        elif self.birthdate:
            birthdate_obj = datetime.datetime.strptime(self.birthdate,'%Y-%m-%d')
        else:
            raise InternalDataException('no birthdate to calc current age')

        cy = from_date_obj.year - birthdate_obj.year
        if from_date_obj.month - birthdate_obj.month > 0:
            return cy
        elif from_date_obj.month - birthdate_obj.month < 0:
            return cy - 1
        elif from_date_obj.month - birthdate_obj.month == 0:
            if from_date_obj.day - birthdate_obj.day >= 0:
                return cy
            else:
                return cy -1



    def attr_competion(self):
        """
        补全数据
        :return:
        """

        if not self.name:
            # 将中文或者英文名进行拼接
            eng_exp = re.compile(r'^[A-Za-z]*$')
            if eng_exp.match(self.last_name+self.first_name):
                # 英文中间添加/
                self.name = u'%s/%s' % (self.first_name,self.last_name )
            else:
                self.name = u'%s%s' % (self.last_name , self.first_name)

        eng_extra_exp = re.compile(r'^[A-Za-z/]*$')
        if self.name and not self.last_name and not self.first_name:
            if self.is_en_name() and '/' in self.name:
                self.first_name,self.last_name = self.name.split('/')
            else:
                if isinstance(self.name,str):
                    self.name = self.name.decode('utf8')

                self.last_name = self.name[:1]
                self.first_name = self.name[1:]

        # 根据身份证补充生日
        if not self.birthdate:
            if self.card_ni:
                self.birthdate = "%s-%s-%s"%(self.card_ni[6:10],self.card_ni[10:12],self.card_ni[12:14])


        if self.card_ni:
            if int(self.card_ni[16:17]) % 2 == 0:
                self.gender = 'F'
            else:
                self.gender = 'M'


    def is_en_name(self):
        eng_exp = re.compile(r'^[A-Za-z/]*$')
        if self.last_name and self.first_name:
            if eng_exp.match(self.last_name + self.first_name):
                return True
            else:
                return False
        elif self.name:
            if eng_exp.match(self.name):
                return True
            else:
                return
        else:
            raise InternalDataException('not found any name columns')




    def save(self, lazy_flush=False):
        if not self.is_saved:
            __ = {k: convert_unicode(getattr(self, k)) for k in self.person_keys}
            __.pop('ffp_accounts')
            __.pop('flight_orders')
            if not __['name']:

                eng_exp = re.compile(r'^[A-Za-z]*$')
                if eng_exp.match(__['last_name'] + __['first_name']):
                    # 英文中间添加/
                    __['name'] = u'%s/%s' % (__['first_name'], __['last_name'])
                else:
                    __['name'] = u'%s%s' % (__['last_name'], __['first_name'])
            self.person_instance = Person(**__)
            if  self.used_card_type != 'NA':
                #  考虑到通用情况，有可能只有用户信息没有关联订单信息，所以不需要关联库
                __ = {k: getattr(self, k) for k in self.p2fo_keys}
                self.p2fo_instance = Person2FlightOrder(**__)
                self.p2fo_instance.person = self.person_instance
            if not lazy_flush:
                flush()
                self.person_id = self.person_instance.id
                if self.passenger_id and self.used_card_type != 'NA':
                    self.p2fo_id = self.p2fo_instance.id
            self.is_saved = True
        return (self.person_instance,self.p2fo_instance,)


class ContactInfo(MixInfo):
    def __init__(self,**kwargs):
        self.contact_instance = None
        self.contact_id = ''
        object.__setattr__(self, "contact_keys", [])
        # self.contact_keys = []
        for k, v in dictobj(Contact).iteritems():
            setattr(self, k, v if v is not None else '')
            if kwargs.has_key(k):
                if str(type(kwargs[k])) == "<type 'datetime.date'>" :
                    setattr(self, k, kwargs[k].strftime('%Y-%m-%d'))
                elif str(type(kwargs[k])) == "<type 'datetime.datetime'>" :
                    setattr(self, k, kwargs[k].strftime('%Y-%m-%d %H:%M:%S'))
                else:
                    setattr(self,k,kwargs[k] if kwargs[k] is not None else '')
            self.contact_keys.append(k)

        self.is_saved = False

    def save(self, lazy_flush=False):
        if not self.is_saved:
            __ = {k : getattr(self, k) if getattr(self, k) is not None else '' for k in self.contact_keys}
            __.pop('flight_order')
            __.pop('sub_orders')
            self.contact_instance = Contact(**__)
            if not lazy_flush:
                flush()
                self.contact_id = self.contact_instance.id
            self.is_saved = True
        return self.contact_instance

class PersonInfo(MixInfo):
    def __init__(self,**kwargs):
        self.person_instance = None
        self.person_id = ''
        object.__setattr__(self, "person_keys", [])
        # self.person_keys = []
        for k, v in dictobj(Person).iteritems():
            setattr(self, k, v if v is not None else '')
            if kwargs.has_key(k):
                if str(type(kwargs[k])) == "<type 'datetime.date'>" :
                    setattr(self, k, kwargs[k].strftime('%Y-%m-%d'))
                elif str(type(kwargs[k])) == "<type 'datetime.datetime'>" :
                    setattr(self, k, kwargs[k].strftime('%Y-%m-%d %H:%M:%S'))
                else:
                    setattr(self,k,kwargs[k] if kwargs[k] is not None else '')
            self.person_keys.append(k)

        self.is_saved = False

    def save(self, lazy_flush=False):
        if not self.is_saved:
            __ = {k : getattr(self, k) if getattr(self, k) is not None else '' for k in self.person_keys}
            self.person_instance = Person(**__)
            if not lazy_flush:
                flush()
                self.person_id = self.person_instance.id
            self.is_saved = True
        return self.person_instance

class FFPAccountInfo(MixInfo):
    def __init__(self,**kwargs):
        self.ffp_account_id = ''
        self.ffp_account_instance = None
        object.__setattr__(self, "ffp_account_keys", [])
        # self.ffp_account_keys = []
        for k, v in dictobj(FFPAccount).iteritems():
            setattr(self, k, v)
            if kwargs.has_key(k):
                if str(type(kwargs[k])) == "<type 'datetime.date'>" :
                    setattr(self, k, kwargs[k].strftime('%Y-%m-%d'))
                elif str(type(kwargs[k])) == "<type 'datetime.datetime'>" :
                    setattr(self, k, kwargs[k].strftime('%Y-%m-%d %H:%M:%S'))
                else:
                    setattr(self,k,kwargs[k])
            self.ffp_account_keys.append(k)

        self.is_saved = False


    def save(self, lazy_flush=False):
        if not self.is_saved:
            __ = {k: getattr(self, k) for k in self.ffp_account_keys}
            if __['reg_person']:
                __['reg_person'] = __['reg_person'].save(lazy_flush=True)[0]
            else :
                __.pop('reg_person')
            self.ffp_account_instance = FFPAccount(**__)
            if not lazy_flush:
                flush()
                commit()
                self.ffp_account_id = self.ffp_account_instance.id
            self.is_saved = True
        return self.ffp_account_instance


class OTAVerifyInfo(MixInfo):

    def __init__(self, **kwargs):

        self.data_instance = None
        for k, v in dictobj(OTAVerify).iteritems():
            setattr(self, k, v)
            if kwargs.has_key(k):
                if str(type(kwargs[k])) == "<type 'datetime.date'>":
                    setattr(self, k, kwargs[k].strftime('%Y-%m-%d'))
                elif str(type(kwargs[k])) == "<type 'datetime.datetime'>":
                    setattr(self, k, kwargs[k].strftime('%Y-%m-%d %H:%M:%S'))
                else:
                    setattr(self, k, kwargs[k])
        self.is_saved = False


    def save(self, lazy_flush=False):
        if not self.is_saved:
            __ = {k: getattr(self, k) for k in self.ffp_account_keys}
            self.data_instance = OTAVerify(**__)
            if not lazy_flush:
                flush()
                commit()
            self.is_saved = True
        return self.data_instance


class FareInfo(MixInfo):
    """
    运价数据结构体
    sdp
    fare_put_mode 新增 LOWPRICE
    priority
    dfr_id
    offer_price
    ota_r1_price
    ota_r2_price
    cost_price
    low_price # 投放最低价
    expired_time  # 过期时间戳 十位
    cabin  # todo 临时设置舱位，三期优化版本可能会摒弃
    """
    def __init__(self, **kwargs):
        self.fare_put_mode = 'NOFARE'  # 默认无运价
        self.assoc_fare_info = ''
        for k,v in kwargs.items():
            setattr(self, k, v)



ERROR_STATUS = {
    'SUCCESS':'成功',
    'INNER_ERROR_1001': '无此OTA',
    'INNER_ERROR_1002': '未知异常',
    'INNER_ERROR_1003': 'OTAToken 错误',
    'INNER_ERROR_1004': '访问频率过快',
'INNER_ERROR_1005': '路由分发错误',


    # 通知扣款接口报错
    'INNER_ERROR_4001': '无此订单号',
    'INNER_ERROR_4002': '扣款失败',
    'INNER_ERROR_4003': '订单无价格',
    'INNER_ERROR_4004': '价格不符',
'INNER_ERROR_4005': '重复支付',

    # 订单状态详情接口报错
    'INNER_ERROR_5001': '无此订单号',

    # 订单列表接口报错
    'INNER_ERROR_6001': '查询时间范围超过一天',
    'INNER_ERROR_6002': '缺少必要字段',
    # 通知出票接口报错
'INNER_ERROR_7001': '无此订单号',
'INNER_ERROR_7002': '此订单已经确认出票',
}


# 将数据库数据加载至 Order_info  TODO:这里需要重构 目前实现太复杂
# order = FlightOrder[flight_order_id]
# order_info_input = order.to_dict(with_collections=True,related_objects=True)
# paxs = []
# contacts =[]
# for p in order_info_input['passangers']:
#     pp = p.person.to_dict()
#     pp.pop('ffp_accounts')
#     pp.pop('flight_orders')
#     pax_info = PaxInfo(**pp)
#     pax_info.ticket_no = p.ticket_no
#     pax_info.used_card_type = p.used_card_type
#     pax_info.passenger_id = p.passenger_id
#     paxs.append(pax_info)
#
# for c in order_info_input['contacts']:
#     pp = c.to_dict()
#     contact_info = ContactInfo(**pp)
#     contacts.append(contact_info)
#
# order_info_input['passangers'] = paxs
# order_info_input['contacts'] = contacts
#
# ffp_account = order_info_input['ffp_account'].to_dict(with_collections=True,related_objects=True)
# ffp_account.pop('reg_person')
# ffp_account.pop('flight_orders')
# order_info_input['ffp_account'] = ffp_account
#
# # 梳理routing 和 segments
# routing = order_info_input['routing'].to_dict()
# from_segments = []
# for f in order_info_input['from_segments']:
#     ff = f.to_dict()
#     fsi = FlightSegmentInfo(**ff)
#     from_segments.append(fsi)
#
# ret_segments = []
# for f in order_info_input['to_segments']:
#     ff = f.to_dict()
#     fsi = FlightSegmentInfo(**ff)
#     ret_segments.append(fsi)
# routing['from_segments'] = from_segments
# routing['ret_segments'] = ret_segments
#
# order_info_input['routing'] = routing
#
# order_info = OrderInfo(**order_info_input)


# 初始化另外一个版本
# order_info = OrderInfo()
# # flight_order = FlightOrder[flight_order_id]
# flight_order = order_info.load_from_meta(flight_order_id)
# if flight_order.ffp_account:
#     # 此数据属于后更新，所以需要在每次循环的时候读取数据库是否存在
#     order_info.ffp_account = FFPAccountInfo(**flight_order.ffp_account.to_dict())
# order_info.provider_order_id = flight_order.provider_order_id
# order_info.assoc_order_id = flight_order.assoc_order_id
# order_info.ota_name = ota_name
# order_info.provider = provider
# order_info.ota_order_status = flight_order.ota_order_status
# order_info.ota_create_order_time = flight_order.ota_create_order_time
# order_info.ota_pay_price = flight_order.ota_pay_price
# order_info.from_airport = flight_order.from_airport
# order_info.to_airport = flight_order.to_airport
# order_info.from_date = flight_order.from_date
# order_info.trip_type = flight_order.trip_type
# order_info.routing_range = flight_order.routing_range
# order_info.adt_count = flight_order.adt_count
# order_info.chd_count = flight_order.chd_count
# order_info.inf_count = flight_order.inf_count
# order_info.session_id = flight_order.session_id
# order_info.provider_price = flight_order.provider_price
# order_info.inf_count = flight_order.inf_count
# order_info.ota_order_id = flight_order.ota_order_id
# order_info.provider_order_status = flight_order.provider_order_status

# 旧逻辑，效率差
# ptask_list = select(o for o in PrimaryFareCrawlTask if o.task_status == 'RUNNING')
# for p in ptask_list:
#     Logger().sdebug('producing ptask %s'% p.id)
#     task_list = select(o for o in SecondaryFareCrawlTask if o.task_status == 'RUNNING' and o.primary_task_id == p)
#     for task in task_list:
#         dl = select(s for s in FareCrawlRepoDL if s.task_id == task and s.from_date >= datetime.date.today()).order_by(desc(FareCrawlRepoDL.id))[:1]
#         if dl:
#             dl = dl[0]
#             Logger().sdebug('dl details %s'%dl.to_dict())
#             if dl.from_date > datetime.date.today():
#                 # 当天的航班不做权重统计
#                 if task.cabin_count_total:
#                     if float(dl.cabin_count_total) > float(task.cabin_count_total) * 1.2:
#                         pass
#                         # # 余位增加20%
#                         # if task.pr > 1:
#                         #     task.pr -= 1
#                         #     Logger().debug('pr decrease ')
#                     elif float(dl.cabin_count_total) < float(task.cabin_count_total) * 0.8 or \
#                                             dl.flightcount_cabin_1_8 / float(dl.flightcount_total) > (task.flightcount_cabin_1_8 / float(task.flightcount_total)) * 1.2:
#                         # 余位减少20% 或者8个以下座位的比例上升20%
#
#
#                         if task.pr < 5:
#                             is_increase = True
#                             task.pr += 1
#                             task.cabin_count_total = dl.cabin_count_total
#                             task.flightcount_cabin_a = dl.flightcount_cabin_a
#                             task.flightcount_cabin_1_8 = dl.flightcount_cabin_1_8
#                             task.flightcount_total = dl.flightcount_total
#                             Logger().sdebug('pr increase ')
#                         else:
#                             is_increase = False
#
#                         if TBG.global_config['METRICS_SETTINGS']['enabled'] == True:
#                             TBG.tb_metrics.write(
#                                 "CRAWLER.MANAGER.CWR_PREVAL_TASK.DL_CHANGE",
#                                 tags=dict(
#                                     from_date=str(task.from_date),
#                                     from_airport=task.from_airport,
#                                     to_airport=task.to_airport,
#                                     pr=task.pr,
#                                     is_increase=is_increase
#                                 ),
#                                 fields=dict(
#                                     count=1
#                                 ))
#
#             else:
#                 Logger().sdebug('current day not calc')
#             if not task.cabin_count_total:
#                 # 任务刚开始没有total的统计，需要新增
#                 Logger().sdebug('cabin_count_total init')
#                 if dl.flightcount_cabin_1_8 / float(dl.flightcount_total) > 0.8:
#                     # 1-8的航班数占总航班数的80%以上
#                     task.pr = 5
#                 task.cabin_count_total = dl.cabin_count_total
#                 task.flightcount_cabin_a = dl.flightcount_cabin_a
#                 task.flightcount_cabin_1_8 = dl.flightcount_cabin_1_8
#                 task.flightcount_total = dl.flightcount_total
#             if not task.lowest_price:
#                 Logger().sdebug('lowest_price init')
#                 task.lowest_price = dl.lowest_price

if __name__ == '__main__':
    a = PaxInfo()
    a.from_date = '2018-10-30'
    a.birthdate = '1990-10-30'
    print a.current_age()