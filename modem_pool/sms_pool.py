#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
猫池检测服务
"""

__author__ = 'wxt'

import time, re
import requests
from modem_ctx import ModemPoolScaner, Mobile
import logging

logging.basicConfig(format='%(asctime)s :%(levelname)s: %(message)s', level=logging.INFO)
logger = logging.getLogger('modem')
SMS_RECIEVER_URL = 'http://misc.tourbillon.qisec.cn:9801/misc/sms_reciever'


global_config = {'SMS_RECIEVER_URL':'http://misc.tourbillon.qisec.cn:9801/misc/sms_reciever',
                 'SMS_HEARTBEAT_URL':'http://misc.tourbillon.qisec.cn:9801/misc/sms_heartbeat'}

def run_in_thread(func,*args,**kwargs):
    from threading import Thread
    thread = Thread(target=func,args=args,kwargs=kwargs)
    thread.daemon = True
    thread.start()
    return thread

class Controller(object):
    CMCC_BALANCE_EXP = re.compile(u'最新余额为(.*?)元')
    CUGSM_BALANCE_EXP = re.compile(u'您的账户当前可用余额(.*?)元')

    def __init__(self):
        logger.info('Controller Init....')

        available_modems = ModemPoolScaner().start()  # 检测COM和速率
        # available_modems = [('COM32',115200)]
        logger.info('available_modems %s,count:%s', available_modems, len(available_modems))
        if len(available_modems) == 0:
            logger.error('available_modems == 0')
            raise Exception
        for port, baudrate in available_modems:  # 生成线程
            run_in_thread(self.modem_worker, port=port, baudrate=baudrate)

        run_in_thread(self.heartbeat)
        while 1:
            time.sleep(1)

    def heartbeat(self):
        """
        发送心跳
        :return:
        """

        while 1:
            try:
                logger.info('send heartbeat')
                requests.get(url=TBG.global_config['SMS_HEARTBEAT_URL'], params={'device_id': 'modem_pool1'})
                time.sleep(60)
            except Exception as e:
                logger.error('heartbeat error')

    def hander_sms_recv(self, port, imsi, sms):
        logger.info(
            u'== SMS message received ==\nFrom: {0}\nTime: {1}\nImsi:{2}\nMessage:\n{3}\n'.format(sms.number, sms.time, imsi, sms.text))

        # ?from_mobile=+86311332112&to_mobile=15216666555&message=123&receive_time=1367723813

        params = {'from_mobile': sms.number,
                  'device_id': imsi,
                  'receive_time': int(time.time()),
                  'message': sms.text,
                  'send_time': sms.time,
                  }

        for x in range(0, 3):
            result = requests.get(url=TBG.global_config['SMS_RECIEVER_URL'], params=params).content
            if result == 'ok':
                # 返回成功
                logger.info('post success %s' % params)
                break
            else:
                logger.info('post fail %s' % params)
                # # imsi对应电话号码
                # mobile = self.modem_sim_card_dao.get_mobile_via_imsi(imsi=imsi)


                # if sms.number in ['10010', '10086']:
                #     # 识别10086查询话费短信
                #     if sms.number == '10010':
                #         match_group = self.CUGSM_BALANCE_EXP.findall(sms.text)
                #     elif sms.number == '10086':
                #         match_group = self.CMCC_BALANCE_EXP.findall(sms.text)
                #
                #     if match_group:
                #         balance = float(match_group[0])
                #         # 余额更新
                #         self.modem_sim_card_dao.update(mobile=mobile,
                #                                        obj={"balance": balance, "update_timestamp": curr_timestamp()})
                #         # metric 发送话费记录
                #         logger.debug('mobile_charge_mobile:%s,balance:%s', mobile, balance)
                #
                #         # 欠费标记
                #         if balance < 1:
                #             recharge = 1
                #         else:
                #             recharge = 0
                #         self.metric_monitor.advenced_write(name="mobile_charge",
                #                                            obj={"mobile": mobile, "balance": balance, "recharge": recharge})

    def modem_worker(self, port, baudrate):
        logger.info('Modem %s:%s Thread Start', port, baudrate)
        first_init = 0
        init_error_count = 0
        while 1:
            try:

                if first_init == 0:
                    md = Mobile(port=port, baudrate=baudrate, hander_sms_recv=self.hander_sms_recv)

                else:
                    logger.info('restart modem %s', port)
                    if md.modem.alive:
                        md = Mobile(port=port, baudrate=baudrate, hander_sms_recv=self.hander_sms_recv, reconnect=True)
                    else:
                        md = Mobile(port=port, baudrate=baudrate, hander_sms_recv=self.hander_sms_recv)
                while 1:
                    time.sleep(0.2)
            except Exception as e:
                time.sleep(5)
                logger.error('Modem %s:%s Thread Connect Error reconnect...', port, baudrate)
                try:
                    time.sleep(3)
                    md.modem.serial.close()
                except Exception as e:
                    pass
                init_error_count += 1
                if init_error_count > 5:
                    break


        logger.warn('Modem %s:%s Thread Stop', port, baudrate)


if __name__ == '__main__':
    Controller()
