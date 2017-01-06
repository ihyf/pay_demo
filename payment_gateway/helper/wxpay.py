#! /usr/bin/env python2.7
# -*- coding: UTF-8 -*-

import time
import json
import qrcode
import hashlib
import urllib
import random
import requests
import logging
from xml.etree import ElementTree
from dict2xml import dict2xml
from collections import OrderedDict
from urllib import urlencode
from odoo.addons.ihyf_payment_gateway.common.backend_common import get_conf_info
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

class WXpayException(Exception):
    """Base Alipay Exception"""


class MissingParameter(WXpayException):
    """Raised when the create payment url process is missing some
    parameters needed to continue"""


class ParameterValueError(WXpayException):
    """Raised when parameter value is incorrect"""


class TokenAuthorizationError(WXpayException):
    """The error occurred when getting token"""


class WXpay(object):
    """ 微信支付base class """

    URL_UINFIEDORDER = get_conf_info('URL_UINFIEDORDER')
    URL_VERIFY_ORDER = get_conf_info('URL_VERIFY_ORDER')
    # URL_UINFIEDORDER = 'https://api.mch.weixin.qq.com/pay/unifiedorder'
    # URL_VERIFY_ORDER = 'https://api.mch.weixin.qq.com/pay/orderquery'

    def __init__(self, appid, mch_id, key, ip,
                 notify_url=None, appsecret=None):
        self.appid = appid
        self.mch_id = mch_id
        self.key = key
        self.appsecret = appsecret
        self.ip = ip
        self.notify_url = notify_url
        self.cert_path = "pem证书路径"

    def generate_nonce_str(self, length=32):
        """ 生成随机字符串 """
        hash_char = [
            '0', '1', '2', '3', '4', '5', '6', '7',
            '8', '9',
            'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H',
            'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P',
            'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X',
            'Y', 'Z',
            'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h',
            'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p',
            'q', 'r', 's', 't', 'u', 'v', 'w', 'x',
            'y', 'z',
        ]
        rand_list = [hash_char[random.randint(0, 61)] for i in range(0, length)]
        nonce_str = ''.join(rand_list)
        return nonce_str

    def xml_to_array(self, xml):
        """将xml转为dict"""
        array_data = {}
        root = ElementTree.fromstring(xml)
        for child in root:
            value = child.text
            array_data[child.tag] = value
        return array_data

    def generate_sign(self, sign_dict):
        """生成签名, 目前只支持MD5签名"""

        params_dict = OrderedDict(sorted(sign_dict.items(),
                                         key=lambda t: t[0]))
        params_dict['key'] = self.key

        foo_sign = []
        for k in params_dict:
            if isinstance(params_dict[k], unicode):
                params_dict[k] = params_dict[k].encode('utf-8')
            foo_sign.append('%s=%s' % (k, params_dict[k], ))
        foo_sign = '&'.join(foo_sign)
        sign = hashlib.md5(foo_sign).hexdigest().upper()
        return sign

    def unifiedorder(self, product, openid=None, trade_type=None):
        """统一下单接口"""

        assert isinstance(product, dict)
        assert trade_type in ('JSAPI', 'NATIVE')

        post_dict = {
            'appid': self.appid,
            'attach': product['attach'],
            'body': product['body'],
            'mch_id': self.mch_id,
            'nonce_str': self.generate_nonce_str(),
            'notify_url': self.notify_url,
            'out_trade_no': product['payment_id'],
            'product_id': product['product_id'],
            'spbill_create_ip': self.ip,
            'total_fee': product['total_fee'],  # 微信基本单位是分
            'trade_type': trade_type,
        }
        if trade_type == 'JSAPI' and openid is None:
            raise MissingParameter(u'JSAPI必须传入openid')
        else:
            if openid:
                post_dict['openid'] = openid
        post_dict['sign'] = self.generate_sign(post_dict)
        ret_xml = dict2xml(post_dict, wrap='xml')
        # logger.info(ret_xml)
        r = requests.post(self.URL_UINFIEDORDER, data=ret_xml.encode('utf-8'))
        r.encoding = 'UTF-8'
        data = r.text.encode('UTF-8')
        logging.info("get weixinpay url")
        logging.info(data)
        ret_dict = {}
        x = ElementTree.fromstring(data)
        if x.find('return_code').text.upper() == 'FAIL':
            raise ParameterValueError(x.find('return_msg').text)
        if x.find('result_code').text.upper() == 'FAIL':
            raise ParameterValueError(x.find('err_code').text)
        if trade_type == 'NATIVE':
            ret_dict['prepay_id'] = x.find('prepay_id').text
            ret_dict['code_url'] = x.find('code_url').text
        else:
            ret_dict['prepay_id'] = x.find('prepay_id').text
        ret_dict['nonce_str'] = post_dict['nonce_str']
        ret_dict['sign'] = post_dict['sign']
        return ret_dict

    def refundorder(
            self,
            out_trade_no=None,
            transaction_id=None,
            total_fee=None,
            refund_fee=None):
        """退款接口"""

        post_dict = {
            'appid': self.appid,
            'mch_id': self.mch_id,
            'nonce_str': self.generate_nonce_str(),
            'out_trade_no': out_trade_no,
            "out_refund_no": out_trade_no,
            "transaction_id": transaction_id,
            "total_fee": total_fee,
            'refund_fee': refund_fee,
            "op_user_id": self.mch_id
        }

        post_dict["sign"] = self.generate_sign(post_dict)
        ret_xml = dict2xml(post_dict, wrap='xml')

        r = requests.post(
            self.URL_REFUND_ORDER,
            data=ret_xml.encode('utf-8'),
            cert=self.cert_path)
        r.encoding = 'UTF-8'
        data = r.text.encode('utf-8')
        ret_dict = {}
        x = ElementTree.fromstring(data)
        if x.find('return_code').text.upper() == 'FAIL':
            raise ParameterValueError(x.find('return_msg').text)
        if x.find('result_code').text.upper() == 'FAIL':
            raise ParameterValueError(x.find('err_code').text)

        if x.find('return_code').text.upper() == "SUCCESS" and x.find(
                'result_code').text.upper() == "SUCCESS":
            return True
        return False

    def verify_notify(self, xml_str):
        """验证通知返回值"""
        xml_dict = {}
        x = ElementTree.fromstring(xml_str)
        xml_dict['appid'] = x.find('appid').text
        xml_dict['attach'] = x.find('attach').text
        xml_dict['bank_type'] = x.find('bank_type').text
        xml_dict['cash_fee'] = x.find('cash_fee').text
        xml_dict['fee_type'] = x.find('fee_type').text
        xml_dict['is_subscribe'] = x.find('is_subscribe').text
        xml_dict['mch_id'] = x.find('mch_id').text
        xml_dict['nonce_str'] = x.find('nonce_str').text
        xml_dict['openid'] = x.find('openid').text
        xml_dict['out_trade_no'] = x.find('out_trade_no').text
        xml_dict['result_code'] = x.find('result_code').text
        xml_dict['return_code'] = x.find('return_code').text
        xml_dict['sign'] = x.find('sign').text
        xml_dict['time_end'] = x.find('time_end').text
        xml_dict['total_fee'] = x.find('total_fee').text
        xml_dict['trade_type'] = x.find('trade_type').text
        xml_dict['transaction_id'] = x.find('transaction_id').text

        sign = xml_dict.pop('sign')
        if sign == self.generate_sign(xml_dict):
            return True, xml_dict
        else:
            raise TokenAuthorizationError(u'签名验证失败')

    def generate_notify_resp(self, resp_dict):
        assert set(resp_dict.keys()) == set(['return_code', 'return_msg'])

        xml_str = dict2xml(resp_dict, wrap='xml')
        return xml_str

    def verify_order(self, out_trade_no=None, transaction_id=None):
        if out_trade_no is None and transaction_id is None:
            raise MissingParameter(u'out_trade_no, transaction_id 不能同时为空')
        params_dict = {
            'appid': self.appid,
            'mch_id': self.mch_id,
            'nonce_str': self.generate_nonce_str(),
        }
        if transaction_id is not None:
            params_dict['transaction_id'] = transaction_id
        elif out_trade_no is not None:
            params_dict['out_trade_no'] = out_trade_no
        params_dict['sign'] = self.generate_sign(params_dict)

        xml_str = dict2xml(params_dict, wrap='xml')

        r = requests.post(self.URL_VERIFY_ORDER, xml_str)
        r.encoding = 'UTF-8'
        data = r.text.encode('UTF-8')

        xml_dict = {}
        # x = ElementTree.fromstring(data)
        # xml_dict['return_code'] = x.find('return_code').text
        # xml_dict['return_msg'] = x.find('return_msg').text
        #
        # if xml_dict['return_code'] == 'FAIL':
        #     return xml_dict
        # xml_dict['appid'] = x.find('appid').text
        # xml_dict['mch_id'] = x.find('mch_id').text
        # # xml_dict['device_info'] = x.find('device_info').text
        # xml_dict['nonce_str'] = x.find('nonce_str').text
        # xml_dict['sign'] = x.find('sign').text
        # xml_dict['result_code'] = x.find('result_code').text
        # # xml_dict['err_code'] = x.find('err_code').text
        # # xml_dict['err_code_des'] = x.find('err_code_des').text
        # xml_dict['openid'] = x.find('openid').text
        # xml_dict['is_subscribe'] = x.find('is_subscribe').text
        # xml_dict['trade_type'] = x.find('trade_type').text
        # xml_dict['bank_type'] = x.find('bank_type').text
        # xml_dict['total_fee'] = x.find('total_fee').text
        # xml_dict['fee_type'] = x.find('fee_type').text
        # xml_dict['cash_fee'] = x.find('cash_fee').text
        # # xml_dict['cash_fee_type'] = x.find('cash_fee_type').text
        # # xml_dict['coupon_fee'] = x.find('coupon_fee').text
        # # xml_dict['coupon_count'] = int(x.find('coupon_count').text)
        # # for i in range(xml_dict['coupon_count']):
        # #     xml_dict['coupon_batch_id_%d' % i+1] = x.find('coupon_batch_id_%d' % i+1).text
        # #     xml_dict['coupon_id_%d' % i+1] = x.find('coupon_id_%d' % i+1).text
        # #     xml_dict['coupon_fee_%d' % i+1] = x.find('coupon_fee_%d' % i+1).text
        # xml_dict['transaction_id'] = x.find('transaction_id').text
        # xml_dict['out_trade_no'] = x.find('out_trade_no').text
        # xml_dict['attach'] = x.find('attach').text
        # xml_dict['time_end'] = x.find('time_end').text
        # xml_dict['trade_state'] = x.find('trade_state').text
        xml_dict = super(QRWXpay, self).xml_to_array(data)
        sign = xml_dict.pop('sign')
        if sign == self.generate_sign(xml_dict):
            return xml_dict
        else:
            xml_dict['result_code'] = 'FAIL'
            return xml_dict
            # raise TokenAuthorizationError(u'签名验证失败')


class QRWXpay(WXpay):
    """ 扫码支付接口 """

    URL_QR = 'weixin://wxpay/bizpayurl?%s'

    def _generate_qr_url(self, product_id):
        """
        生成QR URL
        即微信支付模式一,QR, 预生成一个 用户扫描后, 微信会调用在微信平台上配置的回调URL
        """
        url_dict = {
            'appid': self.appid,
            'mch_id': self.mch_id,
            'nonce_str': self.generate_nonce_str(),
            'product_id': str(product_id),
            'time_stamp': str(int(time.time())),
        }
        url_dict['sign'] = self.generate_sign(url_dict)
        url_str = self.URL_QR % urlencode(url_dict)
        return url_str

    def unifiedorder(self, product, openid=None):
        ret_dict = super(
            QRWXpay,
            self).unifiedorder(
            product,
            trade_type='NATIVE')
        return ret_dict

    def _generate_unfiedorder_url(self, product):
        """
        生成QR URL
        即微信支付模式二, 通过统一下单接口生成 code_url
        """

        ret = self.unifiedorder(product=product)
        return ret['code_url']

    def _generate_qr(self, url):
        """
        生成url 的QR 码

        建议使用Pillow
        """
        img = qrcode.make(url)
        return img

    def generate_static_qr(self, product_id):
        """
        生成商品静态QR码

        即微信支付模式一
        返回为Pillow的img
        """
        url = self._generate_qr_url(product_id)
        img = self._generate_qr(url)
        return img

    def generate_product_qr(self, product):
        """
        生成商品QR码
        即微信支付模式二
        QR码有效时间两小时
        返回为Pillow的img
        """
        url = self._generate_unfiedorder_url(product)
        img = self._generate_qr(url)
        return img

    def _callback_xml2dict(self, xml_str):
        ret_dict = dict()
        # x = ElementTree.fromstring(xml_str)
        # ret_dict['appid'] = x.find('appid').text
        # ret_dict['openid'] = x.find('openid').text
        # ret_dict['mch_id'] = x.find('mch_id').text
        # ret_dict['is_subscribe'] = x.find('is_subscribe').text
        # ret_dict['nonce_str'] = x.find('nonce_str').text
        # ret_dict['product_id'] = x.find('product_id').text
        # ret_dict['sign'] = x.find('sign').text
        ret_dict = super(QRWXpay, self).xml_to_array(xml_str)

        return ret_dict

    def verify_callback(self, xml_str):
        """ 验证回调返回值 """
        xml_dict = self._callback_xml2dict(xml_str)
        sign = xml_dict.pop('sign')
        if sign == self.generate_sign(xml_dict):
            return True, xml_dict
        else:
            return False, xml_dict
            # raise TokenAuthorizationError(u'签名验证失败')

    def generate_cb_resp(self, resp_dict):
        ret_dict = {
            'appid': self.appid,
            'mch_id': self.mch_id,
            'nonce_str': self.generate_nonce_str(),
            'prepay_id': resp_dict['prepay_id'],
            'return_code': resp_dict['return_code'],  # 'SUCCESS', 'FAIL'
            'return_msg': resp_dict['return_msg'],  # 'OK'
            'result_code': resp_dict['result_code'],  # 'SUCCESS', 'FAIL'
            'err_code_des': resp_dict['err_code_des'],  # 'OK'
        }
        ret_dict['sign'] = self.generate_sign(ret_dict)
        ret_xml = dict2xml(ret_dict, wrap='xml')
        return ret_xml


class JSWXpay(WXpay):
    """ JSAPI 支付接口 """

    URL_REDIRECT = '''https://open.weixin.qq.com/connect/oauth2/authorize?%s'''\
                   '''#wechat_redirect'''
    URL_OPENID = '''https://api.weixin.qq.com/sns/oauth2/access_token?%s'''\
                 '''&grant_type=authorization_code'''

    def generate_redirect_url(self, url_dict):
        """ 生成跳转URL, 跳转后获取code, 以code获取openid """
        params_dict = {
            'appid': self.appid,
            'redirect_uri': url_dict['redirect_uri'],
            'response_type': 'code',
            'scope': 'snsapi_base',
            'state': url_dict['state'],
        }
        for k in params_dict:
            if isinstance(params_dict[k], unicode):
                params_dict[k] = params_dict[k].encode('utf-8')
        foo_url = urllib.urlencode(params_dict)
        url = self.URL_REDIRECT % foo_url
        return url

    def generate_openid(self, code):
        """ 根据code 获取openid """
        if self.appsecret is None:
            raise MissingParameter(u'缺少appsecret')
        params_dict = {
            'appid': self.appid,
            'secret': self.appsecret,
            'code': code,
        }

        foo_url = []
        for k in params_dict:
            if isinstance(params_dict[k], unicode):
                params_dict[k] = params_dict[k].encode('utf-8')
            foo_url.append('%s=%s' % (k, params_dict[k], ))
        foo_url = '&'.join(foo_url)
        url = self.URL_OPENID % foo_url

        r = requests.get(url)
        r.encoding = 'UTF-8'
        data = json.loads(r.text)

        return data['openid']

    def unifiedorder(self, product, openid=None):
        ret_dict = super(JSWXpay, self).unifiedorder(product,
                                                     openid=openid,
                                                     trade_type='JSAPI')
        return ret_dict

    def generate_jsapi(self, product, openid):
        """ 实际下单"""
        uni_dict = self.unifiedorder(product, openid)
        ret_dict = {
            'appId': self.appid,
            'timeStamp': int(time.time()),
            'nonceStr': self.generate_nonce_str(),
            'package': 'prepay_id=%s' % uni_dict['prepay_id'],
            'signType': 'MD5',
        }
        ret_dict['paySign'] = self.generate_sign(ret_dict)
        return ret_dict
