# -*-coding:utf-8-*-
from django.db import models
from db.base_model import BaseModel


class OrderInfo(BaseModel):
    """订单模型类"""
    PAY_METHODS = {
        '1': "货到付款",
        '2': "微信支付",
        '3': "支付宝",
        '4': '银联支付'
    }

    PAY_METHODS_ENUM = {
        "CASH": 1,
        "ALIPAY": 2
    }

    # 应该更改成为一个字典来取值
    ORDER_STATUS = {
        1: '待支付',
        2: '待发货',
        3: '待收货',
        4: '待评价',
        5: '已完成'
    }

    PAY_METHOD_CHOICES = (
        (1, '货到付款'),
        (2, '微信支付'),
        (3, '支付宝'),
        (4, '银联支付')
    )

    ORDER_STATUS_CHOICES = (
        (1, '待支付'),
        (2, '待发货'),
        (3, '待收货'),
        (4, '待评价'),
        (5, '已完成')
    )

    # order_id 不是非自动的,是我们指定的, 指定之后自增长的一列就没有了
    order_id = models.CharField(max_length=128, primary_key=True,verbose_name='订单id')
    user = models.ForeignKey('user.User', on_delete=models.CASCADE, verbose_name='用户')
    addr = models.ForeignKey('user.Address', on_delete=models.CASCADE, verbose_name='地址')
    pay_method = models.SmallIntegerField(choices=PAY_METHOD_CHOICES, default=3, verbose_name='支付方式')
    total_count = models.IntegerField(default=1, verbose_name='商品数量')
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='总金额')
    transit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='运费')
    # 设置有Default的之后,插入数据的时候可以不指定值,会使用默认的
    order_status = models.SmallIntegerField(choices=ORDER_STATUS_CHOICES, default=1, verbose_name='订单状态')
    # 支付宝返回的支付编号,开始设置默认为空default=''
    trade_no = models.CharField(max_length=128, default='', verbose_name='支付编号')

    class Meta:
        db_table = 'df_order_info'
        # 记得加上verbose_name,并使其生效
        verbose_name = '订单'
        verbose_name_plural = verbose_name


class OrderGoods(BaseModel):
    """订单商品模型类"""
    order = models.ForeignKey('OrderInfo', on_delete=models.CASCADE, verbose_name='订单')
    sku = models.ForeignKey('goods.GoodsSKU', on_delete=models.CASCADE, verbose_name='商品SKU')
    count = models.IntegerField(default=1, verbose_name='商品数目')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='价格')  # 总价格
    comment = models.CharField(max_length=256, default='', verbose_name='评论') # 评论可以默认为空

    class Meta:
        db_table = 'df_order_goods'
        # 记得加上verbose_name,并使其生效，两行
        verbose_name = '订单商品'
        verbose_name_plural = verbose_name



