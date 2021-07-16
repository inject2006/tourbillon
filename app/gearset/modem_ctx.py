#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'wxt'

import time,logging,re,serial,Queue
from threading import Event
from gsmmodem.serial_comms import  SerialComms
from gsmmodem.modem import GsmModem

logging.basicConfig(format='%(asctime)s :%(levelname)s: %(message)s', level=logging.INFO)
logger = logging.getLogger('modem')


def run_in_thread(func,*args,**kwargs):
    from threading import Thread
    thread = Thread(target=func,args=args,kwargs=kwargs)
    thread.daemon = True
    thread.start()
    return thread



class ModemPoolScaner(object):
    def __init__(self):
        self.result_q = Queue.Queue()
    def start(self,):
        """
        查找所有连接的COM口modem并自动匹配速率
        @return 格式 [(com1,9600),()]
        """
        available = [] 
        available_port = []
        for i in xrange(1,256):
            try:
                logger.debug("start detect %s",'COM{}'.format(i))
                modem = SerialComms(port='COM{}'.format(i),baudrate=9600)
                modem.connect() 
                modem.close()
                available_port.append( 'COM{}'.format(i))
            except Exception,e:
                if modem.alive:
                    modem.close()
            
        threads = []
        for port in available_port:
            threads.append(run_in_thread(self.detecter,port=port))
        for t in threads:
            t.join()
        qsize = self.result_q.qsize()
        for x in xrange(qsize):
            available.append(self.result_q.get())
        return available
    
    def detecter(self,port):
        BAUDRATES = [
             9600,115200]
        for ba in BAUDRATES:
            try:
                logger.debug("start detect %s,%s",port,ba)
                modem = SerialComms(port=port,baudrate=ba,)
                modem.connect() 
                a = modem.write('AT+CPAS\r',timeout=3) #初始化
                if 'OK' in a:
                    logger.debug("available %s,%s",port,ba)
                    self.result_q.put( (port,ba))
                    modem.close()
                    break
                
                modem.close()
            except Exception,e:
                logger.debug("unavailable %s,%s",port,ba)
                if modem.alive:
                    modem.close()  



class ModemSingalError(Exception):
    """modem error"""
    def __init__(self, *args):
        Exception.__init__(self)

class ModemSmsSendError(Exception):
    """modem error"""
    def __init__(self, *args):
        Exception.__init__(self)
        
class Mobile(object):
    def __init__(self,port,baudrate,connect_threshold=12,hander_sms_recv=None,reconnect=False):
        """
        @param port: com 端口
        @param baudrate: com 波特率
        @param connect_threshold: 检测拨号的等待时长
        @param hander_sms_recv:  短信接收回调函数
        @param reconnect: 是否重启modem进行连接
        """
        try:
            logger.info('Init %s,%s',port,baudrate)
            self.hander_sms_recv = hander_sms_recv 
            self.modem = GsmModem(port=port,baudrate=baudrate,incomingCallCallbackFunc=self.handler_call_hangup,smsReceivedCallbackFunc=self._hander_sms_recv,custom_handler_callback=self.notify_callback)
            self.modem.connect(reconnect=reconnect)         
            self.event = Event()
            self.dial_retstatus = 0  # 0 不可用 1 可用  2 未知  3 错误
            self.dial_status = 0 # 0 无命令状态  1  拨号状态  2 拨号完成
            self.connect_threshold = connect_threshold #接通阈值 秒
        except Exception,e:
            logger.exception('Init Error port:%s,baudrate:%s',port,baudrate)
            raise
        

        
    def handler_call_hangup(self,call):
        logger.debug("hangup_call")
        call.hangup()
        
    def _hander_sms_recv(self,sms):
        if self.hander_sms_recv:
            self.hander_sms_recv(self.modem.port,self.modem.imsi,sms)
        
        
    def close(self):
        if self.modem.alive:
            self.modem.close()
    def notify_callback(self,regexMatch):
        
        #来电
        if regexMatch:
            line = regexMatch.group()
            print line
            if line in [ '+WIND: 2','+WIND: 9']: # 莫名其名从 2 变成了 9
                self.modem.write('ATH')
                logger.debug("Connect")
                curr_time = time.time()
                if curr_time - self.dial_starttime < 5:
                    self.dial_retstatus = 0
                else:
                    self.dial_retstatus = 1
                self.dial_status = 2
                self.event.set()
            elif line == 'NO CARRIER':
                logger.debug("NO CARRIER")
                #self.modem.write('AT+CEER')
                self.dial_status = 2
                curr_time = time.time()
                if curr_time - self.dial_starttime < 5:
                    self.dial_retstatus = 2
                else:
                    self.dial_retstatus = 0
                self.event.set()
            elif line == 'BUSY':
                logger.debug("BUSY")
                self.dial_retstatus = 0
                self.dial_status = 2
                self.event.set()  
            else:
                logger.info("no match hangup")
                self.modem.write('ATH')
            
    def error_callback(self,e):
        logger.error('ErrorCallback')
    
    def callStatusUpdateCallbackFunc(self,call):
        call.hangup()
        logger.debug('callStatusUpdateCallbackFunc')

        
    def call_status_detect(self,mobile):
        """
        @param mobile: 电话号码
        @return 0 不可用 1 可用  2 未知  3 错误
        """
        try:

            logger.info('Dial:%s',mobile)
            self.event.clear()
            self.dial_retstatus = 0
            self.dial_status = 1
            
            reconnect_count = 0
            while 1:
                
                reconnect_count +=1
                if reconnect_count > 3:
                    self.modem.connect(reconnect=True)
                    logger.warn('modem reconnect,please wait 30 sec')
                try:
                    signal = self.modem.waitForNetworkCoverage(20)
                    if signal > 0:
                        break
                    else:
                        logger.error('no_signal retry....')
                        continue
                except Exception,e:
                    logger.exception('no_signal retry....')
                    time.sleep(5)
                    continue
                
            reconnect_count = 0
            self.dial_starttime = time.time()
            self.modem.dial(mobile,timeout=5)#拨打电话
            
            self.event.wait(self.connect_threshold)
            self.modem.write('ATH')
            #call.hangup() 
            #self.modem.write('AT+CEER')

            self.dial_endtime = time.time()
            logger.debug('dailing duration time %s',round(self.dial_endtime - self.dial_starttime,2))


                            
 
        except Exception,e:
            logger.exception('Dial Error mobile:%s',mobile)
            raise
            #self.dial_retstatus = 3
        logger.debug('dial_retstatus %s',self.dial_retstatus )
        return self.dial_retstatus 
    
    def __del__(self):
        try:
            self.modem.close()
        except Exception,e:
            pass
            
        


if __name__ == '__main__':
    PORT = 'COM64'
    BAUDRATE = 9600
    
    #sms = u'\u60a8\u597d\uff01\u60a808\u6708\u4efd\u5df2\u6d88\u8d390.60\u5143,\u6700\u65b0\u4f59\u989d\u4e3a9.90\u5143\u3002\u70b9\u51fbhe.10086.cn/cz99 \u5355\u7b14\u5145\u503c100\u5143\u53ca\u4ee5\u4e0a\u5373\u4eab99\u6298\uff01\u4e2d\u56fd\u79fb\u52a8'
    #import re
    #exp = re.compile(u'最新余额为(.*?)元')
    #exp_i =exp.findall(sms)
    #if exp_i:
        #balance = exp_i[0]

    try:
        modem = SerialComms(port='COM21', baudrate=9600, )
        modem.connect()
        a = modem.write('AT+CPAS\r', timeout=3)  # 初始化
        modem.close()
    except Exception, e:
        import traceback
        traceback.print_exc()

    # modem = SerialComms(port='COM41', baudrate=115200, )
    # modem.connect()
    # a = modem.write('AT+CPAS\r', timeout=3)  # 初始化
    # modem.close()
    # modem = SerialComms(port='COM41', baudrate=115200, )
    # modem.connect()
    # a = modem.write('AT+CPAS\r', timeout=3)  # 初始化
    # modem.close()
    #
    # print "start"
    # try:
    #     #b = ModemPoolScaner()
    #     #print b.start()
    #     a = Mobile(port=PORT,baudrate=BAUDRATE,reconnect=False)
    #     #a.query_balance()
    #     #print a.modem.imsi
    #     #print a.modem.imei
    #     #print a.modem.networkName
    #
    #     #print a.modem.write('AT+EGMR',timeout=1000)
    #     #print a.modem.imei
    #     #print a.modem.write('AT+CMGR=1')
    #
    #     #print a.modem.write('AT+CMGL=ALL')
    #     #while 1:
    #         #time.sleep(5)
    #     #a.modem.write("ATE0")
    #     while 1:
    #         print a.call_status_detect('13632552945')
    # except Exception,e:
    #     try:
    #         a.modem.serial.close()
    #     except Exception,e:
    #         print "serial close"
    #     print "1 err"
    # try:
    #     a = Mobile(port=PORT,baudrate=BAUDRATE)
    #     #a.modem.write("AT+SMSO")
    #     a.modem.write("ATE0")
    #     #a.call_status_detect('15216666047')
    #     a.modem.serial.close()
    # except Exception,e:
    #     try:
    #         a.modem.serial.close()
    #     except Exception,e:
    #         print "serial close"
    #     print "1 err"
    #
    # time.sleep(1)
    # print "end"


    #threads = []
    ##scaner = ModemPoolScaner().start()
    ##time.sleep(1)

    #threads.append(run_in_thread(th))
    #while 1:
        #print "loop"
        #for k,v in enumerate(threads):

            #if not v.is_alive():
                #threads[k] = run_in_thread(th)
        #time.sleep(5)

    #a.query_balance()
    ##time.sleep(100)
    #print a.call_status_detect('15216666047')
    #print a.dial('13222890491') #呼叫失败号码
    #print a.dial('13482121020')# lw号码

    



    
