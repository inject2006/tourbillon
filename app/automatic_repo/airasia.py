#!/usr/bin/env python
# -*- coding: utf-8 -*-

import gevent
import json
import datetime
import random
import string
from lxml import etree
from .base import ProvderAutoBase
from ..dao.internal import *
from ..utils.util import RoutingKey
from ..controller.captcha import CaptchaCracker
from ..controller.http_request import HttpRequest
from app.dao.iata_code_new import AIRASIA_IATA_CODE
from app import TBG


class Airasia(ProvderAutoBase):
    timeout = 50  # 请求超时时间
    provider = 'airasia'  # 子类继承必须赋
    provider_channel = 'airasia_web'  # 子类继承必须赋
    operation_product_type = '会员折扣'  # 运价类型：0: GDS公布运价 1:GDS私有运价 2:航司官网产品  3:廉价航司产品 4:特价产品
    operation_product_mode = 'A2B'
    pay_channel = 'ALIPAY'
    is_display = True
    no_flight_ttl = 3600 * 3 # 无航班缓存超时时间设定
    carrier_list = ['AK','D7']  # 供应商所包含的航司列表，如果包含多个并且无法确定，请不要填写，此处会关联执飞航线判断逻辑

    CACHE_PR_CONFIG = {
        1: {'cabin_expired_time': 3600 * 12, 'cabin_attenuation': 3,'fare_expired_time':86400 * 30},
        2: {'cabin_expired_time': 3600 * 3, 'cabin_attenuation': 2,'fare_expired_time':86400 * 20},
        3: {'cabin_expired_time': 60 * 60 * 1, 'cabin_attenuation': 1,'fare_expired_time':86400 * 10},
        4: {'cabin_expired_time': 60 * 40, 'cabin_attenuation': 1,'fare_expired_time':86400 * 5},
        5: {'cabin_expired_time': 60 * 30, 'cabin_attenuation': 0,'fare_expired_time':86400},

    }

    search_interval_time = 1

    def __init__(self):
        super(Airasia, self).__init__()

        self.booking_retries = 3
        self.ota_fare_search_tries = 5

        self.account_list = [
            {'username': '630131222@qq.com', 'password': 'Bigsec2018', 'customer_id': '4790279042'},
            {'username': 'xp.wang@bigsec.com', 'password': 'Bigsec2018', 'customer_id': '8670301151'}
        ]
        if not TBG.redis_conn.redis_pool.llen('airasia_account_list') == len(self.account_list):
            TBG.redis_conn.redis_pool.expire('airasia_account_list', 0)
            for account in self.account_list:
                TBG.redis_conn.redis_pool.lpush('airasia_account_list', account)



    def _pre_order_check(self, http_session, order_info):
        """
        订单预检

        :param http_session:
        :param order_info:
        :return:
        """

        return 'CHECK_SUCCESS'

    def _order_split(self, order_info):
        """
        拆单原则：一个成年人只能带两个小孩，一单最多可以有五个乘机人
        最多拆三单
        :param order_info:
        :return:
        """


        rl = []
        adt_list = [x for x in order_info.passengers if x.current_age_type(from_date=order_info.from_date, is_aggr_chd_adt=True) == 'ADT']
        chd_list = [x for x in order_info.passengers if x.current_age_type(from_date=order_info.from_date, is_aggr_chd_adt=True) == 'CHD']
        for contact in order_info.contacts:
            break

        if not chd_list:
            allow_next = True
        else:
            allow_next = False

        sub_order_set = [[], [], []]
        sub_order_index = 0
        while 1:
            if not chd_list:
                break

            for x in range(2):
                if chd_list and len(sub_order_set[sub_order_index]) < 5:
                    sub_order_set[sub_order_index].append(chd_list.pop())
            sub_order_index += 1
            sub_order_index = sub_order_index % 3

        sub_order_index = 0
        while 1:
            Logger().debug('adt_list %s allow_next %s sub_order_index %s  sub_order_set %s'%(adt_list,allow_next,sub_order_index,sub_order_set))
            if not adt_list:
                break
            if allow_next and adt_list:
                sub_order_set[sub_order_index].append(adt_list.pop())
                allow_next = False
            if len(sub_order_set[sub_order_index]) == 5:
                allow_next = True
            elif sub_order_set[sub_order_index] and adt_list:
                sub_order_set[sub_order_index].append(adt_list.pop())
            sub_order_index += 1
            sub_order_index = sub_order_index % 3

        for s in sub_order_set:
            if s:
                rl.append({'passengers': s, 'contacts': [contact]})

        Logger().sdebug('split_order %s' % rl)
        return rl


    def _login(self, http_session, ffp_account_info):
        """
        登陆模块
        :return: 登陆成功的httpResult 对象
        """

        url = 'https://ssor.airasia.com/config/v2/clients/by-origin'
        http_session.update_headers({
            'Referer': 'https://www.airasia.com/cn/zh/home.page',
            'Content-Type': 'application/json',
            'Origin': 'https://www.airasia.com',
            'Accept': 'application/json',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
        })
        result = http_session.request(url=url, method='GET', verify=False).to_json()
        print(result)
        gevent.sleep(0.3)

        api_key = result.get('apiKey')
        client_id = result.get('id')

        if not api_key:
            raise LoginException('have no api key in client origin')

        post_data = {
            "username": ffp_account_info.username,
            "password": ffp_account_info.password,
        }
        url = 'https://ssor.airasia.com/sso/v2/authorization/by-credentials?clientId={}&gaClientId='.format(client_id)
        http_session.update_headers({'x-api-key': api_key})
        result = http_session.request(url=url, method='POST', json=post_data, verify=False).to_json()
        print result
        gevent.sleep(0.3)

        access_token = result.get('accessToken')
        refresh_token = result.get('refreshToken')
        user_id = result.get('userId')

        url = 'https://booking.airasia.com/Member/InternalLoginWidget'
        post_data = {
            'AirAsiaSsoWidgetLogin.accessToken': access_token,
            'AirAsiaSsoWidgetLogin.refreshToken': refresh_token,
            'AirAsiaSsoWidgetLogin.userId': user_id,
        }
        http_session.update_headers({
            'Content-Type': 'application/x-www-form-urlencoded'
        })
        result = http_session.request(url=url, method='POST', data=post_data, verify=False).to_json()

        http_session.update_headers({
            'Authorization': access_token,
            'x-api-key': api_key,
            'x-aa-client-id': client_id,
            'x-ga-client-id': '',
            # 'Content-Type': 'application/json',
        })

        gevent.sleep(0.5)
        login_result = self._check_login(http_session)
        if login_result:
            return http_session
        else:
            raise LoginException('login failed')

    def _check_login(self, http_session):
        """
        检查登录状态
        :param http_session:
        :return:
        """

        try:
            if not http_session.get_cookies():
                return False
            user_login_info = http_session.get_cookies().get('userLogin')
            if not user_login_info:
                return False
            user_id = user_login_info.split('userid=')[-1]
            url = 'https://ssor.airasia.com/um/v2/users/{}'.format(user_id)
            result = http_session.request(url=url, method="GET", verify=False)
            if not result.content:
                return False
            result = result.to_json()
            if result.get('status') == 'active':
                return True
            else:
                return False
        except:
            import traceback
            Logger().error(traceback.format_exc())
            return False

    def _register(self, http_session, pax_info, ffp_account_info):
        """
        注册模块
        """

        account = TBG.redis_conn.redis_pool.rpoplpush('airasia_account_list', 'airasia_account_list')
        account = eval(account) if account else random.choice(self.account_list)
        ffp_account_info.username = account['username']
        ffp_account_info.password = account['password']
        ffp_account_info.reverse1 = account['customer_id']
        ffp_account_info.provider = self.provider
        return ffp_account_info

    def generate_routing_key(self, product):

        segment_list = product['segment_info']

        dep_time = '{} {}00'.format(segment_list[0]['depDate'], segment_list[0]['depTime'])
        arr_time = '{} {}00'.format(segment_list[-1]['arrDate'], segment_list[-1]['arrTime'])

        adult_price = 0.0
        adult_tax = 0.0
        child_price = 0.0
        child_tax = 0.0
        inf_price = 0.0
        inf_tax = 0.0
        for segment in segment_list:
            try:
                adult_price += int(product['cabin_info']['fbcList'][0]['adPrice'])
                adult_tax_list = [i for i in product['cabin_info']['fbcList'][0]['taxList'] if i['taxType'] == 'ADT']
                for t in adult_tax_list:
                    adult_tax += int(t['taxPrice'])

                child_price += int(product['cabin_info']['fbcList'][0]['chPrice'])
                child_tax_list = [i for i in product['cabin_info']['fbcList'][0]['taxList'] if i['taxType'] == 'CHD']
                for t in child_tax_list:
                    child_tax += int(t['taxPrice'])
            except Exception as e:
                Logger().debug(e)

        rk_info = RoutingKey.serialize(from_airport=segment_list[0]['dep'], dep_time=datetime.datetime.strptime(dep_time, '%Y%m%d %H%M%S'),
                                       to_airport=segment_list[-1]['arr'], arr_time=datetime.datetime.strptime(arr_time, '%Y%m%d %H%M%S'),
                                       flight_number=segment_list[0]['fltNo'],
                                       cabin=product['cabin_info']['adClass'],
                                       product='COMMON',
                                       adult_price=adult_price, adult_tax=adult_tax, provider_channel=self.provider_channel,
                                       child_price=child_price, child_tax=child_tax,
                                       inf_price=inf_price, inf_tax=inf_tax,provider=self.provider)  # 供应商渠道写死为 奥凯



        return rk_info['plain'],rk_info['encrypted'], adult_price, adult_tax, child_price, child_tax

    def _pre_flight_search(self, acw_tc, acw_sc_v3, search_url):

        http_session = HttpRequest()
        http_session.update_headers({'Referer': 'https://www.airasia.com/cn/zh/home.page',
                                     'Upgrade-Insecure-Requests': '1',
                                     })
        http_session.update_cookie({
            'acw_sc_v3': acw_sc_v3,
            'acw_tc': acw_tc
        })
        result = http_session.request(url=search_url, method='GET', verify=False)
        if self.origin_product_list:
            Logger().debug("================ 1 ============")
            Logger().debug(self.origin_product_list)
            self.high_req_limit = False
            return
        if result.current_url == 'https://booking.airasia.com/':
            self.high_req_limit = True
            return
        html = etree.HTML(result.content)
        product_list = html.xpath('//input[@class="square-radio radio-markets"]')
        cabin_list = html.xpath('//div[@class="avail-table-seats-remaining"]')
        if product_list:
            Logger().debug("================= 2 ==================")
            Logger().debug(product_list)
            self.origin_product_list.extend(product_list)
            self.cabin_count_list.extend(cabin_list)
            self.high_req_limit = False

    def _flight_search(self, http_session, search_info):
        """
        航班爬取模块，
        TODO :目前只考虑单程
        :return:
        """

        try:

            Logger().debug('search flight')

            from_airport = search_info.from_airport if not search_info.from_airport == 'SHA' else 'PVG'
            to_airport = search_info.to_airport if not search_info.to_airport == 'SHA' else 'PVG'
            search_url = 'https://booking.airasia.com/Flight/Select?s=false&o1={}&d1={}&ADT={}&CHD={}&dd1={}&mon=true&cc=CNY&inl=0'.format(
                from_airport, to_airport, search_info.adt_count, 1, search_info.from_date)

            # search_session_valid = False
            # origin_product_list = []
            # cabin_count_list = []
            # # 搜索不涉及会员相关操作，只用来获取一次会员价， 使用固定账号登录搜索
            # username = 'xp.wang@bigsec.com'
            # password = 'Bigsec2018'
            # query_params = {'username': username, 'password': password}
            # Logger().sinfo('Login Start {query_params}'.format(query_params=query_params))
            # login_headers = TBG.cache_access_object.get(cache_type='login_headers', provider=self.provider,
            #                                         param_model=query_params)
            # login_session = TBG.cache_access_object.get(cache_type='login_session', provider=self.provider,
            #                                         param_model=query_params)
            # if login_session:
            #     # 如果有会员登录session，尝试直接搜索
            #     Logger().sdebug('login_headers %s' % login_headers)
            #     Logger().sdebug('login_session %s' % login_session)
            #     if login_headers:
            #         http_session.update_headers(login_headers)
            #     http_session.update_cookie(login_session)
            #
            #     result = http_session.request(url=search_url, method='GET', proxy_mode='anti_block_wait',
            #                                   provider_channel=self.provider_channel, verify=False)
            #     html = etree.HTML(result.content)
            #     big_member_flag = html.xpath(
            #         '//div[@class="dv-bigmember-discount-applied dv-bigmember-discount-two-fare"]/text()')
            #     origin_product_list = html.xpath('//input[@class="square-radio radio-markets"]')
            #     if not origin_product_list:
            #         Logger().warn('airasia no flight')
            #         return search_info
            #     if big_member_flag:
            #         search_session_valid = True
            #         cabin_count_list = html.xpath('//div[@class="avail-table-seats-remaining"]')
            # if not search_session_valid:
            #     # 没有会员登录session，或session失效，则重新登录搜索
            #     ffp_account_info = FFPAccountInfo()
            #     ffp_account_info.username = 'xp.wang@bigsec.com'
            #     ffp_account_info.password = 'Bigsec2018'
            #     http_session = self.login(http_session, ffp_account_info)
            #
            #     result = http_session.request(url=search_url, method='GET', proxy_mode='anti_block_wait',
            #                                   provider_channel=self.provider_channel, verify=False)
            #     html = etree.HTML(result.content)
            #     big_member_flag = html.xpath(
            #         '//div[@class="dv-bigmember-discount-applied dv-bigmember-discount-two-fare"]/text()')
            #     origin_product_list = html.xpath('//input[@class="square-radio radio-markets"]')
            #     if not origin_product_list:
            #         Logger().warn('airasia no flight')
            #         return search_info
            #     if not big_member_flag:
            #         # 重新登录搜索还没有会员价，报错
            #         raise FlightSearchException('cannot get member price!')
            #     cabin_count_list = html.xpath('//div[@class="avail-table-seats-remaining"]')

            self.origin_product_list = []
            self.cabin_count_list = []
            self.high_req_limit = False
            acw_session = {s['name']: s['value'] for s in self.get_session()}
            Logger().debug("================== first acw =================")
            Logger().debug(acw_session)
            http_session.update_headers({'Referer': 'https://www.airasia.com/cn/zh/home.page',
                                         'Upgrade-Insecure-Requests': '1',
                                         })
            http_session.update_cookie({
                'acw_sc_v3': acw_session['acw_sc_v3'],
                'acw_tc': acw_session['acw_tc']
            })

            result = http_session.request(url=search_url, method='GET', verify=False)

            if 'setCookie("acw_sc_v3", x);document.location.reload();' in result.content:
                acw_session = {s['name']: s['value'] for s in self.get_session(renew=True)}
                Logger().debug("=============== second acw ===============")
                Logger().debug(acw_session)
                http_session.update_cookie({
                    'acw_sc_v3': acw_session['acw_sc_v3'],
                    'acw_tc': acw_session['acw_tc']
                })
            elif result.current_url == 'https://booking.airasia.com/':
                self.high_req_limit = True
            else:
                html = etree.HTML(result.content)
                self.origin_product_list = html.xpath('//input[@class="square-radio radio-markets"]')
                self.cabin_count_list = html.xpath('//div[@class="avail-table-seats-remaining"]')

            if not self.origin_product_list:
                task_list = [gevent.spawn(self._pre_flight_search, acw_session['acw_tc'], acw_session['acw_sc_v3'],
                                          search_url) for i in xrange(10)]
                gevent.joinall(task_list, timeout=3)

                if self.high_req_limit:
                    raise FlightSearchException(err_code='HIGH_REQ_LIMIT')

                if not self.origin_product_list:
                    Logger().warn('airasia no flight')
                    return search_info

            product_list = []
            price_rate = 1

            # 若非国内出发， 价格根据汇率计算成CNY
            if not self.origin_product_list[0].xpath('@data-cur')[0] == 'CNY':
                if not self.origin_product_list[0].xpath('@data-cur')[0] == 'USD':
                    price_type = self.origin_product_list[0].xpath('@data-cur')[0].lower()
                    url = 'https://k.airasia.com/multicurrency/{}'.format(price_type)
                    result = http_session.request(url=url, method='GET', verify=False).to_json()
                    usd = float(result.get('USD'))
                else:
                    usd = 1
                url = 'https://k.airasia.com/multicurrency/cny'
                result = http_session.request(url=url, method='GET', verify=False).to_json()
                price_rate = usd / float(result.get('USD'))

            for origin_product in self.origin_product_list:
                airasia_routing_id = origin_product.xpath('@value')[0]
                airasia_segment_info = json.loads(origin_product.xpath('@data-json')[0])

                if not airasia_segment_info:
                    continue

                print "================== CNY =================="
                print origin_product.xpath('@data-cur')

                product = {
                    'segment_info': airasia_segment_info,
                    'routing_id': airasia_routing_id
                }

                flight_routing = FlightRoutingInfo()
                adult_price = 0.0
                adult_tax = 0.0
                child_price = 0.0
                child_tax = 0.0
                inf_price = 0.0
                inf_tax = 0.0
                base_segment_info_list = []
                tmp_flight_no = ''
                tmp_seg_group = []
                for index, seg in enumerate(airasia_segment_info):
                    if seg['variant'] == 'Adults':
                        adult_price += float(seg['price'])

                        if not seg['dimension16'] == tmp_flight_no:
                            if tmp_seg_group:
                                base_segment_info_list.append(tmp_seg_group)
                            tmp_flight_no = seg['dimension16']
                            tmp_seg_group = [seg]
                        else:
                            tmp_seg_group.append(seg)
                    elif seg['variant'] == 'Kids':
                        child_price += float(seg['price'])

                    if index + 1 == len(airasia_segment_info):
                        base_segment_info_list.append(tmp_seg_group)

                adult_price = float(int(adult_price * price_rate))
                child_price = float(int(child_price * price_rate))

                dep_time = datetime.datetime.strptime(re.findall(r'(.*?)~(.*?)~(.*?)~(.*?)~(.*?)',
                                                                 airasia_routing_id.split('|')[-1].split('^')[0].split(
                                                                     '~~')[-1])[0][1], '%m/%d/%Y %H:%M')
                arr_time = datetime.datetime.strptime(re.findall(r'(.*?)~(.*?)~(.*?)~(.*?)~(.*?)',
                                                                 airasia_routing_id.split('|')[-1].split('^')[-1].split(
                                                                     '~~')[-1])[0][3], '%m/%d/%Y %H:%M')
                rk_info = RoutingKey.serialize(from_airport=base_segment_info_list[0][0]['dimension2'],
                                               dep_time=dep_time,
                                               to_airport=base_segment_info_list[-1][-1]['dimension3'],
                                               arr_time=arr_time,
                                               flight_number='-'.join([n[0]['dimension16'] for n in base_segment_info_list]),
                                               cabin='-'.join([n[0]['dimension4'] for n in base_segment_info_list]),
                                               product='COMMON',
                                               cabin_grade='-'.join(['Y' for n in base_segment_info_list]),
                                               adult_price=adult_price, adult_tax=adult_tax,
                                               provider_channel=self.provider_channel,
                                               child_price=child_price, child_tax=child_tax,
                                               inf_price=inf_price, inf_tax=inf_tax, provider=self.provider,
                                               search_from_airport=search_info.from_airport,
                                               search_to_airport=search_info.to_airport,
                                               from_date=search_info.from_date,
                                               routing_range=search_info.routing_range,
                                               is_multi_segments=1 if len(base_segment_info_list) > 1 else 0
                                               )

                flight_routing.routing_key_detail = rk_info['plain']
                flight_routing.routing_key = rk_info['encrypted']
                product_list.append(product)

                flight_routing.product_type = 'DEFAULT'
                routing_number = 1
                segment_time_list = [re.findall(r'(.*?)~(.*?)~(.*?)~(.*?)~(.*?)', i.split('~~')[-1]
                                                )[0] for i in airasia_routing_id.split('|')[-1].split('^')]
                for index, segment in enumerate(base_segment_info_list):
                    flight_segment = FlightSegmentInfo()
                    flight_segment.carrier = 'D7'

                    select_time_seg = [i for i in segment_time_list if
                                       i[0] == segment[0]['dimension2'] and i[2] == segment[-1]['dimension3']][0]
                    flight_segment.dep_airport = segment[0]['dimension2']
                    flight_segment.dep_time = datetime.datetime.strptime(select_time_seg[1], '%m/%d/%Y %H:%M').strftime('%Y-%m-%d %H:%M:%S')

                    flight_segment.arr_airport = segment[-1]['dimension3']
                    flight_segment.arr_time = datetime.datetime.strptime(select_time_seg[3], '%m/%d/%Y %H:%M').strftime('%Y-%m-%d %H:%M:%S')

                    # 经停
                    if len(segment) > 1:
                        flight_segment.stop_airports = '/'.join([s['dimension2'] for s in segment[1: ]])

                    flight_segment.flight_number = segment[0]['dimension16']
                    flight_segment.dep_terminal = ''
                    flight_segment.arr_terminal = ''
                    flight_segment.cabin = segment[0]['dimension4']
                    flight_segment.cabin_grade = 'Y'

                    flight_segment.cabin_count = 5
                    for c in self.cabin_count_list:
                        cabin_routing_id = c.getparent().getprevious().xpath('div/input[@class="square-radio radio-markets"]/@value')[0]
                        if cabin_routing_id == airasia_routing_id:
                            flight_segment.cabin_count = int(re.findall(r'\d+', c.xpath('text()')[0])[0])
                            break

                    segment_duration = (datetime.datetime.strptime(flight_segment.arr_time, '%Y-%m-%d %H:%M:%S') -
                                        datetime.datetime.strptime(flight_segment.dep_time, '%Y-%m-%d %H:%M:%S')).seconds
                    duration = int(segment_duration / 60)
                    flight_segment.duration = duration
                    flight_segment.routing_number = routing_number
                    routing_number += 1
                    flight_routing.from_segments.append(flight_segment)
                flight_routing.adult_price = adult_price
                flight_routing.adult_tax = adult_tax
                flight_routing.child_price = child_price
                flight_routing.child_tax = child_tax
                search_info.assoc_search_routings.append(flight_routing)
            search_info.product_list = product_list
            return search_info
        except Exception as e:
            import traceback
            Logger().error(traceback.format_exc())
            raise FlightSearchException(e)

    def _booking(self, http_session, order_info):
        """

        pax_name = '刘志'
        pax_email = 'fdaljrj@tongdun.org'
        pax_mobile = '15216666047'
        pax_pid = '230903199004090819'
        pax_id_type = 'NI'
        contact_name = pax_name
        contact_email = pax_email
        contact_mobile = pax_mobile

        :param http_session:
        :param order_info:
        :return: order_info class
        """

        order_info.provider_order_status = 'REGISTER_FAIL'
        if not order_info.ffp_account:
            # 如果没有账号才需要注册
            try:
                ffp_account_info = self.register(http_session=http_session, pax_info=order_info.passengers[0],
                                                 sub_order_id=order_info.sub_order_id,
                                                 flight_order_id=order_info.flight_order_id)
            except Critical as e:
                raise
            order_info.ffp_account = ffp_account_info  # 需要将账号信息反馈到order_info

        order_info.provider_order_status = 'LOGIN_FAIL'
        http_session = self.login(http_session, order_info.ffp_account)
        customer_id = order_info.ffp_account.reverse1
        gevent.sleep(1)
        order_info.provider_order_status = 'SEARCH_FAIL'
        search_info = self.flight_search(http_session, order_info)

        order_info.provider_order_status = 'BOOK_FAIL'
        # 确认航班
        gevent.sleep(1)
        Logger().info('confirm flight ')

        routing_info = None
        product_details = None
        for index, flight_routing in enumerate(order_info.assoc_search_routings):
            if flight_routing.routing_key == order_info.routing.routing_key:
                routing_info = flight_routing
                product_details = search_info.product_list[index]
                break
        if not routing_info or not product_details:
            order_info.provider_order_status = 'BOOK_FAIL_NO_CABIN'
            raise BookingException('routingkey not found')

        adult_num = 0
        children_num = 0
        inf_num = 0
        order_info.passengers = sorted(order_info.passengers,
                                       key=lambda x: datetime.datetime.strptime(x.birthdate, '%Y-%m-%d'))
        for passenger in order_info.passengers:
            age_type = passenger.current_age_type(order_info.from_date)
            if age_type == 'ADT':
                adult_num += 1
            elif age_type == 'CHD':
                children_num += 1
            elif age_type == 'INF':
                inf_num += 1

        post_data = {
            'airAsiaAvailability.Archery': '',
            'airAsiaAvailability.MarketFareKeys[0]': product_details['routing_id'],
            'airAsiaAvailability.MarketValueBundles[0]': 'false',
            'airAsiaAvailability.RequestSpecialService': 'False',
            'airAsiaAvailability.IsExpressCheckout': 'false',
        }
        http_session.update_headers({
            'Content-Type': 'application/x-www-form-urlencoded'
        })
        url = 'https://booking.airasia.com/Flight/Select'
        result = http_session.request(url=url, method='POST', data=post_data, verify=False)
        print "=============== choose flight ==============="
        print http_session.get_cookies()

        gevent.sleep(1)
        passenger_list = []
        inf_list = []
        person_list = []
        for p in order_info.passengers:
            if p.current_age_type(order_info.from_date) == 'INF':
                inf_list.append(p)
            else:
                person_list.append(p)
        for index, p in enumerate(person_list):
            p_info = {
                'airAsiaPassengers[{}].Name.Title'.format(index): 'MR' if p.current_age_type(order_info.from_date) == 'ADT' else 'CHD',
                'airAsiaPassengers[{}].Name.First'.format(index): p.first_name,
                'airAsiaPassengers[{}].Name.Last'.format(index): p.last_name,
                'airAsiaPassengers[{}].date_of_birth_day_{}'.format(index, index): str(datetime.datetime.strptime(p.birthdate, '%Y-%m-%d').day),
                'airAsiaPassengers[{}].date_of_birth_month_{}'.format(index, index): str(datetime.datetime.strptime(p.birthdate, '%Y-%m-%d').month),
                'airAsiaPassengers[{}].date_of_birth_year_{}'.format(index, index): str(datetime.datetime.strptime(p.birthdate, '%Y-%m-%d').year),
                'airAsiaPassengers[{}].TypeInfo.DateOfBirth'.format(index): datetime.datetime.strptime(p.birthdate, '%Y-%m-%d').strftime('%d/%m/%Y'),
                'airAsiaPassengers[{}].CustomerNumber'.format(index): customer_id if index == 0 else '',
            }
            if p_info['airAsiaPassengers[{}].Name.Title'.format(index)] == 'CHD':
                p_info['airAsiaPassengers[{}].Info.Gender'.format(index)] = '1' if p.gender == 'M' else '2'
            passenger_list.append(p_info)

        for index, p in enumerate(inf_list):
            passenger_list.append({
                'airAsiaPassengers.Infants[{}].Gender'.format(index): '1' if p.gender == 'M' else '2',
                'airAsiaPassengers.Infants[{}].Name.First'.format(index): p.first_name,
                'airAsiaPassengers.Infants[{}].Name.Last'.format(index): p.last_name,
                'airAsiaPassengers.Infants[{}].infant_date_of_birth_day_{}'.format(index, index): str(datetime.datetime.strptime(p.birthdate, '%Y-%m-%d').day),
                'airAsiaPassengers.Infants[{}].infant_date_of_birth_month_{}'.format(index, index): str(datetime.datetime.strptime(p.birthdate, '%Y-%m-%d').month),
                'airAsiaPassengers.Infants[{}].infant_date_of_birth_year_{}'.format(index, index): str(datetime.datetime.strptime(p.birthdate, '%Y-%m-%d').year),
                'airAsiaPassengers.Infants[{}].DateOfBirth'.format(index): datetime.datetime.strptime(p.birthdate, '%Y-%m-%d').strftime('%d/%m/%Y'),
                'airAsiaPassengers.Infants[{}].AttachedPassengerNumber'.format(index): '0',
            })

        post_data = {'airAsiaPassengers.Archery': ''}
        for p in passenger_list:
            post_data.update(p)

        # TODO 1.请求一遍update拿到破解所需数据，2.调用ali破解，获取token，session，sig，3。利用这三个参数再次请求update

        url = 'https://booking.airasia.com/Passengers/Update'
        result = http_session.request(url=url, method='POST', data=post_data, verify=False)
        print "===================== update passenger ==========="
        print http_session.get_cookies()
        print result.content
        ali_token = re.findall(r"token: '(.*?)',", result.content)

        url = 'https://booking.airasia.com/Passengers/Update?=&u_atoken=c5b7a0f7-3455-493b-9406-35e5279daeb6&u_asession=01u4nzp1JU24p0NHuB_dtHfO3ty0-q4-K595WF7NJmK0tr61Z-l5JooW5KevF8_mCm9RCSd6eSglWb_g5q_1wPkWnF7aS6DnRWHt6Tc8a9HEFaWCxJ7q6xTIHCg_VyxASDbI-UElQSpy2JpOihZpevsg&u_asig=05Il5fzBncc_3GGVCLVu67YzUb567RuMNFcY6frYa_BdmaXJn-FzUkZnWc5_kMEMly1qIPt0Vy-9EAe0kRlDq6HOTdLzxvtJCts1opBsmJYjchZ1TwV6AL5C8JuObUyFVkQpS-o5obU0XiA1R6V5QngCf5tOvMaWj3nUo8zm1BUlpr40k3H3Y-_gV6IRIBSAkySCtVtLBMkmFNAELhn2RMKf-rUtJztx5bSuVpxFHVvTsgHc1-Ua7VEYIJpHLE-SP7B0F2IcKGKNZ11V-7-HrMYy5fjc3RJZItvNduSUwwGXYEO0qppF4LJBfirkWYqJORs8l4F-vncluD8I2_Syo_S4pCQGYae9u23qNSAic9wgY&u_aref=jZXNzz%2FPAEVrNWbxtRG%2FeHagTtM%3D'
        http_session.request(url=url, method='POST', data=post_data, verify=False)
        print "===================== update passenger ==========="
        print http_session.get_cookies()

        url = 'https://booking.airasia.com/Extras/Add'
        http_session.request(url=url, method='GET', verify=False)
        print("================== extra add session ====== get jace session id")
        print(http_session.get_cookies())

        url = 'https://booking.airasia.com/Ssrs/AddInsurance'
        post_data = {
            'airAsiaZeusInsure.ApplyPassengerInsuranceFee[0]': '0|INSD|CNY',
            'airAsiaZeusInsure.TermsAndConditions': 'false',
        }

        result = http_session.request(url=url, method='POST', data=post_data, verify=False)
        print "====================== add insurance ============="
        print result.content

        http_session.update_headers({
            'Content-Type': 'application/json',
            'x-jace-session-id': http_session.get_cookies().get('dotRezSignature'),
        })
        url = 'https://jace.airasia.com/BookingService/GetBooking'
        post_data = {
            "RecordLocator": "",
            "GetBookingFilter": 32767
        }
        result = http_session.request(url=url, method='POST', json=post_data, verify=False)
        print "=================== GetBooking ==============="
        print result.content

        booking_info = json.loads(result.content)

        url = 'https://jace.airasia.com/BookingService/GetBookingSummary'
        post_data = {
            "CustomerId": customer_id,
            "Currency": "CNY"
        }
        result = http_session.request(url=url, method='POST', json=post_data, verify=False)
        print "=================== GetBookingSummary ==============="
        print result.content

        gevent.sleep(1)
        url = 'https://jace.airasia.com/PaymentService/ValidatePayments'
        post_data = {}
        result = http_session.request(url=url, method='POST', json=post_data, verify=False)
        print "=================== ValidatePayments =============="
        print result.content

        gevent.sleep(3)
        url = 'https://jace.airasia.com/PaymentService/SupportedSaveCards'
        post_data = {
            "CustomerId": customer_id,
            "Culture": "en-gb",
            "RoleCode": "WWWM",
            "CollectedCurrencyCode": "CNY",
            "TabCode": "BP"
        }
        result = http_session.request(url=url, method='POST', json=post_data, verify=False)
        print "==================== SupportedSaveCards ================"
        print result.content

        url = 'https://jace.airasia.com/PaymentService/GetCreditShell'
        post_data = {
            "CustomerId": customer_id,
            "Currency": "CNY"
        }
        result = http_session.request(url=url, method='POST', json=post_data, verify=False)
        print "============== GetCreditShell ==============="
        print result.content

        gevent.sleep(4)
        url = 'https://jace.airasia.com/BookingService/Booking/Detect'
        post_data = {
            "BookingInfo": booking_info['BookingResponse']['BookingInfo'],
            "BookingSum": booking_info['BookingResponse']['BookingSum'],
            "CurrencyCode": booking_info['BookingResponse']['CurrencyCode'],
            "Journeys": booking_info['BookingResponse']['Journeys'],
            "Passengers": booking_info['BookingResponse']['Passengers'],
        }
        result = http_session.request(url=url, method='POST', json=post_data, verify=False)
        print "=-====================== booking detect ==============="
        print result.content

        gevent.sleep(4)
        http_session.update_headers({
            'authorization': 'User {}'.format(
                hashlib.sha256('AddPaymentToBookingDirectDebit' + http_session.get_headers().get(
                    'x-jace-session-id') + 'Mario630131222@qq.comP861776789475611').hexdigest().upper()),
        })

        url = 'https://jace.airasia.com/PaymentService/AddPaymentToBookingDirectDebit'
        post_data = {
            "CarrierCode": "D7",
            "FromStation": order_info.from_airport,
            "FromCountry": AIRASIA_IATA_CODE[order_info.from_airport],
            "ToStation": order_info.to_airport,
            "ToCountry": AIRASIA_IATA_CODE[order_info.to_airport],
            "BookingContacts": [{
                "Name": {
                    "FirstName": order_info.passengers[0].first_name,
                    "LastName": order_info.passengers[0].last_name,
                },
                "EmailAddress": order_info.ffp_account.username,
                "TypeCode": "P",
                "OtherPhone": "86{}".format(TBG.global_config['OPERATION_CONTACT_MOBILE']),
                "NotificationPreference": "1",
                "CultureCode": "zh-CN",
                "CountryCode": "CN",
                "CustomerNumber": customer_id
            }],
            "EmergencyContact": {},
            "BookingComments": [{
                "CommentText": "SessionID: {}".format(http_session.get_cookies().get('ASP.NET_SessionId')),
                "CommentType": "Default",
                "CreatedDate": "{}+08:00".format(datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))
            }, {
                "CommentText": "GAuserID: ",
                "CommentType": "Default",
                "CreatedDate": "{}+08:00".format(datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))
            }],
            "QuotedCurrency": "CNY",
            "CollectedCurrency": "CNY",
            "ExternalRateBatchId": "",
            "RateQuotedId": "",
            "RoleCode": "WWWM",
            "CultureCode": "zh-CN",
            "ReturnUrl": "https://booking3.airasia.com/",
            "DirectDebit": {
                "PaymentID": "42",
                "TabCode": "DA",
                "PayMethodCode": "C2"
            },
            "PaymentID": "42",
            "TabCode": "DA"
        }

        result = http_session.request(url=url, method='POST', json=post_data,
                              verify=False)
        print("=============== add payment to  booking ================")
        print(result.content)
        print http_session.get_headers()
        print http_session.get_cookies()

    def _check_order_status(self, http_session, ffp_account_info, order_info):
        """
        检查订单状态
        :param http_session:
        :param order_id:
        :return: 返回订单状态
        """

        http_session = self.login(ffp_account_info=ffp_account_info)

        post_data = {"param": json.dumps({"orderNo": order_info.provider_order_id, "orderType": order_info.routing_range})}
        url = 'https://www.okair.net/orderajax!b2cOrderInfo.action'

        result = http_session.request(url=url, method='POST', data=post_data,
                                      provider_channel=self.provider_channel, verify=False).to_json()
        if result.get('errorCode') == '00' and result.get('orderInfo') and result['orderInfo']['orderNo'] == order_info.provider_order_id:

            if result['orderInfo']['orderStatus'] == '已取消':
                order_info.provider_order_status = 'ISSUE_CANCEL'
                return

            psg_list = result['orderInfo']['fltList'][0]['psgList']
            for pax_info in order_info.passengers:
                for psg in psg_list:
                    if pax_info.selected_card_no == psg['docNo'] and psg.get('tktNo'):
                        pax_info.ticket_no = psg['tktNo']
                        order_info.provider_order_status = 'ISSUE_SUCCESS'
                        Logger().info('psg ticket_no %s' % pax_info.ticket_no)
                        break
        else:
            Logger().error("cannot get order info")
            raise CheckOrderStatusException("have no order")

    def _get_coupon(self, http_session, ffp_account_info):
        """
        获取VISA红包
        :return:
        """

        pass

    def _pay(self, order_info, http_session, pay_dict):
        """
        支付
        :param http_session:
        :return:
        """

        pass



    def _get_session(self):
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--no-sandbox')
            capa = DesiredCapabilities.CHROME
            capa["pageLoadStrategy"] = "none"
            driver = webdriver.Chrome(desired_capabilities=capa, chrome_options=chrome_options)
            wait = WebDriverWait(driver, 5)
            driver.get('https://booking.airasia.com/')
            # driver.get('https://booking.airasia.com/Flight/Select?o1=PVG&d1=SIN&dd1=2019-01-22&ADT=1&CHD=0&inl=0&s=false&mon=true&cc=CNY')
            time.sleep(5)
            driver.execute_script("window.stop();")
            cookies = driver.get_cookies()

            acw_sc_v3 = None
            acw_tc = None
            for cookie in cookies:
                if cookie['name'] == 'acw_sc_v3':
                    acw_sc_v3 = cookie['value']
                if cookie['name'] == 'acw_tc':
                    acw_tc = cookie['value']

            driver.close()
            sd = [{'session_type': 'header', 'name': 'acw_sc_v3', 'value': acw_sc_v3}, {'session_type': 'header', 'name': 'acw_tc', 'value': acw_tc}]
            return sd
        except Exception as e:
            try:
                driver.close()  # 强制关闭driver进程，无论任何报错
            except Exception as e:
                pass
            raise
