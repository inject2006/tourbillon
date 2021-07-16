# -*- coding: utf-8 -*-


import hashlib
import json
import re
import time
import uuid
import datetime
import pony.orm.core
from datetime import datetime as datetime_format,date as date_format
from pony import orm
from pony.orm import LongStr

db = orm.Database()
extra_db = orm.Database()

class __objdict(dict):
    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            raise AttributeError("No such attribute: " + name)

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        if name in self:
            del self[name]
        else:
            raise AttributeError("No such attribute: " + name)


def dictobj(cls):
    """
    系统统一采用model模型，该函数将模型转换成字典，依然不会丢失模型的相关属性名称和默认值，主要用于自动化仓库调用
    :param cls:
    :return:
    """
    d = {}
    di = cls.__dict__['_new_attrs_']
    for k in di:
        if not isinstance(k, pony.orm.core.PrimaryKey):
            if isinstance(k, pony.orm.core.Optional) or isinstance(k, pony.orm.core.Required):
                if 'reverse' not in k.name:
                    d[k.name] = k.default
            elif isinstance(k, pony.orm.core.Set):
                d[k.name] = []
            else:
                pass
    return d


class FFPAccount(db.Entity):
    """
    航司会员账号库
    CREATE TABLE ffp_account
CREATE TABLE ffp_account
(
    id INT(11) PRIMARY KEY NOT NULL AUTO_INCREMENT,
    username VARCHAR(80) NOT NULL,
    carrier VARCHAR(32) NOT NULL,
    reg_name VARCHAR(32) NOT NULL,
    reg_mobile VARCHAR(32) NOT NULL,
    reg_pid VARCHAR(32) NOT NULL,
    reg_passport VARCHAR(32) NOT NULL,
    reg_birthdate VARCHAR(32) NOT NULL,
    reg_gender VARCHAR(32) NOT NULL,
    reg_card_type VARCHAR(32) NOT NULL,
    reg_date DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    reverse1 VARCHAR(64) NOT NULL,
    reverse2 VARCHAR(64) NOT NULL,
    reverse3 VARCHAR(64) NOT NULL,
    reverse4 VARCHAR(64) NOT NULL,
    reverse5 VARCHAR(64) NOT NULL,
    reverse6 VARCHAR(64) NOT NULL,
    reverse7 VARCHAR(64) NOT NULL
);
CREATE UNIQUE INDEX username ON ffp_account (username);
    """
    _table_ = 'ffp_account'

    username = orm.Optional(str, 80, default='')
    password = orm.Optional(str, 32, default='')
    provider = orm.Optional(str, 32, default='')  # 供应商
    reg_name = orm.Optional(str, 32, default='')
    reg_mobile = orm.Optional(str, 32, default='')
    reg_pid = orm.Optional(str, 32, default='')
    reg_passport = orm.Optional(str, 32, default='')
    reg_birthdate = orm.Optional(str, 32, default='')
    reg_gender = orm.Optional(str, 32, default='')
    reg_card_type = orm.Optional(str, 32, default='')  # 卡类型 NI 身份证 PP-护照GA - 港澳通行证 TW - 台湾通行证 TB - 台胞证 HX -回乡证 HY - 国际海员证
    reg_date = orm.Required(datetime_format, sql_default='CURRENT_TIMESTAMP')  # 注册日期
    reg_person = orm.Optional(lambda: Person)
    flight_orders = orm.Set(lambda: FlightOrder, lazy=True)
    sub_orders = orm.Set(lambda: SubOrder, lazy=True)
    is_modified_card_no = orm.Optional(int, default=0,index=True)
    reverse1 = orm.Optional(str, 64, nullable=True)
    reverse2 = orm.Optional(str, 64, nullable=True)
    reverse3 = orm.Optional(str, 64, nullable=True)
    reverse4 = orm.Optional(str, 64, nullable=True)
    reverse5 = orm.Optional(str, 64, nullable=True)
    reverse6 = orm.Optional(int)
    reverse7 = orm.Optional(int)

    def __repr__(self):
        return '<User: %s>' % self.username

    def get_id(self):
        return self.id

    def has_perm(self, perm):
        u"""检查权限"""
        perms = [perm.codename for perm in self.permissions if perm.value == 1]
        return perm in perms

    def verify_password(self, password):
        u""" 校验密码 """
        return check_password_hash(self.pwd, password)

    @property
    def nickname(self):
        return self.username.split('@')[0]


class Person(db.Entity):
    """
    用户信息库
    """
    _table_ = 'person'

    name = orm.Optional(unicode, 64, default='',index=True)
    last_name = orm.Optional(str, 64, default='')
    first_name = orm.Optional(str, 64, default='')
    birthdate = orm.Optional(date_format)  # 生日 格式 YYYYMMDD
    gender = orm.Optional(str, 4, default='')  # 性别 F M
    age_type = orm.Optional(str, 4, default='ADT')  # ADT CHD INF
    nationality = orm.Optional(str, 8, default='')  # 国籍，国家二字码
    card_type = orm.Optional(str, 32, default='')  # 主要证件类型 NI 身份证 PP-护照GA - 港澳通行证 TW - 台湾通行证 TB - 台胞证 HX -回乡证 HY - 国际海员证
    card_ni = orm.Optional(str, 32, default='',index=True)  # 身份证
    card_pp = orm.Optional(str, 32, default='',index=True)  # 护照
    card_ga = orm.Optional(str, 32, default='')  # 港澳通行证
    card_tw = orm.Optional(str, 32, default='')  # 台湾通行证
    card_issue_place = orm.Optional(str, 8, default='')  # 证件发行国家 国家二字码
    card_expired = orm.Optional(str, 16, default='')  # 证件有效期，格式 YYYYMMDD
    address = orm.Optional(str, 200, default='')  # 详细地址
    postcode = orm.Optional(str, 32, default='')  # 邮编
    mobile = orm.Optional(str, 32, default='',index=True)  # 联系人手机
    email = orm.Optional(str, 128, default='')  # 邮箱
    ffp_accounts = orm.Set(lambda: FFPAccount, lazy=True)  # 所注册航司账号
    flight_orders = orm.Set(lambda: Person2FlightOrder, lazy=True)
    reverse1 = orm.Optional(str, 64, nullable=True)
    reverse2 = orm.Optional(str, 64, nullable=True)
    reverse3 = orm.Optional(str, 64, nullable=True)
    reverse4 = orm.Optional(str, 64, nullable=True)
    reverse5 = orm.Optional(str, 64, nullable=True)
    reverse6 = orm.Optional(int)
    reverse7 = orm.Optional(int)


class Person2FlightOrder(db.Entity):
    """
    订单关联用户表
    用于确定证件类型
    """
    _table_ = 'person_2_flight_order'
    person = orm.Optional(lambda: Person)
    flight_order = orm.Optional(lambda: FlightOrder)
    sub_order =  orm.Set(lambda: SubOrder)
    ticket_no = orm.Optional(str, 64, default='',index=True)  # 需要回填的票号
    used_card_type = orm.Optional(str, 32, default='NA',index=True)  # 主要证件类型 NI 身份证 PP-护照GA - 港澳通行证 TW - 台湾通行证 TB - 台胞证 HX -回乡证 HY - 国际海员证 NA- 代表无关联
    used_card_no = orm.Optional(str,32,default='',index=True)  # 存储本次order所使用的证件号，冗余字段
    passenger_id = orm.Optional(str, 64, default='',index=True)  # 用于航司回传id
    modified_card_no = orm.Optional(str,32,default='',index=True) # 修改后的证件号
    pnr = orm.Optional(str, 64, nullable=True)
    reverse2 = orm.Optional(str, 64, nullable=True)
    reverse3 = orm.Optional(str, 64, nullable=True)
    reverse4 = orm.Optional(int)
    reverse5 = orm.Optional(int)

    def current_age_type(self,from_date=None,is_aggr_chd_adt = False):
        """
        current_age_type 是否聚合 chd和inf 只显示 chd
        from_date  出发日期 如果不填写按照当前日期进行判断
        根据证件或者生日返回实际日期
        研究了东航，发现是根据行程日期那天你是否成年来决定你是的年龄段
        :return:
        """
        adt_tag = 'ADT'
        chd_tag = 'CHD'
        if is_aggr_chd_adt:
            inf_tag = 'CHD'
        else:
            inf_tag = 'INF'
        if from_date:
            from_date_obj = datetime.datetime.strptime(str(from_date), '%Y-%m-%d')
        else:
            from_date_obj = datetime.datetime.now()
        if self.person.card_ni:
            card_date_obj = datetime.datetime.strptime(self.person.card_ni[6:14],"%Y%m%d")
            if ( from_date_obj - card_date_obj).days < 365*2:
                return inf_tag
            elif 365*2 < (from_date_obj - card_date_obj).days < 365*12:
                return chd_tag
            elif 365*12 < (from_date_obj - card_date_obj).days :
                return adt_tag
        elif self.person.birthdate:
            birthdate_obj = datetime.datetime.strptime(str(self.person.birthdate),'%Y-%m-%d')
            if (from_date_obj - birthdate_obj).days < 365*2:
                return inf_tag
            elif 365*2 < (from_date_obj - birthdate_obj).days < 365*12:
                return chd_tag
            elif 365*12 < (from_date_obj - birthdate_obj).days :
                return adt_tag
        else:
            return 'ADT'
class Contact(db.Entity):
    """
    联系人库
    """
    _table_ = 'contact'

    name = orm.Optional(str, 64, default='',index=True)  # 中文、英文、拼音都可以
    address = orm.Optional(str, 200, default='')  # 详细地址
    postcode = orm.Optional(str, 32, default='')  # 邮编
    mobile = orm.Optional(str, 32, default='')  # 联系人手机
    email = orm.Optional(str, 128, default='')  # 邮箱
    flight_order = orm.Optional(lambda: FlightOrder)
    sub_orders =  orm.Set(lambda: SubOrder)




class FlightRouting(db.Entity):
    _table_ = 'flight_routing'

    # 航线信息
    routing_key = orm.Optional(str, 512, default='',index=True)  # 航司会通过自己的方式生成每个航班的key
    routing_key_detail = orm.Optional(str, 512, default='')  #

    # 价格信息
    child_price_forsale = orm.Optional(float, default=0)  # 售价
    adult_price_forsale = orm.Optional(float, default=0)  # 售价
    inf_price_forsale = orm.Optional(float, default=0)  # 售价
    publish_price = orm.Optional(float, default=0)  # 【公布运价强校验】成人公布价，不含税,当productType=0时必须返回，此项同程将做公布运价校验用，其他类型允许返回默认值0
    adult_price = orm.Optional(float, default=0)  # 成人单价，不含税【正整数】
    adult_price_discount = orm.Optional(int, default=100)  # 折扣 100 代表无折扣 98 代表98折
    adult_full_price = orm.Optional(float, default=0)  # 全价
    adult_tax = orm.Optional(float, default=0)  # 成人税费【整数，最小为0】按照segments数进行收取 国内为60 国外另外考虑
    child_publish_price = orm.Optional(float, default=0)  # 【公布运价强校验】儿童公布价，不含税，若无法提供请返回默认值0
    child_price = orm.Optional(float, default=0)  # 儿童公布价，不含税【成人+儿童时必须返回】，若无法提供请返回默认值0
    child_tax = orm.Optional(float, default=0)  # 儿童税费，【成人+儿童时必须返回】，若无法提供请返回默认值0
    inf_price = orm.Optional(float, default=0)  # 婴儿价，不含税【成人+儿童时必须返回】，若无法提供请返回默认值0
    inf_tax = orm.Optional(float, default=0)  # 婴儿税费，【成人+儿童时必须返回】，若无法提供请返回默认值0
    currency = orm.Optional(str, 8, default='CNY')  # 报价币种，默认要返回CNY，表示报价为人民币币种；若需使用外币币种进行报价，需提前沟通同程，否则报价将被过滤！

    nationality_type = orm.Optional(int, default=0)  # 乘客国籍类型: 0.表示没有国籍限制，1.表示仅适用，2.表示不适用 若无法提供请返回默认值0
    nationality = orm.Optional(str, 8, default='')  # 乘客国籍，可以为空，若输入则为标准国家二字码，多个用,逗号‘，’分隔， 例如 CN,US；最大长度100个字符。若无法提供请返回默认值’’。
    adult_age_restriction = orm.Optional(str,
                                         8, default='')  # 成人适用年龄区间，使用“-”表示“至”，例如*-12，表示12岁及以下；若无表示无限制，仅支持录入一个年龄段；最大长度10个字符, 暂时不支持有年龄限制的行程。若无法提供请返回默认值’’。
    ticket_invoice_type = orm.Optional(int, default=0)  # 报销凭证类型： 0 行程单/1 旅行发票,
    reservation_type = orm.Optional(str,
                                    8,
                                    default='')  # 【公布运价强校验】订座系统：GDS使用IATA标准2字代码 1E：TravelSky 1A：Amadeus 1B：Abacus 1S：Sabre 1P：WorldSpan 1G：Galileo 航司官网使用IATA标准航司2字代码标示，如MU：东航官网 运价类型为GDS公布运价时，此项为必须项，其他选填。
    validating_carrier = orm.Optional(str,
                                      8, default='')  # 【公布运价强校验】出票航司，整个行程只能赋一个航司；如不赋值会取行程第一航段的carrier作为出票航司，productType=0将做公布运价校验;
    fare_basis = orm.Optional(str,
                              32, default='')  # 【公布运价强校验】运价基础，每航段1个，使用“/”分割。同程做公布运价校验用，productType=0时此处不能为空串其他产品类型时允许返回空串，不允许返回null；最大长度100个字符
    min_passenger_count = orm.Optional(int, default=1)  # 最小出行人数【默认要返回1】
    max_passenger_count = orm.Optional(int, default=9)  # 最大出行人数【默认要返回9】
    product_type = orm.Optional(str,16)  # 运价类型：0: GDS公布运价 1:GDS私有运价 2:航司官网产品  3:廉价航司产品 4:特价产品  若无法提供请返回默认值0
    is_include_operation_carrier = orm.Optional(int, default=0) # 是否包含共享承运航段

    segment_min_cabin_count = orm.Optional(int, default=0) # 统计所有航段中座位最少的航段，并记录其数量，判断订票人数航线是否满足靠此字段。
    from_segments = orm.Set(lambda: FlightSegment, reverse='from_flight_routing', lazy=True,cascade_delete=True)
    ret_segments = orm.Set(lambda: FlightSegment, reverse='ret_flight_routing', lazy=True,cascade_delete=True)
    flight_order = orm.Optional(lambda: FlightOrder)
    sub_orders = orm.Set(lambda: SubOrder)
    sub_orders_raw_routing = orm.Set(lambda: SubOrder)
    request_id = orm.Optional(str, 16, nullable=True)  # 关联ota验价时候的request_id

    reverse1 = orm.Optional(str, 64, nullable=True)
    reverse2 = orm.Optional(str, 64, nullable=True)
    reverse3 = orm.Optional(str, 64, nullable=True)
    reverse4 = orm.Optional(str, 64, nullable=True)
    reverse5 = orm.Optional(str, 64, nullable=True)
    reverse6 = orm.Optional(int)
    reverse7 = orm.Optional(int)

# OTA 订单状态 待出票READY_TO_ISSUE ,已取消 CANCEL, 已确认ORDER_CONFIRM ,已出票 ISSUE_FINISH, 已驳回ISSUE_FAIL
OTA_ORDER_STATUS = {
    'MANUAL_ORDER':'人工订单',
    'ORDER_INIT': '订单初始化完成',  #自定义
    'READY_TO_ISSUE': '待出票',
    'CANCEL': '已取消',
    'ORDER_CONFIRM': '已确认',
    'ISSUE_FINISH': '已出票',
    'ISSUE_FAIL': '已驳回(取消)',
    'REFUND': '退票',
    'CHANGE': '改签',
    'MANUAL_ISSUE':'人工完成出票',
    'NOCABIN': '舱位不满足',
    'PRICERISE': '价格上升',
    'NOFLIGHT': '无航班',
    'ERROR': '异常错误',
    'PROVIDER_ERROR': '供应商侧异常',
    'CERTIFICATE_ERROR': '证件验证不通过',
    'FAILED': '订单预检失败',
    'NOCHDPRICE':'无儿童价（可能无儿童舱）',
'TOO_OLD_TO_BOARDING':'年龄过大',
'TOO_YOUNG_TO_BOARDING':'年龄过小',
    'TOO_MANY_CHILD':'小孩过多',
    'SEARCH_FAIL':'航班搜索失败',
    'NEED_MANUAL_DOWNGRADE':'请人工降舱',
    'REPLACED':'已被替换',
    'TAKE_SEAT_FAILED': '占位失败',
    'TIMEOUT':'超时关闭',
}

# 操作订单状态
PROVIDERS_STATUS = {
    'ORDER_INIT':{'cn_desc':'初始化状态','status_type':'success','status_category':'ISSUE_PROCESS','is_display':True},
'NO_SUB_ORDER':{'cn_desc':'无关联子订单','status_type':'success','status_category':'ISSUE_CANCEL','is_display':True},
    'PART_FAIL':{'cn_desc':'部分失败','status_type':'fail','status_category':'ISSUE_PROCESS','is_display':False},
'PART_MANUAL':{'cn_desc':'部分人工','status_type':'manual','status_category':'ISSUE_PROCESS','is_display':False},
    'ALL_SUCCESS':{'cn_desc':'全部出票成功','status_type':'success','status_category':'ISSUE_SUCCESS','is_display':True},
'TEST_ORDER':{'cn_desc':'测试订单','status_type':'manual','status_category':'ISSUE_PROCESS','is_display':True},
'BACKFILL_SUCCESS':{'cn_desc':'回填票号成功','status_type':'success','status_category':'ISSUE_SUCCESS','is_display':True},
'BACKFILL_FAIL':{'cn_desc':'回填票号失败','status_type':'fail','status_category':'ISSUE_PROCESS','is_display':False},
'AFTER_SALES_PROCESSING': {'cn_desc': '退改签处理中', 'status_type': 'manual', 'status_category': 'ISSUE_CANCEL','is_display':True},
    'MANUAL_CANCEL': {'cn_desc': '人工取消', 'status_type': 'manual', 'status_category': 'ISSUE_CANCEL','is_display':True},
    'MANUAL_RERUND': {'cn_desc': '人工退票', 'status_type': 'manual', 'status_category': 'ISSUE_PROCESS','is_display':True},
    'MANUAL_CHANGE': {'cn_desc': '人工改签', 'status_type': 'manual', 'status_category': 'ISSUE_PROCESS','is_display':True},
    'MANUAL_ISSUE': {'cn_desc': '人工完成下单出票', 'status_type': 'manual', 'status_category': 'ISSUE_PROCESS','is_display':True},
'TIMEOUT': {'cn_desc': '订单已超时（一天以上）自动关闭', 'status_type': 'system', 'status_category': 'ISSUE_PROCESS','is_display':False},

}


class FlightOrder(db.Entity):
    """
    订单库

    """
    _table_ = 'flight_order'

    routing_range = orm.Optional(str, 8, default='I2I')  # 区分国际航班和国内航班  IN 国内  OUT 国际
    trip_type = orm.Optional(str, default='OW')  # 行程类型 OW：单程 RT：往返
    session_id = orm.Optional(str, 64, default='',index=True)  # 会话标识
    passengers = orm.Set(lambda: Person2FlightOrder, lazy=True,cascade_delete=False)  # 乘客信息
    contacts = orm.Set(lambda: Contact, lazy=True,cascade_delete=False)  # 联系人信息
    routing = orm.Optional(lambda: FlightRouting,cascade_delete=False)  # 航线信息

    sub_orders = orm.Set(lambda: SubOrder, lazy=True,cascade_delete=True) # 关联子订单
    adt_count = orm.Optional(int,default=0)  # 成人个数
    chd_count = orm.Optional(int,default=0)  # 儿童个数
    inf_count = orm.Optional(int,default=0)  # 婴儿个数

    from_date = orm.Optional(date_format,index=True)  # 去程时间
    ret_date = orm.Optional(date_format,index=True,nullable=True)  # 返程时间
    from_airport = orm.Optional(str, 8, default='',index=True)  # 出发机场
    to_airport = orm.Optional(str, 8, default='',index=True)  # 到达机场
    from_city = orm.Optional(str, 8, default='')  # 出发城市
    to_city = orm.Optional(str, 8, default='')  # 到达城市
    from_country = orm.Optional(str, 8, default='')  # 出发国家
    to_country = orm.Optional(str, 8, default='')  # 到达国家

    # tourbillon internal
    ota_name = orm.Optional(str, 32, default='',index=True)  # 所关联OTA简称
    ota_order_status = orm.Optional(str, 32, default='',index=True,volatile=True)  # ota订单状态  订单状态: 待出票READY_TO_ISSUE ,已取消 CANCEL, 已确认ORDER_CONFIRM ,已出票 ISSUE_FINISH, 已驳回ISSUE_FAIL
    ota_order_id = orm.Optional(str, 32, default='',index=True)  # OTA 订单号
    ota_query_time = orm.Optional(datetime_format,index=True)  # OTA 查询时间
    ota_create_order_time = orm.Optional(datetime_format,index=True)  # OTA 下单时间
    ota_pay_time = orm.Optional(datetime_format)  # 客户支付时间
    ota_backfill_time = orm.Optional(datetime_format)  # 回填票号时间
    ota_adult_price = orm.Optional(float, default=0) # 出售给ota的成人票价
    ota_child_price = orm.Optional(float, default=0)  # 出售给ota的儿童票价
    ota_inf_price = orm.Optional(float, default=0)  # 出售给ota的婴儿票价

    all_finished_time = orm.Optional(datetime_format) # 全部完成时间
    process_duration = orm.Optional(int, default=0)  # 从初始化订单到全部完成的耗时时间
    ota_pay_price = orm.Optional(float)  # ota订单总价
    operation_product_type = orm.Optional(str, 32, default='')  # 确定产品类型  会员、VISA活动、618活动等单一或者组合类型
    operation_product_mode = orm.Optional(str, 32, default='')  # 订单模式  A2A A2B
    is_manual = orm.Optional(int, default=0,index=True)  # 是否有子订单已经人工介入 1 介入 0 未介入
    assoc_order_id = orm.Optional(str, 64, default='',index=True)  # 可用于串联查询、验价逻辑
    ota_product_code = orm.Optional(int, default=0, index=True)  # 0.普通产品 1.小团产品 2.快速出票 3.留学生产品 4.组合产品 5 行李套餐

    providers_status = orm.Optional(str, 32, default='',index=True,volatile=True)  # 供应商状态，所有供应商的状态
    providers_total_price = orm.Optional(float)  # 成本总价 子订单价格相加
    provider_channel = orm.Optional(str,32,default='')  # 供应商渠道
    provider = orm.Optional(str, 32, default='',index=True)  # 供应商名称
    pnr_code = orm.Optional(str, 30, default='')  # pnr 编码
    ffp_account = orm.Optional(lambda: FFPAccount,cascade_delete=False)  # 关联账号
    meta = orm.Optional(lambda: FlightOrderMeta,cascade_delete=False)  #
    income_expense_details = orm.Set(lambda: IncomeExpenseDetail,cascade_delete=False)  # 关联支付信息
    comment = orm.Optional(str,300, default='')  # 人工介入时候可以填写备注信息
    rkey_pax_hash =  orm.Optional(str, 32, default='',index=True) # 将乘机人跟routing_key 进行hash 防止重复下单
    ota_type = orm.Optional(str, 32, default='',index=True)  # ota类型，是对接方式还是界面人工下单方式 API WEB
    is_test_order = orm.Optional(int, default=0,index=True)  # 是否为测试订单
    is_cabin_changed = orm.Optional(int, default=0,index=True) # 是否变舱
    quote_summaries = orm.Optional(str, 200, nullable=True)   # 供应商报价汇总  JSON格式 包括 舱位和价格
    update_time = orm.Optional(datetime_format, index=True)  # 下单时间

    ota_extra_name = orm.Optional(str, 64, nullable=True)
    ota_extra_group = orm.Optional(str, 64, nullable=True)
    reverse2 = orm.Optional(str, 64, nullable=True)
    reverse3 = orm.Optional(str, 64, nullable=True)
    reverse4 = orm.Optional(str, 64, nullable=True)
    reverse5 = orm.Optional(str, 64, nullable=True)
    reverse6 = orm.Optional(int)
    reverse7 = orm.Optional(int)

# 操作订单状态
PROVIDER_ORDER_STATUS = {
    'ORDER_INIT':{'cn_desc':'初始化状态','status_type':'success','status_category':'ISSUE_PROCESS','is_display':True},
    'SEARCH_SUCCESS': {'cn_desc':'查询成功','status_type':'success','status_category':'ISSUE_PROCESS','is_display':False},
    'SEARCH_FAIL':{'cn_desc':'查询失败','status_type':'fail','status_category':'ISSUE_PROCESS','is_display':False},
    'REGISTER_SUCCESS':{'cn_desc':'注册成功','status_type':'success','status_category':'ISSUE_PROCESS','is_display':False},
    'REGISTER_FAIL':{'cn_desc':'注册失败','status_type':'fail','status_category':'ISSUE_PROCESS','is_display':False},
    'LOGIN_SUCCESS':{'cn_desc':'登陆成功','status_type':'success','status_category':'ISSUE_PROCESS','is_display':False},
    'LOGIN_FAIL':{'cn_desc':'登陆失败','status_type':'fail','status_category':'ISSUE_PROCESS','is_display':False},
    'CHECK_ORDER_STATUS_SUCCESS': {'cn_desc': '订单状态检查成功', 'status_type': 'success','status_category':'ISSUE_PROCESS','is_display':False},
    'CHECK_ORDER_STATUS_FAIL': {'cn_desc': '订单状态检查失败', 'status_type': 'fail','status_category':'ISSUE_PROCESS','is_display':False},
    'GET_COUPON_SUCCESS':{'cn_desc':'优惠券领取成功','status_type':'success','status_category':'ISSUE_PROCESS','is_display':False},
    'GET_COUPON_FAIL':{'cn_desc':'优惠券领取失败','status_type':'fail','status_category':'ISSUE_PROCESS','is_display':False},
    'BOOK_SUCCESS_AND_WAITING_PAY':{'cn_desc':'订票成功并等待支付','status_type':'success','status_category':'ISSUE_PROCESS','is_display':True},
    'BOOK_FAIL':{'cn_desc':'订票失败','status_type':'fail','status_category':'ISSUE_PROCESS','is_display':False},
    'BOOK_FAIL_NO_CABIN':{'cn_desc':'订票失败（已无座位）','status_type':'fail','status_category':'ISSUE_PROCESS','is_display':False},
    'PAY_SUCCESS':{'cn_desc':'支付成功','status_type':'success','status_category':'ISSUE_PROCESS','is_display':False},
    'PAY_FAIL':{'cn_desc':'支付失败','status_type':'fail','status_category':'ISSUE_PROCESS','is_display':False},
    'TICKET_NO_GET_FAIL':{'cn_desc':'票号拉取失败','status_type':'fail','status_category':'ISSUE_PROCESS','is_display':False},

    'ISSUE_FAIL':{'cn_desc':'出票失败','status_type':'fail','status_category':'ISSUE_PROCESS','is_display':False},
    'ISSUE_CANCEL':{'cn_desc':'已被取消','status_type':'fail','status_category':'ISSUE_PROCESS','is_display':False},
    'TIMEOUT':{'cn_desc':'订单处理超时关闭','status_type':'system','status_category':'ISSUE_PROCESS','is_display':False},
    'SET_AUTOPAY':{'cn_desc':'准许自动支付','status_type':'success','status_category':'ISSUE_PROCESS','is_display':True},
    'ISSUE_SUCCESS_AND_NEED_MODIFIED_CARD_NO':{'cn_desc':'出票成功并需要致电客服修改证件','status_type':'manual','status_category':'ISSUE_PROCESS','is_display':True},

    # 结束状态
    'MANUAL_CANCEL': {'cn_desc': '人工取消', 'status_type': 'manual', 'status_category': 'ISSUE_CANCEL','is_display':True},
    'MANUAL_RERUND': {'cn_desc': '人工退票', 'status_type': 'manual', 'status_category': 'ISSUE_PROCESS','is_display':True},
    'MANUAL_CHANGE': {'cn_desc': '人工改签', 'status_type': 'manual', 'status_category': 'ISSUE_PROCESS','is_display':True},
    'MANUAL_ISSUE': {'cn_desc': '人工完成下单出票', 'status_type': 'manual', 'status_category': 'ISSUE_SUCCESS','is_display':True},
    'ISSUE_SUCCESS':{'cn_desc':'出票成功','status_type':'success','status_category':'ISSUE_SUCCESS','is_display':True},
    'SYSTEM_ERROR':{'cn_desc':'系统错误','status_type':'system','status_category':'ISSUE_PROCESS','is_display':True},
    'TEST_ORDER':{'cn_desc':'测试订单','status_type':'manual','status_category':'ISSUE_PROCESS','is_display':True},
    'FAIL_CANCEL': {'cn_desc': '占位（搜索）失败取消', 'status_type': 'manual', 'status_category': 'ISSUE_CANCEL','is_display':True},

}

class SubOrder(db.Entity):
    """
    子订单，由主订单拆分形成
    """
    _table_ = 'sub_order'

    routing_range = orm.Optional(str, 8, default='IN')  # 区分国际航班和国内航班  IN 国内  OUT 国际
    trip_type = orm.Optional(str, default='OW')  # 行程类型 OW：单程 RT：往返
    session_id = orm.Optional(str, 64, default='',index=True)  # 会话标识
    passengers = orm.Set(lambda: Person2FlightOrder, lazy=True,cascade_delete=False)  # 乘客信息
    contacts = orm.Set(lambda: Contact, lazy=True)  # 联系人信息
    routing = orm.Optional(lambda: FlightRouting,reverse='sub_orders')  # 航线信息
    raw_routing = orm.Optional(lambda: FlightRouting,reverse='sub_orders_raw_routing')  # 航线信息
    flight_order = orm.Optional(lambda: FlightOrder)  # 关联账号
    adt_count = orm.Optional(int,default=0)  # 成人个数
    chd_count = orm.Optional(int,default=0)  # 儿童个数
    inf_count = orm.Optional(int,default=0)  # 婴儿个数

    from_date = orm.Optional(date_format,index=True)  # 去程时间
    ret_date = orm.Optional(date_format,index=True,nullable=True)  # 返程时间
    from_airport = orm.Optional(str, 8, default='',index=True)  # 出发机场
    to_airport = orm.Optional(str, 8, default='',index=True)  # 到达机场
    from_city = orm.Optional(str, 8, default='')  # 出发城市
    to_city = orm.Optional(str, 8, default='')  # 到达城市
    from_country = orm.Optional(str, 8, default='')  # 出发国家
    to_country = orm.Optional(str, 8, default='')  # 到达国家

    # tourbillon internal

    operation_product_type = orm.Optional(str, 32, default='')  # 确定产品类型  会员、VISA活动、618活动等单一或者组合类型
    operation_product_mode = orm.Optional(str, 32, default='')  # 订单模式  A2A A2B
    is_manual = orm.Optional(int, default=0,index=True)  # 是否已经人工介入 1 介入 0 未介入
    provider_order_id = orm.Optional(str, 32, default='',index=True)  # 用于付款的真实订单，一般是航司，也可能是其他OTA
    provider_order_status = orm.Optional(str, 100, default='',index=True,volatile=True)  # 供应商状态
    provider_price = orm.Optional(float)  # 成本总价
    provider_fee = orm.Optional(float) # 供应商手续费
    provider_channel = orm.Optional(str,32,default='')  # 供应商渠道
    provider = orm.Optional(str, 32, default='',index=True)  # 供应商名称
    pnr_code = orm.Optional(str, 30, default='')  # pnr 编码
    ffp_account = orm.Optional(lambda: FFPAccount)  # 关联账号
    income_expense_details = orm.Set(lambda: IncomeExpenseDetail)  # 关联支付信息
    comment = orm.Optional(str,300, default='')  # 人工介入时候可以填写备注信息
    create_time = orm.Optional(datetime_format,index=True)  # 下单时间
    issue_success_time = orm.Optional(datetime_format)  # 出票完成时间，需要计算
    process_duration = orm.Optional(int, default=0)  # 从初始化订单到全部完成的耗时时间
    extra_data = orm.Optional(LongStr, default='') # 存储供应商订单接口返回结果
    out_trade_no = orm.Optional(str, 64, default='') # 支付商户流水号
    update_time = orm.Optional(datetime_format, index=True)  # 下单时间
    reverse1 = orm.Optional(str, 64, nullable=True)
    reverse2 = orm.Optional(str, 64, nullable=True)
    reverse3 = orm.Optional(str, 64, nullable=True)
    reverse4 = orm.Optional(str, 64, nullable=True)
    reverse5 = orm.Optional(str, 64, nullable=True)
    reverse6 = orm.Optional(int)
    reverse7 = orm.Optional(int)

class FlightOrderMeta(db.Entity):
    """
    存储订单元数据，包含账号、乘客、联系人、routing segments所有信息，用于直接下单
    独立出来防止order表过大，影响性能
    """
    _table_ = 'flight_order_meta'
    flight_order = orm.Optional(lambda: FlightOrder)  # 关联订单
    json_data = orm.Optional(LongStr,default='{}')  # 存储json数据


class FlightSegment(db.Entity):
    """
    航段信息
    """
    _table_ = 'flight_segment'
    carrier = orm.Optional(str, 16, default='',index=True)  # 航司
    dep_airport = orm.Optional(str, 8, default='',index=True)  # 出发机场IATA 三字码
    dep_time = orm.Optional(datetime_format,index=True)  # 起飞日期时间，格式：YYYYMMDDHHMM例：201702041305表示2017年 2 月 04 日 13 时 5 分
    arr_airport = orm.Optional(str, 8, default='',index=True)  # 到达机场IATA 三字码
    arr_time = orm.Optional(datetime_format,index=True)  # 到达日期时间，格式：YYYYMMDDHHMM例：201702041305表示2017年 2 月 04 日 13 时 5 分
    stop_cities = orm.Optional(str, 64, default='')  # 经停城市
    stop_airports = orm.Optional(str, 64, default='')  # 经停机场，/分隔机场三字码(如果有经停，必传)
    code_share = orm.Optional(str, default='false')  # 代码共享标识（true 代码共享/false 非代码共享）
    cabin = orm.Optional(str, 8, default='',index=True)  # 舱位
    cabin_count = orm.Optional(int)  # 当前可售舱位个数，用于判断库存是否满足客户需求
    aircraft_code = orm.Optional(str, 8, default='')  # 机型，IATA标准3字码,并过滤下列机型运价信息BUS|ICE|LCH|LMO|MTL|RFS|TGV|THS|THT|TRN|TSL
    flight_number = orm.Optional(str, 16, default='',index=True)  # 航班号，如：CA1234。航班号数字不足四位，补足四位，如 CZ6 需返回 CZ0006
    operating_carrier = orm.Optional(str, 32, default='')  # 实际承运航司，当codeShare=true时， operatingCarrier不能为空
    operating_flight_no = orm.Optional(str, 16, default='')  # 实际承运航班号,如：CA1234。航班号数字不足四位，补足四位，如 CZ6 需返回 CZ0006
    dep_terminal = orm.Optional(str, 16, default='')  # 出发航站楼，使用简写，例如T1
    arr_terminal = orm.Optional(str, 16, default='')  # 抵达航站楼，使用简写，例如T1
    cabin_grade = orm.Optional(str, 8, default='')  # 舱等 头等：F 商务：C 超经：S 经济： Y
    duration = orm.Optional(int)  # 飞行时长（分钟），通过时差转换后的结果，无法提供时请赋值0
    routing_number = orm.Optional(int, default=1)  # 在订单中的顺序
    # virtual_cabin = orm.Optional(str, 8, default='',index=True)  # 虚拟仓位

    refund_info = orm.Optional(str, 200, default='{}')  # 退订规定 JSON存储
    change_info = orm.Optional(str, 200, default='{}')  # 改签规定 JSON存储
    baggage_info = orm.Optional(str, 200, default='{}')  # 行李额规定 JSON存储
    from_flight_routing = orm.Optional(lambda: FlightRouting)
    ret_flight_routing = orm.Optional(lambda: FlightRouting)
    reverse1 = orm.Optional(str, 64, nullable=True)
    reverse2 = orm.Optional(str, 64, nullable=True)
    reverse3 = orm.Optional(str, 64, nullable=True)
    reverse4 = orm.Optional(int)
    reverse5 = orm.Optional(int)




class PaySource(db.Entity):
    """
    支付数据源信息库
    """
    _table_ = 'pay_source'

    source_name = orm.Optional(str,32,default='')  # 名称
    pay_type = orm.Optional(str,32,default='')  # 支付类型 信用卡、支付宝、借记卡
    credit_card_type = orm.Optional(str,32,default='') # 信用卡类型  visa  master_card unionpay  unionpay_visa  unionpay_master_card
    credit_card_idno =  orm.Optional(str,32,default='')  # 信用卡卡号
    issue_bank = orm.Optional(str,32,default='')  # 发卡行
    card_level = orm.Optional(str,32,default='')  # 卡等级
    owner_name = orm.Optional(str,32,default='')  # 持卡人姓名
    owner_pid  = orm.Optional(str,32,default='')  # 持卡人证件
    pay_account =  orm.Optional(str,64,default='')  #  账号
    pay_password =  orm.Optional(str,64,default='')  # 密码
    credit_card_validthru = orm.Optional(str,16,default='')  # 有效期
    credit_card_cvv2 = orm.Optional(str,8,default='')  #
    credit_card_limit = orm.Optional(int) # 信用卡额度
    credit_card_validthru_month = orm.Optional(str,8,default='')  # 有效期完整月份
    credit_card_validthru_year = orm.Optional(str,8,default='')  # 有效期完整年份
    credit_due_day = orm.Optional(str,32,default='') # 还款日，用于通知还款和计算账单
    credit_bill_day =  orm.Optional(str,32,default='') # 账单日，用于通知还款和计算账单
    secure_password = orm.Optional(str,32,default='')  # 安全支付密码
    reverse_mobile = orm.Optional(str,16,default='')  # 预留手机号码
    pay_channel = orm.Optional(str,32,default='')  # 所支持的支付渠道
    belong_to_provider = orm.Optional(str,32,default='')  # 专属为哪个产品
    belong_to_provider_channel = orm.Optional(str, 32, default='')  # 专属为哪个产品
    income_expense_details = orm.Set(lambda: IncomeExpenseDetail)

    reverse1 = orm.Optional(str, 64, nullable=True)
    reverse2 = orm.Optional(str, 64, nullable=True)
    reverse3 = orm.Optional(str, 64, nullable=True)
    reverse4 = orm.Optional(int)
    reverse5 = orm.Optional(int)


PAY_RESULT = {
    'PAYMENTS_MADE':'已支付',
    'PAYMENTS_DUE':'未支付',
    'CHECKCODE_ERROR':'验证码错误',
    'LACK_OF_BALANCE':'余额不足',
    'ABNORMALITY':'卡状态异常',
    'WITHHOLD_ERROR':'代扣失败',
    'FAIL':'交易失败'

}

PAY_CHANNEL = {
    'ALIPAY':'支付宝',
    'ALIPAY_WITHHOLD':'支付宝代扣',
    '99BILL':'块钱',
    'UNIONPAY':'银联',
    'VISA':'VISA',
    'MASTERCARD':'MASTERCARD',
    'OFFLINE':'线下交易',
    'RETURN':'资金原路退回'
}
TRADE_SUB_TYPE = {
    'REFUND':'退票',
    'BUY':'购票'
}

TRADE_TYPE = {
    'INCOME':'收入',
    'EXPENSE':'支出'
}

class IncomeExpenseDetail(db.Entity):
    """
    收支明细
    """
    _table_ = 'income_expense_detail'

    trade_type = orm.Optional(str,32,default='',index=True)  # 交易类型  INCOME 收入  EXPENSE 支出
    trade_sub_type = orm.Optional(str,32,default='',index=True)  # 交易子类型
    flight_order = orm.Optional(lambda: FlightOrder)  # 所关联订单
    sub_order = orm.Optional(lambda: SubOrder) # 所关联子订单
    expense_source =  orm.Optional(lambda: PaySource)  # 所关联支付源，如果是线下交易则不需关联支付源
    expense_source_offline = orm.Optional(str,32,default='')  # 线下交易的交易者信息
    pay_amount = orm.Optional(float, default=0)  # 交易金额
    pay_channel = orm.Optional(str,32,default='',index=True)  # 交易渠道
    income_source =  orm.Optional(str,32,default='',index=True)  # 付款源，一般是OTA 比如 lvmama，如果是线下交易，需要填写交易者姓名信息
    pay_time = orm.Optional(datetime_format, sql_default='CURRENT_TIMESTAMP',index=True)  # 交易时间
    pay_result = orm.Optional(str,32,default='',index=True)  # 支付结果
    comment = orm.Optional(str,1000,default='')  # 人工订单填写相关信息
    assoc_ticket_no =  orm.Optional(str,600,default='')  #相关联票号
    provider_order_id = orm.Optional(str,128,default='')  #该笔支付对应的供应商订单号
    reverse1 = orm.Optional(str, 64, nullable=True)
    reverse2 = orm.Optional(str, 64, nullable=True)
    reverse3 = orm.Optional(str, 64, nullable=True)
    reverse4 = orm.Optional(int)
    reverse5 = orm.Optional(int)




FLIGHT_CRAWLER_TASK_STATUS = {
    'TODO': '等待开始',
    'RUNNING': '运行中',
    'TOSTOP':'等待停止',
    'STOP':'停止',
    'TODELETE':'等待删除'
}


class PrimaryFareCrawlTask(extra_db.Entity):
    """
    主爬虫任务库
    """
    _table_ = 'primary_fare_crawl_task'
    providers = orm.Optional(str, 500, default='[]')  # 爬取供应商，对于ROUTING_CACHE DYNAMIC_FARE任务类型 暂时只能指定一个，对于 PRICE_COMPARISON 可以设置多个，格式 [["provider","provider_channel"]]
    benchmark_provider_channel =  orm.Optional(str, 32, default='')  #  比价功能相关  比价基准供应商，
    crawl_airlines = orm.Optional(LongStr,default='[]')  # 爬取航线，如果task_type 为DYNAMIC_FARE PRICE_COMPARISON 则采用该字段的航线进行爬取
    cabin_grade = orm.Optional(str, 8, default='[]')  # 爬取舱等 JSON ['Y','F','C','S'], # 舱等 头等：F 商务：C 超经：S 经济： Y
    trip_type = orm.Optional(str, 8, default='OW')  # 行程类型 OW：单程 RT：往返
    within_days = orm.Optional(int, default=0)  # 爬取未来天数 为0代表不爬取
    start_day =  orm.Optional(int, default=0) # 从最近哪一天开始，为0代表从当天开始
    stop_profit = orm.Optional(float, default=0)  # 动态运价相关 止盈价
    stop_loss = orm.Optional(float, default=0)  # 动态运价相关 止损价
    estimate_ota_diff_price = orm.Optional(str,32, default='')  # 动态运价相关 预估ota价差 代数式
    bidding_diff_price =  orm.Optional(float, default=0)  # 动态运价相关 竞价价差
    is_enable_auto_put = orm.Optional(int, default=0)  # 是否开启动态投放  1 开启 0 不开启
    task_type = orm.Optional(str, 32, default='',index=True)  # 爬虫类型，ROUTING_CACHE 路由缓存 DYNAMIC_FARE 动态运价
    task_status = orm.Optional(str, 16, default='',index=True)  # 任务状态
    ota_custom_route_strategy = orm.Optional(str, 1000, default='[]')  # 对ota 进行自定义路由策略，爬取不同的供应商数据
    create_time = orm.Optional(datetime_format, sql_default='CURRENT_TIMESTAMP',index=True)  # 任务创建时间
    secondary_tasks = orm.Set(lambda: SecondaryFareCrawlTask,index=True,cascade_delete=True)
    dynamic_fare_repo = orm.Set(lambda: DynamicFareRepo)  # 关联主爬虫ID，用于获取相关策略
    fare_comparison_repo = orm.Set(lambda: FareComparisonRepo)  # 关联主爬虫ID，用于获取相关策略
    task_name = orm.Optional(str, 32, default='',index=True)  # 策略名称
    priority = orm.Optional(int, default=1)  # 运价优先级 1 ~ 999
    ota = orm.Optional(str, 32, default='',index=True)  # 动态运价的 OTA名称
    reverse1 = orm.Optional(str, 64, nullable=True)
    reverse2 = orm.Optional(str, 64, nullable=True)
    reverse3 = orm.Optional(str, 64, nullable=True)
    reverse4 = orm.Optional(int)
    reverse5 = orm.Optional(int)


class FareComparisonRepo(extra_db.Entity):
    """
    比价库
    """

    _table_ = 'fare_comparison_repo'
    primary_fare_crawl_task = orm.Optional(lambda: PrimaryFareCrawlTask)  # 关联主爬虫ID，用于获取相关策略
    from_airport = orm.Optional(str, 8, default='',index=True)  # 出发机场
    to_airport = orm.Optional(str, 8, default='',index=True)  # 到达机场
    flight_number = orm.Optional(str, 32, default='',index=True)  # 聚合航班号信息
    cabin_grade = orm.Optional(str, 32, default='',index=True)  # 聚合舱等信息（参考）
    from_date = orm.Optional(date_format,index=True)  # 去程时间
    ver = orm.Optional(int,default=1)  # 更新版本号，观察变价频繁程度
    update_time = orm.Optional(datetime_format, sql_default='CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP',index=True)  # 更新时间
    hash = orm.Optional(str, 64,unique=True)  # hash 索引 用于更新用
    provider_fc_repo = orm.Set(lambda: ProviderFCRepo)  # 关联供应商价格
    reverse1 = orm.Optional(str, 64, nullable=True)
    reverse2 = orm.Optional(str, 64, nullable=True)
    reverse3 = orm.Optional(str, 64, nullable=True)
    reverse4 = orm.Optional(int)
    reverse5 = orm.Optional(int)

class ProviderFCRepo(extra_db.Entity):
    """
    供应商比价库
    """

    _table_ = 'provider_fc_repo'

    fare_comparison_repo = orm.Optional(lambda: FareComparisonRepo)  # 关联比价主索引
    provider = orm.Optional(str, 32, default='',index=True)  # 航司
    provider_channel = orm.Optional(str, 64, default='',index=True)  # 渠道
    cabin = orm.Optional(str, 32, default='',index=True)  # 聚合舱位信息（参考）
    from_date = orm.Optional(date_format,index=True)  # 去程时间
    cost_price = orm.Optional(float,default=0)  # 供应商成本价  单价+税
    update_time = orm.Optional(datetime_format, sql_default='CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP',index=True)  # 更新时间
    reverse1 = orm.Optional(str, 64, nullable=True)
    reverse2 = orm.Optional(str, 64, nullable=True)


class SecondaryFareCrawlTask(extra_db.Entity):
    """
    辅爬虫任务库
    """
    _table_ = 'secondary_fare_crawl_task'

    provider = orm.Optional(str, 32, default='',index=True)  # 航司
    provider_channel = orm.Optional(str, 64, default='',index=True)  # 渠道
    primary_task_id = orm.Optional(lambda: PrimaryFareCrawlTask,index=True)
    pr = orm.Optional(int,default=1,index=True)  # PR 权重
    last_trig_time = orm.Optional(datetime_format)  # 最后一次触发时间

    from_date = orm.Optional(date_format,index=True)  # 去程时间
    ret_date = orm.Optional(date_format,index=True,nullable=True)  # 返程时间
    from_airport = orm.Optional(str, 8, default='',index=True)  # 出发机场
    to_airport = orm.Optional(str, 8, default='',index=True)  # 到达机场
    from_city = orm.Optional(str, 8, default='',index=True)  # 出发城市
    to_city = orm.Optional(str, 8, default='',index=True)  # 到达城市
    from_country = orm.Optional(str, 8, default='',index=True)  # 出发国家
    to_country = orm.Optional(str, 8, default='',index=True)  # 到达国家

    trip_type = orm.Optional(str, default='OW',index=True)  # 行程类型 OW：单程 RT：往返

    cabin_count_total = orm.Optional(int, default=0)  # 舱位总数
    lowest_price = orm.Optional(float, default=0)  # 当日最低价
    flightcount_cabin_a = orm.Optional(int, default=0)  # >=9座位航班数
    flightcount_cabin_1_8 = orm.Optional(int, default=0)  # 1-8座位航班数 用于权重判断
    flightcount_total = orm.Optional(int, default=0)  # 航班总个数
    start_day = orm.Optional(int, default=0) # 开始天数，用于判断此任务是否要执行
    dl_hash =  orm.Optional(str, 128, default='',unique=True)  # 标识唯一任务
    dl_repo = orm.Set(lambda: FareCrawlRepoDL, lazy=True,cascade_delete=True)  # 对应日航线爬虫库
    task_status = orm.Optional(str, 16, default='',index=True)  # 任务状态
    task_type = orm.Optional(str, 32, default='', index=True)  # 爬虫类型，ROUTING_CACHE 路由缓存 DYNAMIC_FARE 动态运价
    create_time = orm.Optional(datetime_format, sql_default='CURRENT_TIMESTAMP',index=True)  # 任务创建时间
    reverse1 = orm.Optional(str, 64, nullable=True)
    reverse2 = orm.Optional(str, 64, nullable=True)
    reverse3 = orm.Optional(str, 64, nullable=True)
    reverse4 = orm.Optional(int)
    reverse5 = orm.Optional(int)


class FareCrawlRepoDL(extra_db.Entity):
    """
    日航线运价库
    """
    _table_ = 'fare_crawl_repo_dl'

    provider = orm.Optional(str, 32, default='',index=True)  # 航司
    provider_channel = orm.Optional(str, 32, default='',index=True)  # 渠道
    task_id = orm.Optional(lambda: SecondaryFareCrawlTask)  # task关联id
    pr = orm.Optional(int, default=1,index=True)  # PR 权重
    cabin_repo =orm.Set(lambda: FareCrawlRepoCabin,cascade_delete=True)  # 关联舱位运价库

    cabin_count_total = orm.Optional(int, default=0)  # 舱位总数
    lowest_price = orm.Optional(float, default=0)  # 当日最低价
    flightcount_cabin_a = orm.Optional(int, default=0)  # >=9座位航班数
    flightcount_cabin_1_8 = orm.Optional(int, default=0)  # 1-8座位航班数 用于权重判断
    flightcount_total = orm.Optional(int, default=0)  # 航班总个数

    from_date = orm.Optional(date_format,index=True)  # 去程时间
    ret_date = orm.Optional(date_format,index=True,nullable=True)  # 返程时间
    from_airport = orm.Optional(str, 8, default='',index=True)  # 出发机场
    to_airport = orm.Optional(str, 8, default='',index=True)  # 到达机场
    from_city = orm.Optional(str, 8, default='',index=True)  # 出发城市
    to_city = orm.Optional(str, 8, default='',index=True)  # 到达城市
    from_country = orm.Optional(str, 8, default='',index=True)  # 出发国家
    to_country = orm.Optional(str, 8, default='',index=True)  # 到达国家
    # 搜索信息
    routing_range = orm.Optional(str, 8, default='IN',index=True)  # 区分国际航班和国内航班  IN 国内  OUT 国际
    trip_type = orm.Optional(str, default='OW',index=True)  # 行程类型 OW：单程 RT：往返


    create_time = orm.Optional(datetime_format, sql_default='CURRENT_TIMESTAMP',index=True)  # 任务创建时间
    reverse1 = orm.Optional(str, 64, nullable=True)
    reverse2 = orm.Optional(str, 64, nullable=True)
    reverse3 = orm.Optional(str, 64, nullable=True)
    reverse4 = orm.Optional(int)
    reverse5 = orm.Optional(int)

class FareCrawlRepoCabin(extra_db.Entity):
    """
    舱位运价
    """
    _table_ = 'fare_crawl_repo_cabin'

    provider = orm.Optional(str, 32, default='')  # 航司
    provider_channel = orm.Optional(str, 16, default='')  # 渠道
    dl_repo = orm.Optional(lambda: FareCrawlRepoDL)  # 关联舱位运价库
    routing_key_detail = orm.Optional(str, 512, default='')  #

    pr = orm.Optional(int, default=1)  # PR 权重

    from_date = orm.Optional(date_format,index=True)  # 去程时间
    ret_date = orm.Optional(date_format,index=True,nullable=True)  # 返程时间
    from_airport = orm.Optional(str, 8, default='',index=True)  # 出发机场
    to_airport = orm.Optional(str, 8, default='',index=True)  # 到达机场
    from_city = orm.Optional(str, 8, default='',index=True)  # 出发城市
    to_city = orm.Optional(str, 8, default='',index=True)  # 到达城市
    from_country = orm.Optional(str, 8, default='',index=True)  # 出发国家
    to_country = orm.Optional(str, 8, default='',index=True)  # 到达国家

    # 价格信息
    adult_price = orm.Optional(float, default=0)  # 成人单价，不含税【正整数】
    adult_full_price = orm.Optional(float, default=0)  # 成人全价
    adult_price_discount = orm.Optional(int, default=100)  # 折扣 100 代表无折扣 98 代表98折
    adult_tax = orm.Optional(float, default=0)  # 成人税费【整数，最小为0】按照segments数进行收取 国内为60 国外另外考虑
    child_price = orm.Optional(float, default=0)  # 儿童公布价，不含税【成人+儿童时必须返回】，若无法提供请返回默认值0
    child_tax = orm.Optional(float, default=0)  # 儿童税费，【成人+儿童时必须返回】，若无法提供请返回默认值0
    product_type = orm.Optional(str,16,index=True)  # 运价类型：0: GDS公布运价 1:GDS私有运价 2:航司官网产品  3:廉价航司产品 4:特价产品  若无法提供请返回默认值0
    # 搜索信息
    routing_range = orm.Optional(str, 8, default='IN',index=True)  # 区分国际航班和国内航班  IN 国内  OUT 国际
    trip_type = orm.Optional(str, default='OW',index=True)  # 行程类型 OW：单程 RT：往返

    # 航段参考信息
    reference_flight_number = orm.Optional(str,16,default='',index=True)
    reference_carrier = orm.Optional(str, 16, default='',index=True)

    create_time = orm.Optional(datetime_format, sql_default='CURRENT_TIMESTAMP',index=True)  # 任务创建时间
    reverse1 = orm.Optional(str, 64, nullable=True)
    reverse2 = orm.Optional(str, 64, nullable=True)
    reverse3 = orm.Optional(str, 64, nullable=True)
    reverse4 = orm.Optional(int)
    reverse5 = orm.Optional(int)

class OTASearchLog(extra_db.Entity):
    """
    OTA搜索记录，记录运价情况，用于统计
    """
    _table_ = 'ota_search_log'

    ota_name = orm.Optional(str, 32, default='',index=True)  # 所关联OTA简称
    provider = orm.Optional(str, 32, default='',index=True)  # 航司
    provider_channel = orm.Optional(str, 16, default='',index=True)  # 渠道

    from_date = orm.Optional(date_format,index=True)  # 去程时间
    ret_date = orm.Optional(date_format,index=True,nullable=True)  # 返程时间
    from_airport = orm.Optional(str, 8, default='',index=True)  # 出发机场
    to_airport = orm.Optional(str, 8, default='',index=True)  # 到达机场
    from_city = orm.Optional(str, 8, default='',index=True)  # 出发城市
    to_city = orm.Optional(str, 8, default='',index=True)  # 到达城市
    from_country = orm.Optional(str, 8, default='',index=True)  # 出发国家
    to_country = orm.Optional(str, 8, default='',index=True)  # 到达国家
    adt_count = orm.Optional(int)  # 成人个数
    chd_count = orm.Optional(int)  # 儿童个数
    inf_count =  orm.Optional(int)  # 婴儿个数
    #搜索结果
    total_latency = orm.Optional(int)  # 返回总时长
    provider_latency =  orm.Optional(int)  # 供应商返回时长
    return_status = orm.Optional(str, 32, default='',index=True)  # 供应商返回结果 NOFLIGHT 没有航班 SUCCESS 成功返回航班信息 CACHE 命中缓存
    return_details = orm.Optional(str, 1000,default='' )  # 详细原因
    assoc_search_routings_amount = orm.Optional(int)  # 所返回的航线个数
    fare_operation = orm.Optional(str, 32, default='',index=True) # 所应用的运价策略
    assoc_order_id = orm.Optional(str, 64, default='', index=True)  # 可用于串联查询、验价逻辑

    # 搜索信息
    routing_range = orm.Optional(str, 8, default='IN',index=True)  # 区分国际航班和国内航班  IN 国内  OUT 国际
    trip_type = orm.Optional(str, default='OW',index=True)  # 行程类型 OW：单程 RT：往返

    create_time = orm.Optional(datetime_format, sql_default='CURRENT_TIMESTAMP',index=True)  # 任务创建时间
    reverse1 = orm.Optional(str, 64, nullable=True)
    reverse2 = orm.Optional(str, 64, nullable=True)
    reverse3 = orm.Optional(str, 64, nullable=True)
    reverse4 = orm.Optional(int)
    reverse5 = orm.Optional(int)



class DynamicFareRepo(extra_db.Entity):
    """
    动态运价展示表


    """

    _table_ = 'dynamic_fare_repo'
    primary_fare_crawl_task = orm.Optional(lambda: PrimaryFareCrawlTask)  # 关联主爬虫ID，用于获取相关策略
    from_airport = orm.Optional(str, 8, default='',index=True)  # 出发机场
    to_airport = orm.Optional(str, 8, default='',index=True)  # 到达机场
    flight_number = orm.Optional(str, 32, default='')  # 聚合航班号信息
    cabin = orm.Optional(str, 32, default='')  # 聚合舱位信息（参考）
    cabin_grade = orm.Optional(str, 32, default='')  # 聚合舱等（参考）
    from_date = orm.Optional(date_format,index=True)  # 去程时间
    cost_price = orm.Optional(float, default=0)  # 成本价，不含税【正整数】
    provider = orm.Optional(str, 32, default='', index=True)  # 供应商
    provider_channel = orm.Optional(str, 32, default='', index=True)  # 供应商渠道
    offer_price = orm.Optional(float, default=0)  # 售价，不含税【正整数】
    ota_r1_price = orm.Optional(float, default=0)  # ota参考价（最低价）
    ota_r2_price = orm.Optional(float, default=0)  # ota参考价（此低价）
    fare_put_mode = orm.Optional(str, 32, default='', index=True)  # 自有运价的运价模式
    ver = orm.Optional(int,default=1)  # 更新版本号，观察变价频繁程度
    ret_date = orm.Optional(date_format,index=True)  # 返程时间
    trip_type = orm.Optional(str, 8, default='',index=True)  # OW RT
    source = orm.Optional(str, 32, default='')  # 最后一次数据的更新来源
    update_time = orm.Optional(datetime_format, sql_default='CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP',index=True)  # 更新时间
    hash = orm.Optional(str, 128,unique=True)  # hash 索引 用于更新用
    reverse1 = orm.Optional(str, 64, nullable=True)
    reverse2 = orm.Optional(str, 64, nullable=True)
    reverse3 = orm.Optional(str, 64, nullable=True)
    reverse4 = orm.Optional(int)
    reverse5 = orm.Optional(int)

class SmsMessage(db.Entity):
    """
    短信数据库
    """
    _table_ = 'sms_message'

    from_mobile = orm.Optional(str, 32, default='',index=True)
    to_mobile =orm.Optional(str, 32, default='')
    message = orm.Optional(str, 1000, default='') #  短信内容
    receive_time = orm.Optional(datetime_format,index=True)   # 短信实际接收时间
    create_time = orm.Optional(datetime_format, sql_default='CURRENT_TIMESTAMP',index=True)  # 入库时间
    sms_device_id = orm.Optional(str, 32, default='') # 自定义的手机设备名称

    # 预留字段
    reverse1 = orm.Optional(str, 64, nullable=True)
    reverse2 = orm.Optional(str, 64, nullable=True)
    reverse3 = orm.Optional(str, 64, nullable=True)
    reverse4 = orm.Optional(str, 64, nullable=True)
    reverse5 = orm.Optional(str, 64, nullable=True)
    reverse6 = orm.Optional(int)
    reverse7 = orm.Optional(int)

class MobileRepo(db.Entity):
    """
    手机卡数据库
    """
    _table_ = 'mobile_repo'

    mobile_num = orm.Optional(str, 32, default='', nullable=True) # 手机号码
    sms_device_id = orm.Optional(str, 32, default='',nullable=True) # 所在设备ID
    sim_no =  orm.Optional(str, 32, default='', nullable=True) # sim卡上的号码，用于识别sim卡 ICCID
    imsi = orm.Optional(str, 32, default='', nullable=True) # imsi
    comment = orm.Optional(str, 1000, default='', nullable=True) #  备注
    enable =  orm.Optional(int, default=1, nullable=True) #  是否可用
    provider_channel = orm.Optional(str, 32, default='', nullable=True) # 所属供应商渠道，如果为空，则所有渠道可用
    provider =   orm.Optional(str, 32, default='', nullable=True) # 所属供应商，如果为空，则所有供应商可用
    owner = orm.Optional(str, 32, default='', nullable=True) # 机主姓名
    op =  orm.Optional(str, 32, default='', nullable=True) # 运营商
    status =  orm.Optional(str, 32, default='', nullable=True) # 手机状态  ONLINE 在线


class EmailRepo(db.Entity):
    """
    邮箱数据库
    """
    _table_ = 'email_repo'

    address = orm.Optional(str, 128, default='', nullable=True) # 邮箱地址
    pop3_server = orm.Optional(str, 64, default='', nullable=True)  # 收信地址
    user =  orm.Optional(str, 64, default='', nullable=True)  # 用户名
    password =  orm.Optional(str, 64, default='', nullable=True)  # 密码
    domain = orm.Optional(str, 64, default='', nullable=True) # 邮箱域名
    comment = orm.Optional(str, 1000, default='', nullable=True) #  备注
    enable =  orm.Optional(int, default=1, nullable=True) #  是否可用
    provider_channel = orm.Optional(str, 32, default='', nullable=True) # 所属供应商渠道，如果为空，则所有渠道可用
    provider =   orm.Optional(str, 32, default='', nullable=True) # 所属供应商，如果为空，则所有供应商可用
    status =  orm.Optional(str, 32, default='', nullable=True) # 邮箱状态
    email_type = orm.Optional(str, 32, default='', nullable=True) # 邮箱类型 ENTERPRISE 企业邮箱（支持随机地址收信） PERSONAL 个人邮箱

class FlightRepo(extra_db.Entity):
    """
    热门航线
    """
    _table_ = 'flight_repo'

    from_airport = orm.Optional(str, 8, default='',index=True)  # 出发机场
    to_airport = orm.Optional(str, 8, default='',index=True)  # 到达机场
    from_to_airport = orm.Optional(str, 16,unique=True)  # 航线 HRB-SHA
    is_hot = orm.Optional(int,default=0) # 1 热门 0 非热门
    pr = orm.Optional(int, default=1, index=True)  # PR 权重
    is_crawl = orm.Optional(int, default=1, index=True)  # 是否用于爬取

    create_time = orm.Optional(datetime_format, sql_default='CURRENT_TIMESTAMP',index=True)  # 入库时间


class OTAVerify(db.Entity):
    """
    ota调用验价信息
    """
    _table_ = 'ota_verify'

    ota_name = orm.Optional(str, 64, default='', index=True)
    provider = orm.Optional(str, 64, default='', index=True)
    provider_channel = orm.Optional(str, 128, default='', index=True)
    from_date = orm.Optional(str, 32, default='', index=True)
    ret_date = orm.Optional(str, 32, default='')
    from_airport = orm.Optional(str, 8, default='', index=True)
    to_airport = orm.Optional(str, 8, default='', index=True)
    flight_number = orm.Optional(str, 64, default='', index=True)
    cabin = orm.Optional(str, 32, default='', index=True)
    return_status = orm.Optional(str, 32, default='', index=True)
    return_details = orm.Optional(str, 64, default='')
    ret = orm.Optional(LongStr, default='')
    req = orm.Optional(LongStr, default='')
    routing_key = orm.Optional(str, 512, default='', index=True)
    verify_duration = orm.Optional(int, default=0, index=True)
    verify_time = orm.Optional(datetime_format, nullable=True, index=True)
    search_time = orm.Optional(datetime_format, nullable=True, index=True)
    s2v_duration = orm.Optional(int, default=0, index=True)
    enter_time = orm.Optional(datetime_format, nullable=True, index=True)
    providers_stat = orm.Optional(str, 2000, default='[]')
    create_time = orm.Optional(datetime_format, sql_default='CURRENT_TIMESTAMP', index=True)  # 入库时间
    request_id = orm.Optional(str, 16, nullable=True)  # 关联ota验价时候的request_id
    fare_info = orm.Optional(str, 2000, default='{}')  # 如果运价联动并存在最低价在这里展示
    current_assoc_fare_info = orm.Optional(str, 64, nullable=True)  # 关联ota验价时候的request_id
    adjust_assoc_fare_info =  orm.Optional(str, 64, nullable=True)  # 关联ota验价时候的request_id
    rsno =  orm.Optional(str, 12, nullable=True)  # routing 流水号
    verify_details = orm.Optional(LongStr, default='')  # 存储所有同航班存在舱位的routingkey
    ota_product_code = orm.Optional(int, default=0, index=True)  # 0.普通产品 1.小团产品 2.快速出票 3.留学生产品 4.组合产品 5 行李套餐

class ScheduledAirlineRepo(db.Entity):
    """
    航线库
    """
    _table_ = 'scheduled_airline_repo'

    from_airport = orm.Optional(str, 64, default='', index=True)
    to_airport = orm.Optional(str, 8, default='', index=True)
    provider_channel = orm.Optional(str, 128, default='', index=True)
    create_time = orm.Optional(datetime_format, sql_default='CURRENT_TIMESTAMP', index=True)  # 入库时间

if __name__ == '__main__':
    pass
