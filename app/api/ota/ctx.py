#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, too-many-arguments, broad-except, anomalous-backslash-in-string
# pylint: disable=missing-docstring, line-too-long, too-few-public-methods
"""
# @Author  : wxt
# @Software: PyCharm
"""
import gevent
from app import TBG
from Queue import Queue,Empty

from ...utils.logger import Logger
from ...utils.util import Time
from ...dao.models import *
from ...utils.exception import *
from pony.orm import db_session
import redis


class _LogWriter(object):
    flush_interval = 5  # time: s

    # override these attributes in subclass
    queue = None
    log_model_class = None
    get_log_method = None

    @classmethod
    def flush_later(cls,item):
        cls.queue.put_nowait(item)

    @classmethod
    def _daemon_run(cls):
        while True:
            cls._bulk_insert()
            gevent.sleep(cls.flush_interval)

    @classmethod
    def run_async(cls):
        Logger().sinfo('_LogWriter %s init' %cls.__class__.__name__)
        daemon = gevent.spawn(cls._daemon_run)
        daemon.start()

    @classmethod
    def flush_nowait(cls,item):
        cls.flush_later(item)
        cls._bulk_insert()

    @classmethod
    def _bulk_insert(cls):
        log_items = []
        while cls.queue.qsize():
            try:
                log_items.append(cls.queue.get_nowait())
                cls.queue.task_done()
            except Empty:
                pass
        if not log_items:
            return

        # retry for 3 times
        for _ in range(3):
            try:

                # TODO 硬编码
                cls.ota_search_log_insert_method(log_items)
                break
            except Exception as e:
                Logger().serror(e)
                gevent.sleep(0.1)

        else:
            Logger().swarn('sql insert error ')

    @classmethod
    @db_session
    def ota_search_log_insert_method(cls,log_items):
        insert_list = []
        for record in log_items:
            if record.ret_date:
                _ = '("%s","%s","%s","%s","%s","%s","%s","%s","%s","%s","%s",%s,%s,%s,%s,%s,"%s","%s","%s","%s","%s","%s","%s")' % (record.ota_name, record.provider, record.provider_channel,
                                                                                                                                    record.from_date, record.ret_date , record.from_airport, record.to_airport,
                                                                                                                                    record.from_city, record.to_city, record.from_country, record.to_country,
                                                                                                                                    record.adt_count, record.chd_count, record.inf_count, record.total_latency,
                                                                                                                                    record.provider_latency, record.return_status, record.return_details,
                                                                                                                                    record.assoc_search_routings_amount,
                                                                                                                                    record.fare_operation, record.assoc_order_id, record.routing_range,
                                                                                                                                    record.trip_type)
                insert_list.append(_)
            else:
                _ = '("%s","%s","%s","%s",null,"%s","%s","%s","%s","%s","%s",%s,%s,%s,%s,%s,"%s","%s","%s","%s","%s","%s","%s")' % (record.ota_name, record.provider, record.provider_channel,
                                                                                                                                    record.from_date,record.from_airport, record.to_airport,
                                                                                                                                    record.from_city, record.to_city, record.from_country, record.to_country,
                                                                                                                                    record.adt_count, record.chd_count, record.inf_count, record.total_latency,
                                                                                                                                    record.provider_latency, record.return_status, record.return_details,
                                                                                                                                    record.assoc_search_routings_amount,
                                                                                                                                    record.fare_operation, record.assoc_order_id, record.routing_range,
                                                                                                                                    record.trip_type)
                insert_list.append(_)


        insert_clause = ','.join(insert_list)
        sql_clause = 'insert into ota_search_log (ota_name,provider,provider_channel,from_date,ret_date,from_airport,to_airport,from_city,to_city,from_country,to_country,adt_count,chd_count,inf_count,total_latency,provider_latency,return_status,return_details,assoc_search_routings_amount,fare_operation,assoc_order_id,routing_range,trip_type)values %s' % insert_clause
        Logger().sdebug('sql_clause %s'%sql_clause)
        TBG.tourbillon_extra_db.execute(sql_clause)

    # @classmethod
    # @db_session
    # def ota_search_log_insert_method(cls,log_items):
    #     insert_list = []
    #     for record in log_items:
    #         if record.ret_date:
    #             _ = '("%s","%s","%s","%s","%s","%s","%s","%s","%s","%s","%s",%s,%s,%s,%s,%s,"%s","%s","%s","%s","%s","%s","%s")' % (record.ota_name, record.provider, record.provider_channel,
    #                                                                                                                                 record.from_date, record.ret_date , record.from_airport, record.to_airport,
    #                                                                                                                                 record.from_city, record.to_city, record.from_country, record.to_country,
    #                                                                                                                                 record.adt_count, record.chd_count, record.inf_count, record.total_latency,
    #                                                                                                                                 record.provider_latency, record.return_status, record.return_details,
    #                                                                                                                                 record.assoc_search_routings_amount,
    #                                                                                                                                 record.fare_operation, record.assoc_order_id, record.routing_range,
    #                                                                                                                                 record.trip_type)
    #             insert_list.append(_)
    #         else:
    #             _ = '("%s","%s","%s","%s",null,"%s","%s","%s","%s","%s","%s",%s,%s,%s,%s,%s,"%s","%s","%s","%s","%s","%s","%s")' % (record.ota_name, record.provider, record.provider_channel,
    #                                                                                                                                 record.from_date,record.from_airport, record.to_airport,
    #                                                                                                                                 record.from_city, record.to_city, record.from_country, record.to_country,
    #                                                                                                                                 record.adt_count, record.chd_count, record.inf_count, record.total_latency,
    #                                                                                                                                 record.provider_latency, record.return_status, record.return_details,
    #                                                                                                                                 record.assoc_search_routings_amount,
    #                                                                                                                                 record.fare_operation, record.assoc_order_id, record.routing_range,
    #                                                                                                                                 record.trip_type)
    #             insert_list.append(_)
    #
    #
    #     insert_clause = ','.join(insert_list)
    #     sql_clause = 'insert into ota_search_log (ota_name,provider,provider_channel,from_date,ret_date,from_airport,to_airport,from_city,to_city,from_country,to_country,adt_count,chd_count,inf_count,total_latency,provider_latency,return_status,return_details,assoc_search_routings_amount,fare_operation,assoc_order_id,routing_range,trip_type)values %s' % insert_clause
    #     Logger().sdebug('sql_clause %s'%sql_clause)
    #     TBG.tourbillon_extra_db.execute(sql_clause)


class OTASearchLogDbWriter(_LogWriter):
    get_log_method = None
    queue = Queue()




if __name__ == '__main__':
    pass