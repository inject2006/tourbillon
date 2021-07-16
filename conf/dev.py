# -*- coding: utf-8 -*-

# 线上测试环境使用
import os

basedir = os.path.abspath(os.path.dirname(__file__))
updir = os.path.dirname(basedir)

ALLOW_PRINT_HTTP_INFO_IN_TEST = False   # 测试环境下是否自动打印http请求信息

TOURBILLON_DB = dict(
    MYSQL_HOST='localhost',
    MYSQL_PORT=3306,
    MYSQL_USER='root',
    MYSQL_PASSWORD='111111',
    MYSQL_DB='tourbillon',
)

TOURBILLON_EXTRA_DB = dict(
    MYSQL_HOST='localhost',
    MYSQL_PORT=3306,
    MYSQL_USER='root',
    MYSQL_PASSWORD='111111',
    MYSQL_DB='tourbillon',
)

SENTRY_APP = False
SENTRY_DSN = 'http://bb2b6e5507d347a482fb9e08368a4b17:00a379096c624b818bb814b68c961661@192.168.3.17:9000/7'

REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_PASSWORD = ''
FLIGHT_FARE_CACHE_REDIS_DB = 3
COMMON_REDIS_DB = 4

#proxy 设置

FIX_PROXY_ADDR = 'http://proxy.baibianip.com'
FIX_PROXY_PORT_RANGE_START = 8001
FIX_PROXY_PORT_RANGE_END = 8045
RANDOM_PROXY_ADDR = 'http://proxy.baibianip.com'
RANDOM_PROXY_PORT = 8000

# 验证码收发邮箱设置
MAIL_ADDR = 'imap.exmail.qq.com'
MAIL_USER = 'fvck@tongdun.org'
MAIL_PASSWORD ='XrczRNDTBwBRvaPH'

#是否人工支付
ONLY_MANUAL_PAY = True

# misc 管理系统账号
USER_LIST = {'admin': 'admin', 'sales': 'sales'}

# 运营联系电话
OPERATION_CONTACT_MOBILE = '13736090908'

# 路由设置

ROUTER_CONFIG =[
    {
        'ota_name':'lvmama',
        'auto_provider':'ceair',
        'auto_channel':'web',  #
        'auto_product_type':2, # 0: GDS公布运价 1:GDS私有运价 2:航司官网产品  3:廉价航司产品 4:特价产品
        'trip_type':['OW'] # 只做单程
    }
]

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


LOGGING_CONF = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '[%(asctime)s] [%(levelname)s]%(message)s',
        },
    },
    'handlers': {
        'access_log_file': {
            'level': 'DEBUG',
            'formatter': 'standard',
            'class': 'logging.handlers.RotatingFileHandler',
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

