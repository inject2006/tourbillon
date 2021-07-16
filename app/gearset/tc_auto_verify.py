# coding=utf8

import requests
import datetime
import random
import string
import time
import redis
import json
from selenium import webdriver
from urllib import quote
from flask_script import Command


class TCAutoVerify(Command):

    def h5_run(self, proxy=''):
        session = requests.Session()
        session.headers = {
                # 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.80 Safari/{}.36'.format(
                #     random.randint(100, 999)),
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 11_0 like Mac OS X) AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Mobile/15A372 Safari/604.1',
                'Referer': 'https://m.ly.com/tiflightnfe/book2.html/TH_THL_GTHTCTH/TCPL/TH20190119191901M9A3L453FMOSBN7SFPQM68BHMHHIP44C8ZS68EQ4ZSFS1RPO/258_OW_HKG_SHA_20190131_null_1_0%2320190131_MU8979_X%230_0%23TCPL/THL',
                'touch-token':	'1',
                'Host':	'm.ly.com',
                'Connection': 'keep-alive',
                'Pragma':	'no-cache',
                'Cache-Control':	'no-cache',
                'Accept-Encoding':	'gzip, deflate, br',
                'Accept-Language':	'en-GB,en;q=0.9,en-US;q=0.8,zh-CN;q=0.7,zh;q=0.6',
                # 'Refer': 'https://www.ly.com/iflight/flight-book1.aspx?para=0*HRB*FMA*{}**YSCF*1*0*1&advanced=false&orgAirCode=false&desAirCode=false'.format(datetime.datetime.now().strftime('%Y-%m-%d'))
                # 'aw-plg-as-traceid': '09d778aebe8cd44f539322e3b5c556dc6b8cc684b0106e696b8ab2395d7db30890704e72734c732e210ae7e5246d31b6f89',
                # 'aw-plg-as-openid': '',
                # 'aw-plg-as-sessionid': '0843fb76f5dcb8edb576d5f9d9a6e2a8bbaebed7d6a7475eb669e61230d91ec84ef25c584a2',
                # 'aw-plg-as-matrix': '005FE0xMmJ0sUH9rL2rDnE0Q==@005FE0xMmJ0sUH9rL2rDnE0Q==@065FE0xMmJ0sUH9rL2rDnE0Q==@11Wa/KByD7o58RTKZgs8H04A==@16Wa/KByD7o58RTKZgs8H04A==@065FE0xMmJ0sUH9rL2rDnE0Q==@11Wa/KByD7o58RTKZgs8H04A==@16Wa/KByD7o58RTKZgs8H04A==@005FE0xMmJ0sUH9rL2rDnE0Q==@045FE0xMmJ0sUH9rL2rDnE0Q==',
                # 'aw-plg-as-sign': 'a7dfc33cc95c50d5efbefe47ce7154ef15b2afa8',
                # 'aw-plg-as-calctrace': '6689',
            }

        add_day = random.randint(8, 25)
        f_date = (datetime.datetime.now() + datetime.timedelta(days=add_day)).strftime('%Y%m%d')
        f_date_plus = (datetime.datetime.now() + datetime.timedelta(days=add_day+1)).strftime('%Y%m%d')
        now_datetime = datetime.datetime.now().strftime('%Y%m%d%H%M%S')

        upper_random = ''.join([random.choice(string.ascii_uppercase) for i in xrange(6)])
        lower_random = ''.join([random.choice(string.ascii_lowercase) for i in xrange(6)])

        now_date = datetime.datetime.now().strftime('%Y-%m-%d')
        now_format_datetime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # url = 'https://www.ly.com/iflight/flight-book2.re.aspx?unitKey=432_OW_HRB_FMA_{}_null_1_0#{}_PG0866_N/{}_TG0973_G/{}_SN0440_I#0_0#TCPL&traceId=CN{}ZTOA1VDARFC8BSQVP1ZUYC1ZAEV70GYW30FIAP7A4P{}&resourceId=TCPL&pricingSerialNo=CN_THL_GCNTCTH&og=ef16a7259fe643e78ab10761e6{}{}^OW_HRB_FMA_{}_NA_CN_ADT-1|CHD-0|INF-0_Y|S|F|C_V14^PG0866_{}/TG0973_{}/SN0440_{}'.format(f_date, f_date, f_date_plus, f_date_plus, now_datetime, upper_random, lower_random, now_date, f_date, f_date, f_date_plus, f_date_plus)

        traceId = 'TH{}ZTOA1VDARFC8BSQVP1ZUYC1ZAEV70GYW30FIAP7A4P{}'.format(now_datetime, upper_random)
        unitKey = '432_OW_HRB_FMA_{}_null_1_0#{}_PG0866_N/{}_TG0973_G/{}_SN0440_I#0_0#TCPL'.format(f_date, f_date, f_date_plus, f_date_plus)
        unitKey = '258_OW_HKG_SHA_{}_null_1_0#{}_MU8979_X#0_0#TCPL'.format(f_date, f_date)
        unitKey = '432_OW_HRB_FMA_{}_null_1_0#{}_PG0866_N/{}_TG0973_G/{}_SN0440_I#0_0#TCPL'.format(f_date, f_date, f_date_plus, f_date_plus)
        resourceId = 'TCPL'
        pricingSerialNo = 'TH_THL_GTHTCTH'
        unitGuid = 'ef16a7259fe643e78ab10761e6{}{}^OW_HRB_FMA_{}_NA_CN_ADT-1|CHD-0|INF-0_Y|S|F|C_V14^PG0866_{}/TG0973_{}/SN0440_{}'.format(lower_random, now_format_datetime, f_date, f_date, f_date_plus, f_date_plus)
        unitGuid = '73d96b46737c47c19db88a7664{}{}^OW_HKG_SHA_{}_NA_CN_ADT-1|CHD-0|INF-0_Y|S|F|C_V14^MU8979_{}'.format(
            lower_random, now_format_datetime, f_date, f_date
        )
        unitGuid = 'd574816e06ee4319b0f9c3af3a{}{}^OW_HRB_FMA_{}_NA_TH_ADT-1|CHD-0|INF-0_Y|S|F|C_V14^PG0866_{}/TG0973_{}/SN0440_{}'.format(
            lower_random, now_format_datetime, f_date, f_date, f_date_plus, f_date_plus
        )

        # url = 'https://www.ly.com/pciflightapi/json/searchDetail.html'
        # post_data = {
        #     'og': unitGuid,
        #     'tid': 'CN20190119184612VP10S75OX8ZE3KOTCNAT2HV3M540C250452PFBIY8AKXCI30',
        #     'model': 'snap',
        # }
        #
        # result = session.post(url=url, data=post_data, verify=False)
        # print result.content

        # url = 'https://www.ly.com/pciflightapi/json/getSearchDetail.html?unitKey={}&traceId={}&resourceId={}&pricingSerialNo={}&originGuid={}'.format(quote(unitKey), quote(traceId), quote(resourceId), quote(pricingSerialNo), quote(unitGuid))
        url = 'https://m.ly.com/miflightapi/json/getSearchDetail.html?pricingSerialNo={}&productCode=THL&resourceId={}&traceId={}&unitKey={}&originGuid={}'.format(quote(pricingSerialNo), quote(resourceId), quote(traceId), quote(unitKey), quote(unitGuid))
        print url
        result = session.get(url, verify=False, proxies={
            'http': 'http://{}'.format(proxy),
            'https': 'https://{}'.format(proxy),
        })
        print result.content

        time.sleep(2)
        # url = 'https://www.ly.com/pciflightapi/json/validatePrice.html'
        url = 'https://m.ly.com/miflightapi/json/validatePrice.html'
        post_data = {
            'traceId': traceId,
            'unitKey': unitKey,
            'resourceId': resourceId,
            'pricingSerialNo': pricingSerialNo,
            'unitGuid': unitGuid,
            'reqPassengers[0][passengerType]':	1,
            'reqPassengers[0][passengerNum]':	1,
            'reqPassengers[1][passengerType]':	2,
            'reqPassengers[1][passengerNum]':	0,
            'searchCondition[travelType]':	'OW',
            'searchCondition[departureCity]':	'HRB',
            'searchCondition[departureDate]':	(datetime.datetime.now() + datetime.timedelta(days=add_day)).strftime('%Y-%m-%d'),
            'searchCondition[arrivalCity]':	'FMA',
            'searchCondition[returnDate]':	'1900-01-01',
            'searchCondition[adultNum]':	1,
            'searchCondition[childNum]':	0,
            'searchCondition[submitAdultNum]':	1,
            'searchCondition[submitChildNum]':	0,
        }
        print post_data

        result = session.post(url, verify=False, data=post_data, proxies={
            'http': 'http://{}'.format(proxy),
            'https': 'https://{}'.format(proxy),
        })
        print result.content


    def origin_run(self):
        session = requests.Session()
        session.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.80 Safari/{}.36'.format(
                random.randint(100, 999)),
            # 'Refer': 'https://www.ly.com/iflight/flight-book1.aspx?para=0*HRB*FMA*{}**YSCF*1*0*1&advanced=false&orgAirCode=false&desAirCode=false'.format(datetime.datetime.now().strftime('%Y-%m-%d'))
        }

        add_day = random.randint(8, 25)
        f_date = (datetime.datetime.now() + datetime.timedelta(days=add_day)).strftime('%Y%m%d')
        f_date_plus = (datetime.datetime.now() + datetime.timedelta(days=add_day + 1)).strftime('%Y%m%d')
        now_datetime = datetime.datetime.now().strftime('%Y%m%d%H%M%S')

        upper_random = ''.join([random.choice(string.ascii_uppercase) for i in xrange(6)])
        lower_random = ''.join([random.choice(string.ascii_lowercase) for i in xrange(6)])

        now_date = datetime.datetime.now().strftime('%Y-%m-%d')
        now_format_datetime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # url = 'https://www.ly.com/iflight/flight-book2.re.aspx?unitKey=432_OW_HRB_FMA_{}_null_1_0#{}_PG0866_N/{}_TG0973_G/{}_SN0440_I#0_0#TCPL&traceId=CN{}ZTOA1VDARFC8BSQVP1ZUYC1ZAEV70GYW30FIAP7A4P{}&resourceId=TCPL&pricingSerialNo=CN_THL_GCNTCTH&og=ef16a7259fe643e78ab10761e6{}{}^OW_HRB_FMA_{}_NA_CN_ADT-1|CHD-0|INF-0_Y|S|F|C_V14^PG0866_{}/TG0973_{}/SN0440_{}'.format(f_date, f_date, f_date_plus, f_date_plus, now_datetime, upper_random, lower_random, now_date, f_date, f_date, f_date_plus, f_date_plus)

        traceId = 'CN{}ZTOA1VDARFC8BSQVP1ZUYC1ZAEV70GYW30FIAP7A4P{}'.format(now_datetime, upper_random)
        unitKey = '432_OW_HRB_FMA_{}_null_1_0#{}_PG0866_N/{}_TG0973_G/{}_SN0440_I#0_0#TCPL'.format(f_date, f_date,
                                                                                                   f_date_plus, f_date_plus)
        resourceId = 'TCPL'
        pricingSerialNo = 'CN_THL_GCNTCTH'
        unitGuid = 'ef16a7259fe643e78ab10761e6{}{}^OW_HRB_FMA_{}_NA_CN_ADT-1|CHD-0|INF-0_Y|S|F|C_V14^PG0866_{}/TG0973_{}/SN0440_{}'.format(
            lower_random, now_format_datetime, f_date, f_date,
            f_date_plus, f_date_plus)

        url = 'https://www.ly.com/pciflightapi/json/getSearchDetail.html?unitKey={}&traceId={}&resourceId={}&pricingSerialNo={}&originGuid={}'.format(
            quote(unitKey), quote(traceId), quote(resourceId),
            quote(pricingSerialNo), quote(unitGuid))
        print url
        result = session.get(url, verify=False)
        print result.content

        time.sleep(2)
        url = 'https://www.ly.com/pciflightapi/json/validatePrice.html'
        post_data = {
            'traceId': traceId,
            'unitKey': unitKey,
            'resourceId': resourceId,
            'pricingSerialNo': pricingSerialNo,
            'unitGuid': unitGuid,
            'reqPassengers[0][passengerType]': 1,
            'reqPassengers[0][passengerNum]': 1,
            'reqPassengers[1][passengerType]': 2,
            'reqPassengers[1][passengerNum]': 0,
            'searchCondition[travelType]': 1,
            'searchCondition[departureCity]': 'HRB',
            'searchCondition[departureDate]': (datetime.datetime.now() + datetime.timedelta(days=add_day)).strftime(
                '%Y-%m-%d'),
            'searchCondition[returnDate]': '1900-01-01',
            'searchCondition[adultNum]': 1,
            'searchCondition[childNum]': 0,
            'searchCondition[submitAdultNum]': 1,
            'searchCondition[submitChildNum]': 0,
        }

        result = requests.post(url, verify=False, data=post_data)
        print result.content


    def test_run(self):
        session = requests.Session()
        session.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.80 Safari/{}.36'.format(
                random.randint(100, 999)),
            # 'Refer': 'https://www.ly.com/iflight/flight-book1.aspx?para=0*HRB*FMA*{}**YSCF*1*0*1&advanced=false&orgAirCode=false&desAirCode=false'.format(datetime.datetime.now().strftime('%Y-%m-%d'))
            'Referer': 'https://www.ly.com/iflight/flight-book1.aspx?para=0*HKG*SHA*2019-01-30**YSCF*1*0*1&advanced=false&orgAirCode=false&desAirCode=false',
            'aw-plg-as-traceid': '10bf1778a8ac1185930f69bafb894fffa661d95f13150aa88a6d8345df5d852f12a023a740ba00ae590ba16eeb58c5d293d',
            'aw-plg-as-openid': '',
            'aw-plg-as-sessionid': 'c4b4d0251258cf23d13889628ed89750fd4b505b4e024f1a2b3f711c051ac4d538f63cd40b9',
            'aw-plg-as-matrix': '00CFqBxmaHquSio24D6sg86Q==@16JSJPQoDMikIWQYPXb8A+Qg==@16JSJPQoDMikIWQYPXb8A+Qg==@04CFqBxmaHquSio24D6sg86Q==@01CFqBxmaHquSio24D6sg86Q==@14JSJPQoDMikIWQYPXb8A+Qg==@16JSJPQoDMikIWQYPXb8A+Qg==@17JSJPQoDMikIWQYPXb8A+Qg==@02CFqBxmaHquSio24D6sg86Q==@00CFqBxmaHquSio24D6sg86Q==',
            'aw-plg-as-sign': '10c173e3fc20e5036d4a78dbd236e0c2e07b11a3',
            'aw-plg-as-calctrace': '420',
        }

        add_day = random.randint(8, 25)
        f_date = (datetime.datetime.now() + datetime.timedelta(days=add_day)).strftime('%Y%m%d')
        f_date_plus = (datetime.datetime.now() + datetime.timedelta(days=add_day + 1)).strftime('%Y%m%d')
        now_datetime = datetime.datetime.now().strftime('%Y%m%d%H%M%S')

        upper_random = ''.join([random.choice(string.ascii_uppercase) for i in xrange(6)])
        lower_random = ''.join([random.choice(string.ascii_lowercase) for i in xrange(6)])

        now_date = datetime.datetime.now().strftime('%Y-%m-%d')
        now_format_datetime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # url = 'https://www.ly.com/iflight/flight-book2.re.aspx?unitKey=432_OW_HRB_FMA_{}_null_1_0#{}_PG0866_N/{}_TG0973_G/{}_SN0440_I#0_0#TCPL&traceId=CN{}ZTOA1VDARFC8BSQVP1ZUYC1ZAEV70GYW30FIAP7A4P{}&resourceId=TCPL&pricingSerialNo=CN_THL_GCNTCTH&og=ef16a7259fe643e78ab10761e6{}{}^OW_HRB_FMA_{}_NA_CN_ADT-1|CHD-0|INF-0_Y|S|F|C_V14^PG0866_{}/TG0973_{}/SN0440_{}'.format(f_date, f_date, f_date_plus, f_date_plus, now_datetime, upper_random, lower_random, now_date, f_date, f_date, f_date_plus, f_date_plus)

        traceId = 'CN{}ZTOA1VDARFC8BSQVP1ZUYC1ZAEV70GYW30FIAP7A4P{}'.format(now_datetime, upper_random)
        unitKey = '432_OW_HRB_FMA_{}_null_1_0#{}_PG0866_N/{}_TG0973_G/{}_SN0440_I#0_0#TCPL'.format(f_date, f_date,
                                                                                                   f_date_plus, f_date_plus)
        unitKey = '258_OW_HKG_SHA_{}_null_1_0#{}_MU8979_X#0_0#TCPL'.format(f_date, f_date)
        resourceId = 'TCPL'
        pricingSerialNo = 'CN_THL_GCNTCTH'
        unitGuid = 'ef16a7259fe643e78ab10761e6{}{}^OW_HRB_FMA_{}_NA_CN_ADT-1|CHD-0|INF-0_Y|S|F|C_V14^PG0866_{}/TG0973_{}/SN0440_{}'.format(
            lower_random, now_format_datetime, f_date, f_date, f_date_plus, f_date_plus)
        unitGuid = '73d96b46737c47c19db88a7664{}{}^OW_HKG_SHA_{}_NA_CN_ADT-1|CHD-0|INF-0_Y|S|F|C_V14^MU8979_{}'.format(
            lower_random, now_format_datetime, f_date, f_date
        )

        url = 'https://www.ly.com/pciflightapi/json/searchDetail.html'
        post_data = {
            'og': unitGuid,
            'tid': 'CN20190119184612VP10S75OX8ZE3KOTCNAT2HV3M540C250452PFBIY8AKXCI30',
            'model': 'snap',
        }

        result = session.post(url=url, data=post_data, verify=False)
        print result.content

        # url = 'https://www.ly.com/pciflightapi/json/getSearchDetail.html?unitKey={}&traceId={}&resourceId={}&pricingSerialNo={}&originGuid={}'.format(quote(unitKey), quote(traceId), quote(resourceId), quote(pricingSerialNo), quote(unitGuid))
        # print url
        # result = session.get(url, verify=False)
        # print result.content

        time.sleep(2)
        url = 'https://www.ly.com/pciflightapi/json/validatePrice.html'
        post_data = {
            'traceId': traceId,
            'unitKey': unitKey,
            'resourceId': resourceId,
            'pricingSerialNo': pricingSerialNo,
            'unitGuid': unitGuid,
            'reqPassengers[0][passengerType]': 1,
            'reqPassengers[0][passengerNum]': 1,
            'reqPassengers[1][passengerType]': 2,
            'reqPassengers[1][passengerNum]': 0,
            'searchCondition[travelType]': 1,
            'searchCondition[departureCity]': 'HRB',
            'searchCondition[departureDate]': (datetime.datetime.now() + datetime.timedelta(days=add_day)).strftime(
                '%Y-%m-%d'),
            'searchCondition[returnDate]': '1900-01-01',
            'searchCondition[adultNum]': 1,
            'searchCondition[childNum]': 0,
            'searchCondition[submitAdultNum]': 1,
            'searchCondition[submitChildNum]': 0,
        }
        print post_data

        result = requests.post(url, verify=False, data=post_data)
        print result.content


    def en_run(self, proxy):

        # redis_obj = redis.StrictRedis(host='42.159.91.248', port=26371,
        #                               password='ZIDZGPZPYpd6nTk2zCwLni3K1zvd2ChPkztTcO1HsnM=', db=4)
        redis_obj = redis.StrictRedis(host='127.0.0.1',
                                      password='630131222', db=4)

        session_token = redis_obj.rpoplpush('tc_customer_device_session', 'tc_customer_device_session')
        token = json.loads(session_token)
        print token
        if not token:
            print "have no device session"
            return

        session = requests.Session()

        add_day = random.randint(8, 25)
        # add_day = 32
        f_date = (datetime.datetime.now() + datetime.timedelta(days=add_day)).strftime('%Y%m%d')
        f_date_plus = (datetime.datetime.now() + datetime.timedelta(days=add_day + 1)).strftime('%Y%m%d')
        now_datetime = datetime.datetime.now().strftime('%Y%m%d%H%M%S')

        upper_random = ''.join([random.choice(string.ascii_uppercase) for i in xrange(6)])
        lower_random = ''.join([random.choice(string.ascii_lowercase) for i in xrange(6)])

        trace_id = 'GP{}2E8UVWKC2POCKR3WL3ESYKDFFDBA1J4TOPV26MM0RE{}'.format(
            datetime.datetime.now().strftime('%Y%m%d%H%M%S'), upper_random)

        # trace_id = 'GP20190222130959TLUJYSKRDDBX9TTW5GCCTHSV93VRMBN2J6ESGMAN3HEE0W79'

        now_format_datetime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        unitKey = '432_OW_HRB_FMA_{}_null_1_0#{}_PG0866_N/{}_TG0973_G/{}_SN0440_I#0_0#TCPL'.format(f_date, f_date,
                                                                                                   f_date_plus, f_date_plus)
        resourceId = 'TCPL'
        pricingSerialNo = 'GP_THL_GGPTCTH'
        unitGuid = 'd574816e06ee4319b0f9c3af3a{}{}^OW_HRB_FMA_{}_NA_TH_ADT-1|CHD-0|INF-0_Y|S|F|C_V14^PG0866_{}/TG0973_{}/SN0440_{}'.format(
            lower_random, now_format_datetime, f_date, f_date, f_date_plus, f_date_plus
        )


        url = 'https://en.ly.com/pciflightapi/json/reQuery.html?tdleonid=tdleonid'
        post_data = {
            'tt': 0,
            'ac': 'FMA',
            'dc': 'HRB',
            'at': '1900-01-01',
            'dt': (datetime.datetime.now() + datetime.timedelta(days=add_day)).strftime('%Y-%m-%d'),
            'an': 1,
            'cn': 0,
            'cabin': 'Y',
            'tit': 1,
            'lang': 'en',
            'currency': 'USD',
            'tid': trace_id
        }
        headers = {
            'Referer': 'https://en.ly.com/iflight/book1.html?para=0%2aHKG%2aBJS%2a2019-02-22%2a%2aY%2a1%2a0%2a1&orgAirCode=HKG&DesAirCode=BJS',
            'Host': 'en.ly.com',
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Origin': 'https://en.ly.com',
            'X-Requested-With': 'XMLHttpRequest',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36',
            'intl-token': 'pc',
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-GB,en;q=0.9,en-US;q=0.8,zh-CN;q=0.7,zh;q=0.6',
            'Content-Length': '160',
        }

        cookie_dict = {
            # 'td_sid': token['td_sid'],
            # 'td_did': token['td_did'],
            # 'route': token['route'],
            'td_sid': 'MTU1MTA2ODUyNixiNmVhZWU0ZWVjZmI2MWJkYjE5MThlYzYzNDY4NGRiNjM1ZWM3ZmRiNGQzYzBhM2Q0YTRiYWM3YWVhNzcxNWIwLDE1YjNiMmVhODFhOWJiYjExMjQzZTQ3YzA1OGY1MWU4ZTk2MTIyOGVkMWZhMTNkYzFlNzkyMDYzYzI4Y2NkNzg=',
            'td_did': 'T1yVYcXZBs5SiVuiuN3C6piut8YBBwmZjz6p6PFJ9MmkKj2sOHN2FN5ST9d%2FcVd%2Fs5VWftXsGim73GC43wIxhfNcO81uuJG9XaMwRM4xkHpEFDYZWXUGNPyudqByKUlHcwmtMVihS0KLddZ8rk9bYEOobtsDY7p%2FuVO%2BxaNheslN0n7JBwlYc%2BqZ%2BPpDQb6oEHmsvyaXl8xC31TNMcmpXA%3D%3D',
            'route': '3ef354d2100a5dd3396d860ed0492ce4',
        }
        c = requests.cookies.RequestsCookieJar()
        for k, v in cookie_dict.items():
            c.set(k, v)
        session.cookies.update(c)

        # result = session.post(url=url, data=post_data, headers=headers, verify=False, proxies={
        #     'https': 'https://{}'.format(proxy),
        #     'http': 'http://{}'.format(proxy),
        # })
        result = session.post(url=url, data=post_data, headers=headers, verify=False)
        print result.content
        print result.headers
        print session.cookies

        post_data = {
            'traceId': trace_id,
            'unitKey': unitKey,
            'resourceId': resourceId,
            'pricingSerialNo': pricingSerialNo,
            'language': 'en',
            'currency': 'USD',
            # 'unitGuid': unitGuid,
            'reqPassengers[0][passengerType]': 1,
            'reqPassengers[0][passengerNum]': 1,
            'reqPassengers[1][passengerType]': 2,
            'reqPassengers[1][passengerNum]': 0,
            'searchCondition[travelType]': 'OW',
            'searchCondition[departureCity]': 'HRB',
            'searchCondition[departureDate]': (datetime.datetime.now() + datetime.timedelta(days=add_day)).strftime(
                '%Y-%m-%d'),
            'searchCondition[arrivalCity]': 'FMA',
            'searchCondition[returnDate]': '1900-01-01',
            # 'searchCondition[adultNum]': 1,
            # 'searchCondition[childNum]': 0,
            # 'searchCondition[submitAdultNum]': 1,
            # 'searchCondition[submitChildNum]': 0,
        }
        print post_data

        url = 'https://en.ly.com/pciflightapi/json/validatePrice.html'
        # result = session.post(url, verify=False, data=post_data, proxies={
        #     'http': 'http://{}'.format(proxy),
        #     'https': 'https://{}'.format(proxy),
        # })

        result = session.post(url, verify=False, data=post_data)

        print result.content


    def selenium_run(self, proxy_addr):

        try:
            profile = webdriver.FirefoxProfile()
            profile.set_preference('network.proxy.type', 1)
            profile.set_preference('network.proxy.http', proxy_addr.split(':')[0])
            profile.set_preference('network.proxy.http_port', int(proxy_addr.split(':')[1]))
            profile.set_preference("network.proxy.share_proxy_settings", True)
            profile.set_preference('network.proxy.ssl', proxy_addr.split(':')[0])
            profile.set_preference('network.proxy.ssl_port', int(proxy_addr.split(':')[1]))
            profile.update_preferences()

            # from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
            # binary = FirefoxBinary('/usr/bin/firefox')
            from selenium.webdriver import FirefoxOptions
            opts = FirefoxOptions()
            # opts.add_argument("--headless")
            driver = webdriver.Firefox(firefox_profile=profile, firefox_options=opts)

            add_day = random.randint(5, 60)
            print "====== add day:{} ======".format(add_day)
            driver.get('https://en.ly.com/iflight/book1.html?para=0%2aHRB%2aFMA%2a{}%2a%2aY%2a1%2a0%2a1'.format(
                (datetime.datetime.now() + datetime.timedelta(days=add_day)).strftime('%Y-%m-%d')))
            time.sleep(15)
            driver.set_window_size(1200, 800)

            elems = driver.find_elements_by_class_name('if-list-unit-btn')
            print elems
            e = elems[0]
            sub_icon = e.find_elements_by_class_name('icon')
            sub_icon = sub_icon[0]
            sub_icon.click()
            time.sleep(2)

            elems = driver.find_elements_by_class_name('pro-book-btns')
            print elems
            e = elems[0]
            e.click()

            time.sleep(15)
            driver.close()

        except Exception as e:
            import traceback
            print traceback.format_exc()
            try:
                driver.close()  # 强制关闭driver进程，无论任何报错
            except Exception as e:
                pass
            raise

    def run(self):

        while True:

            redis_obj = redis.StrictRedis(host='42.159.91.248', port=26371,
                                          password='ZIDZGPZPYpd6nTk2zCwLni3K1zvd2ChPkztTcO1HsnM=', db=4)
            trigger = redis_obj.rpop('tc_auto_verify_trigger')
            if trigger:
                for times in xrange(32):
                    proxy_list = []
                    result = requests.get(
                        'http://webapi.http.zhimacangku.com/getip?num=2&type=2&pro=0&city=0&yys=0&port=1&pack=33099&ts=1&ys=1&cs=1&lb=1&sb=0&pb=45&mr=1&regions='
                    ).json()

                    for p in result['data']:
                        proxy_addr = '{}:{}'.format(p['ip'], p['port'])
                        proxy_list.append(proxy_addr)

                    print "========= proxy list:{}".format(proxy_list)
                    try:
                        for p in proxy_list:
                            s = time.time()
                            self.selenium_run(p)
                            print int(time.time() - s)
                    except Exception as e:
                        print e

                    time.sleep(10)
            else:
                print "============ sleep to wait trigger ========"
                time.sleep(5)

if __name__ == '__main__':

    # times = 15
    #
    # for i in xrange(times):
    #     run()
    #     time.sleep(10)

    # test_run()

    # switch_time = None
    # proxy_list = []
    # while 1:
    #     if switch_time and (datetime.datetime.now() - switch_time).seconds < 16 * 60:
    #         pass
    #     else:
    #         proxy_list = []
    #         result = requests.get(
    #             # 'http://webapi.http.zhimacangku.com/getip?num=2&type=2&pro=0&city=0&yys=0&port=1&pack=33099&ts=1&ys=1&cs=1&lb=1&sb=0&pb=45&mr=1&regions='
    #             # 'http://mapi.baibianip.com/getproxy?type=dymatic&apikey=5fcfed32d9a420b2cbe592e8f73a9fb5&count=120&unique=1&lb=1&format=json&sort=1&resf=1,2'
    #             # 'http://api.ip.data5u.com/dynamic/get.html?order=0176a3ac3dbfe89f52d290a5f0c3c544&ttl=1&json=1&sep=3'
    #             # 'http://webapi.http.zhimacangku.com/getip?num=2&type=2&pro=0&city=0&yys=0&port=1&pack=30067&ts=1&ys=1&cs=1&lb=1&sb=0&pb=45&mr=1&regions='
    #             'http://webapi.http.zhimacangku.com/getip?num=2&type=2&pro=0&city=0&yys=0&port=1&pack=33099&ts=1&ys=1&cs=1&lb=1&sb=0&pb=45&mr=1&regions='
    #         ).json()
    #
    #         for p in result['data']:
    #             proxy_addr = '{}:{}'.format(p['ip'], p['port'])
    #             proxy_list.append(proxy_addr)
    #
    #         print "========= proxy list:{}".format(proxy_list)
    #         switch_time = datetime.datetime.now()
    #     # proxy_list = ['117.57.37.240:4226']
    #     try:
    #         for p in proxy_list:
    #             s = time.time()
    #             selenium_run(p)
    #             print int(time.time() - s)
    #     except Exception as e:
    #         print e
    #
    #     time.sleep(10)

    while True:

        redis_obj = redis.StrictRedis(host='42.159.91.248', port=26371,
                                      password='ZIDZGPZPYpd6nTk2zCwLni3K1zvd2ChPkztTcO1HsnM=', db=4)
        trigger = redis_obj.rpop('tc_auto_verify_trigger')
        if trigger:
            proxy_list = []
            for times in xrange(32):
                proxy_list = []
                result = requests.get(
                    'http://webapi.http.zhimacangku.com/getip?num=2&type=2&pro=0&city=0&yys=0&port=1&pack=33099&ts=1&ys=1&cs=1&lb=1&sb=0&pb=45&mr=1&regions='
                ).json()

                for p in result['data']:
                    proxy_addr = '{}:{}'.format(p['ip'], p['port'])
                    proxy_list.append(proxy_addr)

                print "========= proxy list:{}".format(proxy_list)
                try:
                    for p in proxy_list:
                        s = time.time()
                        selenium_run(p)
                        print int(time.time() - s)
                except Exception as e:
                    print e

                time.sleep(10)
        else:
            print "============ sleep to wait trigger ========"
            time.sleep(5)
