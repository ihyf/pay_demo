# -*- coding: utf-8 -*-
from openerp import fields, models


class PaymentPublicSettings(models.Model):
    _name = 'payment.public.settings'

    name = fields.Char(
        string='Name',
        required=True
    )

    notify_url = fields.Char(
        string='Return url',
        required=True
    )
