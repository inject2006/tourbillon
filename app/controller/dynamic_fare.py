#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, too-many-arguments, broad-except, anomalous-backslash-in-string
# pylint: disable=missing-docstring, line-too-long, too-few-public-methods
"""
# @Author  : wxt
# @Software: PyCharm
三方数据辅助查询模块
"""

import datetime
import time
import json
from ..utils.logger import Logger
from ..dao.models import DynamicFareRepo, PrimaryFareCrawlTask
from ..dao.internal import FareInfo
from pony.orm import select, db_session
from ..utils.util import Time
from app import TBG


df_rules = {}
is_load = False
class DynamicFareRuleEngine(object):
    """
    动态运价引擎
    """

    @staticmethod
    def process(ota_name, from_airport, to_airport, from_date, flight_number, routing, ret_date='', trip_type='OW',):
        """
        对比引擎数据返回运价信息
        :param rk_dict:
        :return: [-33,'AUTO_PROFIT']
        """
        global df_rules,is_load
        # Logger().sdebug('processing dfr_hash %s' %(dfr_hash))
        # Logger().sinfo('df_rulesssssssssssssssssssssss %s' % df_rules)
        # result = DynamicFareRuleEngine.search_from_l1cache(from_airport=from_airport, to_airport=to_airport, from_date=from_date, provider=provider,ret_date=ret_date,trip_type=trip_type,dfr_hash=dfr_hash)
        # if result:
        #     return result
        # else:
        if not ret_date:
            ret_date = ''

        dfr_hash = '{ota_name}|{from_airport}|{to_airport}|{from_date}|{flight_number}|{ret_date}|{trip_type}'.format(ota_name=ota_name,
                                                                                               from_airport=from_airport,
                                                                                               to_airport=to_airport,
                                                                                               from_date=from_date,
                                                                                               flight_number=flight_number,ret_date=ret_date,trip_type=trip_type)

        if dfr_hash in df_rules:
            # fare_date 格式 [ota_r1_price,ota_r2_price,bidding_diff_price,stop_loss,stop_profit,priority,dfr_id]
            fare_data = df_rules[dfr_hash]
            fare_info = FareInfo(ota_r1_price=fare_data[0],ota_r2_price=fare_data[1],bidding_diff_price=fare_data[2],stop_loss=fare_data[3],stop_profit=fare_data[4],priority=fare_data[5],assoc_fare_info=fare_data[6])
            if routing.cost_price <= fare_info.ota_r1_price:
                # 提升盈利
                if fare_info.ota_r2_price > fare_info.ota_r1_price:
                    fare_info.fare_put_mode = 'AUTO_BOOST_PROFIT'
                    sdp = fare_info.ota_r2_price + fare_info.bidding_diff_price - routing.cost_price
                else:
                    # r1 == r2
                    fare_info.fare_put_mode = 'AUTO_BOOST_SHOW'
                    sdp = fare_info.ota_r1_price + fare_info.bidding_diff_price - routing.cost_price
            else:
                fare_info.fare_put_mode = 'AUTO_BOOST_SHOW'
                # 提升露出
                sdp = fare_info.ota_r1_price + fare_info.bidding_diff_price - routing.cost_price

            # 止损止盈控制
            if sdp < fare_info.stop_loss:
                fare_info.sdp = fare_info.stop_loss
            elif sdp > fare_info.stop_profit:
                fare_info.sdp = fare_info.stop_profit
            else:
                fare_info.sdp = sdp

            routing.adult_price_forsale = routing.adult_price + fare_info.sdp if routing.adult_price + fare_info.sdp > 0 else 1
            # routing.child_price_forsale = routing.child_price + fare_info.sdp if routing.child_price + fare_info.sdp > 0 else 1
            routing.rk_dict['adult_price_forsale'] = routing.adult_price_forsale
            # routing.rk_dict['child_price_forsale'] = routing.child_price_forsale
            routing.rk_dict['fare_put_mode'] = fare_info.fare_put_mode
            routing.rk_dict['assoc_fare_info'] = fare_info.assoc_fare_info
            routing.fixed_offer_price = routing.adult_price_forsale + routing.rk_dict['adult_tax']
            Logger().sdebug('---df_result--- routing.fixed_offer_price  %s routing_key_detail %s fare_info.sdp %s fare_info %s' % (routing.fixed_offer_price, routing.routing_key_detail,sdp,fare_info))
            return fare_info
        else:
            return None

    @staticmethod
    def process_low_price(routing,fare_info):
        """
        处理低价稳定器的数据
        :return:
        """
        verify_stop_loss = fare_info.verify_stop_loss.get(routing.rk_dict['provider_channel'], fare_info.verify_stop_loss['default'])
        verify_stop_profit = fare_info.verify_stop_profit.get(routing.rk_dict['provider_channel'], fare_info.verify_stop_profit['default'])

        fare_info.ota_r1_price = int(eval(fare_info.estimate_ota_diff_price.replace('x', str(fare_info.ota_r1_price))))
        fare_info.ota_r2_price = int(eval(fare_info.estimate_ota_diff_price.replace('x', str(fare_info.ota_r2_price))))

        is_show = 0
        if fare_info.ota_r1_price:
            # 查询到低价看板数据
            if fare_info.ota_r1_price > fare_info.ota_r2_price:
                # 认为数据有错误，将两者进行对调
                r1 = fare_info.ota_r1_price
                fare_info.ota_r1_price = fare_info.ota_r2_price
                fare_info.ota_r2_price = r1

            if fare_info.offer_price < fare_info.ota_r1_price:
                # 将价格调整到靠近最低价下方 提升露出
                sdp = fare_info.ota_r1_price + fare_info.bidding_diff_price - fare_info.cost_price
            elif fare_info.offer_price == fare_info.ota_r1_price:
                if fare_info.ota_r2_price > fare_info.ota_r1_price:
                    sdp = fare_info.ota_r2_price + fare_info.bidding_diff_price - fare_info.cost_price
                else:
                    sdp = 0
            else:
                # 提升露出
                sdp = fare_info.ota_r1_price + fare_info.bidding_diff_price - fare_info.cost_price

            # 止损止盈控制
            if sdp < verify_stop_loss:
                fare_info.sdp = verify_stop_loss
            elif sdp > verify_stop_profit:
                fare_info.sdp = verify_stop_profit
            else:
                fare_info.sdp = sdp

            fare_info.low_price = fare_info.cost_price + fare_info.sdp
            fare_info.low_adult_price = fare_info.cost_adult_price + fare_info.sdp
            if fare_info.low_price - fare_info.offer_price > 0:
                # 二次运价价格比一次运价价格高
                fare_info.fare_put_mode = 'FARE_UP_TWICE'
            elif fare_info.low_price - fare_info.offer_price < 0:
                # 二次运价价格比一次运价价格低
                fare_info.fare_put_mode = 'FARE_DOWN_TWICE'
            else:
                # 二次运价价格比一次运价价格相等
                fare_info.fare_put_mode = 'FARE_EQ_TWICE'

            if fare_info.low_price <= fare_info.ota_r1_price:  # 通过低价看板判断是否露出，由于并非实时性，所以有判断误差
                is_show = 1
            # Logger().sdebug('sdp %s fare_put_mode %s' % (fare_info.sdp, fare_info.fare_put_mode))

        else:
            ratio = 0.8 # 固定一个百分比
            fare_info.low_price = int(fare_info.cost_price + verify_stop_loss * ratio)  # 将价格调整到止损差内,
            fare_info.low_adult_price = int(fare_info.cost_adult_price + verify_stop_loss * ratio)
            fare_info.fare_put_mode = 'LOWPRICE_FORECAST'

        if routing.fixed_offer_price < fare_info.low_price:
            routing.rk_dict['assoc_fare_info'] = '%s;%s;%s;%s;%s;%s;%s' % (fare_info.ota_r1_price,fare_info.ota_r2_price,fare_info.cost_price,fare_info.offer_price,verify_stop_loss,verify_stop_profit,is_show)  # 记录实时运价的相关数据
            Logger().sdebug("routing.rk_dict['assoc_fare_info'] %s" % routing.rk_dict['assoc_fare_info'])
            routing.adult_price_forsale = fare_info.low_adult_price if fare_info.low_adult_price > 0 else 1
            # routing.child_price_forsale = fare_info.low_adult_price if fare_info.low_adult_price > 0 else 1
            routing.rk_dict['adult_price_forsale'] = fare_info.low_adult_price
            # routing.rk_dict['child_price_forsale'] = fare_info.low_adult_price
            routing.rk_dict['fare_put_mode'] = fare_info.fare_put_mode
        else:
            pass
            # Logger().sdebug("routing.fixed_offer_price > fare_info.low_price")

    @staticmethod
    @TBG.fcache.memoize(TBG.global_config['FCACHE_TIMEOUT_FARE_LOW_PRICE_CACHE'])
    def load_from_low_price_cache(ota_name, from_airport, to_airport, from_date, ret_date, trip_type):
        """
        从L1cache中进行搜索
        :param :
        :return:
        """
        if not ret_date:
            ret_date = ''
        param_model = {
            "from_airport": from_airport,
            "to_airport": to_airport,
            "from_date": from_date,
            "ret_date": ret_date,
            "trip_type": trip_type,
            "ota_name": ota_name
        }
        # Logger().sdebug('load_from_low_price_cache param_model %s' % param_model)

        rules_from_cache = TBG.cache_access_object.get(cache_type='df_low_price_cache', provider='all', param_model=param_model)
        if rules_from_cache:
            return rules_from_cache
        return {}

    @staticmethod
    def upsert_low_price_cache(ota_name, from_airport, to_airport, from_date, dfr_hash, fare_info,ret_date='', trip_type='OW',ttl=300):
        """
        添加L1缓存
        :return: dfr_hash == flight_number
        """
        if not ret_date:
            ret_date = ''
        param_model = {
            "from_airport": from_airport,
            "to_airport": to_airport,
            "from_date": from_date,
            "ret_date": ret_date,
            "trip_type": trip_type,
            "ota_name": ota_name
        }
        data = TBG.cache_access_object.get(cache_type='df_low_price_cache', provider='all', param_model=param_model)
        if data:
            data[dfr_hash] = fare_info
            Logger().sinfo('upsert_low_price_cache 【update】 param_model %s fare_info %s' % (param_model, fare_info))

        else:
            Logger().sinfo('upsert_low_price_cache 【insert】 param_model %s fare_info %s' % (param_model, fare_info))

            data = {
                dfr_hash: fare_info
            }
        TBG.cache_access_object.insert(
            cache_type='df_low_price_cache',
            provider='all',
            param_model=param_model,
            ret_data=data,
            expired_time=ttl,
            is_compress=False
        )

    @staticmethod
    @db_session
    def upsert_l2_cache(dfr_id, ota_r1_price, ota_r2_price, offer_price, cost_price):
        """
        更新dynamic_fare 表数据
        :return:
        """
        try:
            dfr = DynamicFareRepo[dfr_id]
            dfr.ota_r1_price = ota_r1_price
            dfr.ota_r2_price = ota_r2_price
            dfr.offer_price = offer_price
            dfr.cost_price = cost_price
            dfr.ver = dfr.ver + 1
            Logger().sdebug('update l2 id %s succeed ota_r1_price %s ota_r2_price %s offer_price %s cost_price %s' % (dfr_id, ota_r1_price, ota_r2_price, offer_price, cost_price))
        except Exception as e:
            Logger().error('update l2 cache error')

    @staticmethod
    @db_session
    def load():
        """
        将Mysql数据加载到内存dict
        dict 格式
        {'ota_name|from_airport|to_airport|from_date|flight_number|cabin':[-30,'A+M']}
        :return:
        """
        global df_rules,is_load
        df_rules = {}
        from ..automatic_repo.base import ProviderAutoRepo
        task_list = select(o for o in PrimaryFareCrawlTask if o.task_type == 'DYNAMIC_FARE' and o.task_status == 'RUNNING')

        query_pfct_ids = {}  # 开启中的爬取运价任务id
        enable_dynamic_fare_pfct_ids = []  # 开启自动投放模式的任务
        for task in task_list:
            provider, provider_channel = json.loads(task.providers)[0]
            query_pfct_ids[task.id] = {'bidding_diff_price': task.bidding_diff_price,
                                       'estimate_ota_diff_price': task.estimate_ota_diff_price,
                                       'stop_loss': task.stop_loss,
                                       'stop_profit': task.stop_profit,
                                       'ota_name': task.ota,
                                       'provider': provider,
                                       'priority': task.priority,
                                       'start_day': task.start_day,
                                       'within_days': task.within_days}
            if task.is_enable_auto_put == 1:  # 是否开启自动投放
                enable_dynamic_fare_pfct_ids.append(task.id)

        # dfr_list = select(o for o in DynamicFareRepo if o.update_time > Time.hours_before(6))

        # 只对浮动看板三个小时之内的数据进行投放
        dfr_list = select(o for o in DynamicFareRepo if
                o.primary_fare_crawl_task.id in enable_dynamic_fare_pfct_ids and o.ota_r1_price > 0 and o.update_time > Time.hours_before(3))

        for dfr in dfr_list:
            assoc_pfct = query_pfct_ids[dfr.primary_fare_crawl_task.id]
            if assoc_pfct['start_day'] <= (dfr.from_date - datetime.date.today()).days <= assoc_pfct['within_days']:

                dfr_hash = '{ota_name}|{from_airport}|{to_airport}|{from_date}|{flight_number}|{ret_date}|{trip_type}'.format(ota_name=assoc_pfct['ota_name'],
                                                                                                       from_airport=dfr.from_airport, to_airport=dfr.to_airport,
                                                                                                       from_date=str(dfr.from_date),
                                                                                                       flight_number=dfr.flight_number,ret_date=str(dfr.ret_date) if dfr.ret_date else '',
                                                                                                       trip_type=dfr.trip_type)

                if dfr.primary_fare_crawl_task.id in enable_dynamic_fare_pfct_ids:
                    ota_r1_price = int(eval(assoc_pfct['estimate_ota_diff_price'].replace('x', str(dfr.ota_r1_price))))
                    ota_r2_price = int(eval(assoc_pfct['estimate_ota_diff_price'].replace('x', str(dfr.ota_r2_price))))
                    # 纯自动模式
                    # 新变动 2019-03-13 by wxt 将原始数据放入缓存，计算逻辑迁移至路由  [ota_r1_price,ota_r2_price,bidding_diff_price,stop_loss,stop_profit,priority]
                    if df_rules.has_key(dfr_hash):  # 优先级高替换优先级低的运价规则
                        if assoc_pfct['priority'] < df_rules[dfr_hash][5]:
                            df_rules[dfr_hash] = [ota_r1_price, ota_r2_price, assoc_pfct['bidding_diff_price'], assoc_pfct['stop_loss'], assoc_pfct['stop_profit'], assoc_pfct['priority'],dfr.id]
                    else:
                        df_rules[dfr_hash] = [ota_r1_price,ota_r2_price,assoc_pfct['bidding_diff_price'],assoc_pfct['stop_loss'],assoc_pfct['stop_profit'],assoc_pfct['priority'],dfr.id]

        Logger().debug('load df_rules %s' % df_rules)
        is_load = True

if __name__ == '__main__':
    pass
