#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, too-many-arguments, broad-except, anomalous-backslash-in-string
# pylint: disable=missing-docstring, line-too-long, too-few-public-methods
"""
# @Author  : wxt
# @Software: PyCharm
"""

import os
import inspect
from Queue import Queue
from ..utils.logger import Logger
import gevent
import requests

from ..utils.util import Time

HOSTNAME = os.environ.get("HOSTNAME") or "unknown"


class Metrics(object):
    def __init__(self, endpoint=None, flush_interval=None,enabled=None,**kwargs):
        assert isinstance(endpoint, str)
        assert isinstance(flush_interval, int)

        self.interval = flush_interval
        self.endpoint = endpoint
        self.session = requests.session()
        self.q = Queue()
        self.tasks = set()
        self.enabled = enabled

    def register_daemon_task(self, func):
        assert callable(func)
        self.tasks.add(func)

    def write(self, metrics_name, tags=None, fields=None):

        if self.enabled:

            assert isinstance(metrics_name, str)
            assert isinstance(tags, dict)
            assert isinstance(fields, dict)
            tags = tags or {}

            # TODO 自动添加tag功能 暂时注释掉，貌似没卵用
            # lf = inspect.currentframe()
            #
            # current_frame_name = ''
            # last_provider_channel = ''
            # last_ota_name = ''
            # for x in range(0, 20):
            #     lf = lf.f_back
            #
            #     if (current_frame_name and last_provider_channel and last_ota_name) or lf == None:
            #         break
            #     # print lf.f_locals
            #     if not last_provider_channel and 'TB_PROVIDER_CHANNEL' in lf.f_locals:
            #         last_provider_channel = lf.f_locals['TB_PROVIDER_CHANNEL']
            #     if not last_ota_name and 'TB_OTA_NAME' in lf.f_locals:
            #         last_ota_name = lf.f_locals['TB_OTA_NAME']
            #     if not current_frame_name and 'TB_FRAME_NAME' in lf.f_locals:
            #         current_frame_name = lf.f_locals['TB_FRAME_NAME']
            # tags['frame_name'] = current_frame_name
            # tags['ota_name'] = last_ota_name
            # tags['provider_channel'] = last_provider_channel

            tags["hostname"] = HOSTNAME
            fields = fields or {}
            # 'cpu_load_short,host=server01,region=us-west value=0.64 1434055562000000000'
            tags_list = []
            for k,v in tags.iteritems():
                if isinstance(v,bool):
                    if v:
                        tags_list.append('%s=%s' % (k,1))
                    else:
                        tags_list.append('%s=%s' % (k, 0))
                elif v and (isinstance(v,unicode) or isinstance(v,str) ):
                    tags_list.append('%s=%s' % (k,v.replace(' ','\ ').replace('=','\=').replace(',','\,')))
                elif isinstance(v,int):
                    tags_list.append('%s=%s' % (k, v))
            tag_str = ','.join(tags_list)
            point = "{},{} {} {}".format(
                metrics_name,
                tag_str,
                ",".join("{}={}".format(k, v) for k, v in fields.items()),
                Time.timestamp_ns())
            self.q.put_nowait(point)

    def write_nowait(self, metrics_name, tags=None, fields=None):
        self.write(metrics_name, tags=tags, fields=fields)
        self._points_aggregating()

    def _points_aggregating(self):
        try:
            points = []
            count = 0     #       print 'get'
            while self.q.qsize():
                count +=1
                points.append(self.q.get_nowait())
            Logger().info('points length %s' % len(points))
            if points:
                for x in range(0,3):
                    try:
                        Logger().sinfo('points %s'%points[:50])
                        data = "\n".join(points).encode('utf-8')
                        http_conn = self.session.post(self.endpoint, data=data)
                        Logger().sdebug('metrics %s %s' %(http_conn.status_code,http_conn.content))
                        break
                    except requests.RequestException as e:
                        Logger().serror('METRICS_REQUEST_ERROR')
        except Exception as e:
            Logger().error('METRICS_UNKNOWN_ERROR')

    def _daemon_run(self):
        while True:
            try:
                # Logger().info('metrics_loop')
                self._points_aggregating()
                gevent.sleep(self.interval)
            except Exception as e:
                Logger().serror('METRICS_DAEMON_ERROR')

    def run_async(self):
        if self.enabled:
            Logger().sinfo('Metric run_async start')
            daemon = gevent.spawn(self._daemon_run)
            # gevent.spawn(self.write_test)
            daemon.start()

    # def write_test(self):
    #     gevent.sleep(3)
    #     for x in range(0,10):
    #         self.write(
    #             "TEST",
    #             tags=dict(
    #                 task='SCHEDULED_AIRLINE_CACHE_SYNC'
    #
    #             ),
    #             fields=dict(
    #                 count=1
    #             ))
    #         gevent.sleep(0.01)


if __name__ == '__main__':
    pass