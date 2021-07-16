#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, too-many-arguments, broad-except, anomalous-backslash-in-string
# pylint: disable=missing-docstring, line-too-long, too-few-public-methods
"""
# @Author  : wxt
# @Software: PyCharm
"""


from app.utils.blowfish import Blowfish


if __name__ == '__main__':
    print Blowfish().decryptCTR('Liw5a0pli/Z/yiL/EEBqRtaULdJ6C1I8VSA8rYxLpys5PgoLwUQFhUi4juoc7SM7WSF1+7QOtvViALPofVflTjxUZkP2gwF93LxWxbzENd21+dA2AL7EWh+kuFhJ7w==')