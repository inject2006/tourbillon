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

EXCEPTION_HTTP_LOG_OUTPUT = True  # 是否输出异常记录点http请求日志

# 队列数据配置
TB_EXCHANGE = dict(
    USER = 'tb',
    PASSWORD = 'bigsec123',
    HOST = '139.219.3.173',
    EXCHANGE = 'tb_main',
    ENABLE = False  # 是否开启
)


# 内网
TOURBILLON_DB = dict(
    MYSQL_HOST='10.0.13.138',
    MYSQL_PORT=3306,
    MYSQL_USER='tourbillondba',
    MYSQL_PASSWORD='tourbillon@2018',
    MYSQL_DB='tourbillon',
    ENABLE=False
)

# 内网
TOURBILLON_EXTRA_DB = dict(
    MYSQL_HOST='10.0.12.11',
    MYSQL_PORT=3306,
    MYSQL_USER='tourbillondba',
    MYSQL_PASSWORD='tourbillon@2018',
    MYSQL_DB='tourbillon_extra_db',
    ENABLE=False
)

# aliyun
SENTRY_APP = False
SENTRY_DSN = 'http://553b657175b744cea4797e0b43c1db7f:518c76bcfa5847759e87e8bbc5e80832@139.224.135.124:9000/14'


# 猫池回调url
SMS_RECIEVER_URL = 'http://misc.tourbillon.qisec.cn:9801/misc/sms_reciever'
SMS_HEARTBEAT_URL = 'http://misc.tourbillon.qisec.cn:9801/misc/sms_heartbeat'

# 内网
CELERY_BROKER_URL = 'redis://:ZIDZGPZPYpd6nTk2zCwLni3K1zvd2ChPkztTcO1HsnM=@42.159.91.248:26371/1'
CELERY_RESULT_BACKEND = 'redis://:ZIDZGPZPYpd6nTk2zCwLni3K1zvd2ChPkztTcO1HsnM=@42.159.91.248:26371/2'
CELERY_DEFAULT_QUEUE = 'gearset_queue'
CELERY_PASSWORD = 'ZIDZGPZPYpd6nTk2zCwLni3K1zvd2ChPkztTcO1HsnM='
CELERY_QUEUE_DB = 1


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
EXTRACT_PROXY_ADDR_C = 'http://webapi.http.zhimacangku.com/getip?num=2&type=2&pro=0&city=0&yys=0&port=1&pack=33099&ts=1&ys=1&cs=1&lb=1&sb=0&pb=45&mr=1&regions='
EXTRACT_PROXY_ADDR_D = 'http://api.ip.data5u.com/dynamic/get.html?order=0176a3ac3dbfe89f52d290a5f0c3c544&ttl=1&json=1&sep=3'


# 验证码收发邮箱设置
MAIL_ADDR = 'imap.exmail.qq.com'
MAIL_USER = 'fvck@tongdun.org'
MAIL_PASSWORD ='XrczRNDTBwBRvaPH'

# MAIL_USER = 'ak47@btbvs.com'
# MAIL_PASSWORD ='luoaQQQWoyy02147'

#是否人工支付
ONLY_MANUAL_PAY = True

# 运营联系电话
OPERATION_CONTACT_MOBILE = '13736090908'  # 13736090908 18058592110

# 运营邮箱
OPERATION_CONTACT_EMAIL = '317500476@qq.com'  # 13736090908 18058592110


# misc 管理系统账号
# 易达 裘佳琳 、 徐倩倩 、 费叶 、 胡建辉 、麻顺捷、王静、阚萍
# 易悠 周巧，韦盛，熊燕，曾帅，龚蕾蕾
# 'zhouqiao','weisheng','xiongyan','zengshuai','gongleilei'

GROUP_PERM = {
    'admin':{'order_view':{'providers':['*'],'otas':['*']},'misc_api':['flight_order','sub_order','manual_booking','income_expense_detail','sys_control']}, # 管理账号
'yidayiyou':{'order_view':{'providers':['ceair','ch', 'donghaiair', 'okair'],'otas':['lvmama','tongcheng']},'misc_api':['flight_order','sub_order','manual_booking','income_expense_detail']}, # 运营账号
'wantu':{'order_view':{'providers':['*'],'otas':['tc_policy_wt']},'misc_api':['flight_order','sub_order','income_expense_detail']}, # 运营账号
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
'suishiying': {'group':'yidayiyou','password':'yiyou2018'},
'wantu': {'group':'wantu','password':'wantuwantu'}
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

# 运价权重配置
CRAWLER_PR_CONFIG = {
    # 1:{'reference_time':86400*5*3},
    # 2:{'reference_time':86400*1*3},
    # 3:{'reference_time':3600*5*3},
    # 4:{'reference_time':3600*3},
    # 5:{'reference_time':600*3},

    # 1: {'reference_time': 24 * 60 * 60},
    # 2: {'reference_time': 4 * 60 * 60},
    # 3: {'reference_time': 30 * 60},
    # 4: {'reference_time': 24 * 60},
    # 5: {'reference_time': 20 * 60},

    1: {'reference_time': 86400 * 15},
    2: {'reference_time': 86400 * 10},
    3: {'reference_time': 86400 * 5},
    4: {'reference_time': 86400 * 2},
    5: {'reference_time': 86400},
}

CRAWLER_TASK_EXPIRE_TIME = 24*60*60


# ota 询价配置 临时配置
OTA_SEARCH_CONFIG = {
            'search_interface_status':'turn_on',  # 询价接口状态  turn_on 开启 turn_off 关闭
            'switch_mode':'manual',  # manual 手动模式 auto 自动模式
            'is_include_nonworking_day': 0,  # 是否包含节假日 1 包含 0 不包含
            'open_hours': [[6, 20]],  # 每天开启时间,可以包含多个时间段，单位为小时，

            # 业务filter
            'routing_range': ['IN','OW'],  # IN 国内 OUT 国际
            'from_to_routings':[['PVG','KMG'],['PVG','HRB']], # 航线 出发地，目的地
            'trip_type':['OW','RT'], # OW 单程 RT 往返
            'cabin_grade': ['Y','F','C','S'], # 舱等 头等：F 商务：C 超经：S 经济： Y
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
            'format': '[%(tbasctime)s][%(tb_app_name)s][%(levelname)s][%(sub_level)s][%(request_id)s][%(order_id)s][%(sub_order_id)s][%(frame_id)s][%(ota_name)s][%(provider_channel)s][%(frame_name)s]%(message)s',
        },
    },
    'handlers': {
        'access_log_file': {
            'level': 'DEBUG',
            'formatter': 'standard',
            'class': 'cloghandler.ConcurrentRotatingFileHandler',
            'filename':  os.path.join(updir, 'logs', 'info.log'),
            'maxBytes': 200 * 1024 * 1024,
            'backupCount': 50,
        },
        'stdout': {
            'class':'logging.StreamHandler',
            'formatter':'standard',
            'level':'DEBUG'
        }
    },
    'loggers': {
        'logger_access_log': {
            'handlers': ['stdout','access_log_file'],
            'level': 'DEBUG',
            'propagate': False,
        }
    },
}
