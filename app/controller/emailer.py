#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, too-many-arguments, broad-except, anomalous-backslash-in-string
# pylint: disable=missing-docstring, line-too-long, too-few-public-methods
"""
# @Author  : wxt
# @Software: PyCharm
"""

import functools
import gevent
import poplib
import time
import re
from app import TBG
from ..utils.exception import *
from email.parser import Parser
from email.header import decode_header
from email.utils import parseaddr
from ..utils.logger import Logger


def email_lock():

    def real_warp(func):
        @functools.wraps(func)
        def _wrap(*args, **kw):
            receiver = kw['receiver']
            rsp_body = func(*args, **kw)
            if rsp_body:
                success = 1
            else:
                success = 0

            TBG.tb_metrics.write(
                "FRAMEWORK.EMAIL_RECV",
                tags=dict(
                    email_func=func.__name__,
                    receiver=receiver,
                    success=success
                ),
                fields=dict(
                    count=1
                ))
            return rsp_body

        return _wrap

    return real_warp


class Mailer(object):
    def __init__(self, user, password, server):
        self.user = user
        self.password = password
        self.server = server
        self.server_ins = None
        self.recv_tries = 3  # 邮件尝试次数

    @email_lock()
    def get_mail_via_receiver(self, receiver):
        """
        通过收件人名称获取邮件内容
        从最新的一封开始向后遍历，如果获取到此邮件则进行删除，防止邮件过多
        :param reciver:
        :return:
        """
        Logger().sinfo('get_mail_via_receiver %s' % receiver)
        mail = None
        try:
            tries = 0
            is_recved = False
            while 1:
                if is_recved == True:
                    break
                gevent.sleep(10)
                self.server_ins = poplib.POP3(self.server)
                # server.set_debuglevel(1)
                self.server_ins.getwelcome()
                # 认证:
                self.server_ins.user(self.user)
                self.server_ins.pass_(self.password)
                Logger().sinfo('Messages: %s. Size: %s' % self.server_ins.stat())
                resp, mails, octets = self.server_ins.list()
                hit_count = 0
                for email_num in xrange(len(mails), 1, -1):
                    msg = self.get_mail(email_num)
                    if hit_count > 10:
                        break
                    else:
                        hit_count +=1
                    if msg['to'] == receiver:
                        # 获取到指定邮件
                        mail = msg['content']
                        if mail:
                            Logger().sdebug('mail content %s' % mail)
                            is_recved = True
                            break

                if tries < self.recv_tries:
                    tries += 1
                else:
                    break
        except Exception as e:
            Logger().serror('get_checkcode_via_reciver error')
            raise
        self.server_ins.quit()
        return mail

    def get_mail(self, num):
        resp, lines, octets = self.server_ins.retr(num)
        msg = Parser().parsestr('\r\n'.join(lines))
        formated_msg = {"from": '', 'to': '', 'content': '', 'subject': ''}
        self.print_info(msg, formated_msg)
        return formated_msg

    def delete_mail(self, num):
        self.server_ins.dele(num)

    def guess_charset(self, msg):
        charset = msg.get_charset()
        if charset is None:
            content_type = msg.get('Content-Type', '').lower()
            pos = content_type.find('charset=')
            if pos >= 0:
                charset = content_type[pos + 8:].strip()
        return charset

    def decode_str(self, s):
        value, charset = decode_header(s)[0]
        if charset:
            value = value.decode(charset)
        return value

    def print_info(self, msg, formated_msg, indent=0):
        if indent == 0:
            for header in ['From', 'To', 'Subject']:
                value = msg.get(header, '')
                if value:
                    if header == 'Subject':
                        value = self.decode_str(value)
                        formated_msg['subject'] = value
                    else:
                        hdr, addr = parseaddr(value)
                        if header == 'From':
                            formated_msg['from'] = addr
                        elif header == 'To':
                            formated_msg['to'] = addr
                            # print('%s%s: %s' % ('  ' * indent, header, value))
        if (msg.is_multipart()):
            parts = msg.get_payload()
            for n, part in enumerate(parts):
                # print('%spart %s' % ('  ' * indent, n))
                # print('%s--------------------' % ('  ' * indent))
                self.print_info(part, formated_msg, indent + 1)
        else:
            content_type = msg.get_content_type()
            if content_type == 'text/plain' or content_type == 'text/html':
                content = msg.get_payload(decode=True)
                charset = self.guess_charset(msg)
                if charset:
                    content = content.decode(charset)
                formated_msg['content'] += content
                # print('%sText: %s' % ('  ' * indent, content + '...'))


if __name__ == '__main__':
    server = 'imap.exmail.qq.com'
    user = 'fvck@tongdun.org'
    password = 'XrczRNDTBwBRvaPH'
    mail = Mailer(user=user, password=password, server=server)
    print mail.get_checkcode_via_reciver(receiver='cewjkjl@tongdun.org',provider='ceair_hk')
