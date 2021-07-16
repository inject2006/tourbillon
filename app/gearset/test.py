#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, too-many-arguments, broad-except, anomalous-backslash-in-string
# pylint: disable=missing-docstring, line-too-long, too-few-public-methods
"""
# @Author  : wxt
# @Software: PyCharm
"""


import copy,gevent
import datetime
import codecs
from pony.orm import select
import pony.orm.core
from flask_script import Manager,Command
from ..dao.models import *
from ..dao.internal import *
from ..controller.http_request import HttpRequest
from ..utils.logger import Logger
from ..automatic_repo.base import ProviderAutoRepo
from app import TBG
from ..controller.captcha import CaptchaCracker
from ..controller.smser import Smser
from ..utils.triple_des_m import desenc
from ..utils.logger import logger_config
from pony.orm import select, desc, db_session
from ..dao.redis_dao import RedisPool
from ..ota_repo.base import OTARepo
from ..router.core import Router

class a(object):
    def __init__(self):
        pass

    def foo(self):
        getattr(cls,k)

class bb(object):
    def __init__(self):
        self.ddd = {'xx':SearchInfo()}

def profile_text():

    search_info = SearchInfo()
    search_info.adt_count = 1
    search_info.from_date = '2019-03-04'
    search_info.ret_date = '2019-03-04'
    search_info.from_airport = 'SHA'
    search_info.to_airport = 'HRB'
    search_info.trip_type = 'OW'
    search_info.attr_competion()  # 属性自动补全

    self_ota_app = OTARepo.select('fakeota')
    self_ota_app.search_info = search_info
    router = Router(self_ota_app, search_mode='sync_call',is_allow_cabin_revise=False,is_allow_fusing=False,is_allow_max_pax_count_limit=False,is_allow_min_cabin_count_limit=False)
    router.run()

class TestController(Command):
    """
    """
    username = 'hzwantu'
    password = 'hzwantu@tcjp'
    order_list_by_poll_url = 'http://tcflightopenapi.17usoft.com/tc/getorderlist.ashx'  # 生产
    # order_list_by_poll_url = 'http://127.0.0.1:8899/tc/getorderlist.ashx' # 测试

    order_detail_by_poll_url = 'http://tcflightopenapi.17usoft.com/tc/getorderdetail.ashx'  # 生产
    # order_detail_by_poll_url = 'http://127.0.0.1:8899/tc/getorderdetail.ashx' # 测试

    set_order_issued_url = 'http://tcflightopenapi.17usoft.com/tc/ticketnotify.ashx'  # 生产
    # set_order_issued_url = 'http://127.0.0.1:8899/tc/ticketnotify.ashx' # 测试

    def __init__(self,**kwargs):
        self.ddd = {'xx': SearchInfo()}

    # @db_session
    # def run(self):
    #
    #
    #
    #     while 1:
    #         print 'task starfft'
    #         a = SearchInfo()
    #         kwargs = {'aaa': 'bbb'}
    #
    #         result = run_task.apply_async(kwargs={'func': 'order_check', 'search_info': a})
    #         gevent.sleep(3)
    #
    #         # while 1:
    #         #     res = AsyncResult(task_id)
    #         #     if res.status == 'RUNNING':
    #         #         print 'no running'
    #         #     elif res.status == 'SUCCESS' or res.status == 'FAILED':
    #         #         res.forget()
    #         #         print 'forget'
    #         #     elif res.status == 'PENDING':
    #         #         print 'pending'
    #         #     print res.state
    #         #     gevent.sleep(1)

    def test_fateadm(self):
        fta =CaptchaCracker.select('Fateadm')
        print fta.query_balc()


    def sub(self):
        provider_order_status_list = [
            'BOOK_SUCCESS_AND_WAITING_PAY',
            'PAY_SUCCESS',
            'ISSUE_SUCCESS',
            'ORDER_INIT',
            'BACKFILL_SUCCESS'
        ]
        ota_order_status_list = [
            'ORDER_INIT',
            'READY_TO_ISSUE'
        ]
        while 1:
            #  TODO 简单调度系统实现

            # OTA接口请求因为有限制，所以一分钟执行四次READY_TO_ISSUE请求，一次ISSUE_FINISH请求
            Logger().sinfo('Order Controller Loop Start')
            gevent.sleep(5) # 供应商部分一分钟执行12次
            run_count +=1
            # TODO 是否需要增加时间范围限制
            with db_session:
                FlightOrder.get_for_update()
                order_list = select(o for o in FlightOrder if  o.ota_order_status in ota_order_status_list and o.provider_order_status in provider_order_status_list )
                Logger().sinfo('todo order list length %s' % len(order_list))

    @logger_config('test_MODULE',True)
    def req_test(self):
        TB_REQUEST_ID = Random.gen_alpha(19)
        TB_ORDER_ID = Random.gen_alpha(10)
        TB_OTA_NAME = 'tongcheng'
        TB_PROVIDER_CHANNEL = 'ceair'
        a = HttpRequest()

        c = a.request(method='GET',url='http://api.bigsec.com',timeout=3,provider_channel='fakeprovider_web',print_info=True,proxies={'http':'http://127.0.0.1:8080'})
        Logger().debug(c.content)

    def xxx(self):

        while 1:
            import requests
            a = HttpRequest()
            data = """
            _=5aae5a30c0cb11e887a4830dc22f9f04&searchCond={"adtCount":1,"chdCount":0,"infCount":0,"currency":"CNY","tripType":"OW","recommend":false,"reselect":"","page":"0","sortType":"a","sortExec":"a","segmentList":[{"deptCd":"SHA","arrCd":"SIN","deptDt":"2018-10-10","deptAirport":"","arrAirport":"","deptCdTxt":"上海","arrCdTxt":"新加坡","deptCityCode":"SHA","arrCityCode":"SIN"}]}
            """
            Logger().sinfo('start')
            Logger().sinfo(a.request(method='GET',url='http://116.196.108.195:8000/test_delay/').content)
            Logger().sinfo('end')
            gevent.sleep(5)







    def pwd_encrypt(self):
        """
        密码加密模块
        :param pwd:
        :return:
        """
        return md5_hash(self.username+'#'+self.password).lower()


    def alipay_qcode(self, trade_id, trade_data):

        """
        :param trade_id: 唯一ID
        :param trade_data: dict {'qcode_url':'https://qr.alipay.com/upx01604nwq4zafmegk64047'}
        :return:
        """

        if not trade_id:
            raise PayException('have no trade id')
        provider_trade_id = '%s_%s' % (self.provider_channel, trade_id)
        redis_pool = TBG.redis_conn.get_internal_pool()
        d = json.dumps({
            'trade_data': trade_data,
            'trade_id': provider_trade_id,
        })
        redis_pool.lpush('alipay_qcode_queue', d)
        Logger().sdebug("finish push alipay payment task")

        now = datetime.datetime.now()
        while True:
            if (datetime.datetime.now() - now).seconds <= 300:
                result = redis_pool.get('alipay_qcode_result_{}'.format(provider_trade_id))
                if result:
                    Logger().info('result %s'% result)
                    payment_result = json.loads(result)
                    if payment_result.get('result') == 'SUCCESS':
                        Logger().sdebug("alipay payment result ok")
                        redis_pool.expire('payment_task_result_{}'.format(
                            provider_trade_id), 0)
                        return True
                    else :
                        Logger().sdebug("alipay payment result error")
                        redis_pool.expire('payment_task_result_{}'.format(
                            provider_trade_id), 0)
                        raise PayException(payment_result.get('result'))
                else:
                    Logger().sdebug("alipay payment get result retry")
                    time.sleep(2)
            else:
                raise PayException('alipay payment failed')


    def http_test(self):

        while 1:

            http_session = HttpRequest(lock_proxy_pool='C')
            provider_app = ProviderAutoRepo.select('ceair_web_2')
            search_info = SearchInfo()
            search_info.from_airport = 'HKG'
            search_info.to_airport = 'BKK'
            search_info.from_date = '2019-05-27'
            search_info.trip_type = 'OW'
            search_info.adt_count = 1
            search_info.chd_count = 0
            search_info.attr_competion()
            print 123
            provider_app.test_search(http_session=http_session,search_info=search_info,is_only_search_scheduled_airline=False,cache_mode='REALTIME',)
            print search_info.return_status


            break


    def get_sss(self):

        pa = ProviderAutoRepo.select('airasia_web')
        print pa.get_session(renew=True,param_model={'ip':'127.0.0.2'})

    @logger_config('TEST', True)
    @db_session
    def run(self):
        """
        2219,45262619880509500X,黄菊彩,ADT,F,,866-2320449457
2220,421023199009241033,张子扬,ADT,M,,866-2320449458
        """
        from_airport = 'BKK'
        to_airport = 'SHA'
        from_date = '2019-05-30'
        http_session = HttpRequest()
        url = "https://sijipiao.fliggy.com/ie/flight_search_result_poller.do"
        params = {
            '_ksTS':'1556422549733_753',
            'callback': 'jsonp754',
            'supportMultiTrip': 'true',
            'searchBy': '1281',
            'childPassengerNum': '0',
            'infantPassengerNum': '0',
            'searchJourney': '[{{"depCityCode":"{from_airport}","arrCityCode":"{to_airport}","depCityName":"%E6%99%AE%E5%90%89%E5%B2%9B","arrCityName":"%E4%B8%8A%E6%B5%B7","depDate":"{from_date}","selectedFlights":[]}}]'.format(from_airport=from_airport,to_airport=to_airport,from_date=from_date),
            'tripType': '0',
            'searchCabinType': '0',
            'agentId': '-1',
            'controller': '1',
            'searchMode': '0',
            'b2g': '0',
            'formNo': '-1'

        }
        headers = {
            'Referer':'https://sijipiao.fliggy.com/ie/flight_search_result.htm?searchBy=1281&spm=181.7091613.a1z67.1002&_input_charset=utf-8&tripType=0&depCityName=%E6%99%AE%E5%90%89%E5%B2%9B&depCity=HKT&depDate=2019-05-07&arrCityName=%E4%B8%8A%E6%B5%B7&arrCity=SHA&arrDate='
        }
        cookies = {
            't':'2af109a82433ca098e55522d261de77f',
            '_tb_token':'5e8eee5fda337',
            'cookie2':'13caae69a9d2a73e5b70b4f3d26ddcc8',
            'enc':'D59bCos0XWcjAmkD7rxqcbYM0486ZRMtu215YWBZ9Px1bcdLN7M%2BktNjWrOidEQmKpns%2FJU8C7KQ9HelEpMj3A%3D%3D'
        }
        http_session.update_cookie(cookies)
        result = http_session.request(url=url, params=params,is_direct=True, timeout=5,headers=headers)
        print result.content
        return

        self.http_test()
        return
        http_session = HttpRequest(lock_proxy_pool='C')
        Logger().sinfo('afdasfdsafdsa')
        pp = http_session.preset_proxy_ip('A')
        http_session.request(url='https://www.baidu.com',is_direct=False,timeout=2)
        print http_session.last_http_result.proxy_pool
        # print http_session.request(url='https://www.baidu11111111111111111111111.com', is_direct=False, proxy_pool='E', timeout=2, proxies=pp)

        return


        for x in range(11112):
            TBG.tb_metrics.write(
                "TEST",
                tags=dict(
                    task='SCHEDULED_AIRLINE_CACHE_SYNC'

                ),
                fields=dict(
                    count=1
                ))
            print 1
            gevent.sleep(6)
        gevent.sleep(123213)

        cache_key = 'aaa'
        my_lock = TBG.redis_conn.redis_pool.lock(cache_key, timeout=300)
        have_lock = False
        try:
            Logger().sinfo('ready to get Lock')
            have_lock = my_lock.acquire(blocking=True)
            if have_lock:
                Logger().sinfo('have_lock wait ')
                time.sleep(15)

            else:
                Logger().sinfo('locked_hash %s ' % cache_key)
        except Exception as e:
            Logger().error(e)
        finally:
            if have_lock:
                try:
                    my_lock.release()
                except Exception as e:
                    pass

        return


        return
        for x in range(10):
            gevent.spawn(self.http_test)

        while 1:
            gevent.sleep(1)
        return

        from ..dao.iata_code import IATA_CODE
        IATA_AIRPORT_TO_CITY = {'JFK': 'NYC', 'BGA': 'GRA', 'HBE': 'ALY', 'TIU': 'WHO', 'LIN': 'MIL', 'EOH': 'MDE', 'AGB': 'MUC', 'HBB': 'HOB', 'CKU': 'CDV', 'PAC': 'PTY', 'SIG': 'SJU', 'NYO': 'STO',
                                'SVO': 'MOW', 'CPQ': 'SAO', 'NAY': 'PEK', 'PII': 'FAI', 'SXC': 'AVX', 'BWU': 'SYD', 'SXF': 'BER', 'DCF': 'DOM', 'YHM': 'YTO', 'PIE': 'TPA', 'DCA': 'WAS', 'TZA': 'BZE',
                                'HKK': 'WHO', 'TAF': 'ORN', 'HSV': 'APT', 'FGI': 'APW', 'LBG': 'PAR', 'RYG': 'OSL', 'SAP': 'MRJ', 'SAW': 'IST', 'CHA': 'APT', 'IAH': 'HOU', 'YMX': 'YMQ', 'BFI': 'SEA',
                                'GPA': 'SPJ', 'BQH': 'LON', 'WMT': 'ZYI', 'GIG': 'RIO', 'ITM': 'OSA', 'LHR': 'LON', 'BNA': 'APT', 'WME': 'KYF', 'PHJ': 'NTL', 'CXR': 'NHA', 'KIX': 'OSA', 'PZL': 'HLW',
                                'MEB': 'MEL', 'KIT': 'SPJ', 'VIR': 'DUR', 'BVA': 'PAR', 'GSE': 'GOT', 'SFB': 'ORL', 'WUN': 'KYF', 'YUL': 'YMQ', 'AEP': 'BUE', 'DME': 'MOW', 'NGC': 'GCN', 'TSF': 'VCE',
                                'ISL': 'IST', 'TSA': 'TPE', 'NGW': 'CRP', 'CRE': 'MYR', 'TSV': 'MRL', 'BHD': 'BFS', 'DTW': 'DTT', 'CRL': 'BRU', 'AMK': 'DRO', 'BMA': 'STO', 'SCK': 'SAC', 'SZB': 'KUL',
                                'UGB': 'PIP', 'ROB': 'MLW', 'LLW': 'LMB', 'SYQ': 'SJO', 'JUM': 'BJU', 'GEA': 'NOU', 'TTN': 'PHL', 'BMT': 'BPT', 'KBP': 'IEV', 'UVF': 'SLU', 'WBW': 'AVP', 'GRU': 'SAO',
                                'YTZ': 'YTO', 'YKF': 'YTO', 'CJB': 'SXV', 'JGC': 'GCN', 'DSS': 'DKR', 'BLR': 'SXV', 'MYZ': 'LMB', 'TRZ': 'SXV', 'PBA': 'BRW', 'DSI': 'VPS', 'EWR': 'NYC', 'TRF': 'OSL',
                                'GRK': 'ILE', 'VCP': 'SAO', 'KCG': 'KCL', 'PSM': 'BOS', 'AVV': 'MEL', 'MXP': 'MIL', 'LCY': 'LON', 'XCR': 'PAR', 'LCE': 'XPL', 'KCQ': 'KCL', 'OKD': 'SPK', 'CUB': 'CAE',
                                'PIK': 'GLA', 'LCK': 'CMH', 'HLA': 'JNB', 'JBT': 'BET', 'HND': 'TYO', 'JBQ': 'SDQ', 'CTS': 'SPK', 'VKO': 'MOW', 'VBS': 'VRN', 'PEK': 'BJS', 'SMF': 'SAC', 'LUK': 'CVG',
                                'YHU': 'YMQ', 'CGH': 'SAO', 'CGK': 'JKT', 'BGY': 'MIL', 'BKA': 'MOW', 'LFB': 'APL', 'BKL': 'CLE', 'ERS': 'WDH', 'PMF': 'MIL', 'IKA': 'THR', 'PVG': 'SHA', 'CGQ': 'SPA',
                                'SEN': 'LON', 'MDW': 'CHI', 'XFW': 'HAM', 'PMK': 'MRL', 'DMK': 'BKK', 'DNA': 'OKA', 'VVI': 'SRZ', 'CLD': 'SAN', 'DNL': 'AGS', 'IMK': 'BJU', 'CUX': 'CRP', 'TLC': 'MEX',
                                'FEW': 'CYS', 'CUC': 'GRA', 'YIP': 'DTT', 'BBX': 'PHL', 'OBT': 'ODM', 'GMP': 'SEL', 'ADJ': 'AMM', 'LTN': 'LON', 'PLU': 'BHZ', 'CDG': 'PAR', 'ORY': 'PAR', 'KEF': 'REK',
                                'WIL': 'NBO', 'YYZ': 'YTO', 'LER': 'KYF', 'FBK': 'FAI', 'ORD': 'CHI', 'FCO': 'ROM', 'TDW': 'AMA', 'CIB': 'AVX', 'CIA': 'ROM', 'ZSW': 'YPR', 'BPG': 'NOK', 'KNO': 'MES',
                                'AZA': 'PHX', 'TWH': 'AVX', 'SWF': 'NYC', 'GNB': 'LYS', 'HLP': 'JKT', 'MSC': 'PHX', 'UKB': 'OSA', 'RCB': 'HLW', 'YWH': 'YYJ', 'RKV': 'REK', 'TXL': 'BER', 'POX': 'PAR',
                                'TGU': 'MRJ', 'DAL': 'DFW', 'ENC': 'ETZ', 'LBC': 'HAM', 'FLG': 'GCN', 'IAD': 'WAS', 'ONT': 'LAX', 'CNW': 'ACT', 'MTX': 'FAI', 'ICN': 'SEL', 'DHI': 'BJU', 'HAX': 'MKO',
                                'STN': 'LON', 'EJA': 'GRA', 'BQK': 'SSI', 'CNF': 'BHZ', 'DWC': 'DXB', 'EZE': 'BUE', 'FXE': 'FLL', 'HGD': 'MRL', 'KLX': 'SPJ', 'MCO': 'ORL', 'SDU': 'RIO', 'SDV': 'TLV',
                                'TFN': 'TCI', 'VST': 'STO', 'NRN': 'DUS', 'MCI': 'MKC', 'LGA': 'NYC', 'NKM': 'NGO', 'HHN': 'FRA', 'CPS': 'STL', 'TFS': 'TCI', 'PDK': 'ATL', 'BLD': 'LAS', 'RSW': 'FMY',
                                'LGW': 'LON', 'ARN': 'STO', 'NRT': 'TYO'}

        cache = {}

        scheduled_airline_cache_list = TBG.redis_conn.redis_pool.keys('scheduled_airline_cache_HX_2019-04')
        for scheduled_airline_cache in scheduled_airline_cache_list:
            ret = TBG.redis_conn.redis_pool.get(scheduled_airline_cache)
            Logger().sinfo('scheduled_airline_cache %s' % scheduled_airline_cache)
            if ret:
                airline_list = []
                ret = json.loads(ret)
                Logger().sinfo('raw length %s' % len(ret))
                cache[scheduled_airline_cache] = ret
                break
        # with open('/Users/xiaotian/tmp/scheduled_airline_repo.txt','w') as fp:
        #     fp.write(json.dumps(cache))
                new_ret = []
                for airline in ret:
                    airline_list.append(airline)
                    # Logger().sdebug('11111111111111111airline %s' % airline)
                    from_airport,to_airport = airline.split('-')
                    for transit_1 in ret:

                        t1_from_airport, t1_to_airport = transit_1.split('-')
                        if to_airport == t1_from_airport and t1_to_airport != from_airport :
                            # Logger().sdebug('transit_1 %s' % transit_1)
                            if IATA_CODE.has_key(from_airport) and IATA_CODE.has_key(to_airport) and IATA_CODE.has_key(t1_to_airport):
                                if IATA_CODE[from_airport]['cn_country'] != IATA_CODE[to_airport]['cn_country'] and IATA_CODE[from_airport]['cn_country'] == IATA_CODE[t1_to_airport]['cn_country']:
                                    # Logger().sdebug('continue')
                                    continue

                                new_airline = '%s-%s' % (from_airport,t1_to_airport)
                                # Logger().sdebug('new_airline %s' % new_airline)
                                airline_list.append(new_airline)
                                # for transit_2 in ret:
                                #     t2_from_airport, t2_to_airport = transit_2.split('-')
                                #     if t1_to_airport == t2_from_airport:
                                #         airline_list.append('%s-%s' % (from_airport, t2_to_airport))
                Logger().sdebug('before compressed length %s' % len(airline_list))
                result = list(set(airline_list))
                Logger().sdebug('after length %s' % len(result))
                # redis_conn.redis_pool.set(scheduled_airline_cache,json.dumps(result))

        return

        search_info = OrderInfo()
        print isinstance(search_info,dict)
        return
        a = SubOrder(from_airport='asdfdas')

        return
        fo = SubOrder.get(id=2547)
        print fo
        for sub_order in fo.sub_orders:
            print sub_order
            for ied in sub_order.income_expense_details:
                print ied

        return

        from ..controller.fusing_limiter import FusingControl
        FusingControl.add_fusing(fusing_type='aaa',fusing_var='xxx',source='afd',ttl=3)
        print FusingControl.is_fusing(fusing_type='aaa',fusing_var='xxx')
        print FusingControl.fusing_repo_list()
        time.sleep(4)
        print FusingControl.is_fusing(fusing_type='aaa',fusing_var='xxx')
        print FusingControl.fusing_repo_list()
        return
        # from line_profiler import LineProfiler
        # import random
        # numbers = [random.randint(1, 100) for i in range(1000)]
        # lp = LineProfiler()
        # lp_wrapper = lp(profile_text)
        # lp_wrapper()
        # lp.print_stats()
        search_info = OrderInfo()
        search_info.adt_count = 1
        search_info.from_date = '2019-04-02'
        search_info.ret_date = '2019-04-22'
        search_info.from_airport = 'SHA'
        search_info.to_airport = 'HRB'
        search_info.trip_type = 'OW'
        # search_info.attr_competion()  # 属性自动补全
        #
        # self_ota_app = OTARepo.select('fakeota')
        # self_ota_app.search_info = search_info
        # router = Router(self_ota_app, search_mode='sync_call',is_allow_cabin_revise=False,is_allow_fusing=False,is_allow_max_pax_count_limit=False,is_allow_min_cabin_count_limit=False)
        # router.run()

        # return

        from ..automatic_repo.base import ProviderAutoRepo

        provider_app = ProviderAutoRepo.select('fakeprovider_web')

        provider_app.flight_crawl(search_info=search_info)

        for srouting in search_info.assoc_search_routings:
            print json.dumps(srouting)

        # a = "x-(x*0.04+8)"
        # b = a.replace('x',100)
        # print eval(b)
        #
        # self.search_info = SearchInfo()
        # self.search_info.from_date = '2019-02-28'
        # self.search_info.from_airport = 'CNX'
        # self.search_info.to_airport = 'KMG'
        # self.search_info.trip_type = 'OW'
        # self.search_info.attr_competion()  # 属性自动补全
        #
        # from ..ota_repo.base import OTARepo
        # from ..router.core import Router
        #
        # self_ota_app = OTARepo.select('tongcheng')
        # self_ota_app.search_info = self.search_info
        # router = Router(self_ota_app, search_mode='sync_call',is_allow_cabin_revise=False,is_allow_fusing=False,is_allow_max_pax_count_limit=False,is_allow_min_cabin_count_limit=False)
        # router.run()
        #
        #
        # for srouting in self.search_info.assoc_search_routings:
        #     print srouting.routing_key_detail

        # pa = ProviderAutoRepo.select('fakeprovider_web')
        # pa.flight_search(search_info=self.search_info)
        #
        # # print json.dumps(self.search_info)
        # # 3200 -》 2096
        # for srouting in self.search_info.assoc_search_routings:
        #     print json.dumps(srouting)

        # import zlib
        # # print  zlib.decompress('aa')
        # from app import cache_access_object
        #
        # a = """
        # {"sub_orders": [], "adult_price_full_price": 1500.0, "child_price_forsale": 0.0, "max_passenger_count": 9, "adult_full_price": 0.0, "ticket_invoice_type": 0, "currency": "CNY", "flight_routing_id": "", "segment_min_cabin_count": 9, "child_tax": 339.0, "child_price": 840.0, "reference_adult_tax": 0, "adult_price": 1120.0, "routing_key": "8lFfFJVQG9kT8FDfxwXSy8EfX9Ef1ATLzATL5EDMywnTBNEfLtkQ8xHf8hzMwADNxUjMyATOxAjM8BjLwwHMuADN4wHMuAjMxEDfw4CM8BjLwwHMukzMzwHMuADN4wHMukzMzwHMuAjMxEDfiV2dfJXZklmdvJHcltWYmxnclRWa29mcwV2ahZGfKlFS8JFfyUjMV1Ef1EDNwUDMzATOxAjM85UQDxXN1IjM1AzMwkTMwIDfLtkQ8djV", "adult_price_forsale": 0.0, "adult_price_discount": 86, "min_passenger_count": 1, "fare_basis": "", "reference_adult_price": 0, "inf_price_forsale": 0.0, "reference_cabin_grade": "Y", "reference_cabin": "R", "sub_orders_raw_routing": [], "inf_price": 0.0, "nationality_type": 0, "flight_order": null, "inf_tax": 0.0, "ret_segments": [], "nationality": "", "validating_carrier": "", "from_segments": [{"dep_terminal": "T1", "ret_flight_routing": null, "stop_cities": "", "from_flight_routing": null, "duration": 320, "flight_segment_instance": null, "dep_time": "2019-03-05 22:55:00", "stop_airports": "", "flight_number": "MU252", "cabin_grade": "Y", "dep_airport": "BKK", "is_saved": false, "code_share": "false", "cabin": "R", "cabin_count": 9, "arr_airport": "CAN", "aircraft_code": "", "operating_flight_no": "", "operating_carrier": "", "baggage_info": "{}", "refund_info": "{}", "arr_time": "2019-03-05 04:15:00", "flight_segment_id": "", "routing_number": 1, "change_info": "{}", "arr_terminal": "T2", "carrier": "MU"}], "data_source": "RTS_SUCCESS", "product_type": "DEFAULT", "reservation_type": "", "is_include_operation_carrier": 0, "is_saved": false, "adult_tax": 339.0, "routing_key_detail": "V7|BKK|201903052255|CAN|201903050415|MU252|R|HYJ|fakeprovider|fakeprovider_web|1120.0|339.0|840.0|339.0|0.0|0.0|1120.0|840.0|0.0|20190225140038||||BKK|CAN|2019-03-05|OW|O2I|1|1|NOFARE|Y|", "flight_routing_instance": null, "adult_age_restriction": "", "child_publish_price": 0.0, "publish_price": 0.0}
        # """
        #
        # compressed = zlib.compress(a)
        #
        # TBG.cache_access_object.insert(cache_type='farecache', provider='111', param_model={'a':'aa'}, ret_data=a,is_compress=True)
        #
        # bb = TBG.cache_access_object.get(cache_type='farecache', provider='111', param_model={'a': 'aa'},is_decompress=True)
        # print  bb
        # print json.loads()

        # a = """
        # {"sub_orders": [], "adult_price_full_price": 1500.0, "child_price_forsale": 0.0, "max_passenger_count": 9, "adult_full_price": 0.0, "ticket_invoice_type": 0, "currency": "CNY", "flight_routing_id": "", "segment_min_cabin_count": 9, "child_tax": 339.0, "child_price": 840.0, "reference_adult_tax": 0, "adult_price": 1120.0, "routing_key": "8lFfFJVQG9kT8FDfxwXSy8EfX9Ef1ATLzATL5EDMywnTBNEfLtkQ8xHf8hzMwADNxUjMyATOxAjM8BjLwwHMuADN4wHMuAjMxEDfw4CM8BjLwwHMukzMzwHMuADN4wHMukzMzwHMuAjMxEDfiV2dfJXZklmdvJHcltWYmxnclRWa29mcwV2ahZGfKlFS8JFfyUjMV1Ef1EDNwUDMzATOxAjM85UQDxXN1IjM1AzMwkTMwIDfLtkQ8djV", "adult_price_forsale": 0.0, "adult_price_discount": 86, "min_passenger_count": 1, "fare_basis": "", "reference_adult_price": 0, "inf_price_forsale": 0.0, "reference_cabin_grade": "Y", "reference_cabin": "R", "sub_orders_raw_routing": [], "inf_price": 0.0, "nationality_type": 0, "flight_order": null, "inf_tax": 0.0, "ret_segments": [], "nationality": "", "validating_carrier": "", "from_segments": [{"dep_terminal": "T1", "ret_flight_routing": null, "stop_cities": "", "from_flight_routing": null, "duration": 320, "flight_segment_instance": null, "dep_time": "2019-03-05 22:55:00", "stop_airports": "", "flight_number": "MU252", "cabin_grade": "Y", "dep_airport": "BKK", "is_saved": false, "code_share": "false", "cabin": "R", "cabin_count": 9, "arr_airport": "CAN", "aircraft_code": "", "operating_flight_no": "", "operating_carrier": "", "baggage_info": "{}", "refund_info": "{}", "arr_time": "2019-03-05 04:15:00", "flight_segment_id": "", "routing_number": 1, "change_info": "{}", "arr_terminal": "T2", "carrier": "MU"}], "data_source": "RTS_SUCCESS", "product_type": "DEFAULT", "reservation_type": "", "is_include_operation_carrier": 0, "is_saved": false, "adult_tax": 339.0, "routing_key_detail": "V7|BKK|201903052255|CAN|201903050415|MU252|R|HYJ|fakeprovider|fakeprovider_web|1120.0|339.0|840.0|339.0|0.0|0.0|1120.0|840.0|0.0|20190225140038||||BKK|CAN|2019-03-05|OW|O2I|1|1|NOFARE|Y|", "flight_routing_instance": null, "adult_age_restriction": "", "child_publish_price": 0.0, "publish_price": 0.0}
        # """
        #
        # message = 'abcd1234'
        #
        # s = time.time()
        # for x in range(10000):
        #
        #     ffff = zlib.decompress(compressed)
        #
        # print time.time() - s


            # rk_dict = RoutingKey.unserialize(srouting.routing_key_detail)
            # print rk_dict


        # self.test_proxy()

        # from ..controller.freq_limiter import ProviderSearchFreqLimiter
        #
        # ProviderSearchFreqLimiter.add('a',100)
        # print ProviderSearchFreqLimiter.repo_list_with_cache()
        # ProviderSearchFreqLimiter.delete('xx1x')
        # print ProviderSearchFreqLimiter.repo_list()
        # print ProviderSearchFreqLimiter.repo_list_with_cache()
        # ProviderSearchFreqLimiter.acquire_lock('a',proxy_pool='A',blocking=True,timeout=3)

        # from pony.orm import sql_debug
        # sql_debug(True)

        # for x in range(0,5):
        #     gevent.spawn(self.http_test())
        #
        # gevent.sleep(100000)
        #
        # return
        # flight_order = FlightOrder.get(id=1)
        # print int(flight_order.routing)

        # old_flight_order = FlightOrder.get(id=267)
        # flight_order.contacts = old_flight_order.contacts
        # flight_order.income_expense_details = old_flight_order.income_expense_details
        # flight_order.routing = old_flight_order.routing
        # flight_order.sub_orders = old_flight_order.sub_orders
        # flight_order.passengers = old_flight_order.passengers
        # flight_order.meta = old_flight_order.meta
        # flight_order.ffp_account = old_flight_order.ffp_account

        # routing_id = old_flight_order.routing.id
        # old_flight_order.routing = None
        # commit()
        # flight_order.routing = routing_id

        # flight_order.contacts = old_flight_order.contacts

        # old_flight_order.sub_orders = []
        # return
        #
        #
        # self.get_sss()
        # return
        # while 1:
        #     self.http_test()

        # sub_order = SubOrder[261]
        # for pax in sub_order.passengers:
        #     sub_pax_list = select(p for p in Person2FlightOrder if p.flight_order.id == 320 and p.used_card_no == pax.used_card_no)
        # sub_order.passengers = sub_pax_list
        # return

        # self.provider_channel = 'test_provider'
        # # 支付宝qcode 测试
        # self.alipay_qcode(Random.gen_request_id(),{'qcode_url':'https://qr.alipay.com/upx01281g2t5xfsd7aop2026'})
        #
        # return
        #
        # mr = MobileRepo.get(mobile_num='178919331719')
        # # print mr.sms_device_id
        # http_session = HttpRequest()
        #
        # #
        # #list 拉取接口
        # start_time = Time.curr_date_obj() - datetime.timedelta(hours=2)
        # end_time = Time.curr_date_obj()
        # data = {
        #     'Username': self.username,
        #     'Password': self.pwd_encrypt(),
        #     'OrderStatus': 'N',
        #     'OrderBeginDataTime': start_time.strftime('%Y-%m-%d %H:%M:%S'),
        #     'orderEndDataTime': end_time.strftime('%Y-%m-%d %H:%M:%S')
        # }
        # result = http_session.request(method='POST', url=self.order_list_by_poll_url, json=data, verify=False).to_json()
        # Logger().info('result %s' %result)

        #详情拉取接口
        #
        # redis_conn = RedisPool('127.0.0.1', 6379,
        #                        3, None)
        #
        # TBG.redis_conn.insert_value('fare_cache_fakeprovider_b1b7f7aab07576bb7e113d783b7155b363eeb797b5c32992bdd489e74088bd1a',"{\"sub_orders\": [], \"comment\": \"\", \"providers_total_price\": null, \"from_date\": \"2018-12-12\", \"provider_search_err_code\": \"\", \"rkey_pax_hash\": \"\", \"adt_count\": 1, \"assoc_order_routing_key\": \"\", \"ota_child_price\": 0.0, \"ota_inf_price\": 0.0, \"is_modified_card_no\": 0, \"meta\": null, \"ota_type\": \"\", \"trip_type\": \"OW\", \"chd_count\": 1, \"ota_query_time\": null, \"income_expense_details\": [], \"extra_data_2\": null, \"extra_data_3\": null, \"pr\": 2, \"to_airport\": \"SIN\", \"ota_create_order_time\": null, \"return_details\": \"\", \"ota_work_flow\": \"verify\", \"operation_product_mode\": \"\", \"flight_order_keys\": [\"sub_orders\", \"comment\", \"providers_total_price\", \"rkey_pax_hash\", \"adt_count\", \"ota_child_price\", \"operation_product_mode\", \"meta\", \"ota_type\", \"trip_type\", \"chd_count\", \"ota_query_time\", \"income_expense_details\", \"to_airport\", \"ota_create_order_time\", \"contacts\", \"from_date\", \"to_city\", \"to_country\", \"from_airport\", \"routing\", \"ota_pay_price\", \"from_city\", \"operation_product_type\", \"ota_pay_time\", \"routing_range\", \"provider\", \"from_country\", \"ota_order_status\", \"all_finished_time\", \"assoc_order_id\", \"ota_backfill_time\", \"ota_order_id\", \"process_duration\", \"is_test_order\", \"passengers\", \"providers_status\", \"pnr_code\", \"ffp_account\", \"ota_adult_price\", \"inf_count\", \"ota_inf_price\", \"session_id\", \"ota_name\", \"is_manual\", \"provider_channel\", \"ret_date\"], \"to_city\": \"\\u65b0\\u52a0\\u5761\", \"cache_source\": \"provider\", \"from_airport\": \"SHA\", \"routing\": null, \"ota_pay_price\": null, \"from_city\": \"\\u4e0a\\u6d77\", \"operation_product_type\": \"\", \"is_saved\": false, \"extra_data\": null, \"ota_order_status\": \"\", \"routing_range\": \"OUT\", \"flight_order_instance\": null, \"verify_routing_key\": \"w4CM8BjLwwHfw4CM0EDfw4CMwYDf8BjLwIzM8BjLwAjMxwHf85kSZhkMyITVNBDMwADM0QTO1QDN1EjTJNFMwADMwADM4UDN0UTMBh0U\", \"passengers\": [], \"providers_status\": \"\", \"provider_search_raw_code\": \"\", \"search_finished\": true, \"from_country\": \"\\u4e2d\\u56fd\", \"fare_operation\": \"\", \"notice_pay_status\": \"\", \"all_finished_time\": null, \"is_manual\": 0, \"assoc_order_id\": \"\", \"search_time\": \"2018-11-07 14:30:28\", \"ota_backfill_time\": null, \"ota_order_id\": \"\", \"process_duration\": 0, \"is_test_order\": 0, \"order_detail_status\": \"\", \"return_status\": \"\", \"ota_pay_time\": null, \"pnr_code\": \"\", \"ffp_account\": null, \"task_id\": null, \"inf_count\": 0, \"contacts\": [], \"provider\": \"\", \"session_id\": \"\", \"assoc_search_routings\": [{\"sub_orders\": [], \"flight_routing_keys\": [\"sub_orders\", \"max_passenger_count\", \"ticket_invoice_type\", \"currency\", \"segment_min_cabin_count\", \"child_tax\", \"child_price\", \"adult_price\", \"routing_key\", \"adult_price_discount\", \"min_passenger_count\", \"fare_basis\", \"adult_full_price\", \"inf_price\", \"nationality_type\", \"inf_tax\", \"ret_segments\", \"nationality\", \"validating_carrier\", \"from_segments\", \"flight_order\", \"product_type\", \"reservation_type\", \"adult_tax\", \"routing_key_detail\", \"adult_age_restriction\", \"child_publish_price\", \"publish_price\"], \"adult_price_full_price\": 1500.0, \"max_passenger_count\": 9, \"ticket_invoice_type\": 0, \"currency\": \"CNY\", \"flight_routing_id\": \"\", \"segment_min_cabin_count\": 9, \"child_tax\": 140.0, \"child_price\": 600.0, \"adult_price\": 1200.0, \"routing_key\": \"w4CM8BjLwwHfw4CM0EDfw4CMwYDf8BjLwIzM8BjLwAjMxwHf85kSZhkMyITVNBDMwADM0QTO1QDN1EjTJNFMwADMwADM4UDN0UTMBh0U\", \"adult_price_discount\": 86, \"min_passenger_count\": 1, \"fare_basis\": \"\", \"adult_full_price\": 0.0, \"inf_price\": 0.0, \"nationality_type\": 0, \"inf_tax\": 0.0, \"ret_segments\": [], \"nationality\": \"\", \"validating_carrier\": \"\", \"from_segments\": [{\"dep_terminal\": \"T1\", \"ret_flight_routing\": null, \"baggage_info\": \"{}\", \"stop_cities\": \"\", \"from_flight_routing\": null, \"duration\": 320, \"flight_segment_instance\": null, \"dep_time\": \"2018-12-12 10:00:00\", \"stop_airports\": \"\", \"flight_number\": \"MU222\", \"cabin_grade\": \"Y\", \"dep_airport\": \"SHA\", \"is_saved\": false, \"cabin\": \"N\", \"cabin_count\": 9, \"arr_airport\": \"SIN\", \"aircraft_code\": \"\", \"operating_flight_no\": \"\", \"operating_carrier\": \"\", \"code_share\": \"false\", \"refund_info\": \"{}\", \"arr_time\": \"2018-12-12 14:00:00\", \"flight_segment_id\": \"\", \"routing_number\": 1, \"flight_segment_keys\": [\"dep_terminal\", \"ret_flight_routing\", \"baggage_info\", \"from_flight_routing\", \"duration\", \"dep_time\", \"stop_airports\", \"flight_number\", \"cabin_grade\", \"dep_airport\", \"code_share\", \"cabin\", \"routing_number\", \"arr_airport\", \"aircraft_code\", \"operating_flight_no\", \"operating_carrier\", \"stop_cities\", \"refund_info\", \"arr_time\", \"cabin_count\", \"change_info\", \"arr_terminal\", \"carrier\"], \"change_info\": \"{}\", \"arr_terminal\": \"T2\", \"carrier\": \"MU\"}], \"flight_order\": null, \"product_type\": \"DEFAULT\", \"reservation_type\": \"\", \"is_saved\": false, \"adult_tax\": 320.0, \"routing_key_detail\": \"SHA1544580000000SIN1544594400000MU222HYJN|||1200.0|320.0||600.0|140.0||0.0|0.0\", \"flight_routing_instance\": null, \"adult_age_restriction\": \"\", \"child_publish_price\": 0.0, \"publish_price\": 0.0}], \"ota_name\": \"\", \"ota_adult_price\": 0.0, \"flight_order_id\": \"\", \"to_country\": \"\\u65b0\\u52a0\\u5761\", \"total_latency\": 0, \"notice_issue_status\": \"\", \"provider_channel\": \"\", \"ret_date\": null}")

        # 对账逻辑
        # with codecs.open('bill.txt','w',encoding='gbk' ) as fp:
        #     pay_list = select(o for o in IncomeExpenseDetail if o.expense_source == PaySource[3] and o.trade_type == 'EXPENSE')
        #
        #     pay_list = pay_list.order_by(desc(IncomeExpenseDetail.id))
        #     data = []
        #     fp.write('支付金额,OTA,供应商渠道,子订单ID,OTAID,支付渠道,routing信息,航段信息,乘客信息,支付时间')
        #     for p in pay_list:
        #
        #         paxs = []
        #         for pax in p.sub_order.passengers:
        #             pax = "{p2fo_id},{pid},{name},{age_type},{gender},{mobile},{ticket_no}".format(p2fo_id=pax.id, pid=pax.used_card_no, name=pax.person.name, age_type=pax.person.age_type,
        #                                                                                            gender=pax.person.gender, mobile=pax.person.mobile, ticket_no=pax.ticket_no)
        #             paxs.append(pax)
        #         paxs_str = ','.join(paxs)
        #         Logger().sdebug('p.order %s' % p.id)
        #
        #         routing_str = "【{from_city}】-【{to_city}】，出发日期:{from_date}，返程日期:{ret_date}".format(from_city=p.sub_order.from_city, to_city=p.sub_order.to_city, from_date=p.sub_order.from_date, ret_date=p.sub_order.ret_date)
        #         segments = []
        #         if p.sub_order.routing:
        #             for s in p.sub_order.routing.from_segments:
        #                 seg_str = "去程：{flight_number}，{cabin_grade}舱{cabin} 【{dep_airport}】【{dep_terminal}】【{dep_time}】-【{arr_airport}】【{arr_terminal}】【{arr_time}】".format(dep_airport=s.dep_airport,
        #                                                                                                                                                                     dep_time=s.dep_time,
        #                                                                                                                                                                     dep_terminal=s.dep_terminal,
        #                                                                                                                                                                     arr_airport=s.arr_airport,
        #                                                                                                                                                                     arr_time=s.arr_time,
        #                                                                                                                                                                     arr_terminal=s.arr_terminal,
        #                                                                                                                                                                     flight_number=s.flight_number,
        #                                                                                                                                                                     cabin_grade=s.cabin_grade,
        #                                                                                                                                                                     cabin=s.cabin)
        #                 segments.append(seg_str)
        #         segments_str = ','.join(segments)
        #
        #
        #         data_str = "%s | %s | %s | %s | %s | %s | %s | %s | %s | %s"% (p.pay_amount,p.flight_order.ota_name,p.flight_order.provider_channel,p.id,p.flight_order.ota_order_id,p.pay_channel,routing_str,segments_str,paxs_str,str(p.pay_time))
        #         fp.write(data_str)
        #         print data_str
        # data = {
        #     'Username': self.username,
        #     'Password': self.pwd_encrypt(),
        #     'OrderSerialid': 'OCCP7XQSC10FTH008261',
        # }
        # result = http_session.request(method='POST', url=self.order_detail_by_poll_url,  json=data, verify=False).to_json()
        # Logger().info('result %s' % result)

        # # 票号回填接口
        # pax_infos = []
        # pax_infos.append({
        #     'PassengerName': "黄菊彩",
        #     'Pnr': 'IEZ51S',
        #     'TicketNo': "866-2320449457",
        # })
        # pax_infos.append({
        #     'PassengerName': "张子扬",
        #     'Pnr': 'IEZ512',
        #     'TicketNo': "866-2320449458",
        # })
        # data = {
        #     'Username': self.username,
        #     'Password': self.pwd_encrypt(),
        #     'OrderSerialid': 'OBWGJQKQC107G7007356',
        #     'ticketInfo': pax_infos,
        #     'IsTicketSuccess':'T'
        # }
        # result = http_session.request(method='POST', url=self.set_order_issued_url, json=data, verify=False).to_json()
        # Logger().info('result %s' %result)

        # http_session = HttpRequest()
        # url = 'https://m.ceair.com/mobile/user/user-ffp!toReg.shtml?channel=login&area=null'
        # http_session.request(url=url, method='GET', proxy_mode='random')
        # # self.req_test()


        # my_lock = TBG.redis_conn.redis_pool.lock('xxxxx', timeout=30)
        # try:
        #     my_lock.extend(60)
        # except Exception as e:
        #     pass
        # have_lock = my_lock.acquire(blocking=False)
        # try:
        #     my_lock.extend(60)
        # except Exception as e:
        #     pass

        # fl = FlightOrder[10]
        # fl.routing_range = 'IxxfdaN'
        # # TBG.tourbillon_db.execute('update flight_order set routing_range ="XXX" where id = 10 ' )
        # gevent.sleep(5)
        # commit()
        # flush()
        # for x in range(0,10):
        #     gevent.spawn(self.xxx)
        #
        # while 1:
        #     gevent.sleep(5)
        # while 1:
        #     Logger().sinfo('get message!!!!!!!!!')
        #     sms_msg = Smser().get_ceair_booking_verify_code(sms_device_id='xiaomi1')
        #     Logger().sinfo('sms_msg %s'% sms_msg)
        #     gevent.sleep(10)
        # print "%s" % TBG.global_config['FORAUTOMATIC_MOBILE']['mobile']
        # self.req_test()
        # # cc = CaptchaCracker.select('Fateadm')
        # # http = HttpRequest()
        # # while 1:
        #     a = http.request(method='GET',url='https://tssc.sinaapp.com/getip.php',proxy_mode='random',provider_channel='ceair_web_2',verify=False).content
        #     print a
        #     gevent.sleep(1)




    def test_proxy(self):
        c = 1
        s = HttpRequest(lock_proxy_pool='A')
        while 1:

            result = s.request(method='GET',url='https://pv.sohu.com/cityjson',is_direct=True,verify=False).content
            print result
            time.sleep(5)
    @db_session
    def flight_crawl_task(self,search_info):
        """
        航班爬取
        :param search_info:
        :return:
        """
        # Logger().info(search_info)
        # time.sleep(5)
        search_info = SearchInfo(**search_info)
        provider_app = ProviderAutoRepo.select(search_info.provider)
        search_info_with_result = provider_app.flight_crawl(search_info=search_info)
        search_info_with_result.attr_competion()
        search_info_with_result.search_time = Time.time_str()
        if search_info.routing and search_info.routing.routing_key_detail:
            Logger().sinfo(search_info.routing.routing_key_detail)
        query_params = {
            'from_date': search_info_with_result.from_date,
            'from_airport': search_info_with_result.from_airport,
            'to_airport': search_info_with_result.to_airport,
            'ret_date': search_info_with_result.ret_date,
            'trip_type': search_info_with_result.trip_type
        }
        TBG.cache_access_object.insert(cache_type='fare_cache', provider=search_info.provider, param_model=query_params, ret_data=search_info_with_result)
        for routing in search_info_with_result.assoc_search_routings:
            # 存储至redis
            # 存储至数据库
            Logger().sinfo(search_info_with_result)
            ffr = FlightFareRepo(routing_key_detail=routing.routing_key_detail,
                                 from_date=search_info_with_result.from_date,
                                 ret_date=search_info_with_result.ret_date if search_info_with_result.ret_date else None,
                                 reference_cabin_grade=routing.from_segments[0].cabin_grade,
                                 from_airport=search_info_with_result.from_airport,
                                 to_airport=search_info_with_result.to_airport,
                                 from_city=convert_unicode(search_info_with_result.from_city),
                                 to_city=convert_unicode(search_info_with_result.to_city),
                                 from_country=convert_unicode(search_info_with_result.from_country),
                                 to_country=convert_unicode(search_info_with_result.to_country),
                                 adult_price=routing.adult_price,
                                 adult_tax=routing.adult_price,
                                 child_price=routing.child_price,
                                 child_tax=routing.child_tax,
                                 product_type=routing.product_type,
                                 reference_flight_number=routing.from_segments[0].flight_number,
                                 reference_carrier=routing.from_segments[0].carrier,
                                 routing_range=search_info_with_result.routing_range,
                                 trip_type=search_info_with_result.trip_type,
                                 provider=search_info_with_result.provider
                                 )


    def create_fake_order(self):
        p = PaxInfo()
        p.name = '重打ccc放大'
        p.passenger_id = '123'
        p.used_card_type ='PP'
        f = FFPAccountInfo()
        f.reg_person = p
        f.username = 'asfdasdfa'

        b = OrderInfo()
        b.ffp_account = f
        b.assoc_order_id = 'xxxxxxxxxxxxxxxxxxxxxxxxxxx'
        b.passengers.append(p)
        a = FlightRoutingInfo()
        b.routing = a
        c = FlightSegmentInfo()
        a.from_segments.append(c)
        b.save(lazy_flush=True)

    def worker(self):
        for k,v in self.ddd.iteritems():
            v.assoc_order_id = 'fdasfdafdsa'
            print v.assoc_order_id



        # b = PaxInfo()
        # b.birthdate = '2019-01-01'
        # b.save()
        # a=OrderInfo()
        # a.from_date = '2018-07-11 19:49:15'
        # a.save()
        # d = {}
        # di = FlightRouting.__dict__['_new_attrs_']
        # for k in di:
        #     if not  isinstance(k,pony.orm.core.PrimaryKey) :
        #         if isinstance(k,pony.orm.core.Optional) or isinstance(k,pony.orm.core.Required):
        #             if 'reverse' not in k.name:
        #                 d[k.name] = k.default
        #         elif isinstance(k,pony.orm.core.Set):
        #             d[k.name] = []
        #         else:
        #             pass
        #
        # print d
        # a = SearchInfo()
    #     import pickle
    #     pickle.dumps(a)
    #     a.assoc_order_id = '111'
    #     import json
    #     print json.dumps(a)
    #
    #     for task in  select(o for o in FlightCrawlerTask):
    #         print task
    #         task.provider = 'fffff'
    #
    #
    #     # p = PaxInfo()
    #     # p.name = '重打ccc放大'
    #     # p.passenger_id = '123'
    #     # p.used_card_type ='PP'
    #     # f = FFPAccountInfo()
    #     # f.reg_person = p
    #     # f.username = 'asfdasdfa'
    #     #
    #     # b = OrderInfo()
    #     # b.ffp_account = f
    #     # b.assoc_order_id = 'xxxxxx'
    #     # b.passengers.append(p)
    #     # a = FlightRoutingInfo()
    #     # b.routing = a
    #     # c = FlightSegmentInfo()
    #     # a.from_segments.append(c)
    #     # a.save(lazy_flush=True)
    #     # b.save(lazy_flush=True)
    #     # f.save(lazy_flush=True)
    #
    #
    #
    #     #
    #     # a = FlightRouting[8]
    #     # print a.from_date.strftime('%Y%m%d%H%M%S')
    #     # a = FlightRoutingInfo()
    #     # a.from_date = datetime.now()
    #     # a.save()
    #     # a = ContactInfo()
    #     # a.d.name = 'aaa'
    #     # b = ContactInfo()
    #     # b.d.name = 'bbbb'
    #     # c = ContactInfo()
    #     # c.d.name = 'cccc'
    #     #
    #     # a.save(lazy_flush=True)
    #     # b.save(lazy_flush=True)
    #     # c.save(lazy_flush=True)
    #
    #     # p = Person(fdafda=123)
    #     # p2f = Person2FlightOrder()
    #     # p2f.person = p
    #     # flush()
    #     # print p.id
    #     # print p2f.id
    #     # print a['']
    #     # b.arr_airport = '1'
    #     # print a.ret_segments.add(b)
    #     # print [x for x in a.ret_segments][0].arr_airport
    #     # print a.to_dict(related_objects=True,with_lazy=False,with_collections=True)




        Logger().sinfo('asdf')


if __name__ == '__main__':
    pass