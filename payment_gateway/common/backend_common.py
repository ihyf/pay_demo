# -*- coding: utf-8 -*-
import ConfigParser
import os
from datetime import datetime
from xml.etree import ElementTree
import hashlib
import random


def get_md5_string(source):
    now_time = datetime.now()
    now_time_str = now_time.strftime('%Y:%m:%d %H:%M:%S')
    random_string = str(random.random())
    md5 = hashlib.md5()
    md5.update(source + now_time_str + random_string)
    return md5.hexdigest()


def get_payment_user_info(cr, ihyf_payment_id):
    """获取用户网关配置信息"""
    sql = """
            select * from payment_user_info where ihyf_payment_id = '%s'
    """ % (ihyf_payment_id,)
    cr.execute(sql)
    res = cr.dictfetchone()

    if not res:
        return False

    if len(res) == 0:
        return False

    return res


def get_payment_order_by_id(cr, payment_id):
    sql = """
            select * from payment_order where
                payment_id = '%s'
    """ % (payment_id, )
    cr.execute(sql)
    res = cr.dictfetchone()

    if not res:
        return False

    if len(res) == 0:
        return False

    return res


def get_payment_order(cr, name, payment_type, source):
    sql = """
            select * from payment_order where
                name = '%s' and
                payment_type = '%s' and
                source = '%s'
    """ % (name, payment_type, source)
    cr.execute(sql)
    res = cr.dictfetchone()

    if not res:
        return False

    if len(res) == 0:
        return False

    return res


def create_payment_order(
    cr, payment_order, ihyf_payment_id,
    ihyf_secret_key, payment_type, source,
    payment_id, order_status=u'draft'
):
    name = payment_order['order_id']
    total_amount = payment_order['total_amount']
    payment_type = payment_type
    source = source
    payment_status = u'not_pay'
    order_status = order_status
    product_name = payment_order.get('product_name', u'')
    create_time = datetime.utcnow()
    update_time = create_time
    description = payment_order.get('body', u'')
    payment_id = payment_id

    cr.execute("""
        insert into payment_order (
            name,total_amount,payment_type,payment_status,order_status,product_name,create_time,update_time,
            description, ihyf_payment_id, ihyf_secret_key,
            source, payment_id
        ) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", (
        name, total_amount, payment_type, payment_status, order_status,
        product_name, create_time, update_time, description,
        ihyf_payment_id, ihyf_secret_key, source, payment_id)
    )

    cr.commit()

    return


def get_payment_id(order_id, payment_type, source):
    return "%s_%s" % (order_id, source)


def update_payment_order(cr, payment_status, payment_id, payment_type, order_status):
    current_time = datetime.utcnow()

    """更新订单支付状态"""
    cr.execute("""
        update payment_order set payment_status='%s',order_status='%s',
            update_time = '%s'
            where payment_id='%s' and payment_type = '%s'

    """ % (
        payment_status, order_status, current_time, payment_id, payment_type))

    cr.commit()

    return


def update_wangbipay_code(cr, wangbipay_code, order_id):
    """将*币code更新到订单中"""
    cr.execute("""
        update payment_order set wangbipay_code='%s' where name ='%s'

    """ % (wangbipay_code, order_id))

    cr.commit()

    return


def xml_to_array(xml):
    """将xml转为dict"""
    array_data = {}
    root = ElementTree.fromstring(xml)
    for child in root:
        value = child.text
        array_data[child.tag] = value
    return array_data


def get_notify_url(cr):
    """从payment.public.settings获得最新的回调url"""
    cr.execute(
        """select notify_url from payment_public_settings
              order by write_date DESC limit 1"""
    )
    res = cr.dictfetchone()

    if not res:
        return ''
    return res['notify_url']


def get_conf_info(key):
    """获取配置文件信息"""
    config = ConfigParser.ConfigParser()
    path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), os.pardir
        )
    ) + '/gateway.conf'
    config.read(path)
    value = config.get('options', key)
    return value
