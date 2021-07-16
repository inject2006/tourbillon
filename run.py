#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

"""
测试命令备注
ota_api:python run.py -t ota_api -p 9001 -h 0.0.0.0 debug
web_api:python run.py  -t web_api -p 9801 -h 0.0.0.0 debug
init:python run.py  -t init init
test:python run.py -t test test
order_manager:python run.py  -t order_manager order
crawler_manager:python run.py  -t crawler_manager crawler
alipay:python run.py -t alipay alipay
tc_verify:python run.py -t tc_verify tc_verify

一次性执行模块中某函数：python run.py -t crawler_manager crawler -e task_controller

"""


from __future__ import absolute_import
import os
import sys
from multiprocessing import Process
#
# reload(sys)
# sys.setdefaultencoding('utf-8')

this_dir = os.path.dirname(os.path.abspath(__file__))
this_pardir = os.path.join(this_dir, os.pardir)
try:
    from app import create_app
except ImportError:
    sys.path.insert(0, this_pardir)
    from app import create_app

if __name__ == '__main__':

    print('execute from python')
    print(sys.argv)
    if sys.argv[-1] in ['debug','prod']:

        if len(sys.argv) > 5:
            host = sys.argv[6]
            port = int(sys.argv[4])
        else:
            host = '0.0.0.0'
            port = 5000
    else:
        host = '0.0.0.0'
        port = 5000
    tb_app_name = sys.argv[3]
    if tb_app_name in  ['flight_crawl_task','flight_ota_fare_task','dynamic_fare_task','fare_comparison_task','sub_order_task','flight_order_task','check_ota_order_status_task','scheduled_airline_crawl_task','lowprice_stabilizer']:
        # worker启动方式
        process_count = int(sys.argv[4])
        thread_count = int(sys.argv[5])
        print("process_count %s thread_count %s" % (process_count, thread_count))
        subscriber_list = []
        from app import GeventWrap
        if tb_app_name == 'flight_crawl_task':  # 常规routing爬虫
            from app.gearset.crawler import flight_crawl_task
            for i in range(0, process_count):
                subscriber_list.append(GeventWrap(queue='flight_crawl_task',func=flight_crawl_task,tb_app_name=tb_app_name,thread_count=thread_count,no_ack=False))

        elif tb_app_name == 'flight_ota_fare_task':  # OTA异步运价爬取
            from app.gearset.crawler import flight_ota_fare_task
            for i in range(0, process_count):
                subscriber_list.append(GeventWrap(queue='flight_ota_fare_task',func=flight_ota_fare_task,tb_app_name=tb_app_name,thread_count=thread_count,no_ack=False))

        elif tb_app_name == 'dynamic_fare_task':
            from app.gearset.crawler import dynamic_fare_task
            for i in range(0, process_count):
                subscriber_list.append(GeventWrap(queue='dynamic_fare_task',func=dynamic_fare_task,tb_app_name=tb_app_name,thread_count=thread_count,no_ack=False))

        elif tb_app_name == 'fare_comparison_task':
            from app.gearset.crawler import fare_comparison_task
            for i in range(0, process_count):
                subscriber_list.append(GeventWrap(queue='fare_comparison_task',func=fare_comparison_task,tb_app_name=tb_app_name,thread_count=thread_count,no_ack=False))

        elif tb_app_name == 'sub_order_task':
            from app.gearset.order import sub_order_task
            for i in range(0, process_count):
                subscriber_list.append(GeventWrap(queue='sub_order_task',func=sub_order_task,tb_app_name=tb_app_name,thread_count=thread_count,no_ack=False))

        elif tb_app_name == 'flight_order_task':
            from app.gearset.order import flight_order_task
            for i in range(0, process_count):
                subscriber_list.append(GeventWrap(queue='flight_order_task',func=flight_order_task,tb_app_name=tb_app_name,thread_count=thread_count,no_ack=False))

        elif tb_app_name == 'check_ota_order_status_task':
            from app.gearset.order import check_ota_order_status_task
            for i in range(0, process_count):
                subscriber_list.append(GeventWrap(queue='check_ota_order_status_task',func=check_ota_order_status_task,tb_app_name=tb_app_name,thread_count=thread_count,no_ack=False))
        elif tb_app_name == 'scheduled_airline_crawl_task':
            from app.gearset.crawler import scheduled_airline_crawl_task
            for i in range(0, process_count):
                subscriber_list.append(GeventWrap(queue='scheduled_airline_crawl_task',func=scheduled_airline_crawl_task,tb_app_name=tb_app_name,thread_count=thread_count,no_ack=False))
        elif tb_app_name == 'lowprice_stabilizer':
            from app.gearset.lowprice_stabilizer import LowpriceStabilizer

            for i in range(0, process_count):
                subscriber_list.append(GeventWrap(queue='lowprice_stabilizer', func=LowpriceStabilizer.run, tb_app_name=tb_app_name, thread_count=thread_count, no_ack=False))
                # print('22222222')
        process_list = []
        for sub in subscriber_list:
            process = Process(target=sub.run)
            process.start()
            process_list.append(process)

        # wait for all process to finish
        for process in process_list:
            process.join()
    else:


        # gevent补丁，可能会导致某些模块不兼容
        from gevent import monkey
        monkey.patch_all()
        from flask_script import Manager, Shell, Server
        capp = create_app(tb_app_name=sys.argv[2])
        manager = Manager(capp)

        def make_shell_context():
            return dict(app=capp)


        manager.add_command("shell", Shell(make_context=make_shell_context))
        manager.add_command("debug", Server(use_debugger=True, use_reloader=True,host=host,port=port))
        manager.add_command("prod", Server(use_debugger=False, use_reloader=False, host=host, port=port))
        manager.add_option('-t','--tb_app_name',required=False)
        manager.add_option('-p', '--tb_port', required=False)
        manager.add_option('-h', '--tb_host', required=False)
        from app.gearset.test import TestController
        manager.add_command("test", TestController())
        from app.gearset.crawler import CrawlerController
        manager.add_command("crawler_manager", CrawlerController())
        from app.gearset.order import OrderController
        manager.add_command("order_manager", OrderController())
        from app.gearset.alipay import Alipay
        manager.add_command("alipay", Alipay())
        from app.gearset.alipay_qcode import AlipayQcode
        manager.add_command("alipay_qcode", AlipayQcode())
        from app.gearset.provider_session_manager import ProviderSessionManager
        manager.add_command("provider_session_manager", ProviderSessionManager())
        from app.gearset.tc_auto_verify import TCAutoVerify
        manager.add_command("tc_auto_verify", TCAutoVerify())
        from app.gearset.misc_task import MiscController
        manager.add_command("misc_task", MiscController())
        from app.gearset.automator import Automator
        manager.add_command("automator", Automator())

        @manager.command
        def profile(length=25, profile_dir=None):
            """Start the application under the code profiler."""
            from werkzeug.contrib.profiler import ProfilerMiddleware
            capp.wsgi_app = ProfilerMiddleware(
                capp.wsgi_app, restrictions=[length], profile_dir=profile_dir)
            capp.run(debug=True)


        # dev: python wsgi.py profile(shell)
        manager.run()
