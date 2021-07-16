# -*- coding: utf-8 -*-

# 自己的测试环境使用

import os

basedir = os.path.abspath(os.path.dirname(__file__))
updir = os.path.dirname(basedir)


RUN_MODE = 'TEST'  #测试模式

DATA_DIR = os.path.join(updir, 'data') # 数据目录

EMULATOR_APPIUM_ADDR = 'http://127.0.0.1:4723/wd/hub'  # 模拟器地址

ALLOW_PRINT_HTTP_INFO_IN_TEST = False   # 测试环境下是否自动打印http请求信息

FCACHE_TIMEOUT = 10 # OTA redis配置缓存时间

FCACHE_TIMEOUT_FUSING = 3  # 熔断缓存时间

FCACHE_TIMEOUT_FARE_LOW_PRICE_CACHE = 3  # 运价一级缓存时间

EXCEPTION_HTTP_LOG_OUTPUT = True  # 是否输出异常记录点http请求日志

LOG_LEVEL ='INFO'

# # 队列数据配置
# TB_EXCHANGE = dict(
#     USER = 'guest',
#     PASSWORD = 'guest',
#     HOST = '42.159.91.248',
#     EXCHANGE = 'tb_main',
#     ENABLE = True  # 是否开启
# )

# 队列数据配置
TB_EXCHANGE = dict(
    USER = 'tb',
    PASSWORD = 'bigsec123',
    HOST = '139.219.3.173',
    EXCHANGE = 'tb_main',
    ENABLE = True  # 是否开启
)

TOURBILLON_DB = dict(
    MYSQL_HOST='localhost',
    MYSQL_PORT=3306,
    MYSQL_USER='root',
    MYSQL_PASSWORD='111111',
    MYSQL_DB='tourbillon',
    ENABLE=True
)

TOURBILLON_EXTRA_DB = dict(
    MYSQL_HOST='localhost',
    MYSQL_PORT=3306,
    MYSQL_USER='root',
    MYSQL_PASSWORD='111111',
    MYSQL_DB='tourbillon',
    ENABLE=True
)

# 生产
TOURBILLON_DB = dict(
    MYSQL_HOST='139.219.6.161',
    MYSQL_PORT=3306,
    MYSQL_USER='tourbillondba',
    MYSQL_PASSWORD='tourbillon@2018',
    MYSQL_DB='tourbillon',
    ENABLE=True
)


TOURBILLON_EXTRA_DB = dict(
    MYSQL_HOST='139.219.3.173',
    MYSQL_PORT=3306,
    MYSQL_USER='tourbillondba',
    MYSQL_PASSWORD='tourbillon@2018',
    MYSQL_DB='tourbillon_extra_db',
    ENABLE=True
)

SENTRY_APP = False
SENTRY_DSN = 'http://bb2b6e5507d347a482fb9e08368a4b17:00a379096c624b818bb814b68c961661@192.168.3.17:9000/7'

REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_PASSWORD = ''
FLIGHT_FARE_CACHE_REDIS_DB = 3
COMMON_REDIS_DB = 4
CONFIG_REDIS_DB = 5

# 生产
REDIS_HOST = '42.159.91.248'
REDIS_PORT = 26371
REDIS_PASSWORD = 'ZIDZGPZPYpd6nTk2zCwLni3K1zvd2ChPkztTcO1HsnM='
FLIGHT_FARE_CACHE_REDIS_DB = 3
COMMON_REDIS_DB = 4
CONFIG_REDIS_DB = 5

#普通proxy 设置

FIX_PROXY_ADDR = 'http://s3.proxy.baibianip.com'
FIX_PROXY_PORT_RANGE_START = 8001
FIX_PROXY_PORT_RANGE_END = 8045
RANDOM_PROXY_ADDR = 'http://s3.proxy.baibianip.com'
RANDOM_PROXY_PORT = 8000

EXTRACT_PROXY_ADDR_A = 'http://mapi.baibianip.com/getproxy?type=dymatic&apikey=5fcfed32d9a420b2cbe592e8f73a9fb5&count=120&unique=1&lb=1&format=json&sort=1&resf=1,2'
EXTRACT_PROXY_ADDR_B = 'http://api.baibianip.com/api/getproxy?custom=1&count=1&format=json&apikey=5fcfed32d9a420b2cbe592e8f73a9fb5'
EXTRACT_PROXY_ADDR_C = 'http://webapi.http.zhimacangku.com/getip?num=3&type=2&pro=0&city=0&yys=0&port=1&pack=33099&ts=1&ys=1&cs=1&lb=1&sb=0&pb=45&mr=1&regions='
EXTRACT_PROXY_ADDR_D = 'http://api.ip.data5u.com/dynamic/get.html?order=0176a3ac3dbfe89f52d290a5f0c3c544&ttl=1&json=1&sep=3'

# 猫池回传短信接口

SMS_RECIEVER_URL = 'http://misc.tourbillon.qisec.cn:9801/misc/sms_reciever'
SMS_HEARTBEAT_URL = 'http://misc.tourbillon.qisec.cn:9801/misc/sms_heartbeat'

# 验证码收发邮箱设置
MAIL_ADDR = 'pop.exmail.qq.com'
MAIL_USER = 'fvck@tongdun.org'
MAIL_PASSWORD ='XrczRNDTBwBRvaPH'

# MAIL_USER = 'ak47@btbvs.com'
# MAIL_PASSWORD ='luoaQQQWoyy02147'

#是否人工支付
ONLY_MANUAL_PAY = True

CRAWLER_TASK_EXPIRE_TIME = 24*60*60

# 运价权重配置
CRAWLER_PR_CONFIG = {

    1: {'reference_time': 86400 * 4},
    2: {'reference_time': 86400 * 2},
    3: {'reference_time': 86400},
    4: {'reference_time': 43200},
    5: {'reference_time': 28800},
}


GROUP_PERM = {
    'admin':{'order_view':{'providers':['*'],'otas':['*']},'misc_api':['flight_order','sub_order','manual_booking','income_expense_detail','sys_control','fusing_repo','manual_create_sub_order','ota_config','pdc_policy_config']}, # 管理账号
'yidayiyou':{'order_view':{'providers':['ceair','ch'],'otas':['lvmama','tongcheng']},'misc_api':['flight_order','sub_order','manual_booking','income_expense_detail']}, # 运营账号
'wantu':{'order_view':{'providers':['okair'],'otas':['tc_policy_wt']},'misc_api':['flight_order','sub_order','income_expense_detail']}, # 运营账号
'test':{'order_view':{'providers':['*'],'otas':['*']},'misc_api':['flight_order','sub_order','manual_booking']}, # 测试账号
}


# misc 管理系统账号
USER_LIST = {'admin': {'group':'admin','password':'bigsec@2018'},
 'yida2018': {'group':'yidayiyou','password':'yida2018'},
'qiujialin': {'group':'yidayiyou','password':'yida2018'},
'xuqianqian': {'group':'yidayiyou','password':'yida2018'},
'feiye': {'group':'yidayiyou','password':'yida2018'},
'hujianhui': {'group':'yidayiyou','password':'yida2018'},
'mashunjie': {'group':'yidayiyou','password':'yida2018'},
'wangjing': {'group':'yidayiyou','password':'yida2018'},
'kanping': {'group':'yidayiyou','password':'yida2018'},
 'zhouqiao': {'group':'yidayiyou','password':'yiyou2018'},
'weisheng': {'group':'yidayiyou','password':'yiyou2018'},
'xiongyan': {'group':'yidayiyou','password':'yiyou2018'},
'zengshuai': {'group':'yidayiyou','password':'yiyou2018'},
'gongleilei': {'group':'yidayiyou','password':'yiyou2018'},
'wantu': {'group':'wantu','password':'wantuwantu'}
}
# 运营联系电话
OPERATION_CONTACT_MOBILE = '13736090908'  # 13736090908 18058592110

# 运营邮箱
OPERATION_CONTACT_EMAIL = '317500476@qq.com'  # 13736090908 18058592110


# 测试
METRICS_SETTINGS = {
    "endpoint": "http://139.217.134.187:8086/write?db=tourbillon_test&u=tourbillon_test&p=123456",
    "flush_interval": 5,
    'enabled':True,  #是否启用metrics记录
    'host':'139.217.134.187',
    'port':8086,
    'user':'root',
    'password':'Influxdb@2018bigsec',
    'db':'tourbillon'
}

AGGR_METRICS_SETTINGS = {
    "endpoint": "http://139.217.134.187:8086/write?db=tourbillon_test&u=tourbillon_test&p=123456&rp=search_3h",
    "flush_interval": 5,
    'enabled':True,  #是否启用metrics记录
    'host':'139.217.134.187',
    'port':8086,
    'user':'root',
    'password':'Influxdb@2018bigsec',
    'db':'tourbillon'
}

# 生产
METRICS_SETTINGS = {
    "endpoint": "http://139.219.0.115:8086/write?db=tourbillon&u=root&p=Influxdb@2018bigsec",
    "flush_interval": 5,
    'enabled':True,  #是否启用metrics记录
    'host':'139.219.0.115',
    'port':8086,
    'user':'root',
    'password':'Influxdb@2018bigsec',
    'db':'tourbillon'
}

AGGR_METRICS_SETTINGS = {
    "endpoint": "http://139.219.0.115:8086/write?db=tourbillon&u=root&p=Influxdb@2018bigsec&rp=search_3h",
    "flush_interval": 5,
    'enabled':True,  #是否启用metrics记录
    'host':'139.219.0.115',
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

