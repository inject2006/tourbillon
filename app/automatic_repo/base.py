#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, too-many-arguments, broad-except, anomalous-backslash-in-string
# pylint: disable=missing-docstring, line-too-long, too-few-public-methods
"""
# @Author  : wxt
# @Software: PyCharm
"""

import requests
import random
import gevent
import copy
import datetime
from ..utils.util import Time,tb_gevent_spawn,RoutingKey
from ..utils.exception import *
from ..dao.models import *
from ..dao.internal import *
from ..utils.logger import Logger, logger_config
from ..dao.iata_code import BUDGET_AIRLINE_CODE
from ..controller.http_request import HttpRequest
from ..controller.fusing_limiter import FusingControl
from ..controller.freq_limiter import ProviderSearchFreqLimiter
from ..controller.thirdparty_aux import LowestCabinAux
# from ..gearset.crawler import flight_ota_fare_task
from pony.orm import db_session, select
from app import TBG


class ProviderAutoRepo(object):
    @staticmethod
    def select(vender_class):
        """
        :param vender_class: 传入provider_channel
        :return:
        """
        sub_class_list = []
        exist_class_list = []
        tmp_class_list = ProvderAutoBase.__subclasses__()

        while True:
            have_subclass = False
            for c in tmp_class_list:
                if c.provider_channel == vender_class:
                    return c()
                if c not in exist_class_list and c.__subclasses__():
                    have_subclass = True
                    sub_class_list.append(c)
                    sub_class_list.extend(c.__subclasses__())
                exist_class_list.append(c)
            if not have_subclass:
                break
            else:
                tmp_class_list = copy.deepcopy(sub_class_list)
        raise NoSuchProviderException('No such Provider: %s' % vender_class)

        #
        # for sub_class in ProvderAutoBase.__subclasses__():
        #     if sub_class.__subclasses__():
        #         for sub_sub_class in sub_class.__subclasses__():
        #             if sub_sub_class.provider_channel == vender_class:
        #                 return sub_sub_class()
        #     if sub_class.provider_channel == vender_class:
        #         return sub_class()
        # raise NoSuchOTAException('No such Provider: %s' % vender_class)

    @staticmethod
    def list_all_providers():
        """
        列出所有provider
        :param self:
        :return:
        """
        # providers = set([])
        # for sub_class in ProvderAutoBase.__subclasses__():
        #     if sub_class.__subclasses__():
        #         for sub_sub_class in sub_class.__subclasses__():
        #             providers.add(sub_sub_class.provider)
        #     else:
        #         providers.add(sub_class.provider)
        # return list(providers)

        sub_class_list = []
        exist_class_list = []
        tmp_class_list = ProvderAutoBase.__subclasses__()

        while True:
            have_subclass = False
            for c in tmp_class_list:
                if c not in exist_class_list and c.__subclasses__():
                    have_subclass = True
                    sub_class_list.append(c)
                    sub_class_list.extend(c.__subclasses__())
                exist_class_list.append(c)
            if not have_subclass:
                break
            else:
                tmp_class_list = copy.deepcopy(sub_class_list)
        sub_class_list = [s.provider for s in exist_class_list]
        return list(set(sub_class_list))

    @staticmethod
    def list_all_provider_channels():
        return ProviderAutoRepo.list_provider_channels()

    @staticmethod
    def list_provider_channels(allow_providers=[]):
        """
        列出所有provider
        :param self:
        :return:
        """
        # provider_channels = []
        # for sub_class in ProvderAutoBase.__subclasses__():
        #     if sub_class.__subclasses__():
        #         for sub_sub_class in sub_class.__subclasses__():
        #             provider_channels.append(sub_sub_class.provider_channel)
        #     else:
        #         provider_channels.append(sub_class.provider_channel)
        # return provider_channels

        sub_class_list = []
        exist_class_list = []
        tmp_class_list = ProvderAutoBase.__subclasses__()

        while True:
            have_subclass = False
            for c in tmp_class_list:
                if c not in exist_class_list and c.__subclasses__():
                    have_subclass = True
                    sub_class_list.append(c)
                    sub_class_list.extend(c.__subclasses__())
                exist_class_list.append(c)
            if not have_subclass:
                break
            else:
                tmp_class_list = copy.deepcopy(sub_class_list)
        sub_class_list = [s.provider_channel for s in exist_class_list if (s.provider in allow_providers or allow_providers == []) and s.is_display == True]
        return list(set(sub_class_list))


# @TBG.fcache.memoize(TBG.global_config['FCACHE_TIMEOUT'])
# def get_provider_config(provider):
#     """
#     从 redis中获取配置
#     V1 配置明细
#         operation_product_type = None  # 操作产品类型 VISA 会员折扣、优惠券等
#     operation_product_mode = None
#     is_display = False
#         force_autopay = False  # 是否强制自动支付
#     verify_realtime_search_count = 5  # ota验价次数，默认为5
#     is_order_directly = False  # ota调用生单是否直接调用供应商生单模块
#     assoc_ota_name = None  # 动态运价参数，指定该供应商所关联的OTA，用于爬取自己接口数据进行比价
#     is_include_cabin = True  # 是否包含舱位信息
#     pay_channel = 'ALIPAY'
#     :return:
#     """
#     ret = TBG.config_redis.get_value('provider_config')  #获取老的配置为了向下兼容
#     if ret:
#         return json.loads(ret)[provider]
#     else:
#         ret = TBG.config_redis.get_value('provider_config_%s' % provider)
#         if ret:
#             return json.loads(ret)
#         else:
#             raise FetchOTAConfigException

@TBG.fcache.cached(86400,key_prefix='get_scheduled_airline_cache')
def get_scheduled_airline_cache():
    """
    预读取所有的计划航班数据
    :return:
    """
    cache = {}
    scheduled_airline_cache_list = TBG.redis_conn.redis_pool.keys('scheduled_airline_cache*')
    for scheduled_airline_cache in scheduled_airline_cache_list:
        ret = TBG.redis_conn.redis_pool.get(scheduled_airline_cache)
        if ret:
            cache[scheduled_airline_cache] = set(json.loads(ret))
    # Logger().sdebug('get_scheduled_airline_cache %s' % cache)
    return cache


class ProvderAutoBase(object):
    """
    自动化基类
    """
    timeout = 15  # 请求超时时间
    provider = None  # 子类继承必须赋 名字必须保持唯一
    provider_channel = None  # 子类继承必须赋
    operation_product_type = None  # 操作产品类型 VISA 会员折扣、优惠券等
    operation_product_mode = None
    is_display = False
    # 支付配置
    force_autopay = False  # 是否强制自动支付
    verify_realtime_search_count = 3  # ota验价次数，默认为5
    order_realtime_search_count = 3 # ota生单搜索次数，默认为5
    is_order_directly = False  # ota调用生单是否直接调用供应商生单模块
    is_include_booking_module = False  # 是否包含下单模块
    trip_type_list = ['OW']  # 支持航线类型 单程 往返 默认为单程
    routing_range_list = ['O2O','I2I','O2I','I2O']  # 航段范围 默认支持所有
    no_flight_ttl = 1800 # 无航班缓存超时时间设定
    carrier_list = []  # 供应商所包含的航司列表，如果包含多个并且无法确定，请不要填写，此处会关联执飞航线判断逻辑

    # PR配置迁移至供应商侧
    CACHE_PR_CONFIG = {
        1: {'reference_time': 3600 * 24,'cabin_attenuation':3}, # 过期时间  舱位衰减
        2: {'reference_time': 3600 * 12,'cabin_attenuation':2},
        3: {'reference_time': 3600 * 6,'cabin_attenuation':1},
        4: {'reference_time': 3600 * 3,'cabin_attenuation':1},
        5: {'reference_time': 1800,'cabin_attenuation':0},

    }

    # 2019-01-24 新增
    search_interval_time = 1  # 单位秒 可以是浮点小数

    def __init__(self):
        """
        所继承子类需要使用super初始化

        """
        if self.provider is None or self.provider_channel is None or self.operation_product_type is None or self.operation_product_mode is None or self.pay_channel is None:
            raise NotImplementedError
        self.p_c = "%s_%s" % (self.provider, self.provider_channel)
        self.login_retries = 3  # 登陆重试次数
        self.register_retries = 2  # 注册重试次数
        self.booking_retries = 2  # 下单重试次数
        self.get_coupon_tries = 2  # 优惠券重试次数
        self.common_tries = 3  # 通用重试次数
        self.pay_tries = 1  # 支付重试次数
        self.pre_order_check_tries = 1
        self.get_session_tries = 2  # 获取session重试次数
        self.verify_tries = 2 # 验价重试次数

        self._mobile_info = None  # 接受短信的手机信息
        self._email_info = None  # 邮箱信息

        self.final_result = None  # provider接口返回结果

        # self.l2_cache_expired_seconds = 86400 * 1  # l2缓存过期时间

        # self.provider_config = get_provider_config(self.provider)  # TODO 目前只支持PROVIDER层面  不支持 CHANNEL


    def scheduled_airline_judge(self,from_airport,to_airport,from_date):
        """
        计划航班判断
        :return:
        """
        airline_str = '%s-%s' % (from_airport, to_airport)
        result = None
        for carrier in self.carrier_list:
            cache_key = "scheduled_airline_cache_%s" % carrier
            # Logger().sdebug('cache_key %s' % cache_key)
            cache = get_scheduled_airline_cache()
            if cache.has_key(cache_key):
                if airline_str in cache[cache_key]:
                    result = True
                    # Logger().sdebug('sismember true ')
                else:
                    # Logger().sdebug('sismember false')
                    if result != True:
                        result = False
        return result

    def search_control(self,search_info,allow_expired=False,expired_mode='CABIN',cache_source_mark='UNSET',allow_cabin_attenuation=False,cache_mode='MIX',allow_freq_limit=False,freq_limit_mode='WAIT',freq_limit_wait_timeout=10,allow_update_cache=True,proxy_pool=None,http_session=None,req_retries=1,allow_raise_exception=False,custom_expired_time=None,allow_cabin_revise=False,ba_virtual_cabin_mapping=False,nba_virtual_cabin_mapping=False,is_only_search_scheduled_airline=0,logger_level_lock='INFO'):
        """
        搜索控制层
        包括模块：过期时间、座位衰减、搜索模式、频控、缓存更新
        :param search_info:
        :param allow_expired: 是否允许过期控制，在cache_mode == CACHE or MIX 才会生效
        :param expired_mode: 过期模式，CABIN 根据舱位过期时间判断， FARE 根据运价过期时间判断
        :param allow_cabin_attenuation: 是否允许座位衰减 暂时取消此功能
        :param cache_mode:  搜索模式 CACHE REALTIME MIX MIX_ASYNC 异步模式会将查询请求打到爬虫机器
        :param allow_freq_limit:  是否允许频控 ，在实施搜索时候会进行逻辑判断
        :param freq_limit_mode:  触发频控模式： WAIT:一直等待至获取到访问令牌， NOWAIT : 立即返回，抛出异常 allow_freq_limit== True 时生效
        :param freq_limit_wait_timeout:  如果 freq_limit_mode == WAIT 则等待最长时间，如果超时则抛出异常
        :param allow_update_cache: 是否允许对缓存进行更新，只有在正常返回的情况下才会对缓存数据进行更新
        :param proxy_pool: 指定代理池，默认为直连
        :param http_session:
        :param req_retries: 请求重试次数
        :param cache_source_mark:  如果直连入库，其来源标记，必须使用大写
        :param allow_raise_exception:  是否允许将异常抛出
        :param custom_expired_time:  自定义过期时间，如果赋值，则忽略每个供应商设置的CACHE_PR_CONFIG 采用该时间判断是否采用缓存 条件： allow_expired == True 并且 cache_mode in MIX CACHE
        :param allow_cabin_revise:  是否允许舱位修正
        :param ba_virtual_cabin_mapping:  是否映射虚拟舱位，廉航映射
        :param nba_virtual_cabin_mapping:  是否映射虚拟舱位，非廉航映射
        :param is_only_search_scheduled_airline: 是否只搜索计划航线库存在的航班，如果计划航线库存在的话
        :param logger_level_lock: 日志等级锁，用于调试
        :return:
        """
        TB_PROVIDER_CHANNEL = self.provider_channel
        search_info.attr_competion()
        search_info.search_time = Time.time_str() # 该时间会被用作缓存和路由状态汇报
        start_time = Time.timestamp_ms()
        return_details = set([])
        search_info.rts_search_tries = 1

        Logger().sdebug('Start {from_airport}-{to_airport} {from_date} {trip_type} {ret_date}'.format(from_airport=search_info.from_airport, to_airport=search_info.to_airport,
                                                                                   from_date=search_info.from_date,trip_type=search_info.trip_type,ret_date=search_info.ret_date))
        try:
            # 判断航线类型
            if not search_info.trip_type in self.trip_type_list:
                Logger().sdebug('trip_type %s not supported' % search_info.trip_type)
            elif not search_info.routing_range in self.routing_range_list:
                Logger().sdebug('routing_range %s not supported' % search_info.routing_range)
            else:
                # 此处的缓存参数需要跟爬虫模块的缓存参数保持一致
                if search_info.trip_type == 'OW':
                    ret_date = ''
                else:
                    ret_date = search_info.ret_date
                    if not ret_date:
                        raise FlightSearchCritical('trip_type RT but ret_date is None')

                is_continue_search = True  # 是否继续查询
                # Logger().sdebug('get_scheduled_airline_cache %s' % is_only_search_scheduled_airline)
                if is_only_search_scheduled_airline:
                    # 查询计划航线库是否存在航班
                    # TODO 往返的情况目前考虑不严谨
                    is_scheduled_airline = self.scheduled_airline_judge(from_airport=search_info.from_airport,to_airport=search_info.to_airport,from_date=search_info.from_date)
                    if is_scheduled_airline == True:
                        return_details.add('IS_SCHEDULED_AIRLINE')
                        # Logger().sdebug('IS_SCHEDULED_AIRLINE')
                    elif is_scheduled_airline == False:
                        search_info.return_status = 'NO_SCHEDULED_AIRLINE'  # 非计划航班
                        # Logger().sdebug('NO_SCHEDULED_AIRLINE')
                        is_continue_search = False
                    else:
                        # None 库尚不存在
                        return_details.add('SCHEDULED_AIRLINE_CACHE_NOT_FOUND')
                        # Logger().sdebug('SCHEDULED_AIRLINE_CACHE_NOT_FOUND')
                if is_continue_search:
                    fare_cache_query_params = {
                        'from_date': search_info.from_date,
                        'from_airport': search_info.from_airport,
                        'to_airport': search_info.to_airport,
                        'ret_date': ret_date,
                        'trip_type': search_info.trip_type,
                    }
                    total_count = search_info.adt_count + search_info.chd_count + search_info.inf_count

                    is_expired = False
                    is_hit_cache = False
                    if cache_mode in ['CACHE','MIX','MIX_ASYNC']:
                        # Logger().sdebug('fare_cache querying provider %s' % self.provider )
                        cache_search_info_with_result = TBG.cache_access_object.get(cache_type='fare_cache', provider=self.provider, param_model=fare_cache_query_params,is_decompress=True)
                        if cache_search_info_with_result:
                            is_hit_cache = True
                            cache_search_time = datetime.datetime.strptime(cache_search_info_with_result['search_time'], '%Y-%m-%d %H:%M:%S')
                            # Logger().sdebug('is_hit_cache cache_search_time %s ' %cache_search_time)
                            # Logger().sdebug('cache_search_info_with_result %s'%cache_search_info_with_result)


                            data_source = 'CACHE_SUCCESS_FROM_%s' % cache_search_info_with_result['cache_source']


                            # 权重逻辑
                            pr = cache_search_info_with_result['pr']
                            pass_sec = (Time.curr_date_obj() - cache_search_time).total_seconds()

                            if custom_expired_time:
                                expired_time = custom_expired_time
                            else:
                                if expired_mode == 'FARE':
                                    expired_time = self.CACHE_PR_CONFIG[pr]['fare_expired_time']
                                else:
                                    expired_time = self.CACHE_PR_CONFIG[pr]['cabin_expired_time']

                            # Logger().sdebug('pass_sec %s self.no_flight_ttl %s ' % (pass_sec, self.no_flight_ttl))
                            if not cache_search_info_with_result['assoc_search_routings'] and pass_sec > self.no_flight_ttl and allow_expired:  # 如果没航班并且缓存时间超过三小时，认为超时，需要重新搜索
                                    is_expired = True
                                    # Logger().sdebug('cache no flight [is_expired] ')
                            else:
                                if (allow_expired and pass_sec < expired_time ) or not allow_expired:
                                    # Logger().sdebug('cache [is_not_expired] ')
                                    for routing in cache_search_info_with_result['assoc_search_routings']:
                                        routing['is_valid_cabin'] = routing.get('is_valid_cabin',True)  # 如果获取不到此key 说明为老版本，老版本理论上都应该是可用仓位
                                        if routing.get('cache_source',None):
                                            routing['data_source'] = 'CACHE_SUCCESS_FROM_%s' % routing['cache_source']
                                        else:
                                            routing['data_source'] = data_source
                                        if routing['adult_tax'] and routing['adult_price']:
                                            # 暂时屏蔽没有税或者单价的情况
                                            fri = FlightRoutingInfo(**routing)
                                            search_info.assoc_search_routings.append(fri)
                                else:
                                    is_expired = True
                                    # Logger().sdebug('cache [is_expired] ')


                            if not is_expired:
                                if search_info.assoc_search_routings:
                                    search_info.return_status = data_source
                                else:
                                    search_info.return_status = 'CACHE_NOFLIGHT_FROM_%s'  % cache_search_info_with_result['cache_source']
                                search_info.search_finished = True
                            else:
                                return_details.add('CACHE_EXPIRED')
                                search_info.return_status = 'CACHE_EXPIRED'
                        else:
                            is_hit_cache = False
                            # Logger().sdebug('fare_cache not hit')
                            search_info.return_status = 'CACHE_NOFLIGHT_RECORD'
                            return_details.add('CACHE_NOFLIGHT_RECORD')
                    # Logger().sdebug('is_expired %s is_hit_cache %s ' % (is_expired,is_hit_cache))
                    if  cache_mode == 'MIX_ASYNC' and (is_expired or not is_hit_cache):
                        # 异步mix
                        routing_key = 'flight_ota_fare_task'
                        search_info.provider_channel = self.provider_channel
                        dedup_hash = '{from_date}|{from_airport}|{to_airport}|{ret_date}|{trip_type}|{provider_channel}'.format(
                         from_date=search_info.from_date,
                         from_airport= search_info.from_airport,
                         to_airport= search_info.to_airport,
                         ret_date= ret_date,
                         trip_type= search_info.trip_type,
                         provider_channel=self.provider_channel
                        )
                        TBG.tb_publisher.send(body=search_info,routing_key=routing_key,dedup_hash=dedup_hash,ttl=60)
                        search_info.return_status = 'ASYNC_SUCCESS'

                    elif cache_mode == 'MIX' and (is_expired or not is_hit_cache) or cache_mode == 'REALTIME': # 在混合模式下，缓存过期或者没有命中缓存会进行实时查询， 或者为realtime模式

                        # Logger().sdebug('ota_fare_search REALTIME start')

                        if http_session == None:  # 如果httpsession为空就加锁
                            http_session = HttpRequest(lock_proxy_pool=proxy_pool)
                            # Logger().sdebug('http_session = HttpRequest(lock_proxy_pool=proxy_pool) ' )
                        else:
                            if http_session.lock_proxy_pool == None:
                                # Logger().sdebug('http_session.lock_proxy_pool == None ')
                                # 如果存在httpsession 但是锁为空 则赋值当前环境的默认锁
                                http_session.lock_proxy_pool = proxy_pool
                            else:
                                # 如果http_session本身存在锁，则将当前proxy_pool 刷新
                                proxy_pool = http_session.lock_proxy_pool
                                # Logger().sdebug('proxy_pool = http_session.lock_proxy_pool' )

                        tries = 0
                        while 1:
                            tries += 1
                            search_info.rts_search_tries = tries
                            try:
                                if freq_limit_mode == 'WAIT':
                                    blocking = True
                                else:
                                    blocking = False
                                if not allow_freq_limit or allow_freq_limit and ProviderSearchFreqLimiter.acquire_lock(provider_channel=self.provider_channel,proxy_pool=proxy_pool,blocking=blocking,timeout=freq_limit_wait_timeout) :
                                    search_info.assoc_search_routings = []  # 防止出错重复调用的时候append过多routing
                                    self._flight_search(http_session=http_session, search_info=search_info)
                                    Logger().sdebug('success asrs:{asrs} {from_airport}-{to_airport} {from_date} '.format(from_airport=search_info.from_airport, to_airport=search_info.to_airport,
                                                                                                                         from_date=search_info.from_date,
                                                                                                                         asrs=len(search_info.assoc_search_routings)))

                                    break

                            except Critical as e:
                                return_details.add(str(e))
                                Logger().sinfo('critical {err_code} {from_airport}-{to_airport} {from_date} '.format(from_airport=search_info.from_airport, to_airport=search_info.to_airport,
                                                                                                                     from_date=search_info.from_date, err_code=e.err_code))

                                raise

                            except TBException as e:
                                return_details.add(str(e))
                                Logger().sdebug('Failed {err} Retry={tries}'.format(tries=tries, err=str(e)))
                                if e.err_code == 'HIGH_REQ_LIMIT':  # TODO 高频 trigger
                                    # metric 打点

                                    if http_session.last_http_result and http_session.last_http_result.proxy_pool == 'E':  # 判断真正调用的是否为E池
                                        try:
                                            http_session.request(url='http://1.1.1.1', method='GET')
                                        except Exception as e:
                                            pass
                                if tries == req_retries:
                                    raise
                            except Exception as e:
                                return_details.add(str(e))
                                Logger().serror('Failed {err} Retry={tries}'.format(tries=tries, err=str(e)))
                                if tries == req_retries:
                                    raise
                        valid_search_routings = []
                        for routing in search_info.assoc_search_routings:
                            routing.is_valid_cabin = True  # 是否为可用仓位，此字段不作永久存储，每次都会重新计算
                            # 虚拟仓查询并且映射到segment
                            segment_min_cabin_list = []
                            for segment in routing.from_segments:
                                if segment.cabin == 'N/A':
                                    segment.cabin = 'Y'
                                    routing.is_valid_cabin = False
                                segment_min_cabin_list.append(segment.cabin_count)
                            for segment in routing.ret_segments:
                                if segment.cabin == 'N/A':
                                    segment.cabin = 'Y'
                                    routing.is_valid_cabin = False
                                segment_min_cabin_list.append(segment.cabin_count)
                            if segment_min_cabin_list:
                                routing.segment_min_cabin_count = min(segment_min_cabin_list)
                            else:
                                routing.segment_min_cabin_count = 0

                            routing.data_source = 'RTS_SUCCESS'
                            if routing.adult_tax and routing.adult_price:  # 去掉没有税和价格的情况
                                valid_search_routings.append(routing)
                        search_info.assoc_search_routings = valid_search_routings
                        if search_info.assoc_search_routings:
                            search_info.return_status = 'RTS_SUCCESS'
                        else:
                            search_info.return_status = 'RTS_NOFLIGHT'

                        if allow_update_cache:
                            # 存储至缓存库
                            c_day = Time.curr_date_obj_2()
                            from_date = datetime.datetime.strptime(search_info.from_date, "%Y-%m-%d")

                            if (from_date - c_day).days == 1:
                                set_pr = 5
                            elif (from_date - c_day).days <= 3:
                                set_pr = 4
                            elif 3 < (from_date - c_day).days <= 7:
                                set_pr = 3
                            elif 7 < (from_date - c_day).days <= 15:
                                set_pr = 2
                            else:
                                set_pr = 1
                            # Logger().sdebug('save cache set_pr %s' % set_pr)
                            search_info.pr = set_pr
                            search_info.cache_source = cache_source_mark.upper()

                            if datetime.datetime.strptime(search_info.from_date, '%Y-%m-%d') < datetime.datetime.strptime(
                                    datetime.datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d'):
                                # 搜索日期小于今天零点，不保存
                                expire_seconds = 0

                            else:
                                # 保存到搜索日期

                                expire_seconds = int((datetime.datetime.strptime(search_info.from_date, '%Y-%m-%d') +
                                                      datetime.timedelta(days=1) - datetime.datetime.now()).total_seconds())

                            save_search_info = {
                                'pr':search_info.pr,
                                'cache_source':search_info.cache_source,
                                'search_time':search_info.search_time,
                                'assoc_search_routings':search_info.assoc_search_routings
                            }
                            TBG.cache_access_object.insert(
                                cache_type='fare_cache',
                                provider=self.provider,
                                param_model=fare_cache_query_params,
                                ret_data=save_search_info,
                                expired_time=expire_seconds,
                                is_compress=True
                            )

                    # # 虚拟仓映射逻辑
                    # if ba_virtual_cabin_mapping or nba_virtual_cabin_mapping:
                    #
                    #     for routing in search_info.assoc_search_routings:
                    #         virtual_cabin_list = []
                    #         is_need_to_set_virtual_cabin = True
                    #         is_real_set_virtual_cabin = False
                    #         for segment in routing.from_segments:
                    #             if segment.carrier in BUDGET_AIRLINE_CODE and ba_virtual_cabin_mapping or nba_virtual_cabin_mapping and not segment.carrier in BUDGET_AIRLINE_CODE:
                    #                 virtual_cabin = LowestCabinAux.query(flight_number=segment.flight_number, carrier=segment.carrier)
                    #                 if virtual_cabin:
                    #                     is_real_set_virtual_cabin = True
                    #                     virtual_cabin_list.append(virtual_cabin)
                    #                 else:
                    #                     # 任意一个仓位如果没有虚拟仓则不再进行处理，返回原始舱
                    #                     is_need_to_set_virtual_cabin = False
                    #                     break
                    #             else:
                    #                 virtual_cabin_list.append(segment.cabin)
                    #         if not is_need_to_set_virtual_cabin:
                    #             routing.virtual_cabin = ''
                    #             continue
                    #         routing.virtual_cabin = '-'.join(virtual_cabin_list)
                    #
                    #         if search_info.trip_type == 'RT':
                    #             for segment in routing.ret_segments:
                    #                 if segment.carrier in BUDGET_AIRLINE_CODE and ba_virtual_cabin_mapping or nba_virtual_cabin_mapping and not segment.carrier in BUDGET_AIRLINE_CODE:
                    #                     virtual_cabin = LowestCabinAux.query(flight_number=segment.flight_number, carrier=segment.carrier)
                    #                     if virtual_cabin:
                    #                         is_real_set_virtual_cabin = True
                    #                         virtual_cabin_list.append(virtual_cabin)
                    #                     else:
                    #                         is_need_to_set_virtual_cabin = False
                    #                         break
                    #                 else:
                    #                     virtual_cabin_list.append(segment.cabin)
                    #
                    #             if not is_need_to_set_virtual_cabin:
                    #                 routing.virtual_cabin = ''
                    #                 continue
                    #
                    #         routing.virtual_cabin += ',%s' % '-'.join(virtual_cabin_list)
                    #
                    #         # 执行到此处说明虚拟仓位全部映射成功
                    #         if is_real_set_virtual_cabin:  # 如果其中一个segment真实的映射了虚拟仓并且成功则将此routing认为是虚拟仓映射
                    #             for segment in routing.from_segments:
                    #                 segment.cabin = virtual_cabin_list.pop(0)
                    #             if routing.ret_segments:
                    #                 for segment in routing.ret_segments:
                    #                     segment.cabin = virtual_cabin_list.pop(0)

            search_info.return_details = ','.join(return_details)
            search_info.total_latency = Time.timestamp_ms() - start_time
            # Logger().debug('assoc_search_routings length is {}'.format(len(search_info.assoc_search_routings)))
        except HighFreqLockException as e:
            return_details.add(str(e))
            search_info.return_status = 'RTS_HR_LOCK_ERROR'  # 单独拆分出高频锁获取不到的error
            Logger().sdebug('HighFreqLockException %s ' % str(e))
            search_info.return_details = ','.join(return_details)
            search_info.total_latency = Time.timestamp_ms() - start_time
            if allow_raise_exception:
                raise
        except TBException as e:
            return_details.add(str(e))
            if e.err_code == 'HIGH_REQ_LIMIT':  # TODO 高频 trigger
                search_info.return_status = 'RTS_HIGH_REQ_LIMIT_ERROR'  # 单独拆分出高频错误
            else:
                search_info.return_status = 'RTS_ERROR'
            Logger().sdebug('RTS_ERROR %s ' % str(e))
            search_info.return_details = ','.join(return_details)
            search_info.total_latency = Time.timestamp_ms() - start_time
            if allow_raise_exception:
                raise
        except Exception as e:
            return_details.add(str(e))
            search_info.return_status = 'UNKNOWN_ERROR'
            Logger().serror('search_control error')
            search_info.return_details = ','.join(return_details)
            search_info.total_latency = Time.timestamp_ms() - start_time
            if allow_raise_exception:
                raise

        search_info.search_finished = True
        return search_info

    def iata_code_mapping(self, airport):
        """
        返回城市跟机场不同名的机场三字码
        {"supportTrain": false, "airport": [{"heat": 20, "code": "YEG", "title": "埃德蒙顿机场"}], "code": "YEA", "title": "埃德蒙顿", "entry": ["ADMDJC", "AiDeMengDunJiChang", "ADMD", "AiDeMengDun", "EDMONTON"], "country": "CA", "regional": "AM", "heat": 20, "pinyin": "AiDeMengDun", "hot": false}
        {"supportTrain": false, "airport": [{"heat": 825562, "code": "PEK", "title": "首都机场"}, {"heat": 120353, "code": "NAY", "title": "南苑机场"}], "code": "BJS", "title": "北京", "entry": ["NYJC", "NanYuanJiChang", "BJS", "BeiJingShi", "Beijing Nanyuan Apt"], "country": "CN", "regional": "CN", "heat": 945915, "pinyin": "BeiJingShi", "hot": true}
        {"supportTrain": false, "airport": [{"heat": 500, "code": "KIX", "title": "关西机场"}, {"heat": 0, "code": "ITM", "title": "伊丹机场"}], "code": "OSA", "title": "大阪", "entry": ["YD", "YiDan", "DB", "DaBan", "Itami Airport"], "country": "JP", "regional": "JP", "heat": 500, "pinyin": "DaBan", "hot": true}
        {"supportTrain": false, "airport": [{"heat": 1500, "code": "HND", "title": "东京羽田机场"}, {"heat": 0, "code": "NRT", "title": "东京成田机场"}], "code": "TYO", "title": "东京", "entry": ["DJCTJC", "DongJingChengTianJiChang", "DJ", "DongJing", "NARITA"], "country": "JP", "regional": "JP", "heat": 1500, "pinyin": "DongJing", "hot": true}
        {"supportTrain": false, "airport": [{"heat": 0, "code": "YHM", "title": "约翰·卡尔·芒罗哈密尔顿机场"}, {"heat": 1100, "code": "YYZ", "title": "多伦多皮尔逊机场"}], "code": "YTO", "title": "多伦多", "entry": ["DLDPEXJC", "DuoLunDuoPiErXunJiChang", "DLD", "DuoLunDuo", "PEARSON"], "country": "CA", "regional": "AM", "heat": 1100, "pinyin": "DuoLunDuo", "hot": true}
        {"supportTrain": false, "airport": [{"heat": 0, "code": "MLH", "title": "米卢斯机场"}], "code": "EAP", "title": "弗赖堡", "entry": ["MLS", "MiLuSiJiChang", "FLB", "FuLaiBao", "Mulhouse"], "country": "FR", "regional": "EU", "heat": 0, "pinyin": "FuLaiBao", "hot": false}
        {"supportTrain": true, "airport": [], "code": "KVN", "title": "昆山", "entry": null, "country": "CN", "regional": "CN", "heat": 0, "pinyin": "KunShan", "hot": false}
        {"supportTrain": false, "airport": [{"heat": 900, "code": "LHR", "title": "伦敦希思罗机场"}, {"heat": 0, "code": "LGW", "title": "伦敦盖特威克机场"}], "code": "LON", "title": "伦敦", "entry": ["LDGTWKJC", "LunDunGaiTeWeiKeJiChang", "LD", "LunDun", "London Gatwick Airport"], "country": "GB", "regional": "EU", "heat": 900, "pinyin": "LunDun", "hot": true}
        {"supportTrain": false, "airport": [{"heat": 9, "code": "YUL", "title": "蒙特利尔特鲁多机场"}], "code": "YMQ", "title": "蒙特里尔", "entry": ["MTLETLDJC", "MengTeLiErTeLuDuoJiChang", "MTLE", "MengTeLiEr", "PIERRE ELLIOTT TRUDEAU "], "country": "CA", "regional": "AM", "heat": 9, "pinyin": "MengTeLiEr", "hot": false}
        {"supportTrain": true, "airport": [], "code": "QHX", "title": "琼海", "entry": null, "country": "CN", "regional": "CN", "heat": 0, "pinyin": "QIONGHAI ", "hot": false}
        {"supportTrain": true, "airport": [], "code": "SHS", "title": "沙市", "entry": null, "country": "CN", "regional": "CN", "heat": 0, "pinyin": "ShaShi", "hot": false}
        {"supportTrain": false, "airport": [{"heat": 0, "code": "SBP", "title": "圣路易斯 - 奥比斯波县机场"}], "code": "CSL", "title": "圣路易斯奥比斯波", "entry": ["SLYS - ABSBXJC", "ShengLuYiSi - AoBiSiBoXianJiChang", "SLYSABSB", "ShengLuYiSiAoBiSiBo", "COUNTY"], "country": "US", "regional": "AM", "heat": 0, "pinyin": "ShengLuYiSiAoBiSiBo", "hot": false}
        {"supportTrain": false, "airport": [{"heat": 0, "code": "CIU", "title": "奇波瓦郡机场"}], "code": "SSM", "title": "苏圣玛丽（美国）", "entry": ["QBWJ", "QiBoWaJunJiChang", "SSML", "SuShengMaLi", "Chippewa County Airport"], "country": "US", "regional": "AM", "heat": 0, "pinyin": "SuShengMaLi", "hot": false}
        {"supportTrain": true, "airport": [], "code": "SZV", "title": "苏州", "entry": null, "country": "CN", "regional": "CN", "heat": 0, "pinyin": "SuZhou", "hot": false}
        {"supportTrain": true, "airport": [], "code": "TVX", "title": "桐乡", "entry": null, "country": "CN", "regional": "CN", "heat": 0, "pinyin": "TongXiang", "hot": false}
        {"supportTrain": false, "airport": [{"heat": 779976, "code": "XIY", "title": "咸阳机场"}], "code": "SIA", "title": "西安", "entry": ["XYJC", "XianYangJiChang", "XA", "Xi'An", "Xi an Xianyang Apt"], "country": "CN", "regional": "CN", "heat": 779976, "pinyin": "Xi'An", "hot": true}
        {"supportTrain": false, "airport": [{"heat": 1784, "code": "CTS", "title": "札幌"}], "code": "SPK", "title": "札幌", "entry": ["ZH", "ZhaHuang", "ZH", "ZhaHuang", "CHITOSE"], "country": "JP", "regional": "JP", "heat": 1784, "pinyin": "ZhaHuang", "hot": false}
        """
        city_airport_mapping = {
            'YEA': 'YEG',
            'BJS': 'PEK',
            'OSA': 'KIX',
            'TYO': 'HND',
            'YTO': 'YHM',
            'EAP': 'MLH',
            'LON': 'LHR',
            'YMQ': 'YUL',
            'CSL': 'SBP',
            'SSM': 'CIU',
            'SIA': 'XIY',
            'SPK': 'CTS'
        }
        if airport in city_airport_mapping:
            return city_airport_mapping[airport]
        else:
            return airport

    def iata_code_mapping_reverse(self, airport):

        # 通过机场三字码返回城市三字码

        city_airport_mapping = {
            'YEG': 'YEA',
            'PEK': 'BJS',
            'KIX': 'OSA',
            'HND': 'TYO',
            'NRT': 'TYO',
            'YHM': 'YTO',
            'MLH': 'EAP',
            'LHR': 'LON',
            'YUL': 'YMQ',
            'SBP': 'CSL',
            'CIU': 'SSM',
            'XIY': 'SIA',
            'CTS': 'SPK',
            'PVG': 'SHA',
            'GMP': 'SEL',
            'ICN': 'SEL',
            'TSA': 'TPE',
            'YTZ': 'YTO',
            'YKF': 'YTO',
            'YYZ': 'YTO',
            'DME': 'MOW',
            'BKA': 'MOW',
            'SVO': 'MOW',
            'VKO': 'MOW',
            'SWF': 'NYC',
            'EWR': 'NYC',
            'LGA': 'NYC',
            'JFK': 'NYC',
        }
        if airport in city_airport_mapping:
            return city_airport_mapping[airport]
        else:
            return airport

    @property
    def mobile_info(self):
        """
        TODO 后期根据不同供应商选择不同号码，此处先在全局实例中固定下来
        从库中选取手机号码进行操作
        :return: [mobile,sms_device_id]
        """
        if self._mobile_info is None:
            # minfo = TBG.redis_conn.redis_pool.rpoplpush('mobile_repo', 'mobile_repo')
            # minfo = '{}|{}'.format('17891933179', '460075919034679')
            # minfo = '{}|{}'.format('17891961680', '460075919036181')
            minfo = '{}|{}'.format('18368481562', 'xiaomi1')
            if minfo:
                Logger().sinfo('selected minfo %s ' % minfo)
                mobile, sms_device_id = minfo.split('|')
                self._mobile_info = {'mobile': mobile, 'sms_device_id': sms_device_id}
                return self._mobile_info
            else:
                raise NoSmsMobileCritical
        else:
            # Logger().sinfo('selected exists minfo %s ' % self._mobile_info)
            return self._mobile_info

    def change_mobile(self):
        """
        主动触发更换手机号码
        :return:
        """
        minfo = TBG.redis_conn.redis_pool.rpoplpush('mobile_repo', 'mobile_repo')
        if minfo:
            Logger().sinfo('call change_mobile and selected minfo %s ' % minfo)
            mobile, sms_device_id = minfo.split('|')
            self._mobile_info = {'mobile': mobile, 'sms_device_id': sms_device_id}

    @property
    def email_info(self):
        """

        :return: [mobile,sms_device_id]
        """
        if self._email_info is None:
            einfo = TBG.redis_conn.redis_pool.rpoplpush('email_repo', 'email_repo')
            if einfo:

                address, domain, user, password, pop3_server, email_type = einfo.split('|')
                if email_type == 'ENTERPRISE':
                    # 企业邮箱需要随机出邮箱地址
                    address = Random.gen_email(domain=domain)
                self._email_info = {'address': address, 'domain': domain, 'user': user, 'password': password, 'pop3_server': pop3_server}
                Logger().sinfo('selected email info %s ' % self._email_info)
                return self._email_info
            else:
                raise NoEmailCritical
        else:
            # Logger().sinfo('selected exists email info %s ' % self._email_info)
            return self._email_info

    def change_email(self):
        """
        主动触发更换手机号码
        :return:
        """
        einfo = TBG.redis_conn.redis_pool.rpoplpush('email_repo', 'email_repo')
        if einfo:

            address, domain, user, password, pop3_server, email_type = einfo.split('|')
            if email_type == 'ENTERPRISE':
                # 企业邮箱需要随机出邮箱地址
                address = Random.gen_email(domain=domain)

            self._email_info = {'address': address, 'domain': domain, 'user': user, 'password': password, 'pop3_server': pop3_server}
            Logger().sinfo('call change_email and selected email info %s ' % self._email_info)

    @logger_config('PD_ORDER_SPLIT', True)
    def order_split(self, order_info,passengers):
        """
        订单拆分逻辑
        :return:返回乘机人组合列表
        [{'passengers':[],"contacts":[]},]
        """

        splits = self._order_split(order_info=order_info,passengers=passengers)
        Logger().sdebug('splits %s ' % splits)
        return splits

    def _order_split(self, order_info,passengers):
        """
        默认将所有乘机人和联系人放入一个子订单中
        :param order_info:
        :return:
        """
        return [[x for x in order_info.passengers]]

    def save(self, data, query_params):
        """
        标准化后存储缓存库
        :return:
        """

        fmt_data = self.to_format(data)

        TBG.cache_access_object.insert(cache_type='farecache', provider=self.p_c, param_model=query_params, ret_data=fmt_data)


    def _get_session(self):
        """

        :return:
        """
        raise NotImplementedError

    @logger_config('PD_GET_SESSION', True)
    def get_session(self,renew=False,param_model={},expired_time=600):
        """
        expired_time session存储缓存过期时间
        param_model: 自定义查询参数字典，不做约束
        renew 是否更新session， true 更新session false 返回缓存session
        用于特殊需要其他非登陆session的提供

        :return: [{'session_type':'header','name':'acw_sc_v3','value':acw_sc_v3},{'session_type':'header','name':'acw_tc','value':acw_tc}]
        """

        start_time = Time.timestamp_ms()
        ret = None
        raise_exception = None
        TB_PROVIDER_CHANNEL = self.provider_channel

        Logger().sinfo('Get Session Start ')

        tries = 0
        while 1:
            tries += 1
            try:
                if renew:
                    session_data = self._get_session()
                    if session_data:
                        TBG.cache_access_object.insert(cache_type='extra_session', provider=self.p_c,
                                                   param_model=param_model, ret_data=session_data,expired_time=expired_time)
                        Logger().sdebug('renew session_data %s' % session_data)
                        ret = session_data
                    else:
                        raise GetSessionException
                else:
                    session_data = TBG.cache_access_object.get(cache_type='extra_session', provider=self.p_c, param_model=param_model)
                    if session_data:
                        Logger().sdebug('cached session_data %s' % session_data)
                        ret = session_data
                    else:
                        session_data = self._get_session()
                        if session_data:
                            TBG.cache_access_object.insert(cache_type='extra_session', provider=self.p_c,
                                                       param_model=param_model, ret_data=session_data, expired_time=expired_time)
                            Logger().sdebug('cache expired and renew session_data %s' % session_data)
                            ret = session_data
                        else:
                            raise GetSessionException
                break
            except Critical as e:
                raise_exception = e
                break
            except Exception as e:
                Logger().serror('Get Session Failed Retry={tries}'.format(tries=tries))
                if tries >= self.register_retries:
                    raise_exception = GetSessionException(e)
                    break


        if raise_exception:
            err_code = raise_exception.err_code
        else:
            err_code = ''

        if ret:
            success = 1
        else:
            success = 0

        total_latency = Time.timestamp_ms() - start_time
        TBG.tb_metrics.write(
            "PD_APP",
            tags=dict(
                success=success,
                err_code=err_code,
                action='GET_SESSION',
                provider=self.provider,
                provider_channel=self.provider_channel,

            ),
            fields=dict(
                tries=tries,
                total_latency=total_latency,
                count=1
            ))

        if raise_exception:
            raise raise_exception
        else:
            return ret

    @logger_config('PD_LOGIN', True)
    def login(self, http_session=None, ffp_account_info=None):
        """
        登陆模块
        metrics
        登陆成功/失败
        重试次数
        provider_channel
        异常记录
        :param http_session:
        :param kwargs:
        :return:
        """
        TB_PROVIDER_CHANNEL = self.provider_channel
        username = ffp_account_info.username
        password = ffp_account_info.password
        query_params = {'username': username, 'password': password}
        Logger().sinfo('Login Start {query_params}'.format(query_params=query_params))
        if http_session == None:
            http_session = HttpRequest()

        login_headers = TBG.cache_access_object.get(cache_type='login_headers', provider=self.p_c, param_model=query_params)
        login_session = TBG.cache_access_object.get(cache_type='login_session', provider=self.p_c, param_model=query_params)
        need_login = False
        if login_session:
            Logger().sdebug('login_headers %s' % login_headers)
            Logger().sdebug('login_session %s' % login_session)
            if login_headers:
                http_session.update_headers(login_headers)
            http_session.update_cookie(login_session)
            if self._check_login(http_session):
                Logger().sdebug('Login Session Load Success {query_params}'.format(query_params=query_params))
                self._check_login(http_session)
                return http_session
        Logger().sdebug('Login Session expired {query_params} Start Relogin'.format(query_params=query_params))
        tries = 0
        while 1:
            tries += 1
            try:
                http_session = HttpRequest()
                http_session = self._login(http_session, ffp_account_info)
                if self._check_login(http_session):
                    login_headers = http_session.get_headers()
                    login_session = http_session.get_cookies()
                    if login_headers:
                        TBG.cache_access_object.insert(cache_type='login_headers', provider=self.p_c,
                                                param_model=query_params, ret_data=login_headers)
                    TBG.cache_access_object.insert(cache_type='login_session', provider=self.p_c,
                                               param_model=query_params, ret_data=login_session)
                    Logger().sdebug('save session %s' % login_session)
                    return http_session
            except Critical as e:
                raise
            except Exception as e:
                Logger().serror('Login Failed Retry={tries}'.format(tries=tries))
                if tries >= self.login_retries:
                    raise LoginException(e)

    def _check_login(self, http_session, **kwargs):
        """
        检查是否为登陆状态
        :return:
        """
        pass

    def _login(self, http_session, **kwargs):
        """
        登陆模块
        :return: 登陆成功的httpResult 对象
        """
        pass

    @logger_config('PD_REGISTER', True)
    @db_session
    def register(self, pax_info, http_session=None, sub_order_id=None, flight_order_id=None,is_save=True):
        """
        :param is_save: 是否对账号信息进行存储，默认为存储
        :param http_session:
        :param person_info: 不接受 pax_info
        :return: 返回 FFPAccountInfo,modified_card_no
        """
        start_time = Time.timestamp_ms()
        ret = None
        raise_exception = None
        TB_PROVIDER_CHANNEL = self.provider_channel

        pax_info.attr_competion()  # 补全数据
        Logger().sinfo(
            'Register Start name:{name},last_name:{last_name},first_name:{first_name},gender:{gender},pp:{card_pp},ni:{card_ni},birthdate:{birthdate},nationality:{nationality},email:{email},sub_order_id:{sub_order_id},flight_order_id:{flight_order_id}'.format(
                name=pax_info.name, gender=pax_info.gender, card_pp=pax_info.card_pp,first_name=pax_info.first_name,last_name=pax_info.last_name,
                card_ni=pax_info.card_ni, birthdate=pax_info.birthdate, nationality=pax_info.nationality, email=pax_info.email, sub_order_id=sub_order_id, flight_order_id=flight_order_id))
        if http_session == None:
            http_session = HttpRequest()

        tries = 0
        while 1:
            tries += 1
            try:
                ffp_account_info = FFPAccountInfo()
                if sub_order_id:
                    Logger().sinfo('binding sub_order_id and flight_order_id to ffp_account')
                    ffp_account_info.sub_orders.append(SubOrder[sub_order_id])  # TODO 如果有sub_order_id 传过来可以进行存储
                    ffp_account_info.flight_orders.append(FlightOrder[flight_order_id])
                ffp_account_info_with_result = self._register(http_session=http_session, pax_info=pax_info, ffp_account_info=ffp_account_info)

                if pax_info.modified_card_no:
                    Logger().sinfo('set is_modified_card_no to ffp_account %s ' % pax_info.modified_card_no)
                    ffp_account_info_with_result.is_modified_card_no = 1

                Logger().sinfo('pax_info.person_id %s pax_info.p2fo_id %s' % (pax_info.person_id, pax_info.p2fo_id))
                if is_save:
                    if pax_info.person_id:
                        # 代表已经入库过的，所以不再存储

                        ffp_account_info_with_result.person = pax_info.person_id
                        if pax_info.modified_card_no and pax_info.p2fo_id:
                            # 设置修改后证件号到指定的pax上面，如果没有p2fo则认为无需更新
                            Logger().sinfo('set modified_card_no %s to p2fo_id %s' % (pax_info.modified_card_no, pax_info.p2fo_id))
                            TBG.tourbillon_db.execute('update person_2_flight_order set modified_card_no ="%s" where id = %s ' % (pax_info.modified_card_no, pax_info.p2fo_id))
                            commit()
                            flush()

                    else:
                        pi = PersonInfo(**pax_info)
                        ffp_account_info_with_result.person = pi
                        pi.save(lazy_flush=True)
                    ffp_account_info_with_result.save()
                    Logger().sinfo('register success ffp_account_id %s' % ffp_account_info_with_result.ffp_account_id)

                ret = ffp_account_info_with_result
                break
            except Critical as e:
                raise_exception = e
                break
            except Exception as e:
                Logger().serror('Register Failed Retry={tries}'.format(tries=tries))
                if tries >= self.register_retries:
                    raise_exception = RegisterException(e)
                    break

        if raise_exception:
            err_code = raise_exception.err_code
        else:
            err_code = ''

        if ret:
            success = 1
        else:
            success = 0

        total_latency = Time.timestamp_ms() - start_time
        TBG.tb_metrics.write(
            "PD_APP",
            tags=dict(
                success=success,
                err_code=err_code,
                action='REGISTER',
                provider=self.provider,
                provider_channel=self.provider_channel,

            ),
            fields=dict(
                tries=tries,
                total_latency=total_latency,
                count=1
            ))

        if raise_exception:
            raise raise_exception
        else:
            return ret

    def _register(self, pax_info):
        """
        注册模块
        :param person_input:  person model dict
        :return:  返回register 相关model dict
        """
        pass

    @logger_config('PD_BOOKING', True)
    def booking(self, http_session=None, order_info=None):
        """

        :param http_session:
        :param order_info:
        :return: order_info class
        """
        start_time = Time.timestamp_ms()
        ret = None
        raise_exception = None
        TB_PROVIDER_CHANNEL = self.provider_channel

        Logger().sinfo('Booking Start ')
        if http_session == None:
            http_session = HttpRequest()
        tries = 0
        while 1:
            tries += 1
            try:
                order_info = self._booking(http_session=http_session, order_info=order_info)
                Logger().sinfo('Booking Success ')
                ret = order_info
                break
            except Critical as e:
                raise_exception = e
                break
            except Exception as e:
                Logger().serror('Booking Failed Retry={tries}'.format(tries=tries))
                if tries == self.booking_retries:
                    raise_exception = BookingException(e)
                    break

        if raise_exception:
            err_code = raise_exception.err_code
            rk = order_info.routing.routing_key
            bp_key = RoutingKey.trans_bp_key(rk, is_unserialized=False, is_encrypted=True)
            FusingControl.add_fusing(fusing_type='bp_key', fusing_var=bp_key,
                                     source='provider_order_fail_%s' % order_info.request_id, ttl=900)  # 熔断15分钟
        else:
            err_code = ''

        if ret:
            success = 1
        else:
            success = 0

        total_latency = Time.timestamp_ms() - start_time
        TBG.tb_metrics.write(
            "PD_APP",
            tags=dict(
                success=success,
                err_code=err_code,
                action='BOOKING',
                provider=self.provider,
                provider_channel=self.provider_channel,

            ),
            fields=dict(
                tries=tries,
                total_latency=total_latency,
                count=1
            ))

        if raise_exception:
            raise raise_exception
        else:
            return ret

    def _booking(self, http_session, order_info):
        """
        订票模块
        :return:
        """
        pass

    @logger_config('PD_CHECK_ORDER_STATUS', True)
    def check_order_status(self, ffp_account_info, order_info, http_session=None):
        """
        检查订单状态
        :param http_session:
        :param kwargs:
        :return:
        """
        start_time = Time.timestamp_ms()
        ret = None
        raise_exception = None
        TB_PROVIDER_CHANNEL = self.provider_channel

        Logger().sinfo('check_order_status Start ')
        if http_session == None:
            http_session = HttpRequest()
        tries = 0
        while 1:
            tries += 1
            try:
                self._check_order_status(http_session, ffp_account_info=ffp_account_info, order_info=order_info)
                ret = order_info
                break
            except Critical as e:
                raise_exception = e
                break
            except Exception as e:
                Logger().serror('check_order_status Failed Retry={tries}'.format(tries=tries))
                if tries == self.common_tries:
                    raise_exception = CheckOrderStatusException(e)
                    break

        if raise_exception:
            err_code = raise_exception.err_code
        else:
            err_code = ''

        if ret:
            success = 1
        else:
            success = 0

        total_latency = Time.timestamp_ms() - start_time
        TBG.tb_metrics.write(
            "PD_APP",
            tags=dict(
                success=success,
                err_code=err_code,
                action='CHECK_ORDER_STATUS',
                provider=self.provider,
                provider_channel=self.provider_channel,

            ),
            fields=dict(
                tries=tries,
                total_latency=total_latency,
                count=1
            ))

        if raise_exception:
            raise raise_exception
        else:
            return ret

    def _check_order_status(self, http_session, **kwargs):
        """
        检查订单状态
        :param kwargs:
        :return:
        """
        raise NotImplementedError

    @logger_config('PD_GET_COUPON', True)
    def get_coupon(self, ffp_account_info, http_session=None):
        TB_PROVIDER_CHANNEL = self.provider_channel
        Logger().sinfo('get_coupon Start ')
        if http_session == None:
            http_session = HttpRequest()
        tries = 0
        while 1:
            tries += 1
            try:
                return self._get_coupon(http_session, ffp_account_info=ffp_account_info)
            except Critical as e:
                raise
            except Exception as e:
                Logger().serror('get_coupon Failed Retry={tries}'.format(tries=tries))
                if tries == self.get_coupon_tries:
                    raise GetCouponException(e)

    def _pre_order_check(self, http_session, order_info):
        """
        :return:
        """
        return "CHECK_SUCCESS"

    @logger_config('PD_PRE_ORDER_CHECK', True)
    def pre_order_check(self, order_info, http_session=None):
        """
        订单预检

        :param order_info:
        :param http_session:
        :return:

        PAXINFO_INVALID : 乘客信息无效
        REGISTER_INVALID : 无法注册
        CHECK_SUCCESS : 验证成功
        ORDER_NOTSAVE : 订单不存储
        """

        TB_PROVIDER_CHANNEL = self.provider_channel
        Logger().sinfo('pre_order_check')

        if order_info.allow_cabin_downgrade == 1 and [x for x in order_info.passengers if x.current_age_type(from_date=order_info.from_date, is_aggr_chd_adt=True) == 'CHD']:
            # TODO 如果允许降舱并且包含儿童，则进行人工处理，目前暂不支持儿童降舱，因为儿童分配逻辑复杂
            return 'NEED_MANUAL_DOWNGRADE'
        if http_session == None:
            http_session = HttpRequest()
        tries = 0
        while 1:
            tries += 1
            try:
                return self._pre_order_check(http_session=http_session, order_info=order_info)
            except Critical as e:
                raise
            except Exception as e:
                Logger().serror('pre_order_check Failed Retry={tries}'.format(tries=tries))
                if tries == self.pre_order_check_tries:
                    raise PreOrderCheckException(e)

    def _simulate_booking(self,order_info):
        """
        传入search_info中并没有乘客信息和账号信息，需要自行添加paxinfo 和 accountinfo
        :return:
        """
        raise NotImplementedError

    @logger_config('PD_SIMULATE_BOOKING', True)
    def simulate_booking(self,order_info,async=False,is_add_fusing=True):
        """
        异步仿真下单，用于风险单预检，心跳检测（后期）等
        需要针对不同供应商编写逻辑
        每个un_key 一个小时只检测一次
        :param async: 是否异步执行，用于验价环节
        :param async: 如果下单失败是否添加熔断
        :return:
        """
        bp_key = RoutingKey.trans_bp_key(order_info.verify_routing_key, is_unserialized=False, is_encrypted=True)
        redis_pool = TBG.redis_conn.get_internal_pool()
        if redis_pool.get('simulate_booking_lock_%s' % bp_key):
            Logger().info('simulate_booking_lock_%s is locked' % bp_key)
        else:
            redis_pool.set('simulate_booking_lock_%s' % bp_key, '1', ex=3600)
            if async:
                tb_gevent_spawn(self.sub_simulate_booking, order_info=order_info, is_add_fusing=is_add_fusing)
            else:
                return self.sub_simulate_booking(order_info=order_info, is_add_fusing=is_add_fusing)


    def sub_simulate_booking(self,order_info,is_add_fusing):
        start_time = Time.timestamp_ms()
        ret = None
        raise_exception = None
        TB_PROVIDER_CHANNEL = self.provider_channel

        Logger().sinfo('sub_simulate_booking Start ')

        tries = 0
        is_fusing = 0
        is_need_metric = True
        while 1:
            tries += 1
            try:
                # order_info = OrderInfo()
                order_info.is_simulate_booking = 0   # 设置是否为仿真单的状态，在流转过程中可能会有逻辑判断
                try:
                    self._simulate_booking(order_info=order_info)
                except NotImplementedError as e:
                    is_need_metric = False
                    Logger().sinfo('NoSimulateBookingDefineException')
                    break

                if order_info.is_simulate_booking and not order_info.provider_order_status == 'BOOK_SUCCESS_AND_WAITING_PAY' and is_add_fusing:
                    is_fusing = 1
                    FusingControl.add_fusing(fusing_type='bp_key',fusing_var=RoutingKey.trans_bp_key(order_info.verify_routing_key,is_unserialized=False,is_encrypted=True),source='simulate_booking_fail')
                ret = 'finish'
                break

            except Critical as e:
                raise_exception = e
                break
            except Exception as e:
                Logger().serror('sub_simulate_booking Failed Retry={tries}'.format(tries=tries))
                if tries == self.booking_retries:
                    raise_exception = BookingException(e)
                    break

        if is_need_metric:
            if raise_exception:
                err_code = raise_exception.err_code
            else:
                err_code = ''

            if ret:
                success = 1
            else:
                success = 0

                # TODO 此处后续需要与未知异常分离开来，好判断
                is_fusing = 1
                FusingControl.add_fusing(fusing_type='bp_key', fusing_var=RoutingKey.trans_bp_key(order_info.verify_routing_key, is_unserialized=False, is_encrypted=True),source='simulate_booking_fail')

            total_latency = Time.timestamp_ms() - start_time
            TBG.tb_metrics.write(
                "PD_APP",
                tags=dict(
                    is_fusing=is_fusing,
                    success=success,
                    err_code=err_code,
                    action='SIMULATE_BOOKING',
                    provider=self.provider,
                    provider_channel=self.provider_channel,

                ),
                fields=dict(
                    tries=tries,
                    total_latency=total_latency,
                    count=1
                ))

            if raise_exception:
                raise raise_exception
            else:
                return ret
        else:
            return

    def _verify(self, http_session=None, search_info=None):
        """
        验价模块
        :param http_session:
        :param search_info: 带有 verify_routing_key 和 基本搜索条件
        :return: 如果验价失败抛异常 ProviderVerifyFail ，如果成功请返回routingInfo 实例
        """
        raise NotImplementedError

    @logger_config('PD_VERIFY', True)
    def verify(self, http_session=None, search_info=None):
        """
        搜索模块
        :param http_session:
        :return:

        """
        TB_PROVIDER_CHANNEL = self.provider_channel
        Logger().sinfo('verify Start {from_airport}-{to_airport} {from_date} '.format(from_airport=search_info.from_airport, to_airport=search_info.to_airport,
                                                                                      from_date=search_info.from_date))
        if http_session == None:
            http_session = HttpRequest(lock_proxy_pool='F')  # 对于官网验价则使用F池
        tries = 0
        while 1:
            tries += 1
            try:

                routing = self._verify(http_session=http_session, search_info=search_info)
                routing.segment_min_cabin_count = min([f.cabin_count for f in routing.from_segments])
                search_info.return_status = 'PROVIDER_VERIFY_SUCCESS'
                routing_un_key = RoutingKey.trans_un_key(routing.routing_key_detail, is_unserialized=False, is_encrypted=False)
                # 成功则将单条routing更新到缓存库中，如果缓存库存在的情况下 TODO 该逻辑理论上不应该单独放置
                if search_info.trip_type == 'OW':
                    ret_date = ''
                else:
                    ret_date = search_info.ret_date
                fare_cache_query_params = {
                    'from_date': search_info.from_date,
                    'from_airport': search_info.from_airport,
                    'to_airport': search_info.to_airport,
                    'ret_date': ret_date,
                    'trip_type': search_info.trip_type,
                }
                Logger().sinfo('fare_cache_query_params')
                cache_search_info_with_result = TBG.cache_access_object.get(cache_type='fare_cache', provider=self.provider, param_model=fare_cache_query_params, is_decompress=True)
                if cache_search_info_with_result:
                    for index,cache_routing in enumerate(cache_search_info_with_result['assoc_search_routings']):
                        cache_un_key = RoutingKey.trans_un_key(cache_routing['routing_key_detail'], is_unserialized=False, is_encrypted=False)
                        Logger().sdebug('cache_un_key %s routing_un_key %s' % ( cache_un_key, routing_un_key))
                        if cache_un_key == routing_un_key:
                            routing.cache_source = 'PD_VERIFY' # 新增数据来源状态
                            cache_search_info_with_result['assoc_search_routings'][index] = routing

                            expire_seconds = int((datetime.datetime.strptime(search_info.from_date, '%Y-%m-%d') +
                                                  datetime.timedelta(days=1) - datetime.datetime.now()).total_seconds())
                            Logger().sinfo('cache_search_info_with_result routing %s'% routing)
                            TBG.cache_access_object.insert(
                                cache_type='fare_cache',
                                provider=self.provider,
                                param_model=fare_cache_query_params,
                                ret_data=cache_search_info_with_result,
                                expired_time=expire_seconds,
                                is_compress=True
                            )
                            break
                else:
                    Logger().sinfo('no cache_search_info_with_result')

                return routing
            except Critical as e:
                search_info.return_status = 'PROVIDER_VERIFY_ERROR'
                search_info.return_details = str(e)
                search_info.assoc_search_routings = []
                raise
            except NotImplementedError as e:
                raise
            except ProviderVerifyFail as e:
                # 验价失败会熔断
                search_info.assoc_search_routings = [] # 如果验价失败则将routing返回置空
                bp_key = RoutingKey.trans_bp_key(search_info.verify_routing_key, is_unserialized=False, is_encrypted=True)
                FusingControl.add_fusing(fusing_type='bp_key',fusing_var=bp_key,source='provider_verify_fail_%s' % search_info.request_id,ttl=1800)  # 熔断30分钟
                search_info.return_status = 'PROVIDER_VERIFY_FAIL'
                search_info.return_details = str(e)
                raise
            except Exception as e:
                Logger().serror('verify Failed Retry={tries}'.format(tries=tries))
                search_info.return_status = 'PROVIDER_VERIFY_ERROR'
                search_info.return_details = str(e)
                search_info.assoc_search_routings = []
            if tries == self.verify_tries:
                break
            else:
                gevent.sleep(0.1)
        raise ProviderVerifyException

    def _get_coupon(self, http_session, **kwargs):
        """
        获取红包模块
        :return:
        """

    def to_format(self, data):
        """
        将数据标准化
        :param kwargs:
        :return:
        """
        pass

    @logger_config('PD_CRAWL', True)
    def flight_crawl(self, search_info=None, http_session=None,allow_expired=False,cache_mode='REALTIME',proxy_pool='A',custom_expired_time=None,is_only_search_scheduled_airline=0):
        """
        爬虫模块,可自定义一些开关和设置，一般情况下使用默认配置即可
        :param http_session:
        :return:

        """

        return self.search_control(search_info=search_info,
                            allow_expired=allow_expired,
                            expired_mode='FARE',
                            allow_cabin_attenuation=False,
                            cache_mode=cache_mode,
                            allow_freq_limit=True,
                            freq_limit_mode='WAIT',
                            freq_limit_wait_timeout=5,
                            allow_update_cache=True,
                            proxy_pool=proxy_pool,
                            http_session=http_session,
                            req_retries=2,
                            cache_source_mark='PD_CRAWL',
                            allow_raise_exception=False,
                                   custom_expired_time=custom_expired_time,
                                   is_only_search_scheduled_airline=is_only_search_scheduled_airline
                            )

    @logger_config('PD_FARE_SEARCH', True)
    def ota_fare_search(self, search_info,cache_mode,allow_expired=True,expired_mode='CABIN',ba_virtual_cabin_mapping=False,nba_virtual_cabin_mapping=False,custom_expired_time=None,ota_name='',is_only_search_scheduled_airline=0):
        """
        ota 运价直连查询
        :return:
        """
        if search_info.return_status in ['PIPELINE_FILTERED','FUSING']:  #TODO 此处暂时写死，来自路由层 耦合，后续爬虫会调用ota_fare_search
            # 如果包含结果代表可能由上层路由传递，此时仅需执行打点操作即可
            enter_count = 0
        else:
            enter_count = 1

            self.search_control(search_info=search_info,
                                allow_expired=allow_expired,
                                expired_mode=expired_mode,
                                allow_cabin_attenuation=True,
                                cache_mode=cache_mode,
                                allow_freq_limit=False,
                                freq_limit_mode='WAIT',
                                freq_limit_wait_timeout=30,
                                allow_update_cache=True,
                                proxy_pool='D',
                                http_session=None,
                                req_retries=1,
                                cache_source_mark='PD_FARE_SEARCH',
                                allow_raise_exception=False,
                                custom_expired_time=custom_expired_time,
                                ba_virtual_cabin_mapping=ba_virtual_cabin_mapping,
                                nba_virtual_cabin_mapping=nba_virtual_cabin_mapping,
                                is_only_search_scheduled_airline=is_only_search_scheduled_airline
                                )

        metrics_tags = dict(
            ota_name=ota_name,
            provider_channel=self.provider_channel,
            from_date=search_info.from_date,
            return_status=search_info.return_status,
            from_to_airport='%s%s-%s%s' % (search_info.from_airport, search_info.from_city, search_info.to_airport, search_info.to_city)
        )

        # 命中缓存
        if search_info.return_status.startswith('CACHE_'):
            cache_count = 1
        else:
            cache_count = 0

        # 有舱位
        if search_info.return_status.startswith('CACHE_SUCCESS') or search_info.return_status == 'RTS_SUCCESS':
            return_flight_count = 1
        else:
            return_flight_count = 0

        # 是否出错
        if 'ERROR' in search_info.return_status:
            error_count = 1
        else:
            error_count = 0

        TBG.tb_aggr_metrics.write(
            "PD_FARE_SEARCH",
            tags=metrics_tags,
            fields=dict(
                total_latency=search_info.total_latency,
                total_count=1,  # 总量
                cache_count=cache_count,  # 缓存命中量
                return_flight_count=return_flight_count,  # 返回有航班量
                error_count=error_count,  # 错误量
                enter_count=enter_count
            ))

        return

    @logger_config('PD_ASYNC_SEARCH', True)
    def async_search(self, search_info,cache_mode,allow_expired=True,expired_mode='CABIN',ba_virtual_cabin_mapping=False,nba_virtual_cabin_mapping=False,custom_expired_time=None,is_only_search_scheduled_airline=1):
        """
        异步爬虫查询
        :return:
        """

        self.search_control(search_info=search_info,
                            allow_expired=allow_expired,
                            expired_mode=expired_mode,
                            allow_cabin_attenuation=True,
                            cache_mode=cache_mode,
                            allow_freq_limit=False,
                            freq_limit_mode='WAIT',
                            freq_limit_wait_timeout=1,
                            allow_update_cache=True,
                            proxy_pool='D',
                            http_session=None,
                            req_retries=1,
                            cache_source_mark='PD_ASYNC_SEARCH',
                            allow_raise_exception=False,
                            custom_expired_time=custom_expired_time,
                            ba_virtual_cabin_mapping=ba_virtual_cabin_mapping,
                            nba_virtual_cabin_mapping=nba_virtual_cabin_mapping,
                            is_only_search_scheduled_airline=is_only_search_scheduled_airline,
                            )

        metrics_tags = dict(
            provider_channel=self.provider_channel,
            from_date=search_info.from_date,
            return_status=search_info.return_status,
            from_to_airport='%s%s-%s%s' % (search_info.from_airport, search_info.from_city, search_info.to_airport, search_info.to_city)
        )

        # 命中缓存
        if search_info.return_status.startswith('CACHE_'):
            cache_count = 1
        else:
            cache_count = 0

        # 有舱位
        if search_info.return_status.startswith('CACHE_SUCCESS') or search_info.return_status == 'RTS_SUCCESS':
            return_flight_count = 1
        else:
            return_flight_count = 0

        # 是否出错
        if 'ERROR' in search_info.return_status:
            error_count = 1
        else:
            error_count = 0

        TBG.tb_aggr_metrics.write(
            "PD_ASYNC_SEARCH",
            tags=metrics_tags,
            fields=dict(
                total_latency=search_info.total_latency,
                total_count=1,  # 总量
                cache_count=cache_count,  # 缓存命中量
                return_flight_count=return_flight_count,  # 返回有航班量
                error_count=error_count,  # 错误量
            ))

        return

    @logger_config('PD_SCHED_AIRLINE_SEARCH', True)
    def sched_airline_search(self, search_info, cache_mode, allow_expired=True, expired_mode='CABIN', ba_virtual_cabin_mapping=False, nba_virtual_cabin_mapping=False, custom_expired_time=None,
                     is_only_search_scheduled_airline=0):
        """
        航线库爬虫查询
        :return:
        """

        self.search_control(search_info=search_info,
                            allow_expired=allow_expired,
                            expired_mode=expired_mode,
                            allow_cabin_attenuation=True,
                            cache_mode=cache_mode,
                            allow_freq_limit=False,
                            freq_limit_mode='WAIT',
                            freq_limit_wait_timeout=5,
                            allow_update_cache=True,
                            proxy_pool='A',
                            http_session=None,
                            req_retries=1,
                            cache_source_mark='PD_SCHED_AIRLINE_SEARCH',
                            allow_raise_exception=False,
                            custom_expired_time=custom_expired_time,
                            ba_virtual_cabin_mapping=ba_virtual_cabin_mapping,
                            nba_virtual_cabin_mapping=nba_virtual_cabin_mapping,
                            is_only_search_scheduled_airline=is_only_search_scheduled_airline,
                            )

        metrics_tags = dict(
            provider_channel=self.provider_channel,
            from_date=search_info.from_date,
            return_status=search_info.return_status,
            from_to_airport='%s%s-%s%s' % (search_info.from_airport, search_info.from_city, search_info.to_airport, search_info.to_city)
        )

        # 命中缓存
        if search_info.return_status.startswith('CACHE_'):
            cache_count = 1
        else:
            cache_count = 0

        # 有舱位
        if search_info.return_status.startswith('CACHE_SUCCESS') or search_info.return_status == 'RTS_SUCCESS':
            return_flight_count = 1
        else:
            return_flight_count = 0

        # 是否出错
        if 'ERROR' in search_info.return_status:
            error_count = 1
        else:
            error_count = 0

        TBG.tb_aggr_metrics.write(
            "PD_SCHED_AIRLINE_SEARCH",
            tags=metrics_tags,
            fields=dict(
                total_latency=search_info.total_latency,
                total_count=1,  # 总量
                cache_count=cache_count,  # 缓存命中量
                return_flight_count=return_flight_count,  # 返回有航班量
                error_count=error_count,  # 错误量
            ))

        return

    @logger_config('PD_TEST_SEARCH', True)
    def test_search(self, search_info, cache_mode,http_session=None, allow_expired=True, expired_mode='CABIN', ba_virtual_cabin_mapping=False, nba_virtual_cabin_mapping=False, custom_expired_time=None,
                     is_only_search_scheduled_airline=1):
        """
        异步爬虫查询
        :return:
        """

        self.search_control(search_info=search_info,
                            allow_expired=allow_expired,
                            expired_mode=expired_mode,
                            allow_cabin_attenuation=True,
                            cache_mode=cache_mode,
                            allow_freq_limit=True,
                            freq_limit_mode='WAIT',
                            freq_limit_wait_timeout=5,
                            allow_update_cache=True,
                            proxy_pool='D',
                            http_session=http_session,
                            req_retries=1,
                            cache_source_mark='PD_ASYNC_SEARCH',
                            allow_raise_exception=False,
                            custom_expired_time=custom_expired_time,
                            ba_virtual_cabin_mapping=ba_virtual_cabin_mapping,
                            nba_virtual_cabin_mapping=nba_virtual_cabin_mapping,
                            is_only_search_scheduled_airline=is_only_search_scheduled_airline,
                            )

    def _flight_search(self, search_info=None, http_session=None):
        """
        航班爬取模块，返回原始数据即可，后续数据将由爬虫格式化模块和运价查询模块使用
        :param query_params:
        :return:
        """
        pass

    @logger_config('PD_SEARCH', True)
    def flight_search(self, http_session=None, search_info=None,custom_expired_time=30,cache_mode='MIX',allow_expired=True,proxy_pool='E'):
        """
        搜索模块（主要用于生单和后台）
        :param http_session:
        :return:

        """
        raise_exception = None
        ret = None
        Logger().sinfo('Start {from_airport}-{to_airport} {from_date} {trip_type} {ret_date}'.format(from_airport=search_info.from_airport, to_airport=search_info.to_airport,
                                                                               from_date=search_info.from_date,trip_type=search_info.trip_type,ret_date=search_info.ret_date))
        try:
            ret = self.search_control(search_info=search_info,
                                    allow_expired=allow_expired,
                                    expired_mode='CABIN',
                                    allow_cabin_attenuation=False,
                                    cache_mode=cache_mode,
                                    allow_freq_limit=False,
                                    freq_limit_mode='WAIT',
                                    freq_limit_wait_timeout=30,
                                    allow_update_cache=True,
                                    proxy_pool=proxy_pool,
                                    http_session=http_session,
                                    req_retries=3,
                                    cache_source_mark='PD_SEARCH',
                                    allow_raise_exception=True,
                                    custom_expired_time=custom_expired_time,
                                    logger_level_lock='DEBUG'
                                    )

        except Exception as e:
            raise_exception = FlightSearchException(e)

        # 是否出错
        if 'ERROR' in search_info.return_status:
            success = 0
        else:
            success = 1

        TBG.tb_metrics.write(
            "PD_APP",
            tags=dict(
                success=success,
                return_status=search_info.return_status,
                action='SEARCH',
                provider=self.provider,
                provider_channel=self.provider_channel,

            ),
            fields=dict(
                tries=search_info.rts_search_tries,
                total_latency=search_info.total_latency,
                count=1
            ))

        if raise_exception:
            raise raise_exception
        else:
            return ret

    def _pay(self, order_info=None, http_session=None, pay_dict={}):
        """
        支付模块
        :param query_params:
        :return: 返回True 支付成功  False  支付失败
        """
        raise NotImplementedError

    @logger_config('PD_PAY', True)
    @db_session
    def pay(self, order_info=None, http_session=None):
        """
        支付模块
        :param query_params:
        :return:
        """
        start_time = Time.timestamp_ms()
        ret = None
        raise_exception = None
        TB_PROVIDER_CHANNEL = self.provider_channel

        Logger().sinfo('pay Start ')
        if http_session == None:
            http_session = HttpRequest()
        tries = 0
        while 1:
            tries += 1
            try:
                pay_sources = select(p for p in PaySource)
                pay_dict = {}
                if pay_sources:
                    # TODO  暂时直接采用model 暂时不做内部数据封装
                    for ps in pay_sources:
                        pay_dict[ps.source_name] = ps
                else:
                    Logger().swarn('no relative pay source ')

                pay_source = self._pay(http_session=http_session, order_info=order_info, pay_dict=pay_dict)

                detail_result = 'PAYMENTS_MADE'
                # pay_source 返回为某一个支付源的model
                # TODO 目前实现上pay_source 不会返回False
                # else:
                #     order_info.provider_order_status = 'PAY_FAIL'
                #     detail_result = 'FAIL'
                # 记录支付日志
                if pay_source:
                    IncomeExpenseDetail(
                        trade_type='EXPENSE',
                        trade_sub_type='BUY',
                        flight_order=order_info.flight_order_id,
                        sub_order=order_info.sub_order_id,
                        expense_source=pay_source,
                        pay_amount=order_info.provider_price,
                        pay_channel=pay_source.pay_channel,  # 从类属性中继承而来
                        provider_order_id=order_info.provider_order_id,
                        pay_result=detail_result,
                        # out_trade_no= order_info.out_trade_no
                    )
                else:
                    IncomeExpenseDetail(
                        trade_type='EXPENSE',
                        trade_sub_type='BUY',
                        flight_order=order_info.flight_order_id,
                        sub_order=order_info.sub_order_id,
                        expense_source_offline='NOPAYSOURCE',
                        pay_amount=order_info.provider_price,
                        pay_channel=self.pay_channel,  # 从类属性中继承而来
                        provider_order_id=order_info.provider_order_id,
                        pay_result=detail_result,
                        # out_trade_no=order_info.out_trade_no
                    )
                order_info.provider_order_status = 'PAY_SUCCESS'
                Logger().sinfo('PAY_SUCCESS')
                ret = True
                break
            except Critical as e:
                order_info.provider_order_status = 'PAY_FAIL'
                raise_exception = e
                break
            except Exception as e:
                Logger().serror('pay Failed Retry={tries}'.format(tries=tries))
                if tries == self.pay_tries:
                    order_info.provider_order_status = 'PAY_FAIL'
                    raise_exception = PayException(e)
                    break
                else:
                    gevent.sleep(2)

        if raise_exception:
            err_code = raise_exception.err_code
        else:
            err_code = ''

        if ret:
            success = 1
        else:
            success = 0

        total_latency = Time.timestamp_ms() - start_time
        TBG.tb_metrics.write(
            "PD_APP",
            tags=dict(
                success=success,
                err_code=err_code,
                action='PAY',
                provider=self.provider,
                provider_channel=self.provider_channel,

            ),
            fields=dict(
                tries=tries,
                total_latency=total_latency,
                count=1
            ))

        if raise_exception:
            raise raise_exception
        else:
            return ret

    @logger_config('PROVIDER_NOTICE_ISSUE')
    @db_session
    def notice_issue_interface(self, req_body):
        """
        通知出票接口
        :return:
        """

        try:
            notice_data, provider_order_id = self.before_notice_issue_interface(req_body)
            if not notice_data or not provider_order_id:
                Logger().warn('========tc notice issue have no notice data or provider order id')
                Logger().info(notice_data)
                Logger().info(provider_order_id)
                return self.final_result
            sub_order = SubOrder.get(provider_order_id=provider_order_id)
            if not sub_order:
                Logger().warn('========tc notice issue have no sub order ')
                return self.final_result
            self.after_notice_issue_interface(sub_order, notice_data)
        except NoticeIssueInterfaceException as e:
            Logger().serror('notice_issue_interface error')
            return self.final_result

    def before_notice_issue_interface(self, req_body):
        """

        :param req_body:
        :return:
        """
        Logger().sinfo('before_notice_issue_interface start')
        try:

            notice_data, provider_order_id = self._before_notice_issue_interface(req_body)
            return notice_data, provider_order_id
        except Exception as e:
            Logger().serror('before_notice_issue_interface failed')
        raise NoticeIssueInterfaceException

    def _before_notice_issue_interface(self, req_body):
        """

        :param req_body:
        :return:
        """
        raise NotImplementedError

    def after_notice_issue_interface(self, sub_order, notice_data):
        """

        :param req_body:
        :return:
        """
        Logger().sinfo('after_notice_issue_interface start')
        try:
            return self._after_notice_issue_interface(sub_order, notice_data)
        except Exception as e:
            Logger().serror('after_notice_issue_interface failed')
        raise NoticeIssueInterfaceException

    def _after_notice_issue_interface(self, sub_order, notice_data):
        """

        :param order_info: order_info class
        :return:
        """
        raise NotImplementedError

    @logger_config('PROVIDER_NOTICE_FLIGHT_CHANGE')
    @db_session
    def notice_flight_change_interface(self, req_body):
        """
        通知出票接口
        :return:
        """

        try:
            notice_data = self.before_notice_flight_change_interface(req_body)
            if not notice_data:
                Logger().warn('======== notice flight change have no notice data or provider order id')
                Logger().info(notice_data)
                return self.final_result
            self.after_notice_flight_change_interface(notice_data)
        except NoticeIssueInterfaceException as e:
            Logger().serror('notice_flight_change_interface error')
            return self.final_result

    def before_notice_flight_change_interface(self, req_body):
        """

        :param req_body:
        :return:
        """
        Logger().sinfo('before_notice_flight_change_interface start')
        try:

            notice_data = self._before_notice_flight_change_interface(req_body)
            return notice_data
        except Exception as e:
            Logger().serror('before_notice_issue_interface failed')
        raise NoticeIssueInterfaceException

    def _before_notice_flight_change_interface(self, req_body):
        """

        :param req_body:
        :return:
        """
        raise NotImplementedError

    def after_notice_flight_change_interface(self, notice_data):
        """

        :param req_body:
        :return:
        """
        Logger().sinfo('after_notice_flight_change_interface start')
        try:
            return self._after_notice_flight_change_interface(notice_data)
        except Exception as e:
            Logger().serror('after_notice_flight_change_interface failed')
        raise NoticeIssueInterfaceException

    def _after_notice_flight_change_interface(self, sub_order, notice_data):
        """

        :param order_info: order_info class
        :return:
        """
        raise NotImplementedError


    def alipay(self, trade_id, tmpl):

        """

        :param order_info:
        :param tmpl: 供应商支付表单form的模版字符串
        :return:
        """

        if not trade_id:
            raise PayException('have no trade id')
        provider_trade_id = '%s_%s' % (self.provider_channel, trade_id)
        redis_pool = TBG.redis_conn.get_internal_pool()
        redis_pool.lpush('payment_task_queue', {
            'data': tmpl,
            'trade_id': provider_trade_id,
        })
        Logger().sdebug("finish push alipay payment task")

        now = datetime.datetime.now()
        while True:
            if (datetime.datetime.now() - now).seconds <= 300:
                payment_result = eval(redis_pool.get('payment_task_result_{}'.format(
                    provider_trade_id)) or '{}')
                if payment_result.get('result') == 'ok':
                    Logger().sdebug("alipay payment result ok")
                    redis_pool.expire('payment_task_result_{}'.format(
                        provider_trade_id), 0)
                    return True
                elif payment_result.get('result') == 'error':
                    Logger().sdebug("alipay payment result error")
                    redis_pool.expire('payment_task_result_{}'.format(
                        provider_trade_id), 0)
                    raise PayException(payment_result.get('msg'))
                else:
                    Logger().sdebug("alipay payment get result retry")
                    time.sleep(2)
            else:
                raise PayException('alipay payment failed')


    def alipay_qcode(self, trade_id, trade_data):

        """
        :param trade_id: 唯一ID
        :param trade_data: dict {'qcode_url':'https://qr.alipay.com/upx01604nwq4zafmegk64047'}
        :return:
        """

        if not trade_id:
            raise PayException('have no trade id')
        provider_trade_id = '%s_%s' % (self.provider_channel, trade_id)
        redis_pool = TBG.redis_conn.get_internal_pool()
        d = json.dumps({
            'trade_data': trade_data,
            'trade_id': provider_trade_id,
        })
        redis_pool.lpush('alipay_qcode_queue', d)
        Logger().sdebug("finish push alipay payment task")

        now = datetime.datetime.now()
        while True:
            if (datetime.datetime.now() - now).seconds <= 300:
                result = redis_pool.get('alipay_qcode_result_{}'.format(provider_trade_id))
                if result:
                    payment_result = json.loads(result)
                    if payment_result.get('result') == 'SUCCESS':
                        Logger().sdebug("alipay payment result ok")
                        redis_pool.expire('payment_task_result_{}'.format(
                            provider_trade_id), 0)
                        return True
                    else :
                        Logger().sdebug("alipay payment result error")
                        redis_pool.expire('payment_task_result_{}'.format(
                            provider_trade_id), 0)
                        raise PayException(payment_result.get('result'))
                else:
                    Logger().sdebug("alipay payment get result retry")
                    time.sleep(2)
            else:
                raise PayException('alipay payment failed')

if __name__ == '_main_':
    pass
