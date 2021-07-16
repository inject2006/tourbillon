#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, too-many-arguments, broad-except, anomalous-backslash-in-string
# pylint: disable=missing-docstring, line-too-long, too-few-public-methods
"""
# @Author  : wxt
# @Software: PyCharm
"""
import json
import datetime
import base64
from urllib import quote, unquote
from . import misc_app
from ...utils.util import Random, mobile_match, identity_card_match, RoutingKey
from ...utils.util import Time, convert_unicode
from ...utils.logger import Logger
from ...dao.models import *
from ...dao.internal import *
from ...automatic_repo.base import ProviderAutoRepo
from ...ota_repo.base import OTARepo
from flask.views import MethodView
from flask import request, jsonify, Response, g
from pony.orm import select, desc, db_session
from pony.orm.examples.estore import count
from .ctx import perm_check
from ...api import TBResponse
from app import TBG
from ...controller.fusing_limiter import FusingControl
from ...controller.cabin_revise import CabinReviseControl

class SysControl(MethodView):
    """
    系统控制
    :return:
    """

    @perm_check(perm_module='sys_control')
    def get(self):
        """
        查看系统状态
        search_interface_open_time
        {

            'is_include_nonworking_day': 1,  # 是否包含节假日
            'open_hours':[[1,6],[20,23]],  # 每天开启时间,可以包含多个时间段，单位为小时，
        }
        :return: 启动还是停止状态，目前过滤
        """

        operation_config = TBG.config_redis.get_value('operation_config')
        if operation_config:
            operation_config = json.loads(operation_config)
        else:
            operation_config = {}
        return TBResponse({'data': {'operation_config': json.dumps(operation_config)}})

    @perm_check(perm_module='sys_control')
    def post(self):
        """
        {
            'search_interface_status':'turn_on',  # 询价接口状态  turn_on 开启 turn_off 关闭
            'switch_mode':'manual',  # manual 手动模式 auto 自动模式
            'is_include_nonworking_day': 0,  # 是否包含节假日 1 包含 0 不包含
            'open_hours': [[6, 20]],  # 每天开启时间,可以包含多个时间段，单位为小时，
        }
        :return:
        """

        try:
            req_body = request.get_json()
            data = req_body.get('operation_config')
            operation_config = json.loads(data)

            # 参数验证
            for k,v in operation_config.iteritems():
                for fs in v.get('fare_strategy',[]):
                    if not -200 < fs['adult_price_calc'] < 200:
                        return TBResponse('price_calc_invalid_range', status=500)

            TBG.config_redis.insert_value('operation_config', json.dumps(operation_config))
            return TBResponse({'ret_code': 1})
        except Exception as e:
            Logger().serror('sys_control api error')
        return TBResponse('error', status=500)


sys_control_view = SysControl.as_view('sys_control')
misc_app.add_url_rule('/sys_control/',
                      view_func=sys_control_view, methods=['GET','POST' ])


class OTAConfig(MethodView):
    """
    系统控制
    :return:
    """

    @perm_check(perm_module='ota_config')
    def get(self,ota_name=''):
        """
        查看系统状态
        action = list_all_otas 列出所有ota  返回格式 {'data':[{'name':'xxx','cn_name':'xxxx'}]}

        返回单个ota config dict  {'data':{operation_config}}
        :return:
        """

        TB_REQUEST_ID = Random.gen_request_id()
        try:
            action = request.args.get('action', '')
            if action == 'list_all_otas':
                # 列出所有ota
                return TBResponse({'data':OTARepo.list_all_otas()})
            elif action == 'unattended':
                # 无人值守的配置
                if OTARepo.select(ota_name):

                    operation_config = TBG.config_redis.get_value('unattended_operation_config_%s' % ota_name)
                    if operation_config:
                        operation_config = json.loads(operation_config)
                    else:
                        operation_config = {}
                    return TBResponse({'data': operation_config})
                else:
                    raise NoSuchOTAException
            else:
                # 有人值守的默认配置
                if OTARepo.select(ota_name):

                    operation_config = TBG.config_redis.get_value('operation_config_%s'% ota_name)
                    if operation_config:
                        operation_config = json.loads(operation_config)
                    else:
                        operation_config = {}
                    return TBResponse({'data':operation_config})
                else:
                    raise NoSuchOTAException

        except Exception as e:
            Logger().serror('ota_config api error')
        return TBResponse('error', status=500)


    @perm_check(perm_module='ota_config')
    def post(self):
        """
        {'ota_name':'xxx','operation_config':{xxx}}
        :return:
        """
        TB_REQUEST_ID = Random.gen_request_id()
        try:
            req_body = request.get_json()
            ota_name = req_body.get('ota_name','')
            config_mode = req_body.get('config_mode', 'default')
            if ota_name:
                operation_config = req_body.get('operation_config', {})
                if config_mode == 'default':
                    Logger().sinfo('default operation_config save')
                    TBG.config_redis.insert_value('operation_config_%s' % ota_name, json.dumps(operation_config))
                else:
                    Logger().sinfo('unattended operation_config save')
                    TBG.config_redis.insert_value('unattended_operation_config_%s' % ota_name, json.dumps(operation_config))
                return TBResponse({'ret_code': 1})
            else:
                TBResponse('no ota_name', status=500)

        except Exception as e:
            Logger().serror('ota_config api error')
        return TBResponse('error', status=500)


ota_config_view = OTAConfig.as_view('ota_config')
misc_app.add_url_rule('/ota_config/<ota_name>',
                      view_func=ota_config_view, methods=['GET'])
misc_app.add_url_rule('/ota_config/',
                      view_func=ota_config_view, methods=['GET', 'POST'])



class PdcPolicyConfig(MethodView):
    """
    pdc供应商政策操作接口
    :return:
    """

    @perm_check(perm_module='pdc_policy_config')
    def get(self):
        """
        查看系统状态
        action = list_all_otas 列出所有ota  返回格式 {'data':[{'name':'xxx','cn_name':'xxxx'}]}

        返回单个ota config dict  {'data':{operation_config}}
        :return:
        """

        TB_REQUEST_ID = Random.gen_request_id()
        try:
            pdc_policy = TBG.config_redis.get_value('pdc_policy')
            if pdc_policy:
                pdc_policy = json.loads(pdc_policy)
            else:
                pdc_policy = {}
            return TBResponse({'data': pdc_policy})

        except Exception as e:
            Logger().serror('pdc_policy_config api error')
        return TBResponse('error', status=500)


    @perm_check(perm_module='pdc_policy_config')
    def post(self):
        """
        {'ota_name':'xxx','operation_config':{xxx}}
        :return:
        """
        TB_REQUEST_ID = Random.gen_request_id()
        try:
            req_body = request.get_json()
            if req_body:
                pdc_policy_config = req_body.get('pdc_policy_config', {})
                TBG.config_redis.insert_value('pdc_policy',json.dumps(pdc_policy_config))
                return TBResponse({'ret_code': 1})
            else:
                TBResponse('req_body is null', status=500)

        except Exception as e:
            Logger().serror('ota_config api error')
        return TBResponse('error', status=500)


pdc_policy_config_view = PdcPolicyConfig.as_view('pdc_policy_config')
misc_app.add_url_rule('/pdc_policy_config/<ota_name>',
                      view_func=pdc_policy_config_view, methods=['GET'])
misc_app.add_url_rule('/pdc_policy_config/',
                      view_func=pdc_policy_config_view, methods=['GET', 'POST'])


class ManualSearchFlight(MethodView):
    """
    机票搜索
    :return:
    """

    @perm_check(perm_module='manual_booking')
    def get(self):
        TB_REQUEST_ID = Random.gen_request_id()
        provider_channel = request.args.get("provider_channel", '')
        from_date = request.args.get("from_date", '')
        ret_date = request.args.get("ret_date", '')
        from_airport = request.args.get("from_airport", '')
        to_airport = request.args.get("to_airport", '')
        adt_count = request.args.get("adt_count", '1')
        chd_count = request.args.get("chd_count", '0')
        try:
            if from_date:
                try:
                    datetime.datetime.strptime(from_date, '%Y-%m-%d')
                except Exception as e:
                    return Response('from_date format need 1990-04-09', 500)
                from_airport = from_airport.upper()
                to_airport = to_airport.upper()
                search_info = SearchInfo()
                search_info.from_date = from_date
                if ret_date:
                    search_info.ret_date = ret_date
                    search_info.trip_type = 'RT'
                else:
                    search_info.trip_type = 'OW'
                search_info.from_airport = from_airport
                search_info.to_airport = to_airport
                search_info.adt_count = int(adt_count)
                search_info.chd_count = int(chd_count)
                search_info.inf_count = 0
                search_info.attr_competion()

                provider_app = ProviderAutoRepo.select(provider_channel)
                provider_app.flight_search(search_info=search_info)
                provider = provider_app.provider
                ret = {'ret_code': 1, 'data': []}
                data = []
                for flight_routing in search_info.assoc_search_routings:
                    segments = []
                    cabin_grade = flight_routing.from_segments[0].cabin_grade
                    cabin = flight_routing.from_segments[0].cabin
                    cabin_count = flight_routing.from_segments[0].cabin_count
                    for s in flight_routing.from_segments:
                        seg_str = "去程：{flight_number}，{cabin_grade}舱{cabin} 【{dep_airport}】【{dep_terminal}】【{dep_time}】-【{arr_airport}】【{arr_terminal}】【{arr_time}】".format(dep_airport=s.dep_airport,
                                                                                                                                                                            dep_time=s.dep_time,
                                                                                                                                                                            dep_terminal=s.dep_terminal,
                                                                                                                                                                            arr_airport=s.arr_airport,
                                                                                                                                                                            arr_time=s.arr_time,
                                                                                                                                                                            arr_terminal=s.arr_terminal,
                                                                                                                                                                            flight_number=s.flight_number,
                                                                                                                                                                            cabin_grade=s.cabin_grade,
                                                                                                                                                                            cabin=s.cabin)
                        segments.append(seg_str)
                    for s in flight_routing.ret_segments:
                        seg_str = "返程：{flight_number}，{cabin_grade}舱{cabin} 【{dep_airport}】【{dep_terminal}】【{dep_time}】-【{arr_airport}】【{arr_terminal}】【{arr_time}】".format(dep_airport=s.dep_airport,
                                                                                                                                                                            dep_time=s.dep_time,
                                                                                                                                                                            dep_terminal=s.dep_terminal,
                                                                                                                                                                            arr_airport=s.arr_airport,
                                                                                                                                                                            arr_time=s.arr_time,
                                                                                                                                                                            arr_terminal=s.arr_terminal,
                                                                                                                                                                            flight_number=s.flight_number,
                                                                                                                                                                            cabin_grade=s.cabin_grade,
                                                                                                                                                                            cabin=s.cabin)
                        segments.append(seg_str)
                    segments_str = '<br />'.join(segments)

                    """
                "table_columns":["provider","from_airport","to_airport","from_date","cabin_grade","cabin","cabin_count"
                ,"segments","adult_price","adult_price_discount","adult_tax","child_price","child_tax","routing_key",
                "ret_date"],

                    """
                    from_airport_str = "%s(%s)" % (from_airport, search_info.from_city)
                    to_airport_str = "%s(%s)" % (to_airport, search_info.to_city)
                    adult_price_discount_str = "%.1f折" % (float(flight_routing.adult_price_discount) / 10)

                    routing_json = quote(base64.b64encode(json.dumps(flight_routing)))
                    data.append(
                        {
                            'provider_channel': provider_channel,
                            'from_airport': from_airport_str,
                            'to_airport': to_airport_str,
                            'from_date': from_date,
                            'cabin_grade': cabin_grade,
                            'cabin': cabin,
                            'cabin_count': cabin_count,
                            'segments': segments_str,
                            'adult_price': flight_routing.adult_price,
                            'adult_price_discount': adult_price_discount_str,
                            'adult_tax': flight_routing.adult_tax,
                            'child_price': flight_routing.child_price,
                            'child_tax': flight_routing.child_tax,
                            'routing_key': flight_routing.routing_key,
                            'ret_date': ret_date,
                            'operation': '<a class="btn btn-primary" href="/_modules/manual/order.html?routing_key={routing_key}&provider={provider}&provider_channel={provider_channel}&operation_product_type={operation_product_type}&routing_range={routing_range}&trip_type={trip_type}&from_date={from_date}&ret_date={ret_date}&from_airport={from_airport}&to_airport={to_airport}&segments={segments}&adult_price={adult_price}&adult_tax={adult_tax}&child_price={child_price}&child_tax={child_tax}&adult_price_discount={adult_price_discount}&from_airport_str={from_airport_str}&to_airport_str={to_airport_str}&routing_json={routing_json}"  target="_blank" >订票</a>'.format(
                                routing_key=flight_routing.routing_key, provider=provider, provider_channel=provider_app.provider_channel, operation_product_type=provider_app.operation_product_type,
                                routing_range=search_info.routing_range, trip_type=search_info.trip_type, from_date=from_date, ret_date=ret_date,
                                from_airport_str=from_airport_str, to_airport_str=to_airport_str, from_airport=from_airport, to_airport=to_airport, segments=segments_str,
                                adult_price=flight_routing.adult_price, adult_tax=flight_routing.adult_tax,
                                child_price=flight_routing.child_price, child_tax=flight_routing.child_tax, adult_price_discount=adult_price_discount_str, routing_json=routing_json
                            )
                        }
                    )
                ret['data'] = data
                return TBResponse(ret)
            else:

                # 认为该情况为初始化页面，将所有provider进行回传
                if '*' in g.allow_providers:
                    provider_channels = ProviderAutoRepo.list_provider_channels()
                else:
                    provider_channels = ProviderAutoRepo.list_provider_channels(g.allow_providers)

                pl = []
                for p in provider_channels:
                    pl.append({'label': p, 'value': p})
                pl.append({'label': 'all', 'value': 'all'})
                return TBResponse({'data': {'provider_channel': 'ceair_web_2', 'adt_count': '1', 'chd_count': '0'}, 'options': {'provider_channel': pl}})

        except Exception as e:
            Logger().serror(e)
            return TBResponse(str(e), status=500)


manual_search_flight_view = ManualSearchFlight.as_view('manual_search_flight')
misc_app.add_url_rule('/manual_search_flight/',
                      view_func=manual_search_flight_view, methods=['GET', ])


class SmsReciever(MethodView):
    """
    短信接收接口
    接收短信
    :return:
    """

    @db_session
    def get(self):
        """
        ex  http://127.0.0.1:8888/sms_reciever?from_mobile=+86311332112&to_mobile=15216666555&message=123&receive_time=1367723813
        from_mobile 发送手机号码 支持各种格式 如果中间包含空格请滤掉，如果有+号等特殊符号，需要进行urlencode编码
        to_mobile  接收手机号码  支持各种格式 如果中间包含空格请滤掉
        message  发送信息，utf8格式urlencode编码
        receive_time 接收10位时间戳 1535556854

        """
        exception = ''
        try:
            from_mobile = request.args.get('from_mobile', '')
            to_mobile = request.args.get('to_mobile', '')
            message = convert_unicode(request.args.get('message', ''))
            receive_time = int(request.args.get('receive_time'))
            receive_time = datetime.datetime.fromtimestamp(receive_time)
            sms_device_id = request.args.get("device_id", '')
            SmsMessage(from_mobile=from_mobile, to_mobile=to_mobile, message=message, receive_time=receive_time,sms_device_id=sms_device_id)
            return_status = 'SUCCESS'
            ret = 'ok'
        except Exception as e:
            Logger().serror('sms receiver error')
            return_status = 'ERROR'
            exception = str(e)
            ret = str(e)

        if return_status == 'SUCCESS':
            status = 200
        else:
            status = 500


        TBG.tb_metrics.write(
            "FRAMEWORK.MOBILE_RECV_API",
            tags=dict(
                from_mobile=from_mobile,
                to_mobile=to_mobile,
                exception=exception,
                return_status=return_status,
                sms_device_id=sms_device_id

            ),
            fields=dict(
                count=1
            ))
        return Response(ret,status=status)
sms_reciever_view = SmsReciever.as_view('sms_reciever')
misc_app.add_url_rule('/sms_reciever',
                      view_func=sms_reciever_view, methods=['GET', ])


class SmsHeartbeat(MethodView):
    """
    短信心跳接口
    接收短信
    :return:
    """

    @db_session
    def get(self):
        sms_device_id = request.args.get("device_id", '')

        TBG.tb_metrics.write(
            "FRAMEWORK.MOBILE_HEARTBEAT",
            tags=dict(
                sms_device_id=sms_device_id
            ),
            fields=dict(
                count=1
            ))
        return Response('ok', 200)


sms_heartbeat_view = SmsHeartbeat.as_view('sms_heartbeat')
misc_app.add_url_rule('/sms_heartbeat',
                      view_func=sms_heartbeat_view, methods=['GET', ])


class FlightOrderManage(MethodView):
    """
    订单页面
    """

    @perm_check(perm_module='flight_order')
    @db_session
    def get(self):
        """
        "table_columns":["id","ota_name","ota_order_id","provider","provider_order_id","assoc_order_id","ota_order_status","provider_order_status","passengers","routing","segments","provider_price","ota_pay_price","ota_create_order_time","is_manual"],

        :return:
        """
        TB_REQUEST_ID = Random.gen_request_id()
        # 展示三十天内的数据

        # 根据权限组查询订单

        # order_list = select(o for o in FlightOrder if Time.days_before(3) < o.ota_create_order_time and o.provider ).order_by(desc(FlightOrder.id))
        order_list = select(o for o in FlightOrder if Time.days_before(3) < o.ota_create_order_time )
        if '*' not in g.allow_providers:
            order_list = order_list.filter(lambda o:o.provider in g.allow_providers)
        if '*' not in g.allow_otas:
            order_list = order_list.filter(lambda o: o.ota_name in g.allow_otas)
        order_list = order_list.order_by(desc(FlightOrder.id))

        bool_map = {
            None:'否',
            '':'否',
            1:'是',
            0:'否'

        }
        resp = []
        for o in order_list:
            paxs = []
            for pax in o.passengers:
                pax = "{p2fo_id},{pid},{name},{age_type},{gender},{mobile},{ticket_no}".format(p2fo_id=pax.id, pid=pax.used_card_no, name=pax.person.name, age_type=pax.person.age_type,
                                                                                               gender=pax.person.gender, mobile=pax.person.mobile, ticket_no=pax.ticket_no)
                paxs.append(pax)
            paxs_str = '<br />'.join(paxs)

            routing_str = "【{from_city}】-【{to_city}】，出发日期:{from_date}，返程日期:{ret_date}".format(from_city=o.from_city, to_city=o.to_city, from_date=o.from_date, ret_date=o.ret_date)
            segments = []
            if o.routing:
                for s in o.routing.from_segments:
                    seg_str = "去程：{flight_number}，{cabin_grade}舱{cabin} 【{dep_airport}】【{dep_terminal}】【{dep_time}】-【{arr_airport}】【{arr_terminal}】【{arr_time}】".format(dep_airport=s.dep_airport,
                                                                                                                                                                        dep_time=s.dep_time,
                                                                                                                                                                        dep_terminal=s.dep_terminal,
                                                                                                                                                                        arr_airport=s.arr_airport,
                                                                                                                                                                        arr_time=s.arr_time,
                                                                                                                                                                        arr_terminal=s.arr_terminal,
                                                                                                                                                                        flight_number=s.flight_number,
                                                                                                                                                                        cabin_grade=s.cabin_grade,
                                                                                                                                                                        cabin=s.cabin)
                    segments.append(seg_str)
            if o.routing:
                for s in o.routing.ret_segments:
                    seg_str = "返程：{flight_number}，{cabin_grade}舱{cabin} 【{dep_airport}】【{dep_terminal}】【{dep_time}】-【{arr_airport}】【{arr_terminal}】【{arr_time}】".format(dep_airport=s.dep_airport,
                                                                                                                                                                        dep_time=s.dep_time,
                                                                                                                                                                        dep_terminal=s.dep_terminal,
                                                                                                                                                                        arr_airport=s.arr_airport,
                                                                                                                                                                        arr_time=s.arr_time,
                                                                                                                                                                        arr_terminal=s.arr_terminal,
                                                                                                                                                                        flight_number=s.flight_number,
                                                                                                                                                                        cabin_grade=s.cabin_grade,
                                                                                                                                                                        cabin=s.cabin)
                    segments.append(seg_str)
            segments_str = '<br />'.join(segments)
            if o.ffp_account:
                username = o.ffp_account.username
                password = o.ffp_account.password
            else:
                username = ''
                password = ''

            if o.process_duration:
                process_duration = "%s(完成)" % Time.change_time(o.process_duration)
            else:
                process_duration =  "%s(未结束)" % Time.change_time((Time.curr_date_obj() - o.ota_create_order_time).total_seconds())

            order_record = {
                'id': o.id,
                'ota_name': o.ota_name,
                'ota_order_id': o.ota_order_id,
                'provider_channel': o.provider_channel,
                'providers_assoc_id':','.join([str(x.id) for x in o.sub_orders]),
                'assoc_order_id': o.assoc_order_id,
                'ota_order_status': {'value': o.ota_order_status.strip(), 'label': OTA_ORDER_STATUS[o.ota_order_status.strip()]},
                'providers_status': {'value': o.providers_status.strip(), 'label': PROVIDERS_STATUS[o.providers_status.strip()]['cn_desc']},
                'passengers': paxs_str,
                'routing': routing_str,
                'segments': segments_str,
                'providers_total_price': o.providers_total_price,
                'ota_pay_price': o.ota_pay_price,
                'is_manual':{'value':o.is_manual,'label':bool_map[o.is_manual]} ,
                'ota_create_order_time': str(o.ota_create_order_time),
                'ticket_nos': '',
                'username': username,
                'password': password,
                'comment': o.comment,
                "pnr_code": o.pnr_code,
                "process_duration": process_duration,
                'fo': '',
                'is_test_order':{'value':o.is_test_order,'label':bool_map[o.is_test_order]},
                'is_cabin_changed':{'value':o.is_cabin_changed,'label':bool_map[o.is_cabin_changed]},

            }
            resp.append(order_record)
        ota_order_status_list = []
        for k, v in OTA_ORDER_STATUS.iteritems():
            ota_order_status_list.append({'value': k.strip(), 'label': v})
        providers_status_list = []
        for k, v in PROVIDERS_STATUS.iteritems():
            # if v['is_display']:
            providers_status_list.append({'value': k.strip(), 'label': v['cn_desc']})
        bool_list = [{'value':1,'label':'是'},{'value':0,'label':'否'}]
        ret = {'data': resp, 'options': {'providers_status.value': providers_status_list, 'ota_order_status.value': ota_order_status_list,'is_test_order.value':bool_list,'is_manual.value':bool_list}}


        return TBResponse(ret)

    @perm_check(perm_module='flight_order')
    @db_session
    def put(self, order_id):
        """
        关联账号信息
        更新is_manual= 1
        更新供应商价格，解析并更新乘客票号
        更新状态：如果更新为 ISSUE_FINISH 则由系统完成票号回填后续操作，如果更新为 MANUAL_OPERATION 则系统不再介入
        增加人工备注栏
        增加替换功能，填写主订单ID即可将该ID下所有信息关联，同时放弃该账号原有信息
        :return:
        """
        TB_REQUEST_ID = Random.gen_request_id()
        req_body = request.get_json()
        req_body = req_body.get(str(order_id))

        providers_total_price = req_body.get('providers_total_price')

        comment = req_body.get('comment')
        pnr_code = req_body.get('pnr_code')
        providers_status = req_body.get('providers_status')
        ota_order_status = req_body.get('ota_order_status')
        ota_pay_price = req_body.get('ota_pay_price')
        is_test_order = req_body.get('is_test_order')
        replace_flight_order_id = req_body.get('replace_flight_order_id')
        Logger().sdebug('is_test_order %s'%is_test_order)
        flight_order = FlightOrder[order_id]

        if replace_flight_order_id:
            # 替换其他主订单

            # 查询是否存在该订单
            old_flight_order = FlightOrder.get(id=replace_flight_order_id)
            if old_flight_order:
                flight_order.contacts = old_flight_order.contacts
                flight_order.income_expense_details = old_flight_order.income_expense_details
                flight_order.routing = old_flight_order.routing
                sub_orders = old_flight_order.sub_orders
                flight_order.meta = old_flight_order.meta
                flight_order.ffp_account = old_flight_order.ffp_account
                old_flight_order.ota_order_status = 'REPLACED'

                for sub_order in sub_orders:
                    sub_pax_list = []
                    for pax in sub_order.passengers:
                        sub_pax_list = select(p for p in Person2FlightOrder if p.flight_order.id ==  flight_order.id and p.used_card_no == pax.used_card_no)
                    sub_order.passengers = sub_pax_list

                commit()
                flush()
                flight_order.sub_orders = old_flight_order.sub_orders
            else:
                return TBResponse('需要替换的订单不存在', status=500, json_ensure_ascii=False)

        ctime = Time.curr_date_obj()
        if providers_status:
            if flight_order.providers_status != providers_status:  # 如果状态不一样认为是状态更新，需要更新update_time
                flight_order.update_time = ctime
            if providers_status['value'] == 'ALL_SUCCESS' and flight_order.providers_status !=providers_status['value']:
                flight_order.process_duration = (ctime - flight_order.ota_create_order_time).seconds
                flight_order.all_finished_time = ctime
            flight_order.providers_status = providers_status['value']
        if ota_order_status:
            if flight_order.ota_order_status != ota_order_status:  # 如果状态不一样认为是状态更新，需要更新update_time
                flight_order.update_time = ctime
            flight_order.ota_order_status = ota_order_status['value']
        if providers_total_price:
            flight_order.providers_total_price = int(providers_total_price)
        if ota_pay_price:
            flight_order.ota_pay_price = float(ota_pay_price)
        if is_test_order:
            flight_order.is_test_order = is_test_order['value']

        if comment:
            flight_order.comment = convert_unicode(comment)

        if pnr_code:
            flight_order.pnr_code = pnr_code
        flight_order.is_manual = 1
        return TBResponse({'ret_code': 1})

    @perm_check(perm_module='flight_order')
    @db_session
    def delete(self, order_id):
        """
        关联账号信息
        更新is_manual= 1
        更新供应商价格，解析并更新乘客票号
        更新状态：如果更新为 ISSUE_FINISH 则由系统完成票号回填后续操作，如果更新为 MANUAL_OPERATION 则系统不再介入
        增加人工备注栏
        :return:
        """
        TB_REQUEST_ID = Random.gen_request_id()
        try:
            FlightOrder[int(order_id)].delete()
            return TBResponse({'ret_code': 1})
        except Exception as e:
            Logger().error(e)
            return TBResponse(str(e), status=500, json_ensure_ascii=False)



flight_order_manage_view = FlightOrderManage.as_view('flight_order_manage')
misc_app.add_url_rule('/flight_order_manage/',
                      view_func=flight_order_manage_view, methods=['GET', 'POST'])
misc_app.add_url_rule('/flight_order_manage/<int:order_id>', view_func=flight_order_manage_view,
                      methods=['PUT','DELETE'])


class SubOrderManage(MethodView):
    """
    子订单页面
    """

    @perm_check(perm_module='sub_order')
    @db_session
    def get(self):
        """
        "table_columns":["id","ota_name","ota_order_id","provider","provider_order_id","assoc_order_id","ota_order_status","provider_order_status","passengers","routing","segments","provider_price","ota_pay_price","ota_create_order_time","is_manual"],

        :return:
        """
        TB_REQUEST_ID = Random.gen_request_id()
        # 展示三十天内的数据

        # order_list = select(o for o in SubOrder if Time.days_before(3) < o.create_time).order_by(desc(SubOrder.id))
        order_list = select(o for o in SubOrder if Time.days_before(3) < o.create_time)
        if '*' not in g.allow_providers:
            order_list = order_list.filter(lambda o:o.provider in g.allow_providers)
        if '*' not in g.allow_otas:
            order_list = order_list.filter(lambda o: o.flight_order.ota_name in g.allow_otas)
        order_list = order_list.order_by(desc(SubOrder.id))
        bool_map = {
            None:'否',
            '':'否',
            1:'是',
            0:'否'

        }
        resp = []
        for o in order_list:
            paxs = []
            for pax in o.passengers:
                pax = "{p2fo_id},{pid},{name},{age_type},{gender},{mobile},{ticket_no}".format(p2fo_id=pax.id, pid=pax.used_card_no, name=pax.person.name, age_type=pax.person.age_type,
                                                                                               gender=pax.person.gender, mobile=pax.person.mobile, ticket_no=pax.ticket_no)
                paxs.append(pax)
            paxs_str = '<br />'.join(paxs)

            routing_str = "【{from_city}】-【{to_city}】，出发日期:{from_date}，返程日期:{ret_date}".format(from_city=o.from_city, to_city=o.to_city, from_date=o.from_date, ret_date=o.ret_date)
            segments = []
            if o.routing:
                for s in o.routing.from_segments:
                    seg_str = "去程：{flight_number}，{cabin_grade}舱{cabin} 【{dep_airport}】【{dep_terminal}】【{dep_time}】-【{arr_airport}】【{arr_terminal}】【{arr_time}】".format(dep_airport=s.dep_airport,
                                                                                                                                                                        dep_time=s.dep_time,
                                                                                                                                                                        dep_terminal=s.dep_terminal,
                                                                                                                                                                        arr_airport=s.arr_airport,
                                                                                                                                                                        arr_time=s.arr_time,
                                                                                                                                                                        arr_terminal=s.arr_terminal,
                                                                                                                                                                        flight_number=s.flight_number,
                                                                                                                                                                        cabin_grade=s.cabin_grade,
                                                                                                                                                                        cabin=s.cabin)
                    segments.append(seg_str)
            if o.routing:
                for s in o.routing.ret_segments:
                    seg_str = "返程：{flight_number}，{cabin_grade}舱{cabin} 【{dep_airport}】【{dep_terminal}】【{dep_time}】-【{arr_airport}】【{arr_terminal}】【{arr_time}】".format(dep_airport=s.dep_airport,
                                                                                                                                                                        dep_time=s.dep_time,
                                                                                                                                                                        dep_terminal=s.dep_terminal,
                                                                                                                                                                        arr_airport=s.arr_airport,
                                                                                                                                                                        arr_time=s.arr_time,
                                                                                                                                                                        arr_terminal=s.arr_terminal,
                                                                                                                                                                        flight_number=s.flight_number,
                                                                                                                                                                        cabin_grade=s.cabin_grade,
                                                                                                                                                                        cabin=s.cabin)
                    segments.append(seg_str)
            segments_str = '<br />'.join(segments)
            if o.ffp_account:
                username = o.ffp_account.username
                password = o.ffp_account.password
                is_modified_card_no = o.ffp_account.is_modified_card_no
            else:
                username = ''
                password = ''
                is_modified_card_no = 0

            if o.process_duration:
                process_duration = "%s(完成)" % Time.change_time(o.process_duration)
            else:
                process_duration =  "%s(未结束)" % Time.change_time((Time.curr_date_obj() - o.create_time).total_seconds())

            rk_info = RoutingKey.unserialize(routing_key=o.routing.routing_key_detail)
            if o.raw_routing:
                raw_rk_info = RoutingKey.unserialize(routing_key=o.raw_routing.routing_key_detail)
                if o.raw_routing == o.routing:
                    cabin_status = '原舱 %s' % rk_info['cabin']
                else:

                    cabin_status = '%s -> %s' % (raw_rk_info['cabin'],rk_info['cabin'])
            else:
                if o.routing:
                    cabin_status = '原舱 %s' % rk_info['cabin']
                else:
                    cabin_status = '无信息'
            order_record = {
                'id': o.id,
                'flight_order_id':o.flight_order.id,
                'ota_order_id':o.flight_order.ota_order_id,
                'provider_channel': o.provider_channel,
                'provider_order_status': {'value': o.provider_order_status.strip(), 'label': PROVIDER_ORDER_STATUS[o.provider_order_status.strip()]['cn_desc']},
                'passengers': paxs_str,
                'routing': routing_str,
                'segments': segments_str,
                'provider_price': o.provider_price,
                'is_manual':{'value':o.is_manual,'label':bool_map[o.is_manual]} ,
                'ticket_nos': '',
                'username': username,
                'password': password,
                'comment': o.comment,
                "pnr_code": o.pnr_code,
                "create_time":str(o.create_time),
                "process_duration":process_duration,
                ""
                "is_modified_card_no":{'value':is_modified_card_no,'label':bool_map[is_modified_card_no]},
                'fo': '',
                'cabin_status': cabin_status,
                'provider_order_id': o.provider_order_id
            }
            resp.append(order_record)

        provider_order_status_list = []
        for k, v in PROVIDER_ORDER_STATUS.iteritems():
            # if v['is_display']:
            provider_order_status_list.append({'value': k.strip(), 'label': v['cn_desc']})
        bool_list = [{'value':1,'label':'是'},{'value':0,'label':'否'}]
        ret = {'data': resp, 'options': {'provider_order_status.value': provider_order_status_list,'is_manual.value':bool_list,'is_modified_card_no.value':bool_list}}


        return TBResponse(ret)

    @perm_check(perm_module='sub_order')
    @db_session
    def put(self, order_id):
        """
        关联账号信息
        更新is_manual= 1
        更新供应商价格，解析并更新乘客票号
        更新状态：如果更新为 ISSUE_FINISH 则由系统完成票号回填后续操作，如果更新为 MANUAL_OPERATION 则系统不再介入
        增加人工备注栏
        :return:
        """
        TB_REQUEST_ID = Random.gen_request_id()
        req_body = request.get_json()
        req_body = req_body.get(str(order_id))
        ticket_nos = req_body.get('ticket_nos')
        provider_price = req_body.get('provider_price')
        provider_order_id = req_body.get('provider_order_id')
        password = req_body.get('password')
        username = req_body.get('username')
        comment = req_body.get('comment')
        pnr_code = req_body.get('pnr_code')
        provider_order_status = req_body.get('provider_order_status')
        flight_order = SubOrder[order_id]
        # 解析票号
        if ticket_nos:
            ticket_no_list = ticket_nos.split(';')
            for t in ticket_no_list:
                __ = t.split(':')
                p2fo_id = int(__[0])
                ticket_no = __[1]
                Person2FlightOrder[p2fo_id].ticket_no = ticket_no

        if provider_order_status:
            ctime = Time.curr_date_obj()
            if flight_order.provider_order_status != provider_order_status:  # 如果状态不一样认为是状态更新，需要更新update_time
                flight_order.update_time = ctime
            if provider_order_status['value'] == 'ISSUE_SUCCESS' and flight_order.provider_order_status != provider_order_status['value']:
                flight_order.process_duration = (ctime - flight_order.create_time).seconds
                flight_order.issue_success_time = ctime
            flight_order.provider_order_status = provider_order_status['value']
        if provider_price:
            flight_order.provider_price = int(provider_price)
        if provider_order_id:
            flight_order.provider_order_id = provider_order_id

        if flight_order.ffp_account:
            if password:
                flight_order.ffp_account.password = password
            if username:
                flight_order.ffp_account.username = username
        else:
            ffp_account = FFPAccount()
            if password:
                ffp_account.password = password
            if username:
                ffp_account.username = username
            flight_order.ffp_account = ffp_account
        if comment:
            flight_order.comment = convert_unicode(comment)

        if pnr_code:
            flight_order.pnr_code = pnr_code
        flight_order.is_manual = 1
        return TBResponse({'ret_code': 1})

    @perm_check(perm_module='sub_order')
    @db_session
    def delete(self, order_id):
        """
        删除
        :return:
        """
        TB_REQUEST_ID = Random.gen_request_id()
        try:
            SubOrder[int(order_id)].delete()
            return TBResponse({'ret_code': 1})
        except Exception as e:
            Logger().error(e)
            return TBResponse(str(e), status=500, json_ensure_ascii=False)

sub_order_manage_view = SubOrderManage.as_view('sub_order_manage')
misc_app.add_url_rule('/sub_order_manage/',
                      view_func=sub_order_manage_view, methods=['GET', 'POST'])
misc_app.add_url_rule('/sub_order_manage/<int:order_id>', view_func=sub_order_manage_view,
                      methods=['PUT','DELETE'])




"""
========================================== 元宝接口 ========================================
"""

class ManualCreateSubOrder(MethodView):
    """
    人工创建子订单
     {'flight_order_id':11,'pax_id_list':[1,2,3,4],'routing_key':'xxxxxxxx'}
    """
    @perm_check(perm_module='manual_create_sub_order')
    @db_session
    def post(self):

        try:
            TB_REQUEST_ID = Random.gen_request_id()
            req_body = request.get_json()

            flight_order_id = req_body['flight_order_id']
            pax_id_list = req_body['pax_id_list']
            routing_key = req_body['routing_key']

            #乘机人是否在处理订单列表检查
            p2fo_list = []
            adt_count = 0
            chd_count = 0
            for pax_id in pax_id_list:
                p2fo = Person2FlightOrder[pax_id]
                if p2fo.person.age_type == 'ADT':
                    adt_count +=1
                elif p2fo.person.age_type in ['CHD','INF']:
                    chd_count +=1
                else:
                    adt_count +=1
                p2fo_list.append(p2fo)
                # if p2fo.sub_order and p2fo.sub_order.provider_order_status != 'MANUAL_CANCEL':
                #     return TBResponse('用户ID %s 目前依然存在于某未取消的子订单' % pax_id, status=500, json_ensure_ascii=False)
                if p2fo.flight_order.id != flight_order_id:
                    return TBResponse('用户ID %s 不属于主订单%s' % (pax_id,flight_order_id), status=500, json_ensure_ascii=False)

            # 获取联系人
            flight_order = FlightOrder[flight_order_id]
            contacts = flight_order.contacts

            rk_info = RoutingKey.unserialize(routing_key,is_encrypted=True)
            provider_app = ProviderAutoRepo.select(rk_info['provider_channel'])
            un_key = RoutingKey.trans_un_key(rk_info,is_unserialized=True)
            # 生成子订单
            order_info = OrderInfo()
            self.order_info.from_date = rk_info['from_date']
            self.order_info.from_airport = rk_info['search_from_airport']
            self.order_info.to_airport = rk_info['search_to_airport']
            self.order_info.trip_type = rk_info['trip_type']
            order_info.adt_count = adt_count
            order_info.chd_count = chd_count
            order_info.inf_count = 0
            order_info.provider = provider_app.provider
            order_info.provider_channel = provider_app.provider_channel
            order_info.operation_product_type = provider_app.operation_product_type
            order_info.operation_product_mode = provider_app.operation_product_mode
            order_info.pnr_code = 'AAAAAA'
            order_info.attr_competion()

            # 搜索机票

            provider_app.flight_search(search_info=order_info)

            selected_routing = None
            for flight_routing in order_info.assoc_search_routings:
                fr_un_key = RoutingKey.trans_un_key(flight_routing.routing_key_detail)
                if fr_un_key == un_key:
                    selected_routing = flight_routing.save(lazy_flush=False)

            if selected_routing:
                routing_id = selected_routing.id
                sub_order_info = SubOrderInfo(**order_info)
                sub_order = sub_order_info.save(lazy_flush=False)
                sub_order.passengers = p2fo_list
                sub_order.routing = routing_id
                sub_order.raw_routing = routing_id
                sub_order.flight_order = flight_order_id
                sub_order.contacts = contacts
                sub_order.provider_order_status = 'ORDER_INIT'
                # 对舱位进行修正
                CabinReviseControl.add(un_key, len(pax_id_list))
                return TBResponse({'ret_code': 1})
            else:
                return TBResponse('没有搜索到航班', status=500, json_ensure_ascii=False)

        except Exception as e:
            Logger().error(e)
            return TBResponse(str(e), status=500, json_ensure_ascii=False)


manual_create_sub_order_view = ManualCreateSubOrder.as_view('manual_create_sub_order')
misc_app.add_url_rule('/manual_create_sub_order/', view_func=manual_create_sub_order_view, methods=['POST'])


class OrderDetail(MethodView):
    """
    订单详情页面
    """
    @perm_check(perm_module='order_details')
    @db_session
    def get(self, order_id):
        order_id = int(order_id)
        if order_id:
            TB_REQUEST_ID = Random.gen_request_id()
            order_list = select(o for o in FlightOrder if order_id == o.id)

            # 对特定的group做限制
            use_info = TBG.global_config['USER_LIST'][g.user]
            group = use_info['group']
            if group in ['yidayiyou', 'yida', 'yiyou']:
                order_list = order_list.filter(lambda o: o.ota_extra_group == group)
            else:
                if '*' not in g.allow_providers:
                    order_list = order_list.filter(lambda o: o.provider in g.allow_providers)
                if '*' not in g.allow_otas:
                    order_list = order_list.filter(lambda o: o.ota_name in g.allow_otas)

            order_list = order_list.order_by(desc(FlightOrder.id))
            flight_list = {}
            for o in order_list:
                sub_order_list = []
                peoples = []
                # 获取routing信息
                assoc_list = []
                rsno_lists = []
                verify_count = 0
                order_routing_id = ''
                rk = ''
                if o.routing:
                    order_routing_id = o.routing.request_id

                    rk = o.routing.routing_key_detail
                    rk_detail = RoutingKey.unserialize(rk)
                    rsno = rk_detail['rsno'] if rk_detail else ''
                    if rsno:
                        rsno_list = select(ver for ver in OTAVerify if rsno == ver.rsno)
                        for s in rsno_list:
                            rsno_datail = {'primary_id': s.id, 'return_status': s.return_status}
                            rsno_lists.append(rsno_datail)
                        verify_count = len(rsno_lists)

                for pax in o.passengers:
                    pax = {'p2fo_id': pax.id, 'last_name': pax.person.last_name, 'first_name': pax.person.first_name,
                           'used_card_type': pax.used_card_type,
                           'birthdate': str(pax.person.birthdate), 'card_expired': pax.person.card_expired,
                           'nationality': pax.person.nationality,
                           'pid': pax.used_card_no, 'name': pax.person.name, 'age_type': pax.person.age_type,
                           'gender': pax.person.gender,
                           'mobile': pax.person.mobile, 'ticket_no': pax.ticket_no,
                           'card_issue_place': pax.person.card_issue_place,
                           'pnr': pax.pnr}
                    peoples.append(pax)
                for j in o.sub_orders:
                    paxs = []
                    for pax in j.passengers:
                        pax = {'p2fo_id': pax.id, 'last_name': pax.person.last_name, 'first_name': pax.person.first_name,'used_card_type': pax.used_card_type,
                               'birthdate': str(pax.person.birthdate), 'card_expired': pax.person.card_expired, 'nationality': pax.person.nationality,
                               'pid': pax.used_card_no, 'name': pax.person.name, 'age_type': pax.person.age_type, 'gender': pax.person.gender,
                               'mobile': pax.person.mobile, 'ticket_no': pax.ticket_no, 'card_issue_place': pax.person.card_issue_place,
                               'pnr': pax.pnr}
                        paxs.append(pax)
                    paxs_str = paxs
                    segments = []
                    ret_segments = []
                    sub_routing_rid = ''
                    sub_rk_detail = ''
                    sub_primary_id = ''
                    if j.routing:
                        sub_routing_rid = j.routing.request_id
                        sub_rk_detail = j.routing.routing_key_detail
                        sub_primary_id = j.routing.id
                        for s in j.routing.from_segments:
                            seg_str = {'dep_airport': s.dep_airport, 'dep_time': str(s.dep_time), 'arr_terminal': s.arr_terminal, 'dep_terminal': s.dep_terminal,
                                       'arr_airport': s.arr_airport, 'arr_time': str(s.arr_time), 'flight_number': s.flight_number, 'cabin_grade': s.cabin_grade,
                                       'cabin': s.cabin, 'baggage_info': s.baggage_info}
                            segments.append(seg_str)
                    if j.routing:
                        for s in j.routing.ret_segments:
                            ret_segment = {'dep_airport': s.dep_airport, 'dep_time': str(s.dep_time), 'arr_terminal': s.arr_terminal, 'dep_terminal': s.dep_terminal,
                                       'arr_airport': s.arr_airport, 'arr_time': str(s.arr_time), 'flight_number': s.flight_number, 'cabin_grade': s.cabin_grade,
                                       'cabin': s.cabin, 'baggage_info': s.baggage_info}
                            ret_segments.append(ret_segment)
                    if j.ffp_account:
                        ffp_account = {'username': j.ffp_account.username, 'password': j.ffp_account.password, 'provider': j.ffp_account.provider,
                                       'is_modified_card_no': j.ffp_account.is_modified_card_no}
                    else:
                        ffp_account = {'username':'', 'password': '', 'provider': '', 'is_modified_card_no': ''}
                    if j.process_duration:
                        order_status = True
                        order_time = j.process_duration
                    else:
                        order_status = False
                        order_time = (Time.curr_date_obj() - j.update_time).total_seconds()

                    rk_info = RoutingKey.unserialize(routing_key=o.routing.routing_key_detail)
                    if rk_info:
                        if j.raw_routing:
                            raw_rk_info = RoutingKey.unserialize(routing_key=j.raw_routing.routing_key_detail)
                            if j.raw_routing == j.routing:
                                cabin_status = False
                                raw_cabin = raw_rk_info.get('cabin', '')
                                change_cabin = ''
                            else:
                                cabin_status = True
                                raw_cabin = raw_rk_info.get('cabin', '')
                                change_cabin = rk_info.get('cabin', '')
                        else:
                            cabin_status = False
                            raw_cabin = rk_info.get('cabin', '')
                            change_cabin = ''
                    else:
                        cabin_status = False
                        raw_cabin = ''
                        change_cabin = ''
                    payment = {'pay_mount': '', 'pay_time': '', 'pay_channle': '', 'account_name': '', 'account_id': '', 'out_trade_no': j.out_trade_no}
                    if j.income_expense_details:
                        for pay_detail in j.income_expense_details:
                            if pay_detail.expense_source:
                                payment = {'pay_mount': pay_detail.pay_amount, 'pay_time': str(pay_detail.pay_time), 'pay_channel': pay_detail.pay_channel,
                                           'out_trade_no': j.out_trade_no, 'account_name': pay_detail.expense_source.source_name,
                                           'account_id': pay_detail.expense_source.credit_card_idno if pay_detail.expense_source.credit_card_idno else pay_detail.expense_source.pay_account}
                    sub_single = {'provider_order_id': j.provider_order_id, 'out_trade_no': j.out_trade_no, 'payment': payment, 'sub_order_id': j.id,
                                  'create_time': str(j.create_time), 'is_''provider_order_id': j.provider_order_id, 'provider': j.provider,
                                  'provider_channel': j.provider_channel, 'provider_price': j.provider_price,
                                  'provider_order_status': {'value': j.provider_order_status.strip(), 'label': PROVIDER_ORDER_STATUS[j.provider_order_status.strip()]['cn_desc']},
                                  'passengers': paxs_str, 'routings': {'adult_price': j.routing.adult_price,'adult_price_discount': j.routing.adult_price_discount,
                                                                       'adult_full_price': j.routing.adult_full_price,'adult_tax': j.routing.adult_tax,
                                                                       'child_publish_price': j.routing.child_publish_price,'child_price': j.routing.child_tax,
                                                                       'fromSegments': segments, 'retSegments': ret_segments},
                                      'ffp_account': ffp_account, 'sub_order_status': {'order_status': order_status, 'order_time': str(order_time)},
                                  'order_cabin': {'cabin_status': cabin_status, 'raw_cabin': raw_cabin, 'change_cabin': change_cabin},
                                  'sub_order_routing': {'request_id': sub_routing_rid, 'rk': sub_rk_detail, 'primary_id': sub_primary_id}}
                    sub_order_list.append(sub_single)
                flight_list = {'comment': o.comment, 'providers_status': {'value': o.providers_status.strip(), 'label': PROVIDERS_STATUS[o.providers_status.strip()]['cn_desc']},'flight_order': o.id,
                               'from_country': o.from_country, 'to_country': o.to_country, 'from_date': str(o.from_date), 'ota_create_order_time': str(o.ota_create_order_time), 'ota_name': o.ota_name,
                               'ota_order_status':{'value': o.ota_order_status.strip(), 'label': OTA_ORDER_STATUS[o.ota_order_status.strip()]},
                               'ota_pay_price': o.ota_pay_price, 'is_test_order': o.is_test_order, 'is_manual': o.is_manual, 'from_city': o.from_city, 'to_city': o.to_city, 'ota_order_id': o.ota_order_id,
                               'ota_pay_time': str(o.ota_pay_time),'provider_total_price': o.providers_total_price, 'provider': o.provider, 'ota_adult_price': o.ota_adult_price,
                               'ota_child_price': o.ota_child_price, 'is_cabin_changed': o.is_cabin_changed, 'pnr_code': o.pnr_code, 'sub_order_list': sub_order_list, 'ota_extra_name': o.ota_extra_name,'ota_extra_group':o.ota_extra_group,
                               'passengers': peoples, 'flight_order_routing': {'request_id': order_routing_id, 'assoc_list':assoc_list, 'rsno_lists': rsno_lists, 'verify_count': verify_count, 'rk': rk},
                               'trip_type': o.trip_type, 'ota_product_code': o.ota_product_code}
            resp = {'data': flight_list}
        else:
            resp = {'error': 'order_id不存在'}
        Logger().info('{ota_name}==========='.format(ota_name=resp))
        return TBResponse(resp)


order_detail_view = OrderDetail.as_view('order_details')
misc_app.add_url_rule('/order_detail/<int:order_id>/', view_func=order_detail_view, methods=['GET'])


class OrderList(MethodView):
    """
    订单list
    """
    @perm_check(perm_module='order_list')
    @db_session
    def get(self):
        flight_all_list = []
        TB_REQUEST_ID = Random.gen_request_id()
        list_status = request.args.get('list_status', '')
        get_list_date = request.args.get('ota_list_date', '')
        if get_list_date:
            date_range = int(get_list_date)
        else:
            date_range = 7

        if list_status:
            if list_status == 'all':
                order_list = select(o for o in FlightOrder if Time.days_before(date_range) < o.ota_create_order_time and o.is_test_order != 1)
            elif list_status == 'all_success':
                order_list = select(o for o in FlightOrder if Time.days_before(date_range) < o.ota_create_order_time and o.is_test_order != 1 and (o.providers_status == 'ALL_SUCCESS' or o.providers_status == 'MANUAL_ISSUE' or o.providers_status == 'BACKFILL_SUCCESS' or o.providers_status == 'MANUAL_RERUND' or o.providers_status == 'MANUAL_CHANGE'))
            elif list_status == 'all_init':
                order_list = select(o for o in FlightOrder if Time.days_before(date_range) < o.ota_create_order_time and o.is_test_order != 1 and o.ota_order_status != 'CANCEL' and o.ota_order_status != 'ISSUE_FAIL' and o.ota_order_status != 'ISSUE_FAIL' and o.ota_order_status != 'REFUND' and o.ota_order_status != 'ISSUE_FINISH' and o.ota_order_status != 'TIMEOUT' and o.ota_order_status != 'MANUAL_ISSUE' and o.ota_order_status != 'REPLACED' and o.ota_order_status != 'CHANGE' and o.ota_order_status != 'TAKE_SEAT_FAILED')
            elif list_status == 'no_success':
                order_list = select(o for o in FlightOrder if Time.days_before(date_range) < o.ota_create_order_time and o.is_test_order != 1 and (o.ota_order_status == 'CANCEL' or o.ota_order_status == 'ISSUE_FAIL' or o.ota_order_status == 'TAKE_SEAT_FAILED'))
            elif list_status == 'refund':
                order_list = select(o for o in FlightOrder if Time.days_before(date_range) < o.update_time and (o.providers_status == 'MANUAL_RERUND' or o.ota_order_status == 'REFUND' or o.providers_status == 'MANUAL_CHANGE' or o.providers_status == 'AFTER_SALES_PROCESSING'))
            else:
                order_list = select(o for o in FlightOrder if Time.days_before(date_range) < o.ota_create_order_time)
        else:
            order_list = select(o for o in FlightOrder if Time.days_before(date_range) < o.ota_create_order_time and o.is_test_order != 1)

        # 对特定的group做限制
        use_info = TBG.global_config['USER_LIST'][g.user]
        group = use_info['group']
        if group in ['yidayiyou', 'yida', 'yiyou']:
            order_list = order_list.filter(lambda o: o.ota_extra_group == group)
        else:
            if '*' not in g.allow_providers:
                order_list = order_list.filter(lambda o: o.provider in g.allow_providers)
            if '*' not in g.allow_otas:
                order_list = order_list.filter(lambda o: o.ota_name in g.allow_otas)

        order_list = order_list.order_by(desc(FlightOrder.id))

        # 获取近3天主订单id
        for o in order_list:
            sub_order_lists = []
            if o.sub_orders:
                for j in o.sub_orders:
                    sub_order = {'sub_id': j.id, 'provider_order_status': {'value': j.provider_order_status.strip(), 'label': PROVIDER_ORDER_STATUS[j.provider_order_status.strip()]['cn_desc']},
                                 'provider_channel': j.provider_channel, 'provider_price': j.provider_price,
                                 'create_time': str(j.create_time)}
                    sub_order_lists.append(sub_order)
            if o.process_duration:
                flight_status = True
                process_duration = o.process_duration
            else:
                flight_status = False
                process_duration = (Time.curr_date_obj() - o.ota_create_order_time).total_seconds()
            if o.ffp_account:
                ffp_account = {'username': o.ffp_account.username, 'password': o.ffp_account.password,
                               'provider': o.ffp_account.provider,
                               'is_modified_card_no': o.ffp_account.is_modified_card_no}
            else:
                ffp_account = {'username': '', 'password': '', 'provider': '', 'is_modified_card_no': 0}
            from_segments = []
            if o.routing:
                for s in o.routing.from_segments:
                    seg_str = {'dep_airport': s.dep_airport, 'dep_time': str(s.dep_time),
                               'dep_terminal': s.dep_terminal, 'arr_terminal': s.arr_terminal,
                               'arr_airport': s.arr_airport, 'arr_time': str(s.arr_time),
                               'flight_number': s.flight_number, 'cabin_grade': s.cabin_grade, 'cabin': s.cabin}
                    from_segments.append(seg_str)
            if o.routing:
                ret_segments = []
            paxs = []
            for pax in o.passengers:
                pax = {'p2fo_id': pax.id, 'pid': pax.used_card_no, 'name': pax.person.name, 'age_type': pax.person.age_type, 'gender': pax.person.gender, 'mobile': pax.person.mobile, 'ticket_no': pax.ticket_no}
                paxs.append(pax)
            paxs_str = paxs
            flight_list = {'comment': o.comment, 'providers_status': {'value': o.providers_status.strip(), 'label': PROVIDERS_STATUS[o.providers_status.strip()]['cn_desc']},
                           'from_country': o.from_country, 'to_country': o.to_country, 'from_date': str(o.from_date), 'flight_order': o.id,
                           'ota_create_order_time': str(o.ota_create_order_time), 'ota_name': o.ota_name,
                           'ota_order_status': {'value': o.ota_order_status.strip(),'label': OTA_ORDER_STATUS[o.ota_order_status.strip()]},
                           'ota_pay_price': o.ota_pay_price, 'is_test_order': o.is_test_order, 'is_manual': o.is_manual,
                           'from_city': o.from_city, 'to_city': o.to_city, 'ota_order_id': o.ota_order_id,
                           'ota_pay_time': str(o.ota_pay_time), 'provider_total_price': o.providers_total_price,
                           'provider': o.provider, 'ota_adult_price': o.ota_adult_price,
                           'ota_child_price': o.ota_child_price, 'is_cabin_changed': o.is_cabin_changed, 'from_segments': from_segments, 'ret_segments': ret_segments,
                           'ffp_account': ffp_account, 'is_flightorder_success': {'flight_status': flight_status, 'process_duration': process_duration},
                           'passengers': paxs_str, 'pnr_code': o.pnr_code, 'provider_channel': o.provider_channel, 'ota_extra_name': o.ota_extra_name,'ota_extra_group':o.ota_extra_group,
                           'sub_order_lists': sub_order_lists, 'trip_type': o.trip_type, 'ota_product_code': o.ota_product_code
                           }

            flight_all_list.append(flight_list)

        resp = {'data': flight_all_list}
        Logger().info('{ota_name}==========='.format(ota_name=resp))
        return TBResponse(resp)

    # 修改主状态
    @perm_check(perm_module='order_modify')
    @db_session
    def post(self, flight_id):
        TB_REQUEST_ID = Random.gen_request_id()
        req_body = request.get_json()
        providers_status = req_body.get('provider_status')
        ota_order_status = req_body.get('ota_order_status')
        ctime = Time.curr_date_obj()
        flight_order = FlightOrder[flight_id]
        if providers_status:
            if flight_order.providers_status != providers_status:  # 如果状态不一样认为是状态更新，需要更新update_time
                flight_order.update_time = ctime
            if providers_status == 'ALL_SUCCESS' and flight_order.providers_status != providers_status:
                flight_order.process_duration = (ctime - flight_order.ota_create_order_time).seconds
                flight_order.all_finished_time = ctime
            flight_order.providers_status = providers_status
        if ota_order_status:
            if flight_order.ota_order_status != ota_order_status:  # 如果状态不一样认为是状态更新，需要更新update_time
                flight_order.update_time = ctime
            flight_order.ota_order_status = ota_order_status
        flight_order.is_manual = 1
        return TBResponse({'ret_code': 1})

    # 修改主订单价格
    @perm_check(perm_module='order_modify')
    @db_session
    def put(self, flight_id):
        TB_REQUEST_ID = Random.gen_request_id()
        req_body = request.get_json()
        new_price = req_body.get('new_price')
        flight_order = FlightOrder[flight_id]
        if new_price:
            flight_order.providers_total_price = new_price
            resp = {'ret_code': 1}
        else:
            resp = {'ret_code': 2, 'error': 'new_price没有值或不存在'}
        return TBResponse(resp)


order_list_view = OrderList.as_view('order_list')
misc_app.add_url_rule('/order_list/', view_func=order_list_view, methods=['GET'])
misc_app.add_url_rule('/modify_flight_status/<int:flight_id>/', view_func=order_list_view, methods=['POST'])
misc_app.add_url_rule('/modify_flight_price/<int:flight_id>/', view_func=order_list_view, methods=['PUT'])


class ModifyTicketNo(MethodView):
    """
    修改票号
    """
    @perm_check(perm_module='order_modify')
    @db_session
    def get(self, p2fo_id):
        TB_REQUEST_ID = Random.gen_request_id()

        ticket_no = request.args.get('ticket_no', '')
        person_ticket = Person2FlightOrder[p2fo_id]
        if ticket_no:
            person_ticket.ticket_no = ticket_no
            resp = {'ret_code': 1}
        else:
            resp = {'ret_code': 0, 'error': 'p2fo_idb没有值'}
        return TBResponse(resp)


modify_ticket_view = ModifyTicketNo.as_view('modifyticket')
misc_app.add_url_rule('/modify_ticket/<int:p2fo_id>/', view_func=modify_ticket_view, methods=['get'])


class ModifySubOrder(MethodView):
    """
    修改主订单，子订单状态
    """
    @perm_check(perm_module='order_modify')
    @db_session
    def get(self, sub_order_id):
        """
         修改子订单状态
        """
        TB_REQUEST_ID = Random.gen_request_id()

        provider_order_status = request.args.get('order_status', '')
        flight_order = SubOrder[sub_order_id]
        ctime = Time.curr_date_obj()
        if provider_order_status:
            if flight_order.provider_order_status != provider_order_status and provider_order_status != 'SET_AUTOPAY':  # 如果状态不一样认为是状态更新，需要更新update_time
                flight_order.update_time = ctime
            if provider_order_status == 'ISSUE_SUCCESS' and flight_order.provider_order_status != provider_order_status:
                flight_order.process_duration = (Time.curr_date_obj() - flight_order.create_time).seconds
                flight_order.issue_success_time = Time.curr_date_obj()
            flight_order.provider_order_status = provider_order_status
            resp = {'ret_code': 1}
        else:
            resp = {'ret_code': 0, 'error': 'order_status没有参数'}
        flight_order.is_manual = 1
        return TBResponse(resp)

    # 修改子订单所有信息
    @perm_check(perm_module='order_modify')
    @db_session
    def put(self, sub_order_id):
        TB_REQUEST_ID = Random.gen_request_id()
        req_body = request.get_json()
        req_body = req_body.get(str(sub_order_id))
        sub_order = SubOrder[sub_order_id]
        try:
            for key, value in req_body.items():
                setattr(sub_order, key, value)
        except Exception as e:
            return e
        resp = {'ret_code': 1}
        return TBResponse(resp)


modify_suborder_view = ModifySubOrder.as_view('modifysuborder')
misc_app.add_url_rule('/modify_provider_order_status/<int:sub_order_id>/', view_func=modify_suborder_view, methods=['get', 'PUT'])


class GetBillList(MethodView):
    """
    返回账单信息
    """
    @perm_check(perm_module='flight_bill')
    @db_session

    def get(self):
        TB_REQUEST_ID = Random.gen_request_id()
        get_list_date = request.args.get('ota_list_date', '')
        if get_list_date:
            date_range = int(get_list_date)
        else:
            date_range = 7
        flight_lists = select(o for o in FlightOrder if Time.days_before(date_range) < o.ota_create_order_time and o.is_test_order != 1
                             and (o.providers_status == 'ALL_SUCCESS' or o.providers_status == 'MANUAL_ISSUE' or o.providers_status == 'BACKFILL_SUCCESS'))
        if flight_lists:
            bill_lists = []
            for flight_list in flight_lists:
                flight_id = flight_list.id
                ota_create_order_time = str(flight_list.ota_create_order_time)
                ota_name = flight_list.ota_name
                ota_order_id = flight_list.ota_order_id
                provider_channel = flight_list.provider_channel
                from_date = str(flight_list.from_date)
                ota_extra_name = flight_list.ota_extra_name
                ota_extra_group = flight_list.ota_extra_group
                this_week = datetime.datetime.strptime(ota_create_order_time, "%Y-%m-%d %H:%M:%S").strftime("%Y_%m_%W")
                ota_pay_price = flight_list.ota_pay_price if flight_list.ota_pay_price else float(0)
                providers_total_price = flight_list.providers_total_price if flight_list.providers_total_price else float(0)

                for order_list in flight_list.sub_orders:
                    out_trade_no = order_list.out_trade_no
                    provider_price = order_list.provider_price if order_list.provider_price else float(0)
                    provider_order_id = order_list.provider_order_id
                    pay_time = '0000-00-00'
                    for pay_info in order_list.income_expense_details:
                        pay_time = str(pay_info.pay_time)
                    paxs = []
                    for pax in order_list.passengers:
                        pax = {'p2fo_id': pax.id, 'last_name': pax.person.last_name,
                               'first_name': pax.person.first_name,
                               'used_card_type': pax.used_card_type, 'birthdate': str(pax.person.birthdate),
                               'card_expired': pax.person.card_expired, 'nationality': pax.person.nationality,
                               'pid': pax.used_card_no, 'name': pax.person.name, 'age_type': pax.person.age_type,
                               'gender': pax.person.gender, 'mobile': pax.person.mobile, 'ticket_no': pax.ticket_no,
                               'card_issue_place': pax.person.card_issue_place}
                        paxs.append(pax)
                    bill_list = {'flight_order': flight_id, 'sub_order': order_list.id,
                                 'ota_create_time': ota_create_order_time, 'from_date': from_date, 'ota_extra_name': ota_extra_name,'ota_extra_group':ota_extra_group,'ota_name': ota_name, 'ota_order_id': ota_order_id,
                                 'passengers': paxs, 'this_week':this_week, 'pay_time': pay_time,'ota_pay_price': ota_pay_price,'providers_total_price': providers_total_price,
                                 'out_trade_no': out_trade_no, 'provider_price': provider_price, 'provider_order_id': provider_order_id,'provider_channel': provider_channel}
                    bill_lists.append(bill_list)
            resp = {'data': bill_lists, 'ret_code': 1}
        else:
            resp = {'data': '无数据', 'ret_code': 2}
        return TBResponse(resp)


get_bill_list_view = GetBillList.as_view('getbill_list')
misc_app.add_url_rule('/get_bill_list/', view_func=get_bill_list_view, methods=['get'])


class FlightSearch(MethodView):
    """
    订单搜索功能
    搜索参数：ticket_no/ota_order_id/provider_order_id/user_card_no/name/first_name&last_name
    """
    @perm_check(perm_module='order_search')
    @db_session
    def get(self):
        TB_REQUEST_ID = Random.gen_request_id()
        ota_order_id = request.args.get('ota_order_id', '')
        provider_order_id = request.args.get('provider_order_id', '')
        ticket_no = request.args.get('ticket_no', '')
        used_card_no = request.args.get('used_card_no', '')
        name = request.args.get('name', '')
        last_name = request.args.get('last_name', '')
        first_name = request.args.get('first_name', '')

        # 获取group信息
        use_info = TBG.global_config['USER_LIST'][g.user]
        group = use_info['group']
        if ota_order_id:
            flight_orders = []
            search_list = select(o for o in FlightOrder if str(ota_order_id) in o.ota_order_id)

            # 对特定的group做限制
            if group in ['yidayiyou', 'yida', 'yiyou']:
                search_list = search_list.filter(lambda o: o.ota_extra_group == group)

            for i in search_list:
                flight_number = ''
                if i.routing:
                    routing_detail = i.routing.routing_key_detail
                    rk_info = RoutingKey.unserialize(routing_detail, is_encrypted=False)
                    if rk_info:
                        flight_number = rk_info['flight_number']
                flight_order = {'flight_order': i.id, 'ota_name': i.ota_name, 'from_date': str(i.from_date), 'ota_create_order_time': str(i.ota_create_order_time),
                                'from_city': i.from_city, 'to_city': i.to_city, 'from_airport': i.from_airport, 'to_airport': i.to_airport, 'provider_channel': i.provider_channel,
                                'ota_order_status':{'value': i.ota_order_status.strip(), 'label': OTA_ORDER_STATUS[i.ota_order_status.strip()]},
                                'providers_status': {'value': i.providers_status.strip(),'label': PROVIDERS_STATUS[i.providers_status.strip()]['cn_desc']},
                                'flight_number': flight_number
                                }
                flight_orders.append(flight_order)
            resp = {'data': flight_orders, 'ret_code': 1}
        elif provider_order_id:
            flight_orders = []
            search_list = select(o for o in SubOrder if o.provider_order_id == str(provider_order_id))
            for i in search_list:
                flight_number = ''
                # 对特定的group做限制
                if group in ['yidayiyou', 'yida', 'yiyou'] and i.flight_order.ota_extra_group != group:
                    continue
                if i.routing:
                    routing_detail = i.routing.routing_key_detail
                    rk_info = RoutingKey.unserialize(routing_detail, is_encrypted=False)
                    if rk_info:
                        flight_number = rk_info['flight_number']
                flight_order = {'flight_order': i.flight_order.id, 'ota_name': i.flight_order.ota_name, 'from_date': str(i.flight_order.from_date),
                                'ota_create_order_time': str(i.flight_order.ota_create_order_time), 'to_airport': i.flight_order.to_airport,
                                'provider_channel': i.flight_order.provider_channel, 'from_airport': i.flight_order.from_airport,
                                'from_city': i.flight_order.from_city, 'to_city': i.flight_order.to_city,
                                'ota_order_status':{'value': i.flight_order.ota_order_status.strip(), 'label': OTA_ORDER_STATUS[i.flight_order.ota_order_status.strip()]},
                                'providers_status': {'value': i.flight_order.providers_status.strip(), 'label': PROVIDERS_STATUS[i.flight_order.providers_status.strip()]['cn_desc']},
                                'flight_number': flight_number
                                }
                flight_orders.append(flight_order)
            resp = {'data': flight_orders, 'ret_code': 1}
        elif ticket_no:
            flight_orders = []
            search_list = select(o for o in Person2FlightOrder if o.ticket_no == str(ticket_no))
            for i in search_list:
                flight_number = ''
                # 对特定的group做限制
                if group in ['yidayiyou', 'yida', 'yiyou'] and i.flight_order.ota_extra_group != group:
                    continue
                if i.flight_order.routing:
                    routing_detail = i.flight_order.routing.routing_key_detail
                    rk_info = RoutingKey.unserialize(routing_detail, is_encrypted=False)
                    if rk_info:
                        flight_number = rk_info['flight_number']
                flight_order = {'flight_order': i.flight_order.id, 'ota_name': i.flight_order.ota_name, 'from_date': str(i.flight_order.from_date),
                                'ota_create_order_time': str(i.flight_order.ota_create_order_time), 'to_airport': i.flight_order.to_airport,
                                'provider_channel': i.flight_order.provider_channel, 'from_airport': i.flight_order.from_airport,
                                'from_city': i.flight_order.from_city, 'to_city': i.flight_order.to_city,
                                'ota_order_status':{'value': i.flight_order.ota_order_status.strip(), 'label': OTA_ORDER_STATUS[i.flight_order.ota_order_status.strip()]},
                                'providers_status': {'value': i.flight_order.providers_status.strip(), 'label': PROVIDERS_STATUS[i.flight_order.providers_status.strip()]['cn_desc']},
                                'flight_number': flight_number
                                }
                flight_orders.append(flight_order)
            resp = {'data': flight_orders, 'ret_code': 1}
        elif used_card_no:
            search_list = select(o for o in Person2FlightOrder if o.used_card_no == str(used_card_no))
            flight_orders = []
            for i in search_list:
                # 对特定的group做限制
                if group in ['yidayiyou', 'yida', 'yiyou'] and i.flight_order.ota_extra_group != group:
                    continue
                flight_number = ''
                if i.flight_order.routing:
                    routing_detail = i.flight_order.routing.routing_key_detail
                    rk_info = RoutingKey.unserialize(routing_detail, is_encrypted=False)
                    if rk_info:
                        flight_number = rk_info['flight_number']
                flight_order = {'flight_order': i.flight_order.id, 'ota_name': i.flight_order.ota_name, 'from_date': str(i.flight_order.from_date),
                                'ota_create_order_time': str(i.flight_order.ota_create_order_time), 'to_airport': i.flight_order.to_airport,
                                'provider_channel': i.flight_order.provider_channel, 'from_airport': i.flight_order.from_airport,
                                'from_city': i.flight_order.from_city, 'to_city': i.flight_order.to_city,
                                'ota_order_status':{'value': i.flight_order.ota_order_status.strip(), 'label': OTA_ORDER_STATUS[i.flight_order.ota_order_status.strip()]},
                                'providers_status': {'value': i.flight_order.providers_status.strip(), 'label': PROVIDERS_STATUS[i.flight_order.providers_status.strip()]['cn_desc']},
                                'flight_number': flight_number
                                }
                flight_orders.append(flight_order)
            resp = {'data': flight_orders, 'ret_code': 1}
        elif name:
            flight_orders = []
            search_list = select(o for o in Person if o.name == name or o.first_name == name or o.last_name == name)
            for pax in search_list:
                for person_2 in pax.flight_orders:
                    flight_number = ''
                    # 特定group限制
                    if group in ['yidayiyou', 'yida', 'yiyou'] and person_2.flight_order.ota_extra_group != group:
                        continue
                    if person_2.flight_order.routing:
                        routing_detail = person_2.flight_order.routing.routing_key_detail
                        rk_info = RoutingKey.unserialize(routing_detail, is_encrypted=False)
                        if rk_info:
                            flight_number = rk_info['flight_number']
                    flight_order = {'flight_order': person_2.flight_order.id, 'ota_name': person_2.flight_order.ota_name, 'from_date': str(person_2.flight_order.from_date),
                                    'ota_create_order_time': str(person_2.flight_order.ota_create_order_time), 'to_airport': person_2.flight_order.to_airport,
                                    'provider_channel': person_2.flight_order.provider_channel, 'from_airport': person_2.flight_order.from_airport, 'name': pax.name,
                                    'from_city': person_2.flight_order.from_city, 'to_city': person_2.flight_order.to_city, 'last_name': pax.last_name, 'first_name': pax.first_name,
                                    'ota_order_status': {'value': person_2.flight_order.ota_order_status.strip(), 'label': OTA_ORDER_STATUS[person_2.flight_order.ota_order_status.strip()]},
                                    'providers_status': {'value': person_2.flight_order.providers_status.strip(), 'label': PROVIDERS_STATUS[person_2.flight_order.providers_status.strip()]['cn_desc']},
                                    'flight_number': flight_number
                                    }
                    flight_orders.append(flight_order)
            resp = {'data': flight_orders, 'ret_code': 1}
        elif last_name and first_name:
            flight_orders = []
            search_list = select(o for o in Person if o.last_name == last_name and o.first_name == first_name)
            for pax in search_list:
                for person_2 in pax.flight_orders:
                    flight_number = ''
                    # 特定group限制
                    if group in ['yidayiyou', 'yida', 'yiyou'] and person_2.flight_order.ota_extra_group != group:
                        continue
                    if person_2.flight_order.routing:
                        routing_detail = person_2.flight_order.routing.routing_key_detail
                        rk_info = RoutingKey.unserialize(routing_detail, is_encrypted=False)
                        if rk_info:
                            flight_number = rk_info['flight_number']
                    flight_order = {'flight_order': person_2.flight_order.id, 'ota_name': person_2.flight_order.ota_name, 'from_date': str(person_2.flight_order.from_date),
                                    'ota_create_order_time': str(person_2.flight_order.ota_create_order_time), 'to_airport': person_2.flight_order.to_airport,
                                    'provider_channel': person_2.flight_order.provider_channel, 'from_airport': person_2.flight_order.from_airport, 'name': pax.name,
                                    'from_city': person_2.flight_order.from_city, 'to_city': person_2.flight_order.to_city, 'last_name': pax.last_name, 'first_name': pax.first_name,
                                    'ota_order_status':{'value': person_2.flight_order.ota_order_status.strip(), 'label': OTA_ORDER_STATUS[person_2.flight_order.ota_order_status.strip()]},
                                    'providers_status': {'value': person_2.flight_order.providers_status.strip(), 'label': PROVIDERS_STATUS[person_2.flight_order.providers_status.strip()]['cn_desc']},
                                    'flight_number': flight_number
                                    }
                    flight_orders.append(flight_order)
            resp = {'data': flight_orders, 'ret_code': 1}
        else:
            resp = {'error': '请求参数错误', 'ret_code': 2}

        return TBResponse(resp)


flight_search_view = FlightSearch.as_view('flight_search')
misc_app.add_url_rule('/flight_search', view_func=flight_search_view, methods=['get'])


class GetDynamicFare(MethodView):
    """
    动态运价面板数据
    """
    @perm_check(perm_module='order_details')
    @db_session
    def get(self):
        TB_REQUEST_ID = Random.gen_request_id()
        from_airport = request.args.get('from_airport', '')
        to_airport = request.args.get('to_airport', '')
        from_date = request.args.get('from_date', '')
        filter_type = request.args.get('filter_type', '')
        primary_task_id = request.args.get('primary_task_id', '')
        is_transfer = request.args.get('is_transfer', '')
        data_folding = request.args.get('data_folding', '')
        fare_put_mode = request.args.get('fare_put_mode', '')
        is_display = request.args.get('is_display', '')
        now_time = datetime.datetime.now()
        before_30m = datetime.datetime.now() - datetime.timedelta(minutes=180)

        if from_airport and to_airport and from_date:
            dynamic_list = select(o for o in DynamicFareRepo if o.from_airport == str(from_airport) and o.to_airport == str(to_airport) and o.from_date == datetime.datetime.strptime(from_date, "%Y-%m-%d"))
        elif from_airport and to_airport:
            dynamic_list = select(o for o in DynamicFareRepo if o.from_airport == str(from_airport) and o.to_airport == str(to_airport) and o.from_date >= now_time)
        elif from_date:
            dynamic_list = select(o for o in DynamicFareRepo if o.from_date == datetime.datetime.strptime(from_date, "%Y-%m-%d"))
        elif filter_type and filter_type == 'cost_y_r1_y':
            dynamic_list = select(o for o in DynamicFareRepo if o.from_date >= now_time and o.cost_price != 0 and o.ota_r1_price != 0)
        elif filter_type and filter_type == 'cost_y_r1_n':
            dynamic_list = select(o for o in DynamicFareRepo if o.from_date >= now_time and o.cost_price != 0 and o.ota_r1_price == 0)
        elif filter_type and filter_type == 'cost_n_r1_y':
            dynamic_list = select(o for o in DynamicFareRepo if o.from_date >= now_time and o.cost_price == 0 and o.ota_r1_price != 0)
        elif primary_task_id:
            dynamic_list = select(o for o in DynamicFareRepo if o.from_date >= now_time and o.primary_fare_crawl_task.id == primary_task_id and o.update_time > before_30m)
        elif fare_put_mode:
            dynamic_list = select(o for o in DynamicFareRepo if o.from_date >= now_time and o.fare_put_mode == fare_put_mode and o.update_time > before_30m)
        else:
            dynamic_list = select(o for o in DynamicFareRepo if o.from_date >= now_time and o.cost_price != 0 and o.ota_r1_price != 0 and o.offer_price != 0 and o.update_time > before_30m)

        if is_transfer == '0':
            dynamic_list = select(o for o in DynamicFareRepo if o.from_date >= now_time and o.cost_price != 0 and o.ota_r1_price != 0 and o.offer_price != 0 and o.update_time > before_30m and '-' not in o.flight_number)
        elif is_transfer == '1':
            dynamic_list = select(o for o in DynamicFareRepo if o.from_date >= now_time and o.cost_price != 0 and o.ota_r1_price != 0 and o.offer_price != 0 and o.update_time > before_30m and '-' in o.flight_number)

        if is_display == '1':
            dynamic_list = select(o for o in DynamicFareRepo if o.from_date >= now_time and o.offer_price <= o.ota_r1_price and o.update_time > before_30m)
        elif is_display == '0':
            dynamic_list = select(o for o in DynamicFareRepo if o.from_date >= now_time and o.offer_price > o.ota_r1_price and o.update_time > before_30m)

        dynamic_lists = []
        air_lines = []
        air_line_str_lists = []
        ota_verify_list = select(o for o in OTAVerify if Time.days_before(7) < o.verify_time)

        # 获取验价数据，并将验价信息转换成字符串
        for ota_detail in ota_verify_list:
            air_line_str = '{from_airport}-{to_airport}-{from_date}-{flight_number}-{cabin}'.format(from_airport=ota_detail.from_airport,
                                                                                                    to_airport=ota_detail.to_airport,
                                                                                                    from_date=ota_detail.from_date,
                                                                                                    flight_number=ota_detail.flight_number,
                                                                                                    cabin=ota_detail.cabin)
            air_line_str_lists.append(air_line_str)

        # 数据折叠，目前写法太烂后面优化
        if data_folding == 'D' and filter_type == 'cost_y_r1_y':
            dynamic_list = select((o.from_date,o.from_airport, o.to_airport, count(o)) for o in DynamicFareRepo if o.from_date >= now_time and o.cost_price != 0 and o.ota_r1_price != 0)
            for dynamic_detail in dynamic_list:
                air_line = {'from_date': dynamic_detail[0], 'from_airport': dynamic_detail[1], 'to_airport': dynamic_detail[2]}
                air_lines.append(air_line)
            dynamic_min_list = []
            for air_line in air_lines:
                agg_line = select(o for o in DynamicFareRepo if o.from_date == air_line['from_date'] and o.from_airport == air_line['from_airport'] and o.to_airport == air_line['to_airport'])
                ota_r1_price_min = []
                cost_price_list = []
                for dynamic_detail in agg_line:
                    ota_r1_price_min.append(dynamic_detail.ota_r1_price)
                    dynamic_price = {'id': dynamic_detail.id, 'primary_fare_crawl_task': dynamic_detail.primary_fare_crawl_task.id, 'from_airport': dynamic_detail.from_airport,
                                     'to_airport': dynamic_detail.to_airport, 'from_date': str(dynamic_detail.from_date), 'flight_number': dynamic_detail.flight_number,
                                     'cabin': dynamic_detail.cabin, 'cost_price': dynamic_detail.cost_price, 'provider': dynamic_detail.provider, 'offer_price': dynamic_detail.offer_price,
                                     'ota_r1_price': dynamic_detail.ota_r1_price, 'ota_r2_price': dynamic_detail.ota_r2_price, 'update_time': str(dynamic_detail.update_time),
                                     'fare_put_mode': dynamic_detail.fare_put_mode, 'ver': dynamic_detail.ver,
                                     'provider_channel': dynamic_detail.provider_channel, 'cabin_grade': dynamic_detail.cabin_grade}
                    cost_price_list.append(dynamic_price)
                for dynamic_detail in cost_price_list:
                    if dynamic_detail['ota_r1_price'] == min(ota_r1_price_min):
                        airline = '{from_airport}-{to_airport}'.format(from_airport=dynamic_detail.from_airport,
                                                                       to_airport=dynamic_detail.to_airport)
                        air_line_str = '{from_airport}-{to_airport}-{from_date}-{flight_number}-{cabin}'.format(
                                                                                                        from_airport=dynamic_detail.from_airport,
                                                                                                        to_airport=dynamic_detail.to_airport,
                                                                                                        from_date=dynamic_detail.from_date,
                                                                                                        flight_number=dynamic_detail.flight_number,
                                                                                                        cabin=dynamic_detail.cabin)
                        verify_count = {'verify_count': air_line_str_lists.count(air_line_str), 'air_line': airline}
                        dynamic_detail.update(verify_count)
                        dynamic_min_list.append(dynamic_detail)
            dynamic_lists = dynamic_min_list
        elif data_folding == 'D' and filter_type == 'cost_y_r1_n':
            dynamic_list = select((o.from_date,o.from_airport, o.to_airport, count(o)) for o in DynamicFareRepo if o.from_date >= now_time and o.cost_price != 0 and o.ota_r1_price == 0)
            for dynamic_detail in dynamic_list:
                air_line = {'from_date': dynamic_detail[0], 'from_airport': dynamic_detail[1], 'to_airport': dynamic_detail[2]}
                air_lines.append(air_line)
            dynamic_min_list = []
            for air_line in air_lines:
                agg_line = select(o for o in DynamicFareRepo if o.from_date == air_line['from_date'] and o.from_airport == air_line['from_airport'] and o.to_airport == air_line['to_airport'])
                ota_r1_price_min = []
                cost_price_list = []
                for dynamic_detail in agg_line:
                    ota_r1_price_min.append(dynamic_detail.ota_r1_price)
                    dynamic_price = {'id': dynamic_detail.id, 'primary_fare_crawl_task': dynamic_detail.primary_fare_crawl_task.id, 'from_airport': dynamic_detail.from_airport,
                                     'to_airport': dynamic_detail.to_airport, 'from_date': str(dynamic_detail.from_date), 'flight_number': dynamic_detail.flight_number,
                                     'cabin': dynamic_detail.cabin, 'cost_price': dynamic_detail.cost_price, 'provider': dynamic_detail.provider, 'offer_price': dynamic_detail.offer_price,
                                     'ota_r1_price': dynamic_detail.ota_r1_price, 'ota_r2_price': dynamic_detail.ota_r2_price, 'update_time': str(dynamic_detail.update_time),
                                     'fare_put_mode': dynamic_detail.fare_put_mode, 'ver': dynamic_detail.ver, 'cabin_grade': dynamic_detail.cabin_grade,
                                      'provider_channel': dynamic_detail.provider_channel}
                    cost_price_list.append(dynamic_price)
                for dynamic_detail in cost_price_list:
                    if dynamic_detail['ota_r1_price'] == min(ota_r1_price_min):
                        airline = '{from_airport}-{to_airport}'.format(from_airport=dynamic_detail.from_airport,
                                                                        to_airport=dynamic_detail.to_airport)
                        air_line_str = '{from_airport}-{to_airport}-{from_date}-{flight_number}-{cabin}'.format(
                                                                                                        from_airport=dynamic_detail.from_airport,
                                                                                                        to_airport=dynamic_detail.to_airport,
                                                                                                        from_date=dynamic_detail.from_date,
                                                                                                        flight_number=dynamic_detail.flight_number,
                                                                                                        cabin=dynamic_detail.cabin)
                        verify_count = {'verify_count': air_line_str_lists.count(air_line_str), 'air_line': airline}
                        dynamic_detail.update(verify_count)
                        dynamic_min_list.append(dynamic_detail)
            dynamic_lists = dynamic_min_list
        elif data_folding == 'D' and filter_type == 'cost_n_r1_y':
            dynamic_list = select((o.from_date,o.from_airport, o.to_airport, count(o)) for o in DynamicFareRepo if o.from_date >= now_time and o.cost_price == 0 and o.ota_r1_price != 0)
            for dynamic_detail in dynamic_list:
                air_line = {'from_date': dynamic_detail[0], 'from_airport': dynamic_detail[1], 'to_airport': dynamic_detail[2]}
                air_lines.append(air_line)
            dynamic_min_list = []
            for air_line in air_lines:
                agg_line = select(o for o in DynamicFareRepo if o.from_date == air_line['from_date'] and o.from_airport == air_line['from_airport'] and o.to_airport == air_line['to_airport'])
                ota_r1_price_min = []
                cost_price_list = []
                for dynamic_detail in agg_line:
                    ota_r1_price_min.append(dynamic_detail.ota_r1_price)
                    dynamic_price = {'id': dynamic_detail.id, 'primary_fare_crawl_task': dynamic_detail.primary_fare_crawl_task.id, 'from_airport': dynamic_detail.from_airport,
                                     'to_airport': dynamic_detail.to_airport, 'from_date': str(dynamic_detail.from_date), 'flight_number': dynamic_detail.flight_number,
                                     'cabin': dynamic_detail.cabin, 'cost_price': dynamic_detail.cost_price, 'provider': dynamic_detail.provider, 'offer_price': dynamic_detail.offer_price,
                                     'ota_r1_price': dynamic_detail.ota_r1_price, 'ota_r2_price': dynamic_detail.ota_r2_price, 'update_time': str(dynamic_detail.update_time),
                                     'fare_put_mode': dynamic_detail.fare_put_mode, 'ver': dynamic_detail.ver, 'cabin_grade': dynamic_detail.cabin_grade,
                                     'provider_channel': dynamic_detail.provider_channel}
                    cost_price_list.append(dynamic_price)
                for dynamic_detail in cost_price_list:
                    if dynamic_detail['ota_r1_price'] == min(ota_r1_price_min):
                        airline = '{from_airport}-{to_airport}'.format(from_airport=dynamic_detail.from_airport,
                                                                        to_airport=dynamic_detail.to_airport)
                        air_line_str = '{from_airport}-{to_airport}-{from_date}-{flight_number}-{cabin}'.format(
                                                                                                        from_airport=dynamic_detail.from_airport,
                                                                                                        to_airport=dynamic_detail.to_airport,
                                                                                                        from_date=dynamic_detail.from_date,
                                                                                                        flight_number=dynamic_detail.flight_number,
                                                                                                        cabin=dynamic_detail.cabin)
                        verify_count = {'verify_count': air_line_str_lists.count(air_line_str), 'air_line': airline}
                        dynamic_detail.update(verify_count)
                        dynamic_min_list.append(dynamic_detail)
            dynamic_lists = dynamic_min_list
        else:
            for dynamic_detail in dynamic_list:
                airline = '{from_airport}-{to_airport}'.format(from_airport=dynamic_detail.from_airport,
                                                                to_airport=dynamic_detail.to_airport)
                air_line_str = '{from_airport}-{to_airport}-{from_date}-{flight_number}-{cabin}'.format(
                                                                                                        from_airport=dynamic_detail.from_airport,
                                                                                                        to_airport=dynamic_detail.to_airport,
                                                                                                        from_date=dynamic_detail.from_date,
                                                                                                        flight_number=dynamic_detail.flight_number,
                                                                                                        cabin=dynamic_detail.cabin)
                verify_count = air_line_str_lists.count(air_line_str)
                dynamic_price = {'id': dynamic_detail.id, 'primary_fare_crawl_task': dynamic_detail.primary_fare_crawl_task.id, 'from_airport': dynamic_detail.from_airport,
                                 'to_airport': dynamic_detail.to_airport,'from_date': str(dynamic_detail.from_date), 'flight_number': dynamic_detail.flight_number,
                                 'cabin': dynamic_detail.cabin, 'cost_price': dynamic_detail.cost_price,'provider': dynamic_detail.provider, 'offer_price': dynamic_detail.offer_price,
                                 'ota_r1_price': dynamic_detail.ota_r1_price, 'ota_r2_price': dynamic_detail.ota_r2_price, 'update_time': str(dynamic_detail.update_time),
                                 'verify_count': verify_count, 'air_line': airline, 'fare_put_mode': dynamic_detail.fare_put_mode, 'ver': dynamic_detail.ver,
                                  'provider_channel': dynamic_detail.provider_channel,
                                 'cabin_grade': dynamic_detail.cabin_grade}
                dynamic_lists.append(dynamic_price)
        resp = {'data': dynamic_lists, 'ret_code': 1}
        return TBResponse(resp)

    @perm_check(perm_module='order_details')
    @db_session
    def put(self, dynamic_id):
        """
        修改动态运价表的信息
        :param dynamic_id:
        :return:
        """
        TB_REQUEST_ID = Random.gen_request_id()
        req_body = request.get_json()
        req_body = req_body.get(str(dynamic_id))
        cost_price = req_body.get('cost_price')
        offer_price = req_body.get('offer_price')
        fare_put_mode = req_body.get('fare_put_mode')
        primary_fare_crawl_task = req_body.get('primary_fare_crawl_task')
        dynamic_fare_repo = DynamicFareRepo[dynamic_id]
        if cost_price:
            dynamic_fare_repo.cost_price = cost_price
        if offer_price:
            dynamic_fare_repo.offer_price = offer_price
        if primary_fare_crawl_task:
            dynamic_fare_repo.primary_fare_crawl_task.id = primary_fare_crawl_task
        if fare_put_mode:
            dynamic_fare_repo.fare_put_mode = fare_put_mode

        resp = {'ret_code': 1}
        return TBResponse(resp)


get_dynamic_view = GetDynamicFare.as_view('dynamic_fare')
misc_app.add_url_rule('/get_dynamic_fare', view_func=get_dynamic_view, methods=['get'])
misc_app.add_url_rule('/dynamic_fare_repo/<int:dynamic_id>', view_func=get_dynamic_view, methods=['put'])


class GetOtaVerify(MethodView):
    @perm_check(perm_module='ota_verify')
    @db_session
    def get(self, ota_verify_id=''):
        """
        获取验价数据
        """
        TB_REQUEST_ID = Random.gen_request_id()
        date_ranges = request.args.get('date_ranges', '')
        is_success = request.args.get('is_success', '')
        if date_ranges:
            date_range = int(date_ranges)
        else:
            date_range = 7

        if is_success == str(1):
            ota_verify_list = select(o for o in OTAVerify if Time.days_before(date_range) < o.verify_time and o.return_status == 'SUCCESS')
        elif is_success == str(0):
            ota_verify_list = select(o for o in OTAVerify if Time.days_before(date_range) < o.verify_time and o.return_status != 'SUCCESS')
        elif ota_verify_id:
            ota_verify_list = OTAVerify[ota_verify_id]
        else:
            ota_verify_list = select(o for o in OTAVerify if Time.days_before(date_range) < o.verify_time)

        verify_lists = []
        if ota_verify_id:
            verify_lists = {'ota_name': ota_verify_list.ota_name, 'provider': ota_verify_list.provider, 'provider_channel': ota_verify_list.provider_channel,
                            'from_date': str(ota_verify_list.from_date), 'ret_date': ota_verify_list.ret_date, 'from_airport': ota_verify_list.from_airport,
                            'to_airport': ota_verify_list.to_airport, 'flight_number': ota_verify_list.flight_number,'cabin': ota_verify_list.cabin,
                            'return_status': ota_verify_list.return_status, 'return_details': ota_verify_list.return_details, 'routing_key': ota_verify_list.routing_key,
                            'verify_duration': ota_verify_list.verify_duration, 'verify_time': str(ota_verify_list.verify_time), 'search_time': str(ota_verify_list.search_time),
                            's2v_duration': ota_verify_list.s2v_duration, 'enter_time': str(ota_verify_list.enter_time),
                            'create_time': str(ota_verify_list.create_time), 'ret': ota_verify_list.ret, 'req': ota_verify_list.req,
                            'providers_stat': ota_verify_list.providers_stat, 'fare_info': ota_verify_list.fare_info, 'request_id': ota_verify_list.request_id,
                            'current_assoc_fare_info': ota_verify_list.current_assoc_fare_info, 'adjust_assoc_fare_info': ota_verify_list.adjust_assoc_fare_info,
                            'rsno': ota_verify_list.rsno, 'verify_details': ota_verify_list.verify_details, 'ota_product_code': ota_verify_list.ota_product_code}
        else:
            for ota_detail in ota_verify_list:
                air_line = ota_detail.from_airport + '-' + ota_detail.to_airport
                ret = json.loads(ota_detail.ret)
                cabin_grade = ''
                fare_put_mode = ''
                dep_diff_days = ''
                assoc_provider_channels = ''
                if ota_detail.return_status == 'SUCCESS':
                    routing_ks = RoutingKey.unserialize(ota_detail.routing_key, is_encrypted=False)
                    cabin_grade = routing_ks.get('cabin_grade')
                    fare_put_mode = routing_ks.get('fare_put_mode')
                    dep_diff_days = routing_ks.get('dep_diff_days')
                    assoc_provider_channels = routing_ks.get('assoc_provider_channels', '')
                else:
                    if ota_detail.routing_key:
                        routing_ks = RoutingKey.unserialize(ota_detail.routing_key, is_encrypted=False)
                        cabin_grade = routing_ks.get('cabin_grade')
                        fare_put_mode = routing_ks.get('fare_put_mode')
                        dep_diff_days = routing_ks.get('dep_diff_days')
                        assoc_provider_channels = routing_ks.get('assoc_provider_channels', '')

                # 获取验价供应商，并去掉多余字符串
                verify_provider_list = []
                for x in assoc_provider_channels:
                    verify_provider = x.split('#')[0]
                    if verify_provider == 'main':
                        pass
                    else:
                        verify_provider_list.append(verify_provider)

                if ota_detail.return_status == 'SUCCESS':
                    adultPrice = ret['routing']['adultPrice']
                    adultTax = ret['routing']['adultTax']
                    childPrice = ret['routing']['childPrice']
                    childTax = ret['routing']['childTax']
                    if ';' in ota_detail.current_assoc_fare_info:
                        fare_data = ota_detail.current_assoc_fare_info.split(';')
                        fare_result = {'is_two_fare': 1, 'ota_r1_price': fare_data[0], 'ota_r2_price': fare_data[1],
                                       'cost_price': fare_data[2], 'offer_price': fare_data[3], 'verify_stop_loss': fare_data[4],
                                       'verify_stop_profit': fare_data[5], 'is_show': fare_data[6]}
                    else:
                        fare_result = {'is_two_fare': 0, 'manual_name': ota_detail.current_assoc_fare_info}
                else:
                    adultPrice = ''
                    adultTax = ''
                    childPrice = ''
                    childTax = ''
                    fare_result = {}

                verify_list = {'ota_name': ota_detail.ota_name, 'provider': ota_detail.provider, 'provider_channel': ota_detail.provider_channel,
                               'from_date': ota_detail.from_date, 'ret_date': ota_detail.ret_date, 'from_airport': ota_detail.from_airport,
                               'to_airport': ota_detail.to_airport, 'flight_number': ota_detail.flight_number,'cabin': ota_detail.cabin,
                               'return_status': ota_detail.return_status, 'return_details': ota_detail.return_details, 'fare_put_mode': fare_put_mode,
                               'verify_duration': ota_detail.verify_duration, 'verify_time': str(ota_detail.verify_time), 'search_time': str(ota_detail.search_time),
                               's2v_duration': ota_detail.s2v_duration, 'enter_time': str(ota_detail.enter_time),
                               'create_time': str(ota_detail.create_time), 'air_line': air_line, 'id': ota_detail.id, 'adultPrice': adultPrice,
                               'adultTax': adultTax, 'childPrice': childPrice, 'childTax': childTax, 'cabinGrade': cabin_grade,
                               'dep_diff_days': dep_diff_days, 'verify_provider_list': verify_provider_list,
                               'providers_stat': ota_detail.providers_stat, 'fare_info': ota_detail.fare_info, 'request_id': ota_detail.request_id,
                               'current_assoc_fare_info': ota_detail.current_assoc_fare_info,
                               'adjust_assoc_fare_info': ota_detail.adjust_assoc_fare_info,
                               'rsno': ota_detail.rsno, 'fare_result': fare_result, 'ota_product_code': ota_detail.ota_product_code
                               }
                verify_lists.append(verify_list)

        resp = {'data': verify_lists, 'ret_code': 1}
        return TBResponse(resp)


get_ota_verify_view = GetOtaVerify.as_view('ota_verify')
misc_app.add_url_rule('/ota_verify/<int:ota_verify_id>', view_func=get_ota_verify_view, methods=['get'])
misc_app.add_url_rule('/ota_verify', view_func=get_ota_verify_view, methods=['get'])


class PrimaryFareCrawlTaskManage(MethodView):
    @perm_check(perm_module='order_details')
    @db_session
    def get(self):
        TB_REQUEST_ID = Random.gen_request_id()
        crawl_task_list = select(o for o in PrimaryFareCrawlTask)
        crawl_lists = []
        for task_detail in crawl_task_list:
            crawl_list = {'id': task_detail.id, 'providers': task_detail.providers, 'benchmark_provider_channel': task_detail.benchmark_provider_channel,
                          'cabin_grade': task_detail.cabin_grade, 'trip_type': task_detail.trip_type, 'within_days': task_detail.within_days,
                          'start_day': task_detail.start_day, 'task_status': task_detail.task_status, 'create_time': str(task_detail.create_time),
                          'stop_loss': task_detail.stop_loss, 'stop_profit': task_detail.stop_profit, 'crawl_airlines': task_detail.crawl_airlines,
                          'estimate_ota_diff_price': task_detail.estimate_ota_diff_price, 'bidding_diff_price': task_detail.bidding_diff_price,
                          'is_enable_auto_put': task_detail.is_enable_auto_put, 'task_name': task_detail.task_name,
                          'ota_custom_route_strategy': task_detail.ota_custom_route_strategy, 'task_type': task_detail.task_type,
                          'priority': task_detail.priority}
            crawl_lists.append(crawl_list)
        resp = {'data': crawl_lists, 'ret_code': 1}
        return TBResponse(resp)

    @perm_check(perm_module='order_details')
    @db_session
    def put(self, crawl_task_id):
        TB_REQUEST_ID = Random.gen_request_id()
        req_body = request.get_json()
        req_body = req_body.get(str(crawl_task_id))
        crawl_task = PrimaryFareCrawlTask[crawl_task_id]
        for key, value in req_body.items():
            if getattr(crawl_task, key):
                setattr(crawl_task, key, value)
        resp = {'ret_code': 1}
        return TBResponse(resp)

    @perm_check(perm_module='order_details')
    @db_session
    def post(self):
        TB_REQUEST_ID = Random.gen_request_id()
        req_body = request.get_json()
        insert_crawl_task = PrimaryFareCrawlTask()
        for key, value in req_body.items():
            setattr(insert_crawl_task, key, value)
        resp = {'ret_code': 1}
        return TBResponse(resp)


crawl_task_view = PrimaryFareCrawlTaskManage.as_view('crawl_task_manage')
misc_app.add_url_rule('/primary_fare_crawl_task/<int:crawl_task_id>', view_func=crawl_task_view, methods=['PUT'])
misc_app.add_url_rule('/primary_fare_crawl_task', view_func=crawl_task_view, methods=['POST'])
misc_app.add_url_rule('/primary_fare_crawl_task', view_func=crawl_task_view, methods=['GET'])


class FareComparisonManage(MethodView):
    """
    比价接口
    """

    @perm_check(perm_module='order_details')
    @db_session
    def get(self):
        TB_REQUEST_ID = Random.gen_request_id()
        date_ranges = request.args.get('date_ranges', '')
        from_airport = request.args.get('from_airport', '')
        to_airport = request.args.get('to_airport', '')
        data_folding = request.args.get('data_folding', '')
        crawler_task_id = request.args.get('crawler_task_id', '')
        now_time = datetime.datetime.now()
        if date_ranges:
            date_range = int(date_ranges)
        else:
            date_range = 1

        if from_airport and to_airport:
            fare_comparison_list = select(o for o in FareComparisonRepo if o.from_airport == from_airport and o.to_airport == to_airport and o.from_date >= now_time)
        else:
            fare_comparison_list = select(o for o in FareComparisonRepo if o.from_date >= Time.days_before(date_range))

        fare_lists = []
        benchmark_ids = {}
        # 获取所有基准供应商
        crawl_task_list = select([o.id, o.benchmark_provider_channel] for o in PrimaryFareCrawlTask)
        for crawl_task in crawl_task_list:
            benchmark_id = {str(crawl_task[0]): crawl_task[1]}
            benchmark_ids.update(benchmark_id)

        if data_folding == '0':
            if crawler_task_id:
                crawler_task_id = int(crawler_task_id)
            else:
                # 随机获取任务id(随机模块被占用，获取最后一个id)
                crawl_task_list = select(o.id for o in PrimaryFareCrawlTask if o.task_type == 'FARE_COMPARISON')
                crawler_task_ids = []
                for task_id in crawl_task_list:
                    crawler_task_ids.append(task_id)
                crawler_task_id = crawler_task_ids[len(crawler_task_ids)-1]
            fare_comparison_list = fare_comparison_list.filter(lambda o: o.primary_fare_crawl_task.id == int(crawler_task_id))
            air_lines = {}
            for cp_detail in fare_comparison_list:
                provider_comparison_lists = []
                # 获取基准供应商价格
                for provider_list in cp_detail.provider_fc_repo:
                    if provider_list.provider_channel == benchmark_ids[str(cp_detail.primary_fare_crawl_task.id)]:
                        bm_price = provider_list.cost_price
                # 按航线聚合数据
                air_line = cp_detail.from_airport + '-' + cp_detail.to_airport
                # 比价数据整合
                for provider_list in cp_detail.provider_fc_repo:
                    if cp_detail.update_time > provider_list.update_time:
                        time_diff = (cp_detail.update_time - provider_list.update_time).seconds
                    else:
                        time_diff = (provider_list.update_time - cp_detail.update_time).seconds
                    # 判断状态
                    if time_diff <= 10800:
                        provider_status = 'SUCCESS'
                    elif time_diff > 10800 and time_diff <= 21600:
                        provider_status = 'EXPIRED'
                    else:
                        provider_status = 'INVALID'
                    # 判断基准供应商
                    if benchmark_ids.get(str(cp_detail.primary_fare_crawl_task.id)) == provider_list.provider_channel:
                        is_bm = 1
                    else:
                        is_bm = 0

                    provider_comparison = {'provider_channel': provider_list.provider_channel,
                                           'cabin': provider_list.cabin,  'cost_price': provider_list.cost_price,
                                           'fare_status': provider_status, 'is_bm': is_bm,
                                           'price_diff': 0 if is_bm == 1 else provider_list.cost_price - bm_price}
                    provider_comparison_lists.append(provider_comparison)

                fare_list = {'flight_number': cp_detail.flight_number, 'cabin_grade': cp_detail.cabin_grade,
                             'air_line_grade': cp_detail.flight_number + '-' + cp_detail.cabin_grade,
                             'from_date': str(cp_detail.from_date), 'ver': cp_detail.ver, 'update_time': str(cp_detail.update_time),
                             'provider_cost_list': provider_comparison_lists, 'id': cp_detail.id}

                if air_lines.get(str(air_line)):
                    air_lines[str(air_line)].append(fare_list)
                else:
                    air_lines.update({str(air_line): [fare_list]})

            air_line_nbs = {}
            for key, values in air_lines.items():
                air_line_nbs.update({str(key): {}})
                for i in values:
                    if air_line_nbs[str(key)].get(str(i['air_line_grade'])):
                        air_line_nbs[str(key)][str(i['air_line_grade'])].append({'from_date': i['from_date'],
                                                                         'provider_cost_list': i['provider_cost_list'],
                                                                         'update_time': i['update_time']})
                    else:
                        air_line_nbs[str(key)].update({str(i['air_line_grade']): [{'from_date': i['from_date'],
                                                                                   'provider_cost_list': i['provider_cost_list'],
                                                                                   'update_time': i['update_time']}]})
            fare_lists = air_line_nbs
        else:
            if crawler_task_id:
                crawler_task_id = int(crawler_task_id)
            else:
                # 随机获取任务id(随机模块被占用，获取最后一个id)
                crawl_task_list = select(o.id for o in PrimaryFareCrawlTask if o.task_type == 'FARE_COMPARISON')
                crawler_task_ids = []
                for task_id in crawl_task_list:
                    crawler_task_ids.append(task_id)
                crawler_task_id = crawler_task_ids[len(crawler_task_ids)-1]

            # 获取所有基准供应商
            crawl_task_list = select([o.id, o.benchmark_provider_channel] for o in PrimaryFareCrawlTask)
            for crawl_task in crawl_task_list:
                benchmark_id = {str(crawl_task[0]): crawl_task[1]}
                benchmark_ids.update(benchmark_id)

            # 数据整合
            fare_comparison_list = fare_comparison_list.filter(lambda o: o.primary_fare_crawl_task.id == int(crawler_task_id))
            fare_comparison_list = fare_comparison_list.order_by(FareComparisonRepo.from_airport, FareComparisonRepo.to_airport)

            provider_air_lines = {}
            for fare_line in fare_comparison_list:
                provider_comparison_lists = {}
                # 按航段聚合所有供应商的数据价格
                for provider_list in fare_line.provider_fc_repo:
                    bench_mk = {}
                    if provider_list.provider_channel == benchmark_ids.get(str(fare_line.primary_fare_crawl_task.id)):
                        bench_mk = {'bm_price': provider_list.cost_price}
                    provider_comparison = {str(provider_list.provider_channel): provider_list.cost_price}
                    provider_comparison_lists.update(provider_comparison)
                    if bench_mk.get('bm_price'):
                        provider_comparison_lists.update(bench_mk)

                air_line = '{from_airport}-{to_airport}'.format(from_airport=fare_line.from_airport,
                                                                to_airport=fare_line.to_airport)
                fare_list = {'primary_fare_crawl_task_id': fare_line.primary_fare_crawl_task.id, 'from_airport': fare_line.from_airport,
                             'to_airport': fare_line.to_airport, 'cabin_grade': fare_line.cabin_grade,
                             'provider_cost_lists': [provider_comparison_lists], 'id': fare_line.id,
                             'benchmark_provider_channel': benchmark_ids.get(str(fare_line.primary_fare_crawl_task.id))}
                if provider_air_lines.get(str(air_line)):
                    provider_air_lines[str(air_line)]['provider_cost_lists'].append(provider_comparison_lists)
                else:
                    airline = {str(air_line): fare_list}
                    provider_air_lines.update(airline)
            fare_lists = []

            # 计算聚合航线后所有供应商价格差异量
            for provider_line in provider_air_lines.values():
                fare_provider_compar = {}
                line_count = len(provider_line['provider_cost_lists'])
                # 统计供应商数据
                for provider_cost_list in provider_line['provider_cost_lists']:
                    bm_price = provider_cost_list['bm_price']
                    for key, values in provider_cost_list.items():
                        if key != 'bm_price' and key != provider_line['benchmark_provider_channel']:
                            if fare_provider_compar.get(str(key)):
                                if values > bm_price:
                                    fare_provider_compar[str(key)]['high_count'] = fare_provider_compar[str(key)]['high_count'] + 1
                                elif values <= bm_price:
                                    fare_provider_compar[str(key)]['low_count'] = fare_provider_compar[str(key)]['low_count'] + 1
                                    fare_provider_compar[str(key)]['diff_price_list'].append(values - bm_price)
                            else:
                                if values > bm_price:
                                    provider_s = {str(key): {'low_count': 0, 'high_count': 1, 'diff_price_list': [], 'is_bm': 0}}
                                    fare_provider_compar.update(provider_s)
                                elif values <= bm_price:
                                    provider_s = {str(key): {'low_count': 1, 'high_count': 0, 'diff_price_list': [values - bm_price], 'is_bm': 0}}
                                    fare_provider_compar.update(provider_s)

                bm_provider = {str(provider_line['benchmark_provider_channel']): {'line_count': line_count, 'is_bm': 1}}

                # 计算各个供应商的低价率
                for key in fare_provider_compar.keys():

                    fare_provider_compar[str(key)].update({'low_rate': "%.2f%%" % (fare_provider_compar[str(key)]['low_count']/float(line_count) * 100),
                                                           'max_diff': min(fare_provider_compar[str(key)]['diff_price_list']) if fare_provider_compar[str(key)]['diff_price_list'] else '',
                                                           'avg_low_diff': sum(fare_provider_compar[str(key)]['diff_price_list'])/float(len(fare_provider_compar[str(key)]['diff_price_list']))
                                                           if fare_provider_compar[str(key)]['diff_price_list'] else ''}
                                                          )
                    fare_provider_compar[str(key)].pop('diff_price_list')
                fare_provider_compar.update(bm_provider)
                fare_list = {'from_airport': provider_line['from_airport'], 'to_airport': provider_line['to_airport'],
                             'benchmark_provider_channel': provider_line['benchmark_provider_channel'], 'fare_provider_list': fare_provider_compar,
                             'air_line': provider_line['from_airport'] + '-' + provider_line['to_airport']}
                fare_lists.append(fare_list)

        resp = {'data': fare_lists, 'ret_code': 1}
        return TBResponse(resp)


fare_comparison_view = FareComparisonManage.as_view('fare_comparison')
misc_app.add_url_rule('/fare_comparison_repo', view_func=fare_comparison_view, methods=['GET'])


class SmsMessageManage(MethodView):
    """
    获取五分钟内的短信
    """
    @perm_check(perm_module='tb_sms')
    @db_session
    def get(self):
        TB_REQUEST_ID = Random.gen_request_id()
        before_time = datetime.datetime.now() - datetime.timedelta(minutes=15)
        message_list = select(o for o in SmsMessage if o.create_time > before_time)
        msg_list = []
        for msg in message_list:
            msg_list.append({'id': msg.id, 'from_mobile': msg.from_mobile, 'message': msg.message,
                             'receive_time': str(msg.receive_time), 'sms_device_id': msg.sms_device_id,
                             'to_mobile': msg.to_mobile})
        resp = {'data': msg_list, 'ret_code': 1}
        return TBResponse(resp)


sms_message_view = SmsMessageManage.as_view('sms_manage')
misc_app.add_url_rule('/sms_message_manage', view_func=sms_message_view, methods=['GET'])


class IncomeExpenseDetailView(MethodView):
    """
    收支明细
    :return:
    """

    @perm_check(perm_module='income_expense_detail')
    @db_session
    def get(self):
        TB_REQUEST_ID = Random.gen_request_id()
        start_bill_date = request.args.get("start_bill_date", '')
        end_bill_date = request.args.get("end_bill_date", '')
        ota_name = request.args.get("ota_name", '')
        trade_type = request.args.get("trade_type", '')
        try:
            if ota_name == '':
                # 认为该情况为初始化页面，将所有provider进行回传
                otas = g.allow_otas
                trade_type_list = []
                for k, v in TRADE_TYPE.iteritems():
                    trade_type_list.append({'value': k.strip(), 'label': v})
                trade_type_list.append({'label': 'all', 'value': 'all'})

                ol = []
                for o in otas:
                    ol.append({'label': o, 'value': o})
                ol.append({'label': 'all', 'value': 'all'})
                return TBResponse({'data': {'ota_name': 'all', 'start_bill_date': '', 'end_bill_date': '', 'trade_type': 'all'}, 'options': {'ota_name': ol, 'trade_type': trade_type_list}})

            else:
                if not start_bill_date:
                    start_bill_date = Time.days_before(30)
                else:
                    start_bill_date = datetime.datetime.strptime(start_bill_date, '%Y-%m-%d')
                if not end_bill_date:
                    end_bill_date = Time.curr_date_obj()
                else:
                    end_bill_date = datetime.datetime.strptime(end_bill_date, '%Y-%m-%d')

                if trade_type == 'all':
                    trade_type_filter = ['INCOME', 'EXPENSE']
                elif trade_type == 'EXPENSE':
                    trade_type_filter = ['EXPENSE']
                elif trade_type == 'INCOME':
                    trade_type_filter = ['INCOME']



                pay_list = select(o for o in IncomeExpenseDetail if start_bill_date < o.pay_time and end_bill_date > o.pay_time and o.trade_type in trade_type_filter)
                if ota_name != 'all':
                    pay_list = pay_list.filter(lambda o: o.flight_order.ota_name == ota_name)
                if '*' not in g.allow_providers:
                    pay_list = pay_list.filter(lambda o: o.flight_order.provider in g.allow_providers)
                if '*' not in g.allow_otas:
                    pay_list = pay_list.filter(lambda o: o.flight_order.ota_name in g.allow_otas)

                pay_list = pay_list.order_by(desc(IncomeExpenseDetail.id))
                data = []
                for p in pay_list:
                    if p.flight_order.ota_pay_price:
                        pax_count = len(p.flight_order.passengers)
                        avg_price = p.flight_order.ota_pay_price / float(pax_count)
                        paxs = []
                        for pax in p.flight_order.passengers:
                            pax = "{ticket_no}:{pax_price};".format(ticket_no=pax.ticket_no, pax_price=avg_price)
                            paxs.append(pax)
                    else:
                        paxs = []
                        for pax in p.flight_order.passengers:
                            pax = "{ticket_no};".format(ticket_no=pax.ticket_no)
                            paxs.append(pax)
                    paxs_str = '<br />'.join(paxs)
                    Logger().sdebug('p.order %s' % p.id)
                    if p.trade_type == 'EXPENSE':
                        if p.expense_source_offline.strip():
                            expense_source = p.expense_source_offline
                        else:
                            expense_source = p.expense_source.source_name
                    else:
                        expense_source = ''
                    data.append(
                        {
                            'ota_name': p.flight_order.ota_name,
                            'provider': p.flight_order.provider,
                            'provider_channel': p.flight_order.provider_channel,
                            'trade_type': {'value': p.trade_type, 'label': TRADE_TYPE[p.trade_type]},
                            'trade_sub_type': {'value': p.trade_sub_type, 'label': TRADE_SUB_TYPE[p.trade_sub_type]},
                            'flight_order_id': p.flight_order.id,
                            'sub_order_id':p.id,
                            'ota_order_id': p.flight_order.ota_order_id,
                            'pay_amount': p.pay_amount,
                            'pay_channel': p.pay_channel,
                            'pax_info': paxs_str,
                            'expense_source': expense_source,
                            'income_source': p.income_source,
                            'pay_result': {'value': p.pay_result, 'label': PAY_RESULT[p.pay_result]},
                            'pay_time': str(p.pay_time),
                            'comment': p.comment,
                            'fo': ''

                        }
                    )

                trade_type_list = []
                for k, v in TRADE_TYPE.iteritems():
                    trade_type_list.append({'value': k.strip(), 'label': v})

                pay_channel_list = []
                for k, v in PAY_CHANNEL.iteritems():
                    pay_channel_list.append({'value': k.strip(), 'label': v})

                trade_sub_type_list = []
                for k, v in TRADE_SUB_TYPE.iteritems():
                    trade_sub_type_list.append({'value': k.strip(), 'label': v})

                pay_result_list = []
                for k, v in PAY_RESULT.iteritems():
                    pay_result_list.append({'value': k.strip(), 'label': v})

                return TBResponse({'data': data, 'options': {'pay_channel.value': pay_channel_list, 'trade_sub_type.value': trade_sub_type_list, 'pay_result.value': pay_result_list,
                                                             'trade_type.value': trade_type_list}})

        except Exception as e:
            Logger().serror(e)
            return TBResponse(str(e), status=500,json_ensure_ascii=False)


income_expense_detail_view = IncomeExpenseDetailView.as_view('income_expense_detail')
misc_app.add_url_rule('/income_expense_detail/',
                      view_func=income_expense_detail_view, methods=['GET', ])


class FusingRepo(MethodView):
    """
    熔断库管理
    :return:
    """

    @perm_check(perm_module='fusing_repo')
    @db_session
    def get(self):
        TB_REQUEST_ID = Random.gen_request_id()

        try:
            frl = FusingControl.fusing_repo_list()
            frl_list = [{'id':k,'fusing_key':k,"fusing_var":v,"fo":''} for k,v in frl.items()]
            return TBResponse({'data':frl_list})
        except Exception as e:
            Logger().serror(e)
            return TBResponse(str(e), status=500,json_ensure_ascii=False)

    @perm_check(perm_module='fusing_repo')
    @db_session
    def post(self):
        """
        接口请求格式
        需要带上 admin的 Zeus-Token
        POST
        http://misc.tourbillon.qisec.cn:9801/misc/fusing_repo/
        {"0":{"fusing_var":"un_key_SHA|201812221000|PZI|201812221400|MU222|N|fakeprovider","fusing_type":"un_key","source":"ppool a down"}}
        :return:
        """
        TB_REQUEST_ID = Random.gen_request_id()

        try:
            req_body = request.get_json()
            Logger().debug(req_body)
            data = req_body.get('0')
            source = data.get('source','web')
            FusingControl.add_fusing(fusing_type=data['fusing_type'],fusing_var=data['fusing_var'],source=source)

            return TBResponse({'ret_code':1})
        except Exception as e:
            Logger().serror(e)
            return TBResponse(str(e), status=500,json_ensure_ascii=False)

    @perm_check(perm_module='fusing_repo')
    @db_session
    def delete(self,fusing_id=None):
        TB_REQUEST_ID = Random.gen_request_id()

        if fusing_id:
            # 删除单条
            try:
                FusingControl.del_fusing(fusing_id)
                return TBResponse({'data':{}})
            except Exception as e:
                Logger().serror(e)
                return TBResponse(str(e), status=500,json_ensure_ascii=False)
        else:
            # 删除整个熔断库
            try:
                FusingControl.del_all_fusing()
                return TBResponse({'data':{}})
            except Exception as e:
                Logger().serror(e)
                return TBResponse(str(e), status=500,json_ensure_ascii=False)

fusing_repo_view = FusingRepo.as_view('fusing_repo')
misc_app.add_url_rule('/fusing_repo/',
                      view_func=fusing_repo_view, methods=['GET','POST' ,'DELETE'])
misc_app.add_url_rule('/fusing_repo/<fusing_id>',
                      view_func=fusing_repo_view, methods=['PUT','DELETE'])



# ---------------------------特殊业务--------------------------------------



class CeairGroupRegister(MethodView):
    """
    东航集团账号集团渠道注册+领取红包
    接收短信
    :return:
    """

    @db_session
    def get(self):
        TB_REQUEST_ID = Random.gen_request_id()
        try:
            cn_last_name = request.args.get('cn_last_name', '')
            cn_first_name = request.args.get('cn_first_name', '')
            en_last_name = request.args.get('en_last_name', '')
            en_first_name = request.args.get('en_first_name', '')
            gender = request.args.get('gender', '')
            birthdate = request.args.get('birthdate', '')
            passport = request.args.get('passport', '')
            mobile = Random.gen_mobile()
            email = Random.gen_email()

            if gender not in ['M', 'F']:
                return TBResponse('gender need F or M', status=500)
            try:
                datetime.datetime.strptime(birthdate, '%Y-%m-%d')
            except Exception as e:
                return TBResponse('birthdate format need 1990-04-09', status=500)

            pax = PaxInfo()
            pax.cn_last_name = cn_last_name
            pax.cn_first_name = cn_first_name
            pax.last_name = en_last_name
            pax.first_name = en_first_name
            pax.gender = gender
            pax.card_pp = passport
            pax.mobile = mobile
            pax.email = email
            pax.birthdate = birthdate

            provider_app = ProviderAutoRepo.select('ceair_group')
            try:
                ffp_account_info = provider_app.register(pax_info=pax)
                provider_app.get_coupon(ffp_account_info)
                return TBResponse("success ffp_no:%s,pwd:%s" % (ffp_account_info.username, ffp_account_info.password))
            except RegisterException as e:
                return TBResponse('register error', status=500)
            except GetCouponException as e:
                return TBResponse('get coupon error', status=500)
        except Exception as e:
            return TBResponse(str(e), status=500)


ceair_group_register_view = CeairGroupRegister.as_view('ceair_group_register')
misc_app.add_url_rule('/ceair_group_register',
                      view_func=ceair_group_register_view, methods=['GET', ])


class CeairRegister(MethodView):
    """
    m.ceair.com 渠道注册+领取红包
    接收短信
    :return:
    """

    @db_session
    def get(self):
        TB_REQUEST_ID = Random.gen_request_id()
        return_status = 'ERROR'
        ret = 'unknown error'
        start_time = Time.timestamp_ms()
        try:
            last_name = request.args.get('last_name', '')
            first_name = request.args.get('first_name', '')
            gender = request.args.get('gender', '')
            birthdate = request.args.get('birthdate', '')
            nationality = request.args.get('nationality', 'CN')
            is_get_coupon = request.args.get('is_get_coupon', '0')
            provider_channel = request.args.get('provider_channel', 'ceair_web_2')
            email = Random.gen_email(domain='chacuo.net')
            cn_name = request.args.get('cn_name', '')
            card_ni = request.args.get('card_ni', '')
            passport = request.args.get('passport', '')

            if last_name == '' and first_name == '' and cn_name == '':
                ret = 'name error'
                return_status = 'ERROR'
            else:
                pax = PaxInfo()

                if cn_name and card_ni:
                    # 说明是国内乘客注册
                    pax.card_ni = card_ni
                    pax.name = cn_name
                    pax.nationality = 'CN'
                    pax.email = email
                    pax.attr_competion()
                    pax_format_check_success = True
                    pax.card_type = 'NI'
                else:
                    pax_format_check_success = True
                    try:
                        if birthdate:
                            datetime.datetime.strptime(birthdate, '%Y-%m-%d')
                        else:
                            raise Exception
                        pax.last_name = last_name
                        pax.first_name = first_name
                        pax.card_pp = passport
                        pax.gender = gender
                        pax.nationality = nationality
                        pax.birthdate = birthdate
                        pax.email = email
                        pax.card_type = 'PP'
                    except Exception as e:
                        ret = 'birthdate format error'
                        return_status = 'ERROR'
                        pax_format_check_success = False

                Logger().sinfo('register pax_info %s' % pax)
                if pax_format_check_success == True:
                    provider_app = ProviderAutoRepo.select(provider_channel)
                    try:
                        ffp_account_info = provider_app.register(pax_info=pax)

                        if is_get_coupon == '1':
                            provider_app.get_coupon(ffp_account_info)
                        ret = {'ret_code': 1, 'username': ffp_account_info.username, 'password': ffp_account_info.password,'modified_card_no':pax.modified_card_no}
                        return_status = 'SUCCESS'

                    except RegisterCritical as e:
                        ret = str(e)
                        return_status = 'ERROR'
                    except RegisterException as e:
                        ret = 'register error'
                        return_status = 'ERROR'
                    except GetCouponException as e:
                        ret = 'get coupon error'
                        return_status = 'ERROR'


        except Exception as e:
            Logger().serror(e)
            ret = str(e)
            return_status = 'ERROR'

        if return_status == 'SUCCESS':
            status = 200
        else:
            status = 500

        total_latency = Time.timestamp_ms() - start_time

        TBG.tb_metrics.write(
            "MISC.API",
            tags=dict(
                return_status=return_status,
                api_name='ceair_web_2.register'
            ),
            fields=dict(
                count=1,
                total_latency=total_latency
            ))

        return TBResponse(ret, status=status)


ceair_register_view = CeairRegister.as_view('ceair_register')
misc_app.add_url_rule('/ceair_register',
                      view_func=ceair_register_view, methods=['GET', ])


class CeairLogin(MethodView):
    """
    m.ceair.com 渠道注册+领取红包
    接收短信
    :return:
    """

    @db_session
    def get(self):
        TB_REQUEST_ID = Random.gen_request_id()
        try:
            username = request.args.get('username', '')
            password = request.args.get('password', '')

            if username == '' or password == '':
                return TBResponse('name error', status=500)

            ffp_account_info = FFPAccountInfo()
            ffp_account_info.username = username
            ffp_account_info.password = password

            provider_app = ProviderAutoRepo.select('ceair_web_2')
            try:
                provider_app.get_coupon(ffp_account_info)
                return TBResponse("success ffp_no:%s,pwd:%s" % (ffp_account_info.username, ffp_account_info.password))
            except RegisterException as e:
                return TBResponse('register error', status=500)
            except GetCouponException as e:
                return TBResponse('get coupon error', status=500)
        except Exception as e:
            return TBResponse(str(e), status=500)


ceair_login_view = CeairLogin.as_view('ceair_login')
misc_app.add_url_rule('/ceair_login',
                      view_func=ceair_login_view, methods=['GET', ])

class SmsReader(MethodView):
    """
    获取最近30秒的短信
    最新一条会显示在最上面
    :return:
    """

    @db_session
    def get(self):
        TB_REQUEST_ID = Random.gen_request_id()
        search_datetime = Time.curr_date_obj() - datetime.timedelta(seconds=30)
        sms_list = select(o for o in SmsMessage if search_datetime < o.create_time ).order_by(desc(SmsMessage.id))
        sms_str = '只显示最近30秒接收到的短信，最新一条会显示在最上面，该接口请勿外泄<br >短信列表:<br >'
        for sms in sms_list:
            sms_str += "【%s】%s<br >"%(sms.create_time,sms.message)
        return TBResponse(sms_str)


sms_reader_view = SmsReader.as_view('sms_reader')
misc_app.add_url_rule('/sms_reader',
                      view_func=sms_reader_view, methods=['GET', ])

class Test(MethodView):
    """
    m.ceair.com 渠道注册+领取红包
    接收短信
    :return:
    """

    @db_session
    def get(self):
        TB_REQUEST_ID = Random.gen_request_id()
        return TBResponse('fff', status=500)


test_view = Test.as_view('test')
misc_app.add_url_rule('/test',
                      view_func=test_view, methods=['GET', ])


class GenRandom(MethodView):
    """
    随机生成信息，目前只包括身份证
    :return:
    """

    @db_session
    def get(self):
        TB_REQUEST_ID = Random.gen_request_id()
        return "%s<br />%s"%(Random.gen_pid(),Random.gen_pid())


gen_random_view = GenRandom.as_view('gen_random')
misc_app.add_url_rule('/gen_random',
                      view_func=gen_random_view, methods=['GET', ])




if __name__ == '__main__':
    pass
