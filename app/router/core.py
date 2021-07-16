#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, too-many-arguments, broad-except, anomalous-backslash-in-string
# pylint: disable=missing-docstring, line-too-long, too-few-public-methods
"""
# @Author  : wxt
# @Software: PyCharm
"""

import datetime
import gevent
import re
from ..utils.logger import Logger
from ..automatic_repo import ProviderAutoRepo
from ..automatic_repo.pdc_faker import PdcFaker
from ..utils.exception import *
from ..dao.internal import *
from ..controller.fusing_limiter import FusingControl
from ..utils.util import Random, Time, tb_gevent_spawn, RoutingKey
from app import TBG
from ..controller.dynamic_fare import DynamicFareRuleEngine


class RouteResult(object):
    """
    存储路由结果，返回给 OTA BASE

    """

    def __init__(self):
        self.return_status_list = []  # 供应商的搜索状态汇总
        self.route_pipeline_done = False  # 是否执行完成
        self.assoc_search_routings = []  # 存储结果
        self.last_status = 'ROUTE_NOT_FINISH'  # 路由执行过程中记录最后一次provider状态，初始状态为无返回
        self.is_route_exception = False  # 是否路由模块执行出错

    def add_provider_status(self, provider_channel, return_status, search_time, latency, assoc_search_routings_amount=0, return_details=''):
        """

        :param err_code: 如果报错，返回错误代码
        :param assoc_search_routings_amount: 如果搜索成功，返回routing数量
        :param provider_channel:
        :param return_status: SUCCESS NOFLIGHT ERROR FILTERED
        :return:
        """
        rsl = {
            'provider_channel': provider_channel,
            'return_status': return_status,
            'assoc_search_routings_amount': assoc_search_routings_amount,
            'return_details': return_details,
            'return_time': Time.time_str(),
            'search_time': search_time,
            'latency': latency,
        }
        self.return_status_list.append(rsl)
        self.last_status = return_status


class Router(object):
    """
    路由模块
    """

    def __init__(self, ota_app, search_mode=None, route_strategy=[], is_allow_max_pax_count_limit=True, is_allow_min_cabin_count_limit=True, is_allow_fusing=True, is_allow_cabin_revise=True):
        """

        :param route_strategy: 自定义路由策略
        :param config:
        :param ota_app:
        :param result_container: 结果实例，用于gevent线程间通讯
        """
        # TODO 该路由仅适用OTA搜索，不适用界面搜索
        self.is_allow_fusing = is_allow_fusing  # 是否允许熔断
        self.is_allow_cabin_revise = is_allow_cabin_revise  # 是否允许舱位修正
        self.is_allow_min_cabin_count_limit = is_allow_min_cabin_count_limit  # 是否允许最小舱位限制
        self.is_allow_max_pax_count_limit = is_allow_max_pax_count_limit  # 是否允许最大乘客限制
        self.ota_app = ota_app
        self.ota_fare_search_timeout = self.ota_app._operation_config['ota_fare_search_timeout']
        self.invalid_cabin_return_mode = self.ota_app._operation_config['invalid_cabin_return_mode']
        self.is_nba_virtual_cabin_mapping = 0  # 此功能暂停开发
        self.is_ba_virtual_cabin_mapping = 0  # 此功能暂停开发
        self.is_allow_operation_carrier = self.ota_app._operation_config['is_allow_operation_carrier']
        self.ota_carrier_filter = self.ota_app._operation_config.get('carrier_filter`', [])  # 新增 航司后置过滤器
        self.min_cabin_count_limit = self.ota_app._operation_config['min_cabin_count_limit']
        self.max_pax_count_limit = self.ota_app._operation_config['max_pax_count_limit']
        self.verify_stop_loss = self.ota_app._operation_config['verify_stop_loss']
        self.verify_stop_profit = self.ota_app._operation_config['verify_stop_profit']
        self.estimate_ota_diff_price = self.ota_app._operation_config['fare_linkage'].get('estimate_ota_diff_price','x')
        self.bidding_diff_price = self.ota_app._operation_config['fare_linkage'].get('bidding_diff_price',-1)
        if route_strategy:
            self.route_strategy = route_strategy
        else:
            self.route_strategy = self.ota_app._operation_config['route_strategy']
        if search_mode:
            self.search_mode = search_mode
        else:
            self.search_mode = self.ota_app._operation_config.get('search_mode', 'default')
        fare_strategy = self.ota_app._operation_config['fare_strategy']
        # fare_strategy =  [{'rule':'SHA\|.*\|HRB\|.*\|.*\|.*\|.*\|fakeprovider\|fakeprovider_web','priority':1,'price_calc':-333},{'rule':'fakeprovider','priority':2,'price_calc':9999}]
        # fare_strategy =  [{'rule':'fakeprovider_test3','priority':1,'price_calc':-333},{'rule':'fakeprovider_test2','priority':2,'price_calc':9999}]
        # 编译正则
        self.fare_strategy = sorted([{'rule': re.compile(x['rule']), 'priority': x['priority'], 'adult_price_calc': x['adult_price_calc'],'child_price_calc': x.get('child_price_calc','x'), 'title': x['title']} for x in fare_strategy],
                                    key=lambda x: x['priority'])

        # self.operation_product_type = self.ota_app._operation_config['operation_product_type'] # TODO 未实现 供应商所支持的产品类型自定义列表
        self.search_info = self.ota_app.search_info
        self.carrier = ['*']

        self.rk_fusing_repo = []  # 熔断的rk名单
        for rfc in self.ota_app.fusing_repo:
            if rfc.startswith('bp_key'):
                self.rk_fusing_repo.append(rfc[7:])

        self.provider_channel_fusing_repo = []  # 熔断的OTA名单
        for pfc in self.ota_app.fusing_repo:
            if pfc.startswith('provider_channel'):
                self.provider_channel_fusing_repo.append(pfc[17:])

        self.cabin_revise_repo = self.ota_app.cabin_revise_repo

        # Logger().sdebug('rk_fusing_repo %s self.ota_app.fusing_repo %s provider_fusing_repo %s' % (self.rk_fusing_repo, self.ota_app.fusing_repo, self.provider_channel_fusing_repo))

        # 过滤情况 搜索格式 SHA|HKG|2018-12-29|OUT|OW|1|0|0  出发地|目的地|出发日期|国际/国内|单程/多程|成人数量|儿童数量|婴儿数量
        # self.route_strategy = [ {'provider_channels': [{'provider_channel':'fakeprovider_test8','cache_mode':'MIX','filter':['SHA\|HKG']},{'provider_channel':'fakeprovider_test9','cache_mode':'MIX','filter':['SHA\|HKG']}], 'stop_flag': {'error': False, 'noflight': False,'filtered':False}}]

        # # 正常情况
        # self.route_strategy = [{'provider_channels': [{'provider_channel':'fakeprovider_test2','cache_mode':'REALTIME','filter':[]}],'filter':[],'stop_flag': {'error': True, 'noflight': False,'filtered':False}},
        #             {'provider_channels': [{'provider_channel':'fakeprovider_test3','cache_mode':'REALTIME'},{'provider_channel':'fakeprovider_test4','cache_mode':'REALTIME'}],'filter':[], 'stop_flag': {'error': False, 'noflight': False,'filtered':False}}]
        #
        # # 无航班情况
        # self.route_strategy = [{'provider_channels': [{'provider_channel':'fakeprovider_test2','cache_mode':'REALTIME'}],'filter':[],'stop_flag': {'error': True, 'noflight': True,'filtered':False}},
        #             {'provider_channels': [{'provider_channel':'fakeprovider_test3','cache_mode':'REALTIME'},{'provider_channel':'fakeprovider_test4','cache_mode':'REALTIME'}],'filter':[], 'stop_flag': {'error': False, 'noflight': False,'filtered':False}}]
        #
        # # 报错情况
        # self.route_strategy = [{'provider_channels': [{'provider_channel':'fakeprovider_test5','cache_mode':'REALTIME'}],'filter':[],'stop_flag': {'error': False, 'noflight': True,'filtered':False}},
        #             {'provider_channels': [{'provider_channel':'fakeprovider_test3','cache_mode':'REALTIME'},{'provider_channel':'fakeprovider_test4','cache_mode':'REALTIME'}],'filter':[], 'stop_flag': {'error': False, 'noflight': False,'filtered':False}}]
        #
        #
        # # filtered
        # self.route_strategy = [{'provider_channels': [{'provider_channel':'fakeprovider_test2','cache_mode':'REALTIME'}],'filter':['0,0|OW|SHA|HKG'],'stop_flag': {'error': False, 'noflight': True,'filtered':True}},
        #             {'provider_channels': [{'provider_channel':'fakeprovider_test3','cache_mode':'REALTIME'},{'provider_channel':'fakeprovider_test4','cache_mode':'REALTIME'}],'filter':[], 'stop_flag': {'error': False, 'noflight': False,'filtered':False}}]
        #
        # # MIX模式
        # self.route_strategy = [{'provider_channels': [{'provider_channel':'fakeprovider_test2','cache_mode':'REALTIME'}],'filter':[],'stop_flag': {'error': False, 'noflight': True,'filtered':True}},
        #             {'provider_channels': [{'provider_channel':'fakeprovider_test3','cache_mode':'MIX'},{'provider_channel':'fakeprovider_test4','cache_mode':'CACHE'}],'filter':[], 'stop_flag': {'error': False, 'noflight': False,'filtered':False}}]
        # #
        # # # 超时设置
        # # self.route_strategy = [{'provider_channels': [{'provider_channel':'fakeprovider_test6','cache_mode':'REALTIME'}],'filter':[],'stop_flag': {'error': False, 'noflight': True,'filtered':True}},
        # #             {'provider_channels': [{'provider_channel':'fakeprovider_test3','cache_mode':'MIX'},{'provider_channel':'fakeprovider_test4','cache_mode':'CACHE'}],'filter':[], 'stop_flag': {'error': False, 'noflight': False,'filtered':False}}]
        #
        # # 标准单路由
        # self.route_strategy = [{'provider_channels': [{'provider_channel':'fakeprovider_web','cache_mode':'MIX'}],'filter':[],'stop_flag': {'error': False, 'noflight': True,'filtered':True}}]

        self.route_result = RouteResult()


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

    def fare_operation(self, routing, dynamic_fare_priority):
        """
        运价逻辑
        采用正则方式，保证灵活性，后续将正则进行抽象
        每条正则可以设置优先级，从高优先级到低遍历整个列表，符合条件则退出遍历，
        priority 1 ~ 999 正序从高到低
        变更routing_key
        变更 routing_key_detail
        :param: dynamic_fare_priority  如果动运则此变量不为空
        :return:
        """
        for item in self.fare_strategy:
            if dynamic_fare_priority and item['priority'] < dynamic_fare_priority or not dynamic_fare_priority:  # 如果存在动态运价检查目前正则规则是否存在比已经运价的优先级高的正则，如果有的话继续进行匹配
                if item['rule'].search(routing.routing_key_detail):
                    # 命中规则
                    # Logger().sdebug('hit_fare_operation rule %s routing.routing_key_detail %s findall %s' % (item, routing.routing_key_detail, item['rule'].findall(routing.routing_key_detail)))
                    adult_price_forsale = int(eval(item['adult_price_calc'].replace('x', str(routing.adult_price))))
                    adult_price_forsale = adult_price_forsale if  adult_price_forsale > 0 else 1
                    child_price_forsale = int(eval(item['child_price_calc'].replace('x', str(routing.child_price))))
                    child_price_forsale = child_price_forsale if child_price_forsale > 0 else 1
                    routing.adult_price_forsale = adult_price_forsale
                    routing.child_price_forsale = child_price_forsale
                    # routing.adult_price_forsale = routing.adult_price + item['price_calc'] if routing.adult_price + item['price_calc'] > 0 else 0
                    # routing.child_price_forsale = routing.child_price + item['price_calc'] if routing.child_price + item['price_calc'] > 0 else 0
                    routing.rk_dict['adult_price_forsale'] = routing.adult_price_forsale
                    routing.rk_dict['child_price_forsale'] = routing.child_price_forsale
                    routing.rk_dict['fare_put_mode'] = 'MANUAL'
                    routing.rk_dict['assoc_fare_info'] = item['title']
                    routing.fixed_offer_price = routing.adult_price_forsale + routing.rk_dict['adult_tax']
                    break

    def run(self):
        """
        开启线程执行路有逻辑
        :return:
        """
        if self.search_info.get('is_pdc_faker_flight',0):
            # 测试航班特殊逻辑
            current_search_time = Time.time_str_4()
            current_timestamp = Time.timestamp_s()
            from_date_obj = datetime.datetime.strptime(self.search_info.from_date, '%Y-%m-%d')
            curr_date_obj = datetime.datetime.strptime(datetime.datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d')
            dep_diff_days = (from_date_obj - curr_date_obj).days
            pdc_faker_app = PdcFaker()
            pdc_faker_app.flight_search(search_info=self.search_info)
            for routing in self.search_info.assoc_search_routings:
                rk_dict = RoutingKey.unserialize(routing.routing_key_detail, is_encrypted=False)

                routing.rk_dict = rk_dict
                routing.rk_dict['dep_diff_days'] = dep_diff_days  # 添加起飞间隔天数
                routing.adult_price_forsale = routing.adult_price
                routing.child_price_forsale = routing.child_price
                rk_dict['search_time'] = current_search_time  # 加入搜索时间
                rk_dict['data_source'] = routing.data_source  # 加入数据源
                # 更新routingkey ，增加运价后价格
                new_rk_info = RoutingKey.serialize(**routing.rk_dict)
                routing.routing_key = new_rk_info['encrypted']
                routing.routing_key_detail = new_rk_info['plain']
            self.search_info.return_status = 'ROUTE_FINISH'
        else:
            if self.search_mode == 'default':
                gevent.joinall([tb_gevent_spawn(self.execute)], timeout=self.ota_fare_search_timeout)
                self.search_info.assoc_search_routings = self.route_result.assoc_search_routings
                self.search_info.return_status = 'ROUTE_NOT_FINISH'
                if self.route_result.is_route_exception:
                    # 路由报错
                    raise RouterDeliverExeception
                elif self.route_result.route_pipeline_done:
                    self.search_info.route_pipeline_done = self.route_result.route_pipeline_done
                    self.search_info.return_status = 'ROUTE_FINISH'

                # Logger().sdebug('return_status_list %s' % self.route_result.return_status_list)
            elif self.search_mode == 'update_cache':
                # 更新缓存模式，不返回航班，只更新缓存
                tb_gevent_spawn(self.execute)
                self.search_info.assoc_search_routings = []
                if self.route_result.is_route_exception:
                    # 路由报错
                    raise RouterDeliverExeception
                self.search_info.return_status = 'UPDATE_CACHE'
                self.search_info.route_pipeline_done = self.route_result.route_pipeline_done
            elif self.search_mode == 'sync_call':

                # 同步调用
                self.execute()
                self.search_info.assoc_search_routings = self.route_result.assoc_search_routings
                self.search_info.return_status = 'ROUTE_NOT_FINISH'
                if self.route_result.is_route_exception:
                    # 路由报错
                    raise RouterDeliverExeception
                elif self.route_result.route_pipeline_done:
                    self.search_info.route_pipeline_done = self.route_result.route_pipeline_done
                    self.search_info.return_status = 'ROUTE_FINISH'

    def execute(self, **kwargs):
        """
        路有逻辑
        缓存模式
        MIX 混合模式
        CACHE 只读取缓存
        REALTIME 实时查询
        self.route_strategy = [{'provider_channels': [{'provider_channel':'pdc_web','cache_mode':'REALTIME'}],'filter':['0,0|OW|DLC|FNA'],'stop_flag': {'error': True, 'noflight': True,'filtered':False}},
                    {'provider_channels': [{'provider_channel':'fakeprovider_web','cache_mode':'REALTIME'}],'filter':[], 'stop_flag': {'error': False, 'noflight': False,'filtered':False}},
                    {'provider_channels': [{'provider_channel':'ceair_web_2_fake','cache_mode':'REALTIME'}], 'filter': [], 'stop_flag': {'error': False, 'noflight': False, 'filtered': False}}]

        路由特性：
        1.如果某节点成功则不会继续向后执行
        2.filter：过滤条件，如果所有provider被过滤则认为此节点被过滤，根据filtered的开关决定是否结束or继续。
        3.相同节点的providers将进行并发查询，同时对同航班同舱输出最优价选择
        4.error开关：控制在该节点出错后是否继续执行，出错判断逻辑：在指定单节点超时时间内如果没有航班并且某一个provider报错则认为该节点出错。
        5.noflight开关：控制在该节点查询无航班后是否继续执行，没航班判断逻辑：在指定单节点超时时间内没有返回任何routing信息。
        6.每个节点执行完毕后都会将结果统计输出route_result


        ETERM_PUBLISH_FARE: 黑屏公布运价  PRIVATE_FARE:低于票面价、私有运价
        :return: route_result
        """

        try:
            # 运价routing统计初始化
            self.search_info.routing_total_count = 0  # 供应商返回的的routing总数
            self.search_info.routing_show_count = 0  # 展示给ota的数量
            self.search_info.routing_auto_fare_count = 0  # 自动运价的数量 包含 AUTO_BOOST_PROFIT AUTO_BOOST_SHOW AUTO_BOOST
            self.search_info.routing_fare_twice_fare_count = 0  # 二次运价调整数量
            self.search_info.routing_low_price_forecast_fare_count = 0  # 低价预测运价数量
            self.search_info.routing_manual_fare_count = 0  # 无运价数量
            self.search_info.routing_no_fare_count = 0  # 无运价数量
            self.search_info.routing_fusing_count = 0  # 熔断数量
            self.search_info.routing_carrier_filtered_count = 0  # 航司过滤器过滤数量
            self.search_info.routing_invalid_cabin_filtered_count = 0  # 无可用仓位过滤器过滤数量
            self.search_info.routing_min_cabin_count_filtered_count = 0  # 最小仓位数过滤数量
            self.search_info.routing_operation_carrier_filtered_count = 0  # 承运航班过滤数量
            self.search_info.routing_virtual_cabin_count = 0  # 虚拟仓展示数量
            self.search_info.routing_enter_time_interval_long_count = 0  # 长时间间隔的

            current_search_time = Time.time_str_4()
            current_timestamp = Time.timestamp_s()
            from_date_obj = datetime.datetime.strptime(self.search_info.from_date, '%Y-%m-%d')
            curr_date_obj = datetime.datetime.strptime(datetime.datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d')
            dep_diff_days = (from_date_obj - curr_date_obj).days
            chd_aggr_count = self.search_info.chd_count + self.search_info.inf_count  # 儿童人数（包括婴儿）
            total_count = self.search_info.chd_count + self.search_info.inf_count + self.search_info.adt_count  # 总人数
            # 预先拼接过滤字符串 示例 搜索格式 SHA|HKG|2018-12-29|OUT|OW|1|0|0|12  出发地|目的地|出发日期|国际/国内|单程/多程|成人数量|儿童数量|婴儿数量|起飞间隔天数
            search_info_str = '%s|%s|%s|%s|%s|%s|%s|%s|%s' % (
                self.search_info.from_airport, self.search_info.to_airport, self.search_info.from_date, self.search_info.routing_range, self.search_info.trip_type, self.search_info.adt_count,
                self.search_info.chd_count, self.search_info.inf_count, dep_diff_days)
            low_price_list = DynamicFareRuleEngine.load_from_low_price_cache(ota_name=self.ota_app.ota_name, from_airport=self.search_info.from_airport, to_airport=self.search_info.to_airport,
                                                                             from_date=self.search_info.from_date, ret_date=self.search_info.ret_date, trip_type=self.search_info.trip_type)  # 包含
            # Logger().sdebug('low_price_list %s' % low_price_list)
            # Logger().sdebug('search_info_str %s' % search_info_str)
            for index, rst in enumerate(self.route_strategy):
                rst_provider_channels = rst['provider_channels']
                # Logger().sdebug('process node %s channels %s' % (index, rst_provider_channels))

                worker_pool = []
                sub_providers = {}
                filtered_provider_channel_count = 0  # 计算被过滤的供应商个数

                for pcitem in rst_provider_channels:

                    # 过滤
                    provider_app = ProviderAutoRepo.select(pcitem['provider_channel'])  # TODO 后续进行条件过滤

                    sub_providers[provider_app] = SearchInfo(**self.search_info)

                    if not self.prefix_routing_match(search_info_str, pcitem.get('filter', [])):
                        # Logger().sdebug('routing filtered %s ' % pcitem.get('filter', []))
                        filtered_provider_channel_count += 1
                        sub_providers[provider_app].return_status = 'PIPELINE_FILTERED'
                    elif self.is_allow_fusing and pcitem['provider_channel'] in self.provider_channel_fusing_repo:
                        # 判断ota是否被熔断
                        # Logger().sdebug('fusing %s ' % provider_app.provider)
                        sub_providers[provider_app].return_status = 'FUSING'
                    else:
                        sub_providers[provider_app].return_status = ''  # 防止主search_info 存在 return_status 产生干扰
                    # Logger().sdebug('pcitem %s' % pcitem)
                    worker_pool.append(tb_gevent_spawn(provider_app.ota_fare_search, search_info=sub_providers[provider_app], cache_mode=pcitem.get('cache_mode', 'MIX'),is_only_search_scheduled_airline=pcitem.get('is_only_search_scheduled_airline', 0),
                                                       expired_mode=pcitem.get('expired_mode', 'CABIN'), ota_name=self.ota_app.ota_name, ba_virtual_cabin_mapping=self.is_ba_virtual_cabin_mapping,
                                                       nba_virtual_cabin_mapping=self.is_nba_virtual_cabin_mapping))

                gevent.joinall(worker_pool, timeout=self.ota_fare_search_timeout - 0.7)  # 放置在过滤返回判断的语句前面是为了执行一次记录PD_FARE_SEARCH的metric

                if len(rst_provider_channels) == filtered_provider_channel_count:
                    # 认为所有供应商都被过滤了
                    self.route_result.last_status = 'PIPELINE_FILTERED'
                    if rst['stop_flag']['filtered'] == True:
                        self.route_result.route_pipeline_done = True
                        return

                node_has_success = False
                selected_routings = {}
                for s_provider_app, s_search_info in sub_providers.items():
                    # Logger().sdebug('s_search_info.search_finished %s' % s_search_info.search_finished)
                    if s_search_info.search_finished:
                        for routing in s_search_info.assoc_search_routings:
                            # Logger().sdebug('routing.routing_key_detail %s' % routing.routing_key_detail)

                            # TODO 临时将rk_dict加入 为了进入fare_operation 函数

                            rk_dict = RoutingKey.unserialize(routing.routing_key_detail, is_encrypted=False)
                            # TODO 临时将 routing virtual_cabin_aggr_str 加入到 rk_dict 后续应该在搜索控制层直接处理好返回
                            # rk_dict['virtual_cabin'] = routing.get('virtual_cabin', '')
                            routing.rk_dict = rk_dict
                            routing.rk_dict['dep_diff_days'] = dep_diff_days  # 添加起飞间隔天数
                            routing.rk_dict['adt_count'] = self.search_info.adt_count  # 添加查询人数
                            routing.rk_dict['chd_count'] = self.search_info.chd_count  # 添加查询人数
                            routing.enter_time = int(rk_dict['enter_time'])
                            new_rk_info = RoutingKey.serialize(is_encrypt=False, **routing.rk_dict)
                            routing.routing_key_detail = new_rk_info['plain']
                            # vcp_key = RoutingKey.trans_vcp_key(rk_dict, is_unserialized=True)  # 此处使用VCP 考虑到虚拟仓的情况 如果有部分舱位没有转成虚拟仓，则认为此虚拟仓无效，不采用，使用原舱
                            cp_key = RoutingKey.trans_cp_key(rk_dict, is_unserialized=True)
                            bp_key = RoutingKey.trans_bp_key(rk_dict, is_unserialized=True)  # TODO 目前bp_key主要用于 fusing_repo 此处是否需要跟UN_KEY 统一
                            un_key = RoutingKey.trans_un_key(rk_dict, is_unserialized=True)
                            routing.cp_key = cp_key
                            routing.un_key = un_key
                            # 对舱位数量进行修正
                            # Logger().sdebug('cabin_count_revise %s ' % un_key)
                            # 判断修正库数据是否过期
                            if self.is_allow_cabin_revise and routing.un_key in self.cabin_revise_repo:
                                # Logger().sdebug('raw routing cabin count %s '% routing.segment_min_cabin_count)
                                routing.segment_min_cabin_count = routing.segment_min_cabin_count - self.cabin_revise_repo[routing.un_key]
                                if routing.segment_min_cabin_count <= 0:
                                    continue

                            # 座位数是否足够判断
                            if routing.segment_min_cabin_count < total_count:
                                continue

                            # 判断是否有儿童,过滤不包含儿童的航线,目前缓存中不保证儿童座位
                            if chd_aggr_count and not routing.child_price:
                                continue

                            self.search_info.routing_total_count += 1

                            routing.is_virtual_cabin = 0
                            if not routing.is_valid_cabin:
                                if self.invalid_cabin_return_mode == 'FILTERED': # 过滤不展示
                                      # 是否返回可用仓位routing
                                        self.search_info.routing_invalid_cabin_filtered_count += 1
                                        continue
                                elif self.invalid_cabin_return_mode == 'CONVERT_VIRTUAL':  # 转换虚拟仓
                                    routing.is_virtual_cabin = 1
                                    self.search_info.routing_virtual_cabin_count += 1

                            # 是否过滤航司 如果存在filter 则只会选择filter中的航司返回
                            if self.ota_carrier_filter:
                                is_allow = True
                                # 不采用rk的flight_number 是因为无法进行非的判断
                                for fs in routing.from_segments:
                                    if fs.carrier not in self.ota_carrier_filter:
                                        is_allow = False
                                        break

                                # 增加返程判断逻辑
                                for fs in routing.ret_segments:
                                    if fs.carrier not in self.ota_carrier_filter:
                                        is_allow = False
                                        break
                                if not is_allow:
                                    self.search_info.routing_carrier_filtered_count +=1
                                    continue



                            # 是否存在熔断黑名单
                            # Logger().sdebug('RoutingKey.trans_un_key(rk_dict,is_unserialized=True) %s'% RoutingKey.trans_un_key(rk_dict,is_unserialized=True))
                            if bp_key in self.rk_fusing_repo:
                                # Logger().sdebug('fusing bp_key %s' % bp_key)
                                self.search_info.routing_fusing_count += 1
                                continue

                            min_cabin_count_limit = self.min_cabin_count_limit.get(rk_dict['provider_channel'], 1)  # 默认为1
                            if self.is_allow_min_cabin_count_limit and routing.segment_min_cabin_count < min_cabin_count_limit:
                                self.search_info.routing_min_cabin_count_filtered_count += 1
                                continue

                            # 是否为承运航班
                            if self.is_allow_operation_carrier == 0:  # 为了兼容以前rk中不包含 is_include_operation_carrier 的情况
                                if routing.is_include_operation_carrier == 1 or rk_dict['is_include_operation_carrier'] == 1:
                                    self.search_info.routing_operation_carrier_filtered_count += 1
                                    continue

                            max_pax_count_limit = self.max_pax_count_limit.get(rk_dict['provider_channel'], 10)  # 对仓位展示进行限制
                            if self.is_allow_max_pax_count_limit and routing.segment_min_cabin_count > max_pax_count_limit:
                                routing.segment_min_cabin_count = max_pax_count_limit

                            if routing.rk_dict['adult_tax'] == 0:  # TODO 临时先过滤掉取不到税的
                                continue

                            # 运价
                            # 先给出默认 运价=成本价
                            routing.rk_dict['fare_put_mode'] = 'NOFARE'
                            routing.adult_price_forsale = routing.adult_price
                            routing.child_price_forsale = routing.child_price
                            routing.cost_price = routing.adult_price + routing.adult_tax
                            routing.fixed_offer_price = routing.cost_price

                            # 动态运价投放
                            fare_info = DynamicFareRuleEngine.process(ota_name=self.ota_app.ota_name, from_airport=routing.rk_dict['from_airport'], to_airport=routing.rk_dict['to_airport'],
                                                                      from_date=routing.rk_dict['from_date'], flight_number=routing.rk_dict['flight_number'],
                                                                      ret_date=routing.rk_dict['ret_date'], trip_type=routing.rk_dict['trip_type'], routing=routing)
                            if fare_info:
                                dynamic_fare_priority = fare_info.priority
                            else:
                                dynamic_fare_priority = None

                            # 人工运价补充
                            self.fare_operation(routing, dynamic_fare_priority)

                            flight_number = routing.rk_dict['flight_number']
                            if flight_number in low_price_list and low_price_list[flight_number]['expired_time'] > current_timestamp and low_price_list[flight_number]['cost_price']:   # 没有过期并且存在低价看板数据
                                selected_low_price = low_price_list[flight_number]
                                low_price_fare_info = FareInfo(ota_r1_price=selected_low_price.get('ota_r1_price',0),ota_r2_price=selected_low_price.get('ota_r2_price',0),
                                                               cost_adult_price=selected_low_price.get('cost_adult_price',0),cost_price=selected_low_price.get('cost_price',0),
                                                               bidding_diff_price=self.bidding_diff_price,estimate_ota_diff_price=self.estimate_ota_diff_price,
                                                               verify_stop_loss=self.verify_stop_loss,verify_stop_profit=self.verify_stop_profit,offer_price=routing.adult_price_forsale+routing.adult_tax)
                                DynamicFareRuleEngine.process_low_price(routing=routing,fare_info=low_price_fare_info)


                            if routing.rk_dict['fare_put_mode'] in ['AUTO_BOOST_PROFIT','AUTO_BOOST_SHOW','AUTO_BOOST']:
                                self.search_info.routing_auto_fare_count += 1
                            elif routing.rk_dict['fare_put_mode'] == 'NOFARE':
                                self.search_info.routing_no_fare_count += 1
                            elif routing.rk_dict['fare_put_mode'] == 'MANUAL':
                                self.search_info.routing_manual_fare_count += 1
                            elif routing.rk_dict['fare_put_mode'] == 'LOWPRICE_FORECAST':
                                self.search_info.routing_low_price_forecast_fare_count += 1
                            elif routing.rk_dict['fare_put_mode'] in ['FARE_UP_TWICE','FARE_DOWN_TWICE','FARE_EQ_TWICE']:
                                self.search_info.routing_fare_twice_fare_count += 1

                            rk_dict['search_time'] = current_search_time  # 加入搜索时间
                            rk_dict['data_source'] = routing.data_source  # 加入数据源
                            rk_dict['rsno'] = str(Random.gen_num(6))  # 加入routing_serial_number
                            rk_dict['is_virtual_cabin'] = routing.is_virtual_cabin  # 是否为虚拟仓

                            # 更新routingkey ，增加运价后价格
                            new_rk_info = RoutingKey.serialize(**routing.rk_dict)
                            routing.routing_key = new_rk_info['encrypted']
                            routing.routing_key_detail = new_rk_info['plain']

                            if cp_key not in selected_routings:
                                self.search_info.routing_show_count += 1
                                selected_routings[cp_key] = routing
                            else:
                                # 存在同舱竞价航班，时间相近则采用低价优先，如果时间相差较远则采用时间较后面的优先
                                # if -10 < routing.enter_time - selected_routings[cp_key].enter_time < 10:
                                if -172800 < routing.enter_time - selected_routings[cp_key].enter_time < 172800:
                                    # 时间相近低价优先
                                    # Logger().sdebug('enter_time near')
                                    if routing.adult_price_forsale < selected_routings[cp_key].adult_price_forsale:
                                        selected_routings[cp_key] = routing
                                        # Logger().sdebug('enter_time near so select price low')
                                else:
                                    self.search_info.routing_enter_time_interval_long_count += 1
                                    # Logger().sdebug('enter_time far')
                                    if routing.enter_time > selected_routings[cp_key].enter_time:
                                        # 时间不相近则取新鲜的数据
                                        selected_routings[cp_key] = routing
                                        # Logger().sdebug('enter_time far so select fresh routing')


                    if 'ERROR' not in s_search_info.return_status:  # 有任何一个供应商成功了则认为该节点成功 TODO 临时使用return_status 进行区分，会有耦合，后续需要强定义错误类型
                        # 报错
                        # Logger().sdebug('set node_has_success')
                        node_has_success = True

                    self.route_result.add_provider_status(provider_channel=s_provider_app.provider_channel, return_status=s_search_info.return_status,
                                                          assoc_search_routings_amount=len(s_search_info.assoc_search_routings), return_details=s_search_info.return_details,
                                                          latency=s_search_info.total_latency, search_time=s_search_info.search_time)

                # 判断路由是否执行完成
                if index == len(self.route_strategy) - 1:
                    # Logger().sdebug('set route_pipeline_done ')
                    self.route_result.route_pipeline_done = True

                if not selected_routings:
                    if not node_has_success:
                        # Logger().sdebug('error node %s' % index)
                        # 没有航线并且没有任何一个成功标记，将判断为报错
                        if rst['stop_flag']['error'] == True:
                            self.route_result.route_pipeline_done = True
                            # self.route_result.last_status = 'ERROR'

                            return
                        else:
                            continue
                    else:
                        # 没航班
                        # Logger().sdebug('noflight node %s' % index)
                        if rst['stop_flag']['noflight'] == True:
                            self.route_result.route_pipeline_done = True
                            # self.route_result.last_status = 'NOFLIGHT'

                            return
                        else:
                            continue
                else:
                    # 有航班
                    # Logger().sdebug('has flight node %s' % index)
                    # self.route_result.last_status = 'SUCCESS'
                    self.route_result.assoc_search_routings = selected_routings.values()
                    self.route_result.route_pipeline_done = True
                    return
        except Exception as e:
            self.route_result.is_route_exception = True
            Logger().serror('Route error %s' % str(e))


if __name__ == '__main__':
    pass
