# -*- coding: utf-8 -*-

# 生产环境

import os

basedir = os.path.abspath(os.path.dirname(__file__))
updir = os.path.dirname(basedir)

RUN_MODE = 'PROD'

DATA_DIR = os.path.join(updir, 'data') # 数据目录

EMULATOR_APPIUM_ADDR = 'http://192.168.1.11:4723/wd/hub'  # 模拟器地址

ALLOW_PRINT_HTTP_INFO_IN_TEST = False   # 测试环境下是否自动打印http请求信息

FCACHE_TIMEOUT = 10 # OTA redis配置缓存时间

FCACHE_TIMEOUT_FUSING = 3  # 熔断缓存时间

FCACHE_TIMEOUT_FARE_LOW_PRICE_CACHE = 3  # 运价一级缓存时间

EXCEPTION_HTTP_LOG_OUTPUT = True  # 是否输出异常记录点http请求日志

LOG_LEVEL ='INFO'

# 队列数据配置

TB_EXCHANGE = dict(
    USER = 'tb',
    PASSWORD = 'bigsec123',
    HOST = '10.0.12.11',
    EXCHANGE = 'tb_main',
    ENABLE = True  # 是否开启
)

# 内网
TOURBILLON_DB = dict(
    MYSQL_HOST='10.0.12.10',
    MYSQL_PORT=3306,
    MYSQL_USER='tourbillondba',
    MYSQL_PASSWORD='tourbillon@2018',
    MYSQL_DB='tourbillon',
    ENABLE=True
)

# 内网
TOURBILLON_EXTRA_DB = dict(
    MYSQL_HOST='10.0.12.11',
    MYSQL_PORT=3306,
    MYSQL_USER='tourbillondba',
    MYSQL_PASSWORD='tourbillon@2018',
    MYSQL_DB='tourbillon_extra_db',
    ENABLE=True
)

# aliyun
SENTRY_APP = False
SENTRY_DSN = 'http://553b657175b744cea4797e0b43c1db7f:518c76bcfa5847759e87e8bbc5e80832@139.224.135.124:9000/14'


# 猫池回调url
SMS_RECIEVER_URL = 'http://misc.tourbillon.qisec.cn:9801/misc/sms_reciever'
SMS_HEARTBEAT_URL = 'http://misc.tourbillon.qisec.cn:9801/misc/sms_heartbeat'

# 内网
CELERY_BROKER_URL = 'redis://:ZIDZGPZPYpd6nTk2zCwLni3K1zvd2ChPkztTcO1HsnM=@10.0.13.138:6379/1'
CELERY_RESULT_BACKEND = 'redis://:ZIDZGPZPYpd6nTk2zCwLni3K1zvd2ChPkztTcO1HsnM=@10.0.13.138:6379/2'
CELERY_DEFAULT_QUEUE = 'gearset_queue'
CELERY_PASSWORD = 'ZIDZGPZPYpd6nTk2zCwLni3K1zvd2ChPkztTcO1HsnM='
CELERY_QUEUE_DB = 1


REDIS_HOST = '10.0.13.138'
REDIS_PORT = 6379
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
EXTRACT_PROXY_ADDR_C = 'http://webapi.http.zhimacangku.com/getip?num=2&type=2&pro=0&city=0&yys=0&port=1&pack=33099&ts=1&ys=1&cs=1&lb=1&sb=0&pb=45&mr=1&regions='
EXTRACT_PROXY_ADDR_D = 'http://api.ip.data5u.com/dynamic/get.html?order=0176a3ac3dbfe89f52d290a5f0c3c544&ttl=1&json=1&sep=3'
EXTRACT_PROXY_ADDR_F = 'http://http.tiqu.qingjuhe.cn/getip?num=5&type=2&pro=0&city=0&yys=0&port=11&pack=28520&ts=1&ys=0&cs=0&lb=1&sb=0&pb=5&mr=0&regions=110000,310000,320000,330000,420000,430000'

# 验证码收发邮箱设置
MAIL_ADDR = 'imap.exmail.qq.com'
# MAIL_USER = 'fvck@tongdun.org'
# MAIL_PASSWORD ='XrczRNDTBwBRvaPH'

MAIL_USER = 'ak47@btbvs.com'
MAIL_PASSWORD ='luoaQQQWoyy02147'

#是否人工支付
ONLY_MANUAL_PAY = True

# 运营联系电话
# OPERATION_CONTACT_MOBILE = '18321259556'  # 13736090908 18058592110
# OPERATION_CONTACT_MOBILE = '17891933179'  # 13736090908 18058592110
OPERATION_CONTACT_MOBILE = '18368481562'

# 运营邮箱
OPERATION_CONTACT_EMAIL = '317500476@qq.com'  # 13736090908 18058592110


# misc 管理系统账号
# 易达 裘佳琳 、 徐倩倩 、 费叶 、 胡建辉 、麻顺捷、王静、阚萍
# 易悠 周巧，韦盛，熊燕，曾帅，龚蕾蕾
# 'zhouqiao','weisheng','xiongyan','zengshuai','gongleilei'

GROUP_PERM = {
    'admin':{'order_view':{'providers':['*'],'otas':['*']},'misc_api':['flight_order','sub_order','manual_booking','income_expense_detail','sys_control','fusing_repo','manual_create_sub_order','ota_config','order_details','order_list','flight_bill','order_modify','order_search','ota_verify','tb_sms','pdc_policy_config']}, # 管理账号
'yidayiyou':{'order_view':{'providers':['ceair','ch', 'donghaiair', 'okair'],'otas':['lvmama','tongcheng']},'misc_api':['flight_order','sub_order','manual_booking','income_expense_detail', 'order_list', 'order_details', 'order_modify']}, # 运营账号
'yida':{'order_view':{'providers':['ceair','ch', 'donghaiair', 'okair'],'otas':['lvmama','tongcheng']},'misc_api':['flight_order','sub_order','manual_booking','income_expense_detail', 'order_list', 'order_details', 'order_modify', 'order_search']}, # 运营账号
'yiyou':{'order_view':{'providers':['ceair','ch', 'donghaiair', 'okair'],'otas':['lvmama','tongcheng']},'misc_api':['flight_order','sub_order','manual_booking','income_expense_detail', 'order_list', 'order_details', 'order_modify', 'order_search']}, # 运营账号
'wantu':{'order_view':{'providers':['*'],'otas':['tc_policy_wt']},'misc_api':['flight_order','sub_order','income_expense_detail']}, # 运营账号
'test':{'order_view':{'providers':['*'],'otas':['*']},'misc_api':['flight_order','sub_order','manual_booking']}, # 测试账号
    'nb_op': {'order_view': {'providers': ['*'], 'otas': ['*']},
              'misc_api': ['flight_order', 'sub_order', 'manual_booking', 'income_expense_detail', 'sys_control', 'fusing_repo', 'manual_create_sub_order', 'ota_config', 'order_details', 'order_list',
                           'flight_bill', 'order_modify', 'order_search', 'tb_sms']},  # 管理账号
}


# misc 管理系统账号
USER_LIST = {'admin': {'group':'admin','password':'bigsec@2018'},
 'yida2018': {'group':'yidayiyou','password':'907N3Gsk2YvF'},
'qiujialin': {'group':'yidayiyou','password':'7EMiIeQOmw4B'},
'xuqianqian': {'group':'yidayiyou','password':'WoI75AX9V3cy'},
'feiye': {'group':'yidayiyou','password':'a7QxDwWXZ3tB'},
'hujianhui': {'group':'yidayiyou','password':'QbrnwhueG24i'},
'mashunjie': {'group':'yidayiyou','password':'jHgPSMCbKZUL'},
'wangjing': {'group':'yidayiyou','password':'A20xPKO8rkGR'},
'kanping': {'group':'yidayiyou','password':'nDKYoTH27J4V'},
'zhouqiao': {'group':'yidayiyou','password':'O4lFQ8UfoRa3'},
'weisheng': {'group':'yidayiyou','password':'ptNZYHmkdSyl'},
'xiongyan': {'group':'yidayiyou','password':'uNQaWgJKik7v'},
'zengshuai': {'group':'yidayiyou','password':'5uzMsVhNI67g'},
'gongleilei': {'group':'yidayiyou','password':'k3PMlhJbu8z1'},
'suishiying': {'group':'yidayiyou','password':'SQM4Pw7GnjCr'},
'wantu': {'group':'wantu','password':'PyYLojCHub7E'},
'tb-yida': {'group': 'yida', 'password': '8cBFNYVnE5H7'},
'tb-yiyou': {'group': 'yiyou', 'password': '256NJl8BmYSd'},
'amxku': {'group': 'admin', 'password': 'tourbillon@amxku'},
'xm.shi': {'group': 'admin', 'password': 'tourbillon@shixiaomin'},
'jj.ma': {'group': 'admin', 'password': 'tourbillon@majj'},
'aq.lin': {'group': 'nb_op', 'password': 'tourbillon@aqlin'},
'qq.jiang': {'group': 'nb_op', 'password': 'tourbillon@qq.jiang'}
}

# 路由设置
ROUTER_CONFIG =[
    {
        'ota_name':'lvmama',
        'default_provider':'ceair',
        'default_provider_channel':'ceair_web_2',  #
        'product_type':2, #
        'trip_type':['OW'], # 只做单程
        'pipeline': [{'rules':['360,0|OW|HRB|FMA'],'provider':'pdc','provider_channel':'pdc_web'}]
    },
    {
        'ota_name': 'tongcheng',
        'default_provider': 'ceair',
        'default_provider_channel': 'ceair_web_2',  #
        'auto_product_type': 2,  #
        'trip_type': ['OW'],  # 只做单程
        'pipeline': [{'rules':['350,0|OW|HRB|FMA'],'provider':'pdc','provider_channel':'pdc_web'}]
    },
    {
        'ota_name': 'fakeota',
        'default_provider': 'donghaiair',
        'default_provider_channel': 'donghaiair_web',  #
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
        'default_provider': 'ceair',
        'default_provider_channel': 'ceair_web_2',  #
        'product_type': 2,  #
        'trip_type': ['OW'],  #
        'pipeline': [{'rules':['350,0|OW|HRB|FMA'],'provider':'pdc','provider_channel':'pdc_web'}]
    }
]

CACHE_PR_CONFIG = {
    1: {'cabin_expired_time': 3600 * 12, 'cabin_attenuation': 3, 'fare_expired_time': 86400 * 30},
    2: {'cabin_expired_time': 3600 * 3, 'cabin_attenuation': 2, 'fare_expired_time': 86400 * 20},
    3: {'cabin_expired_time': 60 * 60 * 1.5, 'cabin_attenuation': 1, 'fare_expired_time': 86400 * 10},
    4: {'cabin_expired_time': 60 * 60, 'cabin_attenuation': 1, 'fare_expired_time': 86400 * 5},
    5: {'cabin_expired_time': 60 * 30, 'cabin_attenuation': 0, 'fare_expired_time': 86400},

}

# 运价权重配置
CRAWLER_PR_CONFIG = {

    1: {'reference_time': 86400 * 4},
    2: {'reference_time': 86400 * 2},
    3: {'reference_time': 86400},
    4: {'reference_time': 43200},
    5: {'reference_time': 28800},
}

CRAWLER_TASK_EXPIRE_TIME = 24*60*60


METRICS_SETTINGS = {
    "endpoint": "http://metrics.qisec.cn:8086/write?db=tourbillon&u=root&p=Influxdb@2018bigsec",
    "flush_interval": 5,
    'enabled':True,  #是否启用metrics记录
    'host':'metrics.qisec.cn',
    'port':8086,
    'user':'root',
    'password':'Influxdb@2018bigsec',
    'db':'tourbillon'
}

AGGR_METRICS_SETTINGS = {
    "endpoint": "http://metrics.qisec.cn:8086/write?db=tourbillon&u=root&p=Influxdb@2018bigsec&rp=search_3h",
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
