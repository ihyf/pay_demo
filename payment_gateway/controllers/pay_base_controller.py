# coding:utf-8
from odoo import http
from odoo.addons.web.controllers.main import DataSet
from odoo.http import request
from odoo.addons.ihyf_payment_gateway.common.check_common import *


class PayBaseController(DataSet):
    @http.route(['/ihyf/pay'], type='json', auth='none')
    def payment_router(self, *args, **kwargs):
        try:
            method = kwargs.get('method', False)
            res = eval("check_kwargs_%s" % method)(request.cr, kwargs)
            if res['title'] != 'success':
                return res

            return eval("self.%s" % method)(request, *args, **kwargs)
        except Exception, e:
            return e
