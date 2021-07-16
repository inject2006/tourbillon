# coding=utf8

import time, json
import os
import base64
from app import TBG
from ..dao.internal import FareInfo, SearchInfo
from ..automatic_repo.base import ProviderAutoRepo
from ..utils.logger import Logger, logger_config
from ..utils.util import Time, tb_gevent_spawn, Random, RoutingKey
from ..controller.dynamic_fare import DynamicFareRuleEngine
import gevent


class LowpriceStabilizer():
    """
    低价稳定器，用于将某条routing的价格维持在露出并且保证盈利的状态
    """

    @staticmethod
    @logger_config('LP_STABLE', True)
    def worker(task):
        """
        业务逻辑
        :return:
        """
        max_low_price_stable_interval = 60
        try:
            TB_OTA_NAME = task['ota_name']
            TB_REQUEST_ID = Random.gen_request_id()
            Logger().sinfo('worker start')
            TB_ORDER_ID = RoutingKey.trans_cc_key(task['search_info']['rk_info'], is_unserialized=True)
            TB_PROVIDER_CHANNEL = task['low_price_provider_channel']
            fare_info = FareInfo(**task['fare_info'])
            if fare_info.low_price_stable_interval <= 0:
                fare_info.low_price_stable_interval = 5  # 默认为五秒钟

            current_ota_r1_price = fare_info.get("ota_r1_price",0)
            Logger().sinfo('current_ota_r1_price %s' % current_ota_r1_price)
            min_low_price_stable_interval = fare_info.low_price_stable_interval
            while 1:
                Logger().sdebug('worker loop')
                if fare_info.expired_time < Time.timestamp_s():
                    Logger().sinfo('expired expired_time %s' % fare_info.expired_time)
                    break

                Logger().sinfo('current low_price_stable_interval %s' % fare_info.low_price_stable_interval)
                fare_ota_search_info = SearchInfo(**task['search_info'])
                Logger().sinfo('fare_ota_search_info %s' % fare_ota_search_info)
                fare_ota_search_info.attr_competion()
                # 防止人数导致干扰
                fare_ota_search_info.adt_count = 1
                fare_ota_search_info.chd_count = 0
                fare_ota_search_info.inf_count = 0
                provider_app = ProviderAutoRepo.select(task['low_price_provider_channel'])
                provider_app.flight_search(search_info=fare_ota_search_info, cache_mode='MIX', allow_expired=True, custom_expired_time=1)

                fare_ota_search_info.rk_info['dep_time'] = 'N/A'  # 因为某些低价看板没有dep_time
                fare_ota_search_info.rk_info['arr_time'] = 'N/A'  # 因为某些低价看板没有dep_time

                # 不包含舱位 则对比航班最低价
                vkey = RoutingKey.trans_cc_key(fare_ota_search_info.rk_info, is_unserialized=True)

                ota_r1_price = None
                ota_r2_price = None
                for frouting in fare_ota_search_info.assoc_search_routings:

                    rk_dict = RoutingKey.unserialize(frouting.routing_key_detail)
                    rk_dict['dep_time'] = 'N/A'
                    rk_dict['arr_time'] = 'N/A'
                    # Logger().debug('frouting.............%s' % frouting)

                    # 不包含舱位 则对比航班最低价
                    key = RoutingKey.trans_cc_key(rk_dict, is_unserialized=True)
                    Logger().sinfo('vkey =  %s fkey = %s' % (vkey,key))
                    fr_ota_r1_price = rk_dict['adult_price'] + rk_dict['adult_tax']
                    fr_ota_r2_price = frouting.reference_adult_price + frouting.reference_adult_tax
                    if not fr_ota_r2_price:
                        fr_ota_r2_price = fr_ota_r1_price  # 保证r2有数据
                    if vkey == key:
                        Logger().sinfo('EQ  vkey =  %s fkey = %s' % (vkey, key))
                        if ota_r1_price:
                            if ota_r1_price > fr_ota_r1_price:
                                ota_r1_price = fr_ota_r1_price
                                ota_r2_price = fr_ota_r2_price
                                Logger().sinfo('ota_r1_price update %s' % fr_ota_r1_price)
                        else:
                            ota_r1_price = fr_ota_r1_price
                            ota_r2_price = fr_ota_r2_price
                            Logger().sinfo('ota_r1_price create %s' % fr_ota_r1_price)

                is_r1_changed = 0
                if ota_r1_price:
                    has_ota_r1_price = 1
                    fare_info.sdp = 0
                    fare_info.ota_r1_price = ota_r1_price
                    fare_info.ota_r2_price = ota_r2_price

                    if current_ota_r1_price == ota_r1_price:
                        # 价格跟上一次价格一致，不需要更新
                        is_r1_changed = 0

                        fare_info.low_price_stable_interval += 5
                        if fare_info.low_price_stable_interval > max_low_price_stable_interval:
                            fare_info.low_price_stable_interval = max_low_price_stable_interval
                    else:
                        fare_info.low_price_stable_interval = min_low_price_stable_interval
                        is_r1_changed = 1
                        current_ota_r1_price = ota_r1_price

                        DynamicFareRuleEngine.upsert_low_price_cache(ota_name=task['ota_name'], from_airport=fare_ota_search_info.from_airport, to_airport=fare_ota_search_info.to_airport,
                                                                     from_date=fare_ota_search_info.from_date, ret_date=fare_ota_search_info.ret_date,
                                                                     trip_type=fare_ota_search_info.trip_type, dfr_hash=fare_ota_search_info.rk_info['flight_number'], fare_info=fare_info,
                                                                     ttl=fare_info.ttl)

                else:
                    has_ota_r1_price = 0
                    fare_info.low_price_stable_interval += 10
                    if fare_info.low_price_stable_interval > max_low_price_stable_interval:
                        fare_info.low_price_stable_interval = max_low_price_stable_interval
                    Logger().sinfo('low price search nothing continue')


                Logger().sinfo('is_r1_changed %s has_ota_r1_price %s fare_info %s' % (is_r1_changed,has_ota_r1_price,fare_info))
                TBG.tb_metrics.write(
                    "LOWPRICE_STABILIZER",
                    tags=dict(
                        ota_name=TB_OTA_NAME,
                        from_to_airport='%s%s-%s%s' % (fare_ota_search_info.from_airport, fare_ota_search_info.from_city, fare_ota_search_info.to_airport, fare_ota_search_info.to_city),
                        flight_number=fare_ota_search_info.rk_info['flight_number'],
                        trip_type=fare_ota_search_info.trip_type,
                        from_date=fare_ota_search_info.from_date,
                        ret_date=fare_ota_search_info.ret_date,

                    ),
                    fields=dict(
                        total_count=1,
                        price_changed_count=is_r1_changed,  # 价格变化频率，反映出竞价是否激烈
                        has_ota_r1_price_count=has_ota_r1_price,  # 获取到r1价格
                    ))
                gevent.sleep(fare_info.low_price_stable_interval)
        except Exception as e:
            Logger().error(e)


    @staticmethod
    def run(body):

        TB_SUB_ORDER_ID = Random.gen_request_id()
        Logger().sinfo('task %s' % body)
        timeout = body['fare_info']['expired_time'] - Time.timestamp_s()

        # 如果队列存在阻塞的情况下，查看该任务是否还有可执行的必要性，如果超时则放弃
        if timeout > 0:
            tb_gevent_spawn(LowpriceStabilizer.worker, task=body)
        else:
            Logger().sinfo('expired timeout %s' % timeout)



if __name__ == "__main__":
    aq = LowpriceStabilizer()
