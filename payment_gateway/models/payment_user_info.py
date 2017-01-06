# -*- coding: utf-8 -*-
from openerp import api, fields, models
from odoo.addons.ihyf_payment_gateway.common.backend_common import *
from openerp.tools.translate import _


class PaymentUserInfo(models.Model):
    _name = 'payment.user.info'

    name = fields.Char(
        string='Name',
        required=True
    )

    user_id = fields.Many2one(
        comodel_name='res.users',
        string='User',
        required=True,
        default=lambda self: self.env.user.id
    )

    ihyf_payment_id = fields.Char(
        string='Hollywant Payment ID',
        required=True
    )

    ihyf_secret_key = fields.Char(
        string='Hollywant Secret Key',
        required=True
    )
    # 支付宝信息配置
    alipay_seller_id = fields.Char(
        string='Alipay Seller ID',
        required=True
    )

    alipay_app_id = fields.Char(
        string='Alipay App ID',
        required=True
    )

    alipay_private_rsa = fields.Text(
        string='Alipay Private RSA'
    )
    alipay_public_key = fields.Text(
        string='Alipay Public Key'
    )
    # 微信信息配置
    weixinpay_seller_id = fields.Char(
        string='Weixinpay Seller ID',
        required=True
    )

    weixinpay_app_id = fields.Char(
        string='Weixinpay App ID',
        required=True
    )

    weixinpay_private_key = fields.Text(
        string='Weixinpay Private Key'
    )
    # *币信息配置
    wangbipay_seller_id = fields.Char(
        string='Wangbipay Seller ID',
        required=True
    )

    wangbipay_app_id = fields.Char(
        string='Wangbipay App ID',
        required=True
    )

    is_alipay = fields.Boolean(string='AliPay')

    is_weixinpay = fields.Boolean(string='WeixinPay')

    is_wangbipay = fields.Boolean(string='WangbiPay')

    @api.constrains('ihyf_payment_id')
    def _check_payment_id(self):
        payment_user = self.env['payment.user.info'].search(
            [('ihyf_payment_id', '=', self.ihyf_payment_id)]
        )
        if len(payment_user) > 1:
            raise ValueError(_('Payment ID is exist!'))

    @api.onchange('name')
    def onchange_name(self):
        if self.name:
            if not self.ihyf_secret_key:
                self.ihyf_secret_key = get_md5_string(self.name)

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        res = super(PaymentUserInfo, self).read(fields=fields, load=load)
        user_id = self.env.user.id

        if user_id == 1:
            return res

        params = self._context.get('params', False)

        if params:
            action = params.get('action', False)

            if action:
                action_id = self.env.ref(
                    'ihyf_payment_gateway.action_payment_user_info')

                if action == action_id.id:
                    values = []
                    for rec in res:
                        rec_user_id = rec['user_id']

                        if type(rec_user_id) != int:
                            rec_user_id = rec['user_id'][0]
                        if user_id == rec_user_id:
                            values.append(rec)

                    return values
        return res
