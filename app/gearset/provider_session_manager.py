#coding=utf8

import traceback
import time
import random
import datetime
import os
import json
from app import TBG
from app.controller.http_request import HttpRequest
from app.controller.captcha import CaptchaCracker
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from ..utils.logger import Logger
from flask_script import Command



class ProviderSessionManager(Command):

    def __init__(self):
        pass
        # self.driver = webdriver.Chrome()
        # self.driver = webdriver.PhantomJS()
        # self.driver.set_window_size(800, 600)

    def check_browser_errors(self,driver):
        """
        Checks browser for errors, returns a list of errors
        :param driver:
        :return:
        """
        try:
            browserlogs = driver.get_log('browser')
        except Exception as e:

            print 'error'
        print browserlogs
        errors = []
        for entry in browserlogs:
            if entry['level'] == 'SEVERE':
                errors.append(entry)
        return errors

    def airasia(self):
        """

        :return:
        """
        self.p_c = "%s_%s" % ('airasia','airasia_web')
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        capa = DesiredCapabilities.CHROME
        capa["pageLoadStrategy"] = "none"
        driver = webdriver.Chrome(desired_capabilities=capa,chrome_options=chrome_options)
        wait = WebDriverWait(driver, 5)
        # driver.get('https://booking.airasia.com/')
        driver.get('https://booking.airasia.com/Flight/Select?o1=PVG&d1=SIN&dd1=2019-04-22&ADT=1&CHD=0&inl=0&s=false&mon=true&cc=CNY')
        time.sleep(3)
        driver.execute_script("window.stop();")
        driver.get('https://booking.airasia.com/Flight/Select?o1=PVG&d1=SIN&dd1=2019-04-22&ADT=1&CHD=0&inl=0&s=false&mon=true&cc=CNY')
        cookies = driver.get_cookies()
        # cookies = [{u'domain': u'.airasia.com', u'name': u'rxvt', u'value': u'1544517719152|1544515916792', u'path': u'/', u'httpOnly': False, u'secure': False},
        #            {u'domain': u'booking.airasia.com', u'name': u'dotrez', u'value': u'1343415306.20480.0000', u'path': u'/', u'httpOnly': True, u'secure': True},
        #            {u'domain': u'.airasia.com', u'name': u'dtSa', u'value': u'-', u'path': u'/', u'httpOnly': False, u'secure': False},
        #            {u'domain': u'.airasia.com', u'name': u'dtLatC', u'value': u'1', u'path': u'/', u'httpOnly': False, u'secure': False},
        #            {u'domain': u'.airasia.com', u'secure': False, u'value': u'1544515916788M7P9O680I47INAJ58R8LT7133PJMS3NM', u'expiry': 1607674316, u'path': u'/', u'httpOnly': False,
        #             u'name': u'rxVisitor'},
        #            {u'domain': u'.airasia.com', u'name': u'dtCookie', u'value': u'3$9405678E175D6AD5B862AE5B11438800', u'path': u'/', u'httpOnly': False, u'secure': False},
        #            {u'domain': u'.airasia.com', u'name': u'appID', u'value': u'W001', u'path': u'/', u'httpOnly': False, u'secure': False},
        #            {u'domain': u'.airasia.com', u'name': u'dtPC', u'value': u'3$115916779_569h2vIBEBDGNUABCVHIJBONHHQMDNIAFGMMFB', u'path': u'/', u'httpOnly': False, u'secure': False},
        #            {u'domain': u'.airasia.com', u'secure': False,
        #             u'value': u'c2hsMVhjS2RMNEkxbW9nemExdD18Yk1iQXZybWhpdWljcTVrZlo1eWExR2o0bG5NS3dkNjI2Nmw1eXp3cW5zZGZ5WjYxZTh1TGV6c1dZT2xSaTROWjBCZDk5MDAyQkNGaU1yWWhacTN4NFdrR2I5dXl4SXptaWNUaU1MbENaNW9pTVVDSk4rN21pOE1OdlVVYUIwd1JySXFNb3ZQaWhXMGFFaHBUWEhMSGlOYWRCMWlwNU1iVWFWQT0=',
        #             u'expiry': 1544519516.648625, u'path': u'/', u'httpOnly': False, u'name': u'dotRezSignature'},
        #            {u'domain': u'.airasia.com', u'secure': False, u'value': u'cc=en-GB&mcc=MYR&rc=WWWA&ad=dsnqwzy5t1azgom15qciuihm&p=&st=1544515916.48448', u'expiry': 1544519516.648857, u'path': u'/',
        #             u'httpOnly': False, u'name': u'userSession'},
        #            {u'domain': u'booking.airasia.com', u'name': u'ASP.NET_SessionId', u'value': u'dsnqwzy5t1azgom15qciuihm', u'path': u'/', u'httpOnly': True, u'secure': False},
        #            {u'domain': u'booking.airasia.com', u'secure': False, u'value': u'5c0f714a78b27d2258f021c0a1fc015a49c11672', u'expiry': 1544519516.184396, u'path': u'/', u'httpOnly': False,
        #             u'name': u'acw_sc_v3'}, {u'domain': u'booking.airasia.com', u'name': u'__RequestVerificationToken',
        #                                      u'value': u'IVQTXw95xa_Jon8FJt-HT17LImVwhp3weNMBpq3WA_Qp1zDkm77GVpTjq8Sy7IvlGIpbkPImmvavkMftEqbHPufSlJNOCMKunyBE-JprBIi7xS6bBpwk_D-btTiCpnUxZQKszw2',
        #                                      u'path': u'/',
        #                                      u'httpOnly': True, u'secure': False},
        #            {u'domain': u'booking.airasia.com', u'secure': False, u'value': u'6fce042315445159143547064e63bbb68cf1f1579a9a897ec96b169e9a', u'expiry': 1544517714.401975, u'path': u'/',
        #             u'httpOnly': True,
        #             u'name': u'acw_tc'}]
        acw_sc_v3 = None
        acw_tc = None
        __RequestVerificationToken = None
        dotrez = None

        for cookie in cookies:
            if cookie['name'] == 'acw_sc_v3':
                acw_sc_v3 = cookie['value']
            if cookie['name'] == 'acw_tc':
                acw_tc = cookie['value']
            if cookie['name'] == 'dotrez':
                dotrez = cookie['value']
            if cookie['name'] == '__RequestVerificationToken':
                __RequestVerificationToken = cookie['value']
        # driver.close()
        if acw_sc_v3 and acw_tc:
            sd = [{'session_type':'header','name':'acw_sc_v3','value':acw_sc_v3},{'session_type':'header','name':'acw_tc','value':acw_tc},
                  {'session_type': 'header', 'name': '__RequestVerificationToken', 'value': __RequestVerificationToken},{'session_type':'header','name':'dotrez','value':dotrez}]
            Logger().sdebug('session_data %s' % sd)
            TBG.cache_access_object.insert(cache_type='extra_session', provider=self.p_c,
                                       param_model={}, ret_data=sd)
        else:
            raise Exception('no acw cookie')

    def tc_customer(self):

        from selenium import webdriver

        while True:
            try:
                driver = webdriver.Chrome()
                driver.get('https://www.ly.com/iflight/flight-book1.aspx?para=0*SHA*OSA*2019-02-03**YSCF*1*1*1')
                time.sleep(10)
                # driver.execute_script("window.stop();")
                cookies = driver.get_cookies()

                route = ''
                td_did = ''
                td_sid = ''
                for c in cookies:
                    if c['name'] == 'route':
                        route = c['value']
                    if c['name'] == 'td_did':
                        td_did = c['value']
                    if c['name'] == 'td_sid':
                        td_sid = c['value']

                print "===== route: {}".format(route)
                print "======== td_did: {}".format(td_did)
                print "======== td_sid: {}".format(td_sid)

                if route and td_did and td_sid:
                    device_info = {
                        'route': route,
                        'td_did': td_did,
                        'td_sid': td_sid,
                        'create_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    }
                    TBG.redis_conn.redis_pool.lpush('tc_customer_device_session', json.dumps(device_info))
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

        # TODO  以后增加供应商需要修改此代码
        while 1:
            try:
                s = time.time()
                self.airasia()
                # self.tc_customer()
                print int(time.time()-s)
            except Exception as e:
                Logger().error(e)

            time.sleep(30)




if  __name__ == "__main__":

    pass
