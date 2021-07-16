# coding=utf8

import time,json
import os
import base64
from app import TBG
from ..utils.logger import Logger
from ..utils.util import Time
from flask_script import Command


class QcodeInvalidError(Exception):
    """
    二维码失效
    """
    pass

class NoBalanceError(Exception):
    """
    余额不足
    """
    pass

class AlreadyPayError(Exception):
    """
    重复支付
    """
    pass

class AlipayQcode(Command):

    def __init__(self):
        pass

    def login(self):
        """
        登陆支付宝
        :return:
        """

    def check_login(self):
        """
        检查登陆状态
        :return:
        """

    def payment(self,trade_data):
        """
        真实支付
        :return:
        """
        Logger().info('alipay_qcode start payment ')

        import qrcode
        from appium import webdriver

        data_dir = TBG.global_config['DATA_DIR']
        qcode_file = "%s.png" % Time.time_str_3()
        qcode_path = os.path.join(data_dir,qcode_file)
        Logger().info('save path %s'% qcode_path)
        qcode_url = trade_data.get('qcode_url')
        img = qrcode.make(qcode_url)
        img.save(qcode_path)

        # 启动appium实例
        """
        An unknown server-side error occurred while processing the command. Original error: UIAutomation2 is only supported since Android 5.0 (Lollipop). 
        You could still use other supported backends in order to automate older Android versions.
        {
            "platformName": "Android",
            "platformVersion": "4.4.4",
            "deviceName": "Android Emulator",
            "appPackage": "com.eg.android.AlipayGphone",
            "appActivity": "com.eg.android.AlipayGphone.AlipayLogin",
            "noReset": true
        }
        {
  "platformName": "Android",
  "platformVersion": "4.4.4",
  "deviceName": "Android Emulator",
  "appPackage": "com.eg.android.AlipayGphone",
  "appActivity": "com.eg.android.AlipayGphone.AlipayLogin",
  "noReset": true,
  "automationName": "Selendroid"
}
{
  "platformName": "Android",
  "platformVersion": "4.4.4",
  "deviceName": "Android Emulator",
  "app":"/Users/xiaotian/workplace/android/ceair.apk",
  "noReset": true,
  "automationName": "Selendroid"
}
        """
        desired_caps = {
            "platformName": "Android",
            "platformVersion": "4.4.4",
            "deviceName": "Android Emulator",
            "appPackage": "com.eg.android.AlipayGphone",
            "appActivity": "com.eg.android.AlipayGphone.AlipayLogin",
            "noReset": True
        }
        Logger().info('desired_caps %s' % desired_caps)
        wd = webdriver.Remote(TBG.global_config['EMULATOR_APPIUM_ADDR'], desired_caps)
        wd.implicitly_wait(5)
        Logger().info(wd.contexts)
        #
        # width = wd.get_window_size()['width']
        # height = wd.get_window_size()['height']
        # print width
        # print height
        Logger().info('start find')

        # 上传图片
        wd.push_file(destination_path='/sdcard/DCIM/Camera/%s'% qcode_file, source_path=qcode_path)
        Logger().info('picture transfered')

        # 选取照片
        scan_btn_id = 'com.alipay.android.phone.openplatform:id/saoyisao_iv'
        wd.find_element_by_id(scan_btn_id).click()
        Logger().info("saoyisao clicked")

        time.sleep(2)
        album_id = 'com.alipay.mobile.scan:id/title_bar_album'
        wd.find_element_by_id(album_id).click()
        Logger().info("album clicked")

        time.sleep(2)
        # TODO 图库没有图片的情况
        wd.find_element_by_xpath(
            "/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.RelativeLayout/android.widget.GridView/android.widget.RelativeLayout[1]").click()
        Logger().info("pic selected")

        #是否出现错误
        time.sleep(4)
        err_msg = ''
        try:
            err_obj = wd.find_element_by_id('com.alipay.mobile.antui:id/message')
            if err_obj:
                err_msg = err_obj.text
        except Exception as e:
            pass
        if err_msg:
            Logger().warn('Error %s'% err_msg)
            wd.close_app()
            raise QcodeInvalidError(err_msg)
        else:

            wd.tap([(379, 1209)])
            Logger().info("pay btn clicked")

            time.sleep(2)
            """
            输入密码 1 adb shell input tap 136 909
    
            输入密码 5 adb shell input tap 345 1019
    
            输入密码 2 adb shell input tap 357 909
    
            输入密码 4 adb shell input tap 126 1014
    
            输入密码 7 adb shell input tap 134 1115
    
            输入密码 8 adb shell input tap 352 1115
            """

            wd.tap([(136, 909)])
            time.sleep(0.2)

            wd.tap([(345, 1019)])
            time.sleep(0.2)

            wd.tap([(357, 909)])
            time.sleep(0.2)

            wd.tap([(126, 1014)])
            time.sleep(0.2)

            wd.tap([(134, 1115)])
            time.sleep(0.2)

            wd.tap([(352, 1115)])
            Logger().info("pwd list btn clicked")

            try:
                if wd.find_element_by_xpath('//android.widget.TextView[contains(@text, "转账")]'):
                    Logger().info('pay success')
                    return 'NO_TRADE_NO'  # 暂时不提供交易流水号
            except Exception as e:
                raise

            try:
                if wd.find_element_by_xpath('//android.widget.TextView[contains(@text, "选择付款方式")]'):
                    Logger().warn('pay channel error')
                    raise NoBalanceError
            except Exception as e:
                raise




        # # 获取流水号
        #
        # # 点击我的
        # time.sleep(4)
        # wd.tap([(639, 1218)])
        #
        # time.sleep(4)
        # Logger().info(wd.contexts)
        # # 点击账单
        # wd.tap([(398, 447)])
        #
        # time.sleep(8)
        # Logger().info(wd.contexts)
        # # 点击第一个账单
        # wd.tap([(436, 539)])
        #
        # time.sleep(8)
        # Logger().info(wd.contexts)
        #
        # 获取截图数据
        # png_data = wd.get_screenshot_as_png()
        # return

        # ALIPAY 登陆相关
        # login_btn_id = 'com.eg.android.AlipayGphone:id/loginButton'
        # login_btn_xpath = '/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.RelativeLayout/android.widget.RelativeLayout[2]/android.widget.RelativeLayout/android.widget.RelativeLayout/android.widget.LinearLayout/android.widget.LinearLayout/android.widget.RelativeLayout[2]/android.widget.Button'
        #
        # login_input_id = 'com.ali.user.mobile.security.ui:id/content'
        # login_input_xpath = '/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.ScrollView/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.RelativeLayout/android.widget.EditText'
        #
        # login_submit_id = 'com.ali.user.mobile.security.ui:id/nextButton'
        # login_submit_xpath = '/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.ScrollView/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.LinearLayout/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.LinearLayout'
        #
        # login_password_input_id = 'com.ali.user.mobile.security.ui:id/switchLoginMethodCenter'
        # '/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.ScrollView/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.LinearLayout/android.widget.LinearLayout[2]/android.widget.TextView'
        #
        # password_input_id = '/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.ScrollView/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.LinearLayout/android.widget.LinearLayout[1]/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.EditText'
        #
        # last_con = 'com.ali.user.mobile.security.ui:id/loginButton'
        # last_con = '/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.ScrollView/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.LinearLayout/android.widget.LinearLayout[1]/android.widget.LinearLayout/android.widget.Button'


    # def run(self):
    #     qcode_url = 'https://qr.alipay.com/upx01604nwq4zafmegk64047'
    #     self.payment({'qcode_url': qcode_url})

    def run(self):

        redis_pool = TBG.redis_conn.get_internal_pool()

        while True:
            try:
                Logger().info('start loop')
                payment_task = redis_pool.brpop('alipay_qcode_queue', 2*60)
                if payment_task:
                    payment_task = json.loads(payment_task[1])
                    trade_id = payment_task.get('trade_id')
                    trade_data = payment_task.get('trade_data')
                    Logger().sinfo("alipay_qcode start to payment %s " % trade_id)

                    try:
                        trade_no =   self.payment(trade_data)
                        redis_pool.set('alipay_qcode_result_{}'.format(trade_id), json.dumps({'result': 'SUCCESS', 'trade_no':trade_no}))
                    except QcodeInvalidError as e:
                        Logger().info('QcodeInvalidError')
                        redis_pool.set('alipay_qcode_result_{}'.format(trade_id), json.dumps({'result': 'QcodeInvalidError','msg':str(e)}))
                    except NoBalanceError as e:
                        Logger().info('NoBalanceError')
                        redis_pool.set('alipay_qcode_result_{}'.format(trade_id), json.dumps({'result': 'NoBalanceError'}))
                    except Exception as e:
                        Logger().error('Exception')
                        redis_pool.set('alipay_qcode_result_{}'.format(trade_id), json.dumps({'result': 'UnknwonErrorr'}))
            except KeyboardInterrupt:
                break
            except Exception as e:
                time.sleep(3)
                Logger().serror(e)


if __name__ == "__main__":
    aq = AlipayQcode()

