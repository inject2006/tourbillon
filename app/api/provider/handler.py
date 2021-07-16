#coding=utf8

from . import provider_app
from ...dao.models import *
from ...utils.exception import *
from ...automatic_repo.base import ProviderAutoRepo
from ...utils.logger import Logger, logger_config
from ...utils.util import Time, Random
from ...dao.internal import ERROR_STATUS
from flask import request, jsonify, Response
from app import TBG
from ...api import TBResponse




@provider_app.route('/notice_issue', methods=['POST'])
@logger_config('PAPI_NOTICE_ISSUE', frame_id=False)
def notice_issue():

    provider_name = request.args.get("__name", '')
    provider_token = request.args.get("__token", '')
    ret_status = 'INNER_ERROR_1002'
    req_body = request.data
    try:

        if provider_name:
            provider_app = ProviderAutoRepo.select(provider_name)
            if provider_app.provider_token != provider_token:
                raise ProviderTokenException('provider %s,token %s' % (provider_name, provider_token))
        Logger().sinfo('{provider_name} notice_issue_api request  {req_body}'.format(provider_name=provider_name,
                                                                                     req_body=req_body))
        provider_app.work_flow = 'notice_issue'
        provider_app.notice_issue_interface(req_body)
        ret = provider_app.final_result
        Logger().sinfo('{provider_name} notice_issue_api return Success '.format(provider_name=provider_name))
        return Response(ret, mimetype='text/plain')

    except NoSuchProviderException as e:
        ret_status = 'INNER_ERROR_1001'
    except ProviderTokenException as e:
        ret_status = 'INNER_ERROR_1003'
    except Exception as e:
        Logger().serror(
            '{provider_name} notice_issue_api return Failed ret_status: {ret_status}'.format(provider_name=provider_name,
                                                                                             ret_status=ret_status))
    ret = {'status': ret_status, 'msg': ERROR_STATUS[ret_status]}
    return TBResponse(ret, mimetype='text/plain')


@provider_app.route('/notice_flight_change', methods=['POST'])
@logger_config('PAPI_NOTICE_FLIGHT_CHANGE', frame_id=False)
def notice_flight_change():

    provider_name = request.args.get("__name", '')
    provider_token = request.args.get("__token", '')
    ret_status = 'INNER_ERROR_1002'
    req_body = request.data
    try:

        if provider_name:
            provider_app = ProviderAutoRepo.select(provider_name)
            if provider_app.provider_token != provider_token:
                raise ProviderTokenException('provider %s,token %s' % (provider_name, provider_token))
        Logger().sinfo('{provider_name} notice_flight_change_api request  {req_body}'.format(provider_name=provider_name,
                                                                                     req_body=req_body))
        provider_app.work_flow = 'notice_flight_change'
        provider_app.notice_flight_change_interface(req_body)
        ret = provider_app.final_result
        Logger().sinfo('{provider_name} notice_flight_change_api return Success '.format(provider_name=provider_name))
        return Response(ret, mimetype='text/plain')

    except NoSuchProviderException as e:
        ret_status = 'INNER_ERROR_1001'
    except ProviderTokenException as e:
        ret_status = 'INNER_ERROR_1003'
    except Exception as e:
        Logger().serror(
            '{provider_name} notice_flight_change_api return Failed ret_status: {ret_status}'.format(provider_name=provider_name,
                                                                                             ret_status=ret_status))
    ret = {'status': ret_status, 'msg': ERROR_STATUS[ret_status]}
    return TBResponse(ret, mimetype='text/plain')


if __name__ == '__main__':
    pass
