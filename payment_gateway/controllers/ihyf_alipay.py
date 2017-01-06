# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
from odoo.addons.ihyf_payment_gateway.controllers.pay_base_controller \
    import PayBaseController
from odoo.addons.ihyf_payment_gateway.helper.alipay \
    import alipay_generate_prepay_native, alipay_rsa_verify, \
    alipay_trade_query_call, alipay_trade_refund
from odoo.addons.ihyf_payment_gateway.common.backend_common \
    import get_payment_user_info, get_payment_order, get_payment_order_by_id, \
    create_payment_order, update_payment_order, get_notify_url, get_payment_id
from odoo.addons.ihyf_payment_gateway.common.check_common \
    import check_kwargs_pay_refund
from odoo import http
from openerp.http import request
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

_logger = logging.getLogger(__name__)


class HollyWantAliPay(PayBaseController):

    # ##—————————————支付宝预下单————————————————## #
    def pay_qrcode_alipay(self, *args, **kwargs):
        """
        args:
        kwargs: 传入的订单号，总金额，终端id,产品名称
        return: 二维码url
        """
        ihyf_payment_id = kwargs.get('ihyf_payment_id', False)

        payment_user_info = get_payment_user_info(
            request.cr, ihyf_payment_id)

        payment_order = kwargs.get('payment_order')
        order_id = payment_order['order_id']
        body = payment_order.get('body', u'')
        source = kwargs.get('source', 'default')

        if get_payment_order(request.cr, order_id, 'alipay', source):
            return {
                'title': 'failure',
                'error': 'Payment Order is alreay exist'
            }

        payment_id = get_payment_id(order_id, 'alipay', source)

        create_payment_order(
            request.cr, payment_order,
            payment_user_info['ihyf_payment_id'],
            payment_user_info['ihyf_secret_key'],
            'alipay', source, payment_id
        )  # 在网关创建未支付订单
        # 组装访问上行
        data = {}
        cash = payment_order['total_amount']  # 总金额
        description = body or source
        method = "alipay.trade.precreate"  # 支付宝统一收单交易预创建接口
        # 回调url(现为hyf外网地址)
        notify_url = get_notify_url(request.cr)
        if not notify_url:
            _logger.warn("notify_url 不存在")
        else:
            notify_url += '/alipay_callback'
        alipay_seller_id = payment_user_info['alipay_seller_id']  # 卖家id
        alipay_app_id = payment_user_info['alipay_app_id']  # app_id
        alipay_private_rsa = payment_user_info['alipay_private_rsa']  # 私钥
        alipay_public_key = payment_user_info['alipay_public_key']  # 公钥

        data['payment_id'] = payment_id
        data['cash'] = cash
        data['description'] = description
        data['method'] = method
        data['notify_url'] = notify_url
        data['seller_id'] = alipay_seller_id
        data['app_id'] = alipay_app_id
        data['private_key'] = alipay_private_rsa
        if not order_id and cash:
            return {
                "title": "支付宝订单创建",
                "error": "订单id、金额不能为空"
            }

        return alipay_generate_prepay_native(data)

    # ##————————————支付宝异步通知验证————————————## #
    @http.route(
        '/ihyf/pay/alipay_callback',
        type='http',
        auth="none",
        csrf=False)
    def alipay_verify_sign(self, *args, **kwargs):
        """
        url:
        return: 返回支付宝success
        """
        logging.info("alipay_callback")
        logging.info(kwargs)
        if not kwargs:
            return 'null'
        params = {}
        for key, value in kwargs.items():
            # 目前参数中只有sign值内有'='，测试时注意其他键的值是否存在等号
            if key not in ['sign', 'sign_type']:
                params[key] = value
        # 通过http.route过滤了加号，变成空格，实测时注意

        sign = kwargs.get('sign')
        payment_id = kwargs.get('out_trade_no')  # 获取订单号
        trade_status = kwargs.get('trade_status')  # 支付结果
        payment_order = get_payment_order_by_id(request.cr, payment_id)
        ihyf_payment_id = payment_order['ihyf_payment_id']
        payment_user_info = get_payment_user_info(
            request.cr, ihyf_payment_id)
        private_key = payment_user_info['alipay_private_rsa']  # 获取该订单私钥
        public_key = payment_user_info['alipay_public_key']  # 获取该订单公钥
        try:
            res = alipay_rsa_verify(params, sign, private_key, public_key)
            if trade_status == 'WAIT_BUYER_PAY':
                trade_status = 'wait_pay'
                order_status = 'draft'
            elif trade_status == 'TRADE_SUCCESS':
                trade_status = 'paid'
                order_status = 'done'
            else:
                trade_status = 'not_pay'

            payment_type = 'alipay'

            update_payment_order(
                request.cr, trade_status, payment_id,
                payment_type, order_status)  # 更新订单信息
            logging.info(res)
            if res:
                res = 'success'
                logging.info(res)
            else:
                res = 'failure'
        except Exception as e:
            logging.info("\n\nAlipay verify sign error:")
            logging.info(e)
            logging.info("\n\n")
            res = 'server error'
        return res

    # ##————————————支付宝查询————————————## #
    def query_order_alipay(self, *args, **kwargs):
        """
        **kwargs: 安卓传入的订单的状态
        return: 返回订单状态
        """
        info = dict()
        info['title'] = '支付信息查询'
        transact_num = kwargs.get('order_id')  # 获取订单号

        if transact_num:
            source = kwargs.get('source', 'default')
            payment_order = get_payment_order(
                request.cr, transact_num, 'alipay', source)
            if payment_order:
                if payment_order['payment_status'] == 'paid':
                    info['msg'] = 'SUCCESS'
                    return info
                else:
                    payment_id = payment_order['payment_id']
                    ihyf_payment_id = \
                        payment_order['ihyf_payment_id']
                    payment_user_info = get_payment_user_info(
                        request.cr, ihyf_payment_id)

                    method = "alipay.trade.query"  # 支付宝统一收单交易查询接口
                    # 回调url(现为hyf外网地址)
                    notify_url = get_notify_url(request.cr)
                    if not notify_url:
                        _logger.warn("notify_url 不存在")
                    else:
                        notify_url = notify_url + '/alipay_callback'
                    private_key = payment_user_info[
                        'alipay_private_rsa']  # 获取该订单私钥
                    app_id = payment_user_info['alipay_app_id']  # app_id
                    info = alipay_trade_query_call(
                        method, notify_url, private_key, app_id, payment_id)
                    info['title'] = '支付信息查询'
                    return info
            else:
                info['error'] = '未找到该订单'
                return info
        else:
            info['error'] = '订单号有误'

    # ##—————————————支付宝退款————————————————## #
    def pay_refund_alipay(self, *args, **kwargs):
        refund_info = kwargs.get("refund_info", False)
        order_id = refund_info.get("order_id", False)
        refund_amount = refund_info.get("refund_amount", False)
        source = kwargs.get('source', 'default')

        if order_id and refund_amount:
            payment_order = get_payment_order(
                request.cr, order_id, 'alipay', source)
            if not payment_order:
                return {
                    'title': 'failure',
                    'error': 'Payment Order is not exist'
                }
            payment_status = payment_order['payment_status']  # 支付状态
            total_amount = payment_order['total_amount']  # 订单金额
            if payment_status != "paid":
                return {
                    'title': 'failure',
                    'error': 'Payment Order is not paid'
                }
            if refund_amount > total_amount:
                return {
                    'title': 'failure',
                    'error': 'Refund Amount > Order Total Amount'
                }

            payment_id = payment_order['payment_id']
            ihyf_payment_id = kwargs['ihyf_payment_id']
            payment_user_info = get_payment_user_info(
                request.cr, ihyf_payment_id)  # 获取用户配置信息
            app_id = payment_user_info['alipay_app_id']  # 获取支付宝appid
            private_key = payment_user_info['alipay_private_rsa']  # 获取支付宝私钥
            res = alipay_trade_refund(transact_num=payment_id,
                                      refund_amount=refund_amount,
                                      refund_reason=None,
                                      operator_id=None,
                                      store_id=None,
                                      terminal_id=None,
                                      app_id=app_id,
                                      private_key=private_key)
            return res

