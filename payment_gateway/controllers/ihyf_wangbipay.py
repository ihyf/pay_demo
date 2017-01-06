# -*- coding: utf-8 -*-
import json
import requests
from openerp.http import request
from odoo.addons.ihyf_payment_gateway.controllers.pay_base_controller \
    import PayBaseController
from odoo.addons.ihyf_payment_gateway.common.backend_common \
    import get_payment_user_info, get_payment_order, create_payment_order, \
    update_wangbipay_code, update_payment_order, get_payment_id

import logging
_logger = logging.getLogger(__name__)


class HollyWantWangbiPay(PayBaseController):

    def pay_qrcode_wangbipay(self, *args, **kwargs):
        # *币支付请求链接
        ihyf_payment_id = kwargs.get('ihyf_payment_id')

        payment_user_info = get_payment_user_info(
            request.cr, ihyf_payment_id)

        payment_order = kwargs.get('payment_order')
        order_id = payment_order['order_id']
        source = kwargs.get('source', 'default')

        if get_payment_order(request.cr, order_id, 'wangbipay', source):
            return {
                'title': 'failure',
                'error': 'Payment Order is alreay exist'
            }

        payment_id = get_payment_id(order_id, 'wangbipay', source)

        create_payment_order(
            request.cr, payment_order,
            payment_user_info['ihyf_payment_id'],
            payment_user_info['ihyf_secret_key'], 'wangbipay',
            source, payment_id
        )  # 在网关创建未支付订单

        info = dict()
        info['title'] = '*币支付url'
        data = dict()
        data['amount'] = payment_order['total_amount']  # 金额
        data['receiverKey'] = '1'
        data['receiver'] = '10000000000'
        data['orderCode'] = payment_order['order_id']  # 订单号
        data['channel'] = 'WEB'
        hotkid_respose = self.hotkid_order(data)  # 俱乐部返回给我们的信息

        if hotkid_respose.get('error', False):
            return {
                'title': 'failure',
                'error': hotkid_respose.get('error')
            }

        if hotkid_respose:
            url = """https://open.weixin.qq.com/connect/oauth2/authorize?appid=wx160b97fc7a08acc3&redirect_uri=http://www.hotkidclub.com/vmc/payment.html?pcode=%s&response_type=code&scope=snsapi_base#wechat_redirect""" % \
                  (hotkid_respose['object']['code'])
            update_wangbipay_code(
                request.cr, hotkid_respose['object']['code'], order_id)
            # 把*币code 更新至订单中
            info['code_url'] = str(url)
            info['result'] = 'SUCCESS'
        else:
            info['error'] = '获取失败'
        return info

    def query_order_wangbipay(self, *args, **kwargs):

        info = dict()
        info['title'] = '支付信息查询'
        order_id = kwargs.get('order_id')  # 获取订单号
        if not order_id:
            info['error'] = '订单号有误'
            return info

        source = kwargs.get('source', 'default')
        payment_order = get_payment_order(
            request.cr, order_id, 'wangbipay', source)  # 获取订单信息

        if payment_order:
            data = dict()
            data['code'] = payment_order['wangbipay_code']  # 获得*币code
            wangbi_pay_result = self.hotkid_query(data)
            if not wangbi_pay_result.get('object'):
                info['error'] = '交易不存在'
                return info
            if wangbi_pay_result['object']['status'] == 'SUCCESS':
                payment_type = 'wangbipay'
                update_payment_order(
                    request.cr, 'paid', payment_order['payment_id'],
                    payment_type, 'done')  # 更新网关订单信息
                info['msg'] = 'SUCCESS'
            elif wangbi_pay_result['object']['status'] == 'REQUEST':
                info['msg'] = 'WAIT_PAY'
            else:
                info['error'] = '*币支付有误'
            return info
        else:
            info['error'] = '未找到该订单'
            return info

    def hotkid_order(self, order_data):
        # post data to hotkidclub,get pay_code
        url = 'http://www.hotkidclub.com/wb/requestPayment.ctrl'
        order_data = json.dumps(order_data)
        headers = {'content-type': 'application/json'}
        response_pay_code = requests.post(
            url, order_data, headers=headers).json()
        return response_pay_code

    def hotkid_query(self, query_data):
        # query pay_result
        url = 'http://www.hotkidclub.com/wb/selectPayment.ctrl'
        query_data = json.dumps(query_data)
        headers = {'content-type': 'application/json'}
        query_pay_status = requests.post(
            url, query_data, headers=headers).json()
        return query_pay_status
