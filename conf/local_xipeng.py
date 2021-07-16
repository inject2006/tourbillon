# -*- coding: utf-8 -*-

# 自己的测试环境使用

import os

basedir = os.path.abspath(os.path.dirname(__file__))
updir = os.path.dirname(basedir)

RUN_MODE = 'TEST'  #测试模式
EXCEPTION_HTTP_LOG_OUTPUT = True

LOG_LEVEL ='DEBUG'

FCACHE_TIMEOUT = 10 # OTA redis配置缓存时间

ALLOW_PRINT_HTTP_INFO_IN_TEST = False   # 测试环境下是否自动打印http请求信息

TOURBILLON_DB = dict(
    MYSQL_HOST='localhost',
    MYSQL_PORT=3306,
    MYSQL_USER='root',
    MYSQL_PASSWORD='630131222',
    MYSQL_DB='tourbillon',
    ENABLE=True,
)

TOURBILLON_EXTRA_DB = dict(
    MYSQL_HOST='localhost',
    MYSQL_PORT=3306,
    MYSQL_USER='root',
    MYSQL_PASSWORD='630131222',
    MYSQL_DB='tourbillon',
    ENABLE=True,
)

SENTRY_APP = False
SENTRY_DSN = 'http://bb2b6e5507d347a482fb9e08368a4b17:00a379096c624b818bb814b68c961661@192.168.3.17:9000/7'

REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_PASSWORD = '630131222'
FLIGHT_FARE_CACHE_REDIS_DB = 3
COMMON_REDIS_DB = 4
CONFIG_REDIS_DB = 5

FCACHE_TIMEOUT_FUSING = 3  # 熔断缓存时间
FCACHE_TIMEOUT_FARE_LOW_PRICE_CACHE = 3  # 运价一级缓存时间

# 队列数据配置
TB_EXCHANGE = dict(
    USER = 'tb',
    PASSWORD = 'bigsec123',
    HOST = '139.219.3.173',
    EXCHANGE = 'tb_main',
    ENABLE = True  # 是否开启
)

#proxy 设置

FIX_PROXY_ADDR = 'http://proxy.baibianip.com'
FIX_PROXY_PORT_RANGE_START = 8001
FIX_PROXY_PORT_RANGE_END = 8045
RANDOM_PROXY_ADDR = 'http://proxy.baibianip.com'
RANDOM_PROXY_PORT = 8000

# EXTRACT_PROXY_ADDR = 'http://mapi.baibianip.com/getproxy?type=dymatic&apikey=5fcfed32d9a420b2cbe592e8f73a9fb5&count=120&unique=1&lb=1&format=json&sort=1&resf=1,2'

EXTRACT_PROXY_ADDR_A = 'http://mapi.baibianip.com/getproxy?type=dymatic&apikey=5fcfed32d9a420b2cbe592e8f73a9fb5&count=120&unique=1&lb=1&format=json&sort=1&resf=1,2'
EXTRACT_PROXY_ADDR_B = 'http://api.baibianip.com/api/getproxy?custom=1&count=1&format=json&apikey=5fcfed32d9a420b2cbe592e8f73a9fb5'
# EXTRACT_PROXY_ADDR_C = 'http://webapi.http.zhimacangku.com/getip?num=30&type=2&pro=0&city=0&yys=0&port=11&pack=30353&ts=1&ys=1&cs=1&lb=1&sb=0&pb=45&mr=1&regions='
# EXTRACT_PROXY_ADDR_C = 'http://webapi.http.zhimacangku.com/getip?num=5&type=2&pro=0&city=0&yys=0&port=1&pack=30067&ts=1&ys=1&cs=1&lb=1&sb=0&pb=45&mr=1&regions='
# EXTRACT_PROXY_ADDR_C = 'http://webapi.http.zhimacangku.com/getip?num=5&type=2&pro=0&city=0&yys=0&port=2&pack=30353&ts=1&ys=1&cs=1&lb=1&sb=0&pb=45&mr=1&regions='
# EXTRACT_PROXY_ADDR_C = 'http://webapi.http.zhimacangku.com/getip?num=10&type=2&pro=0&city=0&yys=0&port=1&pack=30067&ts=1&ys=1&cs=1&lb=1&sb=0&pb=45&mr=1&regions='
EXTRACT_PROXY_ADDR_C = 'http://webapi.http.zhimacangku.com/getip?num=2&type=2&pro=0&city=0&yys=0&port=1&pack=33099&ts=1&ys=1&cs=1&lb=1&sb=0&pb=45&mr=1&regions='
# EXTRACT_PROXY_ADDR_D = 'http://mapi.baibianip.com/getproxy?type=dymatic&apikey=aaa3da2e429c21e5514ed1977edf6bc7&count=30&unique=1&lb=1&format=json&sort=0&resf=1,2'
EXTRACT_PROXY_ADDR_D = 'http://api.ip.data5u.com/dynamic/get.html?order=0176a3ac3dbfe89f52d290a5f0c3c544&ttl=1&json=1&sep=3'

# 验证码收发邮箱设置
MAIL_ADDR = 'imap.exmail.qq.com'
MAIL_USER = 'fvck@tongdun.org'
MAIL_PASSWORD ='XrczRNDTBwBRvaPH'

#是否人工支付
ONLY_MANUAL_PAY = False

# 运营联系电话
OPERATION_CONTACT_MOBILE = '13736090908'  # 13736090908 18058592110

# 运营邮箱
OPERATION_CONTACT_EMAIL = '317500476@qq.com'  # 13736090908 18058592110

# 自动化电话
MOBILE_DB = {'18368481562':{'mobile':'18368481562','sms_device_id':'chuizi1','owner':'张荣华','comment':'','sim_id':''},
             '18321259556':{'mobile':'18321259556','sms_device_id':'chuizi1','owner':'罗启武','comment':'暂时被东航封禁','sim_id':''},
             '17891921253':{'mobile':'18321259556','sms_device_id':'xiaomi1','owner':'马云','comment':'','sim_id':'918004280016832'},
            '17891937371':{'mobile':'18321259556','sms_device_id':'xiaomi1','owner':'马云','comment':'','sim_id':'918004280016843'},
                       }
FORAUTOMATIC_MOBILE = {'mobile':'18368481562','sms_device_id':'chuizi1','owner':'张荣华','comment':'','sim_id':''}


# misc 管理系统账号
USER_LIST = {'admin': 'admin', 'sales': 'sales'}


# 路由设置

ROUTER_CONFIG =[
    {
        'ota_name':'lvmama',
        'default_provider':'airasia',
        'default_provider_channel':'airasia_web',  #
        'product_type':2, #
        'trip_type':['OW'], # 只做单程
        'pipeline': []
    },
    {
        'ota_name': 'tongcheng',
        'default_provider': 'ceair',
        'default_provider_channel': 'ceair_web_2',  #
        'auto_product_type': 2,  #
        'trip_type': ['OW'],  # 只做单程
        'pipeline': [{'rules':['350,0|OW|DLC|FNA'],'provider':'pdc','provider_channel':'pdc_web'}]
    },
    {
        'ota_name': 'fakeota',
        'default_provider': 'fakeprovider',
        'default_provider_channel': 'fakeprovider_test',  #
        'product_type': 2,  #
        'trip_type': ['OW'],  #
        'pipeline': [{'rules':['0,0|OW|DLC|FNA'],'provider':'pdc','provider_channel':'pdc_web'}]
    },
    {
        'ota_name': 'tc_policy_wt',
        'default_provider': 'okair',
        'default_provider_channel': 'okair_web',  #
        'product_type': 2,  #
        'trip_type': ['OW'],  #
        'pipeline': []
    }
]

# 运价权重配置
FARE_PR_CONFIG = {
    1: {'reference_time': 24 * 60 * 60},
    2: {'reference_time': 30},
    3: {'reference_time': 20},
    4: {'reference_time': 15},
    5: {'reference_time': 10},
    # 2: {'reference_time': 20},
    # 3: {'reference_time': 15},
    # 4: {'reference_time': 12},
    # 5: {'reference_time': 10},
}

CRAWLER_TASK_EXPIRE_TIME = 30*60

# ota 询价默认配置
OTA_DEFAULT_SEARCH_CONFIG = {
            'search_interface_status':'turn_on',  # 询价接口状态  turn_on 开启 turn_off 关闭
            'switch_mode':'auto',  # manual 手动模式 auto 自动模式
            'is_include_nonworking_day': 0,  # 是否包含节假日 1 包含 0 不包含
            'open_hours': [[6, 20]],  # 每天开启时间,可以包含多个时间段，单位为小时，

            # 业务filter
            'routing_range': ['IN'],  # IN 国内 OUT 国际
            'from_to_routings':[], # 航线 出发地，目的地
            'trip_type':['OW'], # OW 单程 RT 往返
            'cabin_grade': ['Y'], # 舱等 头等：F 商务：C 超经：S 经济： Y
            'within_days': 7, # 查询近多少天内的数据

            # 运价策略
            'adult_price_calc': 10,  # 加减计算 减法需要填写负数
            'child_price_calc': 10,  # 加减计算 减法需要填写负数
        }

METRICS_SETTINGS = {
    "endpoint": "http://metrics.qisec.cn:8086/write?db=tourbillon&u=root&p=Influxdb@2018bigsec&precision=s",
    "flush_interval": 5,
    'enabled':True,  #是否启用metrics记录
    'host':'metrics.qisec.cn',
    'port':8086,
    'user':'root',
    'password':'Influxdb@2018bigsec',
    'db':'tourbillon'
}

AGGR_METRICS_SETTINGS = {
    "endpoint": "http://metrics.qisec.cn:8086/write?db=tourbillon&u=root&p=Influxdb@2018bigsec&rp=search_3h&precision=s",
    "flush_interval": 5,
    'enabled':True,  #是否启用metrics记录
    'host':'metrics.qisec.cn',
    'port':8086,
    'user':'root',
    'password':'Influxdb@2018bigsec',
    'db':'tourbillon'
}


LOGGING_CONF = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '[%(tbasctime)s][%(tb_app_name)s][%(levelname)s][%(sub_level)s][%(request_id)s][%(order_id)s][%(sub_order_id)s][%(frame_id)s][%(ota_name)s][%(provider_channel)s][%(frame_name)s][%(proxy_pool)s]%(message)s',
        },
    },
    'handlers': {
        'access_log_file': {
            'level': LOG_LEVEL,
            'formatter': 'standard',
            'class': 'cloghandler.ConcurrentRotatingFileHandler',
            'filename':  os.path.join(updir, 'logs', 'info.log'),
            'maxBytes': 200 * 1024 * 1024,
            'backupCount': 50,
        },
        'stdout': {
            'class':'logging.StreamHandler',
            'formatter':'standard',
            'level':LOG_LEVEL
        }
    },
    'loggers': {
        'logger_access_log': {
            'handlers': ['stdout','access_log_file'],
            'level': LOG_LEVEL,
            'propagate': False,
        }
    },
}