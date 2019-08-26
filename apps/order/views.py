from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.db import transaction
from django.views.generic.base import View
from django_redis import get_redis_connection

from apps.goods.models import GoodsSKU
from apps.order.models import OrderInfo, OrderGoods
from apps.user.models import Address
from utils.mixin import LoginRequiredMixin

from datetime import datetime
# Create your views here.

class OrderPlaceView(LoginRequiredMixin, View):
    '''提交订单页面'''

    def post(self, request):
        # 获取参数,一键多值 接受的是列表, 前端设置好传过来sku_ids
        sku_ids = request.POST.getlist('sku_ids')
        # print(sku_ids)  # ['2', '3', '4']
        # 进行参数校验
        if not all(sku_ids) or len(sku_ids) < 1:
            # 没有商品id, 重定向到购物车页面进行选择, 反向解析
            return redirect(reverse('cart:show'))
        # 获取登录的用户信息, 构建cart_key
        user = request.user
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id

        skus = []
        # 初始化总的数量和总价
        total_count = 0
        total_price = 0
        # 查询对应的商品信息
        for sku_id in sku_ids:
            sku = GoodsSKU.objects.get(id=sku_id)

            # 查询商品在购物车中的数量
            count = conn.hget(cart_key, sku_id)
            # 计算每种商品的小计, redis 中的值是字符串类型, 需要转化类型
            count = int(count)
            amount = sku.price * count
            # 动态的给sku对象添加数量和小计
            sku.count = count
            sku.amount = amount
            # 计算总的数量和总价
            total_count += count
            total_price += amount
            # 将最后的sku对象添加到列表中
            skus.append(sku)

        # for sku in skus:
        #     print(sku, type(sku))
        #     print(sku.name, sku.price, sku.count, sku.amount)

        # 运费:运费子系统(没有,这里写死)
        transit_price = 10
        # 实付款
        total_pay = total_price + transit_price

        # 获取用户的全部地址
        addrs = Address.objects.filter(user=user)

        # 获取用户购买的商品的id,需要拼接成为一个字符串,将sku_id['2', '3', '4'] 以逗号间隔拼接成字符串(操作列表)
        sku_ids = ','.join(sku_ids)

        # 组织上下文
        context = {'addrs': addrs,
                   'total_count': total_count,
                   'total_price': total_price,
                   'transit_price': transit_price,
                   'total_pay': total_pay,
                   'skus': skus,
                   'sku_ids': sku_ids}

        return render(request, 'place_order.html', context)


# 前端传递的参数:地址idaddr_id, 支付方式pay_method 用户要购买的商品的id(sku_ids)
class OrderCommitView(LoginRequiredMixin, View):
    """订单创建"""
    @transaction.atomic   # 事务操作装饰
    def post(self, request):
        '''订单创建'''
        # 判断用户是否登录
        user = request.user
        if not user.is_authenticated:
            # 用户未登录
            return JsonResponse({'res':0, 'errmsg':'用户未登录'})

        # 接收参数
        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')

        # 校验参数
        if not all([addr_id, pay_method, sku_ids]):
            return JsonResponse({'res':1, 'errmsg':'参数不完整'})

        # 校验支付方式
        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res':2, 'errmsg':'非法的支付方式'})

        # 校验地址
        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            # 地址不存在
            return JsonResponse({'res':3, 'errmsg':'地址非法'})

        # todo: 创建订单的核心业务

        # 组织参数:没有的参数搞出来
        # 订单id: 201908261816+用户id
        order_id = datetime.now().strftime('%Y%m%d%H%M%S') + str(user.id)

        # 运费
        transit_price = 10

        # 总数目和总金额
        total_count = 0
        total_price = 0

        # 设置事务的保存点
        save_id = transaction.savepoint()

        try:
        # todo: 向df_order_info表中添加一条记录
            order = OrderInfo.objects.create(order_id=order_id,
                                     user=user,
                                     addr=addr,
                                     pay_method=pay_method,
                                     total_count=total_count,
                                     total_price=total_price,
                                     transit_price=transit_price)

            # todo: 用户的订单中有几个商品,就需要向df_order_goods表中添加几条记录
            conn = get_redis_connection('default')
            cart_key = 'cart_%d'%user.id

            sku_ids = sku_ids.split(',')
            for sku_id in sku_ids:
                # 获取商品的信息
                try:
                    sku = GoodsSKU.objects.get(id=sku_id)
                except:
                    # 商品不存在
                    transaction.savepoint_rollback(save_id)  # 发生异常,数据库回滚
                    return JsonResponse({'res':4, 'errmsg':'商品不存在'})

                # 从redis中获取用户所要购买的商品的数量
                count = conn.hget(cart_key, sku_id)

                # todo:判断商品的库存
                if int(count) > sku.stock:
                    transaction.savepoint_rollback(save_id)
                    return JsonResponse({'res':6, 'errmsg':'商品库存不足'})

                # todo:向df_order_goods表中添加一条记录
                OrderGoods.objects.create(order=order,
                                          sku=sku,
                                          count=count,
                                          price=sku.price)

                # todo: 更新商品的库存和销量
                sku.stock -= int(count)
                sku.sales += int(count)
                sku.save()

                # todo: 累加更新计算订单商品的总数量和总价格
                amount = sku.price*int(count)
                total_count += int(count)
                total_price += amount

            # todo: 更新订单信息表中的商品的总数量和总价格
            order.total_count = total_count
            order.total_price = total_price
            order.save()
        except Exception as e:
            transaction.savepoint_rollback(save_id)
            return JsonResponse({'res':7, 'errmsg':'下单失败'})

        # 数据操作都没有问题之后需要进行数据的提交
        transaction.savepoint_commit(save_id)

        # todo: 清除用户购物车中的对应的记录 [1,3], *号会将列表拆分
        # print(*sku_ids) # 2 3
        conn.hdel(cart_key, *sku_ids)

        # 返回应答
        return JsonResponse({'res':5, 'message':'创建成功'})



























