#!/usr/local/bin/python2.7
# -*- coding: utf-8 -*-

import logging
import sys
import os
import gevent
import json
from flask import Flask
from flask_cors import CORS
from flask_caching import Cache
from app.utils.logger import Logger
from app.utils.util import AttrDict
from app.dao.redis_dao import CacheAccessObject
from app.dao.metrics import Metrics
from haigha.connection import Connection as haigha_Connection
from haigha.message import Message

reload(sys)
sys.setdefaultencoding('utf-8')

__TBVER__ = '1.0.0'  # 版本号，随着版本发布更新


def get_conf_path():
    par_dir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
    env_mode = os.environ.get("env_mode", "").strip()
    config_file = os.path.join(par_dir, "conf/%s.py" % env_mode)
    print(config_file)
    return config_file


# 全局变量
flask_app = Flask(__name__)
CORS(flask_app, resources={r"/*": {"origins": "*"}})
TBG = AttrDict(redis_conn=None)
TBG.fcache = Cache(flask_app, config={'CACHE_TYPE': "simple"})  # flask 进程级别缓存
flask_app.config.from_pyfile(get_conf_path())
TBG.global_config = flask_app.config


# 旧版本引用，弃用，新版本所有变量放入TBG中，采用 TBG.redis_conn 的格式
# redis_conn = None
# config_redis = None
# tourbillon_extra_db = None
# tb_metrics = None
# tb_aggr_metrics = None
# cached_meta = None
# tourbillon_db = None
# mailer = None
# cache_access_object = None
# global_config = None

# class TbWorker(object):
#
#     def __init__(self,queue,func,tb_app_name,thread_count,no_ack=True):
#         """
#
#         :param queue:
#         :param func:
#         :param tb_app_name:
#         :param thread_count:
#         :param no_ack:  是否需要应答  如果no_ack=False,当消费者down掉了，RabbitMQ会重新将该任务添加到队列中
#         """
#
#
#         self._params = pika.connection.ConnectionParameters(TBG.global_config['TB_EXCHANGE_HOST'], 5672, '/',
#                                                             pika.credentials.PlainCredentials(TBG.global_config['TB_EXCHANGE_USER'], TBG.global_config['TB_EXCHANGE_PASSWORD']))
#         self._conn = None
#         self._channel = None
#
#         self.queue = queue
#         self.tb_app_name = tb_app_name
#         self.thread_count = thread_count
#         self.func = func
#         self.no_ack = no_ack
#
#     def connect(self):
#         self._conn = pika.BlockingConnection(self._params)
#         self._channel = self._conn.channel()
#         self._channel.basic_qos(prefetch_count=1)
#
#     def run(self):
#         from gevent import monkey
#         monkey.patch_all()
#         capp = create_app(tb_app_name=self.tb_app_name)
#         self.connect()
#         for c in range(0,self.thread_count):
#             gevent.spawn(self._cosume)
#         while 1:
#             gevent.sleep(0.02)
#         # self.channel.basic_consume(self.func, queue=self.queue, no_ack=True)
#         # self.channel.start_consuming()
#
#     def _cosume(self):
#
#         for method_frame, properties, body in self.channel.consume(queue=self.queue,no_ack=self.no_ack):
#             try:
#                 # 尝试转换 json
#                 try:
#                     body = json.loads(body)
#                 except Exception as e:
#                     pass
#
#                 self.func(body)
#
#                 if not self.no_ack:
#                     self.channel.basic_ack(delivery_tag=method_frame.delivery_tag)
#             except pika.exceptions.ConnectionClosed:
#                 self.connect()

class GeventWrap(object):

    def __init__(self, queue, func, tb_app_name, thread_count, no_ack=True):
        """
        gevent haigha
        x-message-deduplication
        x-message-ttl
        :param queue:
        :param func:
        :param tb_app_name:
        :param thread_count:
        :param no_ack:  是否需要应答  如果no_ack=False,当消费者down掉了，RabbitMQ会重新将该任务添加到队列中
        """
        self.queue = queue
        self.tb_app_name = tb_app_name
        self.thread_count = thread_count
        self.func = func
        self.no_ack = no_ack

    def run(self):
        from gevent import monkey
        monkey.patch_all()
        capp = create_app(tb_app_name=self.tb_app_name)
        for c in range(0,self.thread_count):
            gevent.spawn(TbWorker,queue=self.queue,func=self.func,no_ack=self.no_ack)
        while 1:
            gevent.sleep(0.02)
        # self.channel.basic_consume(self.func, queue=self.queue, no_ack=True)
        # self.channel.start_consuming()


class TbWorker(object):

    def __init__(self, queue, func, no_ack=True):
        """
        gevent haigha
        x-message-deduplication
        x-message-ttl
        :param queue:
        :param func:
        :param thread_count:
        :param no_ack:  是否需要应答  如果no_ack=False,当消费者down掉了，RabbitMQ会重新将该任务添加到队列中
        """
        self.queue = queue
        self.func = func
        self.no_ack = no_ack
        Logger().sinfo('no_ack %s' % no_ack)
        self._conn = None
        self._channel = None
        self.enable = TBG.global_config['TB_EXCHANGE']['ENABLE']
        if self.enable:
            self.connect()
            self._message_pump_greenlet = gevent.spawn(self._message_pump_greenthread)
        else:
            Logger().warn('TB_EXCHANGE disabled')

    def connect(self):
        self._conn = haigha_Connection(transport='gevent', user=TBG.global_config['TB_EXCHANGE']['USER'], password=TBG.global_config['TB_EXCHANGE']['PASSWORD'], vhost='/', port=5672,
                                       host=TBG.global_config['TB_EXCHANGE']['HOST'],close_cb=self._connection_closed_cb,heartbeat=60)
        self._channel = self._conn.channel()
        self._channel.add_close_listener(self._channel_closed_cb)
        self._channel.basic.qos(prefetch_count=1)
        self._channel.basic.consume(queue=self.queue, no_ack=self.no_ack,
                                    consumer=self._handle_incoming_messages)

    def _message_pump_greenthread(self):
        while 1:
            try:
                while self._conn is not None:
                    self._conn.read_frames()
                    gevent.sleep()
            except Exception as e:
                Logger().error(e)
            try:
                gevent.sleep(2)
                self.connect()
            except Exception as e:
                self._conn = None
                Logger().error(e)

    def _handle_incoming_messages(self, msg):
        try:
            try:
                body = json.loads(str(msg.body))
            except Exception as e:
                body = str(msg.body)
            try:
                self.func(body)
            except Exception as e:
                Logger().serror(e)
            if not self.no_ack:
                Logger().debug('ack.............')
                self._channel.basic.ack(delivery_tag=msg.delivery_info['delivery_tag'])
        except Exception as e:
            Logger().serror(e)

    def _channel_closed_cb(self, ch):
        self._channel = None
        self._conn.close()
        return

    def _connection_closed_cb(self):
        self._conn = None
        return

# import pika
# class TbPublisher(object):
#
#     def __init__(self):
#         self._params = pika.connection.ConnectionParameters(TBG.global_config['TB_EXCHANGE']['HOST'],5672,'/',pika.credentials.PlainCredentials(TBG.global_config['TB_EXCHANGE']['USER'], TBG.global_config['TB_EXCHANGE']['PASSWORD']))
#         self._conn = None
#         self._channel = None
#
#     def connect(self):
#         self._conn = pika.BlockingConnection(self._params)
#         self._channel = self._conn.channel()
#
#     def _send(self, msg,dedup_hash=None):
#         if isinstance(msg,list) or isinstance(msg,dict):
#             body = json.dumps(msg)
#         if dedup_hash:
#             prop = pika.BasicProperties(
#                 delivery_mode=2,
#                 headers={'x-deduplication-header': dedup_hash}  # 使消息或任务也持久化存储
#             )
#         else:
#             prop = pika.BasicProperties(
#                 delivery_mode=2            )
#         self._channel.basic_publish(exchange=TBG.global_config['TB_EXCHANGE'],
#                               routing_key=routing_key,
#                               body=body,
#                               properties=prop)
#
#     def send(self, body,routing_key,dedup_hash=None):
#         """Publish msg, reconnecting if necessary."""
#
#         try:
#             self._send(body=body,routing_key=routing_key,dedup_hash=dedup_hash)
#         except pika.exceptions.ConnectionClosed:
#             self.connect()
#             self._publish(body=body,routing_key=routing_key,dedup_hash=dedup_hash)
#
#     def close(self):
#         if self._conn and self._conn.is_open:
#             self._conn.close()

class TbPublisher(object):

    def __init__(self,transport='gevent'):
        """

        :param transport:  gevent 适用于ota_api 对于 crawler_worker 由于发送时长间隔过长，会导致无法发送，链接中断，目前只能每次发送的时候重新建立连接来缓解此问题  socket
        """
        self._conn = None
        self._channel = None
        self.transport = transport
        self.connect()

        if self.transport == 'gevent':
            self._message_pump_greenlet = gevent.spawn(self._message_pump_greenthread)

    def _message_pump_greenthread(self):
        while 1:
            try:
                while self._conn is not None:
                    self._conn.read_frames()
                    gevent.sleep()
            except Exception as e:
                pass
            try:
                gevent.sleep(2)
                self.connect()
            except Exception as e:
                self._conn = None

    def connect(self):
        self.enable = TBG.global_config['TB_EXCHANGE']['ENABLE']
        if self.enable:
            self._conn = haigha_Connection(transport=self.transport,user=TBG.global_config['TB_EXCHANGE']['USER'], password=TBG.global_config['TB_EXCHANGE']['PASSWORD'], vhost='/', port=5672,
                                           host=TBG.global_config['TB_EXCHANGE']['HOST'],heartbeat=60)
            self._channel = self._conn.channel()
            self.exchange = TBG.global_config['TB_EXCHANGE']['EXCHANGE']
        else:
            Logger().warn('TB_EXCHANGE disabled')

    def send(self, body, routing_key, dedup_hash=None,ttl=None):
        """

        :param body: json or str
        :param routing_key:
        :param dedup_hash: 是否需要去重
        :param ttl:  过期时间 单位秒
        :return:
        """
        if self.enable:
            try:
                self._send(body=body, routing_key=routing_key, dedup_hash=dedup_hash,ttl=ttl)
            except Exception as e:
                Logger().error(e)
                self.connect()
                self._send(body=body, routing_key=routing_key, dedup_hash=dedup_hash,ttl=ttl)
        else:
            Logger().info('TbPublisher faker send routing_key %s dedup_hash %s ttl %s message %s ' % (routing_key,dedup_hash,ttl,body))

    def _send(self, body, routing_key, dedup_hash=None,ttl=None):
        if isinstance(body, list) or isinstance(body, dict):
            body = json.dumps(body)

        application_headers = {}
        if dedup_hash:
            application_headers['x-deduplication-header'] = dedup_hash
        if ttl: # TODO 临时注释
            application_headers['x-message-ttl'] = ttl * 1000  # rabbitmq的 ttl为毫秒，所以需要转换
        msg = Message(body, delivery_mode=2, application_headers=application_headers)

        self._channel.basic.publish(msg, self.exchange , routing_key)
        # Logger().sinfo('application_headers %s routing_key %s self.exchange %s msg %s' % (application_headers,routing_key,self.exchange,msg))

    def close(self):
        if self._conn:
            self._conn.close()


def bind_pony_db(app, db_name, dbs=None):
    if app.config[db_name].get('ENABLE', False):
        dbs.bind(
            'mysql',
            host=app.config[db_name]['MYSQL_HOST'],
            port=app.config[db_name]['MYSQL_PORT'],
            user=app.config[db_name]['MYSQL_USER'],
            passwd=app.config[db_name]['MYSQL_PASSWORD'],
            db=app.config[db_name]['MYSQL_DB']
        )
        dbs.generate_mapping(create_tables=True)
    return dbs


def sentry_logger_init(tb_app_name=''):
    print 'logger tb_app_name %s' % tb_app_name
    # 暂时去掉sentry
    # sentry = Sentry()
    # if flask_app.config.get('SENTRY_APP'):
    #     sentry.init_app(
    #         flask_app,
    #         dsn=flask_app.config['SENTRY_DSN'],
    #     #         logging=True,
    #     #         level=logging.WARN
    #     #     )
    #     # else:

    sentry = None
    logging_conf = TBG.global_config['LOGGING_CONF']
    basedir = os.path.abspath(os.path.dirname(__file__))
    updir = os.path.dirname(basedir)
    logging_conf['handlers']['access_log_file']['filename'] = os.path.join(
        updir, 'logs', '{}.log'.format(tb_app_name))
    Logger().init_main_logger(logging_conf, sentry_logger=sentry, tb_app_name=tb_app_name)


def create_app(*args, **kwargs):
    print 'create_app'
    tb_app_name = kwargs.get('tb_app_name', '')
    TBG.global_config['tb_app_name'] = tb_app_name
    # logger

    sentry_logger_init(tb_app_name)

    if not TBG.tb_publisher:
        TBG.tb_publisher = TbPublisher()

    if not TBG.tourbillon_db:
        from app.dao.models import db, extra_db
        tourbillon_db = bind_pony_db(flask_app, 'TOURBILLON_DB', dbs=db)
        tourbillon_extra_db = bind_pony_db(flask_app, 'TOURBILLON_EXTRA_DB', dbs=extra_db)
        TBG.tourbillon_db = tourbillon_db
        TBG.tourbillon_extra_db = tourbillon_extra_db
    # mail
    if not TBG.mailer:
        # mail
        from controller.emailer import Mailer
        mailer = Mailer(user=flask_app.config['MAIL_USER'], password=flask_app.config['MAIL_PASSWORD'], server=flask_app.config['MAIL_ADDR'])
        TBG.mailer = mailer

    # redis
    if not TBG.redis_conn:
        from dao.redis_dao import RedisPool
        redis_conn = RedisPool(flask_app.config['REDIS_HOST'], flask_app.config['REDIS_PORT'], flask_app.config['COMMON_REDIS_DB'],
                               flask_app.config["REDIS_PASSWORD"])
        TBG.redis_conn = redis_conn

    # cache
    if not TBG.cache_access_object:
        cache_access_object = CacheAccessObject(flask_app.config['REDIS_HOST'], flask_app.config['REDIS_PORT'], flask_app.config['FLIGHT_FARE_CACHE_REDIS_DB'],
                                                flask_app.config["REDIS_PASSWORD"])
        TBG.cache_access_object = cache_access_object
    if not TBG.config_redis:
        config_redis = RedisPool(flask_app.config['REDIS_HOST'], flask_app.config['REDIS_PORT'], flask_app.config['CONFIG_REDIS_DB'],
                                 flask_app.config["REDIS_PASSWORD"])
        TBG.config_redis = config_redis
    if not TBG.tb_metrics:
        tb_metrics = Metrics(**flask_app.config['METRICS_SETTINGS'])
        tb_metrics.run_async()
        tb_aggr_metrics = Metrics(**flask_app.config['AGGR_METRICS_SETTINGS'])
        tb_aggr_metrics.run_async()
        TBG.tb_metrics = tb_metrics
        TBG.tb_aggr_metrics = tb_aggr_metrics

    # url mapping
    if tb_app_name == 'ota_api':
        from app.api.ota import ota_app
        flask_app.register_blueprint(ota_app, url_prefix='/ota')

        if not TBG.cached_meta:
            # 缓存预热模块
            TBG.cached_meta = True
            from controller.cache_meta import CachedMeta
            CachedMeta.run_async()

        # # 初始化搜索日志的刷子
        # if not TBG.otasearch
        # from api.ota.ctx import OTASearchLogDbWriter
        # OTASearchLogDbWriter.run_async()

    elif tb_app_name == 'web_api':
        from app.api.misc import misc_app
        flask_app.register_blueprint(misc_app, url_prefix='/misc')

    elif tb_app_name == 'provider_api':
        from app.api.provider import provider_app
        flask_app.register_blueprint(provider_app, url_prefix='/provider')

    return flask_app
