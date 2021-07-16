#!/usr/local/bin/python2.7
# -*- coding: utf-8 -*-

import random
import uuid
import time
import re
import hashlib
import gevent
from faker import Factory
import datetime
from xpinyin import Pinyin
import inspect
from flask import g

# coding:utf8
import time
import math
import base64


class AttrDict(dict):
    # TODO 带参数创建实例功能
    # 时间格式无法序列化

    def __init__(self,*args, **kwargs):
        super(AttrDict, self).__init__(*args,**kwargs)
        self.redis_conn = None
        self.config_redis = None
        self.tourbillon_extra_db = None
        self.tb_metrics = None
        self.tb_aggr_metrics = None
        self.cached_meta = None
        self.tourbillon_db = None
        self.mailer = None
        self.cache_access_object = None
        self.global_config = None
        self.tb_publisher = None

    def __setattr__(self, name, value):
        self[name] = value

    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            return None


class Time(object):

    @staticmethod
    def change_time(secs):

        if secs == None:
            return '暂无统计'
        day = 24 * 60 * 60
        hour = 60 * 60
        min = 60
        if secs < 60:
            return "%d秒" % math.ceil(secs)

        elif secs > day:
            days = divmod(secs, day)
            # hours = divmod(secs, hour)
            return "%d天%s" % (int(days[0]), Time.change_time(int(days[1])))
        elif secs > hour:
            hours = divmod(secs, hour)
            # mins = divmod(secs, min)
            return '%d小时%s' % (int(hours[0]), Time.change_time(int(hours[1])))
        else:
            mins = divmod(secs, min)
            return "%d分钟%d秒" % (int(mins[0]), math.ceil(mins[1]))


    @staticmethod
    def timestamp_ms():
        return int(time.time() * 1000)

    @staticmethod
    def timestamp_s():
        return int(time.time())

    @staticmethod
    def timestamp_ns():
        return int(time.time() * 1000 * 1000 * 1000)

    @staticmethod
    def time_str():
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def time_str_2():
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]

    @staticmethod
    def time_str_3():
        return datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]

    @staticmethod
    def time_str_4():
        return datetime.datetime.now().strftime("%Y%m%d%H%M%S")

    @staticmethod
    def dtime_to_str(dtime):
        return dtime.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def date_str():
        return datetime.datetime.now().strftime("%Y%m%d")

    @staticmethod
    def date_str_2():
        return datetime.datetime.now().strftime("%Y-%m-%d")

    @staticmethod
    def date_str_3():
        return datetime.datetime.now().strftime("%Y-%m")

    @staticmethod
    def curr_date_obj():
        return datetime.datetime.now()

    @staticmethod
    def timedelta_to_ms(td):
        return int(1000 * td.total_seconds())

    @staticmethod
    def days_before(days):
        return Time.curr_date_obj() - datetime.timedelta(days=days)

    @staticmethod
    def days_after(days):
        return Time.curr_date_obj() + datetime.timedelta(days=days)

    @staticmethod
    def hours_before(hours):
        return Time.curr_date_obj() - datetime.timedelta(hours=hours)

    @staticmethod
    def curr_date_obj_2():
        d = datetime.datetime.now()
        return datetime.datetime(d.year, d.month, d.day, 0, 0, 0)

class Random(object):
    @staticmethod
    def gen_passport():
        """
        :return:
        """
        return 'G%s' % random.randint(10000000, 99999999)

    @staticmethod
    def gen_password():
        """
        :return:
        """
        return '%s' % random.randint(10000000, 99999999)

    @staticmethod
    def gen_num(digit=8):
        """
        :return:
        """

        return int(str(random.randint(10000000000, 99999999999))[:digit])

    @staticmethod
    def gen_littlepnr():
        """
        :return:
        """
        str = ''
        chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ123456789'
        length = len(chars) - 1
        for i in range(6):
            str += chars[random.randint(0, length)]
        return str

    @staticmethod
    def gen_alpha(digit=5):
        """
        :return:
        """
        str = ''
        chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ123456789'
        length = len(chars) - 1
        for i in range(digit):
            str += chars[random.randint(0, length)]
        return str

    @staticmethod
    def gen_request_id():
        """
        :return:
        """

        return '%s-%s'% (Time.timestamp_s(),random.randint(10000,99990))

    @staticmethod
    def gen_email(domain='tongdun.org'):
        fake = Factory().create('zh_CN')
        email = fake.email(domain=domain)

        rand_suffix = fake.pyint()
        email = email.replace('@%s'%domain, '%s@%s' % (rand_suffix,domain))
        return email

    @staticmethod
    def gen_birthdate():
        """
        生成40岁-20岁的生日
        :return:
        """
        fake = Factory().create('zh_CN')
        res = fake.date_time_between(start_date="-40y", end_date="-20y", tzinfo=None).strftime('%Y-%m-%d')
        return res

    @staticmethod
    def gen_first_name():
        fake = Factory().create('zh_CN')
        return fake.first_name()

    @staticmethod
    def gen_last_name():
        fake = Factory().create('zh_CN')
        return fake.last_name()

    @staticmethod
    def gen_mobile():
        # prelist = ["130", "131", "132", "133", "134", "135", "136", "137", "138", "139", "147", "150", "151", "152", "153", "155", "156", "157", "158", "159", "186", "187", "188"]
        # prelist = ['180', '181', '182', '183', '184', '185', '186', '187', '188', '189', '170', '171', '172', '173', '174', '175', '176', '177', '178', '179']
        prelist = ['160', '161', '162', '163', '164', '165', '166', '167', '168', '169']
        return random.choice(prelist) + "".join(random.choice("0123456789") for i in range(8))

    @staticmethod
    def gen_address():
        fake = Factory().create('zh_CN')
        return fake.address()

    @staticmethod
    def gen_hash():
        return uuid.uuid4().hex

    @staticmethod
    def gen_full_name():
        fake = Factory().create('zh_CN')
        return fake.last_name()+fake.first_name()

    @staticmethod
    def gen_full_name_4():
        #生成四个字的中文姓名
        fake = Factory().create('zh_CN')
        name = fake.last_name() + fake.first_name() + fake.first_name() + fake.first_name()
        name = name[:4]
        return name

    @staticmethod
    def gen_full_name_3():
        #生成四个字的中文姓名
        fake = Factory().create('zh_CN')
        name = fake.last_name() + fake.first_name() + fake.first_name()
        name = name[:3]
        return name

    @staticmethod
    def gen_pid():
        fake = Factory().create('zh_CN')
        return fake.ssn(min_age=20,max_age=58)

    @staticmethod
    def gen_ratio(min=0,max=1):
        """
        随机生成百分比
        :return:
        """
        return random.randint(min*100,max*100) / float(100)

def fixed_password():
    """
    固定密码
    :return:
    """
    return '13461346'


def md5_hash(plain):
    """
    将routing_key hash 掉plain
    :return:
    """
    m = hashlib.md5()
    m.update(plain)
    return m.hexdigest()

def convert_unicode(data):
    if isinstance(data,str):
        return unicode(data,'utf-8')
    return data

def convert_utf8(data):
    if isinstance(data,unicode):
        return data.encode('utf8')
    return data

def cn_name_to_pinyin(name):
    """
    中文转拼音
    :return:
    """
    pyin = Pinyin()
    return pyin.get_pinyin(name,"")


def mobile_match(mobile):
    """
    Author:wxt
    手机号码验证
    """
    # mobile_exp = re.compile("^(13[0-9]|14[01345789]|15[0-9]|17[012356789]|18[0-9])[0-9]{8}$")
    # mobile_exp = re.compile("^(13[0-9]|14[01345789]|15[0-9]|17[012356789]|18[0-9]|199)[0-9]{8}$")
    mobile_exp = re.compile("^(13[0-9]|14[01345789]|15[0-9]|16[6]|17[012356789]|18[0-9]|19[89])[0-9]{8}$")

    if mobile_exp.match(mobile):
        return True
    else:
        return False


def identity_card_match(id_number):
    """
    身份证号码验证
    :param id_number:
    :return: Boolean
    """
    if type(id_number) is int:
        id_number = str(id_number)
    if type(id_number) is str:
        try:
            int(id_number[:17])
        except ValueError:
            return False

    regex = r'^(^[1-9]\d{7}((0\d)|(1[0-2]))(([0|1|2]\d)|3[0-1])\d{3}$)|(^[1-9]\d{5}[1-9]\d{3}((0\d)|(1[0-2]))(([0|1|2]\d)|3[0-1])((\d{4})|\d{3}[Xx])$)$'

    if len(re.findall(regex, id_number)) == 0:
        return False
    if len(id_number) == 15:
        return True
    if len(id_number) == 18:
        Wi = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
        Ti = ['1', '0', 'x', '9', '8', '7', '6', '5', '4', '3', '2']

        sum = 0
        code = id_number[:17]

        for i in range(17):
            sum += int(code[i]) * Wi[i]

        if id_number[17:].lower() == Ti[sum % 11]:
            return True

    return False

def tb_gevent_spawn(func,**kwargs):



    lf = inspect.currentframe()
    last_frame_name = ''
    last_fid = ''
    last_request_id = ''
    last_order_id = ''
    last_provider_channel = ''
    last_ota_name = ''
    last_tb_is_log_debug = ''



    for x in range(0, 20):
        lf = lf.f_back
        if (last_provider_channel and last_ota_name and last_request_id and last_fid and last_order_id and last_frame_name and last_tb_is_log_debug) or lf == None:
            break

        if not last_provider_channel and 'TB_PROVIDER_CHANNEL' in lf.f_locals:
            last_provider_channel = lf.f_locals['TB_PROVIDER_CHANNEL']
        if not last_ota_name and 'TB_OTA_NAME' in lf.f_locals:
            last_ota_name = lf.f_locals['TB_OTA_NAME']
        if not last_fid and 'TB_FRAME_ID' in lf.f_locals:
            last_fid = lf.f_locals['TB_FRAME_ID']
        if not last_fid and 'TB_FRAME_ID' in lf.f_locals:
            last_fid = lf.f_locals['TB_FRAME_ID']
        if not last_frame_name and 'TB_FRAME_NAME' in lf.f_locals:
            last_frame_name = lf.f_locals['TB_FRAME_NAME']
        if not last_request_id and 'TB_REQUEST_ID' in lf.f_locals:
            last_request_id = lf.f_locals['TB_REQUEST_ID']
        if not last_order_id and 'TB_ORDER_ID' in lf.f_locals:
            last_order_id = lf.f_locals['TB_ORDER_ID']

        if not last_tb_is_log_debug and 'TB_IS_LOG_DEBUG' in lf.f_locals:
            last_tb_is_log_debug = lf.f_locals['TB_IS_LOG_DEBUG']

    kwargs['last_fid'] = last_fid
    kwargs['last_frame_name'] = last_frame_name
    kwargs['last_request_id'] = last_request_id
    kwargs['last_order_id'] = last_order_id
    kwargs['last_provider_channel'] = last_provider_channel
    kwargs['last_ota_name'] = last_ota_name
    kwargs['last_tb_is_log_debug'] = last_tb_is_log_debug
    kwargs['func'] = func

    return gevent.spawn(spawn_wraper,**kwargs)


def spawn_wraper(func,**kwargs):
    TB_FRAME_ID = kwargs.pop('last_fid','')
    TB_REQUEST_ID = kwargs.pop('last_request_id', '')
    TB_ORDER_ID = kwargs.pop('last_order_id', '')
    TB_PROVIDER_CHANNEL= kwargs.pop('last_provider_channel', '')
    TB_OTA_NAME = kwargs.pop('last_ota_name', '')
    TB_FRAME_NAME = kwargs.pop('last_frame_name', '')
    TB_IS_LOG_DEBUG = kwargs.pop('last_tb_is_log_debug', '')
    func(**kwargs)

def modify_ni(card_ni):
    """
    修改身份证17位+校验码
    :return:
    """
    card_ni_17 = int(card_ni[16:17])
    card_ni_17 = (card_ni_17+2) % 10

    modified_card_ni = list(card_ni)
    modified_card_ni[16] = str(card_ni_17)
    modified_card_ni.pop(-1)
    code = ''.join(modified_card_ni)
    sum = 0
    __Wi = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    __Ti = ['1', '0', 'x', '9', '8', '7', '6', '5', '4', '3', '2']
    for i in range(17):
        sum += int(code[i]) * __Wi[i]
    verify_bit = __Ti[sum % 11]
    return code + verify_bit

def modify_pp(card_pp):
    """
    修改护照号后一位,如果是数字则+1 如果是字母则取后一位，如果是Z则取A
    :return:
    """

    modified_card_pp = list(card_pp)

    last_bit = modified_card_pp[-1]
    if 48 <= ord(last_bit) <= 57:
        # 数字
        modified_card_pp[-1] = str((int(modified_card_pp[-1])+1) % 10)
    else:
        # 字母
        current_ord = ord(last_bit)
        if current_ord == 90:
            modified_letter = 'A'
        else:
            modified_letter = chr(current_ord +1)
        modified_card_pp[-1] = modified_letter

    code = ''.join(modified_card_pp)

    return code


def simple_encrypt(decode_str):

    b64str = base64.b64encode(decode_str)
    result = ''
    padding = ''
    if b64str[-2:] == '==':
        b64str = b64str[: -2]
        padding = '=='
    if b64str[-1:] == '=':
        b64str = b64str[: -1]
        padding = '='

    for b in b64str[:: -1]:
        result += b
    result += padding

    return result


def simple_decrypt(encode_str):

    padding = ''
    result = ''
    if encode_str[-2:] == '==':
        padding = '=='
        encode_str = encode_str[: -2]
    if encode_str[-1:] == '=':
        encode_str = encode_str[: -1]
        padding = '='

    for b in encode_str[:: -1]:
        result += b
    result += padding

    return base64.b64decode(result)


def run_in_thread(func,*args,**kwargs):
    from threading import Thread
    thread = Thread(target=func,args=args,kwargs=kwargs)
    thread.daemon = True
    thread.start()
    return thread

class RoutingKey(object):
    """
    routing_key 格式
    SHA|201811061917|SZX|201811061917|FM9331|HYJ_EC|B|35491.0|354.0|354.0|353.0|0.0|0.0|ceair_web_2

    """
    version = 'V12'  # 对routingkey进行版本区分，防止不兼容导致报错

    @staticmethod
    def serialize(from_airport,dep_time,to_airport,arr_time,flight_number,adult_price,adult_tax,provider_channel,provider,cabin='N/A',child_price=0.0,child_tax=0.0,inf_price=0.0,inf_tax=0.0,product='COMMON',adult_price_forsale=0.0,child_price_forsale=0.0,inf_price_forsale=0.0,version='',enter_time='',search_time='',verify_time='',data_source='',search_from_airport='',search_to_airport='',from_date='',trip_type='OW',routing_range='',is_multi_segments='',dep_diff_days=1,fare_put_mode='NOFARE',cabin_grade='',assoc_provider_channels=[],ret_date='',assoc_fare_info='',is_encrypt=True,rsno='',is_include_operation_carrier=0,is_virtual_cabin=0,adt_count=1,chd_count=0):
        return RoutingKey._serialize(from_airport=from_airport,dep_time=dep_time,to_airport=to_airport,arr_time=arr_time,flight_number=flight_number,cabin=cabin,adult_price=adult_price,adult_tax=adult_tax,provider=provider,provider_channel=provider_channel,child_price=child_price,child_tax=child_tax,inf_price=inf_price,inf_tax=inf_tax,product=product,adult_price_forsale=adult_price_forsale,child_price_forsale=child_price_forsale,inf_price_forsale=inf_price_forsale,enter_time=enter_time,search_time=search_time,verify_time=verify_time,data_source=data_source,search_from_airport=search_from_airport,search_to_airport=search_to_airport,from_date=from_date,trip_type=trip_type,routing_range=routing_range,is_multi_segments=is_multi_segments,dep_diff_days=dep_diff_days,fare_put_mode=fare_put_mode,cabin_grade=cabin_grade,assoc_provider_channels=assoc_provider_channels,ret_date=ret_date,assoc_fare_info=assoc_fare_info,is_encrypt=is_encrypt,rsno=rsno,is_include_operation_carrier=is_include_operation_carrier,is_virtual_cabin=is_virtual_cabin,adt_count=adt_count,chd_count=chd_count)

    @staticmethod
    def _serialize(from_airport='',dep_time='',to_airport='',arr_time='',flight_number='',cabin='',adult_price=0.0,adult_tax=0.0,provider='',provider_channel='',child_price=0.0,child_tax=0.0,inf_price=0.0,inf_tax=0.0,product='COMMON',adult_price_forsale=0.0,child_price_forsale=0.0,inf_price_forsale=0.0,enter_time='',search_time='',verify_time='',data_source='',search_from_airport='',search_to_airport='',from_date='',trip_type='',routing_range='',is_multi_segments='',dep_diff_days=1,fare_put_mode='NOFARE',cabin_grade='',assoc_provider_channels=[],ret_date='',assoc_fare_info='',is_encrypt=True,rsno='',is_include_operation_carrier=0,is_virtual_cabin=0,adt_count=1,chd_count=0):
        """
        拼装routing_key
        :return: 返回 {'plain':'明文routing_key','encrypted':'routing_key 密文'}
        时间格式 201811061917  %Y%m%d%H%M%S 如果为datetime格式则会自动转换
        cabin  flight_number  请自行添加横杠
        """

        #判断时间格式转换时间

        if isinstance(arr_time,datetime.datetime):
            arr_time = arr_time.strftime('%Y%m%d%H%M')
        if isinstance(dep_time,datetime.datetime):
            dep_time = dep_time.strftime('%Y%m%d%H%M')

        # 进入时间默认为序列化产生的时间
        if enter_time:
            if isinstance(enter_time,datetime.datetime):
                enter_time = enter_time.strftime('%Y%m%d%H%M%S')
        else:
            enter_time = Time.time_str_4()
        if isinstance(search_time,datetime.datetime):
            search_time = search_time.strftime('%Y%m%d%H%M%S')
        if isinstance(verify_time,datetime.datetime):
            verify_time = verify_time.strftime('%Y%m%d%H%M%S')
        if isinstance(from_date,datetime.datetime):
            from_date = from_date.strftime('%Y-%m-%d')
        if isinstance(ret_date,datetime.datetime):
            ret_date = ret_date.strftime('%Y-%m-%d')
        elif not ret_date:
            ret_date = ''
        if not adult_price_forsale:
            adult_price_forsale = adult_price
        if not child_price_forsale:
            child_price_forsale = child_price
        if not inf_price_forsale:
            inf_price_forsale = inf_price

        plain_routing_key = '{version}|{from_airport}|{dep_time}|{to_airport}|{arr_time}|{flight_number}|{cabin}|{product}|{provider}|{provider_channel}|{adult_price}|{adult_tax}|{child_price}|{child_tax}|0.0|0.0|{adult_price_forsale}|{child_price_forsale}|{inf_price_forsale}|{enter_time}|{search_time}|{verify_time}|{data_source}|{search_from_airport}|{search_to_airport}|{from_date}|{trip_type}|{routing_range}|{is_multi_segments}|{dep_diff_days}|{fare_put_mode}|{cabin_grade}|{assoc_provider_channels}|{ret_date}|{assoc_fare_info}|{rsno}|{is_include_operation_carrier}|{is_virtual_cabin}|{adt_count}|{chd_count}'.format(
                        version=RoutingKey.version,from_airport=from_airport, dep_time=dep_time, to_airport=to_airport,
                        arr_time=arr_time, flight_number=flight_number,
                        product=product, cabin=cabin,
                        adult_price=adult_price, adult_tax=adult_tax,
                        child_price=child_price, child_tax=child_tax,provider=provider,provider_channel=provider_channel,
                        adult_price_forsale=adult_price_forsale,child_price_forsale=child_price_forsale,inf_price_forsale=inf_price_forsale,
                        enter_time=enter_time,search_time=search_time,verify_time=verify_time,data_source=data_source,
                        search_from_airport=search_from_airport, search_to_airport=search_to_airport, from_date=from_date, trip_type=trip_type, routing_range=routing_range,
                        is_multi_segments=is_multi_segments,dep_diff_days=dep_diff_days,fare_put_mode=fare_put_mode,cabin_grade=cabin_grade,assoc_provider_channels=",".join(assoc_provider_channels),ret_date=ret_date,assoc_fare_info=assoc_fare_info,rsno=rsno,is_include_operation_carrier=is_include_operation_carrier,is_virtual_cabin=is_virtual_cabin,adt_count=adt_count,chd_count=chd_count
                        )
        if is_encrypt:
            encrypted_routing_key = simple_encrypt(plain_routing_key)
        else:
            encrypted_routing_key = ''
        return {'plain':plain_routing_key,'encrypted':encrypted_routing_key}

    @staticmethod
    def decrypted(encrypted_routing_key):
        """
        解密加密的rk
        :param encrypted_routing_key:
        :return:
        """
        return simple_decrypt(encrypted_routing_key)

    @staticmethod
    def unserialize(routing_key,is_encrypted=False):
        """
        解析 routing_key

        ===== 版本变化 =====：
        V1 -> V2: 增加 enter_time  search_time  verify_time data_source

        V2 -> V3: 增加 搜索条件
        search_from_airport - 搜索出发机场/城市三字码
        search_to_airport 搜索到达机场/城市三字码
        from_date 出发日期，格式：2018-12-21
        routing_range OUT - 国际 IN - 国内
        is_multi_segments 是否多段航程 1 - 是 0 - 否

        V3 -> V4: 增加起飞间隔天数 dep_diff_days

        V4 -> V5: fare_put_mode 运价投放方式   AUTO 自动化 MANUAL 人工投放 A+M 动运人工

        V5 -> V6: 增加舱等  cabin_grade

        V6 -> V7: 新增关联下单供应商 验价接口产生，用于生单接口 assoc_provider_channels 供应商渠道名称之前用逗号分隔

        V7 -> V8: 新增 ret_date

        V8 -> V9:  新增 assoc_fare_info 关联运价信息

        V9 -> V10:  新增 RSNO

        V10 -> V11:  新增 is_include_operation_carrier is_virtual_cabin

        V11 -> V12:  新增 adt_count chd_count

        :param is_encrypted: 是否为加密routing_key
        :return:
        """
        if is_encrypted:
            routing_key = simple_decrypt(routing_key)
        routing_key_list = routing_key.split('|')

        if routing_key_list[0] == 'V7':
            return {
                'version': routing_key_list[0],
                'from_airport': routing_key_list[1],
                'dep_time': routing_key_list[2],
                'to_airport': routing_key_list[3],
                'arr_time': routing_key_list[4],
                'flight_number': routing_key_list[5],
                'cabin': routing_key_list[6],
                'product': routing_key_list[7],
                'provider': routing_key_list[8],
                'provider_channel': routing_key_list[9],
                'adult_price': float(routing_key_list[10]),
                'adult_tax': float(routing_key_list[11]),
                'child_price': float(routing_key_list[12]),
                'child_tax': float(routing_key_list[13]),
                'inf_price': float(routing_key_list[14]),
                'inf_tax': float(routing_key_list[15]),
                'adult_price_forsale': float(routing_key_list[16]),
                'child_price_forsale': float(routing_key_list[17]),
                'inf_price_forsale': float(routing_key_list[18]),
                'enter_time': routing_key_list[19],
                'search_time': routing_key_list[20],
                'verify_time': routing_key_list[21],
                'data_source': routing_key_list[22],
                'search_from_airport': routing_key_list[23],
                'search_to_airport': routing_key_list[24],
                'from_date': routing_key_list[25],
                'trip_type': routing_key_list[26],
                'routing_range': routing_key_list[27],
                'is_multi_segments': int(routing_key_list[28]),
                'dep_diff_days': int(routing_key_list[29]),
                'fare_put_mode': routing_key_list[30],
                'cabin_grade': routing_key_list[31],
                'assoc_provider_channels':[x for x in routing_key_list[32].split(',')],
                'ret_date': '',
                'assoc_fare_info': '',
                'rsno': '',
                'is_include_operation_carrier':0,
                'is_virtual_cabin': 0,
                'adt_count':1,
                'chd_count':0

            }
        elif routing_key_list[0] == 'V8':
            return {
                'version': routing_key_list[0],
                'from_airport': routing_key_list[1],
                'dep_time': routing_key_list[2],
                'to_airport': routing_key_list[3],
                'arr_time': routing_key_list[4],
                'flight_number': routing_key_list[5],
                'cabin': routing_key_list[6],
                'product': routing_key_list[7],
                'provider': routing_key_list[8],
                'provider_channel': routing_key_list[9],
                'adult_price': float(routing_key_list[10]),
                'adult_tax': float(routing_key_list[11]),
                'child_price': float(routing_key_list[12]),
                'child_tax': float(routing_key_list[13]),
                'inf_price': float(routing_key_list[14]),
                'inf_tax': float(routing_key_list[15]),
                'adult_price_forsale': float(routing_key_list[16]),
                'child_price_forsale': float(routing_key_list[17]),
                'inf_price_forsale': float(routing_key_list[18]),
                'enter_time': routing_key_list[19],
                'search_time': routing_key_list[20],
                'verify_time': routing_key_list[21],
                'data_source': routing_key_list[22],
                'search_from_airport': routing_key_list[23],
                'search_to_airport': routing_key_list[24],
                'from_date': routing_key_list[25],
                'trip_type': routing_key_list[26],
                'routing_range': routing_key_list[27],
                'is_multi_segments': int(routing_key_list[28]),
                'dep_diff_days': int(routing_key_list[29]),
                'fare_put_mode': routing_key_list[30],
                'cabin_grade': routing_key_list[31],
                'assoc_provider_channels':[x for x in routing_key_list[32].split(',')],
                'ret_date':routing_key_list[33] if routing_key_list[33] else '',
                'assoc_fare_info': '',
                'rsno':'',
                'is_include_operation_carrier': 0,
                'is_virtual_cabin': 0,
                'adt_count': 1,
                'chd_count': 0
            }

        elif routing_key_list[0] == 'V9':
            return {
                'version': routing_key_list[0],
                'from_airport': routing_key_list[1],
                'dep_time': routing_key_list[2],
                'to_airport': routing_key_list[3],
                'arr_time': routing_key_list[4],
                'flight_number': routing_key_list[5],
                'cabin': routing_key_list[6],
                'product': routing_key_list[7],
                'provider': routing_key_list[8],
                'provider_channel': routing_key_list[9],
                'adult_price': float(routing_key_list[10]),
                'adult_tax': float(routing_key_list[11]),
                'child_price': float(routing_key_list[12]),
                'child_tax': float(routing_key_list[13]),
                'inf_price': float(routing_key_list[14]),
                'inf_tax': float(routing_key_list[15]),
                'adult_price_forsale': float(routing_key_list[16]),
                'child_price_forsale': float(routing_key_list[17]),
                'inf_price_forsale': float(routing_key_list[18]),
                'enter_time': routing_key_list[19],
                'search_time': routing_key_list[20],
                'verify_time': routing_key_list[21],
                'data_source': routing_key_list[22],
                'search_from_airport': routing_key_list[23],
                'search_to_airport': routing_key_list[24],
                'from_date': routing_key_list[25],
                'trip_type': routing_key_list[26],
                'routing_range': routing_key_list[27],
                'is_multi_segments': int(routing_key_list[28]),
                'dep_diff_days': int(routing_key_list[29]),
                'fare_put_mode': routing_key_list[30],
                'cabin_grade': routing_key_list[31],
                'assoc_provider_channels':[x for x in routing_key_list[32].split(',')],
                'ret_date':routing_key_list[33] if routing_key_list[33] else '',
                'assoc_fare_info': routing_key_list[34],
                'rsno': '',
                'is_include_operation_carrier': 0,
                'is_virtual_cabin': 0,
                'adt_count': 1,
                'chd_count': 0
            }
        elif routing_key_list[0] == 'V10':
            return {
                'version': routing_key_list[0],
                'from_airport': routing_key_list[1],
                'dep_time': routing_key_list[2],
                'to_airport': routing_key_list[3],
                'arr_time': routing_key_list[4],
                'flight_number': routing_key_list[5],
                'cabin': routing_key_list[6],
                'product': routing_key_list[7],
                'provider': routing_key_list[8],
                'provider_channel': routing_key_list[9],
                'adult_price': float(routing_key_list[10]),
                'adult_tax': float(routing_key_list[11]),
                'child_price': float(routing_key_list[12]),
                'child_tax': float(routing_key_list[13]),
                'inf_price': float(routing_key_list[14]),
                'inf_tax': float(routing_key_list[15]),
                'adult_price_forsale': float(routing_key_list[16]),
                'child_price_forsale': float(routing_key_list[17]),
                'inf_price_forsale': float(routing_key_list[18]),
                'enter_time': routing_key_list[19],
                'search_time': routing_key_list[20],
                'verify_time': routing_key_list[21],
                'data_source': routing_key_list[22],
                'search_from_airport': routing_key_list[23],
                'search_to_airport': routing_key_list[24],
                'from_date': routing_key_list[25],
                'trip_type': routing_key_list[26],
                'routing_range': routing_key_list[27],
                'is_multi_segments': int(routing_key_list[28]),
                'dep_diff_days': int(routing_key_list[29]),
                'fare_put_mode': routing_key_list[30],
                'cabin_grade': routing_key_list[31],
                'assoc_provider_channels':[x for x in routing_key_list[32].split(',')],
                'ret_date':routing_key_list[33] if routing_key_list[33] else '',
                'assoc_fare_info': routing_key_list[34],
                'rsno': routing_key_list[35],
                'is_include_operation_carrier': 0,
                'is_virtual_cabin': 0,
                'adt_count': 1,
                'chd_count': 0
            }
        elif routing_key_list[0] == 'V11':
            return {
                'version': routing_key_list[0],
                'from_airport': routing_key_list[1],
                'dep_time': routing_key_list[2],
                'to_airport': routing_key_list[3],
                'arr_time': routing_key_list[4],
                'flight_number': routing_key_list[5],
                'cabin': routing_key_list[6],
                'product': routing_key_list[7],
                'provider': routing_key_list[8],
                'provider_channel': routing_key_list[9],
                'adult_price': float(routing_key_list[10]),
                'adult_tax': float(routing_key_list[11]),
                'child_price': float(routing_key_list[12]),
                'child_tax': float(routing_key_list[13]),
                'inf_price': float(routing_key_list[14]),
                'inf_tax': float(routing_key_list[15]),
                'adult_price_forsale': float(routing_key_list[16]),
                'child_price_forsale': float(routing_key_list[17]),
                'inf_price_forsale': float(routing_key_list[18]),
                'enter_time': routing_key_list[19],
                'search_time': routing_key_list[20],
                'verify_time': routing_key_list[21],
                'data_source': routing_key_list[22],
                'search_from_airport': routing_key_list[23],
                'search_to_airport': routing_key_list[24],
                'from_date': routing_key_list[25],
                'trip_type': routing_key_list[26],
                'routing_range': routing_key_list[27],
                'is_multi_segments': int(routing_key_list[28]),
                'dep_diff_days': int(routing_key_list[29]),
                'fare_put_mode': routing_key_list[30],
                'cabin_grade': routing_key_list[31],
                'assoc_provider_channels':[x for x in routing_key_list[32].split(',')],
                'ret_date':routing_key_list[33] if routing_key_list[33] else '',
                'assoc_fare_info': routing_key_list[34],
                'rsno': routing_key_list[35],
                'is_include_operation_carrier': int(routing_key_list[36]),
                'is_virtual_cabin': int(routing_key_list[37]),
                'adt_count': 1,
                'chd_count': 0
            }
        elif routing_key_list[0] == 'V12':
            return {
                'version': routing_key_list[0],
                'from_airport': routing_key_list[1],
                'dep_time': routing_key_list[2],
                'to_airport': routing_key_list[3],
                'arr_time': routing_key_list[4],
                'flight_number': routing_key_list[5],
                'cabin': routing_key_list[6],
                'product': routing_key_list[7],
                'provider': routing_key_list[8],
                'provider_channel': routing_key_list[9],
                'adult_price': float(routing_key_list[10]),
                'adult_tax': float(routing_key_list[11]),
                'child_price': float(routing_key_list[12]),
                'child_tax': float(routing_key_list[13]),
                'inf_price': float(routing_key_list[14]),
                'inf_tax': float(routing_key_list[15]),
                'adult_price_forsale': float(routing_key_list[16]),
                'child_price_forsale': float(routing_key_list[17]),
                'inf_price_forsale': float(routing_key_list[18]),
                'enter_time': routing_key_list[19],
                'search_time': routing_key_list[20],
                'verify_time': routing_key_list[21],
                'data_source': routing_key_list[22],
                'search_from_airport': routing_key_list[23],
                'search_to_airport': routing_key_list[24],
                'from_date': routing_key_list[25],
                'trip_type': routing_key_list[26],
                'routing_range': routing_key_list[27],
                'is_multi_segments': int(routing_key_list[28]),
                'dep_diff_days': int(routing_key_list[29]),
                'fare_put_mode': routing_key_list[30],
                'cabin_grade': routing_key_list[31],
                'assoc_provider_channels':[x for x in routing_key_list[32].split(',')],
                'ret_date':routing_key_list[33] if routing_key_list[33] else '',
                'assoc_fare_info': routing_key_list[34],
                'rsno': routing_key_list[35],
                'is_include_operation_carrier': int(routing_key_list[36]),
                'is_virtual_cabin': int(routing_key_list[37]),
                'adt_count': int(routing_key_list[38]),
                'chd_count': int(routing_key_list[39])
            }



    # @staticmethod
    # def dynamic_serialize(from_airport='',dep_time='',to_airport='',arr_time='',flight_number='',cabin='',adult_price=0.0,adult_tax=0.0,provider='',provider_channel='',child_price=0.0,child_tax=0.0,inf_price=0.0,inf_tax=0.0,product='',adult_price_forsale=0.0,child_price_forsale=0.0,inf_price_forsale=0.0,version=''):
    #     """
    #     拼装动态routing_key，无必填参数
    #     :return: 返回 {'plain':'明文routing_key','encrypted':'routing_key 密文'}
    #     时间格式 201811061917  %Y%m%d%H%M%S 如果为datetime格式则会自动转换
    #     cabin  flight_number  请自行添加横杠
    #     """
    #     return RoutingKey._serialize(from_airport=from_airport,dep_time=dep_time,to_airport=to_airport,arr_time=arr_time,flight_number=flight_number,cabin=cabin,adult_price=adult_price,adult_tax=adult_tax,provider=provider,provider_channel=provider_channel,child_price=child_price,child_tax=child_tax,inf_price=inf_price,inf_tax=inf_tax,product=product,adult_price_forsale=adult_price_forsale,child_price_forsale=child_price_forsale,inf_price_forsale=inf_price_forsale)
    #

    @staticmethod
    def trans_cp_key(routing_key,is_unserialized=False,is_encrypted=False):
        """
        将明文的routing_key 转换拼装用于择价的routing_key （同航班同舱位）

        """
        if not is_unserialized:
            d = RoutingKey.unserialize(routing_key,is_encrypted=is_encrypted)
        else:
            d = routing_key
        return '%s|%s|%s|%s|%s|%s' % (d['from_airport'],d['dep_time'],d['to_airport'],d['arr_time'],d['flight_number'],d['cabin'])

    @staticmethod
    def trans_vcp_key(routing_key,is_unserialized=False):
        """
        将明文的routing_key 转换拼装用于择价的routing_key （同航班同舱位）
        如果存在虚拟仓位则将cabin字段替换成虚拟仓位

        """
        if not is_unserialized:
            d = RoutingKey.unserialize(routing_key)
        else:
            d = routing_key
        cabin = d['cabin']
        virtual_cabin = d.get('virtual_cabin',None)
        if virtual_cabin:
            cabin = virtual_cabin
        return '%s|%s|%s|%s|%s|%s' % (d['from_airport'],d['dep_time'],d['to_airport'],d['arr_time'],d['flight_number'],cabin)

    @staticmethod
    def trans_cc_key(routing_key,is_unserialized=False):
        """
        将明文的routing_key 转换拼装用于变舱的routing_key （同航班）

        """
        if not is_unserialized:
            d = RoutingKey.unserialize(routing_key)
        else:
            d = routing_key
        return '%s|%s|%s|%s|%s' % (d['from_airport'],d['dep_time'],d['to_airport'],d['arr_time'],d['flight_number'])



    @staticmethod
    def unserialize_cc_key(cc_key):
        """
        反序列化CC_KEY

        """
        d = cc_key.split('|')
        return {
            'from_airport':d[0],
            'dep_time': d[1],
            'to_airport': d[2],
            'arr_time': d[3],
            'flight_number': d[4],
            'cabin_grade': d[5],

        }


    @staticmethod
    def trans_un_key(routing_key,is_unserialized=False,is_encrypted=False):
        """
        将明文的routing_key 转换拼装唯一的routing_key （同航班同舱位同供应商渠道同产品）

        :return:
        """
        if not is_unserialized:
            d = RoutingKey.unserialize(routing_key,is_encrypted=is_encrypted)
        else:
            d = routing_key
        return '%s|%s|%s|%s|%s|%s|%s|%s' % (d['from_airport'], d['dep_time'], d['to_airport'], d['arr_time'], d['flight_number'], d['cabin'],d['product'],d['provider_channel'])

    @staticmethod
    def trans_bp_key(routing_key,is_unserialized=False,is_encrypted=False):
        """
        将明文的routing_key 转换拼装唯一的routing_key （同航班同舱位同供应商渠道）
        :return:
        """
        if not is_unserialized:
            d = RoutingKey.unserialize(routing_key,is_encrypted=is_encrypted)
        else:
            d = routing_key
        return '%s|%s|%s|%s|%s|%s|%s' % (d['from_airport'], d['dep_time'], d['to_airport'], d['arr_time'], d['flight_number'], d['cabin'],d['provider_channel'])


if __name__ == '__main__':
    print Time.change_time(90000)
    print Time.time_str_3()
    print Random.gen_ratio(min=0.5,max=0.8)
    # print type(Random.gen_mobile())
    # print cn_name_to_pinyin(u'我非').upper()
    # print Random.gen_full_name()
    # print Random.gen_request_id()
    # print modify_pp('EI12321Z')
    # print Random.gen_mobile()
    # print Random.gen_mobile()
    # print Time.change_time(0)
    # print RoutingKey.serialize(from_airport='CAN',dep_time=Time.curr_date_obj(),to_airport='SHA',arr_time=Time.curr_date_obj(),flight_number='MU1234',product='COMMON',cabin='B',adult_price=1000.0,adult_tax=80.0,provider_channel='CEAIR',child_price=0.0,child_tax=0.0,inf_price=0.0,inf_tax=0.0)
    # print RoutingKey.unserialize('U2ahZ2Xy8lYld3XylWYlNGfw4CM8BjLwwHMuADfw4CM8BDO8BjLwkjMzwnTP1UTPNEfKxXM0MTNV1EfpETL9Q3ckNXaf1GdgwiN0MTP5FGZ59Vb0BCLy0TehR2df1GdgwCM9MWZz9Vb0BCL1QTPulWbf1GdgwCNx0jc19Gaf1GdgwiMx0TehRWbf1GdgwiMx0jbv12XtRHIsgTMwITPyFWZ59Vb0hSZtlGdfR3Y1JHdz5SZtlGd8hlWTxXKx0SP0NHZzl2XtRHIsYDNz0TehRWef1GdgwiM9kXYkd3XtRHIsATPjV2cf1GdgwCMx0jbp12XtRHIsITM9IXdvh2XtRHIsITM9kXYk12XtRHIsITM942bt9Vb0BCL4EDMy0jchVWef1GdoUWbpR3X0NWdyR3cuUWbpRHfBh0U=',is_encrypted=True)
    # print RoutingKey.unserialize('CAN|201811071020|SHA|201811071020|MU1234|B|COMMON|1000.0|80.0|0.0|0.0|0.0|0.0|CEAIR', is_encrypted=False)
    # print RoutingKey.dynamic_serialize(from_airport='CAN',dep_time=Time.curr_date_obj(),to_airport='SHA',arr_time=Time.curr_date_obj(),flight_number='MU1234',cabin='B')
    # print RoutingKey.trans_cp_key('CAN|201811071020|SHA|201811071020|MU1234|B|COMMON|1000.0|80.0|0.0|0.0|0.0|0.0|CEAIR')

    # mobile = '230903199004090819'
    # while 1:
    #     time.sleep(1)
    #     mobile = modify_ni(mobile)
    #     print mobile
