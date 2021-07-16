#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, too-many-arguments, broad-except, anomalous-backslash-in-string
# pylint: disable=missing-docstring, line-too-long, too-few-public-methods
"""
# @Author  : wxt
# @Software: PyCharm
"""

import gevent, datetime
from pony.orm import *
import pony.orm.core
from flask_script import Manager, Command, Option
from ..utils.exception import *
from ..dao.models import *
from ..dao.internal import *
from ..utils.logger import Logger, logger_config
from ..utils.util import md5_hash, convert_unicode
from ..automatic_repo import ProviderAutoRepo
from ..ota_repo.base import OTARepo
from ..router.core import Router
from app import TBG
from app import TbPublisher
from apscheduler.schedulers.gevent import GeventScheduler
from apscheduler.schedulers.blocking import BlockingScheduler


class CrawlerController(Command):
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
            if task_exec == 'pr_task_1':
                self.pr_task(1)
            elif task_exec == 'pr_task_2':
                self.pr_task(2)
            elif task_exec == 'pr_task_3':
                self.pr_task(3)
            elif task_exec == 'pr_task_4':
                self.pr_task(4)
            elif task_exec == 'pr_task_5':
                self.pr_task(5)
            elif task_exec == 'pr_task_6':
                self.pr_task(6)
            elif task_exec == 'pr_task_7':
                self.pr_task(7)
            else:
                getattr(self, task_exec)()
            gevent.sleep(6)
            Logger().sinfo('Task End %s' % task_exec)
        else:
            # 正常模式
            # job_defaults = {
            #     'coalesce': False,
            #     'max_instances': 10,
            #     # 'misfire_grace_time': 3600,
            # }
            # executors = {
            #     'processpool': ProcessPoolExecutor(10)
            # }
            # scheduler = BlockingScheduler(executors=executors, job_defaults=job_defaults)

            # TODO 尝试采用gevent模式，因为去掉了celery 看看效果
            scheduler = GeventScheduler()

            scheduler.add_job(self.within_day_task, 'cron', hour=15)
            scheduler.add_job(self.task_controller, 'interval', seconds=10)

            scheduler.add_job(self.pr_task, 'interval', args=(5,), seconds=TBG.global_config['CRAWLER_PR_CONFIG'][5]['reference_time'])
            scheduler.add_job(self.pr_task, 'interval', args=(4,), seconds=TBG.global_config['CRAWLER_PR_CONFIG'][4]['reference_time'])
            scheduler.add_job(self.pr_task, 'interval', args=(3,), seconds=TBG.global_config['CRAWLER_PR_CONFIG'][3]['reference_time'])
            scheduler.add_job(self.pr_task, 'interval', args=(2,), seconds=TBG.global_config['CRAWLER_PR_CONFIG'][2]['reference_time'])
            scheduler.add_job(self.pr_task, 'interval', args=(1,), seconds=TBG.global_config['CRAWLER_PR_CONFIG'][1]['reference_time'])

            scheduler.add_job(self.pr_evaluation_task, 'interval', seconds=7200)

            # 动态运价爬虫 PR6 为动态运价和比价专有
            scheduler.add_job(self.pr_task, 'interval', args=(6,), seconds=60 * 15,
                              next_run_time=datetime.datetime.now() - datetime.timedelta(seconds=8 * 60 * 60) + datetime.timedelta(seconds=5 * 60))

            # 动态运价爬虫 PR6 为动态运价和比价专有
            scheduler.add_job(self.pr_task, 'interval', args=(7,), seconds=86400)
            scheduler.add_job(self.scheduled_airline_sampling_revise, 'interval', seconds=299)
            g = scheduler.start()
            try:
                g.join()
            except (KeyboardInterrupt, SystemExit):
                pass

    @logger_config('CWR_PREVAL_TASK')
    def pr_evaluation_task(self):
        """
        权重计算 通过最后一次爬取的座位数与最后一次导致PR权重变化的座位数进行环比
        :return:
        """
        exception = ''
        start_time = Time.timestamp_ms()
        try:
            Logger().sdebug('pr_evaluation_task Start')
            max_fcrd_id = TBG.redis_conn.get_value('pr_evaluation_fcrd_id_offset')
            if not max_fcrd_id:
                max_fcrd_id = 0
            Logger().sdebug('start fcrd_id %s' % max_fcrd_id)
            processed_sfct_ids = set([])
            while 1:
                with db_session:

                    # 暂时不对PR=6的数据进行评估，PR=6暂时为动态运价和比价专有
                    res = TBG.tourbillon_extra_db.execute(
                        'select secondary_fare_crawl_task.id,fare_crawl_repo_dl.id,secondary_fare_crawl_task.cabin_count_total,fare_crawl_repo_dl.cabin_count_total,secondary_fare_crawl_task.flightcount_cabin_1_8,fare_crawl_repo_dl.flightcount_cabin_1_8,secondary_fare_crawl_task.flightcount_total,fare_crawl_repo_dl.flightcount_total,secondary_fare_crawl_task.pr,fare_crawl_repo_dl.flightcount_cabin_a,fare_crawl_repo_dl.lowest_price,secondary_fare_crawl_task.from_date,secondary_fare_crawl_task.from_airport,secondary_fare_crawl_task.to_airport,fare_crawl_repo_dl.from_date,secondary_fare_crawl_task.lowest_price from secondary_fare_crawl_task left join fare_crawl_repo_dl on secondary_fare_crawl_task.id = fare_crawl_repo_dl.task_id where secondary_fare_crawl_task.task_status="RUNNING" and secondary_fare_crawl_task.pr < 6 and fare_crawl_repo_dl.id > %s order by fare_crawl_repo_dl.id desc limit 10000;' % (
                            max_fcrd_id))
                    is_return_data = False
                    # Logger().sdebug('processed res length %s' % len(res))
                    for r in res:
                        Logger().sdebug(r)
                        sfct_id = r[0]
                        fcrd_id = r[1]
                        if not is_return_data:
                            is_return_data = True
                            max_fcrd_id = fcrd_id
                        sfct_cabin_count_total = r[2]
                        fcrd_cabin_count_total = r[3]
                        sfct_flightcount_cabin_1_8 = r[4]
                        fcrd_flightcount_cabin_1_8 = r[5]
                        sfct_flightcount_total = r[6]
                        fcrd_flightcount_total = r[7]
                        sfct_pr = r[8]
                        fcrd_flightcount_cabin_a = r[9]
                        fcrd_lowest_price = r[10]
                        sfct_from_date = r[11]
                        sfct_from_airport = r[12]
                        sfct_to_airport = r[13]
                        fcrd_from_date = r[14]
                        sfct_lowest_price = r[15]
                        if sfct_id in processed_sfct_ids:
                            Logger().sdebug('pass sfct_id %s' % sfct_id)
                            continue
                        else:
                            processed_sfct_ids.add(sfct_id)
                            sfct = None
                            if fcrd_from_date > datetime.date.today():
                                # 当天的航班不做权重统计
                                if sfct_cabin_count_total:
                                    if float(fcrd_cabin_count_total) > float(sfct_cabin_count_total) * 1.2:
                                        pass
                                        # # 余位增加20%
                                        # if task.pr > 1:
                                        #     task.pr -= 1
                                        #     Logger().debug('pr decrease ')
                                    elif float(fcrd_cabin_count_total) < float(sfct_cabin_count_total) * 0.8 or \
                                            fcrd_flightcount_cabin_1_8 / float(fcrd_flightcount_total) > (sfct_flightcount_cabin_1_8 / float(sfct_flightcount_total)) * 1.2:
                                        # 余位减少20% 或者8个以下座位的比例上升20%

                                        Logger().sdebug('fcrd_cabin_count_total %s sfct_cabin_count_total %s' % (fcrd_cabin_count_total, sfct_cabin_count_total))
                                        if sfct_pr < 5:
                                            is_increase = True
                                            sfct = SecondaryFareCrawlTask[sfct_id]
                                            final_pr = sfct_pr + 1
                                            sfct.pr = final_pr
                                            sfct.cabin_count_total = fcrd_cabin_count_total
                                            sfct.flightcount_cabin_a = fcrd_flightcount_cabin_a
                                            sfct.flightcount_cabin_1_8 = fcrd_flightcount_cabin_1_8
                                            sfct.flightcount_total = fcrd_flightcount_total
                                            Logger().sdebug('pr increase ')
                                        else:
                                            is_increase = False

                                        TBG.tb_metrics.write(
                                            "CRAWLER.MANAGER.CWR_PREVAL_TASK.DL_CHANGE",
                                            tags=dict(
                                                from_date=str(sfct_from_date),
                                                from_airport=sfct_from_airport,
                                                to_airport=sfct_to_airport,
                                                pr=sfct_pr,
                                                is_increase=is_increase
                                            ),
                                            fields=dict(
                                                count=1
                                            ))
                            else:
                                Logger().sdebug('current day not calc')
                            if not sfct_cabin_count_total:
                                # 任务刚开始没有total的统计，需要新增
                                Logger().sdebug('cabin_count_total init')
                                if not sfct:
                                    sfct = SecondaryFareCrawlTask[sfct_id]
                                if fcrd_flightcount_cabin_1_8 / float(fcrd_flightcount_total) > 0.8:
                                    # 1-8的航班数占总航班数的80%以上
                                    sfct.pr = 5
                                sfct.cabin_count_total = fcrd_cabin_count_total
                                sfct.flightcount_cabin_a = fcrd_flightcount_cabin_a
                                sfct.flightcount_cabin_1_8 = fcrd_flightcount_cabin_1_8
                                sfct.flightcount_total = fcrd_flightcount_total
                            if not sfct_lowest_price:
                                if not sfct:
                                    sfct = SecondaryFareCrawlTask[sfct_id]
                                Logger().sdebug('lowest_price init')
                                sfct.lowest_price = fcrd_lowest_price
                        Logger().sdebug('commit')
                        flush()
                        commit()
                    if not is_return_data:
                        Logger().sdebug('save fcrd_id %s' % max_fcrd_id)
                        TBG.redis_conn.insert_value('pr_evaluation_fcrd_id_offset', max_fcrd_id)
                        break
            task_result = 'SUCCESS'
        except Exception as e:
            Logger().serror(e)
            task_result = 'ERROR'
            exception = str(e)
        Logger().sdebug('pr_evaluation_task End')

        total_latency = Time.timestamp_ms() - start_time

        TBG.tb_metrics.write(
            "CRAWLER.MANAGER",
            tags=dict(
                task='CWR_PREVAL_TASK',
                task_result=task_result,
                exception=exception

            ),
            fields=dict(
                total_latency=total_latency,
                count=1
            ))

    @logger_config('CWR_WITHINDAY_TASK')
    def within_day_task(self):
        """
        用于生成近期xx天内的任务
        :return:
        """
        exception = ''
        start_time = Time.timestamp_ms()
        try:
            with db_session:
                Logger().sdebug('within_day_task Start')
                # flight_segments = select(o for o in FlightRepo if o.is_crawl == 1)
                task_list = select(o for o in PrimaryFareCrawlTask if o.task_status in ['RUNNING'])
                Logger().sdebug(len(task_list))
                for task in task_list:
                    try:
                        c_day = Time.curr_date_obj_2()
                        toadd_day = c_day + datetime.timedelta(days=task.within_days + 1)

                        crawl_list = select(o for o in SecondaryFareCrawlTask if o.primary_task_id == task)

                        for secondary in crawl_list:
                            from_airport = secondary.from_airport
                            to_airport = secondary.to_airport
                            pr = secondary.pr
                            Logger().sdebug('within_day_task %s-%s add %s ' % (from_airport, to_airport, toadd_day))

                            if (toadd_day - c_day).days <= 7:
                                if pr < 4:
                                    set_pr = 4
                                else:
                                    set_pr = pr
                            elif 7 < (toadd_day - c_day).days <= 30:
                                if pr < 3:
                                    set_pr = 3
                                else:
                                    set_pr = pr
                            elif 30 < (toadd_day - c_day).days <= 60:
                                if pr < 2:
                                    set_pr = 2
                                else:
                                    set_pr = pr
                            else:
                                set_pr = pr

                            # TODO 临时在以下两种类型的任务添加 TASKID ，保证新的任务虽然航段重复但是依然可以爬取到
                            if secondary.task_type in ['DYNAMIC_FARE', 'FARE_COMPARISON']:
                                dl_hash = '%s%s%s%s%s%s%s' % (secondary.provider_channel, from_airport, to_airport, toadd_day.strftime('%Y-%m-%d'), secondary.trip_type, secondary.task_type, task.id)
                            else:
                                dl_hash = '%s%s%s%s%s%s' % (secondary.provider_channel, from_airport, to_airport, toadd_day.strftime('%Y-%m-%d'), secondary.trip_type, secondary.task_type)

                            try:
                                Logger().info("crawler within day task dlhash: {}".format(dl_hash))
                                sfct = SecondaryFareCrawlTask(provider=secondary.provider, provider_channel=secondary.provider_channel, pr=set_pr, from_date=toadd_day.strftime('%Y-%m-%d'),
                                                              from_airport=from_airport, to_airport=to_airport, task_status=secondary.task_status,
                                                              dl_hash=dl_hash, primary_task_id=task, task_type=secondary.task_type,start_day=secondary.start_day,trip_type=secondary.trip_type)
                                commit()
                            except Exception as e:
                                # 如果插入重复会报错
                                Logger().error("crawler within day task add error: {}".format(e))
                    except Exception as e:
                        Logger().serror(e)
            task_result = 'SUCCESS'
        except Exception as e:
            task_result = 'ERROR'
            exception = str(e)
        Logger().sdebug('within_day_task end')

        total_latency = Time.timestamp_ms() - start_time

        TBG.tb_metrics.write(
            "CRAWLER.MANAGER",
            tags=dict(
                task='CWR_WITHINDAY_TASK',
                task_result=task_result,
                exception=exception

            ),
            fields=dict(
                total_latency=total_latency,
                count=1
            ))

    @logger_config('CWR_PR_TASK')
    def pr_task(self, pr):
        """
        根据权重触发不同的task
        :param pr:
        :return:
        """
        tb_pub = TbPublisher(transport='socket')
        exception = ''
        start_time = Time.timestamp_ms()
        Logger().sdebug('pr_task %s Start' % pr)
        try:

            with db_session:
                select_secondary_start = time.time()
                task_list = select(o for o in SecondaryFareCrawlTask if o.pr == pr and o.task_status == 'RUNNING' and o.from_date >= datetime.date.today())
                select_secondary_end = time.time()
                Logger().info('{} pr {} selected. use time {}s'.format(pr, len(task_list),
                                                                       select_secondary_end - select_secondary_start))
                async_task_load_start = time.time()
                for task in task_list:
                    # 仅执行pr=2,pr=3,pr=4,pr=5的爬取
                    # frs = select(i for i in FlightRepo if i.from_airport == task.from_airport and i.to_airport == task.to_airport and i.pr in [2, 3, 4, 5])
                    # if not frs:
                    #     continue
                    try:
                        curr_date = datetime.date.today()
                        if (task.from_date - curr_date).days >= task.start_day:
                            search_info = SearchInfo()
                            search_info.provider = task.provider
                            search_info.provider_channel = task.provider_channel
                            search_info.from_date = task.from_date.strftime('%Y-%m-%d')
                            search_info.from_airport = task.from_airport
                            search_info.to_airport = task.to_airport
                            search_info.adt_count = 1
                            search_info.chd_count = 0
                            search_info.inf_count = 0
                            search_info.trip_type = task.trip_type
                            # 自定义数据 SecondaryFareCrawlTask id 传递过去
                            search_info.task_id = task.id
                            search_info.pr = pr
                            search_info.crawl_primary_task_id = task.primary_task_id.id
                            if task.primary_task_id.ota_custom_route_strategy:
                                search_info.ota_custom_route_strategy = json.loads(task.primary_task_id.ota_custom_route_strategy)
                            # Logger().debug('search_info %s' % search_info)
                            dedup_hash = task.dl_hash
                            Logger().sdebug('dedup_hash %s' % dedup_hash)
                            if task.task_type == 'ROUTING_CACHE':
                                routing_key = 'flight_crawl_task'
                            elif task.task_type == 'FARE_COMPARISON':
                                routing_key = 'fare_comparison_task'
                            else:
                                routing_key = 'dynamic_fare_task'
                            Logger().sdebug('routing_key %s' % routing_key)
                            tb_pub.send(body=search_info, routing_key=routing_key, dedup_hash=dedup_hash, ttl=TBG.global_config['CRAWLER_TASK_EXPIRE_TIME'])
                            Logger().sdebug('task %s dilivered ' % task.id)
                        else:
                            Logger().sdebug('not in allow day range %s' % task.id)
                    except Exception as e:
                        Logger().serror(e)
                async_task_load_end = time.time()
                Logger().info('task {} loaded. use time {}s'.format(pr, async_task_load_end - async_task_load_start))
            task_result = 'SUCCESS'
        except Exception as e:
            task_result = 'ERROR'
            exception = str(e)
        tb_pub.close()
        Logger().sdebug('pr_task %s end' % pr)

        total_latency = Time.timestamp_ms() - start_time

        TBG.tb_metrics.write(
            "CRAWLER.MANAGER",
            tags=dict(
                task='CWR_PR_TASK_%s' % pr,
                task_result=task_result,
                exception=exception

            ),
            fields=dict(
                total_latency=total_latency,
                count=1
            ))

    @logger_config('CWR_TASK_CONTROL')
    def task_controller(self):
        exception = ''
        start_time = Time.timestamp_ms()
        try:
            with db_session:
                Logger().sdebug('Crawler Controller Loop Start')
                crawl_airlines = select(o for o in FlightRepo if o.is_crawl == 1)
                # flight_segments = select(o for o in FlightRepo if o.pr in [4, 5])
                task_list = select(o for o in PrimaryFareCrawlTask if o.task_status in ['RUNNING', 'TODO', 'TOSTOP', 'TODELETE','TORESUME'])
                for task in task_list:
                    Logger().sdebug('Task id %s loaded' % task.id)
                    if task.task_status in ['TODO','TORESUME']:

                        if task.task_status == 'TORESUME':
                            # 删除所有子任务，然后重新创建
                            TBG.tourbillon_extra_db.execute('delete from secondary_fare_crawl_task where primary_task_id = %s ' % (task.id))
                            Logger().sdebug('RESUME task %s' % task.id)
                        # 启动任务
                        c_day = Time.curr_date_obj()
                        crawl_day_lists = []
                        for i in xrange(task.start_day, task.within_days + 1):
                            if i == 0:
                                crawl_day_lists.append([c_day + datetime.timedelta(days=i), 5])
                            elif i <= 7:
                                crawl_day_lists.append([c_day + datetime.timedelta(days=i), 4])
                            elif 7 < i <= 30:
                                crawl_day_lists.append([c_day + datetime.timedelta(days=i), 3])
                            elif 30 < i <= 60:
                                crawl_day_lists.append([c_day + datetime.timedelta(days=i), 2])
                            else:
                                crawl_day_lists.append([c_day + datetime.timedelta(days=i), 1])

                        if task.task_type in ['DYNAMIC_FARE','FARE_COMPARISON']:
                            crawl_airlines = json.loads(task.crawl_airlines)
                        for fs in crawl_airlines:

                            if task.task_type  == 'DYNAMIC_FARE':
                                # 动态运价
                                pr = 6  # TODO 暂时固定为PR 6
                                from_airport = fs[0]
                                to_airport = fs[1]
                            elif task.task_type  ==  'FARE_COMPARISON':
                                # 比价
                                pr = 7  # TODO 暂时固定为PR 7
                                from_airport = fs[0]
                                to_airport = fs[1]
                            else:
                                # 路由缓存
                                from_airport = fs.from_airport
                                to_airport = fs.to_airport
                                pr = fs.pr

                            for crawl_day, pr_min in crawl_day_lists:
                                if pr < pr_min:  # 根据时间接近度修正PR
                                    Logger().sdebug('pr%s %s' % (pr, pr_min))
                                    set_pr = pr_min
                                else:
                                    set_pr = pr

                                for p in json.loads(task.providers):
                                    provider = p[0]
                                    provider_channel = p[1]

                                    # TODO 临时在以下两种类型的任务添加 TASKID ，保证新的任务虽然航段重复但是依然可以爬取到
                                    if task.task_type in ['DYNAMIC_FARE','FARE_COMPARISON']:
                                        dl_hash = '%s%s%s%s%s%s%s' % (provider_channel, from_airport, to_airport, crawl_day.strftime('%Y-%m-%d'), task.trip_type, task.task_type,task.id)
                                    else:
                                        dl_hash = '%s%s%s%s%s%s' % (provider_channel, from_airport, to_airport, crawl_day.strftime('%Y-%m-%d'), task.trip_type, task.task_type)

                                    Logger().sinfo('dl_hash %s added PR %s' % (dl_hash, set_pr))
                                    try:
                                        exist_dl_hash = select(o for o in SecondaryFareCrawlTask if o.dl_hash == dl_hash)
                                        if not exist_dl_hash:
                                            sfct = SecondaryFareCrawlTask(provider=provider, provider_channel=provider_channel, pr=set_pr, from_date=crawl_day.strftime('%Y-%m-%d'),
                                                                          from_airport=from_airport, to_airport=to_airport, task_status='RUNNING',
                                                                          dl_hash=dl_hash, trip_type=task.trip_type, primary_task_id=task, task_type=task.task_type,start_day=task.start_day)

                                    except Exception as e:
                                        # 如果插入重复会报错
                                        Logger().sdebug(e)

                                    if task.task_type == 'FARE_COMPARISON':  # 如果是比价则选择一个供应商即可
                                        break
                        task.task_status = 'RUNNING'
                        commit()


                    elif task.task_status == 'TOSTOP':
                        TBG.tourbillon_extra_db.execute('update secondary_fare_crawl_task set task_status="STOP" where primary_task_id = %s ' % (task.id))
                        task.task_status = 'STOP'
                        Logger().sdebug('stopping task %s' % task.id)



                    elif task.task_status == 'TODELETE':
                        PrimaryFareCrawlTask[task.id].delete()
                        Logger().sdebug('delete task %s' % task.id)

            task_result = 'SUCCESS'
        except Exception as e:
            task_result = 'ERROR'
            exception = str(e)
            Logger().serror('Crawler Controller Loop Error')
        Logger().sdebug('Crawler Controller Loop End')

        total_latency = Time.timestamp_ms() - start_time

        TBG.tb_metrics.write(
            "CRAWLER.MANAGER",
            tags=dict(
                task='CWR_TASK_CONTROL',
                task_result=task_result,
                exception=exception

            ),
            fields=dict(
                total_latency=total_latency,
                count=1
            ))

    @logger_config('SCHED_AIRLINE_SAMPLING_REVISE', True)
    @db_session
    def scheduled_airline_sampling_revise(self):
        """
        定期从metric中抽取大流量的查询产生实际查询并修正

        """
        tb_pub = TbPublisher(transport='socket')
        exception = ''
        start_time = Time.timestamp_ms()
        try:
            from influxdb import InfluxDBClient
            client = InfluxDBClient(TBG.global_config['METRICS_SETTINGS']['host'], TBG.global_config['METRICS_SETTINGS']['port'], TBG.global_config['METRICS_SETTINGS']['user'],
                                    TBG.global_config['METRICS_SETTINGS']['password'], TBG.global_config['METRICS_SETTINGS']['db'])

            result = client.query(
                'SELECT sum("total_count") FROM "search_3h"."PD_ASYNC_SEARCH" WHERE ("return_status" = \'NO_SCHEDULED_AIRLINE\') AND time >= now() - 5m GROUP BY "from_to_airport","provider_channel" fill(null) ')
            no_sched_airline_list = set([])
            point_count = []
            raw_count = 0
            for point in result.raw.get('series', []):
                point_count.append(point['values'][0][1])
                count = point['values'][0][1]
                raw_count +=1
                if count > 5 and point['tags']['from_to_airport'] and point['tags']['provider_channel']:
                    __ = point['tags']['from_to_airport']
                    from_airport = __.split('-')[0][:3]
                    to_airport = __.split('-')[1][:3]
                    provider_channel = point['tags']['provider_channel']
                    no_sched_airline_list.add('%s|%s|%s' % (provider_channel, from_airport, to_airport))

            Logger().sinfo('no_sched_airline_list before %s length %s' % (raw_count,len(no_sched_airline_list)))
            error_count = 0
            total_count = 0
            today_str = Time.date_str_2()
            # no_sched_airline_list = ['%s|%s|%s' % ('ceair_web_2', 'HGH', 'AMS')]
            for record in no_sched_airline_list:
                provider_channel, from_airport, to_airport = record.split('|')

                res = select(s for s in ScheduledAirlineRepo if s.provider_channel == provider_channel and s.from_airport == from_airport and s.to_airport == to_airport)
                is_sched_airline = False
                for x in res:
                    is_sched_airline = True
                    break
                if not is_sched_airline:
                    total_count += 1

                    provider_app = ProviderAutoRepo.select(provider_channel)
                    search_info = SearchInfo()
                    search_info.from_airport = from_airport
                    search_info.to_airport = to_airport
                    search_info.from_date = today_str
                    search_info.trip_type = 'OW'
                    search_info.adt_count = 1
                    search_info.chd_count = 0
                    search_info.attr_competion()
                    search_info.provider_channel = provider_channel
                    # 发送至queue
                    routing_key = 'scheduled_airline_crawl_task'

                    dedup_hash = '{from_airport}|{to_airport}|{provider_channel}'.format(
                        from_airport=search_info.from_airport,
                        to_airport=search_info.to_airport,
                        provider_channel=provider_channel
                    )
                    tb_pub.send(body=search_info, routing_key=routing_key, dedup_hash=dedup_hash)

                else:
                    pass
                    # Logger().sinfo('is sched airline continue')

            Logger().sinfo('total_count %s error_count %s' % (total_count, error_count))

            task_result = 'SUCCESS'
        except Exception as e:
            Logger().serror(e)
            exception = str(e)
            task_result = 'ERROR'

        tb_pub.close()
        total_latency = Time.timestamp_ms() - start_time

        TBG.tb_metrics.write(
            "CRAWLER.MANAGER",
            tags=dict(
                task='SCHEDULED_AIRLINE_SAMPLING_REVISE',
                task_result=task_result,
                exception=exception

            ),
            fields=dict(
                total_latency=total_latency,
                count=1
            ))


# ----------------------TASKSET--------------------------------


@logger_config('CWR_FLIGHT_CRAWL_WORKER')
@db_session
def flight_crawl_task(search_info):
    """
    航班爬取
    :param search_info:
    :return:
    """
    start_time = Time.timestamp_ms()
    TB_PROVIDER_CHANNEL = search_info['provider_channel']

    exception = ''
    try:
        # Logger().info('flight_crawl_task start %s' % search_info)
        search_info = SearchInfo(**search_info)
        provider_app = ProviderAutoRepo.select(search_info.provider_channel)
        search_info.attr_competion()
        search_info_with_result = provider_app.flight_crawl(search_info=search_info,is_only_search_scheduled_airline=1)

        # 新增日航线库存储
        # Logger().debug('search_info_with_result %s' % search_info_with_result)
        if search_info_with_result.assoc_search_routings:
            fcrd = FareCrawlRepoDL()
            fcrd.task_id = search_info_with_result.task_id
            fcrd.provider = search_info_with_result.provider
            fcrd.provider_channel = search_info_with_result.provider_channel
            fcrd.from_date = search_info_with_result.from_date
            fcrd.from_airport = search_info_with_result.from_airport
            fcrd.to_airport = search_info_with_result.to_airport
            fcrd.from_city = convert_unicode(search_info_with_result.from_city)
            fcrd.from_country = convert_unicode(search_info_with_result.from_country)
            fcrd.to_city = convert_unicode(search_info_with_result.to_city)
            fcrd.to_country = convert_unicode(search_info_with_result.to_country)
            fcrd.routing_range = search_info_with_result.routing_range
            fcrd.trip_type = search_info_with_result.trip_type
            fcrd.pr = search_info_with_result.pr
            cabin_count_total = 0
            flightcount_total = 0
            flightcount_cabin_a = 0
            flightcount_cabin_1_8 = 0
            price_list = []
            for routing in search_info_with_result.assoc_search_routings:
                # 存储至数据库
                cabin_count_total += routing.from_segments[0].cabin_count
                flightcount_total += 1
                if routing.from_segments[0].cabin_count >= 9:
                    flightcount_cabin_a += 1
                elif 1 <= routing.from_segments[0].cabin_count <= 8:
                    flightcount_cabin_1_8 += 1

                price_list.append(routing.adult_price)

            fcrd.lowest_price = min(price_list)
            fcrd.cabin_count_total = cabin_count_total
            fcrd.flightcount_cabin_1_8 = flightcount_cabin_1_8
            fcrd.flightcount_cabin_a = flightcount_cabin_a
            fcrd.flightcount_total = flightcount_total
            commit()

    except (FlightSearchException, FlightSearchCritical) as e:
        exception = str(e)
    except Exception as e:
        Logger().serror(e)
        exception = str(e)

    total_latency = Time.timestamp_ms() - start_time
    if exception == '':
        success_count = 1
    else:
        success_count = 0

    TBG.tb_metrics.write(
        "CRAWLER.FLIGHT_CRAWL_WORKER",
        tags=dict(
            return_status=search_info_with_result.return_status,
            from_airport=search_info_with_result.from_airport,
            to_airport=search_info_with_result.to_airport,
            from_date=search_info_with_result.from_date,
            provider_channel=search_info_with_result.provider_channel,
            #    from_city=search_info_with_result.from_city,
            # to_city=search_info_with_result.to_city,
            from_country=search_info_with_result.from_country,
            to_country=search_info_with_result.to_country,
            pr=search_info_with_result.pr,
            exception=exception
        ),
        fields=dict(
            total_latency=total_latency,
            total_count=1,
            success_count=success_count,
            return_flight_count=len(search_info_with_result.assoc_search_routings)
        ))


@logger_config('CWR_SCHED_AIRLINE_REVISE_WORKER')
@db_session
def flight_ota_fare_task(search_info):
    """
    航线库抽样修正爬虫
    :param search_info:
    :return:
    """

    start_time = Time.timestamp_ms()
    TB_PROVIDER_CHANNEL = search_info['provider_channel']

    exception = ''
    try:
        # Logger().info('flight_ota_fare_task start %s' % search_info)
        search_info = SearchInfo(**search_info)
        provider_app = ProviderAutoRepo.select(search_info.provider_channel)
        search_info.attr_competion()
        search_info_with_result = provider_app.async_search(search_info=search_info,cache_mode='MIX',allow_expired=True,custom_expired_time=20,is_only_search_scheduled_airline=1)  # 10秒内则不再进行查询

    except (FlightSearchException, FlightSearchCritical) as e:
        exception = str(e)
    except Exception as e:
        Logger().serror(e)
        exception = str(e)

@logger_config('CWR_SCHED_AIRLINE_CRAWL_WORKER')
@db_session
def scheduled_airline_crawl_task(search_dict):
    """
    航班爬取
    :param search_info:
    :return:
    """

    start_time = Time.timestamp_ms()
    TB_PROVIDER_CHANNEL = search_dict['provider_channel']
    TB_REQUEST_ID = Random.gen_request_id()
    exception = ''
    try:
        # Logger().info('flight_ota_fare_task start %s' % search_info)
        # with db_session:
        #     res = select(s for s in ScheduledAirlineRepo if s.provider_channel == search_dict['provider_channel'] and s.from_airport == search_dict['from_airport'] and s.to_airport == search_dict['to_airport'])
        #     is_sched_airline = False
        #     for x in res:
        #         is_sched_airline = True
        #         break

        from_date_list = []  # 搜索天数  2天  10天  30天
        from_date = Time.days_after(2)
        from_date = from_date.strftime('%Y-%m-%d')
        from_date_list.append(from_date)
        from_date = Time.days_after(10)
        from_date = from_date.strftime('%Y-%m-%d')
        from_date_list.append(from_date)
        from_date = Time.days_after(30)
        from_date = from_date.strftime('%Y-%m-%d')
        from_date_list.append(from_date)

        for from_date in from_date_list:
            search_info = SearchInfo(**search_dict)
            search_info.from_date = from_date
            search_info.attr_competion()

            provider_app = ProviderAutoRepo.select(search_info.provider_channel)
            provider_app.sched_airline_search(search_info=search_info, cache_mode='MIX', allow_expired=False)  # 仅搜索缓存中的数据，不允许过期
            Logger().sinfo('%s-%s assoc_search_routings length  %s return_status %s' %(search_info.from_airport,search_info.to_airport, len(search_info.assoc_search_routings),search_info.return_status))
            # Logger().sinfo('from_airport %s to_airport %s provider_channel %s from_date %s return_status %s' % (from_airport,to_airport,provider_channel,from_date,search_info.return_status))
            if search_info.assoc_search_routings:  # 认为有数据
                carrier = search_info.assoc_search_routings[0].from_segments[0]['carrier']  # 抽取第一个routing并根据其carrier 决定这个数据应该录入到哪个航线库（航线库是根据carrier区分）
                cache_key = "scheduled_airline_cache_%s" % carrier
                # 获取原始数据

                my_lock = TBG.redis_conn.redis_pool.lock('lock_%s' % cache_key, timeout=300)
                have_lock = False
                try:
                    Logger().sinfo('ready to get Lock')
                    have_lock = my_lock.acquire(blocking=True)
                    if have_lock:
                        raw_data = TBG.redis_conn.redis_pool.get(cache_key)
                        if raw_data:
                            # 基于原有数据进行更新，append模式，不会进行任何航线的删除操作，该模式后期会产生一定的准确误差，可以接受
                            raw_airline_list = json.loads(raw_data)
                            Logger().sinfo('raw_data length %s' % len(raw_airline_list))
                            raw_airline_list.append('%s-%s' % (search_info.from_airport, search_info.to_airport))
                            save_list = list(set(raw_airline_list))
                            Logger().sinfo('to save  length %s' % len(save_list))
                            TBG.redis_conn.redis_pool.set(cache_key, json.dumps(save_list))
                            ScheduledAirlineRepo(from_airport=search_info.from_airport, to_airport=search_info.to_airport, provider_channel=search_info.provider_channel)
                            commit()
                        else:
                            pass  # 如果没有基础数据，则不会进行录入，防止数据库中只包含零星数据导致航线库错误率暴增
                            Logger().sinfo('no cache so discard！！！！')
                    else:
                        Logger().sinfo('locked_hash %s ' % cache_key)
                except Exception as e:
                    Logger().error(e)
                finally:
                    if have_lock:
                        try:
                            my_lock.release()
                        except Exception as e:
                            pass


                Logger().sinfo(
                    '【REVISE DATA】from_airport %s to_airport %s provider_channel %s from_date %s return_status %s' % (search_info.from_airport, search_info.to_airport, search_info.provider_channel, from_date, search_info.return_status))
                break

    except (FlightSearchException, FlightSearchCritical) as e:
        Logger().serror(e)
    except Exception as e:
        Logger().serror(e)
        exception = str(e)

@logger_config('CWR_DYNAMIC_FARE_WORKER')
@db_session
def dynamic_fare_task(search_info):
    """
    航班爬取
    :param search_info:
    :return:
    """

    start_time = Time.timestamp_ms()
    TB_PROVIDER_CHANNEL = search_info['provider_channel']
    pfct_id = search_info['crawl_primary_task_id']
    TB_ORDER_ID = pfct_id
    pfct_info = PrimaryFareCrawlTask.get(id=pfct_id)
    dynamic_fare_search_result = 'NOFLIGHT'

    exception = ''
    try:
        Logger().info('start')
        fare_ota_search_info = SearchInfo(**search_info)  # 所要运价的OTAInfo
        fare_ota_search_info.attr_competion()
        fare_ota_app = ProviderAutoRepo.select(fare_ota_search_info.provider_channel)
        try:
            self_search_info = SearchInfo(**search_info)  # 自有价格info
            self_search_info.attr_competion()
            self_ota_app = OTARepo.select(pfct_info.ota)
            self_ota_app.search_info = self_search_info
            router = Router(self_ota_app, search_mode='sync_call', route_strategy=self_search_info.ota_custom_route_strategy,is_allow_cabin_revise=False,is_allow_fusing=False,is_allow_max_pax_count_limit=False,is_allow_min_cabin_count_limit=False)
            router.run()

        except Exception as e:
            Logger().error(e)

        try:
            # 初始化OTA，挂载路由
            fare_ota_app.flight_crawl(search_info=fare_ota_search_info, cache_mode='MIX', allow_expired=True,custom_expired_time=120)

        except Exception as e:
            Logger().error(e)

        fare_set = {}

        # 查询自己的ota接口
        for srouting in self_search_info.assoc_search_routings:

            rk_dict = RoutingKey.unserialize(srouting.routing_key_detail)
            rk_dict['dep_time'] = 'N/A'
            rk_dict['arr_time'] = 'N/A'
            # Logger().debug('srouting.............%s' % srouting)
            # Logger().debug('srouting.rk_dict............%s' % rk_dict)

            # 不包含舱位 则对比航班最低价
            key = RoutingKey.trans_cc_key(rk_dict, is_unserialized=True)

            rk_dict['cost_price'] = rk_dict['adult_price'] + rk_dict['adult_tax']
            rk_dict['offer_price'] = rk_dict['adult_price_forsale'] + rk_dict['adult_tax']
            rk_dict['ota_r1_price'] = 0
            rk_dict['ota_r2_price'] = 0
            if key not in fare_set:
                fare_set[key] = rk_dict
            else:
                if fare_set[key]['offer_price'] > rk_dict['offer_price']:
                    # 只存储最低售价
                    fare_set[key] = rk_dict

        if fare_ota_search_info.assoc_search_routings:
            dynamic_fare_search_result = 'EXISTFLIGHT'
        if 'ERROR' in fare_ota_search_info.return_status:
            dynamic_fare_search_result = fare_ota_search_info.return_status

        # 查询OTA 低价看板或者C端
        for frouting in fare_ota_search_info.assoc_search_routings:

            rk_dict = RoutingKey.unserialize(frouting.routing_key_detail)
            rk_dict['dep_time'] = 'N/A'
            rk_dict['arr_time'] = 'N/A'
            # Logger().debug('frouting.............%s' % frouting)
            # Logger().debug('frouting.rk_dict............%s' % rk_dict)

            # 不包含舱位 则对比航班最低价
            key = RoutingKey.trans_cc_key(rk_dict, is_unserialized=True)

            if key not in fare_set:
                # 补充完整数据
                rk_dict['cost_price'] = 0
                rk_dict['offer_price'] = 0
                rk_dict['ota_r1_price'] = rk_dict['adult_price'] + rk_dict['adult_tax']
                rk_dict['ota_r2_price'] = frouting.reference_adult_price + frouting.reference_adult_tax
                rk_dict['provider'] = ''
                rk_dict['provider_channel'] = ''
                rk_dict['fare_put_mode'] = ''

                fare_set[key] = rk_dict
            else:
                # 补充参考价
                # Logger().info('before same key !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!1 %s %s' % (key,fare_set[key]['ota_r1_price']))
                if fare_set[key]['ota_r1_price']:
                    # 如果存在价格对比是否为最低价，补充最低价
                    if fare_set[key]['ota_r1_price'] > rk_dict['adult_price'] + rk_dict['adult_tax']:
                        fare_set[key]['ota_r1_price'] = rk_dict['adult_price'] + rk_dict['adult_tax']
                        fare_set[key]['ota_r2_price'] = frouting.reference_adult_price + frouting.reference_adult_tax
                else:
                    # Logger().info('xxx xxx xx no price  same key  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!1 %s %s' % (key, fare_set[key]))
                    fare_set[key]['ota_r1_price'] = rk_dict['adult_price'] + rk_dict['adult_tax']
                    fare_set[key]['ota_r2_price'] = frouting.reference_adult_price + frouting.reference_adult_tax

                # Logger().info('after same key !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!1 %s in key r1 price %s rk_dict price %s' % (key, fare_set[key]['ota_r1_price'],rk_dict['adult_price'] + rk_dict['adult_tax']))

        # Logger().info('self_search_info.assoc_search_routings %s fare_ota_search_info.assoc_search_routings %s' % (self_search_info.assoc_search_routings,fare_ota_search_info.assoc_search_routings))
        Logger().sinfo('fare_set length %s self_search_info %s length %s fare_ota_search_info  %s length %s' % (len(fare_set),pfct_info.ota,len(self_search_info.assoc_search_routings),fare_ota_search_info.provider_channel,len(fare_ota_search_info.assoc_search_routings)))
        for key, fare_data in fare_set.items():

            hash = '%s_%s_%s_%s_%s' % (pfct_id, key, fare_data['from_date'],fare_data['ret_date'],fare_data['trip_type'])
            dfp = DynamicFareRepo.get(hash=hash)
            if dfp:
                # 如果运价库存在数据，则更新价格数据

                # Logger().info('has dfp %s' % dfp)
                if dfp.cost_price and dfp.ota_r1_price and not fare_data['ota_r1_price']:  # 如果历史数据中包含完整数据，新数据没有完整数据，则暂不对其记录进行更新
                    continue

                if dfp.cost_price != fare_data['cost_price'] or dfp.offer_price != fare_data['offer_price'] or dfp.ota_r1_price != fare_data['ota_r1_price'] or dfp.ota_r2_price != fare_data[
                    'ota_r2_price'] or dfp.provider != fare_data['provider']:

                    Logger().sinfo('dfp id %s to fare_data cost_price %s %s offer_price %s %s ota_r1_price %s %s ota_r2_price %s %s provider %s %s ' %(dfp.id,dfp.cost_price,fare_data['cost_price'],dfp.offer_price,fare_data['offer_price'],dfp.ota_r1_price,fare_data['ota_r1_price'],dfp.ota_r2_price,
                                     fare_data['ota_r2_price'],dfp.provider,fare_data['provider']                                                                                                           ))
                    dfp.ver = dfp.ver + 1
                dfp.cost_price = fare_data['cost_price']
                dfp.offer_price = fare_data['offer_price']
                dfp.ota_r1_price = fare_data['ota_r1_price']
                dfp.ota_r2_price = fare_data['ota_r2_price']
                dfp.provider = fare_data['provider']
                dfp.provider_channel = fare_data['provider_channel']
                dfp.fare_put_mode = fare_data['fare_put_mode']
                dfp.source = 'CRAWLER_UPDATE'


            else:
                # TODO 包含r1则会入库
                # Logger().info('insert cost %s r1 %s ' %(fare_data['cost_price'],fare_data['ota_r1_price']))
                if fare_data['ota_r1_price']:
                    DynamicFareRepo(
                        from_airport=fare_data['from_airport'],
                        to_airport=fare_data['to_airport'],
                        flight_number=fare_data['flight_number'],
                        cabin=fare_data['cabin'],
                        cabin_grade=fare_data['cabin_grade'],
                        from_date=fare_data['from_date'],
                        cost_price=fare_data['cost_price'],
                        provider=fare_data['provider'],
                        provider_channel=fare_data['provider_channel'],
                        offer_price=fare_data['offer_price'],
                        ota_r1_price=fare_data['ota_r1_price'],
                        ota_r2_price=fare_data['ota_r2_price'],
                        ret_date=fare_data['ret_date'] if fare_data['ret_date'] else None,
                        trip_type=fare_data['trip_type'],
                        fare_put_mode='AUTO_BOOST',  # 此状态标识可能会运价
                        hash=hash,
                        primary_fare_crawl_task=pfct_id,
                        source='CRAWLER_CREATE'
                    )

    except Exception as e:
        Logger().serror(e)
        exception = str(e)
        dynamic_fare_search_result = 'ERROR'

    total_latency = Time.timestamp_ms() - start_time
    if exception == '':
        success_count = 1
    else:
        success_count = 0

    TBG.tb_metrics.write(
        "CRAWLER.DYNAMIC_FARE_WORKER",
        tags=dict(
            flight_crawl_result=dynamic_fare_search_result,
            pfct_id=pfct_id
        ),
        fields=dict(
            total_latency=total_latency,
            total_count=1,
            success_count=success_count,
        ))


@logger_config('CWR_FARE_COMPARISON_WORKER')
@db_session
def fare_comparison_task(search_info):
    """
    航班爬取
    :param search_info:
    :return:
    """
    TB_REQUEST_ID = Random.gen_request_id()
    TB_SUB_ORDER_ID = search_info['from_date']
    start_time = Time.timestamp_ms()
    fare_comparison_search_result = 'SUCCESS'

    exception = ''
    try:
        # Logger().info('flight_crawl_task start %s' % search_info)

        pfct_id = search_info['crawl_primary_task_id']
        pfct_info = PrimaryFareCrawlTask.get(id=pfct_id)
        providers = json.loads(pfct_info.providers)

        fare_set_total_dict = {}
        to_save_cc_key_list = None

        for provider_item in providers:
            psearch_info = SearchInfo(**search_info)  # 所要运价的OTAInfo
            psearch_info.attr_competion()
            provider = provider_item[0]
            provider_channel = provider_item[1]
            TB_PROVIDER_CHANNEL = provider_channel
            provider_app = ProviderAutoRepo.select(provider_channel)

            provider_app.flight_crawl(search_info=psearch_info,cache_mode='MIX',allow_expired=True)
            fare_set = {}
            for srouting in psearch_info.assoc_search_routings:

                rk_dict = RoutingKey.unserialize(srouting.routing_key_detail)
                rk_dict['dep_time'] = 'N/A'
                rk_dict['arr_time'] = 'N/A'
                # Logger().debug('srouting.............%s' % srouting)
                # Logger().debug('srouting.rk_dict............%s' % rk_dict)
                # 不包含舱位 则对比航班最低价
                key = RoutingKey.trans_cc_key(rk_dict, is_unserialized=True)
                rk_dict['cost_price'] = rk_dict['adult_price'] + rk_dict['adult_tax']
                if key not in fare_set:
                    fare_set[key] = rk_dict
                else:
                    if fare_set[key]['cost_price'] > rk_dict['cost_price']:
                        # 只存储最低售价
                        fare_set[key] = rk_dict

            Logger().info('fare_set length %s' % len(fare_set))
            Logger().info(' provider_channel %s fare_set %s' % (provider_channel,fare_set.keys()))

            # 将KEY放入set，用于算出多个供应商的交集，只有交集会入库
            if to_save_cc_key_list is None:
                to_save_cc_key_list = set(fare_set.keys())
            else:
                to_save_cc_key_list.intersection_update(fare_set.keys())


            fare_set_total_dict["%s|%s" % (provider, provider_channel)] = fare_set


        Logger().info('------------------- to_save_cc_key_list %s ' % (to_save_cc_key_list))
        for ts_cc_key in to_save_cc_key_list:
            cc_key_dict = RoutingKey.unserialize_cc_key(ts_cc_key)
            fc_hash = '%s_%s_%s' % (pfct_id, ts_cc_key, search_info['from_date'])
            Logger().info('main loop ts_cc_key %s ' % (ts_cc_key))
            fcr = FareComparisonRepo.get(hash=fc_hash)
            if fcr:
                # 如果库中存在主条目，那么默认认为也会存在所有需要对比的供应商子条目
                is_need_to_update_ver = False
                for pfcr in fcr.provider_fc_repo:
                    rk_dict = fare_set_total_dict.get("%s|%s" % (pfcr.provider, pfcr.provider_channel), {}).get(ts_cc_key, {})
                    Logger().debug('exists fcr ts_cc_key %s rk_dict%s' % (ts_cc_key, rk_dict))
                    if rk_dict:
                        # 该供应商存在价格

                        if pfcr.cost_price != rk_dict['cost_price']:
                            # 价格不相等需要更新
                            is_need_to_update_ver = True
                            pfcr.cost_price = rk_dict['cost_price']

                        if pfcr.cabin != rk_dict['cabin']:
                            # 舱位不相等需要更新，最低价有可能舱位有变化
                            is_need_to_update_ver = True
                            pfcr.cabin = rk_dict['cabin']

                if is_need_to_update_ver:
                    fcr.ver += 1

            else:

                new_fcr = FareComparisonRepo(
                    primary_fare_crawl_task=pfct_id,
                    from_airport=cc_key_dict['from_airport'],
                    to_airport=cc_key_dict['to_airport'],
                    flight_number=cc_key_dict['flight_number'],
                    cabin_grade=cc_key_dict['cabin_grade'],
                    from_date=search_info['from_date'],
                    hash=fc_hash,
                    ver=1
                )

                for provider_str, fare_set in fare_set_total_dict.items():
                    provider, provider_channel = provider_str.split('|')
                    TB_PROVIDER_CHANNEL = provider_channel
                    rk_dict = fare_set.get(ts_cc_key, {})
                    Logger().info(' ts_cc_key %s rk_dict%s' % (ts_cc_key,rk_dict))
                    if rk_dict:
                        # 存在数据
                        cabin = rk_dict['cabin']
                        cost_price = rk_dict['cost_price']
                    else:
                        # 不存在数据 也需要将供应商信息入库，cost_price 为0 舱位为空
                        cabin = ''
                        cost_price = 0
                        Logger().info('no rk_dict case %s' % (fare_set))

                    ProviderFCRepo(
                        fare_comparison_repo=new_fcr,
                        provider=provider,
                        provider_channel=provider_channel,
                        cabin=cabin,
                        from_date=search_info['from_date'],
                        cost_price=cost_price
                    )

    except Exception as e:
        Logger().serror(e)
        exception = str(e)
        fare_comparison_search_result = 'ERROR'

    total_latency = Time.timestamp_ms() - start_time
    if exception == '':
        success_count = 1
    else:
        success_count = 0

    TBG.tb_metrics.write(
        "CRAWLER.FARE_COMPARISON_WORKER",
        tags=dict(
            flight_crawl_result=fare_comparison_search_result
        ),
        fields=dict(
            total_latency=total_latency,
            total_count=1,
            success_count=success_count,
        ))



if __name__ == '__main__':
    pass
