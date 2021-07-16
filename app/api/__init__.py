#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, too-many-arguments, broad-except, anomalous-backslash-in-string
# pylint: disable=missing-docstring, line-too-long, too-few-public-methods
"""
# @Author  : wxt
# @Software: PyCharm
"""
import inspect
import json
from flask import Response
from ..utils.logger import Logger

class TBResponse(Response):
    """
    将返回整理成json格式，并且添加request_id
    """
    def __init__(self, response, **kwargs):
        json_ensure_ascii = kwargs.pop('json_ensure_ascii',True)
        if kwargs.get('status',200) == 500:
            Logger().sdebug('status 500')
            lf = inspect.currentframe()
            last_request_id = ''

            for x in range(0,30):
                lf = lf.f_back

                if (last_request_id ) or lf == None:
                    break

                if not last_request_id and 'TB_REQUEST_ID' in lf.f_locals:
                    last_request_id = lf.f_locals['TB_REQUEST_ID']
            kwargs['mimetype'] = 'application/json'
            response = json.dumps({'msg':response,'ret_code':2,'request_id':last_request_id},ensure_ascii=json_ensure_ascii)

        elif isinstance(response,dict):
            if not kwargs.get('mimetype',''):
                kwargs['mimetype'] = 'application/json'
            lf = inspect.currentframe()
            last_request_id = ''

            for x in range(0, 30):
                lf = lf.f_back

                if (last_request_id ) or lf == None:
                    break

                if not last_request_id and 'TB_REQUEST_ID' in lf.f_locals:
                    last_request_id = lf.f_locals['TB_REQUEST_ID']
            response['request_id'] = last_request_id
            response = json.dumps(response)
        # Logger().sdebug('TBResponse response %s' % response)
        return super(TBResponse, self).__init__(response, **kwargs)

if __name__ == '__main__':
    pass