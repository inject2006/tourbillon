# -*- coding: utf-8 -*-

# 自己的测试环境使用

import os

basedir = os.path.abspath(os.path.dirname(__file__))
updir = os.path.dirname(basedir)


RUN_MODE = 'TEST'  #测试模式

DATA_DIR = os.path.join(updir, 'data') # 数据目录

EMULATOR_APPIUM_ADDR = 'http://192.168.1.11:4723/wd/hub'  # 模拟器地址

ALLOW_PRINT_HTTP_INFO_IN_TEST = False   # 测试环境下是否自动打印http请求信息

FCACHE_TIMEOUT = 10 # OTA redis配置缓存时间

FCACHE_TIMEOUT_FUSING = 3  # 熔断缓存时间

FCACHE_TIMEOUT_FARE_LOW_PRICE_CACHE = 3  # 运价一级缓存时间

LOG_LEVEL ='DEBUG'

EXCEPTION_HTTP_LOG_OUTPUT = True  # 是否输出异常记录点http请求日志

# 队列数据配置
TB_EXCHANGE = dict(
    USER = 'guest',
    PASSWORD = 'guest',
    HOST = '10.0.12.9',
    EXCHANGE = 'tb_main',
    ENABLE = True  # 是否开启
)


# 生产环境的数据库，库不同
TOURBILLON_DB = dict(
    MYSQL_HOST='10.0.12.10',
    MYSQL_PORT=3306,
    MYSQL_USER='tourbillon_test',
    MYSQL_PASSWORD='ne#@(<$D1',
    MYSQL_DB='tourbillon_test',
    ENABLE=True
)

# 生产环境数据库，库不同
TOURBILLON_EXTRA_DB = dict(
    MYSQL_HOST='10.0.12.11',
    MYSQL_PORT=3306,
    MYSQL_USER='tourbillon_test',
    MYSQL_PASSWORD='ne#@(<$D1',
    MYSQL_DB='tourbillon_extra_db_test',
    ENABLE=True
)

SENTRY_APP = False
SENTRY_DSN = 'http://bb2b6e5507d347a482fb9e08368a4b17:00a379096c624b818bb814b68c961661@192.168.3.17:9000/7'

REDIS_HOST = '10.0.12.9'
REDIS_PORT = 6379
REDIS_PASSWORD = 'Redis@2018bigsec'
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

# 猫池回传短信接口

SMS_RECIEVER_URL = 'http://10.0.12.9:9801/misc/sms_reciever'
SMS_HEARTBEAT_URL = 'http://10.0.12.9:9801/misc/sms_heartbeat'

# 验证码收发邮箱设置
MAIL_ADDR = 'pop.exmail.qq.com'
MAIL_USER = 'fvck@tongdun.org'
MAIL_PASSWORD ='XrczRNDTBwBRvaPH'

# MAIL_USER = 'ak47@btbvs.com'
# MAIL_PASSWORD ='luoaQQQWoyy02147'

#是否人工支付
ONLY_MANUAL_PAY = True



GROUP_PERM = {
    'admin':{'order_view':{'providers':['*'],'otas':['*']},'misc_api':['flight_order','sub_order','manual_booking','income_expense_detail','sys_control','fusing_repo','manual_create_sub_order','ota_config','order_details','order_list','flight_bill','pdc_policy_config']}, # 管理账号
'yidayiyou':{'order_view':{'providers':['ceair','ch'],'otas':['lvmama','tongcheng']},'misc_api':['flight_order','sub_order','manual_booking','income_expense_detail']}, # 运营账号
'wantu':{'order_view':{'providers':['okair'],'otas':['tc_policy_wt']},'misc_api':['flight_order','sub_order','income_expense_detail']}, # 运营账号
'test':{'order_view':{'providers':['*'],'otas':['*']},'misc_api':['flight_order','sub_order','manual_booking']}, # 测试账号
}


# misc 管理系统账号
USER_LIST = {'admin': {'group':'admin','password':'bigsec@2018'}}
# 运营联系电话
OPERATION_CONTACT_MOBILE = '13736090908'  # 13736090908 18058592110

# 运营邮箱
OPERATION_CONTACT_EMAIL = '317500476@qq.com'  # 13736090908 18058592110


# 路由设置
ROUTER_CONFIG =[
    {
        'ota_name':'lvmama',
        'default_provider':'okair',
        'default_provider_channel':'okair_web',  #
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
    },
    {
        'ota_name': 'ceair_test_fake_pay',
        'default_provider': 'ceair',
        'default_provider_channel': 'ceair_web_2_fake',  #
        'product_type': 2,  #
        'trip_type': ['OW'],  #
        'pipeline': []
    },
    {
        'ota_name': 'tuniu',
        'default_provider': 'fakeprovider',
        'default_provider_channel': 'fakeprovider_test',  #
        'product_type': 2,  #
        'trip_type': ['OW'],  #
        'pipeline': []
    }
]
# 运价权重配置
CRAWLER_PR_CONFIG = {
    1:{'reference_time':86400*5},
    2:{'reference_time':86400*1},
    3:{'reference_time':3600*5},
    4:{'reference_time':3600},
    5:{'reference_time':600},
}


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
    "endpoint": "http://139.217.134.187:8086/write?db=tourbillon_test&u=root&p=1qaz9ol.&precision=s",
    "flush_interval": 5,
    'enabled':True,  #是否启用metrics记录
    'host':'10.100.0.7',
    'port':8086,
    'user':'root',
    'password':'1qaz9ol.',
    'db':'tourbillon_test'
}

AGGR_METRICS_SETTINGS = {
    "endpoint": "http://139.217.134.187:8086/write?db=tourbillon_test&u=root&p=1qaz9ol.&rp=search_3h&precision=s",
    "flush_interval": 5,
    'enabled':True,  #是否启用metrics记录
    'host':'10.100.0.7',
    'port':8086,
    'user':'root',
    'password':'1qaz9ol.',
    'db':'tourbillon_test'
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