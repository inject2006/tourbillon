#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, too-many-arguments, broad-except, anomalous-backslash-in-string
# pylint: disable=missing-docstring, line-too-long, too-few-public-methods
"""
# @Author  : wxt
# @Software: PyCharm
"""

import json, gevent, datetime, copy
from ..utils.exception import *
from ..utils.logger import Logger, logger_config
from ..utils.util import Random, Time, tb_gevent_spawn, simple_decrypt, simple_encrypt, RoutingKey
from ..dao.internal import *
from ..dao.models import *
from app import TBG
from ..dao.iata_code import IATA_CODE,BUDGET_AIRLINE_CODE
from ..dao.internal import ERROR_STATUS
from ..utils.nonworkingdays_2018 import day_list
from ..controller.freq_limiter import OTAFrequencyVerification
from ..controller.fusing_limiter import FusingControl
from ..controller.cabin_revise import CabinReviseControl
from ..controller.dynamic_fare import DynamicFareRuleEngine
from pony.orm import db_session, select
from ..automatic_repo.base import ProviderAutoRepo
from ..automatic_repo.pdc_faker import PdcFaker
from ..controller.pokeman import Pokeman


class OTARepo(object):
    @staticmethod
    def select(vender_class):
        """

        :param vender_class: 传入验证码厂商类名
        :return:
        """
        for sub_class in OTABase.__subclasses__():
            if sub_class.ota_name == vender_class:
                return sub_class()
        raise NoSuchOTAException('No such OTA: %s' % vender_class)

    @staticmethod
    def list_all_otas():
        """
        列出所有provider
        :param self:
        :return:
        """
        otas = []
        for sub_class in OTABase.__subclasses__():
            otas.append({'name': sub_class.ota_name, 'cn_name': sub_class.cn_ota_name})
        return otas


@TBG.fcache.memoize(TBG.global_config['FCACHE_TIMEOUT'])
def get_ota_config(ota_name,config_mode='default'):
    """
    从 redis中获取配置
    :return:
    """
    if config_mode == 'default':
        ret = TBG.config_redis.get_value('operation_config_%s' % ota_name)
    else:
        ret = TBG.config_redis.get_value('unattended_operation_config_%s' % ota_name)
    if ret:
        return json.loads(ret)
    else:
        raise FetchOTAConfigException


@TBG.fcache.cached(TBG.global_config['FCACHE_TIMEOUT'], key_prefix='get_fusing_repo')
def get_fusing_repo():
    """
    获取熔断库并缓存
    :return:
    """
    frl = FusingControl.fusing_repo_list()
    return frl.keys()


@TBG.fcache.cached(TBG.global_config['FCACHE_TIMEOUT'], key_prefix='get_cabin_revise_repo')
def get_cabin_revise_repo():
    """
    获取舱位修正缓存库
    :return:
    """

    res = CabinReviseControl.repo_list()

    return res


class OTABase(object):
    """
    OTA 接口基类，
    该接口所有子类集成必须自己实现异常捕捉，如果抛出异常则OTA请求会返回500
    """
    ota_name = None  # OTA名称，保证唯一，必须赋值
    ota_env = 'PROD'  # 生产OR测试接口 TODO 暂时无作用
    pay_channel = 'ALIPAY'  # 如果供应商发起扣款的渠道
    product_type = 0  # 运价类型：0: GDS私有运价 1:GDS公布运价 2:航司官网产品  3:廉价航司产品 4:特价产品
    verify_search_timeout = 13  # 验价搜索时间
    order_search_timeout = 21  # 订单搜索超时时间
    order_by_pull_interval = 35  # 拉取订单间隔时间
    order_detail_process_mode = None  # 订单详情处理方式 api 开放接口等待调用的方式 pull 拉取别人接口的方式
    ticket_process_mode = None  # 票号处理方式 api 开放接口等待调用  push 主动推送
    order_process_mode = None  # 订单处理方式是  polling  轮询
    low_price_provider_channel = None  # 定义该ota的关联低价看板
    cn_ota_name = '未定义名称'

    verify_return_status = {
        'SUCCESS': '验价成功',
        'NOCABIN': '仓位不满足',
        'PRICERISE': '价格上升',
        'NOFLIGHT': '无航班',
        'ERROR': '异常错误',
        'PROVIDER_ERROR': '供应商侧异常'
    }
    order_return_status = {
        'CHECK_SUCCESS': '预检成功',
        'NOCABIN': '舱位不满足',
        'PRICERISE': '价格上升',
        'NOFLIGHT': '无航班',
        'ERROR': '异常错误',
        'PROVIDER_ERROR': '供应商侧异常',
        'CERTIFICATE_ERROR': '证件验证不通过',
        'ORDER_NOTSAVE': '订单不存储',
        'ORDER_SAVE': '订单存储',
        'FAILED': '订单预检失败',
        'TOO_OLD_TO_BOARDING': '年龄过大'
    }
    search_return_status = {
        'TIMEOUT_NOFLIGHT': '超时无结果',
        'RTS_NOFLIGHT': '供应商返回无结果',
        'RTS_ERROR_NOFLIGHT': '供应商请求错误返回无结果',
        'CACHE_NOFLIGHT_FROM_XXX': '缓存无结果',
        'RTS_SUCCESS': '供应商返回结果',
        'CACHE_SUCCESS_FROM_XX': '缓存返回',
        'ERROR': '异常',
        'FILTERED': '不符合运营策略条件',
        'FREQ_LIMITED': '频率限制',
        'NO_ROUTE': '路由分发异常'
    }

    def __init__(self):
        if self.ota_name is None:
            raise NotImplementedError

        self.request_id = Random.gen_hash()  # 用来关联
        self.search_info = None
        self.order_info = None
        self._operation_config = get_ota_config(ota_name=self.ota_name,config_mode='default')

        self.ota_extra_name = None
        self.ota_extra_group = None
        self.final_result = None
        self.is_filtered = False
        self.provider_app = None
        self.fare_cache_query_params_hash = None  # 搜索缓存查询参数hash
        self.work_flow = None  # 工作流 search verify order
        self.route_pipeline = []
        self.current_provider = ''
        self.current_provider_channel = ''
        self.fusing_repo = get_fusing_repo()

        self.ota_fusing_repo = []  # ota熔断库
        for ofc in self.fusing_repo:
            if ofc.startswith('ota'):
                self.ota_fusing_repo.append(ofc[4:])

        # 舱位修正库数据
        self.cabin_revise_repo = get_cabin_revise_repo()

    # def __get_operation_config(self):
    #     """
    #     临时从配置文件中获取
    #     :return:
    #     """
    #     ret = current_app.config['OTA_SEARCH_CONFIG']
    #     if ret:
    #
    #         self._operation_config = ret
    #     else:
    #         raise FetchOTAConfigException

    @logger_config('OTA_FREQ_LIMIT')
    def frequency_verification(self, api_name):
        if OTAFrequencyVerification()(ota_name=self.ota_name, api_name=api_name, freq_info=self._operation_config['freq_info'].get(api_name, '')):
            return True
        else:
            return False

    def search_interface_error_output(self):
        """
        接口报错返回
        :return:
        """
        raise NotImplementedError

    def verify_interface_error_output(self):
        """
        接口报错返回
        :return:
        """
        raise NotImplementedError

    def order_interface_error_output(self):
        """
        接口报错返回
        :return:
        """
        return ''

    def is_open_time(self):
        """
        是否为开放时间判断
        :return: 返回open则代表开放
        """
        filtered_reason = 'OPEN'
        if self._operation_config['search_interface_status'] == 'turn_off':
            filtered_reason = 'TURN_OFF'

        if self._operation_config['switch_mode'] == 'auto':  # 如果是自动模式需要关心节假日和工作时间
            # 节假日计算
            if self._operation_config['is_include_nonworking_day'] == 0 and Time.date_str() in day_list:
                filtered_reason = 'IS_NONWORKING_DAY'

            # 工作时间范围计算
            is_work = False
            current_hour = datetime.datetime.now().hour
            for hour_range in self._operation_config['open_hours']:
                if hour_range[0] <= current_hour < hour_range[1]:
                    is_work = True
            if not is_work:
                filtered_reason = 'NOT_IN_OPEN_HOURS'

        return filtered_reason

    @TBG.fcache.cached(TBG.global_config['FCACHE_TIMEOUT_FUSING'])
    def get_fusing_repo(self):
        """
        获取熔断库并缓存
        :return:
        """
        frl = FusingControl.fusing_repo_list()
        self.fusing_repo = frl.keys()

    def is_ota_fusing(self):
        """
        判断ota是否被熔断，使用缓存过的荣短库，准实时
        :return:
        """
        if self.ota_name in self.ota_fusing_repo:
            return True
        else:
            return False

    def is_rk_fusing(self, bp_key):
        """
        不加缓存，在验价和生单时候使用，需要高实时性
        :param un_key:
        :return:
        """
        return FusingControl.is_fusing(fusing_type='bp_key', fusing_var=bp_key)

    def select_config(self):
        """
        通过时间判断选用那个配置（默认or无人值守）
        :return:
        """
        reason = self.is_open_time()
        if reason != 'OPEN':
            Logger().sdebug('not open %s' % reason)
            if self._operation_config['enable_unattended'] and reason in ['NOT_IN_OPEN_HOURS', 'IS_NONWORKING_DAY']:  # 使用无人值守配置替换掉当前配置
                self._operation_config = get_ota_config(ota_name=self.ota_name, config_mode='unattended')
                Logger().sinfo('use unattended config')
    @logger_config('OTA_SEARCH_FILTER')
    def filter(self, is_debug):
        """
        询价前参数过滤器,对运营策略和业务进行过滤
        此处需要定义在非运营状态以及不满足业务过滤后的返回
        :return: 如果过滤条件不满足则返回None
        """
        # 运营
        filtered_reason = ''
        if not is_debug:  # 如果是debug模式则不会受到此策略影响
            reason = self.is_open_time()
            if reason != 'OPEN':
                # Logger().sdebug('not open')
                if self._operation_config['enable_unattended'] and reason in ['NOT_IN_OPEN_HOURS','IS_NONWORKING_DAY']:  # 使用无人值守配置替换掉当前配置
                    self._operation_config = get_ota_config(ota_name=self.ota_name,config_mode='unattended')
                    # Logger().sinfo('self._operation_config %s' % self._operation_config)
                else:
                    if self._operation_config['pdc_faker_always_online']:  # 判断测试航线供应商保持在线开关是否打开
                        if not self.search_info.is_pdc_faker_flight:
                            Logger().sdebug('is_pdc_faker_flight is False ')
                            self.is_filtered = True
                            filtered_reason = reason
                        else:
                            # 测试供应商有航班，通过
                            pass
                    else:
                        self.is_filtered = True
                        filtered_reason = reason

        # ----- 业务filter --------

        ####### 硬性规定
        # 航段是否在IATA CODE 列表中
        # 此处涉及查询IATA的三字码，并关联城市，有可能存在三字码找不到的情况

        if self.search_info.from_airport not in IATA_CODE or self.search_info.to_airport not in IATA_CODE:
            filtered_reason = ' %s - %s not in IATA_CODE' % (self.search_info.from_airport, self.search_info.to_airport)
            self.is_filtered = True
        else:
            if self.search_info.chd_count + self.search_info.inf_count and self._operation_config['is_allow_child'] == 0:
                filtered_reason = 'not allow child'
                self.is_filtered = True

            # 一个成年人只能带三个儿童
            total_pax_count = self.search_info.adt_count + self.search_info.chd_count + self.search_info.inf_count
            if total_pax_count > 9:
                filtered_reason = 'too many pax '
                self.is_filtered = True
            elif self.search_info.chd_count > self.search_info.adt_count * 3:
                filtered_reason = 'too many chd_count '
                self.is_filtered = True

            ######  策略可配置

            # 国际 or 国内
            if self.search_info.routing_range not in self._operation_config['routing_range']:
                filtered_reason = 'out of routing_range '

                self.is_filtered = True
            # 航线筛选
            if self._operation_config['from_to_routings']:
                if [self.search_info.from_airport, self.search_info.to_airport] not in self._operation_config['from_to_routings']:
                    filtered_reason = 'out of from_to_routings '
                    self.is_filtered = True
            # 单程 or 往返
            if self.search_info.trip_type not in self._operation_config['trip_type']:
                # Logger().sdebug('self.search_info.trip_type %s' % self.search_info.trip_type)
                filtered_reason = 'out of trip_type '
                self.is_filtered = True
            # 舱位过滤
            if self.search_info.cabin_grade_list:
                has_cabin_grade = False
                for cg in self.search_info.cabin_grade_list:
                    if cg in self._operation_config['cabin_grade']:
                        has_cabin_grade = True
                if not has_cabin_grade:
                    self.is_filtered = True
                    filtered_reason = 'has no cabin grade '

            # 查询时间范围
            if self._operation_config['within_days'] != []:
                from_date_obj = datetime.datetime.strptime(self.search_info.from_date, '%Y-%m-%d')
                if self._operation_config['within_days'][1] == 0:
                    last_search_day = Time.curr_date_obj_2() + datetime.timedelta(days=1000)
                else:
                    last_search_day = Time.curr_date_obj_2() + datetime.timedelta(days=self._operation_config['within_days'][1])
                if self._operation_config['within_days'][0] == 0:
                    first_search_day = datetime.datetime.strptime(datetime.datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d')
                else:
                    first_search_day = datetime.datetime.strptime(datetime.datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d') + datetime.timedelta(days=self._operation_config['within_days'][0])

                if not first_search_day <= from_date_obj <= last_search_day:
                    self.is_filtered = True
                    filtered_reason = 'out of within_days '

        if self.is_filtered:
            self.search_info.return_status = 'FILTERED'
            self.search_info.return_details = filtered_reason
            Logger().sdebug('request is filtered {search_info} reason 【【【{filtered_reason}】】】'.format(search_info=self.search_info, filtered_reason=filtered_reason))
            return True
        else:
            Logger().sdebug('request by pass')
            return False

    def before_search_interface(self, req_body):
        """
        询价接口
        :param result search返回
        """
        # Logger().sdebug('before_search_interface start')
        try:
            self.search_info = SearchInfo()
            self.search_info.ota_work_flow = self.work_flow
            self._before_search_interface(req_body)
            pdc_faker_app = PdcFaker()
            if pdc_faker_app.is_exist_flight(search_info=self.search_info):  # 测试供应商无航班
                self.search_info.is_pdc_faker_flight = 1  # 是否为测试航班
            else:
                self.search_info.is_pdc_faker_flight = 0
            self.search_info.attr_competion()
            return
        except Exception as e:
            Logger().serror('before_search_interface failed')
        raise SearchInterfaceException

    def _before_search_interface(self, req_body, **kwargs):
        """

        :param req_body:
        :param kwargs:
        :return:
        """
        raise NotImplementedError

    def after_search_interface(self):
        """
        询价接口teardown
        :param result search返回
        """
        search_info = self.search_info  # TODO 临时适配
        # Logger().sdebug('{ota_name} after_search_interface start'.format(ota_name=self.ota_name))
        try:

            self._after_search_interface(search_info=search_info)
        except Exception as e:
            Logger().serror('{ota_name} after_search_interface failed'.format(ota_name=self.ota_name))
            raise SearchInterfaceException

    def _after_search_interface(self, search_info):
        """
        询价接口teardown
        :param result search返回
        是否成功需要返回 True or False
        """
        raise NotImplementedError

    # 验价接口
    @logger_config('SUB_VERIFY')
    def sub_verify(self, provider_app, search_info):
        """
        生单子线程
        :param order_info:
        :return:
        """
        TB_PROVIDER = provider_app.provider
        TB_PROVIDER_CHANNEL = provider_app.provider_channel

        try:
            Logger().sinfo('sub_verify start request_id: %s' % search_info.request_id)
            flight_routing = provider_app.verify(search_info=search_info)  # 调用供应商验价模块去验价
            search_info.assoc_search_routings = [flight_routing]
            search_info.search_finished = True
        except NotImplementedError as e:
            try:
                provider_app.flight_search(search_info=search_info, proxy_pool='F')
            except Exception as e:
                Logger().serror('sub_verify provider search error')
        except Exception as e:
            search_info.assoc_search_routings = []  # routings 置空
            # 验价失败情况
            Logger().serror('sub_verify provider verify error')

    @logger_config('FARE_LINKAGE')
    def fare_linkage(self):
        """
        生单子线程
        :param fare_info: 运价信息结构体
        :return:
        """

        Logger().sinfo('verify_linkage start ')

        try:
            fare_ota_search_info = SearchInfo(**self.search_info)
            # 防止人数导致干扰
            fare_ota_search_info.adt_count = 1
            fare_ota_search_info.chd_count = 0
            fare_ota_search_info.inf_count = 0
            provider_app = ProviderAutoRepo.select(self.low_price_provider_channel)
            provider_app.flight_search(search_info=fare_ota_search_info, cache_mode='MIX', allow_expired=True, custom_expired_time=5)

            fare_ota_search_info.rk_info['dep_time'] = 'N/A'  # 因为某些低价看板没有dep_time
            fare_ota_search_info.rk_info['arr_time'] = 'N/A'  # 因为某些低价看板没有dep_time

            # 不包含舱位 则对比航班最低价
            vkey = RoutingKey.trans_cc_key(fare_ota_search_info.rk_info, is_unserialized=True)

            # 查询OTA 低价看板或者C端
            fare_set = {}
            self.search_info.fare_info.cabin = fare_ota_search_info.rk_info['cabin']
            self.search_info.fare_info.low_price = None
            for frouting in fare_ota_search_info.assoc_search_routings:

                rk_dict = RoutingKey.unserialize(frouting.routing_key_detail)
                rk_dict['dep_time'] = 'N/A'
                rk_dict['arr_time'] = 'N/A'
                # Logger().debug('frouting.............%s' % frouting)

                # 不包含舱位 则对比航班最低价
                key = RoutingKey.trans_cc_key(rk_dict, is_unserialized=True)

                low_price = None
                ota_r1_price = rk_dict['adult_price'] + rk_dict['adult_tax']
                ota_r2_price = frouting.reference_adult_price + frouting.reference_adult_tax
                if not ota_r2_price:
                    ota_r2_price = ota_r1_price  # 保证r2有数据
                if vkey == key:
                    if self.search_info.fare_info.get("ota_r1_price", 0):
                        if self.search_info.fare_info.ota_r1_price > ota_r1_price:
                            self.search_info.fare_info.ota_r1_price = ota_r1_price
                            self.search_info.fare_info.ota_r2_price = ota_r2_price
                            Logger().sinfo('ota_r1_price update %s' % ota_r1_price)
                    else:
                        self.search_info.fare_info.ota_r1_price = ota_r1_price
                        self.search_info.fare_info.ota_r2_price = ota_r2_price
                        Logger().sinfo('ota_r1_price create %s' % ota_r1_price)
        except Exception as e:
            Logger().error('fare_linkage error')

    def prefix_routing_match(self, search_info_str, filter_conditions):
        """
        航班是否符合过滤条件，符合返回True，不符合返回False
        :return:
        """
        if filter_conditions:
            for f in filter_conditions:
                if re.search(f, search_info_str):
                    # 命中规则
                    return True
            else:
                # 所有条件不满足则不通过
                return False
        else:
            # 没有过滤条件则全部通过
            return True

    @logger_config('OTA_VERIFY')
    @db_session
    def verify_interface(self, request_id):
        """
        验价接口

        """
        self.select_config()  # 选择配置
        self.search_info.request_id = request_id
        current_verify_time = Time.time_str_4()
        routing_key_detail = RoutingKey.decrypted(self.search_info.verify_routing_key)
        rk_info = RoutingKey.unserialize(routing_key_detail, is_encrypted=False)
        offer_price = rk_info['adult_price_forsale'] + rk_info['adult_tax']
        cc_key = RoutingKey.trans_cc_key(rk_info, is_unserialized=True)
        cp_key = RoutingKey.trans_cp_key(rk_info, is_unserialized=True)
        bp_key = RoutingKey.trans_bp_key(rk_info, is_unserialized=True)
        Logger().sinfo('routing_key_detail %s' % routing_key_detail)
        # 扩展搜索条件
        self.search_info.from_date = rk_info['from_date']
        self.search_info.from_airport = rk_info['search_from_airport']
        self.search_info.to_airport = rk_info['search_to_airport']
        self.search_info.trip_type = rk_info['trip_type']
        self.search_info.ret_date = rk_info['ret_date']
        self.search_info.rk_info = rk_info
        self.search_info.providers_stat = []  # 收集供应商状态
        self.search_info.fare_info = FareInfo(**self._operation_config.get('fare_linkage', {}))
        Logger().sinfo('self.search_info.fare_info %s' % self.search_info.fare_info)
        self.search_info.attr_competion()  # 属性自动补全
        self.search_info.verify_details = {}


        # 判断是否为廉航，判断条件：所有航段的carrier都为廉航才判断为廉航
        flight_numbers = [fn[:2] for fn in rk_info['flight_number'].split('-')]
        Logger().sinfo('flight_numbers %s' % flight_numbers)
        is_ba = True
        for fn in flight_numbers:
            if fn not in BUDGET_AIRLINE_CODE:
                is_ba = False
                break

        Logger().sinfo('is_ba %s' % is_ba)

        current_provider_app = ProviderAutoRepo.select(rk_info['provider_channel'])
        # 赋值用于metric打点

        self.current_provider = current_provider_app.provider
        self.current_provider_channel = current_provider_app.provider_channel
        # from_date_obj = datetime.datetime.strptime(self.search_info.from_date, '%Y-%m-%d')
        # curr_date_obj = datetime.datetime.strptime(datetime.datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d')
        # dep_diff_days = (from_date_obj - curr_date_obj).days
        # search_info_str = '%s|%s|%s|%s|%s|%s|%s|%s|%s' % (
        #     self.search_info.from_airport, self.search_info.to_airport, self.search_info.from_date, self.search_info.routing_range, self.search_info.trip_type, self.search_info.adt_count,
        #     self.search_info.chd_count, self.search_info.inf_count, dep_diff_days)

        try:

            if self.current_provider_channel == 'pdc_faker':
                current_provider_app.flight_search(search_info=self.search_info)
                is_exist_routing = False
                same_cabin_routing = None
                for flight_routing in self.search_info.assoc_search_routings:
                    fr_cp_key = RoutingKey.trans_cp_key(flight_routing.routing_key_detail)
                    if cp_key == fr_cp_key:
                        is_exist_routing = True
                        same_cabin_routing = flight_routing
                if is_exist_routing:
                    rk_info['assoc_provider_channels'] = ['%s#%s' % (self.current_provider_channel, 888)]
                    self.search_info.return_status = 'SUCCESS'
                    # 在routingkey中添加验价时间
                    rk_info['verify_time'] = current_verify_time
                    # 更新routingkey
                    new_rk_info = RoutingKey.serialize(**rk_info)
                    # 价格返回同舱价格
                    same_cabin_routing.adult_price_forsale = rk_info['adult_price_forsale']
                    same_cabin_routing.child_price_forsale = rk_info['child_price_forsale']
                    same_cabin_routing.adult_price = rk_info['adult_price']
                    same_cabin_routing.child_price = rk_info['child_price']
                    same_cabin_routing.child_tax = rk_info['child_tax']
                    same_cabin_routing.adult_tax = rk_info['adult_tax']
                    same_cabin_routing.routing_key_detail = new_rk_info['plain']
                    same_cabin_routing.routing_key = new_rk_info['encrypted']
                    rk_info['assoc_provider_channels'].append('%s#%s' % ('main', 888))  # main 记录的是验价routing

                    # 更新routingkey
                    new_rk_info = RoutingKey.serialize(**rk_info)
                    self.search_info.routing = same_cabin_routing
                    Logger().sinfo('same_cabin_routing same_cabin_routing %s' % same_cabin_routing)
                    # Logger().sdebug('same_cabin_routing.adult_price_forsale %s ' % same_cabin_routing.adult_price_forsale)
                    self.search_info.verify_routing_key = new_rk_info['encrypted']
                    # Logger().sdebug('new_rk_info %s ' % new_rk_info)
                    self.after_verify_interface(self.search_info)
                else:
                    self.search_info.return_status = 'NOFLIGHT'
                    self.final_result = self.verify_interface_error_output()
            else:

                # 判断是否允许儿童订票
                if not self._operation_config.get('is_allow_child', 0) and self.search_info.chd_count > 0:
                    Logger().sinfo('raise NotAllowChildException ')
                    raise NotAllowChildException

                # 如果是虚拟仓 先熔断
                is_continue_process = True # 是否在供应商全部返回结果后进行聚合处理并返回成功
                if rk_info['is_virtual_cabin']:
                    if FusingControl.is_fusing(fusing_type='bp_key', fusing_var=bp_key):
                        raise FusingException
                    else:
                        if not self._operation_config['is_allow_vcba_order'] and is_ba or not is_ba: # 是虚拟仓但是不允许虚拟仓廉航下单 或者不是虚拟仓
                            FusingControl.add_fusing(fusing_type='bp_key', fusing_var=bp_key, source='verify_virtual_cabin', ttl=10800)  # 熔断三个小时，如果再无数据补充，则依然会继续熔断
                            is_continue_process = False

                is_order_directly_list = []
                fare_search_sub_providers = []
                worker_pool = []
                is_include_fare_provider = False
                for item in self._operation_config['order_provider_channels']:
                    provider_channel = item['provider_channel']
                    if current_provider_app.provider_channel == provider_channel:
                        is_include_fare_provider = True
                    filter_exp = item.get('filter', [])
                    if not self.prefix_routing_match(routing_key_detail, filter_exp):
                        Logger().sinfo('routing filtered %s provider_channel %s' % (filter_exp, provider_channel))
                        continue

                    provider_app = ProviderAutoRepo.select(provider_channel)

                    is_include_available_carrier = False
                    if not provider_app.carrier_list:
                        is_include_available_carrier = True
                    else:
                        for carrier in provider_app.carrier_list:
                            if carrier in  rk_info['flight_number']:
                                is_include_available_carrier = True
                    if not is_include_available_carrier:
                        # 如果验价航班中没有航司列表中的航班则过滤
                        Logger().sinfo('is_include_available_carrier false ')
                        continue
                    pc_rk_info = copy.deepcopy(rk_info)
                    pc_rk_info['provider'] = provider_app.provider
                    pc_rk_info['provider_channel'] = provider_app.provider_channel
                    pc_bp_key = RoutingKey.trans_bp_key(pc_rk_info, is_unserialized=True)
                    search_info = SearchInfo(**self.search_info)
                    rk_item = RoutingKey.serialize(**pc_rk_info)

                    search_info.verify_routing_key = rk_item['encrypted']  # 更新 verify_routing_key
                    if provider_app.is_order_directly:
                        is_order_directly_list.append(provider_app.provider_channel)
                    # 进行仿真下单测试，推送到熔断库，并在下单环节阻断，触发条件：不占位兜底的情况下，并且模拟下单开启
                    if self._operation_config.get('is_simulate_booking_test', 0) and not self._operation_config.get('is_force_hold_seat', 0):
                        ProviderAutoRepo.select(pc_rk_info['provider_channel']).simulate_booking(order_info=search_info, async=True, is_add_fusing=True)

                    Logger().sinfo('pc_bp_key %s' % pc_bp_key)
                    if FusingControl.is_fusing(fusing_type='bp_key', fusing_var=pc_bp_key):
                        Logger().sinfo('bp_key %s is fusing' % pc_bp_key)
                    else:
                        for x in range(provider_app.verify_realtime_search_count):
                            fare_search_sub_providers.append({'provider_app': provider_app, 'info': search_info})

                if not is_include_fare_provider:
                    # 如果验价供应商中不包含运价供应商则会单独发起更新操作， 更新运价供应商的数据，只做更新不做验价使用，五分钟内不进行更新
                    __search_info = SearchInfo(**self.search_info)
                    tb_gevent_spawn(current_provider_app.flight_search, custom_expired_time=300, search_info=__search_info, proxy_pool='F')

                low_price_lock_acquire = False  # 后面发送到稳定器需要此标识进行判断
                if self.search_info.fare_info.enable:
                    Logger().sinfo('is_fare_linkage enabled')
                    self.search_info.fare_info.expired_time = Time.timestamp_s() + self.search_info.fare_info.ttl
                    if self.low_price_provider_channel:

                        # 判断是否该航线已经开始存在稳定器中，如果存在则不会进行二次运价
                        hash = 'low_price_stable_lock_%s|%s|%s|%s|%s|%s|%s' % (
                            self.ota_name, self.search_info.from_airport, self.search_info.to_airport, self.search_info.from_date, self.search_info.ret_date,
                            self.search_info.trip_type, rk_info['flight_number'])
                        my_lock = TBG.redis_conn.redis_pool.lock(hash, timeout=300)
                        have_lock = False
                        try:
                            have_lock = my_lock.acquire(blocking=False)
                            if have_lock:
                                low_price_lock_acquire = True
                                worker_pool.append(tb_gevent_spawn(self.fare_linkage))
                            else:
                                Logger().sinfo('locked_hash %s ' % hash)
                        except Exception as e:
                            Logger().error(e)

                    else:
                        Logger().sinfo('no low_price_provider_channel')
                else:
                    Logger().sinfo('is_fare_linkage disabled %s')

                for sps in fare_search_sub_providers:
                    worker_pool.append(tb_gevent_spawn(self.sub_verify, provider_app=sps['provider_app'], search_info=sps['info']))
                gevent.joinall(worker_pool, timeout=self.verify_search_timeout)

                search_err_code_list = []

                for sps in fare_search_sub_providers:
                    info = sps['info']
                    if info.search_finished and len(info.assoc_search_routings) > 0:
                        for routing in info.assoc_search_routings:
                            fri = FlightRoutingInfo(**routing)
                            self.search_info.assoc_search_routings.append(fri)  # 将所有不同的供应商结果聚合
                    self.search_info.providers_stat.append(
                        {'search_finished': info.search_finished, 'return_status': info.return_status, 'return_details': info.return_details, 'provider_channel': sps['provider_app'].provider_channel})


                is_verify_success = False
                # 确定验价是否正确
                is_exist_routing = False
                is_exist_price = False
                is_exist_cabin = False
                is_exist_child_price = True
                is_exist_flight = False
                price_asc_sorted_assoc_search_routings = sorted(self.search_info.assoc_search_routings, key=lambda x: x.adult_price)  # 价格从低到高排序
                cabin_total_count = 0  # 计算符合条件的成人舱位数量
                same_cabin_routing = None  # 获取同舱routing，用于返回价格
                available_routings = {}  # 可用的routing列表（有仓位、价格合适）
                lowest_cost_price = None  # 止损差外的价格统计，存储的为同舱位最低价
                lowest_cost_adult_price = None
                lowest_provider_channel = None
                # TODO 不考虑没有儿童价位的情况，如果有问题人工介入
                # TODO 优化空间: 可以通过合理分配小孩和成人然后然后计算所占舱位平均价格的方式进行验价，可能盈利点更多

                # 先预设标志位，如果是占位兜底预设为false 在后期根据条件调整为true
                Logger().sinfo('is_order_directly_list %s' % is_order_directly_list)
                if self._operation_config.get('is_force_hold_seat', 0):
                    is_exist_provider_channel = False
                else:
                    is_exist_provider_channel = True
                for flight_routing in price_asc_sorted_assoc_search_routings:


                    fr_rk = RoutingKey.unserialize(flight_routing.routing_key_detail)
                    is_exist_flight = True
                    TB_PROVIDER_CHANNEL = fr_rk['provider_channel']
                    # 判断是否为同航班
                    fr_cc_key = RoutingKey.trans_cc_key(flight_routing.routing_key_detail)
                    fr_cp_key = RoutingKey.trans_cp_key(flight_routing.routing_key_detail)

                    if fr_cc_key != cc_key:
                        continue
                    Logger().debug('cc_key fr_rk %s  rk_info %s' % (fr_cc_key, cc_key))

                    if fr_rk['is_virtual_cabin']:
                        # 如果是虚拟仓的话不进行仓位匹配
                        is_exist_routing = True
                        Logger().sinfo('is_virtual_cabin is_exist_routing')
                    else:
                        if fr_rk['cabin'] != rk_info['cabin']:
                            continue
                        else:
                            Logger().debug('cp_key search_rk: %s  result_rk: %s' % (fr_cp_key, cp_key))
                            is_exist_routing = True

                    # if fr_cp_key != cp_key:  # 不允许降舱的情况下需要对比cp_key,如果本次循环命中，则break
                    #     if self.search_info.allow_cabin_downgrade == 0:
                    #         continue
                    # else:
                    #     Logger().debug('cp_key search_rk: %s  result_rk: %s' % (fr_cp_key, cp_key))
                    #     is_exist_routing = True

                    if self._operation_config.get('is_force_hold_seat', 0):
                        Logger().sinfo("fr_rk['provider_channel'] %s" % fr_rk['provider_channel'])
                        if fr_rk['provider_channel'] in is_order_directly_list:
                            is_exist_provider_channel = True

                    # 舱位修正
                    Logger().sinfo('raw routing cabin count %s ' % flight_routing.segment_min_cabin_count)
                    fr_un_key = RoutingKey.trans_un_key(flight_routing.routing_key_detail)
                    if fr_un_key in self.cabin_revise_repo:

                        flight_routing.segment_min_cabin_count = flight_routing.segment_min_cabin_count - self.cabin_revise_repo[fr_un_key]
                        if flight_routing.segment_min_cabin_count < 0:
                            flight_routing.segment_min_cabin_count = 0
                        Logger().sinfo('after revise routing cabin count %s ' % flight_routing.segment_min_cabin_count)
                    max_pax_count_limit = self._operation_config['max_pax_count_limit'].get(fr_rk['provider_channel'], 10)  # 对仓位展示进行限制
                    Logger().sinfo('max_pax_count_limit %s ' % max_pax_count_limit)
                    if flight_routing.segment_min_cabin_count > max_pax_count_limit:
                        flight_routing.segment_min_cabin_count = max_pax_count_limit

                    if flight_routing.segment_min_cabin_count >= self.search_info.adt_count + self.search_info.chd_count:
                        is_exist_cabin = True
                        Logger().info('is_exist_cabin True')
                    else:
                        # self.search_info.verify_details.append({'rk': flight_routing.routing_key_detail, 'is_exist_cabin': False})
                        continue

                    Logger().sinfo('adult_offer_price %s adult_offer_price %s child_offer_price %s child_cost_price %s child_judge %s' % (
                        (rk_info['adult_price_forsale'] + rk_info['adult_tax']),
                        (fr_rk['adult_price'] + fr_rk['adult_tax']),
                        (rk_info['child_price_forsale'] +
                         rk_info['child_tax']),
                        (fr_rk['child_price'] + fr_rk['child_tax']),
                        (not rk_info['child_price'] or fr_rk[
                            'child_price'])
                    ))

                    # 记录价格

                    # 售价 - 成本价 > 止损 -100
                    verify_stop_loss = self._operation_config['verify_stop_loss'].get(fr_rk['provider_channel'], self._operation_config['verify_stop_loss']['default'])
                    Logger().sinfo('verify_stop_loss %s' % verify_stop_loss)

                    if ((rk_info['adult_price_forsale'] + rk_info['adult_tax']) - (fr_rk['adult_price'] + fr_rk['adult_tax']) >= verify_stop_loss):
                        # 价格合适
                        is_exist_price_for_adult = True
                    else:
                        is_exist_price_for_adult = False
                    if self.search_info.chd_count:
                        if ((rk_info['child_price'] and fr_rk['child_price'])):  # 判断是否存在儿童价
                            if ((rk_info['child_price_forsale'] + rk_info['child_tax']) - (fr_rk['child_price'] + fr_rk['child_tax']) >= verify_stop_loss):
                                # (not rk_info['child_price'] or fr_rk['child_price']) 代码代表如果比较双方任何一方没有儿童价就代表没有儿童舱位，则不需要比较儿童价
                                # 价格合适
                                is_exist_price_for_child = True
                            else:
                                is_exist_price_for_child = False
                        else:
                            is_exist_price_for_child = False
                    else:
                        is_exist_price_for_child = True
                    if is_exist_price_for_adult and is_exist_price_for_child:
                        Logger().info('is_exist_price True')
                        if fr_rk['provider_channel'] in available_routings:
                            if available_routings[fr_rk['provider_channel']].adult_price + available_routings[fr_rk['provider_channel']].adult_tax > fr_rk['adult_price'] + fr_rk['adult_tax']:  # 选择最优价
                                available_routings[fr_rk['provider_channel']] = flight_routing
                        else:
                            available_routings[fr_rk['provider_channel']] = flight_routing  # 单供应商重复routing去重

                        if same_cabin_routing:  # 判断舱位数，返回舱位数少的routing以及舱位数量，保证下单成功率
                            if same_cabin_routing.segment_min_cabin_count > flight_routing.segment_min_cabin_count:
                                same_cabin_routing = flight_routing
                        else:
                            same_cabin_routing = flight_routing
                        self.search_info.verify_details[flight_routing.routing_key_detail] = True
                    else:
                        self.search_info.verify_details[flight_routing.routing_key_detail] = False

                    # 在止损差之外的routing
                    if not lowest_cost_price:
                        lowest_cost_price = fr_rk['adult_price'] + fr_rk['adult_tax']
                        lowest_cost_adult_price = fr_rk['adult_price']
                        lowest_provider_channel = fr_rk['provider_channel']
                    else:
                        if lowest_cost_price > fr_rk['adult_price'] + fr_rk['adult_tax']:  # 保证存储的是最低价
                            lowest_cost_price = fr_rk['adult_price'] + fr_rk['adult_tax']
                            lowest_cost_adult_price = fr_rk['adult_price']
                            lowest_provider_channel = fr_rk['provider_channel']

                if self.search_info.allow_cabin_downgrade == 0:
                    # 不允许降舱
                    TB_PROVIDER_CHANNEL = ''
                    if not is_exist_routing:
                        self.search_info.return_status = 'NOFLIGHT'
                        self.final_result = self.verify_interface_error_output()
                        self.verify_boost()
                    else:
                        if not is_exist_cabin:
                            self.search_info.return_status = 'NOCABIN'
                            self.final_result = self.verify_interface_error_output()
                            self.verify_boost()
                        else:
                            if low_price_lock_acquire:
                                # 运价联动逻辑
                                is_need_low_price_stable = False  # 只有价格在止损差内的routing才会进行低价稳定
                                self.search_info.fare_info.cost_price = lowest_cost_price
                                self.search_info.fare_info.cost_adult_price = lowest_cost_adult_price
                                self.search_info.fare_info.provider_channel = lowest_provider_channel
                                self.search_info.fare_info.offer_price = offer_price
                                self.search_info.fare_info.assoc_fare_info = Random.gen_alpha()
                                self.search_info.fare_info.verify_stop_loss = self._operation_config['verify_stop_loss']
                                self.search_info.fare_info.verify_stop_profit = self._operation_config['verify_stop_profit']
                                if self.search_info.fare_info.enable and self.low_price_provider_channel:
                                    # 运价逻辑
                                    if self.search_info.fare_info.get("ota_r1_price", 0):

                                        # 查询到低价看板数据
                                        if self.search_info.fare_info.offer_price <= self.search_info.fare_info.ota_r1_price:
                                            if self.search_info.fare_info.ota_r2_price > self.search_info.fare_info.ota_r1_price:
                                                sdp = self.search_info.fare_info.ota_r2_price + self.search_info.fare_info.bidding_diff_price - self.search_info.fare_info.cost_price
                                            else:
                                                sdp = 0
                                        else:
                                            # 提升露出
                                            sdp = self.search_info.fare_info.ota_r1_price + self.search_info.fare_info.bidding_diff_price - self.search_info.fare_info.cost_price

                                        # 止损止盈控制
                                        verify_stop_loss = self.search_info.fare_info.verify_stop_loss.get(self.search_info.fare_info.provider_channel, self.search_info.fare_info.verify_stop_loss['default'])
                                        verify_stop_profit = self.search_info.fare_info.verify_stop_profit.get(self.search_info.fare_info.provider_channel, self.search_info.fare_info.verify_stop_profit['default'])

                                        if sdp < verify_stop_loss:  # 如果小于止损则不会进入低价稳定器
                                            self.search_info.fare_info.sdp = verify_stop_loss
                                        elif sdp > verify_stop_profit:
                                            is_need_low_price_stable = True
                                            self.search_info.fare_info.sdp = verify_stop_profit
                                        else:
                                            is_need_low_price_stable = True
                                            self.search_info.fare_info.sdp = sdp

                                        self.search_info.fare_info.low_price = self.search_info.fare_info.cost_price + self.search_info.fare_info.sdp
                                        self.search_info.fare_info.low_adult_price = self.search_info.fare_info.cost_adult_price + self.search_info.fare_info.sdp
                                        if self.search_info.fare_info.low_price - self.search_info.fare_info.offer_price > 0:
                                            # 二次运价价格比一次运价价格高
                                            self.search_info.fare_info.fare_put_mode = 'FARE_UP_TWICE'
                                        elif self.search_info.fare_info.low_price - self.search_info.fare_info.offer_price < 0:
                                            # 二次运价价格比一次运价价格低
                                            self.search_info.fare_info.fare_put_mode = 'FARE_DOWN_TWICE'
                                        else:
                                            # 二次运价价格比一次运价价格相等
                                            self.search_info.fare_info.fare_put_mode = 'FARE_EQ_TWICE'

                                    else:
                                        is_need_low_price_stable = True

                                    DynamicFareRuleEngine.upsert_low_price_cache(ota_name=self.ota_name, from_airport=self.search_info.from_airport, to_airport=self.search_info.to_airport,
                                                                                 from_date=self.search_info.from_date, ret_date=self.search_info.ret_date,
                                                                                 trip_type=self.search_info.trip_type, dfr_hash=rk_info['flight_number'], fare_info=self.search_info.fare_info,
                                                                                 ttl=self.search_info.fare_info.ttl)

                                    Logger().sinfo('self.search_info.fare_info.low_price_stable_enable %s is_need_low_price_stable %s' % (
                                    self.search_info.fare_info.low_price_stable_enable, is_need_low_price_stable))
                                    if self.search_info.fare_info.low_price_stable_enable and is_need_low_price_stable:
                                        routing_key = 'lowprice_stabilizer'
                                        TBG.tb_publisher.send(body={
                                            'ota_name': self.ota_name,
                                            'search_info': {
                                                'rk_info': rk_info,
                                                'from_airport': self.search_info.from_airport,
                                                'to_airport': self.search_info.to_airport,
                                                'from_date': self.search_info.from_date,
                                                'ret_date': self.search_info.ret_date,
                                                'trip_type': self.search_info.trip_type
                                            },
                                            'fare_info': self.search_info.fare_info,
                                            'low_price_provider_channel': self.low_price_provider_channel

                                        }, routing_key=routing_key)


                                    # 该逻辑成立的前提是验价过来是最低价，同程OTA是三个低价同时来验，无法保证是最低价，所以逻辑弃用
                                    # if fare_info.fare_put_mode == 'LOWPRICE_ACCURATE':
                                    #     # 查询到低价看板数据
                                    #     if fare_info.low_price - out_stop_loss_cost_price > self._operation_config['verify_stop_loss']:  # 最高可投放的价格 - 最低成本 > 止损差 表示可以投放
                                    #         # 存储最低价缓存
                                    #         DynamicFareRuleEngine.upsert_low_price_cache(ota_name=self.ota_name, from_airport=self.search_info.from_airport, to_airport=self.search_info.to_airport,
                                    #                                                      from_date=self.search_info.from_date, ret_date=self.search_info.ret_date,
                                    #                                                      trip_type=self.search_info.trip_type, dfr_hash=rk_info['flight_number'], fare_info=fare_info)
                                    #         self.search_info.low_price = fare_info.low_price
                                    #         self.search_info.return_status = 'PRICERISE_LOWPRICE_ACCURATE'
                                    #     else:
                                    #         # 熔断该航班
                                    #         FusingControl.add_fusing(fusing_type='bp_key', fusing_var=bp_key, source='FARE_LINKAGE', ttl=1800)  # 拉黑半个小时
                                    #         self.search_info.return_status = 'PRICERISE_LOWPRICE_FUSING'
                                    # else:
                                    #     # 没有查询到低价看板数据
                                    #     ratio = Random.gen_ratio(min=0.3, max=0.7)  # 随机一个百分比
                                    #     fare_info.low_price = int(fare_info.cost_price + self._operation_config['verify_stop_loss'] * ratio)  # 将价格调整到止损差内,
                                    #     fare_info.fare_put_mode = 'LOWPRICE_FORECAST'
                                    #     Logger().sdebug('LOWPRICE_FORECAST %s ' % fare_info.low_price)
                                    #     DynamicFareRuleEngine.upsert_low_price_cache(ota_name=self.ota_name, from_airport=self.search_info.from_airport, to_airport=self.search_info.to_airport,
                                    #                                                  from_date=self.search_info.from_date, ret_date=self.search_info.ret_date,
                                    #                                                  trip_type=self.search_info.trip_type, dfr_hash=rk_info['flight_number'], fare_info=fare_info)
                                    #     self.search_info.low_price = fare_info.low_price
                                    #     self.search_info.return_status = 'PRICERISE_LOWPRICE_FORECAST'
                                    Logger().sinfo('fare_info %s' % self.search_info.fare_info)
                                else:
                                    Logger().sinfo('is_fare_linkage disabled ')
                            else:
                                Logger().sinfo('low_price_lock not release')

                            if not is_exist_price:
                                # 在止损差外
                                self.search_info.return_status = 'PRICE_RISE'
                                self.final_result = self.verify_interface_error_output()
                                self.verify_boost()
                            else:
                                if is_continue_process:
                                    # 存储ROUTING TODO 存储机制需重构
                                    rk_info['assoc_provider_channels'] = []
                                    for provider_channel, routing in available_routings.items():
                                        routing.request_id = request_id
                                        routing.save()
                                        # 添加关联下单供应商列表
                                        rk_info['assoc_provider_channels'].append('%s#%s' % (provider_channel, routing.flight_routing_id))

                                    if is_exist_provider_channel:  # 如果是占位兜底则该标记用于判断是否存在验舱验价都通过的占位透传供应商
                                        self.search_info.return_status = 'SUCCESS'
                                        # 在routingkey中添加验价时间
                                        rk_info['verify_time'] = current_verify_time

                                        # 更新routingkey
                                        new_rk_info = RoutingKey.serialize(**rk_info)

                                        # 价格返回同舱价格
                                        same_cabin_routing.adult_price_forsale = rk_info['adult_price_forsale']
                                        same_cabin_routing.child_price_forsale = rk_info['child_price_forsale']
                                        same_cabin_routing.adult_price = rk_info['adult_price']
                                        same_cabin_routing.child_price = rk_info['child_price']
                                        same_cabin_routing.child_tax = rk_info['child_tax']
                                        same_cabin_routing.adult_tax = rk_info['adult_tax']
                                        same_cabin_routing.routing_key_detail = new_rk_info['plain']
                                        same_cabin_routing.routing_key = new_rk_info['encrypted']
                                        flight_routing_info = FlightRoutingInfo(**same_cabin_routing)
                                        flight_routing_info.request_id = request_id
                                        flight_routing_info.save()
                                        flight_routing_id = flight_routing_info.flight_routing_id
                                        rk_info['assoc_provider_channels'].append('%s#%s' % ('main', flight_routing_id))  # main 记录的是验价routing

                                        # 更新routingkey
                                        new_rk_info = RoutingKey.serialize(**rk_info)
                                        self.search_info.routing = same_cabin_routing

                                        Logger().sdebug('same_cabin_routing same_cabin_routing %s' % same_cabin_routing)
                                        # Logger().sdebug('same_cabin_routing.adult_price_forsale %s ' % same_cabin_routing.adult_price_forsale)
                                        self.search_info.verify_routing_key = new_rk_info['encrypted']
                                        # Logger().sdebug('new_rk_info %s ' % new_rk_info)
                                        self.after_verify_interface(self.search_info)
                                    else:
                                        self.search_info.return_status = 'NOPROVIDER'  # 在占位兜底的情况下，代表无符合条件的占位透传的供应商
                                        self.final_result = self.verify_interface_error_output()
                                        self.verify_boost()
                                else:
                                    self.search_info.return_status = 'VIRTUAL_CABIN'  # 虚拟仓必定返回失败
                                    self.final_result = self.verify_interface_error_output()
                                    self.verify_boost()
                    Logger().sinfo('return_status 【%s】' % self.search_info.return_status)
                else:
                    raise Exception('downgrade logic is offline')
                    # 允许降舱 TODO 此分支逻辑暂时无法使用 受新模式影响 2019-01-30
                    # if cabin_total_count < self.search_info.adt_count + self.search_info.chd_count:
                    #     self.search_info.return_status = 'NOCABIN'
                    #     self.final_result = self.verify_interface_error_output()
                    #     self.verify_boost()
                    # else:
                    #     self.search_info.return_status = 'SUCCESS'
                    #
                    #     # 价格返回同舱价格,因为降舱有可能找不到同舱的情况，所以此处需要新建routing填充价格信息，TODO 由于此处routing信息获取不全（仅包含价格信息），后续有可能采用redis存储搜索过来的routing信息
                    #
                    #     fri = FlightRoutingInfo()
                    #     fri.adult_price_forsale = rk_info['adult_price_forsale']
                    #     fri.child_price_forsale = rk_info['child_price_forsale']
                    #     fri.adult_price = rk_info['adult_price']
                    #     fri.adult_tax = rk_info['adult_tax']
                    #     fri.child_price = rk_info['child_price']
                    #     fri.child_tax = rk_info['child_tax']
                    #     rk = RoutingKey.serialize(**rk_info)
                    #
                    #     fri.routing_key_detail = rk['plain']
                    #     fri.routing_key = rk['encrypted']
                    #     fri.reference_cabin = rk_info['cabin']
                    #     fri.reference_cabin_grade = rk_info['cabin_grade']  # TODO 因为无法取到舱等，暂时使用舱位
                    #     self.search_info.routing = fri
                    #
                    #     # 在routingkey中添加验价时间
                    #     rk_info['verify_time'] = current_verify_time
                    #
                    #     # 更新routingkey
                    #     new_rk_info = RoutingKey.serialize(**rk_info)
                    #     self.search_info.verify_routing_key = new_rk_info['encrypted']
                    #
                    #     self.after_verify_interface(self.search_info)

        except (FlightSearchException, FlightSearchCritical) as e:
            self.search_info.return_status = 'PROVIDER_ERROR'
            self.final_result = self.verify_interface_error_output()
            self.verify_boost()
        except FusingException as e:
            self.search_info.return_status = 'FUSING'
            self.final_result = self.verify_interface_error_output()
            self.verify_boost()
        except NotAllowChildException as e:
            self.search_info.return_status = 'NOT_ALLOW_CHILD'
            self.final_result = self.verify_interface_error_output()
            self.verify_boost()
        except ProviderVerifyException as e:
            self.search_info.return_status = 'PROVIDER_VERIFY_ERROR'
            self.final_result = self.verify_interface_error_output()
            self.verify_boost()
        except ProviderVerifyFail as e:
            self.search_info.return_status = 'PROVIDER_VERIFY_FAIL'
            self.final_result = self.verify_interface_error_output()
            self.verify_boost()
        except Exception as e:
            Logger().error(e)
            self.search_info.return_status = 'ERROR'
            self.final_result = self.verify_interface_error_output()
            self.verify_boost()

    def before_verify_interface(self, req_body):
        """
        验价接口，

        """
        Logger().sinfo('before_verify_interface start')
        try:
            self.search_info = SearchInfo()
            self.search_info.ota_work_flow = self.work_flow
            self._before_verify_interface(req_body)
            return
        except Exception as e:
            Logger().serror('before_verify_interface failed')
        raise VerifyInterfaceException

    def _before_verify_interface(self, req_body):
        """
        验价接口，

        根据fromsegments 列表中的第一个segment的depairport 和最后一个的arrairport 确定 出发地和目的地
        根据第一个segment的起飞时间确定 起飞日期
        根据第一个segment的舱位数量确认成人位置
        寻找查询结果中的第一个去程航班的起飞时间、降落时间、舱位信息、舱位数量、航班号是否相等确认该所属Routing

        :return:
        """
        raise NotImplementedError

    def after_verify_interface(self, search_info):
        """
        验价接口，
        :param result search返回
        """
        Logger().sinfo('after_verify_interface start')
        try:

            is_success = self._after_verify_interface(search_info)
            if not is_success:
                Logger().swarn('after_verify_interface not success')
            return is_success
        except Exception as e:
            Logger().serror('after_verify_interface failed')
        raise VerifyInterfaceException

    def _after_verify_interface(self, result):
        """
        验价接口，

        :param result:
        :return: 是否成功需要返回 True or False
        """
        raise NotImplementedError

    @logger_config('SUB_ORDER')
    def sub_order(self, provider_app, order_info):
        """
        生单子线程
        :param order_info:
        :return:
        """
        TB_PROVIDER = provider_app.provider
        TB_PROVIDER_CHANNEL = provider_app.provider_channel
        start_time = Time.timestamp_ms()
        order_info.provider = provider_app.provider
        order_info.provider_channel = provider_app.provider_channel
        order_info.operation_product_type = provider_app.operation_product_type
        order_info.operation_product_mode = provider_app.operation_product_mode
        order_info.rk_info['provider'] = provider_app.provider
        order_info.rk_info['provider_channel'] = provider_app.provider_channel

        cc_key = RoutingKey.trans_cc_key(order_info.rk_info, is_unserialized=True)
        cp_key = RoutingKey.trans_cp_key(order_info.rk_info, is_unserialized=True)
        bp_key = RoutingKey.trans_bp_key(order_info.rk_info, is_unserialized=True)

        if self.is_rk_fusing(bp_key):
            order_info.return_status = 'FUSING'
            Logger().sinfo('bp_key %s is fusing' % bp_key)

        else:
            pre_order_check_result = provider_app.pre_order_check(self.order_info)
            if pre_order_check_result in ['CHECK_SUCCESS']:

                if provider_app.is_order_directly:
                    # 占位透传
                    Logger().sinfo('provider_booking_task start')
                    try:
                        # pax_infos = []
                        # for pax in fo_pax_list:
                        #     # pax的model实例在下单时候无法使用，所以只能找到对应的paxInfo传入生单
                        #     pi = [x for x in self.order_info.passengers if x['used_card_no'] == pax.used_card_no][0]
                        #     pi.person_id = pax.person.id  # 防止在register模块中存储任何信息
                        #     pax_infos.append(pi)
                        order_info.passengers = self.order_info.passengers

                        order_info.sub_order_id = None  # 防止在register模块中存储任何信息
                        order_info.flight_order_id = None  # 防止在register模块中存储任何信息

                        provider_app.booking(order_info=order_info)
                        if order_info.provider_order_status == 'BOOK_SUCCESS_AND_WAITING_PAY':
                            Logger().sinfo('is_order_directly order success')
                            order_info.return_status = 'SUCCESS'

                    except Critical as e:
                        Logger().serror(e)
                    except BookingException as e:
                        Logger().serror(e)
                else:

                    # try:
                    #     flight_routing = provider_app.verify(search_info=SearchInfo(**self.order_info))  # 调用供应商验价模块去验价
                    #     assoc_search_routings = [flight_routing]
                    # except NotImplementedError as e:
                    assoc_search_routings = []
                    fare_search_sub_providers = []
                    worker_pool = []
                    for x in range(provider_app.order_realtime_search_count):
                        fare_search_sub_providers.append({'provider_app': ProviderAutoRepo.select(provider_app.provider_channel), 'info': SearchInfo(**order_info)})

                    for sps in fare_search_sub_providers:
                        worker_pool.append(tb_gevent_spawn(self.sub_verify, provider_app=sps['provider_app'], search_info=sps['info']))
                    gevent.joinall(worker_pool, timeout=self.order_search_timeout - 2)  # 保证有足够的时间处理后续逻辑
                    for sps in fare_search_sub_providers:
                        info = sps['info']
                        if info.search_finished and len(info.assoc_search_routings) > 0:
                            assoc_search_routings = info.assoc_search_routings
                            break

                    is_verify_success = False
                    # 确定验价是否正确
                    is_exist_routing = False
                    is_exist_price = False
                    is_exist_cabin = False
                    is_exist_child_price = True
                    is_exist_flight = False
                    price_asc_sorted_assoc_search_routings = sorted(assoc_search_routings, key=lambda x: x.adult_price)  # 价格从低到高排序

                    # Logger().debug('price_asc_sorted_assoc_search_routings %s' % price_asc_sorted_assoc_search_routings)

                    cabin_total_count = 0  # 计算符合条件的成人舱位数量
                    # order_cabin_count = self.search_info.adt_count + self.search_info.chd_count
                    same_cabin_routing = None  # 获取同舱routing，用于返回价格
                    available_routings = {}  # 可用的routing列表（有仓位、价格合适）
                    # TODO 新逻辑不考虑没有儿童价位的情况，如果有问题人工介入
                    # TODO 优化空间: 可以通过合理分配小孩和成人然后然后计算所占舱位平均价格的方式进行验价，可能盈利点更多
                    for flight_routing in price_asc_sorted_assoc_search_routings:
                        fr_rk = RoutingKey.unserialize(flight_routing.routing_key_detail)
                        is_exist_flight = True

                        # 判断是否为同航班
                        fr_cc_key = RoutingKey.trans_cc_key(flight_routing.routing_key_detail)
                        fr_cp_key = RoutingKey.trans_cp_key(flight_routing.routing_key_detail)

                        if fr_cc_key != cc_key:
                            continue
                        Logger().info('cc_key fr_rk %s  rk_info %s' % (fr_cc_key, cc_key))

                        if fr_cp_key != cp_key:  # 不允许降舱的情况下需要对比cp_key,如果本次循环命中，则break
                            if self.order_info.allow_cabin_downgrade == 0:
                                continue
                        else:
                            is_exist_routing = True
                            Logger().sinfo('cp_key fr_rk %s  rk_info %s' % (fr_cp_key, cp_key))

                        Logger().sinfo('adult_offer_price %s adult_offer_price %s child_offer_price %s child_cost_price %s child_judge %s' % (
                            (order_info.rk_info['adult_price_forsale'] + order_info.rk_info['adult_tax']),
                            (fr_rk['adult_price'] + fr_rk['adult_tax']),
                            (order_info.rk_info['child_price_forsale'] +
                             order_info.rk_info['child_tax']),
                            (fr_rk['child_price'] + fr_rk['child_tax']),
                            (not order_info.rk_info['child_price'] or fr_rk[
                                'child_price'])
                        ))

                        verify_stop_loss = self._operation_config['verify_stop_loss'].get(fr_rk['provider_channel'], self._operation_config['verify_stop_loss']['default'])
                        if ((order_info.rk_info['adult_price_forsale'] + order_info.rk_info['adult_tax']) - (fr_rk['adult_price'] + fr_rk['adult_tax']) >= verify_stop_loss):
                            # 价格合适
                            is_exist_price_for_adult = True
                        else:
                            is_exist_price_for_adult = False
                        if order_info.chd_count:
                            if ((order_info.rk_info['child_price'] and fr_rk['child_price'])):  # 判断是否存在儿童价
                                if ((order_info.rk_info['child_price_forsale'] + order_info.rk_info['child_tax']) - (fr_rk['child_price'] + fr_rk['child_tax']) >= verify_stop_loss):
                                    # (not rk_info['child_price'] or fr_rk['child_price']) 代码代表如果比较双方任何一方没有儿童价就代表没有儿童舱位，则不需要比较儿童价
                                    # 价格合适
                                    is_exist_price_for_child = True
                                else:
                                    is_exist_price_for_child = False
                            else:
                                is_exist_price_for_child = False
                        else:
                            is_exist_price_for_child = True
                        if is_exist_price_for_adult and is_exist_price_for_child:                            # 价格合适
                            is_exist_price = True
                            Logger().info('is_exist_price True')
                            # 舱位修正
                            fr_un_key = RoutingKey.trans_un_key(flight_routing.routing_key_detail)
                            if fr_un_key in self.cabin_revise_repo:
                                Logger().sinfo('raw routing cabin count %s ' % flight_routing.segment_min_cabin_count)
                                flight_routing.segment_min_cabin_count = flight_routing.segment_min_cabin_count - self.cabin_revise_repo[fr_un_key]
                                Logger().sinfo('after cabin_revise routing cabin count %s ' % flight_routing.segment_min_cabin_count)
                                if flight_routing.segment_min_cabin_count < 0:
                                    flight_routing.segment_min_cabin_count = 0

                            max_pax_count_limit = self._operation_config['max_pax_count_limit'].get(fr_rk['provider_channel'], 10)  # 对仓位展示进行限制
                            if flight_routing.segment_min_cabin_count > max_pax_count_limit:
                                flight_routing.segment_min_cabin_count = max_pax_count_limit
                            if flight_routing.segment_min_cabin_count >= self.order_info.adt_count + self.order_info.chd_count:
                                is_exist_cabin = True
                                Logger().info('is_exist_cabin True')
                                same_cabin_routing = flight_routing

                            # max_pax_count_limit = self._operation_config['max_pax_count_limit'].get(fr_rk['provider_channel'], 10)  # 对仓位展示进行限制
                            # if flight_routing.segment_min_cabin_count > max_pax_count_limit:
                            #     flight_routing.segment_min_cabin_count = max_pax_count_limit
                            #
                            # cabin_total_count += flight_routing.segment_min_cabin_count
                            # Logger().debug('cabin %s segment_min_cabin_count %s' % (flight_routing.from_segments[0]['cabin'], flight_routing.segment_min_cabin_count))
                            # Logger().debug('cabin_total_count %s' % cabin_total_count)
                            # 保存此routing和座位数
                            # selected_routings.append(flight_routing)

                            # # 判断是否真正变舱，判断舱位是否跟验仓舱位一致
                            # if self.order_info.allow_cabin_downgrade == 1 and fr_rk['cabin'] != pc_rk_info['cabin']:
                            #     self.order_info.is_cabin_changed = 1

                            # if cabin_total_count >= self.order_info.adt_count + self.order_info.chd_count:  # 如果座位数量凑足则退出循环
                            #     is_exist_cabin = True
                            #     break

                        # if self.order_info.allow_cabin_downgrade == 0 and RoutingKey.trans_cp_key(flight_routing.routing_key_detail) == RoutingKey.trans_cp_key(rk_info,
                        #                                                                                                                                          is_unserialized=True):  # 不允许降舱的情况下需要对比cp_key,如果本次循环命中，则break
                        #     break

                    if self.order_info.allow_cabin_downgrade == 0:
                        # 不允许降舱
                        if not is_exist_routing:
                            order_info.return_status = 'NOFLIGHT'

                        else:
                            if not is_exist_price:
                                order_info.return_status = 'PRICERISE'

                            else:
                                if not is_exist_cabin:
                                    order_info.return_status = 'NOCABIN'

                                else:
                                    order_info.routing = same_cabin_routing

                                    order_info.return_status = 'SUCCESS'

                        Logger().sinfo('return_status 【%s】' % order_info.return_status)
                    else:
                        # 允许降舱 TODO 此逻辑暂时不可用 受新模式影响 2019-01-30
                        Logger().swarn('downgrade logic is offline')
            else:
                Logger().sinfo('pre_order_check_result failed %s' % pre_order_check_result)
        # metric 记录

        log = order_info
        log.total_latency = Time.timestamp_ms() - start_time
        log.fare_operation = ''

        metrics_tags = dict(
            ota_name=log.ota_name,
            provider=log.provider,
            provider_channel=log.provider_channel,
            from_date=log.from_date,
            ret_date=log.ret_date,
            from_airport=log.from_airport,
            to_airport=log.to_airport,
            return_status=log.return_status,
            return_details=log.return_details

        )

        if log.return_status == 'SUCCESS':
            success_count = 1
        else:
            success_count = 0

        TBG.tb_metrics.write(
            "OTA.SUB_ORDER",
            tags=metrics_tags,
            fields=dict(
                total_latency=log.total_latency,
                total_count=1,
                success_count=success_count
            ))

    # 生单接口
    @logger_config('OTA_ORDER')
    @db_session
    def order_interface(self, req_body, request_id):
        """
        生单接口
        :return:
        """

        try:
            self.select_config()  # 选择配置
            self.order_info.request_id = request_id
            routing_key = self.order_info.verify_routing_key
            routing_key_detail = RoutingKey.decrypted(routing_key)
            rk_info = RoutingKey.unserialize(routing_key_detail, is_encrypted=False)
            cp_key = RoutingKey.trans_cp_key(rk_info, is_unserialized=True)
            self.order_info.rk_info = rk_info

            # 扩展搜索条件
            self.order_info.from_date = rk_info['from_date']
            self.order_info.from_airport = rk_info['search_from_airport']
            self.order_info.to_airport = rk_info['search_to_airport']
            self.order_info.trip_type = rk_info['trip_type']
            self.order_info.ret_date = rk_info['ret_date']
            self.order_info.attr_competion()  # 属性自动补全

            # 赋值用于metric打点
            current_provider_app = ProviderAutoRepo.select(rk_info['provider_channel'])
            self.current_provider = current_provider_app.provider
            self.current_provider_channel = current_provider_app.provider_channel

            # 构建ota查询数据
            self.order_info.ota_extra_name = self.ota_extra_name
            self.order_info.ota_extra_group = self.ota_extra_group
            self.order_info.ota_name = self.ota_name
            self.order_info.ota_create_order_time = Time.time_str()
            self.order_info.ota_type = 'API'
            self.order_info.product_type = self.product_type
            self.order_info.pnr_code = 'AAAAAA'
            # self.search_info.allow_cabin_downgrade = 0
            Logger().sinfo('search_info.allow_cabin_downgrade %s' % self.order_info.allow_cabin_downgrade)

            # 预置通用错误状态
            pre_order_check_result = 'FAILED'
            flight_order_id = ''

            # 屏蔽自刷航线
            if self.current_provider_channel == 'pdc_faker':
                current_provider_app.flight_search(search_info=self.order_info)
                is_exist_routing = False
                same_cabin_routing = None
                for flight_routing in self.order_info.assoc_search_routings:
                    fr_cp_key = RoutingKey.trans_cp_key(flight_routing.routing_key_detail)
                    if cp_key == fr_cp_key:
                        is_exist_routing = True
                        same_cabin_routing = flight_routing
                if is_exist_routing:
                    pre_order_check_result = current_provider_app.pre_order_check(self.order_info)
                    if pre_order_check_result in ['CHECK_SUCCESS']:
                        self.order_info.return_status = 'SUCCESS'

                        # 价格返回同舱价格
                        same_cabin_routing.adult_price_forsale = rk_info['adult_price_forsale']
                        same_cabin_routing.child_price_forsale = rk_info['child_price_forsale']
                        same_cabin_routing.adult_price = rk_info['adult_price']
                        same_cabin_routing.child_price = rk_info['child_price']
                        same_cabin_routing.child_tax = rk_info['child_tax']
                        same_cabin_routing.adult_tax = rk_info['adult_tax']

                        self.order_info.routing = same_cabin_routing
                        Logger().sinfo('same_cabin_routing same_cabin_routing %s' % same_cabin_routing)
                        self.after_order_interface(self.order_info)
                    else:
                        self.order_info.return_status = 'PAXINFO_INVALID'
                        self.final_result = self.order_interface_error_output()
                else:
                    self.order_info.return_status = 'NOFLIGHT'
                    self.final_result = self.order_interface_error_output()

            else:

                # 订单查重： 查询近30分钟内,被取消的订单
                rkey_pax_hash = self.order_info.gen_rkey_pax_hash()
                Logger().sinfo('rkey_pax_hash %s' % rkey_pax_hash)
                res = select(
                    s for s in FlightOrder if
                    s.rkey_pax_hash == rkey_pax_hash and s.ota_order_status == 'ISSUE_FAIL' and s.ota_create_order_time > Time.curr_date_obj() - datetime.timedelta(seconds=1800))

                old_order = None
                for o in res:
                    old_order = o
                    break
                if old_order:
                    # 存在老订单并且需要替换
                    pre_order_check_result = 'REPLACE_OLD_ORDER'
                    old_order.ota_order_id = self.order_info.ota_order_id
                    old_order.assoc_order_id = self.order_info.assoc_order_id
                    old_order.ota_create_order_time = self.order_info.ota_create_order_time
                    old_order.ota_order_status = 'ORDER_INIT'
                    flight_order_id = old_order.id

                    # 拼装old_order 的 routing 和 segment
                    order_info_input = old_order.to_dict(with_collections=True, related_objects=True)

                    Logger().sinfo("order_info_input.get('routing', '')  %s" % order_info_input.get('routing', ''))
                    # 梳理routing 和 segments
                    if order_info_input.get('routing', ''):
                        routing = order_info_input['routing'].to_dict(with_collections=True, related_objects=True)
                        from_segments = []
                        for f in routing['from_segments']:
                            ff = f.to_dict()
                            fsi = FlightSegmentInfo(**ff)
                            from_segments.append(fsi)

                        ret_segments = []
                        for f in routing['ret_segments']:
                            ff = f.to_dict()
                            fsi = FlightSegmentInfo(**ff)
                            ret_segments.append(fsi)
                        routing['from_segments'] = from_segments
                        routing['ret_segments'] = ret_segments

                        self.order_info.routing = FlightRoutingInfo(**routing)
                        self.after_order_interface(self.order_info)
                else:
                    pre_order_check_result = 'NEW_ORDER'

                if pre_order_check_result == 'NEW_ORDER':

                    # 新订单处理逻辑
                    if self.order_info.routing_range in ['O2I', 'I2O', 'O2O'] and [x for x in self.order_info.passengers if x.used_card_type == 'NI']:
                        # 如果出国不能使用身份证，只能使用护照，这里判断一下
                        self.order_info.return_status = 'CERTIFICATE_ERROR'
                    else:
                        self.sub_order_return_dict = {ProviderAutoRepo.select(x.split('#')[0]): {'order_info': OrderInfo(**self.order_info), 'routing_id': x.split('#')[1]} for x in
                                                      rk_info['assoc_provider_channels'] if x.split('#')[0] != 'main'}

                        worker_pool = []
                        for provider_app, item in self.sub_order_return_dict.items():
                            worker_pool.append(tb_gevent_spawn(self.sub_order, provider_app=provider_app, order_info=item['order_info']))
                        gevent.joinall(worker_pool, timeout=self.order_search_timeout)

                        is_include_success = False
                        flight_order_routing_selected = None  # 选择一个routing作为主订单的关联routing
                        for provider_app, item in self.sub_order_return_dict.items():
                            order_info = item['order_info']
                            if self._operation_config['is_force_hold_seat']:  # 是否设置占位兜底
                                if provider_app.is_order_directly and order_info.return_status == 'SUCCESS':
                                    Logger().sinfo('is_force_hold_seat true is_include_success true ')
                                    is_include_success = True
                                else:
                                    Logger().sinfo('is_force_hold_seat true is_include_success false')
                            else:
                                if order_info.return_status == 'SUCCESS':
                                    is_include_success = True
                                    Logger().sinfo('is_force_hold_seat false is_include_success true')
                                else:
                                    Logger().sinfo('is_force_hold_seat false is_include_success false')

                        if is_include_success:
                            self.order_info.providers_status = 'ORDER_INIT'
                            self.order_info.ota_order_status = 'ORDER_INIT'
                            self.order_info.return_status = 'SUCCESS'
                        else:
                            self.order_info.providers_status = 'ORDER_INIT'
                            self.order_info.ota_order_status = 'TAKE_SEAT_FAILED'
                            self.order_info.return_status = 'TAKE_SEAT_FAILED'

                        # 不管成功失败都会生单
                        flight_order_routing_id = int([x.split('#')[1] for x in rk_info['assoc_provider_channels'] if x.split('#')[0] == 'main'][0])
                        Logger().sinfo('flight_order_routing_id %s' % flight_order_routing_id)
                        self.order_info.routing = FlightRouting.get(id=flight_order_routing_id)
                        # TODO 理论上ORDER接口跟验价数据不一定会一致，如果追求数据精准，此处需要重新更新routing数据
                        # # 关联routing，将信息修改为验价过来的routing价格
                        # self.order_info.routing.adult_price_forsale = rk_info['adult_price_forsale']
                        # self.order_info.routing.child_price_forsale = rk_info['child_price_forsale']
                        # self.order_info.routing.adult_price = rk_info['adult_price']
                        # self.order_info.routing.child_price = rk_info['child_price']
                        #
                        # self.order_info.routing.routing_key = routing_key
                        # self.order_info.routing.routing_key_detail = routing_key_detail

                        # 记录卖出单价
                        self.order_info.ota_adult_price = rk_info['adult_price_forsale']
                        self.order_info.ota_child_price = rk_info['child_price_forsale']

                        # 计算总价 总价包含了 assign_fare_operation 运价后的策略
                        ota_pay_price = 0
                        for pax in self.order_info.passengers:
                            if pax.age_type == 'CHD':
                                ota_pay_price += rk_info['child_price_forsale'] + rk_info['child_tax']
                            elif pax.age_type == 'ADT':
                                ota_pay_price += rk_info['adult_price_forsale'] + rk_info['adult_tax']
                            elif pax.age_type == 'INF':  # 暂时采用儿童价格
                                ota_pay_price += rk_info['child_price_forsale'] + rk_info['child_tax']
                        self.order_info.ota_pay_price = ota_pay_price
                        Logger().sinfo('ota_pay_price %s' % ota_pay_price)

                        # 创建主订单
                        flight_order = self.order_info.save(lazy_flush=False)
                        flight_order_id = flight_order.id
                        TB_ORDER_ID = flight_order_id  # 添加ORDER_ID到日志中
                        fo_pax_list = [pax for pax in flight_order.passengers]

                        quote_summaries = []
                        for provider_app, item in self.sub_order_return_dict.items():
                            TB_PROVIDER_CHANNEL = provider_app.provider_channel
                            routing_id = item['routing_id']
                            Logger().sinfo(
                                'provider_channel %s routing_id %s' % (provider_app.provider_channel, routing_id))
                            order_info = item['order_info']
                            routing = FlightRouting.get(id=int(routing_id))
                            # 创建子订单
                            sub_order_info = SubOrderInfo(**order_info)
                            sub_order_info.passengers = fo_pax_list
                            sub_order_info.routing = routing
                            sub_order_info.raw_routing = self.order_info.routing
                            sub_order_info.flight_order = flight_order
                            sub_order_info.contacts = flight_order.contacts

                            # # 提取将报价信息
                            # quote_summaries[provider_app.provider_channel] = {'cabin_count':routing.segment_min_cabin_count,'adult_price':routing.adult_tax+routing.adult_price}

                            if provider_app.is_order_directly:

                                if order_info.provider_order_status == 'BOOK_SUCCESS_AND_WAITING_PAY':
                                    sub_order_info.provider_order_status = 'BOOK_SUCCESS_AND_WAITING_PAY'
                                    sub_order_info.provider_price = order_info.provider_price
                                    sub_order_info.provider_order_id = str(order_info.provider_order_id)
                                    sub_order_info.pnr_code = order_info.pnr_code
                                    sub_order_info.extra_data = order_info.extra_data
                                    sub_order_info.provider_fee = order_info.provider_fee

                                    # 对舱位进行修正
                                    un_key = RoutingKey.trans_un_key(routing.routing_key_detail, is_unserialized=False, is_encrypted=False)
                                    CabinReviseControl.add(un_key, len(fo_pax_list))
                                    is_success = 'S'
                                else:
                                    sub_order_info.provider_order_status = 'FAIL_CANCEL'  # 订票失败
                                    is_success = 'F'

                                sub_order_info.save()
                            else:
                                if order_info.return_status == 'SUCCESS':
                                    sub_order_info.provider_order_status = 'ORDER_INIT'
                                    # 对舱位进行修正
                                    un_key = RoutingKey.trans_un_key(routing.routing_key_detail, is_unserialized=False, is_encrypted=False)
                                    Logger().sinfo('CabinReviseControl add un_key %s' % un_key)
                                    CabinReviseControl.add(un_key, len(fo_pax_list))
                                    is_success = 'S'
                                else:
                                    sub_order_info.provider_order_status = 'FAIL_CANCEL'  # 查询失败
                                    is_success = 'F'
                                sub_order_info.save()

                            quote_summaries.append('%s@%s￥%s' % (provider_app.provider_channel, is_success, routing.adult_tax + routing.adult_price))

                        if is_include_success:
                            # 任意一个供应商占位或者搜索成功

                            # TODO 为了适配之前的 after_order_interface的数据结构，只能暂时将model的数据转为internal数据
                            tmp_routing = self.order_info.routing.to_dict(with_collections=True, related_objects=True)
                            from_segments = []
                            for f in tmp_routing['from_segments']:
                                ff = f.to_dict()
                                fsi = FlightSegmentInfo(**ff)
                                from_segments.append(fsi)

                            ret_segments = []
                            for f in tmp_routing['ret_segments']:
                                ff = f.to_dict()
                                fsi = FlightSegmentInfo(**ff)
                                ret_segments.append(fsi)
                            tmp_routing['from_segments'] = from_segments
                            tmp_routing['ret_segments'] = ret_segments
                            self.order_info.routing = FlightRoutingInfo(**tmp_routing)
                            self.after_order_interface(self.order_info)
                            pre_order_check_result = 'VERIFY_SUCCESS_SAVE'
                        else:
                            # 全部失败
                            self.final_result = self.order_interface_error_output()


                elif pre_order_check_result in ['REPLACE_OLD_ORDER']:  # 验价通过但是不存储
                    self.order_info.return_status = 'SUCCESS'
                    self.after_order_interface(self.order_info)
                else:
                    self.final_result = self.order_interface_error_output()

                # 微信发送
                if pre_order_check_result in ['VERIFY_SUCCESS_SAVE', 'REPLACE_OLD_ORDER']:  # 只有需要存储的订单和老订单替换才会微信提醒
                    if TBG.global_config['RUN_MODE'] == 'PROD':
                        if self.order_info.is_test_order == 1:
                            test_or_prod_order = '测试'
                        else:
                            test_or_prod_order = '真实'

                        if pre_order_check_result == 'REPLACE_OLD_ORDER':
                            subject = u'[%s]直连接口新订单(替换原订单-%s)' % (test_or_prod_order, old_order.id)
                        else:
                            subject = u'[%s]直连接口新订单' % test_or_prod_order

                        content = u"供应商渠道 {provider_channel}\n主订单号：{flight_order_id}\nOTA名称：{ota_name}\nOTA下单时间：{ota_create_order_time}\nOTA价格：{ota_pay_price}\n出发时间：{from_date}\n出发地机场：{from_airport}\n目的地机场：{to_airport}\n成人数：{adt_count}\n儿童数：{chd_count}".format(
                            provider_channel="\n".join(quote_summaries),
                            flight_order_id=flight_order_id,
                            ota_name=self.order_info.ota_name,
                            ota_create_order_time=self.order_info.ota_create_order_time,
                            ota_pay_price=self.order_info.ota_pay_price,
                            from_date=self.order_info.from_date,
                            from_airport=self.order_info.from_airport,
                            to_airport=self.order_info.to_airport,
                            adt_count=self.order_info.adt_count,
                            chd_count=self.order_info.chd_count,

                        )
                        Pokeman.send_wechat(content=content, subject=subject, level='info', agentid=1000011)

        except Exception as e:
            Logger().serror('error')
            self.final_result = self.order_interface_error_output()

    def before_order_interface(self, req_body):
        """

        :param req_body:
        :return:
        """
        Logger().sinfo('before_order_interface start')
        try:
            self.order_info = OrderInfo()
            self._before_order_interface(req_body)
            self.order_info.ota_work_flow = self.work_flow
            return
        except Exception as e:
            Logger().serror('before_order_interface failed')
        raise OrderInterfaceException

    def _before_order_interface(self, req_body):
        """

        :param req_body:
        :return:
        """
        raise NotImplementedError

    def after_order_interface(self, order_info):
        """

        :param req_body:
        :return:
        """
        Logger().sinfo('after_order_interface start')
        try:

            return self._after_order_interface(order_info)
        except Exception as e:
            Logger().serror('after_order_interface failed')
        raise OrderInterfaceException

    def _after_order_interface(self, order_info):
        """

        :param order_info: order_info class
        :return:
        """
        raise NotImplementedError

    def _export_order_list(self, req_body):
        """
        导出订单列表

        """
        raise NotImplementedError

    @logger_config('OTA_EXPORT_LIST')
    def export_order_list(self, ota_order_status='READY_TO_ISSUE', start_time=None, end_time=None):
        """

        :param req_body:
        :return:
        """

        Logger().sinfo('start')
        try:
            # 如果开始结束时间为默认，则取前后两天的数据
            if start_time is None:
                start_time = Time.curr_date_obj_2() - datetime.timedelta(days=2)
            if end_time is None:
                end_time = Time.curr_date_obj_2() + datetime.timedelta(days=2)

            order_info_list = self._export_order_list(ota_order_status=ota_order_status, start_time=start_time, end_time=end_time)
            return order_info_list
        except Exception as e:
            Logger().serror('failed')
        raise ExportOrderListException

    @logger_config('OTA_EXPORT_DETAIL')
    def export_order_detail(self, ota_order_status='READY_TO_ISSUE', ota_order_id=None):
        """

        :param req_body:
        :return: 返回order_info 类
        """

        Logger().sinfo('start')
        try:

            return self._export_order_detail(ota_order_status=ota_order_status, ota_order_id=ota_order_id)
        except Exception as e:
            Logger().serror('failed')
        raise ExportOrderListException

    def _export_order_detail(self, req_body):
        """
        导出订单详情
        :return: 返回order_info 类
        """
        raise NotImplementedError

    @db_session
    def exists_order_filter(self, ota_order_id_list):
        """
        过滤系统中存在的订单，返回需要操作的订单id列表
        :param ota_order_id_list:
        :return:
        """
        ota_order_id_list = set(ota_order_id_list)
        exists_order_list_from_db = select(o for o in FlightOrder if o.ota_order_id in ota_order_id_list and o.ota_name == self.ota_name)
        exists_order_list = set([])
        for exist_order in exists_order_list_from_db:
            exists_order_list.add(exist_order.ota_order_id)

        return ota_order_id_list - exists_order_list

    @logger_config('OTA_ORDER_BY_POLL')
    def order_by_poll(self, request_id):
        """
        获取出票订单拉取模式
        1. 对比订单池，防止重复拉取
        2. 非自动处理订单提醒、无舱位、验价失败都需录入订单（针对万途定制）
        3. 非初始化状态设置
        :return: 订单
        :return:
        """
        try:
            Logger().sinfo('start')
            order_list = self._order_by_poll()
            if order_list:
                Logger().sinfo('order_list length %s' % len(order_list))
                for o in order_list:
                    with db_session:
                        self.order_info = o
                        # 订单处理流程，基本参考order函数
                        # 预置通用错误状态
                        pre_order_check_result = 'FAILED'
                        flight_order_id = ''
                        quote_summaries = []
                        try:
                            routing_key = o.verify_routing_key
                            routing_key_detail = RoutingKey.decrypted(routing_key)
                            rk_info = RoutingKey.unserialize(routing_key_detail, is_encrypted=False)
                            cp_key = RoutingKey.trans_cp_key(rk_info, is_unserialized=True)
                            o.rk_info = rk_info

                            # 扩展搜索条件
                            o.from_date = rk_info['from_date']
                            o.from_airport = rk_info['search_from_airport']
                            o.to_airport = rk_info['search_to_airport']
                            o.trip_type = rk_info['trip_type']
                            o.ret_date = rk_info['ret_date']
                            o.attr_competion()  # 属性自动补全

                            from_date_obj = datetime.datetime.strptime(o.from_date, '%Y-%m-%d')
                            curr_date_obj = datetime.datetime.strptime(datetime.datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d')
                            dep_diff_days = (from_date_obj - curr_date_obj).days
                            search_info_str = '%s|%s|%s|%s|%s|%s|%s|%s|%s' % (
                                o.from_airport, o.to_airport, o.from_date, o.routing_range, o.trip_type,
                                o.adt_count,
                                o.chd_count, o.inf_count, dep_diff_days)

                            # 构建ota查询数据
                            o.ota_extra_name = self.ota_extra_name
                            o.ota_extra_group = self.ota_extra_group
                            o.ota_name = self.ota_name
                            o.ota_create_order_time = Time.time_str()
                            o.ota_type = 'API'
                            o.product_type = self.product_type
                            o.pnr_code = 'AAAAAA'
                            # self.search_info.allow_cabin_downgrade = 0
                            Logger().sinfo('search_info.allow_cabin_downgrade %s' % o.allow_cabin_downgrade)

                            # 订单查重： 查询近30分钟内,被取消的订单 TODO 替换逻辑有问题
                            rkey_pax_hash = o.gen_rkey_pax_hash()
                            Logger().sinfo('rkey_pax_hash %s' % rkey_pax_hash)
                            res = select(
                                s for s in FlightOrder if
                                s.rkey_pax_hash == rkey_pax_hash and s.ota_order_status == 'ISSUE_FAIL' and s.ota_create_order_time > Time.curr_date_obj() - datetime.timedelta(seconds=1800))

                            old_order = None
                            for oo in res:
                                old_order = oo
                                break
                            if old_order:
                                # 存在老订单并且需要替换
                                Logger().info('REPLACE_OLD_ORDER.....')
                                pre_order_check_result = 'REPLACE_OLD_ORDER'
                                old_order.ota_order_id = o.ota_order_id
                                old_order.assoc_order_id = o.assoc_order_id
                                old_order.ota_create_order_time = o.ota_create_order_time
                                old_order.ota_order_status = 'ORDER_INIT'
                                flight_order_id = old_order.id
                            else:
                                pre_order_check_result = 'NEW_ORDER'

                            if pre_order_check_result == 'NEW_ORDER':

                                # 新订单处理逻辑
                                if o.routing_range in ['O2I', 'I2O', 'O2O'] and [x for x in o.passengers if x.used_card_type == 'NI']:
                                    # 如果出国不能使用身份证，只能使用护照，这里判断一下
                                    o.return_status = 'CERTIFICATE_ERROR'
                                else:

                                    # 此处跟正常验价逻辑不一样，routing不会预先存储，所以需要获取实时routing
                                    # self.sub_order_return_dict = {ProviderAutoRepo.select(x.split('#')[0]): {'order_info': OrderInfo(**o), 'routing_id': x.split('#')[1]} for x in
                                    #                               rk_info['assoc_provider_channels'] if x.split('#')[0] != 'main'}

                                    worker_pool = []
                                    fare_search_sub_providers = []
                                    for item in self._operation_config['order_provider_channels']:
                                        provider_channel = item['provider_channel']
                                        filter_exp = item.get('filter', [])
                                        if not self.prefix_routing_match(search_info_str, filter_exp):
                                            Logger().sinfo('routing filtered %s provider_channel %s' % (filter_exp, provider_channel))
                                            continue
                                        provider_app = ProviderAutoRepo.select(provider_channel)
                                        fare_search_sub_providers.append({'provider_app': provider_app, 'order_info': OrderInfo(**o)})

                                    for item in fare_search_sub_providers:
                                        worker_pool.append(tb_gevent_spawn(self.sub_order, provider_app=item['provider_app'], order_info=item['order_info']))
                                    gevent.joinall(worker_pool, timeout=self.order_search_timeout)

                                    is_include_success = False
                                    flight_order_routing_selected = None  # 选择一个routing作为主订单的关联routing
                                    for item in fare_search_sub_providers:
                                        order_info = item['order_info']
                                        if order_info.return_status == 'SUCCESS':
                                            is_include_success = True
                                            Logger().sinfo('is_force_hold_seat false is_include_success true')
                                        else:
                                            Logger().sinfo('is_force_hold_seat false is_include_success false')

                                    o.ota_order_status = 'READY_TO_ISSUE'
                                    if is_include_success:
                                        # 任意一个供应商占位或者搜索成功
                                        o.providers_status = 'ORDER_INIT'

                                        # 记录卖出单价
                                        o.ota_adult_price = rk_info['adult_price_forsale']
                                        o.ota_child_price = rk_info['child_price_forsale']

                                        # 计算总价 总价包含了 assign_fare_operation 运价后的策略
                                        ota_pay_price = 0
                                        for pax in o.passengers:
                                            if pax.age_type == 'CHD':
                                                ota_pay_price += rk_info['child_price_forsale'] + rk_info['child_tax']
                                            elif pax.age_type == 'ADT':
                                                ota_pay_price += rk_info['adult_price_forsale'] + rk_info['adult_tax']
                                            elif pax.age_type == 'INF':  # 暂时采用儿童价格
                                                ota_pay_price += rk_info['child_price_forsale'] + rk_info['child_tax']
                                        o.ota_pay_price = ota_pay_price
                                        Logger().sinfo('ota_pay_price %s' % ota_pay_price)

                                        # 创建主订单
                                        flight_order = o.save(lazy_flush=False)
                                        flight_order_id = flight_order.id
                                        TB_ORDER_ID = flight_order_id  # 添加ORDER_ID到日志中
                                        fo_pax_list = [pax for pax in flight_order.passengers]

                                        for item in fare_search_sub_providers:
                                            order_info = item['order_info']
                                            provider_app = item['provider_app']
                                            TB_PROVIDER_CHANNEL = provider_app.provider_channel

                                            # 创建子订单
                                            sub_order_info = SubOrderInfo(**order_info)
                                            sub_order_info.passengers = fo_pax_list
                                            sub_order_info.raw_routing = flight_order.routing
                                            sub_order_info.flight_order = flight_order
                                            sub_order_info.contacts = flight_order.contacts

                                            # # 提取将报价信息
                                            # quote_summaries[provider_app.provider_channel] = {'cabin_count':routing.segment_min_cabin_count,'adult_price':routing.adult_tax+routing.adult_price}

                                            if provider_app.is_order_directly:

                                                if order_info.provider_order_status == 'BOOK_SUCCESS_AND_WAITING_PAY':
                                                    sub_order_info.provider_order_status = 'BOOK_SUCCESS_AND_WAITING_PAY'
                                                    sub_order_info.provider_price = order_info.provider_price
                                                    sub_order_info.provider_order_id = str(order_info.provider_order_id)
                                                    sub_order_info.pnr_code = order_info.pnr_code
                                                    sub_order_info.extra_data = order_info.extra_data

                                                    # 对舱位进行修正
                                                    un_key = RoutingKey.trans_un_key(order_info.routing.routing_key_detail, is_unserialized=False, is_encrypted=False)
                                                    CabinReviseControl.add(un_key, len(fo_pax_list))
                                                    is_success = 'S'
                                                else:
                                                    sub_order_info.provider_order_status = 'FAIL_CANCEL'  # 订票失败
                                                    is_success = 'F'

                                                sub_order_info.save()
                                            else:
                                                if order_info.return_status == 'SUCCESS':
                                                    sub_order_info.provider_order_status = 'ORDER_INIT'
                                                    # 对舱位进行修正
                                                    un_key = RoutingKey.trans_un_key(order_info.routing.routing_key_detail, is_unserialized=False, is_encrypted=False)
                                                    Logger().sinfo('CabinReviseControl add un_key %s' % un_key)
                                                    CabinReviseControl.add(un_key, len(fo_pax_list))
                                                    is_success = 'S'
                                                else:
                                                    sub_order_info.provider_order_status = 'FAIL_CANCEL'  # 查询失败
                                                    is_success = 'F'
                                                sub_order_info.save()

                                            quote_summaries.append('%s@%s￥%s' % (provider_app.provider_channel, is_success, order_info.routing.adult_tax + order_info.routing.adult_price))

                                        o.return_status = 'SUCCESS'
                                        pre_order_check_result = 'VERIFY_SUCCESS_SAVE'
                                    else:
                                        # 全部失败
                                        o.return_status = 'TAKE_SEAT_FAILED'


                            elif pre_order_check_result in ['REPLACE_OLD_ORDER']:  # 验价通过但是不存储
                                o.return_status = 'SUCCESS'
                            else:
                                o.return_status = 'UNKNOWN'
                        except Exception as e:
                            o.return_status = str(e)
                            Logger().serror('error')

                        # 微信发送
                        Logger().sinfo('ready to send wechat... pre_order_check_result %s' % pre_order_check_result)
                        if pre_order_check_result in ['VERIFY_SUCCESS_SAVE', 'REPLACE_OLD_ORDER']:  # 只有需要存储的订单和老订单替换才会微信提醒
                            Logger().sinfo('RUN_MODE %s ' % TBG.global_config['RUN_MODE'])
                            if TBG.global_config['RUN_MODE'] == 'PROD':
                                if o.is_test_order == 1:
                                    test_or_prod_order = '测试'
                                else:
                                    test_or_prod_order = '真实'

                                if pre_order_check_result == 'REPLACE_OLD_ORDER':
                                    subject = u'[%s]轮询接口新订单(替换原订单-%s)' % (test_or_prod_order, old_order.id)
                                else:
                                    if o.return_status == 'SUCCESS':
                                        subject = u'[%s]轮询接口新订单-成功' % test_or_prod_order
                                    else:
                                        subject = u'[%s]轮询接口新订单-失败' % test_or_prod_order

                                content = u"供应商渠道 {provider_channel}\n主订单号：{flight_order_id}\nOTA名称：{ota_name}\nOTA下单时间：{ota_create_order_time}\nOTA价格：{ota_pay_price}\n出发时间：{from_date}\n出发地机场：{from_airport}\n目的地机场：{to_airport}\n成人数：{adt_count}\n儿童数：{chd_count}\n错误代码:{return_status}\nRequest_id：{request_id}」".format(
                                    provider_channel="\n".join(quote_summaries),
                                    flight_order_id=flight_order_id,
                                    ota_name=o.ota_name,
                                    ota_create_order_time=o.ota_create_order_time,
                                    ota_pay_price=o.ota_pay_price,
                                    from_date=o.from_date,
                                    from_airport=o.from_airport,
                                    to_airport=o.to_airport,
                                    adt_count=o.adt_count,
                                    chd_count=o.chd_count,
                                    return_status=o.return_status,
                                    request_id=request_id

                                )
                                Logger().sinfo('send wechat')
                                Pokeman.send_wechat(content=content, subject=subject, level='info', agentid=1000011)


        except Exception as e:
            Logger().error(e)

    def _order_by_poll(self):
        """

        """
        raise NotImplementedError

    # def get_order_detail_list(self,ota_order_status=['READY_TO_ISSUE'],start_time=None,end_time=None):
    #     """
    #     通过 list 和dedail 两个接口获取订单详情列表
    #     :param ota_order_status:
    #     :param start_time:
    #     :param end_time:
    #     :return:
    #     """
    #     # TODO 未开发完成
    #     order_info_list = self.export_order_list(ota_order_status=ota_order_status,start_time=start_time,end_time=end_time)
    #     for order_info in order_info_list:
    #         self.export_order_list(ota_order_status=ota_order_status, start_time=start_time, end_time=end_time)

    @logger_config('OTA_SET_ISSUED')
    def set_order_issued(self, order_info):
        """

        :param req_body:
        :return:
        """

        Logger().sinfo('start')
        try:

            return self._set_order_issued(order_info)
        except Exception as e:
            Logger().serror('failed')
        raise SetOrderIssuedException

    def _set_order_issued(self, req_body):
        """
        导出订单列表

        """
        raise NotImplementedError

    @logger_config('OTA_NOTICE_ISSUE')
    @db_session
    def notice_issue_interface(self, req_body):
        """
        通知出票接口
        :return:
        """

        try:
            self.order_info = OrderInfo()
            self.before_notice_issue_interface(req_body)

            # 可支持ota order id 和 关联id
            if self.order_info.ota_order_id:
                flight_order = FlightOrder.get(ota_order_id=self.order_info.ota_order_id)
            elif self.order_info.assoc_order_id:
                flight_order = FlightOrder.get(assoc_order_id=self.order_info.assoc_order_id)
            if flight_order:
                TB_ORDER_ID = flight_order.id
                if flight_order.ota_order_status == 'READY_TO_ISSUE' and self.order_info.ota_order_status == 'ISSUE_FAIL':
                    self.order_info.notice_issue_status = 'INNER_ERROR_7002'
                else:
                    flight_order.ota_order_status = self.order_info.ota_order_status
            else:
                self.order_info.notice_issue_status = 'INNER_ERROR_7001'
            self.after_notice_issue_interface(self.order_info)
        except NoticeIssueInterfaceException as e:
            Logger().serror('notice_issue_interface error')
            raise

    def before_notice_issue_interface(self, req_body):
        """

        :param req_body:
        :return:
        """
        Logger().sinfo('before_notice_issue_interface start')
        try:

            self._before_notice_issue_interface(req_body)
            return
        except Exception as e:
            Logger().serror('before_notice_issue_interface failed')
        raise NoticeIssueInterfaceException

    def _before_notice_issue_interface(self, req_body):
        """

        :param req_body:
        :return:
        """
        raise NotImplementedError

    def after_notice_issue_interface(self, order_info):
        """

        :param req_body:
        :return:
        """
        Logger().sinfo('after_notice_issue_interface start')
        try:
            return self._after_notice_issue_interface(order_info)
        except Exception as e:
            Logger().serror('after_notice_issue_interface failed')
        raise NoticeIssueInterfaceException

    def _after_notice_issue_interface(self, order_info):
        """

        :param order_info: order_info class
        :return:
        """
        raise NotImplementedError

    @logger_config('OTA_NOTICE_PAY')
    @db_session
    def notice_pay_interface(self, req_body):
        """
        通知扣款接口
        :return:
        """

        try:
            self.order_info = OrderInfo()
            self.before_notice_pay_interface(req_body)

            # 可支持ota order id 和 关联id

            if self.order_info.ota_order_id:
                flight_order = FlightOrder.get(ota_order_id=self.order_info.ota_order_id)
            elif self.order_info.assoc_order_id:
                flight_order = FlightOrder.get(assoc_order_id=self.order_info.assoc_order_id)

            if flight_order:
                TB_ORDER_ID = flight_order.id
                if flight_order.ota_order_status == 'ORDER_INIT':

                    if flight_order.ota_pay_price and flight_order.ota_pay_price == self.order_info.ready_to_pay_price:
                        # 采取相应扣款操作，比如支付宝

                        # 记录收支明细
                        if True:
                            # 在此处根据结果更新状态
                            detail_result = 'PAYMENTS_MADE'
                            self.order_info.notice_pay_status = 'SUCCESS'
                            flight_order.ota_order_status = 'READY_TO_ISSUE'
                        else:
                            detail_result = 'FAIL'
                            self.order_info.notice_pay_status = 'INNER_ERROR_4002'

                        # 记录支付日志
                        IncomeExpenseDetail(
                            trade_type='INCOME',
                            trade_sub_type='BUY',
                            flight_order=flight_order,
                            income_source=self.ota_name,
                            pay_amount=flight_order.ota_pay_price,
                            pay_channel=self.pay_channel,  # 从类属性中继承而来
                            pay_result=detail_result
                        )


                    else:
                        self.order_info.notice_pay_status = 'INNER_ERROR_4004'
                else:
                    self.order_info.notice_pay_status = 'INNER_ERROR_4005'

            else:
                self.order_info.notice_pay_status = 'INNER_ERROR_4001'
            self.after_notice_pay_interface(self.order_info)
        except NoticePayInterfaceException as e:
            Logger().serror('notice_pay_interface error')
            raise

    def before_notice_pay_interface(self, req_body):
        """

        :param req_body:
        :return:
        """
        Logger().sinfo('before_notice_pay_interface start')
        try:

            self._before_notice_pay_interface(req_body)
            return
        except Exception as e:
            Logger().serror('before_notice_pay_interface failed')
        raise NoticePayInterfaceException

    def _before_notice_pay_interface(self, req_body):
        """

        :param req_body:
        :return:
        """
        raise NotImplementedError

    def after_notice_pay_interface(self, order_info):
        """

        :param req_body:
        :return:
        """
        Logger().sinfo('after_notice_pay_interface start')
        try:
            return self._after_notice_pay_interface(order_info)
        except Exception as e:
            Logger().serror('after_notice_pay_interface failed')
        raise NoticePayInterfaceException

    def _after_notice_pay_interface(self, order_info):
        """

        :param order_info: order_info class
        :return:
        """
        raise NotImplementedError

    @logger_config('OTA_ORDER_DETAIL')
    @db_session
    def order_detail_interface(self, req_body):
        """
        订单状态详情拉取接口
        :return:
        """

        try:
            self.order_info = OrderInfo()
            self.before_order_detail_interface(req_body)

            # 可支持ota order id 和 关联id
            if self.order_info.ota_order_id:
                flight_order = FlightOrder.get(ota_order_id=self.order_info.ota_order_id)
            elif self.order_info.assoc_order_id:
                flight_order = FlightOrder.get(assoc_order_id=self.order_info.assoc_order_id)
            if flight_order:
                TB_ORDER_ID = flight_order.id
                # 将数据load到对象中
                order_info_input = flight_order.to_dict(with_collections=True, related_objects=True)

                paxs = []
                contacts = []
                ticket_backfill_success = True
                if flight_order.providers_status != 'ALL_SUCCESS':
                    ticket_backfill_success = False
                for p in order_info_input['passengers']:
                    pp = p.person.to_dict()
                    pax_info = PaxInfo(**pp)
                    if not p.ticket_no:
                        ticket_backfill_success = False
                    if flight_order.providers_status == 'ALL_SUCCESS':
                        pax_info.ticket_no = p.ticket_no
                    else:
                        pax_info.ticket_no = ''

                    pax_info.used_card_no = p.used_card_no
                    pax_info.used_card_type = p.used_card_type
                    pax_info.passenger_id = p.passenger_id
                    pax_info.person_id = p.person.id
                    paxs.append(pax_info)

                for c in order_info_input['contacts']:
                    pp = c.to_dict()
                    contact_info = ContactInfo(**pp)
                    contacts.append(contact_info)
                order_info_input['passengers'] = paxs
                order_info_input['contacts'] = contacts

                if order_info_input['ffp_account']:
                    ffp_account = order_info_input['ffp_account'].to_dict(with_collections=True, related_objects=True)
                    ffp_account.pop('reg_person')
                    ffp_account.pop('flight_orders')
                    order_info_input['ffp_account'] = FFPAccountInfo(**ffp_account)
                else:
                    order_info_input['ffp_account'] = None

                # 梳理routing 和 segments
                if order_info_input['routing']:
                    routing = order_info_input['routing'].to_dict(with_collections=True, related_objects=True)
                    from_segments = []
                    for f in routing['from_segments']:
                        ff = f.to_dict()

                        fsi = FlightSegmentInfo(**ff)
                        from_segments.append(fsi)

                    ret_segments = []
                    for f in routing['ret_segments']:
                        ff = f.to_dict()
                        fsi = FlightSegmentInfo(**ff)
                        ret_segments.append(fsi)
                    routing['from_segments'] = from_segments
                    routing['ret_segments'] = ret_segments
                    order_info_input['routing'] = FlightRoutingInfo(**routing)
                if not flight_order.providers_status == 'ALL_SUCCESS':
                    order_info_input['pnr_code'] = ''
                flight_order_id = order_info_input.pop('id')
                order_info = OrderInfo(**order_info_input)
                order_info.flight_order_id = flight_order_id

                self.order_info = order_info

                if ticket_backfill_success:  # 所有票号都返回认为是出票成功
                    flight_order.ota_order_status = 'ISSUE_FINISH'
            else:
                self.order_info.order_detail_status = 'INNER_ERROR_5001'

            self.after_order_detail_interface(self.order_info)
        except OrderDetailInterfaceException as e:
            Logger().serror('order_detail_interface error')
            raise

    def before_order_detail_interface(self, req_body):
        """

        :param req_body:
        :return:
        """
        Logger().sinfo('before_order_detail_interface start')
        try:

            self._before_order_detail_interface(req_body)
            return
        except Exception as e:
            Logger().serror('before_order_detail_interface failed')
        raise OrderDetailInterfaceException

    def _before_order_detail_interface(self, req_body):
        """

        :param req_body:
        :return:
        """
        raise NotImplementedError

    def after_order_detail_interface(self, order_info):
        """

        :param req_body:
        :return:
        """
        Logger().sinfo('after_order_detail_interface start')
        try:
            return self._after_order_detail_interface(order_info)
        except Exception as e:
            Logger().serror('after_order_detail_interface failed')
        raise OrderDetailInterfaceException

    def _after_order_detail_interface(self, order_info):
        """

        :param order_info: order_info class
        :return:
        """
        raise NotImplementedError

    @logger_config('OTA_ORDER_LIST')
    @db_session
    def order_list_interface(self, req_body):
        """
        订单列表拉取接口
        :return:
        """

        try:
            req_body = self.before_order_list_interface(req_body)
            if not req_body.get('start_time', None) or not req_body.get('end_time', None) or not req_body.get('order_status', None):
                self.final_result = json.dumps({'status': 'INNER_ERROR_6002', 'msg': ERROR_STATUS['INNER_ERROR_6001']})
                return
            start_time = req_body['start_time']
            start_time = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
            end_time = req_body['end_time']
            end_time = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
            if (end_time - start_time).total_seconds() >= 86401:  # 时间范围小于一天
                self.final_result = json.dumps({'status': 'INNER_ERROR_6001', 'msg': ERROR_STATUS['INNER_ERROR_6001']})
                return

            order_status = req_body.get('order_status', None)
            if order_status == 'ALL':
                status_filters = ['ISSUE_CANCEL', 'ISSUE_SUCCESS', 'ISSUE_PROCESS']
            else:
                status_filters = order_status
            order_info_list = []
            order_list = select(o for o in FlightOrder if o.ota_create_order_time >= start_time and o.ota_create_order_time <= end_time and o.ota_name == self.ota_name)
            for flight_order in order_list:
                if PROVIDERS_STATUS[flight_order.providers_status]['status_category'] in status_filters:
                    # 将数据load到对象中
                    order_info_input = flight_order.to_dict(with_collections=True, related_objects=True)

                    paxs = []
                    contacts = []

                    for p in order_info_input['passengers']:
                        pp = p.person.to_dict()
                        pax_info = PaxInfo(**pp)

                        # if flight_order.providers_status == 'ALL_SUCCESS':
                        #     pax_info.ticket_no = p.ticket_no
                        # else:
                        #     pax_info.ticket_no = ''
                        pax_info.ticket_no = p.ticket_no if p.ticket_no else ''

                        pax_info.used_card_no = p.used_card_no
                        pax_info.used_card_type = p.used_card_type
                        pax_info.passenger_id = p.passenger_id
                        pax_info.person_id = p.person.id
                        pax_info.pnr = p.pnr
                        paxs.append(pax_info)

                    for c in order_info_input['contacts']:
                        pp = c.to_dict()
                        contact_info = ContactInfo(**pp)
                        contacts.append(contact_info)
                    order_info_input['passengers'] = paxs
                    order_info_input['contacts'] = contacts

                    if order_info_input['ffp_account']:
                        ffp_account = order_info_input['ffp_account'].to_dict(with_collections=True, related_objects=True)
                        ffp_account.pop('reg_person')
                        ffp_account.pop('flight_orders')
                        order_info_input['ffp_account'] = FFPAccountInfo(**ffp_account)
                    else:
                        order_info_input['ffp_account'] = None

                    sub_order = select(i for i in SubOrder if i.flight_order.id == flight_order.id)
                    sub_orders = []
                    for s in sub_order:
                        sub_order_info = s.to_dict()
                        sub_orders.append(SubOrderInfo(**sub_order_info))

                    # 梳理routing 和 segments
                    if order_info_input['routing']:
                        routing = order_info_input['routing'].to_dict(with_collections=True, related_objects=True)
                        from_segments = []
                        for f in routing['from_segments']:
                            ff = f.to_dict()
                            fsi = FlightSegmentInfo(**ff)
                            from_segments.append(fsi)

                        ret_segments = []
                        for f in routing['ret_segments']:
                            ff = f.to_dict()
                            fsi = FlightSegmentInfo(**ff)
                            ret_segments.append(fsi)
                        routing['from_segments'] = from_segments
                        routing['ret_segments'] = ret_segments
                        order_info_input['routing'] = FlightRoutingInfo(**routing)
                    if not flight_order.providers_status == 'ALL_SUCCESS':
                        order_info_input['pnr_code'] = ''
                    flight_order_id = order_info_input.pop('id')
                    order_info = OrderInfo(**order_info_input)
                    order_info.flight_order_id = flight_order_id
                    order_info.sub_orders = sub_orders
                    order_info_list.append(order_info)

            self.after_order_list_interface(order_info_list)
        except OrderListInterfaceException as e:
            Logger().serror('order_list_interface error')
            raise

    def before_order_list_interface(self, req_body):
        """

        :param req_body:
        :return:
        """
        Logger().sinfo('before_order_list_interface start')
        try:

            return self._before_order_list_interface(req_body)

        except Exception as e:
            Logger().serror('before_order_list_interface failed')
        raise OrderListInterfaceException

    def _before_order_list_interface(self, req_body):
        """

        :param req_body:
        :return:
        """
        raise NotImplementedError

    def after_order_list_interface(self, order_info_list):
        """

        :param req_body:
        :return:
        """
        Logger().sinfo('after_order_list_interface start')
        try:
            return self._after_order_list_interface(order_info_list)
        except Exception as e:
            Logger().serror('after_order_list_interface failed')
        raise OrderListInterfaceException

    def _after_order_list_interface(self, order_info_list):
        """

        :param order_info: order_info class
        :return:
        """
        raise NotImplementedError

    def config(self, req_body, req_params):
        """
        自动配置接口
        :return:
        """
        # TODO 暂时先走get参数
        search_interface_status = req_params.get('search_interface_status', None)
        switch_mode = req_params.get('switch_mode', None)
        if search_interface_status and not search_interface_status in ['turn_off', 'turn_on']:
            raise ConfigInterfaceException
        if switch_mode and not switch_mode in ['manual', 'auto']:
            raise ConfigInterfaceException

        operation_config = TBG.config_redis.get_value('operation_config')
        if operation_config:
            operation_config = json.loads(operation_config)
            ota_config = operation_config.get(self.ota_name)
            ota_config_search_interface_status = ota_config['search_interface_status']
            ota_config_switch_mode = ota_config['switch_mode']
            need_update = False
            if search_interface_status:
                need_update = True
                current_search_interface_status = search_interface_status
                operation_config[self.ota_name]['search_interface_status'] = search_interface_status
            else:
                current_search_interface_status = ota_config_search_interface_status
            if switch_mode:
                need_update = True
                current_switch_mode = switch_mode
                operation_config[self.ota_name]['switch_mode'] = switch_mode
            else:
                current_switch_mode = ota_config_switch_mode

            if need_update:
                TBG.config_redis.insert_value('operation_config', json.dumps(operation_config))
            ret = {'msg': '成功', 'status': 'SUCCESS', 'config': {'search_interface_status': {'previous': ota_config_search_interface_status, 'current': current_search_interface_status},
                                                                'switch_mode': {'previous': ota_config_switch_mode, 'current': current_switch_mode}}}
            self.final_result = json.dumps(ret)
        else:
            raise ConfigInterfaceException

    @logger_config('OTA_VERIFY_BOOST')
    def verify_boost(self):
        """
        验价率提升
        :return:
        """
        if TBG.global_config['RUN_MODE'] == 'PROD':
            Logger().info('Start Verify Boost')
            tb_gevent_spawn(self._verify_boost)
        else:
            Logger().warn('TEST env ，Verify Boost not launch')

    def _verify_boost(self):
        Logger().debug('No verify boost implement')
        return


if __name__ == '__main__':
    pass
