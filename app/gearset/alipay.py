#coding=utf8

import traceback
import time
import random
import datetime
import os
from app import TBG
from app.controller.http_request import HttpRequest
from app.controller.captcha import CaptchaCracker
from ..utils.logger import Logger
from flask_script import Command



class Alipay(Command):

    def __init__(self):
        pass
        # self.driver = webdriver.Chrome()
        # self.driver = webdriver.PhantomJS()
        # self.driver.set_window_size(800, 600)

    def login(self):

        try:
            self.driver.get(self.alipay_login_url)
            self.driver.find_element_by_id('logonId').click()
            time.sleep(1)
            self.driver.find_element_by_xpath('//input[@id="logonId"]').click()
            self.driver.find_element_by_xpath('//input[@id="logonId"]').clear()
            for i in self.alipay_account:
                time.sleep(random.random())
                self.driver.find_element_by_xpath('//input[@id="logonId"]').send_keys(i)

            time.sleep(1)
            self.driver.find_element_by_xpath('//input[@id="password_rsainput"]').click()
            self.driver.find_element_by_xpath('//input[@id="password_rsainput"]').clear()
            for i in self.alipay_password:
                time.sleep(random.random())
                self.driver.find_element_by_xpath('//input[@id="password_rsainput"]').send_keys(i)

            # check code
            have_check_code = False
            check_elem = None
            try:
                check_elem = self.driver.find_element_by_xpath('//img[@id="checkCodeImg"]').click()
                have_check_code = True
            except:
                print traceback.format_exc()

            if have_check_code and check_elem:
                check_code_src = self.driver.find_element_by_xpath('//img[@id="checkCodeImg"]').get_attribute('src')
                # print "================== src ====================="
                # print check_code_src
                http_session = HttpRequest()
                result = http_session.request(
                    url=check_code_src, method='GET',
                    stream=True, is_direct=True).content
                # print "================== content ============"
                # print result
                cracker = CaptchaCracker.select('Fateadm')
                captcha_code = cracker.crack(result)
                if not captcha_code:
                    raise Exception('cannot get check code ')

                self.driver.find_element_by_xpath('//input[@id="authcode"]').click()
                self.driver.find_element_by_xpath('//input[@id="authcode"]').clear()
                for i in captcha_code:
                    time.sleep(random.random())
                    self.driver.find_element_by_xpath('//input[@id="authcode"]').send_keys(i)

            time.sleep(2)
            self.driver.find_element_by_xpath('//span[@id="btn-submit"]').click()

            time.sleep(3)
            try:
                self.driver.find_element_by_xpath('//input[@id="logonId"]').click()
                Logger().serror("alipay login failed")
                return False, "failed"
            except:
                Logger().sinfo("alipay login success")
                return True, "success"
        except:
            Logger().serror("alipay login failed")
            Logger().sdebug(traceback.format_exc())
            time.sleep(3)
            return False, traceback.format_exc()

    def check_login(self):
        try:
            self.driver.find_element_by_xpath('//input[@id="logonId"]').click()
            return False
        except:
            return True


    def set_payment_template(self, tmpl):

        try:
            f =  open(self.local_payment_html, 'w+')
            f.write(tmpl)
            f.close()
            return True
        except Exception as e:
            Logger().serror("alipay set local template failed")
            return False

    def payment(self):

        time.sleep(3)

        try:
            for i in xrange(3):
                try:
                    self.driver.get('file://{}'.format(self.local_payment_html))
                    self.driver.set_window_size(800, 600)
                    time.sleep(2)
                    self.driver.find_element_by_xpath('//a[@class="manage-item manage-more fn-left"]').click()
                    time.sleep(2.5)
                    self.driver.find_element_by_xpath('//span[@class="channel-tit channel-icon icon banklogo-BALANCE_s"]').click()
                    time.sleep(3)
                    self.driver.find_element_by_xpath('//input[@id="payPassword_rsainput"]').click()
                    break
                except:
                    Logger().serror("============ cannot get pay password input ========")

            for i in self.alipay_payment_password:
                time.sleep(random.random())
                self.driver.find_element_by_xpath('//input[@id="payPassword_rsainput"]').send_keys(i)
            time.sleep(2)
            self.driver.find_element_by_xpath('//input[@id="J_authSubmit"]').click()
            for i in xrange(10):
                time.sleep(6)
                if 'cashiersu18.alipay.com' not in self.driver.current_url:
                    Logger().sinfo("alipay payment success")
                    return True, "success"
                else:
                    Logger().sinfo("waiting alipay payment result. current url:{}".format(self.driver.current_url))
            return False, 'final payment failed'
        except:
            if self.check_login():
                Logger().serror("alipay payment failed")
                return False, traceback.format_exc()
            else:
                Logger().serror('first time payment failed. ready to retry payment')
                return False, 'login'

    def retry_payment(self):

        success, msg = self.login()
        if success:
            success, msg = self.payment()
            return success, msg
        else:
            Logger().serror('retry payment failed')
            return False, 'retry payment failed'


    def run(self):
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        self.alipay_account = 'yiyou180@126.com'
        self.alipay_password = 'yiyou806'
        self.alipay_payment_password = 'yiyou608'
        # self.alipay_account = 'nbyd1689@163.com'
        # self.alipay_password = 'yida9632'
        # self.alipay_payment_password = 'yida963'
        self.alipay_login_url = 'https://auth.alipay.com/login/user.htm'
        self.local_payment_html = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                               'alipay_payment.html')

        self.login_retry_times = 3

        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')

        self.driver = webdriver.Chrome(chrome_options=chrome_options)
        last_login_time = datetime.datetime.now()
        login_success = False
        redis_pool = TBG.redis_conn.get_internal_pool()

        while True:
            try:
                if not login_success or (datetime.datetime.now() - last_login_time).seconds > 5*60:
                    for t in xrange(self.login_retry_times):
                        success, msg = self.login()
                        if success:
                            login_success = True
                            last_login_time = datetime.datetime.now()
                            break
                        else:
                            login_success = False
                            time.sleep(2)

                if login_success:
                    payment_task = redis_pool.brpop('payment_task_queue', 2*60)
                    if not payment_task or not isinstance(payment_task, tuple) or not payment_task[
                        0] == 'payment_task_queue' \
                            or not len(payment_task) > 1:
                        continue
                    payment_task = eval(payment_task[1])
                    trade_id = payment_task.get('trade_id')
                    tmpl = payment_task.get('data')
                    Logger().sinfo("alipay start to payment")

                    set_tmpl_success = self.set_payment_template(tmpl)
                    if not trade_id or not tmpl or not set_tmpl_success:
                        redis_pool.set('payment_task_result_{}'.format(trade_id),
                                       {'result': 'error', 'msg': 'set alipay tmpl form error'})

                    success, msg = self.payment()
                    if success:
                        redis_pool.set('payment_task_result_{}'.format(trade_id), {'result': 'ok', 'msg': 'success'})
                    elif msg == 'login':
                        # 支付时登录session失效，重试一次登录支付，支付仍然失败返回
                        Logger().sinfo("alipay login session expire when payment. start to retry login!")
                        success, msg = self.retry_payment()
                        if success:
                            redis_pool.set('payment_task_result_{}'.format(trade_id),
                                           {'result': 'ok', 'msg': 'success'})
                        else:
                            redis_pool.set('payment_task_result_{}'.format(trade_id), {'result': 'error', 'msg': msg})
                    else:
                        redis_pool.set('payment_task_result_{}'.format(trade_id), {'result': 'error', 'msg': msg})
            except KeyboardInterrupt:
                break
            except Exception as e:
                time.sleep(3)
                Logger().serror(e)


if  __name__ == "__main__":

    pass
