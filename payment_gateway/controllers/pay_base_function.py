# coding:utf-8
from odoo.addons.ihyf_payment_gateway.controllers.pay_base_controller \
    import PayBaseController
from odoo.http import request


class PayBaseFunction(PayBaseController):
    def pay_qrcode(self, *args, **kwargs):
        payment_type = kwargs.get('payment_type', False)
        method = kwargs.get('method', False)
        payment_url = "self.%s_%s" % (method, payment_type)
        return eval(payment_url)(request, *args, **kwargs)

    def query_order(self, *args, **kwargs):
        payment_type = kwargs.get('payment_type', False)
        method = kwargs.get('method', False)

        if not payment_type:
            order_id = kwargs.get('order_id')
            request.cr.execute(
                """
                    select * from payment_order where name = '%s'
                    ORDER BY update_time
                """ % (order_id,)
            )
            res = request.cr.dictfetchall()
            if res:
                for rec in res[0:-1]:
                    payment_type = rec['payment_type']
                    query_url = "self.%s_%s" % (
                        method, payment_type)

                    info = eval(query_url)(request, *args, **kwargs)

                    error = info.get('error', False)

                    if not error:
                        msg = info.get('msg', False)

                        if msg == 'SUCCESS':
                            return info

                payment_type = res[-1]['payment_type']
            else:
                return {"error": "order is not exist!"}

        query_url = "self.%s_%s" % (method, payment_type)
        return eval(query_url)(request, *args, **kwargs)

    def pay_refund(self, *args, **kwargs):
        """退款"""
        payment_type = kwargs.get('payment_type', False)
        method = kwargs.get('method', False)
        payment_url = "self.%s_%s" % (method, payment_type)
        return eval(payment_url)(request, *args, **kwargs)