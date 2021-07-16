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
import calendar
import gevent, datetime
import requests
from pony.orm import *
import pony.orm.core
from dateutil.relativedelta import relativedelta
from flask_script import Manager, Command, Option
from ..utils.exception import *
from ..utils.util import Time
from ..dao.models import *
from ..dao.iata_code import IATA_AIRPORT_TO_CITY,IATA_CODE
from ..dao.internal import *
from ..utils.logger import Logger
from app import TBG
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.schedulers.gevent import GeventScheduler
from ..automatic_repo.base import ProviderAutoRepo
from ..dao.redis_dao import RedisPool
from ..controller.pokeman import Pokeman
from ..controller.http_request import HttpRequest


class MiscController(Command):
    """
     year (int|str) – 4-digit year
     month (int|str) – month (1-12)
     day (int|str) – day of the (1-31)
     week (int|str) – ISO week (1-53)
     day_of_week (int|str) – number or name of weekday (0-6 or mon,tue,wed,thu,fri,sat,sun)
     hour (int|str) – hour (0-23)
     minute (int|str) – minute (0-59)
     second (int|str) – second (0-59)

     start_date (datetime|str) – earliest possible date/time to trigger on (inclusive)
     end_date (datetime|str) – latest possible date/time to trigger on (inclusive)
     timezone (datetime.tzinfo|str) – time zone to use for the date/time calculations (defaults to scheduler timezone)

     *    any    Fire on every value
     */a    any    Fire every a values, starting from the minimum
     a-b    any    Fire on any value within the a-b range (a must be smaller than b)
     a-b/c    any    Fire every c values within the a-b range
     xth y    day    Fire on the x -th occurrence of weekday y within the month
     last x    day    Fire on the last occurrence of weekday x within the month
     last    day    Fire on the last day within the month
     x,y,z    any    Fire on any matching expression; can combine any number of any of the above expressions
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
            gevent.sleep(6)
            Logger().sinfo('Task End %s' % task_exec)
        else:

            # 清除爬虫锁
            lock_task_list = TBG.redis_conn.redis_pool.keys('flight_crawl_task*')
            for lock_task_key in lock_task_list:
                TBG.redis_conn.redis_pool.expire(lock_task_key, 0)

            scheduler = BlockingScheduler()
            scheduler.add_job(self.extract_flight, 'cron', hour=14)  # 按照本地时区是八点运行
            # scheduler.add_job(self.reset_proxy_pool_b_geted_count_per_day, 'cron', hour=16)
            # scheduler.add_job(self.proxy_pool_b_geted_count_per_day, 'cron', hour=16)
            scheduler.add_job(self.get_proxy_ip_list_a, 'interval', seconds=1)
            # scheduler.add_job(self.get_proxy_ip_list_b, 'interval', seconds=55)
            scheduler.add_job(self.get_proxy_ip_list_c, 'interval', seconds=13*60)
            scheduler.add_job(self.get_proxy_ip_list_d, 'interval', seconds=2)
            scheduler.add_job(self.get_proxy_ip_list_f, 'interval', seconds=5*60)
            # scheduler.add_job(self.tb_report, 'cron', hour=0)  # 按照本地时区是八点运行
            scheduler.add_job(self.email_mobile_repo_sync, 'interval', seconds=600)
            scheduler.add_job(self.scheduled_airline_cache_sync,'cron', day='1,14,28')  # 每两周执行一次
            # scheduler.add_job(self.fusing_repo_monitor, 'interval', seconds=3600)

            # scheduler.add_job(self.tc_auto_verify_task, 'cron', hour=1)
            # scheduler.add_job(self.tc_auto_verify_task, 'cron', hour=3)
            # scheduler.add_job(self.tc_auto_verify_task, 'cron', hour=6)
            # scheduler.add_job(self.tc_auto_verify_task, 'cron', hour=9)
            # scheduler.add_job(self.tc_auto_verify_task, 'cron', hour=12)

            scheduler.start()
            # gevent.sleep(6)

    def tc_auto_verify_task(self):

        Logger().info('start to tc auto verify')
        for i in xrange(3):
            TBG.redis_conn.redis_pool.lpush('tc_auto_verify_trigger', 1)
        Logger().info('end tc auto verify')



    def scheduled_airline_cache_sync(self):
        """
        定时将db中的手机号码和邮箱同步到redis的list，进行轮询
        :return:

        POST /drx?_c=TTT HTTP/1.1
        Host: map.variflight.com
        Content-Length: 165
        Accept: application/json, text/javascript, */*; q=0.01
        Origin: http://map.variflight.com
        X-Requested-With: XMLHttpRequest
        User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36
        Content-Type: application/x-www-form-urlencoded; charset=UTF-8
        Referer: http://map.variflight.com/
        Accept-Encoding: gzip, deflate
        Accept-Language: en,zh-CN;q=0.9,zh;q=0.8
        Cookie: _ga=GA1.2.1960778503.1547453041; Hm_lvt_d1f759cd744b691c20c25f874cadc061=1551697178,1554188750; Hm_lpvt_d1f759cd744b691c20c25f874cadc061=1554188750; _gid=GA1.2.1764762544.1554188762;
         PHPSESSID=fs8voj6e8rhv4nqkk140d0dun5; Hm_lvt_2ad30bb2583cfacb7d56e2a6e1444d4b=1554189020,1554189852,1554192422; Hm_lpvt_2ad30bb2583cfacb7d56e2a6e1444d4b=1554192422
        Connection: close

        queryDate1=2019-06-04&queryDate2=2019-06-04&alliance=&dep=&depType=1&aircode=MU&arr=&arrType=1&isDirect=1&isStop=1&isOwn=1&isShare=1&isConnect=0&isNC=1&isCX=0&isC3=0

        空数据：{"code":0,"msg":"OK","data":[]}
        查询中 {"code":10,"msg":"\u7ee7\u7eed...","data":[]}
        """
        exception = ''
        start_time = Time.timestamp_ms()
        try:
            # 搜索所有供应商所包含的执飞航司列表
            carrier_list = []
            provider_channels = ProviderAutoRepo.list_all_provider_channels()
            for provider_channel in provider_channels:
                provider_app = ProviderAutoRepo.select(provider_channel)
                carrier_list.extend(provider_app.carrier_list)
            carrier_list = list(set(carrier_list))  # 去重

            # carrier_list = ['TR']
            Logger().sinfo('carrier_list %s' % carrier_list)
            # 生成从当月起四个月的数据，目前飞常准无法提供四个月外的数据

            today_obj = datetime.date.today()
            curr_date = today_obj
            year = curr_date.year
            month = curr_date.month
            end = calendar.monthrange(year, month)[1]
            start_date = '%s-%02d-01' % (year, month)
            end_date = '%s-%02d-%s' % (year, month, end)
            month_str = datetime.date.strftime(curr_date, '%Y-%m')

            # 准备请求信息
            url = "http://map.variflight.com/drx?_c=TTT"
            http_session = HttpRequest()
            http_session.update_cookie(cookie_dict={'PHPSESSID':'fs8voj6e8rhv4nqkk140d0dun5','_ga':'GA1.2.1960778503.1547453041','Hm_lvt_d1f759cd744b691c20c25f874cadc061':'1551697178,1554188750',
                                                    'Hm_lpvt_d1f759cd744b691c20c25f874cadc061':'1554188750','_gid':'GA1.2.1764762544.1554188762','Hm_lvt_2ad30bb2583cfacb7d56e2a6e1444d4b':'1554189020,1554189852,1554192422',
                                                    'Hm_lpvt_2ad30bb2583cfacb7d56e2a6e1444d4b':'1554192422'
                                                    })
            http_session.update_headers(headers={'X-Requested-With':'XMLHttpRequest','Origin':'http://map.variflight.com','User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36',
                                                 'Referer':'http://map.variflight.com/'})
            for carrier in carrier_list:
                cache_key = "scheduled_airline_cache_%s" % carrier
                Logger().sinfo('ready to update %s' % cache_key)
                data = {
                    'queryDate1':start_date,
                    'queryDate2': end_date,
                    'alliance': '',
                    'dep': '',
                    'depType': 1,
                    'aircode': carrier,
                    'arr': '',
                    'arrType': 1,
                    'isStop': 1,
                    'isOwn': 1,
                    'isShare': 1,
                    'isDirect': 1,
                    'isConnect': 0,
                    'isDomestic': 1,  # 境内
                    'isCross':1,  # 境外

                }
                Logger().sinfo('request data %s' % data)
                for x in range(0,30):
                    try:
                        result = http_session.request(url=url,method='POST',is_direct=True,data=data).to_json()
                        if result['code'] == 0:
                            if result['data']:
                                Logger().sinfo('cache_key %s date fetched length %s' %(cache_key, len(result['data'])))
                                airline_list = []
                                air1 = []
                                for item in result['data']:
                                    from_airport_list = [item[0]]
                                    to_airport_list = [item[1]]

                                    if item[0] in IATA_AIRPORT_TO_CITY:
                                        from_airport_list.append(IATA_AIRPORT_TO_CITY[item[0]])
                                    if item[0] in IATA_CODE:
                                        for airport in IATA_CODE[item[0]].get('airport_list',[]):
                                            from_airport_list.append(airport['code'])

                                    if item[1] in IATA_AIRPORT_TO_CITY:
                                        to_airport_list.append(IATA_AIRPORT_TO_CITY[item[1]])
                                    if item[1] in IATA_CODE:
                                        for airport in IATA_CODE[item[1]].get('airport_list',[]):
                                            to_airport_list.append(airport['code'])

                                    for from_airport in from_airport_list:
                                        for to_airport in to_airport_list:
                                            airline_str = "%s-%s" % (from_airport,to_airport)
                                            air1.append(airline_str)
                                air1 = list(set(air1))
                                Logger().sinfo('before join 2 length %s' % len(air1))
                                for airline in air1:
                                    airline_list.append(airline)
                                    # Logger().sdebug('11111111111111111airline %s' % airline)
                                    from_airport, to_airport = airline.split('-')
                                    for transit_1 in air1:  # 第一次中转航班拼接，由于数据调研发现二次中转航班的查询率极低，所以不会拼接两次中转

                                        t1_from_airport, t1_to_airport = transit_1.split('-')
                                        if to_airport == t1_from_airport and t1_to_airport != from_airport:
                                            # Logger().sdebug('transit_1 %s' % transit_1)
                                            if IATA_CODE.has_key(from_airport) and IATA_CODE.has_key(to_airport) and IATA_CODE.has_key(t1_to_airport):
                                                if IATA_CODE[from_airport]['cn_country'] != IATA_CODE[to_airport]['cn_country'] and IATA_CODE[from_airport]['cn_country'] == IATA_CODE[t1_to_airport][
                                                    'cn_country']:
                                                    # Logger().sdebug('continue')
                                                    continue

                                                new_airline = '%s-%s' % (from_airport, t1_to_airport)
                                                airline_list.append(new_airline)
                                Logger().sinfo('before compressed length %s' % len(airline_list))
                                result = list(set(airline_list))
                                Logger().sinfo('after length %s' % len(result))

                                # 获取原始数据
                                raw_data = TBG.redis_conn.redis_pool.get(cache_key)
                                if raw_data:
                                    # 基于原有数据进行更新，append模式，不会进行任何航线的删除操作，该模式后期会产生一定的准确误差，可以接受
                                    raw_airline_list = json.loads(raw_data)
                                    Logger().sinfo('raw_data length %s' % len(result))
                                    raw_airline_list.extend(airline_list)
                                    save_list = list(set(raw_airline_list))
                                    Logger().sinfo('to save  length %s' % len(save_list))
                                    TBG.redis_conn.redis_pool.set(cache_key, json.dumps(save_list))
                                else:
                                    TBG.redis_conn.redis_pool.set(cache_key,json.dumps(airline_list))
                            else:
                                Logger().sinfo('no data')
                            break
                        elif result['code'] == 10:
                            gevent.sleep(20)
                            Logger().sinfo('wait for data')
                    except Exception as e:
                        Logger().error(str(e))

                gevent.sleep(5)


            task_result = 'SUCCESS'
        except Exception as e:
            Logger().serror(e)
            exception = str(e)
            task_result = 'ERROR'

        total_latency = Time.timestamp_ms() - start_time

        TBG.tb_metrics.write(
            "MISCTASK",
            tags=dict(
                task='SCHEDULED_AIRLINE_CACHE_SYNC',
                task_result=task_result,
                exception=exception

            ),
            fields=dict(
                total_latency=total_latency,
                count=1
            ))

    @db_session
    def email_mobile_repo_sync(self):
        """
        定时将db中的手机号码和邮箱同步到redis的list，进行轮询
        :return:
        """
        exception = ''
        start_time = Time.timestamp_ms()
        try:
            # 手机

            res = select(s for s in MobileRepo if s.enable == 1)
            current_mobile_list = TBG.redis_conn.redis_pool.lrange('mobile_repo', 0, -1)
            db_list = ["%s|%s" % (m.mobile_num, m.sms_device_id) for m in res]
            Logger().sdebug('current_mobile_list %s db_list %s' % (current_mobile_list, db_list))
            add_list = set(db_list).difference(set(current_mobile_list))
            del_list = set(current_mobile_list).difference(set(db_list))
            for x in add_list:
                TBG.redis_conn.redis_pool.lpush('mobile_repo', x)
            for x in del_list:
                TBG.redis_conn.redis_pool.lrem('mobile_repo', 0, x)

            # 邮箱
            res = select(s for s in EmailRepo if s.enable == 1)
            current_email_list = TBG.redis_conn.redis_pool.lrange('email_repo', 0, -1)
            db_list = ["%s|%s|%s|%s|%s|%s" % (m.address, m.domain,m.user,m.password,m.pop3_server,m.email_type) for m in res]
            Logger().sdebug('current_email_list %s db_list %s' % (current_email_list, db_list))
            add_list = set(db_list).difference(set(current_email_list))
            del_list = set(current_email_list).difference(set(db_list))
            for x in add_list:
                TBG.redis_conn.redis_pool.lpush('email_repo', x)
            for x in del_list:
                TBG.redis_conn.redis_pool.lrem('email_repo', 0, x)

            task_result = 'SUCCESS'
        except Exception as e:
            Logger().serror(e)
            exception = str(e)
            task_result = 'ERROR'

        total_latency = Time.timestamp_ms() - start_time

        TBG.tb_metrics.write(
            "MISCTASK",
            tags=dict(
                task='MOBILE_REPO_SYNC',
                task_result=task_result,
                exception=exception

            ),
            fields=dict(
                total_latency=total_latency,
                count=1
            ))

    # @db_session
    # def tb_report(self):
    #     """
    #     报表
    #     {u'count': 857139, u'cache_count': 53768, u'success_count': 60331, u'enter_count': 264484, u'time': u'2018-09-03T16:00:00.000000001Z'}
    #     :return:
    #     """
    #     exception = ''
    #     start_time = Time.timestamp_ms()
    #     try:
    #         from influxdb import InfluxDBClient
    #         client = InfluxDBClient(TBG.global_config['METRICS_SETTINGS']['host'], TBG.global_config['METRICS_SETTINGS']['port'], TBG.global_config['METRICS_SETTINGS']['user'],
    #                                 TBG.global_config['METRICS_SETTINGS']['password'], TBG.global_config['METRICS_SETTINGS']['db'])
    #
    #         today = datetime.date.today()
    #         yesterday = today - datetime.timedelta(days=1)
    #         yesterday_start_time = int(time.mktime(time.strptime(str(yesterday), '%Y-%m-%d'))) * 1000
    #         yesterday_end_time = int(time.mktime(time.strptime(str(today), '%Y-%m-%d'))) * 1000 - 1
    #         Logger().sdebug('time_range %s %s' % (yesterday_start_time, yesterday_end_time))
    #
    #         # 搜索总数
    #         result = client.query(
    #             'SELECT sum(count) as count,sum(success_count) as success_count,sum(enter_count) as enter_count,sum(cache_count) as cache_count FROM "two_year"."OTA.SEARCH.AGGR" WHERE time > %sms and time < %sms ' % (
    #                 yesterday_start_time, yesterday_end_time))
    #         ota_search_total_count = 0
    #         ota_search_enter_count = 0
    #         ota_search_success_return_count = 0
    #         ota_search_cache_success_return_count = 0
    #         for point in result.get_points():
    #             ota_search_total_count += point['count']
    #             ota_search_success_return_count = point['success_count']
    #             ota_search_cache_success_return_count = point['cache_count']
    #             ota_search_enter_count = point['enter_count']
    #
    #         if ota_search_enter_count == 0:
    #             ota_search_enter_success_ratio = 0.0
    #         else:
    #             ota_search_enter_success_ratio = float(ota_search_success_return_count) / ota_search_enter_count
    #
    #         if ota_search_total_count == 0:
    #             ota_search_success_ratio = 0.0
    #         else:
    #             ota_search_success_ratio = float(ota_search_success_return_count) / ota_search_total_count
    #
    #         if ota_search_total_count == 0:
    #             ota_search_cache_success_ratio = 0.0
    #         else:
    #             ota_search_cache_success_ratio = float(ota_search_cache_success_return_count) / ota_search_total_count
    #
    #         Logger().debug('ota_search_cache_success_return_count %s' % ota_search_cache_success_return_count)
    #
    #         # OTA.ORDER 总数
    #         result = client.query('SELECT sum(count) FROM "OTA.ORDER" WHERE time > %sms and time < %sms ' % (yesterday_start_time, yesterday_end_time))
    #         ota_order_total_count = 0
    #         for point in result.get_points():
    #             ota_order_total_count += point['sum']
    #
    #         # OTA.ORDER 成功
    #         result = client.query('SELECT sum(count) FROM "OTA.ORDER" WHERE time > %sms and time < %sms and "return_status" = \'SUCCESS\' ' % (yesterday_start_time, yesterday_end_time))
    #         ota_order_success_return_count = 0
    #         for point in result.get_points():
    #             ota_order_success_return_count += point['sum']
    #
    #         if ota_order_total_count == 0:
    #             ota_order_success_ratio = 0.0
    #         else:
    #             ota_order_success_ratio = float(ota_order_success_return_count) / ota_order_total_count
    #
    #         # 查订比
    #         if ota_search_total_count == 0:
    #             ota_search_order_ratio = 0.0
    #         else:
    #             ota_search_order_ratio = float(ota_order_total_count) / ota_search_total_count
    #
    #         # 接口订单
    #         order_total_count = 0
    #         order_api_count = 0
    #         order_web_count = 0
    #         order_manual_count = 0
    #         income_amount = 0
    #         expense_amount = 0
    #         res = select(s for s in FlightOrder if s.ota_create_order_time >= yesterday and s.ota_create_order_time < today)
    #         # res = select(s for s in FlightOrder )
    #
    #         for o in res:
    #             order_total_count += 1
    #             if o.ota_type == 'API':
    #                 order_api_count += 1
    #             if o.ota_type == 'WEB':
    #                 order_web_count += 1
    #             if o.is_manual == 1:
    #                 order_manual_count += 1
    #
    #             if o.ota_pay_price and o.providers_total_price:
    #                 income_amount += o.ota_pay_price
    #                 expense_amount += o.providers_total_price
    #         profit = income_amount - expense_amount
    #
    #         m = dict(
    #             ota_search_enter_success_ratio=ota_search_enter_success_ratio,
    #             ota_search_total_count=ota_search_total_count,
    #             ota_search_success_ratio=ota_search_success_ratio,
    #             ota_search_cache_success_ratio=ota_search_cache_success_ratio,
    #             ota_order_total_count=ota_order_total_count,
    #             ota_order_success_ratio=ota_order_success_ratio,
    #             ota_search_order_ratio=ota_search_order_ratio,
    #             order_total_count=order_total_count,
    #             order_api_count=order_api_count,
    #             order_web_count=order_web_count,
    #             order_manual_count=order_manual_count,
    #             income_amount=income_amount,
    #             expense_amount=expense_amount,
    #             profit=profit
    #
    #         )
    #
    #         TBG.tb_metrics.write(
    #             "REPORT.DAILY",
    #             tags=dict(
    #                 ota_name='',
    #                 provider='',
    #                 provider_channel='',
    #                 report_date=str(yesterday)
    #             ),
    #             fields=m)
    #
    #         # 微信发送
    #         subject = u'TB-每日报表'
    #         content = u"生成日期： {report_date}\n直连搜索量：{ota_search_total_count}\n直连搜索缓存返回成功率：{ota_search_cache_success_ratio}\n直连搜索非过滤返回成功率：{ota_search_enter_success_ratio}\n直连生单接口调用量：{ota_order_total_count}\n直连生单接口成功率：{ota_order_success_ratio}\n查订比：{ota_search_order_ratio}\n订单总数：{order_total_count}\n直连订单数： {order_api_count}\n界面订单数：{order_web_count}\n人工介入订单数：{order_manual_count}\n收入：{income_amount}\n支出：{expense_amount}\n利润：{profit}".format(
    #             report_date=str(yesterday),
    #             ota_search_total_count=ota_search_total_count,
    #             ota_search_success_ratio='%.3f%%' % (ota_search_success_ratio * 100),
    #             ota_search_cache_success_ratio='%.3f%%' % (ota_search_cache_success_ratio * 100),
    #             ota_order_total_count=ota_order_total_count,
    #             ota_order_success_ratio='%.3f%%' % (ota_order_success_ratio * 100),
    #             ota_search_order_ratio='%.3f%%' % (ota_search_order_ratio * 100),
    #             order_total_count=order_total_count,
    #             order_api_count=order_api_count,
    #             order_web_count=order_web_count,
    #             order_manual_count=order_manual_count,
    #             income_amount=income_amount,
    #             expense_amount=expense_amount,
    #             profit=profit,
    #             ota_search_enter_success_ratio='%.3f%%' % (ota_search_enter_success_ratio * 100)
    #         )
    #
    #         r = requests.post("http://139.219.106.96:10000/bpns/event", json={
    #             "product": "tourbillon",
    #             "team": "dev",
    #             "source": "tourbillon",
    #             "category": "",
    #             "level": "warning",
    #             "subject": subject,
    #             "content": content,
    #             "sendto_wechat": {
    #                 "agentid": 1000010,
    #                 "msgtype": "text",
    #             }
    #         }, timeout=6)
    #         task_result = 'SUCCESS'
    #     except Exception as e:
    #         Logger().serror(e)
    #         exception = str(e)
    #         task_result = 'ERROR'
    #
    #     total_latency = Time.timestamp_ms() - start_time
    #
    #     TBG.tb_metrics.write(
    #         "MISCTASK",
    #         tags=dict(
    #             task='TB_REPORT',
    #             task_result=task_result,
    #             exception=exception
    #
    #         ),
    #         fields=dict(
    #             total_latency=total_latency,
    #             count=1
    #         ))

    def fusing_repo_monitor(self):
        """
        查看熔断库状态，如果有数据则定期通知熔断库数据到微信
        :return:
        """
        exception = ''
        start_time = Time.timestamp_ms()
        try:

            redis_conn = RedisPool(TBG.global_config['REDIS_HOST'], TBG.global_config['REDIS_PORT'],
                                   TBG.global_config['COMMON_REDIS_DB'], TBG.global_config["REDIS_PASSWORD"])

            fusing_result = TBG.redis_conn.redis_pool.hgetall('fusing_repo')
            Logger().sdebug('fusing_repo_list %s' % fusing_result)
            if fusing_result:
                content = ''
                for k,v in fusing_result.items():
                    content += '%s|%s\n---------------------\n'%(k,v)
                subject = '熔断库存在数据，请处理'
                Pokeman.send_wechat(content=content,subject=subject,level='info',agentid=1000010)


            task_result = 'SUCCESS'
        except Exception as e:
            Logger().serror(e)
            exception = str(e)
            task_result = 'ERROR'

        total_latency = Time.timestamp_ms() - start_time

        TBG.tb_metrics.write(
            "MISCTASK",
            tags=dict(
                task='GET_CELERY_QUEUE_INFO',
                task_result=task_result,
                exception=exception

            ),
            fields=dict(
                total_latency=total_latency,
                count=1
            ))

    def get_proxy_ip_list_a(self):
        """
        调用百变IP接口获取IP
        :return:
        """

        exception = ''
        start_time = Time.timestamp_ms()
        try:
            result = requests.get(TBG.global_config['EXTRACT_PROXY_ADDR_A']).json()
            proxy_list = result['proxy_list']
            proxy_list.sort(key=lambda x: x['ip'])
            proxy_list = [
                '%s:%s@%s' % (x['ip'], x['port'], datetime.datetime.strftime(
                    datetime.datetime.now() + datetime.timedelta(seconds=x['remain_time']), '%Y-%m-%d %H:%M:%S'
                )) for x in proxy_list if x['remain_time'] >= 10]

            Logger().sdebug(' proxy_list len %s' % (len(proxy_list)))
            ppool_list = TBG.redis_conn.redis_pool.lrange('PPOOL_A', 0, -1)

            # 当前代理池中小于5秒生存期的ip删除
            try:
                del_list = [i for i in ppool_list if (datetime.datetime.strptime(
                    i.split('@')[-1], '%Y-%m-%d %H:%M:%S') - datetime.timedelta(
                    seconds=10)) < datetime.datetime.now()]
            except:
                del_list = set(ppool_list).difference(set(proxy_list))

            add_list = set(proxy_list).difference(set(ppool_list))
            for x in add_list:
                TBG.redis_conn.redis_pool.lpush('PPOOL_A', x)
            for x in del_list:
                TBG.redis_conn.redis_pool.lrem('PPOOL_A', 0, x)

            TBG.tb_metrics.write(
                "HTTP.PROXY",
                tags=dict(
                    ip_pool='A'
                ),
                fields=dict(
                    extract_count=len(proxy_list),
                    add_count=len(add_list),
                    del_count=len(del_list),

                ))

            task_result = 'SUCCESS'

        except Exception as e:
            Logger().serror(e)
            exception = str(e)
            task_result = 'ERROR'

        total_latency = Time.timestamp_ms() - start_time

        TBG.tb_metrics.write(
            "MISCTASK",
            tags=dict(
                task='GET_PROXY_IP_LIST_A',
                task_result=task_result,
                exception=exception,

            ),
            fields=dict(
                total_latency=total_latency,
                count=1
            ))

    # def get_proxy_ip_list_b(self):
    #     """
    #     调用百变IP接口获取IP
    #              {
    #     "errno": 0,
    #     "errmsg": "SUCCESS",
    #     "proxy_list": [
    #     {
    #     "proxy_ip_port": "183.129.207.77:21066",
    #     "ip": "183.129.207.77",
    #     "port": "21066",
    #     "backend_ip": "125.73.92.186"
    #     },
    #     {
    #     "proxy_ip_port": "183.129.207.77:21049",
    #     "ip": "183.129.207.77",
    #     "port": "21049",
    #     "backend_ip": "113.13.167.162"
    #     }
    #     ]
    #     }
    #     :return:
    #     """
    #
    #     exception = ''
    #     start_time = Time.timestamp_ms()
    #     try:
    #         ip_data = requests.get(TBG.global_config['EXTRACT_PROXY_ADDR_B']).json()
    #         if ip_data['errno'] == '0' and ip_data['proxy_list']:
    #             proxy_ip = ip_data['proxy_list'][0]['proxy_ip_port']
    #             backend_ip = ip_data['proxy_list'][0]['backend_ip']
    #             TBG.redis_conn.insert_value('ppool_b_static', '{}@{}'.format(proxy_ip, backend_ip))
    #
    #             TBG.tb_metrics.write(
    #                 "HTTP.PROXY",
    #                 tags=dict(
    #                     ip_pool='b'
    #                 ),
    #                 fields=dict(
    #                     extract_count=1,
    #                     add_count=1,
    #                     del_count=1,
    #
    #                 ))
    #
    #             task_result = 'SUCCESS'
    #         else:
    #             Logger().error("==== pool b get ipdata err:{}".format(ip_data))
    #             task_result = 'FAIL'
    #
    #     except Exception as e:
    #         Logger().serror(e)
    #         exception = str(e)
    #         task_result = 'ERROR'
    #
    #     total_latency = Time.timestamp_ms() - start_time
    #
    #     TBG.tb_metrics.write(
    #         "MISCTASK",
    #         tags=dict(
    #             task='GET_PROXY_IP_LIST_B',
    #             task_result=task_result,
    #             exception=exception,
    #
    #         ),
    #         fields=dict(
    #             total_latency=total_latency,
    #             count=1
    #         ))

    def get_proxy_ip_list_c(self):
        """
        调用芝麻IP接口获取IP
        :return:
        """

        exception = ''
        start_time = Time.timestamp_ms()
        try:
            result = requests.get(TBG.global_config['EXTRACT_PROXY_ADDR_C']).json()
            Logger().sdebug(json.dumps(result))
            proxy_list = result['data']
            proxy_list.sort(key=lambda x: x['ip'])
            proxy_list = ['%s:%s@%s' % (x['ip'], x['port'], x['expire_time']) for x in proxy_list if (
                datetime.datetime.strptime(x['expire_time'], '%Y-%m-%d %H:%M:%S') - datetime.datetime.now()
            ).seconds >= 5]

            Logger().sdebug('proxy_list len %s' % ( len(proxy_list)))
            ppool_list = TBG.redis_conn.redis_pool.lrange('PPOOL_C', 0, -1)

            # 当前代理池中小于10秒生存期的ip删除
            try:
                del_list = [i for i in ppool_list if (datetime.datetime.strptime(
                    i.split('@')[-1], '%Y-%m-%d %H:%M:%S') - datetime.timedelta(seconds=60)) < datetime.datetime.now()]
            except:
                del_list = ppool_list

            add_list = set(proxy_list).difference(set(ppool_list))
            for x in add_list:
                TBG.redis_conn.redis_pool.lpush('PPOOL_C', x)
            for x in del_list:
                TBG.redis_conn.redis_pool.lrem('PPOOL_C', 0, x)

            TBG.tb_metrics.write(
                "HTTP.PROXY",
                tags=dict(
                    ip_pool='C'
                ),
                fields=dict(
                    extract_count=len(proxy_list),
                    add_count=len(add_list),
                    del_count=len(del_list),

                ))

            task_result = 'SUCCESS'

        except Exception as e:
            Logger().serror(e)
            exception = str(e)
            task_result = 'ERROR'

        total_latency = Time.timestamp_ms() - start_time

        TBG.tb_metrics.write(
            "MISCTASK",
            tags=dict(
                task='GET_PROXY_IP_LIST_C',
                task_result=task_result,
                exception=exception,

            ),
            fields=dict(
                total_latency=total_latency,
                count=1
            ))

    def get_proxy_ip_list_d(self):
        """
        调用百变IP接口获取IP
        :return:
        """

        exception = ''
        start_time = Time.timestamp_ms()
        try:
            result = requests.get(TBG.global_config['EXTRACT_PROXY_ADDR_D']).json()
            proxy_list = result['data']
            proxy_list.sort(key=lambda x: x['ip'])
            proxy_list = [
                '%s:%s@%s' % (x['ip'], x['port'], datetime.datetime.strftime(
                    datetime.datetime.now() + datetime.timedelta(seconds=int(x['ttl'] / 1000)), '%Y-%m-%d %H:%M:%S'
                )) for x in proxy_list if int(x['ttl'] / 1000) >= 10]

            # for ttlp in proxy_list:
            #     TBG.redis_conn.redis_pool.lpush('global_proxy_ip_hash',ttlp)


            Logger().sdebug('proxy_list len %s' % (len(proxy_list)))
            ppool_list = TBG.redis_conn.redis_pool.lrange('PPOOL_D', 0, -1)

            # 当前代理池中小于10秒生存期的ip删除
            try:
                del_list = [i for i in ppool_list if (datetime.datetime.strptime(
                    i.split('@')[-1], '%Y-%m-%d %H:%M:%S') - datetime.timedelta(
                    seconds=10)) < datetime.datetime.now()]
            except:
                del_list = set(ppool_list).difference(set(proxy_list))

            add_list = set(proxy_list).difference(set(ppool_list))
            for x in add_list:
                TBG.redis_conn.redis_pool.lpush('PPOOL_D', x)
            for x in del_list:
                TBG.redis_conn.redis_pool.lrem('PPOOL_D', 0, x)

            TBG.tb_metrics.write(
                "HTTP.PROXY",
                tags=dict(
                    ip_pool='D'
                ),
                fields=dict(
                    extract_count=len(proxy_list),
                    add_count=len(add_list),
                    del_count=len(del_list),

                ))

            task_result = 'SUCCESS'

        except Exception as e:
            Logger().serror(e)
            exception = str(e)
            task_result = 'ERROR'

        total_latency = Time.timestamp_ms() - start_time

        TBG.tb_metrics.write(
            "MISCTASK",
            tags=dict(
                task='GET_PROXY_IP_LIST_D',
                task_result=task_result,
                exception=exception,

            ),
            fields=dict(
                total_latency=total_latency,
                count=1
            ))

    def get_proxy_ip_list_f(self):
        """
        调用太阳代理获取ip，
        :return:
        """
        exception = ''
        start_time = Time.timestamp_ms()
        try:
            result = requests.get(TBG.global_config['EXTRACT_PROXY_ADDR_F']).json()
            proxy_list = result['data']
            proxy_list.sort(key=lambda x: x['ip'])
            proxy_list = ['%s:%s@%s' % (x['ip'], x['port'], x['expire_time']) for x in proxy_list if (
                datetime.datetime.strptime(x['expire_time'], '%Y-%m-%d %H:%M:%S') - datetime.datetime.now()
            ).seconds >= 10]

            Logger().sdebug('proxy_list len %s' % (len(proxy_list)))
            # 获取所有PPOOL_F的ip
            ppool_list = TBG.redis_conn.redis_pool.lrange('PPOOL_F', 0, -1)

            # 当前代理池中小于10秒生存期的ip删除
            try:
                del_list = [i for i in ppool_list if (datetime.datetime.strptime(
                    i.split('@')[-1], '%Y-%m-%d %H:%M:%S') - datetime.timedelta(
                    seconds=10)) < datetime.datetime.now()]
            except:
                del_list = set(ppool_list).difference(set(proxy_list))

            add_list = set(proxy_list).difference(set(ppool_list))
            for x in add_list:
                TBG.redis_conn.redis_pool.lpush('PPOOL_F', x)
            for x in del_list:
                TBG.redis_conn.redis_pool.lrem('PPOOL_F', 0, x)

            TBG.tb_metrics.write(
                "HTTP.PROXY",
                tags=dict(
                    ip_pool='F'
                ),
                fields=dict(
                    extract_count=len(proxy_list),
                    add_count=len(add_list),
                    del_count=len(del_list),

                ))

            task_result = 'SUCCESS'

        except Exception as e:
            Logger().serror(e)
            exception = str(e)
            task_result = 'ERROR'

        total_latency = Time.timestamp_ms() - start_time

        TBG.tb_metrics.write(
            "MISCTASK",
            tags=dict(
                task='GET_PROXY_IP_LIST_F',
                task_result=task_result,
                exception=exception,

            ),
            fields=dict(
                total_latency=total_latency,
                count=1
            ))

    # def reset_proxy_pool_b_geted_count_per_day(self):
    #     """
    #     每天凌晨重置计数器
    #     :return:
    #     """
    #
    #     exception = ''
    #     start_time = Time.timestamp_ms()
    #     try:
    #         TBG.redis_conn.insert_value('proxy_pool_b_geted_count_per_day', 0)
    #         task_result = 'SUCCESS'
    #     except Exception as e:
    #         Logger().serror(e)
    #         exception = str(e)
    #         task_result = 'ERROR'
    #
    #     total_latency = Time.timestamp_ms() - start_time
    #     TBG.tb_metrics.write(
    #         "MISCTASK",
    #         tags=dict(
    #             task='RESET_PPOOL_B_COUNTER',
    #             task_result=task_result,
    #             exception=exception,
    #
    #         ),
    #         fields=dict(
    #             total_latency=total_latency,
    #             count=1
    #         ))

    # def proxy_pool_b_geted_count_per_day(self):
    #     """
    #     统计B池每日获取IP数
    #     :return:
    #     """
    #
    #     exception = ''
    #     start_time = Time.timestamp_ms()
    #     try:
    #         value = TBG.redis_conn.get_value('proxy_pool_b_geted_count_per_day')
    #         task_result = 'SUCCESS'
    #         TBG.tb_metrics.write(
    #             "HTTP.PROXY.POOL_B_GETED_COUNT_PER_DAY",
    #             fields=dict(
    #                 value=value
    #             ))
    #     except Exception as e:
    #         Logger().serror(e)
    #         exception = str(e)
    #         task_result = 'ERROR'
    #
    #     total_latency = Time.timestamp_ms() - start_time
    #     TBG.tb_metrics.write(
    #         "MISCTASK",
    #         tags=dict(
    #             task='GET_PPOOL_B_COUNTER',
    #             task_result=task_result,
    #             exception=exception,
    #
    #         ),
    #         fields=dict(
    #             total_latency=total_latency,
    #             count=1
    #         ))

    def extract_hot_flight(self):
        """
        从metric中提取热门航班到数据库，用于优化爬虫
        :return:
        """

    @db_session
    def extract_flight(self):
        """
        提取航班
        {u'values': [[u'2018-08-31T16:00:00.000000001Z', 2]], u'name': u'OTA.SEARCH', u'columns': [u'time', u'sum'], u'tags': {u'to_airport': u'DPS', u'from_airport': u'ZYI'}}
        :return:
        """
        exception = ''
        start_time = Time.timestamp_ms()
        try:
            from influxdb import InfluxDBClient
            client = InfluxDBClient(TBG.global_config['METRICS_SETTINGS']['host'], TBG.global_config['METRICS_SETTINGS']['port'], TBG.global_config['METRICS_SETTINGS']['user'],
                                    TBG.global_config['METRICS_SETTINGS']['password'], TBG.global_config['METRICS_SETTINGS']['db'])

            today = datetime.date.today()
            yesterday = today - datetime.timedelta(days=1)

            # 测试
            xxx = datetime.date.today()
            today = xxx - datetime.timedelta(days=1)
            yesterday = xxx - datetime.timedelta(days=2)

            yesterday_start_time = int(time.mktime(time.strptime(str(yesterday), '%Y-%m-%d'))) * 1000
            yesterday_end_time = int(time.mktime(time.strptime(str(today), '%Y-%m-%d'))) * 1000 - 1
            Logger().sdebug('time_range %s %s' % (yesterday_start_time, yesterday_end_time))
            # yesterday_end_time = 1535757599999
            # 搜索总数
            # result = client.query(
            #     'SELECT sum(count) FROM "two_year"."OTA.SEARCH.AGGR" WHERE time > %sms and time < %sms group by "from_airport","to_airport"' % (yesterday_start_time, yesterday_end_time))
            result = client.query(
                'SELECT sum(count) FROM "two_year"."OTA.SEARCH.AGGR" WHERE time > %sms and time < %sms group by "from_to_airport"' % (yesterday_start_time, yesterday_end_time))
            #
            # result = client.query(
            #     'SELECT sum(count) FROM "one_year"."OTA.SEARCH.AGGR" where time > now() - 2h group by "from_to_airport"')

            flights = []
            point_count = []
            for point in result.raw.get('series', []):
                point_count.append(point['values'][0][1])
                count = point['values'][0][1]
                # TODO 该参数后面需要动态调整
                if count > 1000 and point['tags']['from_to_airport']:
                    if 1000 < count <= 2000:
                        pr = 2
                    elif 2000 < count <= 4000:
                        pr = 3
                    elif 4000 < count:
                        pr = 4
                    flights.append((point['tags']['from_to_airport'], pr))
                    # flights.add('%s-%s' % (point['tags']['to_airport'], point['tags']['from_airport']))

            Logger().sdebug('point_count %s' % sorted(point_count, reverse=True))
            for f, pr in flights:
                try:
                    from_airport, to_airport = f.split('-')
                    from_airport = from_airport[:3]
                    to_airport = to_airport[:3]
                    fr = FlightRepo()
                    fr.from_airport = from_airport
                    fr.to_airport = to_airport
                    fr.from_to_airport = f
                    fr.pr = pr
                    fr.is_crawl = 1
                    commit()
                    flush()
                except Exception as e:
                    pass
                    # Logger().sdebug('flight insert error %s' % str(e))

            task_result = 'SUCCESS'
        except Exception as e:
            Logger().serror(e)
            exception = str(e)
            task_result = 'ERROR'

        total_latency = Time.timestamp_ms() - start_time
        TBG.tb_metrics.write(
            "MISCTASK",
            tags=dict(
                task='EXTRACT_FLIGHT',
                task_result=task_result,
                exception=exception

            ),
            fields=dict(
                total_latency=total_latency,
                count=1
            ))


if __name__ == '__main__':
    pass
