#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, too-many-arguments, broad-except, anomalous-backslash-in-string
# pylint: disable=missing-docstring, line-too-long, too-few-public-methods
"""
# @Author  : wxt
# @Software: PyCharm
执行订单状态监测任务
完成支付、票号回填等功能
"""

import time
import gevent
import signal
import logging
from pony.orm import *
from ..ota_repo.base import OTARepo
from ..automatic_repo import ProviderAutoRepo
from flask_script import Manager,Command,Option
from ..dao.models import *
from ..dao.internal import *
from ..utils.logger import Logger,logger_config
from ..utils.util import md5_hash,convert_unicode,Random
from app import TBG
from .base import GearSetBase
from apscheduler.schedulers.blocking import BlockingScheduler
# from apscheduler.schedulers.gevent import GeventScheduler


class OrderController(GearSetBase):
    """
    查询订单并根据状态发配任务
    """

    option_list = (
        Option('--task_exec', '-e', dest='task_exec'),
    )

    def __init__(self):
        self.scheduler = BlockingScheduler()

    def order_poll(self,ota_name):
        """
        轮询订单
        :return:
        """
        try:
            try:
                Logger().sdebug('order_poll Start')
                exception = ''
                start_time = Time.timestamp_ms()
                TB_REQUEST_ID = Random.gen_request_id()
                TB_OTA_NAME = ota_name
                ota_app = OTARepo.select(ota_name)
                ota_app.work_flow = 'order_by_poll'
                reason = ota_app.is_open_time()
                if reason == 'OPEN':
                    ota_app.order_by_poll(request_id=TB_REQUEST_ID)
                else:
                    Logger().sdebug(reason)
                task_result = 'SUCCESS'

            except Exception as e:
                Logger().serror(e)
                exception = str(e)
                task_result = 'ERROR'


            total_latency = Time.timestamp_ms() - start_time

            TBG.tb_metrics.write(
                "ORDER.MANAGER",
                tags=dict(
                    task='ORDER_POLL',
                    task_result=task_result,
                    exception=exception

                ),
                fields=dict(
                    total_latency=total_latency,
                    count=1
                ))
        except Exception as e:
            pass


    def run(self,task_exec):
        #查询

        if task_exec == 'order_poll_faker':
            Logger().sinfo('Runing %s right now' % task_exec)
            self.order_poll('order_poll_faker')
            Logger().sinfo('Task End %s' % task_exec)
        elif task_exec == 'order_poll_tc_policy_wt':
            Logger().sinfo('Runing %s right now' % task_exec)
            self.order_poll('tc_policy_wt')
            Logger().sinfo('Task End %s' % task_exec)
        elif task_exec == 'order_poll_tc_policy_nb':
            Logger().sinfo('Runing %s right now' % task_exec)
            self.order_poll('tc_policy_nb')
            Logger().sinfo('Task End %s' % task_exec)
        else:
            if TBG.global_config['RUN_MODE'] == 'TEST':
                # 测试环境拉取faker ota
                # self.scheduler.add_job(self.order_poll, 'interval', seconds=35,args=('order_poll_faker',))
                self.scheduler.add_job(self.order_poll, 'interval', seconds=10,args=('tc_policy_nb',))
            else:
                # self.scheduler.add_job(self.order_poll, 'interval', seconds=10, args=('tc_policy_wt',))
                self.scheduler.add_job(self.order_poll, 'interval', seconds=30, args=('tc_policy_nb',))
            self.scheduler.add_job(self.order_main, 'interval', seconds=8)
            g = self.scheduler.start()
            try:
                g.join()
            except (KeyboardInterrupt, SystemExit):
                pass

    def order_main(self):
        # TODO 暂时注释
        run_count =0
        providers_status_list = [
            'ALL_SUCCESS',
            'ORDER_INIT',
            'BACKFILL_SUCCESS',
            'PART_FAIL'
        ]
        provider_order_status_list = [
            'BOOK_SUCCESS_AND_WAITING_PAY',
            'PAY_SUCCESS',
            'ORDER_INIT',
            'SET_AUTOPAY'
        ]
        ota_order_status_list = [
            'ORDER_INIT',
            'READY_TO_ISSUE',
        ]


        exception = ''
        start_time = Time.timestamp_ms()
        try:
            #  TODO 简单调度系统实现
            TB_REQUEST_ID = Random.gen_request_id()
            # OTA接口请求因为有限制，所以一分钟执行n次READY_TO_ISSUE请求，n次ISSUE_FINISH请求
            Logger().sdebug('Order Controller Loop Start')
            run_count +=1


            # TODO 是否需要增加时间范围限制
            with db_session:
                # OTA 侧
                order_list = select(o for o in FlightOrder if ( o.ota_order_status in ota_order_status_list and o.providers_status in providers_status_list and o.ota_type == 'API')  )
                Logger().sdebug('todo order list length %s' % len(order_list))

                # group by ota
                to_process_list = []
                ota_group = {}
                for o in order_list:
                    if (Time.curr_date_obj() - o.update_time).days >= 3:
                        # 超时标记
                        Logger().sinfo('order set timeout flag')
                        o.process_duration = (o.update_time - o.ota_create_order_time).seconds  # 计算执行时长
                        o.ota_order_status = 'TIMEOUT'
                        o.update_time=o.update_time
                        Logger().sdebug('flght_task expired %s' % o.id)
                    else:
                        Logger().sdebug('dispatch flight_order_task %s' % o.id)
                        dedup_hash = str(o.id)
                        TBG.tb_publisher.send(body={'ota_name': o.ota_name, 'flight_order_id': o.id}, routing_key='flight_order_task', dedup_hash=dedup_hash)

                        # flight_order_run_task.apply_async(
                        #     kwargs={'func': 'flight_order_task', 'ota_name': o.ota_name, 'flight_order_id': o.id})
                        to_process_list.append(o.id)
                        if o.ota_type == 'API':
                            ota_app = OTARepo.select(o.ota_name)
                            if ota_app.order_detail_process_mode == 'polling':
                                if o.ota_name not in ota_group:
                                    ota_group[o.ota_name] = []
                                    ota_group[o.ota_name].append(o)
                                else:
                                    ota_group[o.ota_name].append(o)
                Logger().sinfo('flight_order_task list %s' % to_process_list)
                Logger().sdebug('ota_group %s'%ota_group)

                for ota_name,olist in ota_group.iteritems():
                    TB_OTA_NAME = ota_name
                    if run_count % 6 == 1: # 6
                        # 检查READY_TO_ISSUE的状态

                        prepare_update_status_list = []
                        for o in olist:
                            Logger().sdebug('ota_order_status %s' % o.ota_order_status)
                            if  o.ota_order_status == 'ORDER_INIT' :
                                prepare_update_status_list.append({'flight_order_id':o.id,'assoc_order_id':o.assoc_order_id,'ota_order_status':o.ota_order_status,'ota_pay_price':o.ota_pay_price})
                        if prepare_update_status_list:
                            Logger().sdebug('Check  READY_TO_ISSUE process %s'%prepare_update_status_list)
                            dedup_hash = 'check_ota_order_status_task_READY_TO_ISSUE_%s' % ota_name
                            TBG.tb_publisher.send(body={'ota_name': ota_name,  'prepare_update_status_list': prepare_update_status_list,'ota_order_status':'READY_TO_ISSUE'}, routing_key='check_ota_order_status_task', dedup_hash=dedup_hash)
                            # flight_order_run_task.apply_async(kwargs={'func': 'check_ota_order_status_task', 'ota_name': ota_name,  'prepare_update_status_list': prepare_update_status_list,'ota_order_status':'READY_TO_ISSUE'})
                    if run_count % 10 == 1: # 10
                        # 检查ISSUE_FINISH的状态

                        prepare_update_status_list = []
                        for o in olist :
                            if  o.ota_order_status == 'READY_TO_ISSUE' :
                                prepare_update_status_list.append({'flight_order_id':o.id,'assoc_order_id':o.assoc_order_id,'ota_order_status':o.ota_order_status,})
                        if prepare_update_status_list:
                            Logger().sdebug('Check ISSUE_FINISH process %s'% prepare_update_status_list)
                            dedup_hash = 'check_ota_order_status_task_ISSUE_FINISH_%s' % ota_name
                            TBG.tb_publisher.send(body={'ota_name': ota_name,'prepare_update_status_list': prepare_update_status_list,'ota_order_status':'ISSUE_FINISH'}, routing_key='check_ota_order_status_task', dedup_hash=dedup_hash)
                            # flight_order_run_task.apply_async(kwargs={'func': 'check_ota_order_status_task', 'ota_name': ota_name,'prepare_update_status_list': prepare_update_status_list,'ota_order_status':'ISSUE_FINISH'})
                    TB_OTA_NAME = ''



                # provider 侧
                order_list = select(o for o in SubOrder if  o.provider_order_status in provider_order_status_list and o.flight_order.ota_order_status in ota_order_status_list )

                # 处理供应商事务
                to_process_list = []
                for o in order_list:

                    TB_OTA_NAME = o.flight_order.ota_name
                    TB_PROVIDER_CHANNEL = o.provider_channel
                    TB_SUB_ORDER_ID = o.id
                    TB_ORDER_ID = o.flight_order.id
                    ota_name = o.flight_order.ota_name
                    provider = o.provider
                    provider_channel = o.provider_channel
                    # 航司下单不支付 provider_order_id  provider_order_status provider_price

                    if (Time.curr_date_obj() - o.update_time).days >= 3 and o.provider_order_status in ['ORDER_INIT']:
                        # 超时标记
                        Logger().sinfo('order set timeout flag')
                        o.process_duration = (o.update_time - o.create_time).seconds  # 计算执行时长
                        o.provider_order_status = 'TIMEOUT'
                        o.update_time = o.update_time
                        Logger().sdebug('sub_order_process_task expired %s'% o.id)
                    else:

                        dedup_hash = str(o.id)
                        # my_lock = TBG.redis_conn.redis_pool.get(task_id)
                        # if my_lock:
                        #     Logger().sdebug('sub_order_process_task executing... bypass')
                        #     continue
                        Logger().sdebug('sub_order_process_task send')
                        to_process_list.append(TB_SUB_ORDER_ID)
                        TBG.tb_publisher.send(body={'ota_name': ota_name, 'provider_channel':provider_channel,'sub_order_id': o.id,'flight_order_id':o.flight_order.id},
                                              routing_key='sub_order_task', dedup_hash=dedup_hash)

                        # sub_order_run_task.apply_async(kwargs={'func': func, 'ota_name': ota_name, 'provider': provider, 'provider_channel':provider_channel,'sub_order_id': o.id,'flight_order_id':o.flight_order.id})
                        TB_OTA_NAME = ''
                        TB_PROVIDER_CHANNEL = ''
                        TB_SUB_ORDER_ID = ''
                        TB_ORDER_ID = ''
                Logger().sinfo('sub_order_process_task list %s'% to_process_list)
                Logger().sdebug('Order Controller Loop End')
                task_result = 'SUCCESS'
        except Exception as e:
            Logger().serror(e)
            exception = str(e)
            task_result = 'ERROR'

        total_latency = Time.timestamp_ms() - start_time

        TBG.tb_metrics.write(
            "ORDER.MANAGER",
            tags=dict(
                task='CONTORLLER',
                task_result=task_result,
                exception=exception

            ),
            fields=dict(
                total_latency=total_latency,
                count=1
            ))


# -------------------TASKSET------------------------------


@logger_config('SUB_ORDER_TASK')
def sub_order_task(body):
    """
    订单处理子程序，覆盖订单的整个声明周期
    :param ota_name:
    :param provider:
    :param flight_order_id:
    :return:
    """
    ota_name = body['ota_name']
    provider_channel = body['provider_channel']
    flight_order_id = body['flight_order_id']
    sub_order_id = body['sub_order_id']
    transaction_start_time = Time.timestamp_s()


    # def sigint_handler(signum, stack):
    #     global need_stop
    #     need_stop  =  True
    #     print 'need_stop:', signum
    #
    # # 注册信号处理程序
    # signal.signal(signal.SIGINT, sigint_handler)
    # signal.signal(signal.SIGHUP, sigint_handler)
    # signal.signal(signal.SIGTERM, sigint_handler)
    TB_ORDER_ID = flight_order_id

    TB_OTA_NAME = ota_name
    TB_SUB_ORDER_ID = sub_order_id
    TB_PROVIDER_CHANNEL = provider_channel
    try:

        TB_REQUEST_ID = Random.gen_request_id()

        is_processed = False
        Logger().sdebug('loop start')
        with db_session:
            # 将数据load到对象中
            sub_order = SubOrder[sub_order_id]
            provider_app = ProviderAutoRepo.select(provider_channel)

            # 如果30分钟无法处理这个订单，则归结为超时，不包含失败情况
            if Time.timestamp_s() - transaction_start_time > 30 * 60:
                Logger().swarn(' timeout')
                sub_order.provider_order_status = 'TIMEOUT'
                return

            order_info_input = sub_order.to_dict(with_collections=True,related_objects=True)
            order_info_input['extra_data'] = sub_order.extra_data

            paxs = []
            contacts =[]
            for p in order_info_input['passengers']:
                pp = p.person.to_dict()
                pax_info = PaxInfo(**pp)
                pax_info.ticket_no = p.ticket_no
                pax_info.used_card_no = p.used_card_no
                pax_info.modified_card_no = p.modified_card_no
                pax_info.used_card_type = p.used_card_type

                pax_info.passenger_id = p.passenger_id
                pax_info.person_id = p.person.id
                pax_info.p2fo_id = p.id
                pax_info.pnr = p.pnr
                paxs.append(pax_info)

            for c in order_info_input['contacts']:
                pp = c.to_dict()
                contact_info = ContactInfo(**pp)
                contacts.append(contact_info)
            order_info_input['passengers'] = paxs
            order_info_input['contacts'] = contacts

            order_info_input['is_modified_card_no'] = 0
            if order_info_input['ffp_account'] and order_info_input['ffp_account'].username and order_info_input['ffp_account'].password:

                ffp_account = order_info_input['ffp_account'].to_dict(with_collections=True,related_objects=True)
                ffp_account.pop('reg_person')
                ffp_account.pop('flight_orders')
                order_info_input['ffp_account'] = FFPAccountInfo(**ffp_account)
                if ffp_account['is_modified_card_no']:
                    order_info_input['is_modified_card_no'] = 1
            else:
                order_info_input['ffp_account'] = None

            # 梳理routing 和 segments
            routing = order_info_input['routing'].to_dict(with_collections=True,related_objects=True)
            from_segments = []
            for f in routing['from_segments']:
                ff = f.to_dict()
                fsi = FlightSegmentInfo(**ff)
                from_segments.append(fsi)

            ret_segments = []
            for f in routing['ret_segments']:
                ff = f.to_dict()
                fsi = FlightSegmentInfo(**ff)
                ret_segments.append(fsi)
            routing['from_segments'] = from_segments
            routing['ret_segments'] = ret_segments
            order_info_input['routing'] = FlightRoutingInfo(**routing)
            sub_order_id = order_info_input.pop('id')
            order_info = SubOrderInfo(**order_info_input)
            order_info.flight_order_id = flight_order_id
            order_info.sub_order_id = sub_order_id
            order_info.ota_name = ota_name
            order_info.ota_work_flow = 'order'

            Logger().sinfo('order_info.provider_order_status %s '%order_info.provider_order_status)
            Logger().sinfo('sub_order.flight_order.ota_order_status %s' % sub_order.flight_order.ota_order_status)
            Logger().sinfo('order_info.is_modified_card_no %s' % order_info.is_modified_card_no)

            if (Time.curr_date_obj() - sub_order.update_time).days  >= 3 and sub_order.provider_order_status in ['ORDER_INIT']:
                # 超时标记
                Logger().sinfo('order set timeout flag')
                sub_order.process_duration = (sub_order.update_time - sub_order.create_time).seconds  # 计算执行时长
                sub_order.provider_order_status = 'TIMEOUT'
                sub_order.update_time = sub_order.update_time
                commit()
                flush()
            else:
                if order_info.provider_order_status in ['ORDER_INIT']:
                    # 下单
                    is_processed = True
                    try:
                        Logger().sinfo('provider_booking_task start' )
                        try:
                            provider_app.booking(order_info=order_info)
                        except Critical as e:
                            Logger().serror(e)
                        except BookingException as e:
                            Logger().serror(e)
                        if order_info.ffp_account and order_info.ffp_account.is_modified_card_no == 1:
                            # 通过账号的is_modified_card_no 字段判断是否为修改账号后的订单，并给sub_order 赋值
                            Logger().sinfo('has modified_card_no fpp')
                            sub_order.is_modified_card_no = 1
                            order_info.is_modified_card_no = 1
                        order_info.check_provider_order_status()
                        sub_order.provider_order_status = order_info.provider_order_status
                        sub_order.provider_price = order_info.provider_price
                        sub_order.provider_order_id = order_info.provider_order_id
                        sub_order.pnr_code = order_info.pnr_code

                        # TODO extra_data 需要标准规范化
                        if isinstance(order_info.extra_data,dict):
                            sub_order.extra_data = json.dumps(order_info.extra_data)
                        else:
                            sub_order.extra_data = order_info.extra_data
                        commit()
                        flush()
                    except Exception as e:
                        Logger().serror(
                            'provider_booking_task error ')

                if  sub_order.flight_order.ota_order_status in ['READY_TO_ISSUE','MANUAL_ORDER'] and order_info.provider_order_status in ['BOOK_SUCCESS_AND_WAITING_PAY','SET_AUTOPAY']:
                    # 出单成功准备自动支付
                    is_processed = True

                    Logger().sinfo('provider_order_pay_task start')

                    if TBG.global_config['ONLY_MANUAL_PAY'] == True:
                        if order_info.provider_order_status == 'SET_AUTOPAY' :
                            Logger().sinfo('SET_AUTOPAY ')
                            try:
                                provider_app.pay(order_info=order_info)
                            except PayException as e:
                                pass

                            sub_order.provider_order_status = order_info.provider_order_status
                            sub_order.out_trade_no = order_info.out_trade_no
                        elif  provider_app.force_autopay == True:
                            Logger().sinfo('Force autopay ')
                            try:
                                provider_app.pay(order_info=order_info)
                            except PayException as e:
                                pass

                            sub_order.provider_order_status = order_info.provider_order_status
                            sub_order.out_trade_no = order_info.out_trade_no
                        else:

                            # 不做任何操作
                            Logger().sinfo('provider_order_pay_task ONLY_MANUAL_PAY no action')
                            pass
                    else:
                        try:
                            provider_app.pay(order_info=order_info)
                        except PayException as e:
                            pass

                        sub_order.provider_order_status = order_info.provider_order_status
                        sub_order.out_trade_no = order_info.out_trade_no
                    commit()
                    flush()
                if sub_order.flight_order.ota_order_status in ['READY_TO_ISSUE','MANUAL_ORDER'] and ((TBG.global_config['ONLY_MANUAL_PAY'] == False and order_info.provider_order_status == 'PAY_SUCCESS') or( TBG.global_config['ONLY_MANUAL_PAY'] == True and order_info.provider_order_status in ['PAY_SUCCESS','BOOK_SUCCESS_AND_WAITING_PAY'])):
                    # 检查供应商订单状态 等待状态变更为出单成功/失败 出单成功就将票号存储
                    is_processed = True
                    Logger().sinfo('check_provider_order_status_task start ')
                    if TBG.global_config['ONLY_MANUAL_PAY'] and order_info.provider_order_status == 'BOOK_SUCCESS_AND_WAITING_PAY':
                        # 需要设置一些时间等待人工支付
                        gevent.sleep(10)

                    try:
                        previous_status = order_info.provider_order_status
                        # 当订单为 BOOK_SUCCESS_AND_WAITING_PAY 状态时 check_order_status 可以检测是否超时
                        try:
                            provider_app.check_order_status(ffp_account_info=order_info.ffp_account, order_info=order_info)
                            if previous_status != order_info.provider_order_status and order_info.provider_order_status in ['ISSUE_SUCCESS','ISSUE_SUCCESS_AND_NEED_MODIFIED_CARD_NO']:
                                # 此处需要获取票号和pnr
                                # 如果状态有变化就存储数据库，TODO 此处回传的order_info 不完整，只能硬编码根据条件取部分信息，需要优化
                                if order_info.pnr_code:
                                    sub_order.pnr_code = order_info.pnr_code
                                    Logger().sinfo('pnr_code %s updated ' % order_info.pnr_code)
                                if order_info.out_trade_no:
                                    sub_order.out_trade_no = order_info.out_trade_no
                                for pax in order_info.passengers:
                                    # pony 暂不支持直接update，所以只能采用此方式，节省IO
                                    if pax.ticket_no:

                                        sql = 'UPDATE person_2_flight_order as a inner join person2flightorder_suborder as b on a.id = b.person2flightorder set a.ticket_no = "%s" where b.suborder = %s and a.modified_card_no = "%s"' % (pax.ticket_no, sub_order_id, pax.selected_card_no)
                                        TBG.tourbillon_db.execute(sql)
                                        commit()
                                        flush()
                                        sql = 'UPDATE person_2_flight_order as a inner join person2flightorder_suborder as b on a.id = b.person2flightorder set a.ticket_no = "%s" where b.suborder = %s and a.used_card_no = "%s"' % (pax.ticket_no, sub_order_id, pax.selected_card_no)
                                        TBG.tourbillon_db.execute(sql)
                                        commit()
                                        flush()

                                        # update(p.set(ticket_no=pax.ticket_no) for p in Person2FlightOrder
                                        #        if p.flight_order.id == flight_order_id and p.used_card_no == pax.used_card_no and p.used_card_type == pax.used_card_type)
                                        Logger().sinfo('ticket_no:{ticket_no} updated '.format(ticket_no=pax.ticket_no))
                                    else:
                                        Logger().sinfo('pax %s has no ticketno' % pax.selected_card_no)
                                        order_info.provider_order_status == 'TICKET_NO_GET_FAIL'
                                        break

                                if order_info.is_modified_card_no and order_info.provider_order_status == 'ISSUE_SUCCESS':
                                    # 变更状态为提示致电客服修改卡号
                                    order_info.provider_order_status = 'ISSUE_SUCCESS_AND_NEED_MODIFIED_CARD_NO'
                        except NotImplementedError as e:
                            Logger().sinfo('check_order_status function NotImplemented')
                    except CheckOrderStatusException as e:
                        order_info.provider_order_status = 'CHECK_ORDER_STATUS_FAIL'
                        Logger().serror('check_provider_order_status_task error ' )
                    Logger().sinfo('status {previous_status} to {current_status}'.format(previous_status=previous_status, current_status=order_info.provider_order_status))
                    if previous_status != order_info.provider_order_status:
                        # 判断状态是否需要人工介入
                        order_info.check_provider_order_status()
                        if order_info.provider_order_status in ['ISSUE_SUCCESS','ISSUE_SUCCESS_AND_NEED_MODIFIED_CARD_NO'] :
                            #计算执行完成时间
                            sub_order.issue_success_time = Time.curr_date_obj()
                            sub_order.process_duration = (Time.curr_date_obj() - sub_order.create_time ).seconds
                        # 数据回写至db，TODO 此处后面可以考虑移植到internal 的info 类中
                        if previous_status == 'PAY_SUCCESS' and order_info.provider_order_status == 'BOOK_SUCCESS_AND_WAITING_PAY':
                            # 阻止状态回倒
                            Logger().sinfo('pay success to BOOK_SUCCESS_AND_WAITING_PAY is not allowed ')
                            sub_order.provider_order_status = 'PAY_SUCCESS'
                        else:
                            sub_order.provider_order_status = order_info.provider_order_status
                    commit()
                    flush()

            # 目前暂时都是break状态


        Logger().sdebug('loop end')
        gevent.sleep(10)
    except Exception as e:
        Logger().serror(e)
    Logger().sdebug('terminate')


@logger_config('FLIGHT_ORDER_TASK')
def flight_order_task(body):
    """
    汇总子订单的状态到主订单，并且根据条件进行票号回填
    :param ota_name:
    :param provider:
    :param flight_order_id:
    :return:
    """
    ota_name = body['ota_name']
    flight_order_id = body['flight_order_id']

    transaction_start_time = Time.timestamp_s()
    is_processed = False

    TB_ORDER_ID = flight_order_id
    TB_OTA_NAME = ota_name
    try:
        TB_REQUEST_ID = Random.gen_request_id()

        Logger().sdebug('loop start')
        with db_session:
            # 将数据load到对象中
            flight_order = FlightOrder[flight_order_id]
            order_info_input = flight_order.to_dict(with_collections=True,related_objects=True)
            paxs = []
            for p in order_info_input['passengers']:
                pp = p.person.to_dict()
                pax_info = PaxInfo(**pp)
                pax_info.ticket_no = p.ticket_no
                pax_info.used_card_no = p.used_card_no
                pax_info.used_card_type = p.used_card_type
                pax_info.passenger_id = p.passenger_id
                pax_info.person_id = p.person.id
                pax_info.pnr = p.pnr
                paxs.append(pax_info)
            order_info_input['passengers'] = paxs

            # 梳理routing 和 segments
            if order_info_input.get('routing',''):
                routing = order_info_input['routing'].to_dict(with_collections=True,related_objects=True)
                from_segments = []
                for f in routing['from_segments']:
                    ff = f.to_dict()
                    fsi = FlightSegmentInfo(**ff)
                    from_segments.append(fsi)

                ret_segments = []
                for f in routing['ret_segments']:
                    ff = f.to_dict()
                    fsi = FlightSegmentInfo(**ff)
                    ret_segments.append(fsi)
                routing['from_segments'] = from_segments
                routing['ret_segments'] = ret_segments
                order_info_input['routing'] = FlightRoutingInfo(**routing)
            flight_order_id = order_info_input.pop('id')
            order_info = OrderInfo(**order_info_input)
            order_info.flight_order_id = flight_order_id

            Logger().sinfo('duration %s'% (Time.curr_date_obj() - flight_order.ota_create_order_time))
            if (Time.curr_date_obj() - flight_order.update_time).days >= 3 :
                # 超时标记
                Logger().sinfo('order set timeout flag')
                flight_order.process_duration = (flight_order.update_time - flight_order.ota_create_order_time).seconds  # 计算执行时长
                flight_order.ota_order_status = 'TIMEOUT'
                flight_order.update_time = flight_order.update_time

                commit()
                flush()
            else:
                if order_info.providers_status in ['ORDER_INIT','PART_FAIL']:
                    Logger().sdebug('sub order status summaried start')


                    is_processed = True
                    fail_flag = False
                    finished = True
                    total_price = float(0)
                    has_sub_order = False
                    for sub_order in flight_order.sub_orders:
                        if sub_order.provider_order_status not in [ 'MANUAL_CANCEL','FAIL_CANCEL']:  # 如果人工取消或占位（搜索）失败取消 则该订单排除聚合范围和逻辑处理
                            has_sub_order = True
                            if not sub_order.provider_order_status in ['ISSUE_SUCCESS','MANUAL_ISSUE']:
                                # TODO MANUAL_ISSUE
                                finished = False
                            total_price += sub_order.provider_price
                            status_info = PROVIDER_ORDER_STATUS[sub_order.provider_order_status]
                            if status_info['status_type'] == 'fail':
                                fail_flag = True
                            # TODO 暂时没有加入部分人工的判断

                    if has_sub_order:

                        if finished:
                            flight_order.providers_total_price = total_price
                            flight_order.all_finished_time = Time.curr_date_obj()
                            flight_order.process_duration = (flight_order.all_finished_time - flight_order.ota_create_order_time ).seconds  # 计算执行时长
                            flight_order.providers_status = 'ALL_SUCCESS'
                            # 汇总总价

                        if fail_flag:
                            flight_order.providers_status = 'PART_FAIL'
                        Logger().sdebug('fail_flag %s,finished %s ' %(fail_flag,finished))
                        commit()
                        flush()


                if  order_info.ota_type == 'API' and order_info.ota_order_status == 'READY_TO_ISSUE' and order_info.providers_status =='ALL_SUCCESS' and order_info.ota_order_id:
                    # 回填票号  ota_backfill_time
                    # 人工需要将供应商状态置为 ALL_SUCCESS 才可以触发自动回填票号
                    is_processed =  True
                    Logger().sinfo('backfill process start')
                    ota_app = OTARepo.select(ota_name)

                    if ota_app.ticket_process_mode == 'push': # 代表票号为推送到三方接口的方式
                        try:
                            Logger().sinfo(
                                'ota_backfill_task start ')

                            try:
                                set_order_issued_result = ota_app.set_order_issued(order_info=order_info)
                                if set_order_issued_result:
                                    order_info.providers_status = 'BACKFILL_SUCCESS'
                                    flight_order.providers_status = 'BACKFILL_SUCCESS'
                                    flight_order.ota_order_status = 'ISSUE_FINISH'
                                    flight_order.ota_backfill_time = Time.curr_date_obj()
                                    providers_total_price = 0
                                    for sub_order in flight_order.sub_orders:
                                        if sub_order.provider_order_status in ['ISSUE_SUCCESS','MANUAL_ISSUE']:
                                            providers_total_price += sub_order.provider_price
                                    flight_order.providers_total_price = providers_total_price
                                else:
                                    order_info.providers_status = 'BACKFILL_FAIL'
                                    flight_order.providers_status = 'BACKFILL_FAIL'
                            except SetOrderIssuedException as e:
                                Logger().serror('ota_backfill_task fail %s' % e)
                                order_info.providers_status = 'BACKFILL_FAIL'
                                flight_order.providers_status = 'BACKFILL_FAIL'

                            # 是否需要人工介入
                            # order_info.check_providers_status()
                        except Exception as e:
                            Logger().serror(
                                'ota_backfill_task error ')
                    commit()
                    flush()



            Logger().sdebug('loop end')
    except Exception as e:
        Logger().serror(e)
    Logger().sdebug('terminate')


@logger_config('CHECK_OTA_ORDER_STATUS_TASK')
@db_session
def check_ota_order_status_task(body):
    """
    更新OTA状态
    ￼update(p.set(price=price * 1.1) for p in Product
if p.category.name == "T-Shirt")


    :param ota_name:
    :param prepare_update_status_list:  TODO 此处暂时为str格式，需要使用json.loads
    :return:
    """
    ota_name = body['ota_name']
    prepare_update_status_list = body['prepare_update_status_list']
    ota_order_status = body['ota_order_status']

    TB_OTA_NAME = ota_name
    TB_REQUEST_ID = Random.gen_request_id()
    Logger().sdebug('check_ota_order_status_task start')
    ota_app = OTARepo.select(ota_name)
    try:
        order_info_list = ota_app.export_order_list(ota_order_status=ota_order_status)
        Logger().sdebug('ota_order_status %s'% ota_order_status)
        Logger().sdebug('prepare_update_status_list %s' % prepare_update_status_list)

        for update_order_info in prepare_update_status_list:
            # 查找是否具有状态改变并且assoc_order_id 有关联的订单
            TB_ORDER_ID = update_order_info['flight_order_id']
            __ = [x for x in order_info_list if x.assoc_order_id == update_order_info['assoc_order_id']]
            if __:
                __  = __[0]
                Logger().sinfo('ota status change  {previous_status} to {current_status}'.format(previous_status=update_order_info['ota_order_status'],current_status=__.ota_order_status))
                fo = FlightOrder[update_order_info['flight_order_id']]
                fo.ota_order_status = __.ota_order_status
                fo.ota_order_id = __.ota_order_id
                if ota_order_status == 'READY_TO_ISSUE':
                    # 变更该状态时间用来代表用户支付时间
                    fo.ota_pay_time = Time.curr_date_obj()

    except Exception as e:
        Logger().serror('check_ota_order_status_task error')


if __name__ == '__main__':
    pass