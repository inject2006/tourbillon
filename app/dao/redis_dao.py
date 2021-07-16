#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, too-many-arguments, broad-except, anomalous-backslash-in-string
# pylint: disable=missing-docstring, line-too-long, too-few-public-methods
"""
# @Time    : 2016-11-24
# @Author  : wxt
# @File    : dao.py
# @Function: 数据库操作模块
# @Software: PyCharm
"""

import hashlib
import json
import redis
import zlib
from gevent import socket as gsocket
import redis.connection

redis.connection.socket = gsocket

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET


class RedisPool(object):
    """
    封装cicp_redis数据库操作
    """

    def __init__(self, redis_host, redis_port, db=0, password=None):
        """
        :param redis_host: [string] redis服务器地址
        :param redis_port: [string] redis服务器端口
        :return: [object]
        """

        if password:
            cache_redis_db = redis.ConnectionPool(host=redis_host, port=redis_port, db=db, password=password)
        else:
            cache_redis_db = redis.ConnectionPool(host=redis_host, port=redis_port, db=db)
        # connection_pool warden's redis
        self.redis_pool = redis.StrictRedis(connection_pool=cache_redis_db)

    @classmethod
    def get_instance(cls, *args, **kw):
        """
        CicpRedisPool 单例对象
        """
        if not hasattr(cls, '_instance'):
            cls._instance = cls(*args, **kw)
        return cls._instance

    def test_connect(self):
        """
        测试redis连通性
        :return: [bool] 是否连通
        """
        if "Error" in self.redis_pool.info():
            return False
        return True

    def get_value(self, key):
        """
        查询key
        :param key:
        :return: [string] value
        """
        return self.redis_pool.get(key)

    def mget_value(self, key):
        """
        查询多个key
        :param key:
        :return: [list] value
        """
        return self.redis_pool.mget(key)

    def insert_value(self, key, value, ex=None, px=None):
        """
        插入键值对
        :param key:
        :param value:
        :return: [bool] 插入结果
        """
        res = self.redis_pool.set(key, value, ex=ex, px=px)
        if res:
            return True
        return False

    def incr_value(self, key, value=1):
        """
        插入键值对
        :param key:
        :param value:
        :return: [bool] 插入结果
        """
        res = self.redis_pool.incr(key, value)
        if res:
            return True
        return False

    def get_and_insert(self, key, value):
        """
        查找并插入键值对
        :param key:
        :param value:
        :return: [string] 查询到的value
        """
        res = self.get_value(key)
        if res is None:
            self.insert_value(key, value)
        return res

    def get_values(self, prefix):
        """
        根据前缀查询符合条件的keys
        :param prefix:
        :return: [list] value
        """
        pipe = self.redis_pool.pipeline()
        key_list = []

        for key in self.redis_pool.scan_iter(match='%s*' % prefix):
            key_list.append(key)
            pipe.get(key)
        return {x: y for x, y in zip(key_list, pipe.execute())}

    def get_internal_pool(self):
        """
        返回内部封装的redis连接池.

        :return:
        """
        return self.redis_pool


class CacheAccessObject(object):
    """
    继承Redis的三方接口缓存层
    :缓存key格式   cache_provider_hash(params_dict)
    :缓存value格式   字符串直接存储，JSON则进行dumps后存储
    """

    def __init__(self, cache_host, cache_port, db=0, password=None):
        self.rp = RedisPool(redis_host=cache_host, redis_port=cache_port, db=db, password=password)
        self.expired_time = None  # 默认缓存时间 单位：秒

    @staticmethod
    def _data_serialize(data, is_compress):
        """
        根据不同的情况将数据序列化成字符串
        :param data:
        :return:
        """

        # TODO: 中文问题处理
        if isinstance(data, dict) or isinstance(data, list):
            if is_compress:
                return zlib.compress(json.dumps(data))
            else:
                return json.dumps(data)
        elif isinstance(data, str) or isinstance(data, unicode):
            if is_compress:
                return zlib.compress(data)
            else:
                return data

    @staticmethod
    def _data_deserialize(data, is_decompress):
        """
        根据不同的情况将数据反序列化成字符串
        :param data:
        :return:
        """

        # TODO: 中文问题处理
        if data is not None:
            if is_decompress:
                try:
                    return json.loads(zlib.decompress(data))
                except Exception as e:
                    try:
                        return zlib.decompress(data)
                    except Exception as e:
                        return json.loads(data)
            else:
                try:
                    return json.loads(data)
                except Exception as e:
                    return data
        else:
            return None

    def hash(self, param_model):
        keys = [k for k, v in param_model.iteritems()]
        keys.sort()
        data = '|'.join([param_model[k] if param_model[k] else '' for k in keys])
        if isinstance(data, unicode):
            data = data.encode('utf-8')
        m = hashlib.sha256()
        m.update(data)
        sha = m.hexdigest()
        return sha

    def get(self, cache_type, provider, param_model, is_decompress=False):
        """

        :param version: 接口版本
        :param param_model: 查询参数model
        :param provider: 厂商
        :return:
        """

        qhash = self.hash(param_model)

        cache_key = '%s_%s_%s' % (cache_type, provider, qhash)
        raw = self.rp.get_value(cache_key)
        return CacheAccessObject._data_deserialize(raw,is_decompress=is_decompress)

    def insert(self, cache_type, provider, param_model, ret_data, expired_time=None, is_compress=False):
        if expired_time is None:  # 如果过期时间为空，则采用默认时间
            expired_time = self.expired_time
        qhash = self.hash(param_model)
        cache_key = '%s_%s_%s' % (cache_type, provider, qhash)
        data = CacheAccessObject._data_serialize(ret_data, is_compress)
        self.rp.insert_value(cache_key, data, ex=expired_time)
