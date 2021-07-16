#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, too-many-arguments, broad-except, anomalous-backslash-in-string
# pylint: disable=missing-docstring, line-too-long, too-few-public-methods
"""
# @Author  : wxt
# @Software: PyCharm
三方数据辅助查询模块
"""

import requests
from app import TBG
from ..utils.logger import Logger
from ..dao.iata_code import BUDGET_AIRLINE_CODE


class DomesticTaxAux(object):
    """
    国内税费查询，依赖三方接口
            {
        "error_code": 0,
        "reason": "成功",
        "result": [
        {
        "CabinDesc": null,
        "CabinType": "F",
        "basicCabinType": "F",
        "MoneyType": "CNY",
        "FarePrice": null,
        "SinglePrice": "1220.00",
        "RoundPrice": "2440.00",
        "PolicyCode": null,
        "discountRate": "151",
        "startDate": "2007-05-29",
        "endDate": "2019-12-27",
        "airline": "8C",
        "AirportTax": "50",
        "fuelTax": "10",
        "rule": "0001 PFN:01",
        "Points": null,
        "TradePrice": null,
        "ChdPrice": null,
        "orgCity": "SHA",
        "dstcity": "WUH"
        }]
        }
    """


    @staticmethod
    @TBG.fcache.memoize(86400) # 一天后过期
    def query(from_airport, to_airport, age_type='ADT'):
        """
        查询
        先查询缓存，如果缓存无命中，查询接口，如果接口无命中，返回0

        :param from_airport: 出发地
        :param to_airport:  目的地
        :param age_type:  ADT 成人  CHD 儿童 不支持婴儿
        :return:
        """

        try:
            ret = None
            param_model = {
                'from_airport': from_airport,
                'to_airport': to_airport,
                'age_type': age_type
            }
            ret = TBG.cache_access_object.get(cache_type='domestic_tax', provider='all', param_model=param_model)
            if ret:
                Logger().sdebug('cache search domestic tax result %s' % ret)

            else:
                req_has_exception = 0
                no_data = 0
                success = 0
                if age_type == 'ADT':
                    pass_type = 'AD'
                else:
                    pass_type = 'CH'

                url = "http://apis.haoservice.com/efficient/flight/fd?orgCity=%s&dstCity=%s&passType=%s&key=187f8946351d4efb93d0624b97bdad2f" % (from_airport, to_airport, pass_type)
                try:
                    response = requests.request("GET", url, timeout=3).json()
                    if response['error_code'] == 0 and response['result']:
                        airport_tax = response['result'][0]['AirportTax']
                        if airport_tax is None:
                            airport_tax = 0
                        else:
                            airport_tax = int(airport_tax)
                        fuel_tax = response['result'][0]['fuelTax']
                        if fuel_tax is None:
                            fuel_tax = 0
                        else:
                            fuel_tax = int(fuel_tax)
                        rt_tax = fuel_tax + airport_tax
                        ret = {'tax':rt_tax}
                        Logger().sdebug('realtime search domestic tax result %s' % ret)
                        TBG.cache_access_object.insert(cache_type='domestic_tax', provider='all', param_model=param_model, ret_data=ret, expired_time=2592000)  # 2592000 一个月的秒，默认一个月过期
                        success = 1
                    else:
                        no_data = 1
                        raise Exception('no data')
                except Exception as e:
                    req_has_exception = 1
                    Logger().serror('haoservice request error')
                TBG.tb_metrics.write(
                    "AUX.DOMESTIC_TAX.QUERY_API",
                    tags=dict(
                        from_to_airport_age_type = '%s-%s-%s' % (from_airport,to_airport,age_type)
                    ),
                    fields=dict(
                        total_count=1,
                        error_count=req_has_exception,
                        no_data_count=no_data,
                        success_count=success
                    ))
        except Exception as e:
            Logger().serror('domestic tax error')
            has_exception = 1

        Logger().sdebug('final search domestic tax result %s' % ret)

        if ret is None:

            # 返回不同类型的默认值
            if age_type == 'ADT':
                return 80
            else:
                return 10
        else:
            return ret['tax']


class LowestCabinAux(object):
    """
    使用Eterm 查询航班最低仓位
    1. 最低舱由航司统一规定
    2. 每个航班可售最低舱不一致，需要使用AVH 查询，查询单位 航班，不限日期
    """


    @staticmethod
    @TBG.fcache.memoize(86400) # 一天后过期
    def query(flight_number,carrier=None):
        """
        查询
        先查询缓存，如果缓存无命中，查询接口，如果接口无命中，返回0

        :param flight_number rk的聚合航班号
        :param carrier 航司，用于区分廉航非廉航
        :return:
        """
        ret = None
        try:

            success = 1
            if carrier in BUDGET_AIRLINE_CODE:
                ret = 'Y'
            else:

                param_model = {
                    'flight_number': flight_number,
                }
                ret = TBG.cache_access_object.get(cache_type='lowest_cabin', provider='all', param_model=param_model)
                if ret:
                    Logger().sdebug('cache search lowest cabin result %s' % ret)

                else:

                    # TODO 黑屏查询逻辑
                    # for test
                    if flight_number in ['DZ222','MU1932']:
                        ret = None
                        # ff
                    else:
                        ret = 'U' # TODO TEST
                    TBG.cache_access_object.insert(cache_type='lowest_cabin', provider='all', param_model=param_model, ret_data=ret, expired_time=2592000)  # 2592000 一个月的秒，默认一个月过期

            TBG.tb_metrics.write(
                "AUX.LOWEST_CABIN",
                tags=dict(
                    flight_number=flight_number
                ),
                fields=dict(
                    total_count=1,
                    success_count=success
                ))
        except Exception as e:
            Logger().serror('lowest_cabin error')
            has_exception = 1

        Logger().sdebug('final search lowest cabin result %s' % ret)

        return ret


if __name__ == '__main__':
    pass
