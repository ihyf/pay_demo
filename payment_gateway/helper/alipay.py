# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import rsa
import json
import base64
import urllib
import datetime
import requests
from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from odoo.addons.ihyf_payment_gateway.common.backend_common import get_conf_info
import logging

_logger = logging.getLogger(__name__)

# 支付宝统一接口
ALIPAY_OPENAPI_GATEWAY = get_conf_info('ALIPAY_OPENAPI_GATEWAY')  # 获得config配置
# ALIPAY_OPENAPI_GATEWAY = 'https://openapi.alipaydev.com/gateway.do'  # 沙箱
# ALIPAY_OPENAPI_GATEWAY = 'https://openapi.alipay.com/gateway.do'  # 正式环境

# 支付宝统一收单交易查询接口
METHOD_TRADE_QUERY = "alipay.trade.query"

# 支付宝统一收单交易预创建接口
METHOD_TRADE_PRECREATE = "alipay.trade.precreate"

# 支付宝统一收单交易退款接口
METHOD_TRADE_REFUND = "alipay.trade.refund"

# 支付宝统一收单交易关闭接口
METHOD_TRADE_CLOSE = "alipay.trade.close"

# 支付宝统一收单交易撤销接口
METHOD_TRADE_CANCEL = "alipay.trade.cancel"


def _generate_sign(private_key, reverse=False, quotes=False, **kwargs):
    """
    计算支付宝支付的签名
    """
    query = ""
    SIGN_TYPE = "SHA-1"
    for key in sorted(kwargs.keys(), reverse=reverse):
        value = kwargs[key]
        if quotes:
            query += str(key) + "=\"" + str(value) + "\"&"
        else:
            query += str(key) + "=" + str(value) + "&"
    message = query[0:-1]
    private_key = rsa.PrivateKey._load_pkcs1_pem(private_key)
    sign = rsa.sign(message, private_key, SIGN_TYPE)
    b64sing = base64.b64encode(sign)
    return b64sing


def _base_open_api_params(method, app_id, private_key, **kwargs):
    """
    传入基础api参数
    ali-pay request generator
    kwargs:
    dict to generate a json
    """
    all_params = {
        "app_id": app_id,
        "method": method,
        "charset": "UTF-8",
        "sign_type": "RSA",
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "version": "1.0",
        "biz_content": json.dumps(kwargs)
    }
    all_params.update(kwargs)
    all_params["sign"] = _generate_sign(
        private_key, **all_params)
    return all_params


def alipay_generate_prepay_native(data):
    """
    获取支付宝的付款二维码
    transact_num: 交易号
    cash: 金额(float)
    subject: 显示在交易内容里面
    """

    resp = requests.post(ALIPAY_OPENAPI_GATEWAY, data=_base_open_api_params(
        method=data['method'],
        notify_url=data['notify_url'],
        app_id=data['app_id'],
        private_key=data['private_key'],
        biz_content=json.dumps({
            "out_trade_no": data['payment_id'],
            "seller_id": data['seller_id'],
            "total_amount": data['cash'],
            "subject": data['description']
        })
    ))
    content = json.loads(resp.content.decode("gbk"))
    logging.info("get alipay url")
    logging.info(content)
    if content["alipay_trade_precreate_response"]["msg"] == "Success":
        return {
            'result': 'SUCCESS',
            'code_url': content["alipay_trade_precreate_response"]["qr_code"]
        }
    else:
        return {
            'title': 'FAIL',
            'error': content["alipay_trade_precreate_response"]["msg"]
        }


def alipay_rsa_verify(paras, sign, private_key, public_key):
    """对签名做rsa验证"""
    paras = params_to_query(paras)
    sign = base64.b64decode(sign)
    pubkey = rsa.PublicKey.load_pkcs1_openssl_pem(public_key)
    return rsa.verify(paras, sign, pubkey)


def params_to_query(params, quotes=False, reverse=False):
    """
    生成需要签名的字符串
    param params:
    return:
    """
    query = ""
    for key in sorted(params.keys(), reverse=reverse):
        value = params[key]
        if quotes:
            query += str(key) + "=\"" + str(value) + "\"&"
        else:
            query += str(key) + "=" + str(value) + "&"
    query = query[0:-1]
    return query


def _alipay_filter_para(paras):
    """过滤空值和签名"""
    for k, v in paras.items():
        if (k in ['sign', 'sign_type']) or v == '':
            paras.pop(k)
    return paras


def _alipay_create_link_string(paras, sort, encode):
    """对参数排序并拼接成query string的形式"""
    if sort:
        paras = sorted(paras.items(), key=lambda d: d[0])
    if encode:
        return urllib.urlencode(paras)
    else:
        if not isinstance(paras, list):
            paras = list(paras.items())
        ps = ''
        for p in paras:
            if ps:
                ps = '%s&%s=%s' % (ps, p[0], p[1])
            else:
                ps = '%s=%s' % (p[0], p[1])

        return ps


# ##————————————支付宝查询订单支持————————————## #
def alipay_trade_query_call(
        method,
        notify_url,
        private_key,
        app_id,
        transact_num,
        trade_no=None,
        subject="查询"):
    """
    查询订单状态
    param trade_no: 交易号
    param out_trade_no: 订单号
    param subject: 显示在交易内容里面
    订单号,和支付宝交易号不能同时为空。 trade_no,out_trade_no如果同时存在优先取trade_no

    状态TRADE_SUCCESS的通知触发条件是商户签约的产品支持退款功能的前提下，买家付款成功；
    交易状态TRADE_FINISHED的通知触发条件是商户签约的产品不支持退款功能的前提下，买家付款成功；
    """
    resp = requests.post(ALIPAY_OPENAPI_GATEWAY, data=_base_open_api_params(
        method=method,
        notify_url=notify_url,
        app_id=app_id,
        private_key=private_key,
        biz_content=json.dumps({
            "out_trade_no": transact_num,
            "subject": subject,
            "trade_no": trade_no,
        })
    ))
    content = json.loads(resp.content.decode("gbk"))
    logging.info("query alipay")
    logging.info(content)
    response_info = content["alipay_trade_query_response"]
    out_trade_no = response_info.get('out_trade_no')
    sub_code = response_info.get('sub_code')
    trade_status = response_info.get('trade_status')
    params = dict()
    if response_info.get("code") == "10000":
        # 交易创建，等待买家付款
        if trade_status == "WAIT_BUYER_PAY":
            params['msg'] = 'WAIT_PAY'
        # 未付款交易超时关闭，或支付完成后全额退款
        elif trade_status == "TRADE_CLOSED":
            params['msg'] = 'TRADE_CLOSED'
        # 交易支付成功
        elif trade_status == "TRADE_SUCCESS":
            params['msg'] = 'SUCCESS'
        # 交易结束，不可退款
        elif trade_status == "TRADE_FINISHED":
            params['msg'] = 'TRADE_FINISHED'
        # 不存在，网路异常等等其他情况
        else:
            params['服务器错误,请联系客服']
    else:
        # 系统错误，重新发送请求
        if sub_code == "ACQ.SYSTEM_ERROR":
            alipay_trade_query_call(out_trade_no)
        # 参数无效，请检查请求参数
        elif sub_code == "ACQ.INVALID_PARAMETER":
            params['error'] = '请检查请求参数'
        # 交易不存在
        elif sub_code == "ACQ.TRADE_NOT_EXIST":
            params['msg'] = 'NOT_PAY'
    return params


# ##————————————支付宝退款支持————————————## #
def alipay_trade_refund(
        transact_num,
        refund_amount,
        refund_reason=None,
        trade_no=None,
        operator_id=None,
        store_id=None,
        terminal_id=None,
        app_id=None,
        private_key=None):
    """
    trade_no和out_trade_no不能同时为空,如果同时传了 out_trade_no和 trade_no，则以 trade_no为准
    refund_amount: 需要退款的金额，该金额不能大于订单金额,单位为元，
    out_request_no:标识一次退款请求，同一笔交易多次退款需要保证唯一，如需部分退款，则此参数必传。
    store_id:商户的门店编号
    terminal_id:商户的终端编号
    operator_id :商户的操作员编号
    return:
    """
    resp = requests.post(ALIPAY_OPENAPI_GATEWAY, data=_base_open_api_params(
        method=METHOD_TRADE_REFUND,
        app_id=app_id,
        private_key=private_key,
        biz_content=json.dumps({
            "out_trade_no": transact_num,
            "operator_id": operator_id,
            "refund_amount": refund_amount,
            "trade_no": trade_no,
            "refund_reason": refund_reason,
            "store_id": store_id,
            "terminal_id": terminal_id,
        })
    ))
    content = json.loads(resp.content.decode("gbk"))
    response_info = content["alipay_trade_refund_response"]
    # 判断code或sub_code
    if response_info['code'] == '10000' and response_info['msg'] == 'Success':
        if response_info['fund_change'] == 'Y':
            # 要修改退款表
            logging.info("alipay_pay_refund success")
            return {
                "result": {
                    "msg": "SUCCESS",
                    "title": "支付宝退款"
                }
            }
        elif response_info['fund_change'] == 'N':
            """已发生过退款,账户金额未变动"""
            return {
                "result": {
                    "msg": "SUCCESS N",
                    "title": "支付宝已退款过"
                }
            }
    else:
        return {
            "error": "退款失败",
            "title": "支付宝退款"
        }



# ##————————————支付宝关闭交易支持————————————## #
def alipay_trade_close(transact_num, trade_no=None, operator_id=None):
    """
    trade_no和out_trade_no不能同时为空,如果同时传了 out_trade_no和 trade_no，则以 trade_no为准
    :param operator_id 卖家端自定义的的操作员 ID
    :return:
    """
    resp = requests.post(ALIPAY_OPENAPI_GATEWAY, data=_base_open_api_params(
        method=METHOD_TRADE_CLOSE,
        biz_content=json.dumps({
            "out_trade_no": transact_num,
            "operator_id": operator_id,
            "trade_no": trade_no,
        })
    ))
    content = json.loads(resp.content.decode("gbk"))
    response_info = content["alipay_trade_close_response"]
    # 判断code或sub_code
    if response_info['code'] == '':
        pass


# ##————————————支付宝撤销交易支持————————————## #
def alipay_trade_cancel(transact_num, trade_no=None):
    """
    trade_no和out_trade_no不能同时为空,如果同时传了 out_trade_no和 trade_no，则以 trade_no为准
    param a:
    param b:
    return:
    """
    resp = requests.post(ALIPAY_OPENAPI_GATEWAY, data=_base_open_api_params(
        method=METHOD_TRADE_CANCEL,
        biz_content=json.dumps({
            "out_trade_no": transact_num,
            "trade_no": trade_no,
        })
    ))
    content = json.loads(resp.content.decode("gbk"))
    response_info = content["alipay_trade_cancel_response"]
    # 判断code或sub_code
    if response_info['code'] == '10000':
        # 是否需要重试
        if response_info['retry_flag '] == 'N':
            pass
        # close(关闭交易，无退款) or refund (产生了退款)
        if response_info['action'] == 'close':
            pass
