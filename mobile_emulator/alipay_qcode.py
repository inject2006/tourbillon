#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, too-many-arguments, broad-except, anomalous-backslash-in-string
# pylint: disable=missing-docstring, line-too-long, too-few-public-methods
"""
# @Author  : wxt
# @Software: PyCharm
"""

import time
from appium import webdriver

{
  "platformName": "Android",
  "platformVersion": "4.4.4",
  "deviceName": "Android Emulator",
  "appPackage": "com.eg.android.AlipayGphone",
  "appActivity": "com.eg.android.AlipayGphone.AlipayLogin",
  "noReset":True
}
def run():

    desired_caps = {
      "platformName": "Android",
      "platformVersion": "4.4.4",
      "deviceName": "Android Emulator",
      "appPackage": "com.eg.android.AlipayGphone",
      "appActivity": "com.eg.android.AlipayGphone.AlipayLogin",
        "noReset":True
    }
    import json
    print json.dumps(desired_caps)
    wd = webdriver.Remote('http://192.168.1.11:4723/wd/hub', desired_caps)
    wd.implicitly_wait(10)
    #
    width = wd.get_window_size()['width']
    height = wd.get_window_size()['height']
    print width
    print height


    # ALIPAY
    login_btn_id = 'com.eg.android.AlipayGphone:id/loginButton'
    login_btn_xpath = '/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.RelativeLayout/android.widget.RelativeLayout[2]/android.widget.RelativeLayout/android.widget.RelativeLayout/android.widget.LinearLayout/android.widget.LinearLayout/android.widget.RelativeLayout[2]/android.widget.Button'

    login_input_id = 'com.ali.user.mobile.security.ui:id/content'
    login_input_xpath = '/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.ScrollView/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.RelativeLayout/android.widget.EditText'

    login_submit_id = 'com.ali.user.mobile.security.ui:id/nextButton'
    login_submit_xpath = '/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.ScrollView/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.LinearLayout/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.LinearLayout'

    login_password_input_id = 'com.ali.user.mobile.security.ui:id/switchLoginMethodCenter'
    '/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.ScrollView/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.LinearLayout/android.widget.LinearLayout[2]/android.widget.TextView'

    password_input_id = '/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.ScrollView/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.LinearLayout/android.widget.LinearLayout[1]/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.EditText'


    last_con = 'com.ali.user.mobile.security.ui:id/loginButton'
    last_con = '/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.ScrollView/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.LinearLayout/android.widget.LinearLayout[1]/android.widget.LinearLayout/android.widget.Button'

    # 上传图片
    wd.push_file(destination_path='/sdcard/DCIM/Camera/a.png', source_path='a.png')
    print "picture transfered"
    # 选取照片
    scan_btn_id = 'com.alipay.android.phone.openplatform:id/saoyisao_iv'
    wd.find_element_by_id(scan_btn_id).click()
    print "saoyisao clicked"
    time.sleep(3)
    print "start album clicked"
    album_id = 'com.alipay.mobile.scan:id/titleBar_album'
    wd.find_element_by_id(album_id).click()
    print "album clicked"
    time.sleep(3)
    # TODO 图库没有图片的情况
    wd.find_element_by_xpath("/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.RelativeLayout/android.widget.GridView/android.widget.RelativeLayout[1]").click()
    print "album clicked"
    time.sleep(5)
    wd.tap([(379,1209)])
    print "pay btn clicked"

    time.sleep(3)
    """
    输入密码 1 adb shell input tap 136 909
    
    输入密码 5 adb shell input tap 345 1019

    输入密码 2 adb shell input tap 357 909
    
    输入密码 4 adb shell input tap 126 1014
    
    输入密码 7 adb shell input tap 134 1115
    
    输入密码 8 adb shell input tap 352 1115
    """
    print "pwd 1"
    wd.tap([(136,909)])
    time.sleep(0.2)
    print "pwd 5"
    wd.tap([(345, 1019)])
    time.sleep(0.2)
    print "pwd 2"
    wd.tap([(357, 909)])
    time.sleep(0.2)
    print "pwd 4"
    wd.tap([(126, 1014)])
    time.sleep(0.2)
    print "pwd 7"
    wd.tap([(134, 1115)])
    time.sleep(0.2)
    print "pwd 8"
    wd.tap([(352, 1115)])







    # AIRASIA
    # desired_caps = {}
    # desired_caps['platformName'] = 'Android'
    # desired_caps['platformVersion'] = '7.1'
    # desired_caps['deviceName'] = 'Android Emulator'
    # desired_caps['app'] = 'http://dl001.liqucn.com/upload/2015/shenghuo/com.airasia.mobile_5.0.5_liqucn.com.apk'
    # desired_caps['noReset'] = False
    # desired_caps["unicodeKeyboard"] = True
    # desired_caps["resetKeyboard"] = True
    # import json
    # print json.dumps(desired_caps)
    # wd = webdriver.Remote('http://127.0.0.1:4723/wd/hub', desired_caps)
    # wd.implicitly_wait(60)
    # #
    # width = wd.get_window_size()['width']
    # height = wd.get_window_size()['height']
    # print width
    # print height

    # start_search_btn = wd.find_element_by_android_uiautomator('(//android.widget.ImageView[@content-desc="Image Description"])[4]')
    # depart_btn = wd.find_element_by_android_uiautomator('/hierarchy/android.widget.FrameLayout/android.support.v4.widget.DrawerLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.ViewGroup/android.widget.FrameLayout[2]/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.FrameLayout/android.widget.RelativeLayout/android.widget.LinearLayout/android.widget.LinearLayout[1]/android.widget.Button[1]')
    # depart_select_input = wd.find_element_by_android_uiautomator('/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.ViewGroup/android.widget.FrameLayout[2]/android.widget.LinearLayout/android.widget.LinearLayout/android.widget.EditText')
    # depart_select_first = wd.find_element_by_android_uiautomator('/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.ViewGroup/android.widget.FrameLayout[2]/android.widget.LinearLayout/android.widget.ScrollView/android.widget.LinearLayout/android.widget.ListView/android.widget.RelativeLayout/android.widget.LinearLayout')
    # arrive_select_input = wd.find_element_by_android_uiautomator('/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.ViewGroup/android.widget.FrameLayout[2]/android.widget.LinearLayout/android.widget.LinearLayout/android.widget.EditText')
    # arrive_select_first = wd.find_element_by_android_uiautomator('/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.ViewGroup/android.widget.FrameLayout[2]/android.widget.LinearLayout/android.widget.ScrollView/android.widget.LinearLayout/android.widget.ListView/android.widget.RelativeLayout/android.widget.LinearLayout/android.widget.TextView')
    # flight_date_input = wd.find_element_by_android_uiautomator('/hierarchy/android.widget.FrameLayout/android.support.v4.widget.DrawerLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.ViewGroup/android.widget.FrameLayout[2]/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.FrameLayout/android.widget.RelativeLayout/android.widget.LinearLayout/android.widget.LinearLayout[2]/android.widget.TextView')
    # flight_date_number = wd.find_element_by_android_uiautomator('/hierarchy/android.widget.FrameLayout/android.support.v4.widget.DrawerLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.ViewGroup/android.widget.FrameLayout[2]/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.LinearLayout[2]/android.widget.ListView/android.widget.RelativeLayout[1]/android.widget.LinearLayout/android.widget.TableLayout/android.widget.TableRow[6]/android.widget.RelativeLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.Button')
    # OW_btn = wd.find_element_by_android_uiautomator('/hierarchy/android.widget.FrameLayout/android.support.v4.widget.DrawerLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.ViewGroup/android.widget.FrameLayout[2]/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.LinearLayout[2]/android.widget.Button')
    # adult_num = wd.find_element_by_android_uiautomator('/hierarchy/android.widget.FrameLayout/android.support.v4.widget.DrawerLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.ViewGroup/android.widget.FrameLayout[2]/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.FrameLayout/android.widget.RelativeLayout/android.widget.LinearLayout/android.widget.LinearLayout[3]/android.widget.TextView[2]')
    # adult_num_select = wd.find_element_by_android_uiautomator('/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/android.support.v7.widget.LinearLayoutCompat/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.LinearLayout[1]/android.widget.NumberPicker/android.widget.EditText')
    # child_num = wd.find_element_by_android_uiautomator('/hierarchy/android.widget.FrameLayout/android.support.v4.widget.DrawerLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.ViewGroup/android.widget.FrameLayout[2]/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.FrameLayout/android.widget.RelativeLayout/android.widget.LinearLayout/android.widget.LinearLayout[3]/android.widget.TextView[4]')
    # search_btn = wd.find_element_by_android_uiautomator('/hierarchy/android.widget.FrameLayout/android.support.v4.widget.DrawerLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.ViewGroup/android.widget.FrameLayout[2]/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.FrameLayout/android.widget.RelativeLayout/android.widget.Button')
    #
    # first_routing_list_elem = wd.find_element_by_android_uiautomator('/hierarchy/android.widget.FrameLayout/android.support.v4.widget.DrawerLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.ViewGroup/android.widget.FrameLayout[2]/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.RelativeLayout[4]/android.support.v4.view.ViewPager/android.widget.LinearLayout/android.widget.ListView/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.LinearLayout[1]/android.widget.LinearLayout[2]')
    #
    # first_routing_elem = wd.find_element_by_android_uiautomator('/hierarchy/android.widget.FrameLayout/android.support.v4.widget.DrawerLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.ViewGroup/android.widget.FrameLayout[2]/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.RelativeLayout[4]/android.support.v4.view.ViewPager/android.widget.LinearLayout/android.widget.ListView/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.LinearLayout[3]/android.widget.LinearLayout[1]/android.widget.RelativeLayout[2]/android.widget.TextView')
    #
    # member_input = wd.find_element_by_android_uiautomator('/hierarchy/android.widget.FrameLayout/android.support.v4.widget.DrawerLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.ViewGroup/android.widget.FrameLayout[2]/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.FrameLayout/android.widget.RelativeLayout/android.widget.ScrollView/android.widget.LinearLayout/android.widget.LinearLayout[2]/android.widget.LinearLayout/android.widget.LinearLayout[2]/android.widget.LinearLayout[2]/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.EditText')
    # family_name_input = wd.find_element_by_android_uiautomator('/hierarchy/android.widget.FrameLayout/android.support.v4.widget.DrawerLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.ViewGroup/android.widget.FrameLayout[2]/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.FrameLayout/android.widget.RelativeLayout/android.widget.ScrollView/android.widget.LinearLayout/android.widget.LinearLayout[2]/android.widget.LinearLayout/android.widget.LinearLayout[2]/android.widget.LinearLayout[3]/android.widget.LinearLayout/android.widget.EditText')
    # personal_name_input = wd.find_element_by_android_uiautomator('/hierarchy/android.widget.FrameLayout/android.support.v4.widget.DrawerLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.ViewGroup/android.widget.FrameLayout[2]/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.FrameLayout/android.widget.RelativeLayout/android.widget.ScrollView/android.widget.LinearLayout/android.widget.LinearLayout[2]/android.widget.LinearLayout/android.widget.LinearLayout[2]/android.widget.LinearLayout[4]/android.widget.LinearLayout/android.widget.EditText')
    # birthdate_select = wd.find_element_by_android_uiautomator('/hierarchy/android.widget.FrameLayout/android.support.v4.widget.DrawerLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.ViewGroup/android.widget.FrameLayout[2]/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.FrameLayout/android.widget.RelativeLayout/android.widget.ScrollView/android.widget.LinearLayout/android.widget.LinearLayout[2]/android.widget.LinearLayout/android.widget.LinearLayout[2]/android.widget.LinearLayout[5]/android.widget.LinearLayout/android.widget.RelativeLayout')
    #
    # contact_family_name_input = wd.find_element_by_android_uiautomator('/hierarchy/android.widget.FrameLayout/android.support.v4.widget.DrawerLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.ViewGroup/android.widget.FrameLayout[2]/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.FrameLayout/android.widget.RelativeLayout/android.widget.ScrollView/android.widget.LinearLayout/android.widget.LinearLayout[3]/android.widget.LinearLayout/android.widget.LinearLayout[2]/android.widget.LinearLayout[1]/android.widget.LinearLayout/android.widget.EditText')
    # contact_personal_name_input = wd.find_element_by_android_uiautomator('/hierarchy/android.widget.FrameLayout/android.support.v4.widget.DrawerLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.ViewGroup/android.widget.FrameLayout[2]/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.FrameLayout/android.widget.RelativeLayout/android.widget.ScrollView/android.widget.LinearLayout/android.widget.LinearLayout[3]/android.widget.LinearLayout/android.widget.LinearLayout[2]/android.widget.LinearLayout[2]/android.widget.LinearLayout/android.widget.EditText')
    # phone_prefix = wd.find_element_by_android_uiautomator('/hierarchy/android.widget.FrameLayout/android.support.v4.widget.DrawerLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.ViewGroup/android.widget.FrameLayout[2]/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.FrameLayout/android.widget.RelativeLayout/android.widget.ScrollView/android.widget.LinearLayout/android.widget.LinearLayout[3]/android.widget.LinearLayout/android.widget.LinearLayout[2]/android.widget.LinearLayout[3]/android.widget.LinearLayout[1]/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.Button')
    # phone_prefix_search = wd.find_element_by_android_uiautomator('/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.ViewGroup/android.widget.FrameLayout[2]/android.widget.LinearLayout/android.widget.LinearLayout/android.widget.EditText')
    # china_phone_prefix = wd.find_element_by_android_uiautomator('/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.ViewGroup/android.widget.FrameLayout[2]/android.widget.LinearLayout/android.widget.ScrollView/android.widget.LinearLayout/android.widget.ListView/android.widget.RelativeLayout[6]/android.widget.LinearLayout')
    #
    # # passenger_save_btn = wd.find_element_by_android_uiautomator('/hierarchy/android.widget.FrameLayout/android.support.v4.widget.DrawerLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.ViewGroup/android.widget.FrameLayout[2]/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.LinearLayout/android.widget.LinearLayout/android.widget.Button')
    # passenger_save_btn = wd.find_element_by_android_uiautomator('/hierarchy/android.widget.FrameLayout/android.support.v4.widget.DrawerLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.ViewGroup/android.widget.FrameLayout[2]/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.LinearLayout/android.widget.LinearLayout/android.widget.Button')
    # payment_btn = wd.find_element_by_android_uiautomator('/hierarchy/android.widget.FrameLayout/android.support.v4.widget.DrawerLayout/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/android.view.ViewGroup/android.widget.FrameLayout[2]/android.widget.LinearLayout/android.widget.RelativeLayout/android.widget.FrameLayout/android.widget.RelativeLayout/android.widget.LinearLayout/android.widget.Button')



if __name__ == '__main__':

    run()
