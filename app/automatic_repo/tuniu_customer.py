#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gevent
import json
import datetime
import random
import string
import hashlib
import base64
import StringIO
import gzip
from .base import ProvderAutoBase
from ..dao.internal import *
from ..utils.util import simple_encrypt, Random,RoutingKey, simple_decrypt
from ..controller.captcha import CaptchaCracker
from app import TBG
from Crypto.Cipher import AES
from pony.orm import select, db_session
from app.dao.iata_code import CN_CITY_TO_AIRPORT
from ..dao.iata_code import BUDGET_AIRLINE_CODE
from hyper import HTTPConnection
from urllib import quote


class TuniuCustomer(ProvderAutoBase):
    timeout = 50  # 请求超时时间
    provider = 'tuniu_customer'  # 子类继承必须赋
    provider_channel = 'tuniu_customer_web'  # 子类继承必须赋
    operation_product_type = '会员折扣'  # 运价类型：0: GDS公布运价 1:GDS私有运价 2:航司官网产品  3:廉价航司产品 4:特价产品
    operation_product_mode = 'A2B'
    pay_channel = 'ALIPAY'
    provider_token = '5e7ba8bddd7b9648'
    is_display = True
    assoc_ota_name = 'tuniu'
    is_include_cabin = False
    no_flight_ttl = 1800  # 无航班缓存超时时间设定


    CACHE_PR_CONFIG = {
        1: {'cabin_expired_time': 60 * 10, 'cabin_attenuation': 3,'fare_expired_time':86400 * 30},
        2: {'cabin_expired_time': 60 * 10, 'cabin_attenuation': 2,'fare_expired_time':86400 * 20},
        3: {'cabin_expired_time': 60 * 5, 'cabin_attenuation': 1,'fare_expired_time':86400 * 10},
        4: {'cabin_expired_time': 60 * 5, 'cabin_attenuation': 1,'fare_expired_time':86400 * 5},
        5: {'cabin_expired_time': 60 * 5, 'cabin_attenuation': 0,'fare_expired_time':86400},

    }
    search_interval_time = 0.3

    TUNIU_CITY_CODE = {
    "CPH":{
        "tuniu_code":"1170419",
        "cn_code":"哥本哈根"
    },
    "KMG":{
        "tuniu_code":3302,
        "cn_code":"昆明"
    },
    "PAR":{
        "tuniu_code":"786784",
        "cn_code":"巴黎"
    },
    "ZQZ":{
        "tuniu_code":1016,
        "cn_code":"张家口"
    },
    "LIA":{
        "tuniu_code":323,
        "cn_code":"梁平区"
    },
    "":{
        "tuniu_code":120,
        "cn_code":"芜湖"
    },
    "XIC":{
        "tuniu_code":2828,
        "cn_code":"西昌市"
    },
    "BOS":{
        "tuniu_code":"44611",
        "cn_code":"波士顿"
    },
    "NAN":{
        "tuniu_code":"786402",
        "cn_code":"楠迪"
    },
    "CKG":{
        "tuniu_code":300,
        "cn_code":"重庆"
    },
    "MIG":{
        "tuniu_code":2816,
        "cn_code":"绵阳"
    },
    "LLV":{
        "tuniu_code":2607,
        "cn_code":"吕梁"
    },
    "SIA":{
        "tuniu_code":2710,
        "cn_code":"咸阳"
    },
    "WDS":{
        "tuniu_code":1410,
        "cn_code":"十堰"
    },
    "AXF":{
        "tuniu_code":40392,
        "cn_code":"阿拉善左旗"
    },
    "BOM":{
        "tuniu_code":"786695",
        "cn_code":"孟买"
    },
    "TCG":{
        "tuniu_code":3117,
        "cn_code":"塔城"
    },
    "CPT":{
        "tuniu_code":"787308",
        "cn_code":"开普敦"
    },
    "SIN":{
        "tuniu_code":"47109",
        "cn_code":"新加坡"
    },
    "XNT":{
        "tuniu_code":1015,
        "cn_code":"邢台"
    },
    "AOG":{
        "tuniu_code":1903,
        "cn_code":"鞍山"
    },
    "LDS":{
        "tuniu_code":1115,
        "cn_code":"伊春"
    },
    "RIZ":{
        "tuniu_code":2415,
        "cn_code":"日照"
    },
    "NNG":{
        "tuniu_code":702,
        "cn_code":"南宁"
    },
    "OHE":{
        "tuniu_code":40679,
        "cn_code":"漠河县"
    },
    "HSN":{
        "tuniu_code":3427,
        "cn_code":"舟山"
    },
    "GYU":{
        "tuniu_code":2203,
        "cn_code":"固原"
    },
    "KHH":{
        "tuniu_code":"2906",
        "cn_code":"高雄"
    },
    "SPK":{
        "tuniu_code":"47150",
        "cn_code":"札幌"
    },
    "PZI":{
        "tuniu_code":2820,
        "cn_code":"攀枝花"
    },
    "LYA":{
        "tuniu_code":1210,
        "cn_code":"洛阳"
    },
    "SPN":{
        "tuniu_code":"786461",
        "cn_code":"塞班"
    },
    "DCY":{
        "tuniu_code":143,
        "cn_code":"亚丁"
    },
    "TAO":{
        "tuniu_code":2413,
        "cn_code":"青岛"
    },
    "HKG":{
        "tuniu_code":"1300",
        "cn_code":"香港(中国香港)"
    },
    "KHG":{
        "tuniu_code":3111,
        "cn_code":"喀什"
    },
    "YMQ":{
        "tuniu_code":"786252",
        "cn_code":"蒙特利尔"
    },
    "TPE":{
        "tuniu_code":"2902",
        "cn_code":"台北(中国台北)"
    },
    "AYN":{
        "tuniu_code":1203,
        "cn_code":"安阳"
    },
    "HAM":{
        "tuniu_code":"43321",
        "cn_code":"汉堡"
    },
    "YVR":{
        "tuniu_code":"786254",
        "cn_code":"温哥华"
    },
    "CHG":{
        "tuniu_code":1905,
        "cn_code":"朝阳"
    },
    "MRU":{
        "tuniu_code":"4049",
        "cn_code":"毛里求斯"
    },
    "JIL":{
        "tuniu_code":1808,
        "cn_code":"吉林"
    },
    "NNY":{
        "tuniu_code":1211,
        "cn_code":"南阳"
    },
    "LHK":{
        "tuniu_code":1961178,
        "cn_code":"光化街道"
    },
    "HZH":{
        "tuniu_code":42121,
        "cn_code":"黎平县"
    },
    "THQ":{
        "tuniu_code":511,
        "cn_code":"天水"
    },
    "NAO":{
        "tuniu_code":2818,
        "cn_code":"南充"
    },
    "LHW":{
        "tuniu_code":502,
        "cn_code":"兰州"
    },
    "JUZ":{
        "tuniu_code":3419,
        "cn_code":"衢州"
    },
    "JIU":{
        "tuniu_code":1708,
        "cn_code":"九江"
    },
    "AKU":{
        "tuniu_code":3103,
        "cn_code":"阿克苏"
    },
    "LLB":{
        "tuniu_code":42130,
        "cn_code":"荔波县"
    },
    "LPF":{
        "tuniu_code":807,
        "cn_code":"六盘水"
    },
    "YIN":{
        "tuniu_code":42672,
        "cn_code":"伊宁市"
    },
    "WUT":{
        "tuniu_code":2610,
        "cn_code":"忻州"
    },
    "BNE":{
        "tuniu_code":"42951",
        "cn_code":"布里斯班"
    },
    "HRB":{
        "tuniu_code":1102,
        "cn_code":"哈尔滨"
    },
    "WUS":{
        "tuniu_code":413,
        "cn_code":"武夷山市"
    },
    "TYN":{
        "tuniu_code":2602,
        "cn_code":"太原"
    },
    "TYO":{
        "tuniu_code":"45103",
        "cn_code":"东京"
    },
    "BFJ":{
        "tuniu_code":804,
        "cn_code":"毕节"
    },
    "SYD":{
        "tuniu_code":"42985",
        "cn_code":"悉尼"
    },
    "YEA":{
        "tuniu_code":"786260",
        "cn_code":"埃德蒙顿"
    },
    "JNZ":{
        "tuniu_code":1911,
        "cn_code":"锦州"
    },
    "DBC":{
        "tuniu_code":1803,
        "cn_code":"白城"
    },
    "WUX":{
        "tuniu_code":1619,
        "cn_code":"无锡"
    },
    "GXH":{
        "tuniu_code":42532,
        "cn_code":"夏河县"
    },
    "RHT":{
        "tuniu_code":40393,
        "cn_code":"阿拉善右旗"
    },
    "SYM":{
        "tuniu_code":3316,
        "cn_code":"普洱"
    },
    "TGO":{
        "tuniu_code":2110,
        "cn_code":"通辽"
    },
    "UYN":{
        "tuniu_code":2712,
        "cn_code":"榆林"
    },
    "SFO":{
        "tuniu_code":"44557",
        "cn_code":"旧金山"
    },
    "WUA":{
        "tuniu_code":2111,
        "cn_code":"乌海"
    },
    "DOY":{
        "tuniu_code":2406,
        "cn_code":"东营"
    },
    "LAX":{
        "tuniu_code":"44558",
        "cn_code":"洛杉矶"
    },
    "MAD":{
        "tuniu_code":"1741916",
        "cn_code":"马德里"
    },
    "LXA":{
        "tuniu_code":3202,
        "cn_code":"拉萨"
    },
    "MEL":{
        "tuniu_code":"42973",
        "cn_code":"墨尔本"
    },
    "ZAT":{
        "tuniu_code":3321,
        "cn_code":"昭通"
    },
    "WUH":{
        "tuniu_code":1402,
        "cn_code":"武汉"
    },
    "LXI":{
        "tuniu_code":40320,
        "cn_code":"林西县"
    },
    "LAS":{
        "tuniu_code":"44673",
        "cn_code":"拉斯维加斯"
    },
    "TSN":{
        "tuniu_code":3000,
        "cn_code":"天津"
    },
    "HZG":{
        "tuniu_code":2705,
        "cn_code":"汉中"
    },
    "NGB":{
        "tuniu_code":3415,
        "cn_code":"宁波"
    },
    "YUS":{
        "tuniu_code":2310,
        "cn_code":"玉树"
    },
    "YBP":{
        "tuniu_code":2825,
        "cn_code":"宜宾"
    },
    "NGO":{
        "tuniu_code":"47148",
        "cn_code":"名古屋"
    },
    "HDG":{
        "tuniu_code":1008,
        "cn_code":"邯郸"
    },
    "FUG":{
        "tuniu_code":108,
        "cn_code":"阜阳"
    },
    "AEB":{
        "tuniu_code":703,
        "cn_code":"百色"
    },
    "DEL":{
        "tuniu_code":"46046",
        "cn_code":"新德里"
    },
    "NGQ":{
        "tuniu_code":3203,
        "cn_code":"阿里"
    },
    "YIH":{
        "tuniu_code":1418,
        "cn_code":"宜昌"
    },
    "JDZ":{
        "tuniu_code":1706,
        "cn_code":"景德镇"
    },
    "BER":{
        "tuniu_code":"43306",
        "cn_code":"柏林"
    },
    "FUO":{
        "tuniu_code":607,
        "cn_code":"佛山"
    },
    "YSQ":{
        "tuniu_code":1810,
        "cn_code":"松原"
    },
    "ZUH":{
        "tuniu_code":628,
        "cn_code":"珠海"
    },
    "DTU":{
        "tuniu_code":40666,
        "cn_code":"五大连池市"
    },
    "DTT":{
        "tuniu_code":"44637",
        "cn_code":"底特律"
    },
    "TCZ":{
        "tuniu_code":3323,
        "cn_code":"腾冲市"
    },
    "ROM":{
        "tuniu_code":"787024",
        "cn_code":"罗马"
    },
    "XAI":{
        "tuniu_code":1217,
        "cn_code":"信阳"
    },
    "JNB":{
        "tuniu_code":"787312",
        "cn_code":"约翰内斯堡"
    },
    "YZY":{
        "tuniu_code":515,
        "cn_code":"张掖"
    },
    "JUH":{
        "tuniu_code":109,
        "cn_code":"池州"
    },
    "HUO":{
        "tuniu_code":40333,
        "cn_code":"霍林郭勒市"
    },
    "MFM":{
        "tuniu_code":"2002",
        "cn_code":"澳门"
    },
    "JMU":{
        "tuniu_code":1108,
        "cn_code":"佳木斯"
    },
    "JMJ":{
        "tuniu_code":42200,
        "cn_code":"澜沧拉祜族自治县"
    },
    "SZX":{
        "tuniu_code":619,
        "cn_code":"深圳"
    },
    "YYA":{
        "tuniu_code":1512,
        "cn_code":"岳阳"
    },
    "MNL":{
        "tuniu_code":"43502",
        "cn_code":"马尼拉"
    },
    "HMI":{
        "tuniu_code":3109,
        "cn_code":"哈密"
    },
    "OSA":{
        "tuniu_code":"784018",
        "cn_code":"大阪"
    },
    "JNG":{
        "tuniu_code":2408,
        "cn_code":"济宁"
    },
    "AMS":{
        "tuniu_code":"1796169",
        "cn_code":"阿姆斯特丹"
    },
    "SZV":{
        "tuniu_code":1615,
        "cn_code":"苏州"
    },
    "LLF":{
        "tuniu_code":1513,
        "cn_code":"永州"
    },
    "HUZ":{
        "tuniu_code":609,
        "cn_code":"惠州"
    },
    "BUE":{
        "tuniu_code":"42806",
        "cn_code":"布宜诺斯艾利斯"
    },
    "DLC":{
        "tuniu_code":1906,
        "cn_code":"大连"
    },
    "YKH":{
        "tuniu_code":1915,
        "cn_code":"营口"
    },
    "SHS":{
        "tuniu_code":1408,
        "cn_code":"荆州"
    },
    "JGN":{
        "tuniu_code":516,
        "cn_code":"嘉峪关"
    },
    "YTY":{
        "tuniu_code":1622,
        "cn_code":"扬州"
    },
    "ENH":{
        "tuniu_code":1403,
        "cn_code":"恩施"
    },
    "RQA":{
        "tuniu_code":42631,
        "cn_code":"若羌县"
    },
    "JGD":{
        "tuniu_code":1841114,
        "cn_code":"加格达奇区"
    },
    "LJG":{
        "tuniu_code":3312,
        "cn_code":"丽江"
    },
    "DSN":{
        "tuniu_code":2106,
        "cn_code":"鄂尔多斯"
    },
    "SHA":{
        "tuniu_code":2500,
        "cn_code":"上海"
    },
    "SHE":{
        "tuniu_code":1902,
        "cn_code":"沈阳"
    },
    "DLU":{
        "tuniu_code":3306,
        "cn_code":"大理"
    },
    "FOC":{
        "tuniu_code":402,
        "cn_code":"福州"
    },
    "HCJ":{
        "tuniu_code":707,
        "cn_code":"河池"
    },
    "ENY":{
        "tuniu_code":2711,
        "cn_code":"延安"
    },
    "NZL":{
        "tuniu_code":40352,
        "cn_code":"扎兰屯市"
    },
    "JGS":{
        "tuniu_code":1707,
        "cn_code":"井冈山市"
    },
    "DDG":{
        "tuniu_code":1907,
        "cn_code":"丹东"
    },
    "CJU":{
        "tuniu_code":"43660",
        "cn_code":"济州"
    },
    "LZY":{
        "tuniu_code":3205,
        "cn_code":"林芝"
    },
    "CZX":{
        "tuniu_code":1604,
        "cn_code":"常州"
    },
    "SYX":{
        "tuniu_code":906,
        "cn_code":"三亚"
    },
    "KCA":{
        "tuniu_code":42639,
        "cn_code":"库车县"
    },
    "CGO":{
        "tuniu_code":1202,
        "cn_code":"郑州"
    },
    "HTN":{
        "tuniu_code":3110,
        "cn_code":"和田"
    },
    "LCX":{
        "tuniu_code":404,
        "cn_code":"龙岩"
    },
    "NBS":{
        "tuniu_code":151,
        "cn_code":"长白山风景区"
    },
    "ZHY":{
        "tuniu_code":2206,
        "cn_code":"中卫"
    },
    "HTT":{
        "tuniu_code":2303,
        "cn_code":"海西"
    },
    "LZO":{
        "tuniu_code":2814,
        "cn_code":"泸州"
    },
    "HLH":{
        "tuniu_code":40373,
        "cn_code":"乌兰浩特市"
    },
    "TNA":{
        "tuniu_code":2402,
        "cn_code":"济南"
    },
    "WMT":{
        "tuniu_code":1959778,
        "cn_code":"茅台镇"
    },
    "HJJ":{
        "tuniu_code":1506,
        "cn_code":"怀化"
    },
    "AVA":{
        "tuniu_code":803,
        "cn_code":"安顺"
    },
    "CSX":{
        "tuniu_code":1502,
        "cn_code":"长沙"
    },
    "ACC":{
        "tuniu_code":"787284",
        "cn_code":"阿克拉"
    },
    "CTU":{
        "tuniu_code":2802,
        "cn_code":"成都"
    },
    "BCN":{
        "tuniu_code":"1741448",
        "cn_code":"巴塞罗那"
    },
    "SHF":{
        "tuniu_code":3116,
        "cn_code":"石河子"
    },
    "TWC":{
        "tuniu_code":3113,
        "cn_code":"图木舒克"
    },
    "ATL":{
        "tuniu_code":"44778",
        "cn_code":"亚特兰大"
    },
    "PER":{
        "tuniu_code":"42981",
        "cn_code":"珀斯"
    },
    "IST":{
        "tuniu_code":"1742915",
        "cn_code":"伊斯坦布尔"
    },
    "KUL":{
        "tuniu_code":"44331",
        "cn_code":"吉隆坡"
    },
    "TVS":{
        "tuniu_code":1013,
        "cn_code":"唐山"
    },
    "WGN":{
        "tuniu_code":1509,
        "cn_code":"邵阳"
    },
    "AKL":{
        "tuniu_code":"1742970",
        "cn_code":"奥克兰"
    },
    "HNY":{
        "tuniu_code":1505,
        "cn_code":"衡阳"
    },
    "BPE":{
        "tuniu_code":1012,
        "cn_code":"秦皇岛"
    },
    "AKA":{
        "tuniu_code":2703,
        "cn_code":"安康"
    },
    "ACX":{
        "tuniu_code":42094,
        "cn_code":"兴义市"
    },
    "HFE":{
        "tuniu_code":102,
        "cn_code":"合肥"
    },
    "LUM":{
        "tuniu_code":3324,
        "cn_code":"芒市"
    },
    "XNN":{
        "tuniu_code":2302,
        "cn_code":"西宁"
    },
    "JIQ":{
        "tuniu_code":315,
        "cn_code":"黔江区"
    },
    "WNH":{
        "tuniu_code":3317,
        "cn_code":"文山"
    },
    "YNJ":{
        "tuniu_code":40547,
        "cn_code":"延吉市"
    },
    "TEN":{
        "tuniu_code":808,
        "cn_code":"铜仁"
    },
    "XFN":{
        "tuniu_code":1416,
        "cn_code":"襄阳"
    },
    "JKT":{
        "tuniu_code":"46037",
        "cn_code":"雅加达"
    },
    "HPG":{
        "tuniu_code":1412,
        "cn_code":"神农架"
    },
    "CGD":{
        "tuniu_code":1503,
        "cn_code":"常德"
    },
    "JSJ":{
        "tuniu_code":4395812,
        "cn_code":"建三江"
    },
    "BKK":{
        "tuniu_code":"45398",
        "cn_code":"曼谷"
    },
    "LNL":{
        "tuniu_code":512,
        "cn_code":"陇南"
    },
    "LYG":{
        "tuniu_code":1610,
        "cn_code":"连云港"
    },
    "NBO":{
        "tuniu_code":"786429",
        "cn_code":"内罗毕"
    },
    "SEA":{
        "tuniu_code":"44548",
        "cn_code":"西雅图"
    },
    "LNJ":{
        "tuniu_code":3311,
        "cn_code":"临沧"
    },
    "BSD":{
        "tuniu_code":3304,
        "cn_code":"保山"
    },
    "LFQ":{
        "tuniu_code":2608,
        "cn_code":"临汾"
    },
    "SEL":{
        "tuniu_code":"43796",
        "cn_code":"首尔"
    },
    "XUZ":{
        "tuniu_code":1620,
        "cn_code":"徐州"
    },
    "WEF":{
        "tuniu_code":2417,
        "cn_code":"潍坊"
    },
    "SQD":{
        "tuniu_code":1711,
        "cn_code":"上饶"
    },
    "YIE":{
        "tuniu_code":40374,
        "cn_code":"阿尔山市"
    },
    "XMN":{
        "tuniu_code":414,
        "cn_code":"厦门"
    },
    "DIG":{
        "tuniu_code":3320,
        "cn_code":"迪庆"
    },
    "MDG":{
        "tuniu_code":1110,
        "cn_code":"牡丹江"
    },
    "KHN":{
        "tuniu_code":1702,
        "cn_code":"南昌"
    },
    "YIC":{
        "tuniu_code":1713,
        "cn_code":"宜春"
    },
    "JZH":{
        "tuniu_code":2811,
        "cn_code":"九寨沟县"
    },
    "DFW":{
        "tuniu_code":"44496",
        "cn_code":"达拉斯"
    },
    "KJI":{
        "tuniu_code":42690,
        "cn_code":"布尔津县"
    },
    "DNH":{
        "tuniu_code":505,
        "cn_code":"敦煌市"
    },
    "NDG":{
        "tuniu_code":1111,
        "cn_code":"齐齐哈尔"
    },
    "XIL":{
        "tuniu_code":40380,
        "cn_code":"锡林浩特市"
    },
    "CGQ":{
        "tuniu_code":1802,
        "cn_code":"长春"
    },
    "ADD":{
        "tuniu_code":"786366",
        "cn_code":"亚的斯亚贝巴"
    },
    "KRL":{
        "tuniu_code":42628,
        "cn_code":"库尔勒市"
    },
    "HEL":{
        "tuniu_code":"1174441",
        "cn_code":"赫尔辛基"
    },
    "MXZ":{
        "tuniu_code":614,
        "cn_code":"梅州"
    },
    "ADL":{
        "tuniu_code":"42958",
        "cn_code":"阿德莱德"
    },
    "TLQ":{
        "tuniu_code":3118,
        "cn_code":"吐鲁番"
    },
    "HEK":{
        "tuniu_code":1107,
        "cn_code":"黑河"
    },
    "CDE":{
        "tuniu_code":1006,
        "cn_code":"承德"
    },
    "LED":{
        "tuniu_code":"787372",
        "cn_code":"圣彼得堡"
    },
    "RLK":{
        "tuniu_code":2109,
        "cn_code":"巴彦淖尔"
    },
    "ALG":{
        "tuniu_code":"1742817",
        "cn_code":"阿尔及尔"
    },
    "EDI":{
        "tuniu_code":"46051",
        "cn_code":"爱丁堡"
    },
    "LYI":{
        "tuniu_code":2411,
        "cn_code":"临沂"
    },
    "JJN":{
        "tuniu_code":408,
        "cn_code":"泉州"
    },
    "IQN":{
        "tuniu_code":514,
        "cn_code":"庆阳"
    },
    "BJS":{
        "tuniu_code":200,
        "cn_code":"北京"
    },
    "WNZ":{
        "tuniu_code":3426,
        "cn_code":"温州"
    },
    "NTG":{
        "tuniu_code":1611,
        "cn_code":"南通"
    },
    "PUS":{
        "tuniu_code":"43658",
        "cn_code":"釜山"
    },
    "BAV":{
        "tuniu_code":2104,
        "cn_code":"包头"
    },
    "HET":{
        "tuniu_code":2102,
        "cn_code":"呼和浩特"
    },
    "SQJ":{
        "tuniu_code":409,
        "cn_code":"三明"
    },
    "DPS":{
        "tuniu_code":"784812",
        "cn_code":"巴厘岛"
    },
    "CIF":{
        "tuniu_code":2105,
        "cn_code":"赤峰"
    },
    "JHG":{
        "tuniu_code":3318,
        "cn_code":"西双版纳"
    },
    "SWA":{
        "tuniu_code":616,
        "cn_code":"汕头"
    },
    "KRY":{
        "tuniu_code":3112,
        "cn_code":"克拉玛依"
    },
    "CIH":{
        "tuniu_code":2603,
        "cn_code":"长治"
    },
    "LON":{
        "tuniu_code":"46085",
        "cn_code":"伦敦"
    },
    "BPL":{
        "tuniu_code":42624,
        "cn_code":"博乐市"
    },
    "HYN":{
        "tuniu_code":3424,
        "cn_code":"台州"
    },
    "MSP":{
        "tuniu_code":"44654",
        "cn_code":"明尼阿波利斯"
    },
    "IQM":{
        "tuniu_code":42632,
        "cn_code":"且末县"
    },
    "AAT":{
        "tuniu_code":3104,
        "cn_code":"阿勒泰"
    },
    "CAI":{
        "tuniu_code":"787114",
        "cn_code":"开罗"
    },
    "HAK":{
        "tuniu_code":902,
        "cn_code":"海口"
    },
    "CAN":{
        "tuniu_code":602,
        "cn_code":"广州"
    },
    "YNZ":{
        "tuniu_code":1621,
        "cn_code":"盐城"
    },
    "ERL":{
        "tuniu_code":40379,
        "cn_code":"二连浩特市"
    },
    "BPX":{
        "tuniu_code":3204,
        "cn_code":"昌都"
    },
    "IBR":{
        "tuniu_code":"45098",
        "cn_code":"茨城"
    },
    "KOW":{
        "tuniu_code":1704,
        "cn_code":"赣州"
    },
    "JIC":{
        "tuniu_code":507,
        "cn_code":"金昌"
    },
    "TXN":{
        "tuniu_code":113,
        "cn_code":"黄山"
    },
    "KWE":{
        "tuniu_code":802,
        "cn_code":"贵阳"
    },
    "HAN":{
        "tuniu_code":"46126",
        "cn_code":"河内"
    },
    "CHI":{
        "tuniu_code":"44759",
        "cn_code":"芝加哥"
    },
    "LZH":{
        "tuniu_code":709,
        "cn_code":"柳州"
    },
    "FYJ":{
        "tuniu_code":40645,
        "cn_code":"抚远市"
    },
    "URC":{
        "tuniu_code":3102,
        "cn_code":"乌鲁木齐"
    },
    "FYN":{
        "tuniu_code":42691,
        "cn_code":"富蕴县"
    },
    "KWL":{
        "tuniu_code":705,
        "cn_code":"桂林"
    },
    "RKZ":{
        "tuniu_code":3207,
        "cn_code":"日喀则"
    },
    "DAT":{
        "tuniu_code":2604,
        "cn_code":"大同"
    },
    "HIA":{
        "tuniu_code":1606,
        "cn_code":"淮安"
    },
    "AQG":{
        "tuniu_code":103,
        "cn_code":"安庆"
    },
    "GYS":{
        "tuniu_code":2810,
        "cn_code":"广元"
    },
    "UCB":{
        "tuniu_code":2108,
        "cn_code":"乌兰察布"
    },
    "YNT":{
        "tuniu_code":2419,
        "cn_code":"烟台"
    },
    "SGN":{
        "tuniu_code":"46127",
        "cn_code":"胡志明市"
    },
    "AHJ":{
        "tuniu_code":42014,
        "cn_code":"红原县"
    },
    "DYG":{
        "tuniu_code":1514,
        "cn_code":"张家界"
    },
    "DAX":{
        "tuniu_code":2804,
        "cn_code":"达州"
    },
    "KJH":{
        "tuniu_code":42111,
        "cn_code":"凯里市"
    },
    "YCU":{
        "tuniu_code":2613,
        "cn_code":"运城"
    },
    "EJN":{
        "tuniu_code":40394,
        "cn_code":"额济纳旗"
    },
    "WEH":{
        "tuniu_code":2418,
        "cn_code":"威海"
    },
    "CNS":{
        "tuniu_code":"42953",
        "cn_code":"凯恩斯"
    },
    "HXD":{
        "tuniu_code":42572,
        "cn_code":"德令哈市"
    },
    "NLH":{
        "tuniu_code":42191,
        "cn_code":"宁蒗彝族自治县"
    },
    "BAR":{
        "tuniu_code":905,
        "cn_code":"琼海市"
    },
    "GMQ":{
        "tuniu_code":2308,
        "cn_code":"果洛"
    },
    "SJW":{
        "tuniu_code":1002,
        "cn_code":"石家庄"
    },
    "JXA":{
        "tuniu_code":1109,
        "cn_code":"鸡西"
    },
    "KTM":{
        "tuniu_code":"786170",
        "cn_code":"加德满都"
    },
    "CWJ":{
        "tuniu_code":42209,
        "cn_code":"沧源佤族自治县"
    },
    "ULN":{
        "tuniu_code":"44811",
        "cn_code":"乌兰巴托"
    },
    "HGH":{
        "tuniu_code":3402,
        "cn_code":"杭州"
    },
    "QSZ":{
        "tuniu_code":42656,
        "cn_code":"莎车县"
    },
    "WXN":{
        "tuniu_code":302,
        "cn_code":"万州区"
    },
    "NZH":{
        "tuniu_code":40350,
        "cn_code":"满洲里市"
    },
    "GOQ":{
        "tuniu_code":42571,
        "cn_code":"格尔木市"
    },
    "TNH":{
        "tuniu_code":1811,
        "cn_code":"通化"
    },
    "NLT":{
        "tuniu_code":1953443,
        "cn_code":"那拉提镇"
    },
    "ZHA":{
        "tuniu_code":625,
        "cn_code":"湛江"
    },
    "HLD":{
        "tuniu_code":40342,
        "cn_code":"海拉尔区"
    },
    "KGT":{
        "tuniu_code":42015,
        "cn_code":"康定市"
    },
    "NKG":{
        "tuniu_code":1602,
        "cn_code":"南京"
    },
    "OOL":{
        "tuniu_code":"42952",
        "cn_code":"黄金海岸"
    },
    "YIW":{
        "tuniu_code":40810,
        "cn_code":"义乌市"
    },
    "BHY":{
        "tuniu_code":704,
        "cn_code":"北海"
    },
    "PNH":{
        "tuniu_code":"43977",
        "cn_code":"金边"
    },
    "WUZ":{
        "tuniu_code":711,
        "cn_code":"梧州"
    },
    "ZYI":{
        "tuniu_code":811,
        "cn_code":"遵义"
    },
    "LAD":{
        "tuniu_code":"786586",
        "cn_code":"罗安达"
    },
    "INC":{
        "tuniu_code":2202,
        "cn_code":"银川"
    },
    "DXB":{
        "tuniu_code":"42838",
        "cn_code":"迪拜"
    },
    "DQA":{
        "tuniu_code":1104,
        "cn_code":"大庆"
    },
    "CNX":{
        "tuniu_code": 784710,
        "cn_code": "清迈"
    },
    "XIY":{
        "tuniu_code": 2702,
        "cn_code": "西安",
    },
    "HKT":{
        "tuniu_code": 785093,
        "cn_code": "普吉",
    }
}

    TUNIU_CITY_AIRPORT_MAPPING = {
        u'浦东机场': 'PVG',
        u'虹桥机场': 'SHA',
        u'仁川机场': 'ICN',
        u'金浦机场': 'GMP',
        u'素万那普机场': 'BKK',
        u'廊曼机场': 'DMK',
        u'关西机场': 'KIX',
        u'伊丹机场': 'ITM',
        u'神户机场': 'UKB',
        u'帕尔森机场': 'YYZ',
        u'多伦多岛机场': 'YTZ',
        u'羽田机场': 'HND',
        u'成田机场': 'NRT',
        u'首都机场': 'PEK',
        u'阿瓦伦机场': 'AVV',
        u'米德威机场': 'MDW',
        u'奥黑尔机场': 'ORD',
        u'里纳特机场': 'LIN',
        u'马尔潘萨机场': 'MXP',
        u'梳邦机场': 'SZB',
        u'西斯罗机场': 'LHR',
        u'盖特维克机场': 'LGW',
        u'伦敦城机场': 'LCY',
        u'中部航空机场': 'NGO',
        u'戴高乐机场': 'CDG',
        u'奥利机场': 'ORY',
        u'洛杉矶机场': 'LAX',
        u'阿勒马克图姆机场': 'DWC',
        u'迪拜机场': 'DXB',
        u'新千岁机场': 'CTS',
        u'萨比哈哥克赛恩机场': 'SAW',
        u'阿塔图尔克机场': 'IST',
        u'新机场': 'ISL',
        u'雅加达机场': 'CGK',
        u'费尤米西诺机场': 'FCO',
        u'塔克马机场': 'SEA',
        u'泰格尔机场': 'TXL',
        u'肖尔内菲尔德机场': 'SXF'
    }


    def __init__(self):
        super(TuniuCustomer, self).__init__()

    def _flight_search(self, http_session, search_info):
        """
        航班爬取模块，
        TODO :目前只考虑单程
        :return:
        """

        Logger().debug('search flight')

        if not self.TUNIU_CITY_CODE.get(search_info.from_airport) or not self.TUNIU_CITY_CODE.get(search_info.to_airport):
            Logger().info('tuniu customer no flight')
            return search_info

        if search_info.routing_range == 'I2O':
            dep_nation = 1
            arr_nation = 2
        elif search_info.routing_range == 'O2I':
            dep_nation = 2
            arr_nation = 1
        elif search_info.routing_range == 'I2I':
            dep_nation = 1
            arr_nation = 1
        else:
            dep_nation = 2
            arr_nation = 2


        url = 'http://super.tuniu.com/tn?r=supdiy/planeAjax/getIndividualFlight'
        post_data = {
            "journey": [{
                "primary": {
                    "departureCityCode": int(self.TUNIU_CITY_CODE[search_info.from_airport]['tuniu_code']),
                    "departureCity": self.TUNIU_CITY_CODE[search_info.from_airport]['cn_code'],
                    "arrivalCityCode": int(self.TUNIU_CITY_CODE[search_info.to_airport]['tuniu_code']),
                    "arrivalCity": self.TUNIU_CITY_CODE[search_info.to_airport]['cn_code'],
                    "departsDate": search_info.from_date,
                    "arrivalNationType": arr_nation,
                    "departureNationType": dep_nation,
                    "nationType": 1
                },
                "journeyRph": 1
            }],
            "adultNumber": 1,
            "childNumber": 0,
            "searchType": 1
        }
        post_data = {'postData': json.dumps(post_data)}

        result = http_session.request(url=url, data=post_data, method='POST', proxy_pool='A').to_json()
        Logger().debug("====== search result:{} ==".format(json.dumps(result)))

        if not result['success'] == True:
            raise FlightSearchException(err_code='HIGH_REQ_LIMIT')

        if result['data']['rows'][0]['count'] == 0:
            Logger().warn('tuniu customer no flight')
            return search_info

        routing_list = result['data']['rows'][0]['rows']
        for routing in routing_list:
            seg_list = routing['flightItems']
            if not seg_list:
                continue
            flight_routing = FlightRoutingInfo()
            flight_routing.product_type = 'DEFAULT'
            routing_number = 1
            valid_routing = True
            for index, seg in enumerate(seg_list):
                flight_segment = FlightSegmentInfo()
                flight_segment.carrier = seg['flightNo'][:2]
                dep_time = datetime.datetime.strptime(seg['departureDate'] + seg['departureTime'],
                                                      '%Y-%m-%d%H:%M').strftime('%Y-%m-%d %H:%M:%S')
                arr_time = datetime.datetime.strptime(seg['arrivalDate'] + seg['arrivalTime'],
                                                      '%Y-%m-%d%H:%M').strftime('%Y-%m-%d %H:%M:%S')

                if self.TUNIU_CITY_AIRPORT_MAPPING.get(seg['dPortName']):
                    dep_airport = self.TUNIU_CITY_AIRPORT_MAPPING[seg['dPortName']]
                elif CN_CITY_TO_AIRPORT.get(seg['dCityName'].encode('utf8')):
                    dep_airport = CN_CITY_TO_AIRPORT[seg['dCityName'].encode('utf8')]
                else:
                    valid_routing = False
                    break

                if self.TUNIU_CITY_AIRPORT_MAPPING.get(seg['aPortName']):
                    arr_airport = self.TUNIU_CITY_AIRPORT_MAPPING[seg['aPortName']]
                elif CN_CITY_TO_AIRPORT.get(seg['aCityName'].encode('utf8')):
                    arr_airport = CN_CITY_TO_AIRPORT[seg['aCityName'].encode('utf8')]
                else:
                    valid_routing = False
                    break

                flight_segment.dep_airport = dep_airport
                flight_segment.dep_time = dep_time
                flight_segment.arr_airport = arr_airport
                flight_segment.arr_time = arr_time
                flight_segment.flight_number = seg['flightNo']
                flight_segment.dep_terminal = seg['dTerminal']
                flight_segment.arr_terminal = seg['aTerminal']
                if flight_segment.carrier in BUDGET_AIRLINE_CODE:
                    flight_segment.cabin = 'Y'
                else:
                    flight_segment.cabin = 'N/A'
                flight_segment.cabin_grade = 'Y'
                flight_segment.cabin_count = int(routing['prices'][0]['seatStatus']) if not routing['prices'][0]['seatStatus'] == '>9' else 9
                segment_duration = (datetime.datetime.strptime(arr_time, '%Y-%m-%d %H:%M:%S') -
                                    datetime.datetime.strptime(dep_time, '%Y-%m-%d %H:%M:%S')).total_seconds()
                flight_segment.duration = int(segment_duration / 60)
                flight_segment.routing_number = routing_number
                routing_number += 1
                flight_routing.from_segments.append(flight_segment)

            if not valid_routing:
                continue

            flight_routing.adult_price = float(routing['prices'][0]['adultPrice'])
            flight_routing.adult_tax = float(routing['prices'][0]['adultTaxes'])
            flight_routing.child_price = float(routing['prices'][0]['childPrice'])
            flight_routing.child_tax = float(routing['prices'][0]['childTaxes'])
            rk_info = RoutingKey.serialize(from_airport=flight_routing.from_segments[0].dep_airport,
                                           dep_time=datetime.datetime.strptime(flight_routing.from_segments[0].dep_time,
                                                                               '%Y-%m-%d %H:%M:%S'),
                                           to_airport=flight_routing.from_segments[-1].arr_airport,
                                           arr_time=datetime.datetime.strptime(flight_routing.from_segments[-1].arr_time,
                                                                               '%Y-%m-%d %H:%M:%S'),
                                           flight_number='-'.join([s.flight_number for s in flight_routing.from_segments]),
                                           cabin='-'.join([s.cabin for s in flight_routing.from_segments]),
                                           cabin_grade='-'.join([s.cabin_grade for s in flight_routing.from_segments]),
                                           product='COMMON',
                                           adult_price=flight_routing.adult_price, adult_tax=flight_routing.adult_tax,
                                           provider_channel=self.provider_channel,
                                           child_price=flight_routing.child_price, child_tax=flight_routing.child_tax,
                                           inf_price=0.0,
                                           inf_tax=0.0,
                                           provider=self.provider,
                                           search_from_airport=search_info.from_airport,
                                           search_to_airport=search_info.to_airport,
                                           from_date=search_info.from_date,
                                           routing_range=search_info.routing_range,
                                           trip_type=search_info.trip_type,
                                           is_include_operation_carrier=0,
                                           is_multi_segments=1 if len(flight_routing.from_segments) > 1 else 0
                                           )

            flight_routing.routing_key_detail = rk_info['plain']
            flight_routing.routing_key = rk_info['encrypted']
            search_info.assoc_search_routings.append(flight_routing)

        return search_info


class TuniuCustomerCommon(TuniuCustomer):
    timeout = 50  # 请求超时时间
    provider = 'tuniu_customer'  # 子类继承必须赋
    provider_channel = 'tuniu_customer_common'  # 子类继承必须赋
    operation_product_type = '会员折扣'  # 运价类型：0: GDS公布运价 1:GDS私有运价 2:航司官网产品  3:廉价航司产品 4:特价产品
    operation_product_mode = 'A2B'
    pay_channel = 'ALIPAY'
    provider_token = '5e7ba8bddd7b9648'
    is_display = True
    assoc_ota_name = 'tuniu'
    is_include_cabin = False
    no_flight_ttl = 1800  # 无航班缓存超时时间设定


    CACHE_PR_CONFIG = {
        1: {'cabin_expired_time': 60 * 25, 'cabin_attenuation': 3,'fare_expired_time':86400 * 30},
        2: {'cabin_expired_time': 60 * 15, 'cabin_attenuation': 2,'fare_expired_time':86400 * 20},
        3: {'cabin_expired_time': 60 * 12, 'cabin_attenuation': 1,'fare_expired_time':86400 * 10},
        4: {'cabin_expired_time': 60 * 8, 'cabin_attenuation': 1,'fare_expired_time':86400 * 5},
        5: {'cabin_expired_time': 60 * 8, 'cabin_attenuation': 0,'fare_expired_time':86400},

    }
    search_interval_time = 0.3

    def __init__(self):
        super(TuniuCustomerCommon, self).__init__()

    def _flight_search(self, http_session, search_info):
        """
        航班爬取模块，
        TODO :目前只考虑单程
        :return:
        """

        Logger().debug('search flight')

        headers = {
            'Host': 'flight.tuniu.com',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_2) AppleWebKit/588.36 (KHTML, like Gecko) Chrome/73.0.3683.123 Safari/588.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
            'Referer': 'http://flight.tuniu.com/intl/list/BJS_TYO_1_0_0?deptDate=2019-05-22&type=1&cabinClass=0',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-GB,en;q=0.9,en-US;q=0.8,zh-CN;q=0.7,zh;q=0.6',
        }

        http_session.update_headers(headers)
        url = 'http://flight.tuniu.com/intl/list/{}_{}_1_0_0?deptDate={}&type=1&cabinClass=0'.format(
            search_info.from_airport, search_info.to_airport, search_info.from_date
        )
        http_session.request(url=url, method='GET', proxy_pool='A', verify=False)
        mtoken = http_session.get_cookies().get('mtoken')

        if not mtoken:
            raise FlightSearchException('cannot get mtoken')

        # FIXME get proxy a
        result = http_session.request(
            url='http://mapi.baibianip.com/getproxy?type=dymatic&apikey=5fcfed32d9a420b2cbe592e8f73a9fb5&count=120&unique=1&lb=1&format=json&sort=1&resf=1,2',
            is_direct=True, method='GET'
        ).to_json()
        proxy_list = result['proxy_list']
        proxy = random.choice(proxy_list)
        proxy = '{}:{}'.format(proxy['ip'], proxy['port'])

        conn = HTTPConnection('flight-api.tuniu.com:443', proxy_host=proxy)
        timestamp = int(time.time() * 1000)
        callback_jq = 'jQuery3310738671{}_{}'.format(random.randint(100000000000, 999999999999), timestamp)

        poll_tag = 0
        channel_count = 0
        rph = 0
        data = '{"direct":"0","cabinClass":"0","baggageInfoFlag":0,"pollTag":%s,"channelCount":%s,"adultQuantity":"%s","childQuantity":"%s","babyQuantity":"0","rph":%s,"language":"zh","segmentList":[{"dCityIataCode":"%s","aCityIataCode":"%s","departDate":"%s"}],"bif":{"intel":1,"abToken":""},"hackersFlightNos":"","tokenKey":"%s"}' % (
            poll_tag, channel_count, search_info.adt_count, search_info.chd_count, rph, search_info.from_airport,
            search_info.to_airport, search_info.from_date, mtoken)
        post_data = [
            'callback={}'.format(callback_jq),
            'data={}'.format(quote(data)),
            '_={}'.format(timestamp + 3)
        ]
        post_data = '&'.join(post_data)
        url = '/wzt/intel/flight/v1/listFlight?{}'.format(post_data)
        Logger().debug("========= post data: {} ===".format(post_data))
        headers = {
            ':method': 'GET',
            ':authority': 'flight-api.tuniu.com',
            ':scheme': 'https',
            ':path': url,
        }
        conn.request(url=url, method='GET', headers=headers)
        result = conn.get_response()
        result = result.read()
        Logger().debug("========= search result:{}".format(result))

        parse_result = re.findall(callback_jq + '\((.*)\)', result)
        if parse_result:
            parse_result = json.loads(parse_result[0])
        else:
            Logger().error("flight search error:{}".format(result))
            raise FlightSearchException('parse flight search result error')

        if not parse_result.get('errorCode') == 170000:
            Logger().error(parse_result.get('msg'))
            raise FlightSearchException('tuniu customer common flight search error')

        have_routing_result = None

        if parse_result['data'].get('fareList'):
            have_routing_result = dict(parse_result)


        for times in xrange(10):
            if parse_result['data']['needQueryMore'] == 0:
                # 还需要轮询
                poll_tag = 1
                channel_count = parse_result['data']['channelCount']
                rph = 1
                data = '{"direct":"0","cabinClass":"0","baggageInfoFlag":0,"pollTag":%s,"channelCount":%s,"adultQuantity":"%s","childQuantity":"%s","babyQuantity":"0","rph":%s,"language":"zh","segmentList":[{"dCityIataCode":"%s","aCityIataCode":"%s","departDate":"%s"}],"bif":{"intel":1,"abToken":""},"hackersFlightNos":"","tokenKey":"%s"}' % (
                    poll_tag, channel_count, search_info.adt_count, search_info.chd_count, rph,
                    search_info.from_airport,
                    search_info.to_airport, search_info.from_date, mtoken)
                post_data = [
                    'callback={}'.format(callback_jq),
                    'data={}'.format(quote(data)),
                    '_={}'.format(timestamp + 3)
                ]
                post_data = '&'.join(post_data)
                url = '/wzt/intel/flight/v1/listFlight?{}'.format(post_data)
                Logger().debug("========= post data: {} ===".format(post_data))
                headers = {
                    ':method': 'GET',
                    ':authority': 'flight-api.tuniu.com',
                    ':scheme': 'https',
                    ':path': url,
                }
                conn.request(url=url, method='GET', headers=headers)
                result = conn.get_response()
                result = result.read()
                Logger().debug("========= search result:{}".format(result))

                parse_result = re.findall(callback_jq + '\((.*)\)', result)
                if parse_result:
                    parse_result = json.loads(parse_result[0])
                else:
                    Logger().error("flight search error:{}".format(result))
                    raise FlightSearchException('parse flight search result error')

                if not parse_result.get('errorCode') == 170000:
                    Logger().error(parse_result.get('msg'))
                    raise FlightSearchException('tuniu customer common flight search error')
            elif not parse_result['data'].get('fareList'):
                # 明确无航班
                Logger().warn('tuniu customer common no flight')
                return search_info
            else:
                # 不需要继续轮询
                break

            if parse_result['data'].get('fareList'):
                have_routing_result = dict(parse_result)
            time.sleep(1)

        if not have_routing_result:
            Logger().warn('tuniu customer common no flight')
            return search_info

        routing_list = have_routing_result['data']['fareList']

        cabin_grade_map = {
            1: 'Y',
            2: 'C',
            3: 'F',
            4: 'S',
        }
        for routing in routing_list:
            cabin_list = routing['flightPriceList']
            for cabin in cabin_list:
                flight_no_list = []
                cabin_info_list = cabin['priceFlightCabinList']
                if not cabin_info_list:
                    continue
                for c in cabin_info_list:
                    flight_no_list.append(c['flightNo'])

                flight_routing = FlightRoutingInfo()
                flight_routing.product_type = 'DEFAULT'
                routing_number = 1
                valid_routing = True

                flight_no_key = '-'.join(flight_no_list)
                seg_key_map = have_routing_result['data']['voyageMap'].get(flight_no_key)
                if not seg_key_map:
                    continue
                seg_key_list = seg_key_map['segmentKeys']

                for index, seg_key in enumerate(seg_key_list):
                    seg = have_routing_result['data']['segmentMap'].get(seg_key)
                    if not seg:
                        valid_routing = False
                        break
                    flight_segment = FlightSegmentInfo()
                    flight_segment.carrier = seg['airlineIataCode']
                    dep_time = datetime.datetime.strptime(seg['departureDate'] + seg['departureTime'],
                                                          '%Y-%m-%d%H:%M').strftime('%Y-%m-%d %H:%M:%S')
                    arr_time = datetime.datetime.strptime(seg['arrivalDate'] + seg['arrivalTime'],
                                                          '%Y-%m-%d%H:%M').strftime('%Y-%m-%d %H:%M:%S')

                    flight_segment.dep_airport = seg['dPortIataCode']
                    flight_segment.dep_time = dep_time
                    flight_segment.arr_airport = seg['aPortIataCode']
                    flight_segment.arr_time = arr_time
                    flight_segment.flight_number = seg['flightNo']
                    flight_segment.dep_terminal = seg['dTerminal']
                    flight_segment.arr_terminal = seg['aTerminal']
                    flight_segment.cabin = cabin_info_list[index]['cabinClass']
                    flight_segment.cabin_grade = cabin_grade_map.get(cabin_info_list[index]['seatTypeCode'], 'Y')
                    flight_segment.cabin_count = int(cabin_info_list[index]['seatStatus'])
                    segment_duration = (datetime.datetime.strptime(arr_time, '%Y-%m-%d %H:%M:%S') -
                                        datetime.datetime.strptime(dep_time, '%Y-%m-%d %H:%M:%S')).total_seconds()
                    flight_segment.duration = int(segment_duration / 60)
                    flight_segment.routing_number = routing_number
                    routing_number += 1
                    flight_routing.from_segments.append(flight_segment)

                if not valid_routing:
                    continue

                flight_routing.adult_price = float(cabin['psgTypePriceMap']['ADT']['taxExclusiveFare'])
                flight_routing.adult_tax = float(cabin['psgTypePriceMap']['ADT']['tax'])
                flight_routing.child_price = float(cabin['psgTypePriceMap']['CHD']['taxExclusiveFare']) if cabin['psgTypePriceMap'].get('CHD') else flight_routing.adult_price
                flight_routing.child_tax = float(cabin['psgTypePriceMap']['CHD']['tax']) if cabin['psgTypePriceMap'].get('CHD') else flight_routing.adult_tax
                rk_info = RoutingKey.serialize(from_airport=flight_routing.from_segments[0].dep_airport,
                                               dep_time=datetime.datetime.strptime(flight_routing.from_segments[0].dep_time,
                                                                                   '%Y-%m-%d %H:%M:%S'),
                                               to_airport=flight_routing.from_segments[-1].arr_airport,
                                               arr_time=datetime.datetime.strptime(flight_routing.from_segments[-1].arr_time,
                                                                                   '%Y-%m-%d %H:%M:%S'),
                                               flight_number='-'.join([s.flight_number for s in flight_routing.from_segments]),
                                               cabin='-'.join([s.cabin for s in flight_routing.from_segments]),
                                               cabin_grade='-'.join([s.cabin_grade for s in flight_routing.from_segments]),
                                               product='COMMON',
                                               adult_price=flight_routing.adult_price, adult_tax=flight_routing.adult_tax,
                                               provider_channel=self.provider_channel,
                                               child_price=flight_routing.child_price, child_tax=flight_routing.child_tax,
                                               inf_price=0.0,
                                               inf_tax=0.0,
                                               provider=self.provider,
                                               search_from_airport=search_info.from_airport,
                                               search_to_airport=search_info.to_airport,
                                               from_date=search_info.from_date,
                                               routing_range=search_info.routing_range,
                                               trip_type=search_info.trip_type,
                                               is_include_operation_carrier=0,
                                               is_multi_segments=1 if len(flight_routing.from_segments) > 1 else 0
                                               )

                flight_routing.routing_key_detail = rk_info['plain']
                flight_routing.routing_key = rk_info['encrypted']
                search_info.assoc_search_routings.append(flight_routing)

        return search_info
