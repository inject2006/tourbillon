#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, too-many-arguments, broad-except, anomalous-backslash-in-string
# pylint: disable=missing-docstring, line-too-long, too-few-public-methods
"""
# @Author  : wxt
# @Software: PyCharm
"""

from . import ota_app
from flask import g
from ...dao.models import *
from ...utils.exception import *
from ...ota_repo.base import OTARepo
from ...utils.logger import Logger, logger_config
from ...utils.util import Time, Random, RoutingKey, simple_decrypt
from ...router.core import Router
from .ctx import OTASearchLogDbWriter
from ...dao.internal import ERROR_STATUS, OTAVerifyInfo
from flask import request, jsonify, Response
from app import TBG
from ...api import TBResponse
from pony.orm import flush, commit, db_session


@ota_app.route('/search', methods=['POST'])
@logger_config('OTA_SEARCH', frame_id=False)
def search():
    """
    询价接口

    :return:
    """

    request_start_time = Time.timestamp_ms()
    ota_name = request.args.get("__name", '')
    ota_token = request.args.get("__token", '')
    ota_extra_name = request.args.get("__extra_name", '')
    ota_extra_group = request.args.get("__extra_group", '')
    is_debug = int(request.args.get("__is_debug", 0))  # 是否开启调试模式
    if is_debug:
        # 需要修改日志level
        TB_IS_LOG_DEBUG = 'Enable'

    ret_status = 'INNER_ERROR_1002'
    req_body = request.data
    ota_app = None
    TB_OTA_NAME = ota_name
    TB_REQUEST_ID = Random.gen_request_id()
    has_exception = 0
    has_filtered = 0
    try:

        if ota_name:
            ota_app = OTARepo.select(ota_name)
            if ota_app.ota_token != ota_token:
                raise OTATokenException('ota %s,token %s' % (ota_name, ota_token))
        # Logger().sdebug('{ota_name} search_api request ,Search Conditions {req_body}'.format(ota_name=ota_name, req_body=req_body))
        ota_app.work_flow = 'search'
        ota_app.ota_extra_name = ota_extra_name
        ota_app.ota_extra_group = ota_extra_group
        ota_app.before_search_interface(req_body)
        if ota_app.is_ota_fusing():  # add 2018-12-12
            ota_app.search_info.return_status = 'FUSING'
            raise AccessControlException('ota %s,token %s fusing' % (ota_name, ota_token))
        if not ota_app.frequency_verification(api_name='search'):
            ota_app.search_info.return_status = 'FREQ_LIMITED'
            raise AccessControlException('ota %s,token %s frequency_verification' % (ota_name, ota_token))
        if ota_app.filter(is_debug=is_debug):
            raise AccessControlException('ota %s,token %s filtered' % (ota_name, ota_token))

        router = Router(ota_app)
        router.run()
        ota_app.after_search_interface()
        ret = ota_app.final_result
        # Logger().sdebug('{ota_name} search_api return Success '.format(ota_name=ota_name))

    except RouterDeliverExeception as e:
        has_exception = 1
        ret = ota_app.search_interface_error_output()
    except AccessControlException as e:
        has_filtered = 1
        Logger().sdebug(e)
        ret = ota_app.search_interface_error_output()
    except NoSuchOTAException as e:
        Logger().sinfo(e)
        ret_status = 'INNER_ERROR_1001'
        ret = {'status': ret_status, 'msg': ERROR_STATUS[ret_status]}
    except OTATokenException as e:
        Logger().sinfo(e)
        ret_status = 'INNER_ERROR_1003'
        ret = {'status': ret_status, 'msg': ERROR_STATUS[ret_status]}
    except Exception as e:
        # 2018-12-07 屏蔽所有异常
        Logger().serror(
            '{ota_name} search_api return Failed ret_status: {ret_status}'.format(ota_name=ota_name, ret_status=ret_status))

        ret = ota_app.search_interface_error_output()
        has_exception = 1

    # 日志记录
    if ota_app and ota_app.search_info:
        log = ota_app.search_info

        request_total_latency = Time.timestamp_ms() - request_start_time
        log.ota_name = ota_name


        # TODO 临时缩减字段，降低influxdb压力
        metrics_tags = dict(
            ota_name=ota_name,
            from_date=log.from_date,
            return_status=log.return_status,
            return_details = log.return_details,
            from_to_airport='%s%s-%s%s' % (log.from_airport, log.from_city, log.to_airport, log.to_city)
        )

        if log.assoc_search_routings:
            return_flight_count = 1
        else:
            return_flight_count = 0

        if has_filtered : # TODO 此处有耦合
            enter_count = 0
        else:
            enter_count = 1

        TBG.tb_aggr_metrics.write(
            "OTA.SEARCH",
            tags=metrics_tags,
            fields=dict(
                total_latency=request_total_latency,
                total_count=1,
                return_flight_count=return_flight_count,
                error_count=has_exception,
                enter_count=enter_count,
                routing_total_count=log.get('routing_total_count',0),
                routing_show_count=log.get('routing_show_count', 0),
                routing_auto_fare_count=log.get('routing_auto_fare_count', 0),
                routing_fare_twice_fare_count=log.get('routing_fare_twice_fare_count', 0),
                routing_low_price_forecast_fare_count=log.get('routing_low_price_forecast_fare_count', 0),
                routing_manual_fare_count=log.get('routing_manual_fare_count', 0),
                routing_no_fare_count=log.get('routing_no_fare_count', 0),
                routing_fusing_count=log.get('routing_fusing_count', 0),
                routing_carrier_filtered_count=log.get('routing_carrier_filtered_count', 0),
                routing_invalid_cabin_filtered_count=log.get('routing_invalid_cabin_filtered_count', 0),
                routing_min_cabin_count_filtered_count=log.get('routing_min_cabin_count_filtered_count', 0),
                routing_operation_carrier_filtered_count=log.get('routing_operation_carrier_filtered_count', 0),
                routing_virtual_cabin_count=log.get('routing_virtual_cabin_count', 0),
                routing_enter_time_interval_long_count=log.get('routing_enter_time_interval_long_count', 0),


            ))

    Logger().sdebug('ret %s' % ret)
    return TBResponse(ret, mimetype='text/plain')


@ota_app.route('/verify', methods=['POST'])
@logger_config('OTA_VERIFY', frame_id=False)
def verify():
    """
    验价接口
    备注： 查询前过滤器，查询后过滤器
    :return:
    """
    request_start_time = Time.timestamp_ms()
    ota_name = request.args.get("__name", '')
    ota_token = request.args.get("__token", '')
    ota_extra_name = request.args.get("__extra_name", '')
    ota_extra_group = request.args.get("__extra_group", '')
    is_debug = int(request.args.get("__is_debug", 0))  # 是否开启调试模式
    if is_debug:
        # 需要修改日志level
        TB_IS_LOG_DEBUG = 'Enable'
    ret_status = 'INNER_ERROR_1002'
    req_body = request.data
    ota_app = None
    TB_OTA_NAME = ota_name
    TB_REQUEST_ID = Random.gen_request_id()
    try:

        if ota_name:
            ota_app = OTARepo.select(ota_name)
            if ota_app.ota_token != ota_token:
                raise OTATokenException('ota %s,token %s' % (ota_name, ota_token))
        ota_app.work_flow = 'verify'
        ota_app.ota_extra_name = ota_extra_name
        ota_app.ota_extra_group = ota_extra_group
        ota_app.before_verify_interface(req_body)
        ota_app.verify_interface(request_id=TB_REQUEST_ID)
        ret = ota_app.final_result

    except RouterDeliverExeception as e:
        ota_app.search_info.return_status = 'NO_ROUTE'
        ret = ota_app.verify_interface_error_output()
    except NoSuchOTAException as e:
        ret_status = 'INNER_ERROR_1001'
        ret = {'status': ret_status, 'msg': ERROR_STATUS[ret_status]}
    except OTATokenException as e:
        ret_status = 'INNER_ERROR_1003'
        ret = {'status': ret_status, 'msg': ERROR_STATUS[ret_status]}
    except Exception as e:
        Logger().serror(
            '{ota_name} verify_api return Failed ret_status: {ret_status}'.format(ota_name=ota_name, ret_status=ret_status))
        ret = {'status': ret_status, 'msg': ERROR_STATUS[ret_status]}

    if ota_app.current_provider_channel == 'pdc_faker':
        try:
            Logger().info("pdc_faker verify log: {}/{}-{}".format(
                ota_app.search_info.from_date, ota_app.search_info.from_airport, ota_app.search_info.to_airport))
        except:
            Logger().info('pdc_faker verify log error')

    if ota_app and ota_app.search_info and ota_app.current_provider_channel != 'pdc_faker':  # 屏蔽测试航线
        log = ota_app.search_info
        log.total_latency = Time.timestamp_ms() - request_start_time
        log.fare_operation = ''
        log.provider = ota_app.current_provider
        log.provider_channel = ota_app.current_provider_channel
        log.ota_name = ota_name

        metrics_tags = dict(
            ota_name=log.ota_name,
            provider=log.provider,
            provider_channel=log.provider_channel,
            from_date=log.from_date,
            ret_date=log.ret_date,
            from_airport=log.from_airport,
            to_airport=log.to_airport,
            return_status=log.return_status

        )
        if log.return_status == 'SUCCESS':
            success_count = 1
        else:
            success_count = 0

        TBG.tb_metrics.write(
            "OTA.VERIFY",
            tags=metrics_tags,
            fields=dict(
                total_latency=log.total_latency,
                total_count=1,
                success_count = success_count
            ))

        logfile_tags = dict(
            ota_name=log.ota_name,
            provider=log.provider,
            provider_channel=log.provider_channel,
            from_date=log.from_date,
            ret_date=log.ret_date,
            from_airport=log.from_airport,
            to_airport=log.to_airport,
            return_status=log.return_status,
            ret=ret,
            req=req_body,
            verify_routing_key=log.verify_routing_key,
            providers_stat=log.get('providers_stat', {}),
            low_price=log.get('low_price',0)
        )

        # 验价数据入库
        with db_session:
            try:
                req_body = json.dumps(json.loads(req_body))
                rk_info = RoutingKey().unserialize(log.verify_routing_key, is_encrypted=True)
                OTAVerify(
                    ota_name=log.ota_name, provider=log.provider, provider_channel=log.provider_channel,
                    from_date=log.from_date, ret_date=log.ret_date if log.ret_date else '', from_airport=log.from_airport,
                    to_airport=log.to_airport, return_status=log.return_status,
                    ret=json.dumps(ret), req = req_body, routing_key = simple_decrypt(log.verify_routing_key),
                    flight_number=rk_info['flight_number'], cabin = rk_info['cabin'], verify_duration = int(log.total_latency / 1000),
                    verify_time=datetime.datetime.strptime(time.strftime('%Y%m%d%H%M%S', time.localtime(int(request_start_time / 1000))), '%Y%m%d%H%M%S'),
                    search_time=datetime.datetime.strptime(rk_info['search_time'], '%Y%m%d%H%M%S') if rk_info['search_time'] else None,
                    enter_time=datetime.datetime.strptime(rk_info['enter_time'], '%Y%m%d%H%M%S') if rk_info['enter_time'] else None,
                    s2v_duration=int(request_start_time / 1000 - time.mktime(time.strptime(
                        rk_info['search_time'], '%Y%m%d%H%M%S'))) if rk_info['search_time'] else 0,
                    providers_stat=json.dumps(log.get('providers_stat',{})),request_id=TB_REQUEST_ID,fare_info=json.dumps(log.fare_info),
                    current_assoc_fare_info=rk_info['assoc_fare_info'],adjust_assoc_fare_info=log.fare_info.assoc_fare_info,rsno=rk_info['rsno'],
                    verify_details=json.dumps(log.verify_details),ota_product_code=log.ota_product_code
                )
            except Exception as e:
                Logger().serror('ota verify save db error')

        Logger().sinfo(json.dumps(logfile_tags))

    return TBResponse(ret, mimetype='text/plain')


@ota_app.route('/order', methods=['POST'])
@logger_config('OTA_ORDER', frame_id=False)
def order():
    """
    验价接口
    备注： 查询前过滤器，查询后过滤器
    :return:
    """
    request_start_time = Time.timestamp_ms()
    ota_name = request.args.get("__name", '')
    ota_token = request.args.get("__token", '')
    ota_extra_name = request.args.get("__extra_name", '')
    ota_extra_group = request.args.get("__extra_group", '')
    is_debug = int(request.args.get("__is_debug", 0))  # 是否开启调试模式
    if is_debug:
        # 需要修改日志level
        TB_IS_LOG_DEBUG = 'Enable'
    ret_status = 'INNER_ERROR_1002'
    req_body = request.data
    ota_app = None
    TB_OTA_NAME = ota_name
    TB_REQUEST_ID = Random.gen_request_id()
    try:

        if ota_name:
            ota_app = OTARepo.select(ota_name)
            if ota_app.ota_token != ota_token:
                raise OTATokenException('ota %s,token %s' % (ota_name, ota_token))
        ota_app.work_flow = 'order'
        ota_app.ota_extra_name = ota_extra_name
        ota_app.ota_extra_group = ota_extra_group
        ota_app.before_order_interface(req_body)
        ota_app.order_interface(req_body=req_body,request_id=TB_REQUEST_ID)
        ret = ota_app.final_result
    except RouterDeliverExeception as e:
        ret = ota_app.order_interface_error_output()
        ota_app.order_info.return_status = 'NO_ROUTE'
    except NoSuchOTAException as e:
        ret_status = 'INNER_ERROR_1001'
        ret = {'status': ret_status, 'msg': ERROR_STATUS[ret_status]}
    except OTATokenException as e:
        ret_status = 'INNER_ERROR_1003'
        ret = {'status': ret_status, 'msg': ERROR_STATUS[ret_status]}
    except Exception as e:
        Logger().serror(
            '{ota_name} order_api return Failed ret_status: {ret_status}'.format(ota_name=ota_name, ret_status=ret_status))
        ret = {'status': ret_status, 'msg': ERROR_STATUS[ret_status]}

    if ota_app and ota_app.order_info:
        log = ota_app.order_info
        log.total_latency = Time.timestamp_ms() - request_start_time
        log.fare_operation = ''
        log.provider = ota_app.current_provider
        log.provider_channel = ota_app.current_provider_channel
        log.ota_name = ota_name

        metrics_tags = dict(
            ota_name=log.ota_name,
            provider=log.provider,
            provider_channel=log.provider_channel,
            from_date=log.from_date,
            ret_date=log.ret_date,
            from_airport=log.from_airport,
            to_airport=log.to_airport,
            return_status=log.return_status,
            return_details=log.return_details,

        )

        if log.return_status == 'SUCCESS':
            success_count = 1
        else:
            success_count = 0

        TBG.tb_metrics.write(
            "OTA.ORDER",
            tags=metrics_tags,
            fields=dict(
                total_latency=log.total_latency,
                total_count=1,
                success_count = success_count
            ))

        logfile_tags = dict(
            ota_name=log.ota_name,
            provider=log.provider,
            provider_channel=log.provider_channel,
            from_date=log.from_date,
            ret_date=log.ret_date,
            from_airport=log.from_airport,
            to_airport=log.to_airport,
            return_status=log.return_status,
            return_details=log.return_details,
            ret=ret,
            req=req_body,
            verify_routing_key=log.verify_routing_key
        )
        Logger().sinfo(json.dumps(logfile_tags))


    Logger().info(ret)

    return TBResponse(ret, mimetype='text/plain')

@ota_app.route('/notice_issue', methods=['POST'])
@logger_config('OTA_NOTICE_ISSUE', frame_id=False)
def notice_issue():
    """
    通知出票（支付取消）接口

    :return:
    """
    ota_name = request.args.get("__name", '')
    ota_token = request.args.get("__token", '')
    ota_extra_name = request.args.get("__extra_name", '')
    ota_extra_group = request.args.get("__extra_group", '')
    is_debug = int(request.args.get("__is_debug", 0))  # 是否开启调试模式
    if is_debug:
        # 需要修改日志level
        TB_IS_LOG_DEBUG = 'Enable'
    ret_status = 'INNER_ERROR_1002'
    req_body = request.data
    TB_OTA_NAME = ota_name
    TB_REQUEST_ID = Random.gen_request_id()
    try:

        if ota_name:
            ota_app = OTARepo.select(ota_name)
            if ota_app.ota_token != ota_token:
                raise OTATokenException('ota %s,token %s' % (ota_name, ota_token))
        Logger().sinfo('{ota_name} notice_issue_api request  {req_body}'.format(ota_name=ota_name, req_body=req_body))
        ota_app.work_flow = 'notice_issue'
        ota_app.ota_extra_name = ota_extra_name
        ota_app.ota_extra_group = ota_extra_group
        ota_app.notice_issue_interface(req_body)
        ret = ota_app.final_result
        Logger().sinfo('{ota_name} notice_issue_api return Success '.format(ota_name=ota_name))
        Logger().info(ret)
        return Response(ret, mimetype='text/plain')

    except NoSuchOTAException as e:
        ret_status = 'INNER_ERROR_1001'
    except OTATokenException as e:
        ret_status = 'INNER_ERROR_1003'
    except Exception as e:
        Logger().serror(
            '{ota_name} notice_issue_api return Failed ret_status: {ret_status}'.format(ota_name=ota_name, ret_status=ret_status))
    ret = {'status': ret_status, 'msg': ERROR_STATUS[ret_status]}
    return TBResponse(ret, mimetype='text/plain')


@ota_app.route('/notice_pay', methods=['POST'])
@logger_config('OTA_NOTICE_PAY', frame_id=False)
def notice_pay():
    """
    通知扣款接口

    :return:
    """
    ota_name = request.args.get("__name", '')
    ota_token = request.args.get("__token", '')
    ota_extra_name = request.args.get("__extra_name", '')
    ota_extra_group = request.args.get("__extra_group", '')
    is_debug = int(request.args.get("__is_debug", 0))  # 是否开启调试模式
    if is_debug:
        # 需要修改日志level
        TB_IS_LOG_DEBUG = 'Enable'
    ret_status = 'INNER_ERROR_1002'
    req_body = request.data
    TB_OTA_NAME = ota_name
    TB_REQUEST_ID = Random.gen_request_id()
    try:

        if ota_name:
            ota_app = OTARepo.select(ota_name)
            if ota_app.ota_token != ota_token:
                raise OTATokenException('ota %s,token %s' % (ota_name, ota_token))
        Logger().sinfo('{ota_name} notice_pay request  {req_body}'.format(ota_name=ota_name, req_body=req_body))
        ota_app.work_flow = 'notice_pay'
        ota_app.ota_extra_name = ota_extra_name
        ota_app.ota_extra_group = ota_extra_group
        ota_app.notice_pay_interface(req_body)
        ret = ota_app.final_result
        Logger().sinfo('{ota_name} notice_pay_api return Success '.format(ota_name=ota_name))
        return Response(ret, mimetype='text/plain')

    except NoSuchOTAException as e:
        ret_status = 'INNER_ERROR_1001'
    except OTATokenException as e:
        ret_status = 'INNER_ERROR_1003'
    except Exception as e:
        Logger().serror(
            '{ota_name} notice_pay_api return Failed ret_status: {ret_status}'.format(ota_name=ota_name, ret_status=ret_status))
    ret = {'status': ret_status, 'msg': ERROR_STATUS[ret_status]}
    return TBResponse(ret, mimetype='text/plain')


@ota_app.route('/order_detail', methods=['POST'])
@logger_config('OTA_ORDER_DETAIL', frame_id=False)
def order_detail():
    """
    订单详情查询接口

    :return:
    """
    ota_name = request.args.get("__name", '')
    ota_token = request.args.get("__token", '')
    ota_extra_name = request.args.get("__extra_name", '')
    ota_extra_group = request.args.get("__extra_group", '')
    is_debug = int(request.args.get("__is_debug", 0))  # 是否开启调试模式
    if is_debug:
        # 需要修改日志level
        TB_IS_LOG_DEBUG = 'Enable'
    ret_status = 'INNER_ERROR_1002'
    req_body = request.data
    TB_OTA_NAME = ota_name
    TB_REQUEST_ID = Random.gen_request_id()
    try:

        if ota_name:
            ota_app = OTARepo.select(ota_name)
            if ota_app.ota_token != ota_token:
                raise OTATokenException('ota %s,token %s' % (ota_name, ota_token))
        Logger().sinfo('{ota_name} order_detail request  {req_body}'.format(ota_name=ota_name, req_body=req_body))
        ota_app.work_flow = 'order_detail'
        ota_app.ota_extra_name = ota_extra_name
        ota_app.ota_extra_group = ota_extra_group
        ota_app.order_detail_interface(req_body)
        ret = ota_app.final_result
        Logger().sinfo('{ota_name} order_detail_api return Success '.format(ota_name=ota_name))
        return Response(ret, mimetype='text/plain')

    except NoSuchOTAException as e:
        ret_status = 'INNER_ERROR_1001'
    except OTATokenException as e:
        ret_status = 'INNER_ERROR_1003'
    except Exception as e:
        Logger().serror(
            '{ota_name} order_detail_api return Failed ret_status: {ret_status}'.format(ota_name=ota_name, ret_status=ret_status))
    ret = {'status': ret_status, 'msg': ERROR_STATUS[ret_status]}
    return TBResponse(ret, mimetype='text/plain')


@ota_app.route('/order_list', methods=['POST'])
@logger_config('OTA_ORDER_LIST', frame_id=False)
def order_list():
    """
    订单列表查询接口

    :return:
    """
    ota_name = request.args.get("__name", '')
    ota_token = request.args.get("__token", '')
    ota_extra_name = request.args.get("__extra_name", '')
    ota_extra_group = request.args.get("__extra_group", '')
    is_debug = int(request.args.get("__is_debug", 0))  # 是否开启调试模式
    if is_debug:
        # 需要修改日志level
        TB_IS_LOG_DEBUG = 'Enable'
    ret_status = 'INNER_ERROR_1002'
    req_body = request.data
    TB_OTA_NAME = ota_name
    TB_REQUEST_ID = Random.gen_request_id()
    try:

        if ota_name:
            ota_app = OTARepo.select(ota_name)
            if ota_app.ota_token != ota_token:
                raise OTATokenException('ota %s,token %s' % (ota_name, ota_token))
        if not ota_app.frequency_verification(api_name='order_list'):
            raise AccessControlException('ota %s,token %s frequency_verification' % (ota_name, ota_token))
        Logger().sinfo('{ota_name} order_list request  {req_body}'.format(ota_name=ota_name, req_body=req_body))
        ota_app.work_flow = 'order_list'
        ota_app.ota_extra_name = ota_extra_name
        ota_app.ota_extra_group = ota_extra_group
        ota_app.order_list_interface(req_body)
        ret = ota_app.final_result
        Logger().sinfo('{ota_name} order_list_api return Success '.format(ota_name=ota_name))
        return Response(ret, mimetype='text/plain')

    except NoSuchOTAException as e:
        ret_status = 'INNER_ERROR_1001'
    except OTATokenException as e:
        ret_status = 'INNER_ERROR_1003'
    except AccessControlException as e:
        ret_status = 'INNER_ERROR_1004'
    except Exception as e:
        Logger().serror(
            '{ota_name} order_list_api return Failed ret_status: {ret_status}'.format(ota_name=ota_name, ret_status=ret_status))
    ret = {'status': ret_status, 'msg': ERROR_STATUS[ret_status]}
    return TBResponse(ret, mimetype='text/plain')

@ota_app.route('/config', methods=['POST','GET'])
@logger_config('OTA_CONFIG', frame_id=False)
def config():
    """
    订单列表查询接口

    :return:
    """
    ota_name = request.args.get("__name", '')
    ota_token = request.args.get("__token", '')
    ota_extra_name = request.args.get("__extra_name", '')
    ota_extra_group = request.args.get("__extra_group", '')
    is_debug = int(request.args.get("__is_debug", 0))  # 是否开启调试模式
    if is_debug:
        # 需要修改日志level
        TB_IS_LOG_DEBUG = 'Enable'
    ret_status = 'INNER_ERROR_1002'
    req_body = request.data
    req_params = {}
    for k,v in request.args.iteritems():
        if k not in ['__name','__token']:
            req_params[k] = v

    TB_OTA_NAME = ota_name
    TB_REQUEST_ID = Random.gen_request_id()
    try:

        if ota_name:
            ota_app = OTARepo.select(ota_name)
            if ota_app.ota_token != ota_token:
                raise OTATokenException('ota %s,token %s' % (ota_name, ota_token))

        Logger().sinfo('{ota_name} config request  {req_body}'.format(ota_name=ota_name, req_body=req_body))
        ota_app.work_flow = 'config'
        ota_app.ota_extra_name = ota_extra_name
        ota_app.ota_extra_group = ota_extra_group
        ota_app.config(req_body=req_body,req_params=req_params)
        ret = ota_app.final_result
        Logger().sinfo('{ota_name} config_api return Success '.format(ota_name=ota_name))
        return Response(ret, mimetype='text/plain')

    except NoSuchOTAException as e:
        ret_status = 'INNER_ERROR_1001'
    except OTATokenException as e:
        ret_status = 'INNER_ERROR_1003'
    except AccessControlException as e:
        ret_status = 'INNER_ERROR_1004'
    except Exception as e:
        Logger().serror(
            '{ota_name} config_api return Failed ret_status: {ret_status}'.format(ota_name=ota_name, ret_status=ret_status))
    ret = {'status': ret_status, 'msg': ERROR_STATUS[ret_status]}
    return TBResponse(ret, mimetype='text/plain')

@ota_app.route('/test', methods=['GET'])
def test():
    return 'ok'


if __name__ == '__main__':
    pass
