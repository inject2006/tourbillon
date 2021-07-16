#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, too-many-arguments, broad-except, anomalous-backslash-in-string
# pylint: disable=missing-docstring, line-too-long, too-few-public-methods
"""
# @Author  : wxt
# @Software: PyCharm
"""
import logging
import json
import gevent, datetime
import requests
from pony.orm import *
import pony.orm.core
from flask_script import Manager, Command, Option
from ..utils.exception import *
from ..utils.util import Time
from ..dao.models import *
from ..dao.internal import *
from ..utils.logger import Logger
from app import TBG
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.schedulers.gevent import GeventScheduler
from ..automatic_repo.base import ProviderAutoRepo
from ..utils.util import run_in_thread
from ..dao.redis_dao import RedisPool
from ..controller.pokeman import Pokeman


class Automator(Command):
    """
    """

    option_list = (
        Option('--task_exec', '-e', dest='task_exec'),
    )

    def __init__(self, **kwargs):
        pass

    def run(self, task_exec):
        if task_exec:
            Logger().sinfo('Runing %s right now' % task_exec)
            getattr(self, task_exec)()
            Logger().sinfo('Task End %s' % task_exec)
        else:
            Logger().sinfo('no task exec')

    @db_session
    def t1(self):
        """
        从ota日志中拉取错误
        :return:
        """
        Logger().sinfo('t1 start')
        ovs = select(s for s in OTAVerify if s.create_time > Time.days_before(4))

        error_set = set([])
        for r in ovs:
            if r.providers_stat:
                pst_list = json.loads(r.providers_stat)
                for pst in pst_list:
                    error_set.add(pst['provider_channel'])
                    if pst['provider_channel'] in ['igola_provider_agent','tuniu_provider_agent','tc_provider_agent']:
                        print pst
                    # return_details = pst.get('return_details','')
                    # if len(return_details) > 30:
                    #     t = "%s||%s||%s" % (pst['provider_channel'],pst['return_status'],pst['return_details'])
                    #     error_set.add(t)

        print error_set

        # a = set([u'igola_provider_agent||PROVIDER_VERIFY_SUCCESS||sequence item 0: expected string, NoneType found', u"ceair_web_2||UNKNOWN_ERROR||CACHE_EXPIRED,invalid literal for int() with base 10: 'Q'", u"ceair_web_2||UNKNOWN_ERROR||CACHE_EXPIRED,invalid literal for int() with base 10: '0-15'", u'NX_PROVIDER_WEB||UNKNOWN_ERROR||CACHE_NOFLIGHT_ALL,airmacau have no did', u"ceair_web_2||UNKNOWN_ERROR||\u822a\u73ed\u67e5\u8be2\u9519\u8bef,err_code:HIGH_REQ_LIMIT,invalid literal for int() with base 10: '0-15'", u'ceair_web_2||RTS_ERROR||CACHE_EXPIRED,ceair search web no flight', u'ceair_web_2||RTS_ERROR||CACHE_NOFLIGHT_ALL,ceair search web no flight', u'NX_PROVIDER_WEB||UNKNOWN_ERROR||CACHE_EXPIRED,airmacau have no did', u'ZH_PROVIDER_WEB||RTS_ERROR||\u822a\u73ed\u67e5\u8be2\u9519\u8bef,err_code:ERROR,CACHE_NOFLIGHT_ALL', u'ZH_PROVIDER_WEB||RTS_ERROR||CACHE_EXPIRED,\u822a\u73ed\u67e5\u8be2\u9519\u8bef,err_code:ERROR', u'ceair_web_2||RTS_SUCCESS||CACHE_EXPIRED,ceair search web no flight', u"ceair_web_2||UNKNOWN_ERROR||invalid literal for int() with base 10: 'L',CACHE_EXPIRED", u"ceair_web_2||RTS_ERROR||CACHE_EXPIRED,\u822a\u73ed\u67e5\u8be2\u9519\u8bef,err_code:HIGH_REQ_LIMIT,invalid literal for int() with base 10: '0-15'", u'ceair_web_2||RTS_ERROR||CACHE_EXPIRED,\u822a\u73ed\u67e5\u8be2\u9519\u8bef,err_code:HIGH_REQ_LIMIT', u'ceair_web_2||RTS_ERROR||\u822a\u73ed\u67e5\u8be2\u9519\u8bef,err_code:HIGH_REQ_LIMIT,CACHE_NOFLIGHT_ALL', u'ceair_web_2||RTS_SUCCESS||CACHE_EXPIRED,\u822a\u73ed\u67e5\u8be2\u9519\u8bef,err_code:HIGH_REQ_LIMIT,ceair search web no flight', u'ceair_web_2||RTS_ERROR||\u822a\u73ed\u67e5\u8be2\u9519\u8bef,err_code:HIGH_REQ_LIMIT,ceair search web no flight', u"ceair_web_2||RTS_ERROR||\u822a\u73ed\u67e5\u8be2\u9519\u8bef,err_code:HIGH_REQ_LIMIT,invalid literal for int() with base 10: '0-15'", u'ceair_web_2||RTS_SUCCESS||CACHE_EXPIRED,\u822a\u73ed\u67e5\u8be2\u9519\u8bef,err_code:HIGH_REQ_LIMIT', u"ceair_web_2||UNKNOWN_ERROR||CACHE_EXPIRED,\u822a\u73ed\u67e5\u8be2\u9519\u8bef,err_code:HIGH_REQ_LIMIT,invalid literal for int() with base 10: '0-15'", u"ceair_web_2||RTS_ERROR||CACHE_EXPIRED,\u822a\u73ed\u67e5\u8be2\u9519\u8bef,err_code:HIGH_REQ_LIMIT,invalid literal for int() with base 10: 'Q'", u'ceair_web_2||RTS_ERROR||\u822a\u73ed\u67e5\u8be2\u9519\u8bef,err_code:HIGH_REQ_LIMIT,CACHE_NOFLIGHT_ALL,ceair search web no flight', u'ch_web||UNKNOWN_ERROR||CACHE_NOFLIGHT_ALL,list index out of range', u'ZH_PROVIDER_WEB||RTS_SUCCESS||CACHE_EXPIRED,\u822a\u73ed\u67e5\u8be2\u9519\u8bef,err_code:ERROR', u"ceair_web_2||UNKNOWN_ERROR||CACHE_EXPIRED,\u822a\u73ed\u67e5\u8be2\u9519\u8bef,err_code:HIGH_REQ_LIMIT,invalid literal for int() with base 10: 'Q'", u'ceair_web_2||RTS_ERROR||CACHE_EXPIRED,\u822a\u73ed\u67e5\u8be2\u9519\u8bef,err_code:HIGH_REQ_LIMIT,ceair search web no flight', u'ch_web||UNKNOWN_ERROR||CACHE_EXPIRED,list index out of range', u"tuniu_provider_agent||PROVIDER_VERIFY_ERROR||invalid literal for int() with base 10: ''", u'igola_provider_agent||PROVIDER_VERIFY_ERROR||sequence item 0: expected string, NoneType found', u'igola_provider_agent||RTS_SUCCESS||sequence item 0: expected string, NoneType found', u'tc_provider_agent||PROVIDER_VERIFY_SUCCESS||No JSON object could be decoded'])
        #
        # for x in a:
        #     print x

    def t2_ex(self,provider_channel):
        """

        :return:
        """
        from influxdb import InfluxDBClient
        client = InfluxDBClient(TBG.global_config['METRICS_SETTINGS']['host'], TBG.global_config['METRICS_SETTINGS']['port'], TBG.global_config['METRICS_SETTINGS']['user'],
                                TBG.global_config['METRICS_SETTINGS']['password'], TBG.global_config['METRICS_SETTINGS']['db'])
        Logger().sinfo('start provider_channel %s' % provider_channel)
        provider_app = ProviderAutoRepo.select(provider_channel)
        result = client.query(
            'SELECT sum("total_count") FROM "search_3h"."PD_ASYNC_SEARCH" WHERE ("return_status" = \'NO_SCHEDULED_AIRLINE\') AND time >= now() - 5m GROUP BY "from_to_airport","%s","from_date" fill(null) ' % provider_channel)
        no_sched_airline_list = []
        for point in result.keys():
            p = point[1]
            __ = p['from_to_airport']
            from_date = p['from_date']
            from_airport = __.split('-')[0][:3]
            to_airport = __.split('-')[1][:3]
            no_sched_airline_list.append([from_airport, to_airport, from_date])

        Logger().sinfo('no_sched_airline_list length %s' % len(no_sched_airline_list))
        error_count = 0
        total_count = 0
        for from_airport, to_airport, from_date in no_sched_airline_list:

            search_info = SearchInfo()
            search_info.from_airport = from_airport
            search_info.to_airport = to_airport
            search_info.from_date = from_date
            search_info.trip_type = 'OW'
            search_info.adt_count = 1
            search_info.chd_count = 0
            search_info.attr_competion()
            provider_app.ota_fare_search(search_info=search_info, cache_mode='CACHE', allow_expired=False)  # 仅搜索缓存中的数据，不允许过期
            # Logger().sinfo('from_airport %s to_airport %s provider_channel %s from_date %s return_status %s' % (from_airport,to_airport,provider_channel,from_date,search_info.return_status))
            if search_info.assoc_search_routings:
                error_count += 1
            Logger().sinfo('from_airport %s to_airport %s provider_channel %s from_date %s return_status %s' % (from_airport,to_airport,provider_channel,from_date,search_info.return_status))

            total_count += 1

        Logger().sinfo('total_count %s error_count %s' % (total_count, error_count))

    @db_session
    def t2(self):
        """

        :return:
        """



        # today = datetime.date.today()
        # yesterday = today - datetime.timedelta(days=1)
        # yesterday_start_time = int(time.mktime(time.strptime(str(yesterday), '%Y-%m-%d'))) * 1000
        # yesterday_end_time = int(time.mktime(time.strptime(str(today), '%Y-%m-%d'))) * 1000 - 1
        # Logger().sdebug('time_range %s %s' % (yesterday_start_time, yesterday_end_time))

        # 搜索总数



        from influxdb import InfluxDBClient
        client = InfluxDBClient(TBG.global_config['METRICS_SETTINGS']['host'], TBG.global_config['METRICS_SETTINGS']['port'], TBG.global_config['METRICS_SETTINGS']['user'],
                                TBG.global_config['METRICS_SETTINGS']['password'], TBG.global_config['METRICS_SETTINGS']['db'])

        result = client.query(
            'SELECT sum("total_count") FROM "search_3h"."PD_ASYNC_SEARCH" WHERE ("return_status" = \'NO_SCHEDULED_AIRLINE\') AND time >= now() - 5m GROUP BY "from_to_airport","provider_channel" fill(null) ')
        no_sched_airline_list = set([])
        point_count = []
        for point in result.raw.get('series', []):
            point_count.append(point['values'][0][1])
            count = point['values'][0][1]
            # TODO 该参数后面需要动态调整
            if count > 12 and point['tags']['from_to_airport'] and point['tags']['provider_channel']:
                __ = point['tags']['from_to_airport']
                from_airport = __.split('-')[0][:3]
                to_airport = __.split('-')[1][:3]
                provider_channel = point['tags']['provider_channel']
                no_sched_airline_list.add('%s|%s|%s' % (provider_channel,from_airport,to_airport))


        Logger().sinfo('no_sched_airline_list length %s' % len(no_sched_airline_list))
        error_count = 0
        total_count = 0
        for record in no_sched_airline_list:
            from_date = '2019-04-18'
            provider_channel,from_airport, to_airport = record.split('|')
            Logger().sinfo('start provider_channel %s' % provider_channel)
            provider_app = ProviderAutoRepo.select(provider_channel)
            search_info = SearchInfo()
            search_info.from_airport = from_airport
            search_info.to_airport = to_airport
            search_info.from_date = from_date
            search_info.trip_type = 'OW'
            search_info.adt_count = 1
            search_info.chd_count = 0
            search_info.attr_competion()
            provider_app.ota_fare_search(search_info=search_info, cache_mode='CACHE', allow_expired=False)  # 仅搜索缓存中的数据，不允许过期
            # Logger().sinfo('from_airport %s to_airport %s provider_channel %s from_date %s return_status %s' % (from_airport,to_airport,provider_channel,from_date,search_info.return_status))
            if search_info.assoc_search_routings:
                error_count += 1
            Logger().sinfo('from_airport %s to_airport %s provider_channel %s from_date %s return_status %s' % (from_airport, to_airport, provider_channel, from_date, search_info.return_status))

            total_count += 1

        Logger().sinfo('total_count %s error_count %s' % (total_count, error_count))

        # for provider_channel in provider_channels:
        #     threads.append(run_in_thread(self.t2_ex,provider_channel=provider_channel))
        #
        # for t in threads:
        #     t.join()
        return
        self.search_control(search_info=search_info,
                            allow_expired=allow_expired,
                            expired_mode=expired_mode,
                            allow_cabin_attenuation=True,
                            cache_mode=cache_mode,
                            allow_freq_limit=False,
                            freq_limit_mode='WAIT',
                            freq_limit_wait_timeout=2,
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

if __name__ == '__main__':
    pass
