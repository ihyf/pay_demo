# -*- coding: utf-8 -*-
from openerp import api, fields, models
from odoo.addons.ihyf_payment_gateway.common.backend_common \
    import get_payment_user_info
from openerp.tools.translate import _


class PaymentOrder(models.Model):
    _name = 'payment.order'
    _order = 'update_time desc'

    name = fields.Char(
        string='Order ID'
    )

    payment_id = fields.Char(
        string='Payment ID'
    )

    total_amount = fields.Float(
        string='Total Amount'
    )

    payment_type = fields.Selection(
        string='Payment Type',
        selection='_get_payment_type',
    )

    payment_status = fields.Selection(
        string='Payment Status',
        selection='_get_payment_status',
    )

    order_status = fields.Selection(
        string='Order Status',
        selection='_get_order_status',
    )

    product_name = fields.Char(
        string='Product Name',
    )

    create_time = fields.Datetime(
        string="Create Time",
    )

    update_time = fields.Datetime(
        string="Update Time",
    )

    ihyf_payment_id = fields.Char(
        string="Hollywant Payment ID",
    )

    ihyf_secret_key = fields.Char(
        string="Hollywant Secret Key",
    )

    description = fields.Char(
        string="Description",
    )

    wangbipay_code = fields.Char(
        string="Wangbi code"
    )

    source = fields.Char(
        string="Source"
    )

    @api.model
    def _get_payment_type(self):
        return [
            ('alipay', _('Ali pay')),
            ('weixinpay', _('Weixin Pay')),
            ('wangbipay', _('Wang Bi Pay')),
        ]

    @api.model
    def _get_payment_status(self):
        return [
            ('not_pay', _('Not Pay')),
            ('paid', _('Paid')),
            ('wait_pay', _('Wait Pay')),
        ]

    @api.model
    def _get_order_status(self):
        return [
            ('draft', _('Draft')),
            ('done', _('Done')),
            ('cancel', _('Cancel')),
            ('return', _('Return')),
        ]

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        res = super(PaymentOrder, self).read(fields=fields, load=load)
        user_id = self.env.user.id

        if user_id == 1:
            return res

        params = self._context.get('params', False)

        if params:
            action = params.get('action', False)

            if action:
                action_id = self.env.ref(
                    'ihyf_payment_gateway.action_payment_order')

                if action == action_id.id:
                    values = []
                    for rec in res:
                        payment_user_info = get_payment_user_info(
                            self._cr,
                            rec['ihyf_payment_id'])

                        if user_id == payment_user_info['user_id']:
                            values.append(rec)

                    return values
        return res
