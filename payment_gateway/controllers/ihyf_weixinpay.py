# -*- coding: utf-8 -*-
import logging
from odoo.addons.ihyf_payment_gateway.controllers.pay_base_controller \
    import PayBaseController
from odoo.http import request
from odoo.addons.ihyf_payment_gateway.common.backend_common \
    import get_payment_user_info, get_payment_order, create_payment_order, \
    xml_to_array, update_payment_order, get_notify_url, get_payment_id, \
    get_payment_order_by_id, get_conf_info
from odoo import http

from odoo.addons.ihyf_payment_gateway.helper.wxpay import QRWXpay

_logger = logging.getLogger(__name__)


class HollyWantWxPay(PayBaseController):
    def pay_qrcode_weixinpay(self, *args, **kwargs):
        ihyf_payment_id = kwargs.get('ihyf_payment_id')
        payment_user_info = get_payment_user_info(
            request.cr, ihyf_payment_id)

        payment_order = kwargs.get('payment_order')
        order_id = payment_order['order_id']
        body = payment_order.get('body', u'')
        source = kwargs.get('source', 'default')

        if get_payment_order(request.cr, order_id, 'weixinpay', source):
            return {
                'title': 'failure',
                'error': 'Payment Order is alreay exist'
            }

        payment_id = get_payment_id(order_id, 'weixinpay', source)

        create_payment_order(
            request.cr, payment_order,
            payment_user_info['ihyf_payment_id'],
            payment_user_info['ihyf_secret_key'], 'weixinpay',
            source, payment_id
        )  # 在网关创建未支付订单

        product = dict()
        # 附加数据，在查询API和支付通知中原样返回，该字段主要用于商户携带订单的自定义数据,这里暂定售货机ID
        product['attach'] = 1
        product['body'] = body or source
        product['payment_id'] = payment_id
        product['product_id'] = 1
        product['total_fee'] = int(payment_order['total_amount'] * 100)

        app_id = payment_user_info['weixinpay_app_id']  # app_id
        mch_id = payment_user_info['weixinpay_seller_id']  # 卖家id
        key = payment_user_info['weixinpay_private_key']  # 私钥
        ip = get_conf_info('gateway_ip')

        if not ip:
            return {
                "title": "Weixin Pay",
                "error": "Gateway Ip is not configured"
            }
        # 回调url(现为hyf外网地址)
        notify_url = get_notify_url(request.cr)
        if not notify_url:
            _logger.warn("notify_url 不存在")
        else:
            notify_url += '/weixin_callback'
        try:
            weixin_pay = QRWXpay(
                app_id,
                mch_id,
                key,
                ip,
                notify_url=notify_url)
            weixin_result = weixin_pay.unifiedorder(product)
            result = {
                "result": "SUCCESS",
                # "returnMsg": "OK",
                # "appid": app_id,
                # "mchId": mch_id,
                # "deviceInfo": "WEB",
                # "nonceStr": weixin_result['nonce_str'],
                # "sign": weixin_result['sign'],
                # "resultCode": "SUCCESS",
                # "tradeType": "NATIVE",
                # "prepayId": weixin_result['prepay_id'],
                "code_url": weixin_result['code_url']}
            return result
        except Exception as e:
            return {
                "title": "微信订单创建",
                "error": e.message
            }

    @http.route(
        ['/ihyf/pay/weixin_callback'],
        type='http',
        auth="none",
        csrf=False)
    def weixin_callback(self, *args, **kwargs):
        """
        微信回调接口处理
        """
        _logger.info("\n\n\n")
        _logger.info("Payment Gateway: receive the weixin callback")

        xml_data = request.httprequest.data
        xml_dict = xml_to_array(xml_data)
        _logger.info(xml_dict)

        payment_id = xml_dict['out_trade_no']  # 获取返回订单号
        payment_order = get_payment_order_by_id(request.cr, payment_id)
        _logger.info(payment_order)
        if payment_order:
            ihyf_payment_id = payment_order['ihyf_payment_id']

            payment_user_info = get_payment_user_info(
                request.cr, ihyf_payment_id)  # 获取该user信息
            app_id = payment_user_info['weixinpay_app_id']  # 获得app_id
            seller_id = payment_user_info['weixinpay_seller_id']  # 卖家id 和 mch_id 是一样的东西
            private_key = payment_user_info['weixinpay_private_key']  # 获取该订单私钥
            ip = get_conf_info('gateway_ip')

            if not ip:
                return {
                    "title": "Weixin Pay",
                    "error": "Gateway Ip is not configured"
                }
            # 回调url(现为hyf外网地址)
            notify_url = get_notify_url(request.cr)
            if not notify_url:
                _logger.warn("notify_url 不存在")
            else:
                notify_url += '/weixin_callback'
            weixin_pay = QRWXpay(
                app_id, seller_id, private_key, ip, notify_url)

            result = weixin_pay.verify_callback(xml_data)
            _logger.info(result)
            if result and len(result) >= 1:
                if result[0] and result[1]['result_code'] == 'SUCCESS' and payment_order[
                        'total_amount'] * 100 == float(result[1]['total_fee']):  # 如果返回true，签名验证成功,支付金额需要和订单金额一致
                    payment_type = 'weixinpay'
                    # 验证成功，更新payment_order信息
                    update_payment_order(request.cr, 'paid', payment_id, payment_type, 'done')
                    _logger.info("update the payment order")
                    return "<xml><return_code><![CDATA[SUCCESS]]></return_code><return_msg><![CDATA[OK]]></return_msg></xml>"
                else:  # 验证失败
                    return "<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[FAIL]]></return_msg></xml>"
            else:  # 验证失败
                return "<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[FAIL]]></return_msg></xml>"

    def query_order_weixinpay(self, *args, **kwargs):
        """
        查询订单支付结果接口
        kwargs: kwargs['outTradeNo']订单ID
        return: {}
        """
        info = dict()
        info['title'] = '支付信息查询'
        order_id = kwargs.get('order_id')
        if not order_id:
            info['error'] = '订单号有误'
            return info

        source = kwargs.get('source', 'default')
        payment_order = get_payment_order(
            request.cr, order_id, 'weixinpay', source)
        if not payment_order:
            info['error'] = '未找到该订单'
            return info

        if payment_order and payment_order['payment_status'] == 'paid':
            info['msg'] = 'SUCCESS'
        # elif payment_order and payment_order['payment_status'] == 'not_pay':
        #     info['msg'] = 'NOT_PAY'
        else:
            ihyf_payment_id = payment_order['ihyf_payment_id']
            # 查询微信服务器
            payment_user_info = get_payment_user_info(
                request.cr, ihyf_payment_id)

            app_id = payment_user_info['weixinpay_app_id']  # 获得app_id
            seller_id = payment_user_info['weixinpay_seller_id']  # 卖家id 和 mch_id 是一样的东西
            private_key = payment_user_info['weixinpay_private_key']  # 获取该订单私钥
            ip = get_conf_info('gateway_ip')

            if not ip:
                return {
                    "title": "Weixin Pay",
                    "error": "Gateway Ip is not configured"
                }
            # 回调url(现为hyf外网地址)
            notify_url = get_notify_url(request.cr)
            if not notify_url:
                _logger.warn("notify_url 不存在")
            else:
                notify_url += '/weixin_callback'
            weixin_pay = QRWXpay(
                app_id, seller_id, private_key, ip, notify_url)

            weixin_return_result = weixin_pay.verify_order(
                out_trade_no=payment_order['payment_id'])
            logging.info("query weixinpay")
            logging.info(weixin_return_result)
            if weixin_return_result.get('trade_state') == 'SUCCESS':
                update_payment_order(
                    request.cr, 'paid', payment_order['payment_id'], 'done')
                info['msg'] = 'SUCCESS'
            else:
                info['msg'] = 'NOT_PAY'
        return info
