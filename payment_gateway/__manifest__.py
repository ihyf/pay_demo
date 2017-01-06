# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Hollywant Payment Gateway',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Payment Gateway',
    'description': """
    """,
    'depends': ['base'],
    'data': [
        "views/payment_order_view.xml",
        "views/payment_user_info_view.xml",
        "views/payment_public_settings_view.xml",
        "views/index_view.xml",
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
