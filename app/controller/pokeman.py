#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, too-many-arguments, broad-except, anomalous-backslash-in-string
# pylint: disable=missing-docstring, line-too-long, too-few-public-methods
"""
# @Author  : wxt
# @Software: PyCharm
"""

import requests
from ..utils.logger import Logger


class Pokeman(object):
    """
    消息推送模块

    """
    wechat_url = "http://10.0.7.6:10000/bpns/event"

    @staticmethod
    def send_wechat(content,subject,agentid=1000011,level="info"):
        """
        发送微信
        :return:
        """
        try:
            requests.post(Pokeman.wechat_url, json={
                "product": "tourbillon",
                "team": "dev",
                "source": "tourbillon",
                "category": "",
                "level": level,
                "subject": subject,
                "content":content ,
                "sendto_wechat": {
                    "agentid": agentid,
                    "msgtype": "text",
                }
            }, timeout=3)
        except Exception as e:
            Logger().serror(e)

if __name__ == '__main__':
    pass