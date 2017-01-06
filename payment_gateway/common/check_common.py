# -*- coding: utf-8 -*-
from odoo.addons.ihyf_payment_gateway.common.backend_common \
    import get_payment_user_info


def check_kwargs_pay_qrcode(cr, kwargs):
    res = check_identity(cr, kwargs)

    if res['title'] != 'success':
        return res

    payment_type = kwargs.get('payment_type', False)
    if not payment_type:
        return {
            'title': 'failure',
            'error': 'Invalid Payment Type'
        }

    if payment_type not in ('alipay', 'weixinpay', 'wangbipay'):
        return {
            'title': 'failure',
            'error': 'Not support this payment'
        }

    payment_order = kwargs.get('payment_order', False)
    if not payment_order:
        return {
            'title': 'failure',
            'error': 'Invalid Payment Order'
        }

    order_id = payment_order.get('order_id', False)
    if not order_id:
        return {
            'title': 'failure',
            'error': 'Invalid Order ID'
        }

    total_amount = payment_order.get('total_amount', False)
    if not total_amount:
        return {
            'title': 'failure',
            'error': 'Invalid Total Amount'
        }

    return {
        'title': 'success'
    }


def check_kwargs_query_order(cr, kwargs):
    res = check_identity(cr, kwargs)

    if res['title'] != 'success':
        return res

    order_id = kwargs.get('order_id', False)
    if not order_id:
        return {
            'title': 'failure',
            'error': 'Invalid Order ID'
        }

    return {
        'title': 'success'
    }


def check_kwargs_pay_refund(cr, kwargs):
    """退款接口参数校验"""
    res = check_identity(cr, kwargs)

    if res['title'] != 'success':
        return res

    refund_info = kwargs.get("refund_info", False)
    if not refund_info or "order_id" not in refund_info \
            or "refund_amount" not in refund_info:
        return{
            "title": "failure",
            "error": "Invalid refund info"
        }

    return {
        "title": "success"
    }


def check_identity(cr, kwargs):
    if not kwargs.get('ihyf_payment_id', False):
        return {
            'title': 'failure',
            'error': "Invalid Hollywant Payment ID"
        }
    ihyf_payment_id = kwargs.get('ihyf_payment_id', False)

    if not kwargs.get('ihyf_secret_key', False):
        return {
            'title': 'failure',
            'error': 'Invalid Hollywant Secret Key'
        }
    ihyf_secret_key = kwargs.get('ihyf_secret_key', False)

    payment_user_info = get_payment_user_info(cr, ihyf_payment_id)
    if not payment_user_info:
        return {
            'title': 'failure',
            'error': 'Payment ID is not exist'
        }

    if ihyf_secret_key != payment_user_info['ihyf_secret_key']:
        return {
            'title': 'failure',
            'error': 'Hollywant Secret Key ID is not right'
        }

    return {
        'title': 'success'
    }
