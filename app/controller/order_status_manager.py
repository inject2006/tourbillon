#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, too-many-arguments, broad-except, anomalous-backslash-in-string
# pylint: disable=missing-docstring, line-too-long, too-few-public-methods
"""
# @Author  : wxt
# @Software: PyCharm
"""
import requests
from ..dao.models import PROVIDER_ORDER_STATUS, OTA_ORDER_STATUS,PROVIDERS_STATUS
from ..utils.logger import Logger
from app import TBG
from ..controller.pokeman import Pokeman


class OrderStatusManager(object):
    """
    状态正确性检测，
    如果是错误状态则直接转人工
    """

    @staticmethod
    def verify_format(status):
        if status in PROVIDER_ORDER_STATUS or status in PROVIDERS_STATUS :
            return True
        else:
            return False

    @staticmethod
    def manual_intervention(status, order_info):
        """
        通知人工进行介入
        :param status:
        :param order_info:
        :return:
        """
        # TODO 后续准备采用GEVENT 异步
        if TBG.global_config['RUN_MODE'] == 'PROD':
            try:
                content = ''
                if OrderStatusManager.verify_format(status):
                    status_info = PROVIDER_ORDER_STATUS[status]
                    if status_info['status_type'] == 'fail':
                        subject = u'有订单需要人工介入'
                        content = u"主订单号：{flight_order_id}\n子订单号：{sub_order_id}\nOTA：{ota_name}\n供应商渠道名称：{provider_channel}\n供应商订单状态：{provider_order_status}\n供应商价格：{provider_price}\n供应商订单号：{provider_order_id}\n关联账号：{ffp_account_username}\n关联账号密码：{ffp_account_password}\nOTA名称：{ota_name}\n出发时间：{from_date}\n出发地机场：{from_airport}\n目的地机场：{to_airport}\n国际/国内：{routing_range}\n单程/往返：{trip_type}\n成人数：{adt_count}\n儿童数：{chd_count}".format(
                            flight_order_id=order_info.flight_order_id,sub_order_id=order_info.sub_order_id,provider_channel=order_info.provider_channel, provider_order_status=PROVIDER_ORDER_STATUS.get(order_info.provider_order_status,{'cn_desc':''})['cn_desc'],
                            provider_price=order_info.provider_price, ffp_account_username=order_info.ffp_account.username if order_info.ffp_account else '',
                            ffp_account_password=order_info.ffp_account.password if order_info.ffp_account else '',from_date=order_info.from_date,
                            from_airport=order_info.from_airport, to_airport=order_info.to_airport,
                            routing_range=order_info.routing_range,
                            trip_type=order_info.trip_type, adt_count=order_info.adt_count, chd_count=order_info.chd_count,
                            provider_order_id=order_info.provider_order_id,ota_name=order_info.ota_name
                        )
                        Pokeman.send_wechat(content=content,subject=subject,agentid=1000011,level='warning')
                    else:
                        return False
            except Exception as e:
                Logger().serror('manual_intervention error')
            Logger().swarn(u'manual_intervention {content}'.format(content=content))
        return True


if __name__ == '__main__':
    pass
