# -*- coding: utf-8 -*-
import functools
import time
import copy
from . import misc_app
from flask import Response, g
from flask import jsonify
from flask import request
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, SignatureExpired, BadSignature
from ...utils.logger import Logger
from app import TBG

######################################### 界面相关 ###############################################

SECRET_KEY = 'fdsafdsafdasfdsafdas'
TOKEN_EXPIRED_TIME = 3600 * 24 * 365


@misc_app.before_request
def zeus_auth():
    # 验证
    g.user = None
    verify_user_list = TBG.global_config['USER_LIST']
    token = request.headers.get('Zeus-Token') or ""

    try:
        s = Serializer(SECRET_KEY)
        data = s.loads(token)
        username = data['user_id']
        Logger().sdebug('username %s' % username)
        if username in verify_user_list:
            g.user = username
            group = verify_user_list[username]['group']
            g.allow_providers = TBG.global_config['GROUP_PERM'][group]['order_view']['providers']
            otas = copy.deepcopy(TBG.global_config['GROUP_PERM'][group]['order_view']['otas'])
            if '*' not in otas:
                # 需要加入自己组的user
                otas.extend([user for user,data in verify_user_list.iteritems() if data['group'] == group])
            g.allow_otas = otas
            Logger().sdebug('g.allow_otas %s'% g.allow_otas)
            Logger().sdebug('g.allow_providers %s' % g.allow_providers)
    except SignatureExpired:
        pass
    except BadSignature:
        pass
    except Exception:
        pass

@misc_app.before_request
def init_audit_module():
    # 初始化审计日志相关变量
    g.audit_category = ''
    g.audit_comment = ''
    g.audit_operation = ''

# @misc_app.before_request
# def init_audit_module():
#     # 初始化审计日志相关变量
#     g.audit_category = ''
#     g.audit_comment = ''
#     g.audit_operation = ''
#
#
# @misc_app.teardown_request
# def teardown(e):
#     current_app.redq_meta_db.close()
#     current_app.redq_log_db.close()


@misc_app.route('/login', methods=['POST'])
def login():
    req_body = request.get_json()
    userlist = TBG.global_config['USER_LIST']
    for username, data in userlist.iteritems():
        password = data['password']
        if req_body['username'] == username and req_body['password'] == password:
            expired = (int(time.time()) + TOKEN_EXPIRED_TIME) * 1000
            s = Serializer(SECRET_KEY, expires_in=TOKEN_EXPIRED_TIME)
            userinfo = TBG.global_config['USER_LIST'][req_body['username']]
            group = userinfo['group']
            ss = {'user_id': username,'group':group}
            Logger().sdebug('token, %s' % ss)
            token = s.dumps(ss)
            Logger().sdebug('token, %s'% token)
            return jsonify({'username': username, 'expired': expired, 'token': token,'group':group})
    return Response('error', status=500)


def perm_check(perm_module):
    def real_warp(func):
        @functools.wraps(func)
        def _wrap(*args, **kw):
            is_allow = False
            if g.user and g.user in TBG.global_config['USER_LIST']:
                userinfo = TBG.global_config['USER_LIST'][g.user]
                group = userinfo['group']
                perm_list = TBG.global_config['GROUP_PERM'][group]['misc_api']
                if '*' in perm_list or perm_module in perm_list:
                    is_allow = True
            if is_allow:
                try:
                    rsp_body = func(*args, **kw)
                    return rsp_body
                except Exception as e:
                    Logger().serror(e)
                    return Response(e, status=500)
            else:
                return Response('no permssion', status=500)

        return _wrap

    return real_warp
