from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.conf import settings
from django.db import transaction
from django.views.generic.base import View
from django_redis import get_redis_connection

from apps.goods.models import GoodsSKU
from apps.order.models import OrderInfo, OrderGoods
from apps.user.models import Address
from utils.mixin import LoginRequiredMixin

from alipay import AliPay

from datetime import datetime
import os


# Create your views here.

# /order/place
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
# 加上了MySQL的事务:一组MySQL操作,要么都成功,要么都失败
# 为了便于学习,这里设置为 OrderCommitView1
class OrderCommitView1(LoginRequiredMixin, View):
    """订单创建"""

    @transaction.atomic  # 事务操作装饰
    def post(self, request):
        '''订单创建'''
        # 判断用户是否登录
        user = request.user
        if not user.is_authenticated:
            # 用户未登录
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

        # 接收参数
        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')

        # 校验参数
        if not all([addr_id, pay_method, sku_ids]):
            return JsonResponse({'res': 1, 'errmsg': '参数不完整'})

        # 校验支付方式
        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res': 2, 'errmsg': '非法的支付方式'})

        # 校验地址
        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            # 地址不存在
            return JsonResponse({'res': 3, 'errmsg': '地址非法'})

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
            cart_key = 'cart_%d' % user.id

            sku_ids = sku_ids.split(',')
            for sku_id in sku_ids:
                # 获取商品的信息
                try:
                    sku = GoodsSKU.objects.get(id=sku_id)
                except:
                    # 商品不存在
                    transaction.savepoint_rollback(save_id)  # 发生异常,数据库回滚
                    return JsonResponse({'res': 4, 'errmsg': '商品不存在'})

                # 从redis中获取用户所要购买的商品的数量
                count = conn.hget(cart_key, sku_id)

                # todo:判断商品的库存
                if int(count) > sku.stock:
                    transaction.savepoint_rollback(save_id)
                    return JsonResponse({'res': 6, 'errmsg': '商品库存不足'})

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
                amount = sku.price * int(count)
                total_count += int(count)
                total_price += amount

            # todo: 更新订单信息表中的商品的总数量和总价格
            order.total_count = total_count
            order.total_price = total_price
            order.save()
        except Exception as e:
            transaction.savepoint_rollback(save_id)
            return JsonResponse({'res': 7, 'errmsg': '下单失败'})

        # 数据操作都没有问题之后需要进行数据的提交
        transaction.savepoint_commit(save_id)

        # todo: 清除用户购物车中的对应的记录 [1,3], *号会将列表拆分
        # print(*sku_ids) # 2 3
        conn.hdel(cart_key, *sku_ids)

        # 返回应答
        return JsonResponse({'res': 5, 'message': '创建成功'})


# 前端传递的参数:地址idaddr_id, 支付方式pay_method 用户要购买的商品的id(sku_ids)
# 加上了MySQL的事务:一组MySQL操作,要么都成功,要么都失败
# 高并发:秒杀-----> 解法1:悲观锁 ; 解法2:乐观锁
# 支付宝支付
# 悲观锁解决实例:认为别人也会购买:一开始就加锁
class OrderCommitView2(LoginRequiredMixin, View):
    """订单创建"""

    @transaction.atomic  # 事务操作装饰
    def post(self, request):
        '''订单创建'''
        # 判断用户是否登录
        user = request.user
        if not user.is_authenticated:
            # 用户未登录
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

        # 接收参数
        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')

        # 校验参数
        if not all([addr_id, pay_method, sku_ids]):
            return JsonResponse({'res': 1, 'errmsg': '参数不完整'})

        # 校验支付方式
        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res': 2, 'errmsg': '非法的支付方式'})

        # 校验地址
        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            # 地址不存在
            return JsonResponse({'res': 3, 'errmsg': '地址非法'})

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
            cart_key = 'cart_%d' % user.id

            sku_ids = sku_ids.split(',')
            for sku_id in sku_ids:
                # 获取商品的信息
                try:
                    # mysql中加锁的sql: select * from df_goods_sku where id=sku_id for update;
                    # 下面的查询需要做相应的更改,加上:select_for_update()
                    sku = GoodsSKU.objects.select_for_update().get(id=sku_id)
                except:
                    # 商品不存在
                    transaction.savepoint_rollback(save_id)  # 发生异常,数据库回滚
                    return JsonResponse({'res': 4, 'errmsg': '商品不存在'})

                # 演示悲观锁:连个用户秒杀一个鸡腿, 一个用户先拿到锁,释放之后另一个才能拿到锁
                # print('user:%d stock:%d'%(user.id, sku.stock))
                # import time
                # time.sleep(10)

                # 从redis中获取用户所要购买的商品的数量
                count = conn.hget(cart_key, sku_id)

                # todo:判断商品的库存
                if int(count) > sku.stock:
                    transaction.savepoint_rollback(save_id)
                    return JsonResponse({'res': 6, 'errmsg': '商品库存不足'})

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
                amount = sku.price * int(count)
                total_count += int(count)
                total_price += amount

            # todo: 更新订单信息表中的商品的总数量和总价格
            order.total_count = total_count
            order.total_price = total_price
            order.save()
        except Exception as e:
            transaction.savepoint_rollback(save_id)
            return JsonResponse({'res': 7, 'errmsg': '下单失败'})

        # 数据操作都没有问题之后需要进行数据的提交
        transaction.savepoint_commit(save_id)

        # todo: 清除用户购物车中的对应的记录 [1,3], *号会将列表拆分
        # print(*sku_ids) # 2 3
        conn.hdel(cart_key, *sku_ids)

        # 返回应答
        return JsonResponse({'res': 5, 'message': '创建成功'})


# 前端传递的参数:地址idaddr_id, 支付方式pay_method 用户要购买的商品的id(sku_ids)
# 加上了MySQL的事务:一组MySQL操作,要么都成功,要么都失败
# 高并发:秒杀-----> 解法1:悲观锁 ; 解法2:乐观锁
# 支付宝支付
# 乐观锁解决实例:认为别人不会购买,只在更新的时候判断,不一致才更新失败,否则成功
class OrderCommitView(LoginRequiredMixin, View):
    """订单创建"""

    @transaction.atomic  # 事务操作装饰
    def post(self, request):
        '''订单创建'''
        # 判断用户是否登录
        user = request.user
        if not user.is_authenticated:
            # 用户未登录
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

        # 接收参数
        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')

        # 校验参数
        if not all([addr_id, pay_method, sku_ids]):
            return JsonResponse({'res': 1, 'errmsg': '参数不完整'})

        # 校验支付方式
        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res': 2, 'errmsg': '非法的支付方式'})

        # 校验地址
        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            # 地址不存在
            return JsonResponse({'res': 3, 'errmsg': '地址非法'})

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
            cart_key = 'cart_%d' % user.id

            sku_ids = sku_ids.split(',')
            for sku_id in sku_ids:
                # 防止乐观锁判断购买一次失败,但是库存还有商品失败,所以尝试3次
                for i in range(3):
                    # 获取商品的信息
                    try:
                        sku = GoodsSKU.objects.get(id=sku_id)
                    except:
                        # 商品不存在
                        transaction.savepoint_rollback(save_id)  # 发生异常,数据库回滚
                        return JsonResponse({'res': 4, 'errmsg': '商品不存在'})

                    # 从redis中获取用户所要购买的商品的数量
                    count = conn.hget(cart_key, sku_id)

                    # todo:判断商品的库存
                    if int(count) > sku.stock:
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({'res': 6, 'errmsg': '商品库存不足'})

                    # todo: 更新商品的库存和销量
                    origin_stock = sku.stock
                    new_stock = origin_stock - int(count)
                    new_sales = sku.sales + int(count)  # 注意这里是数据库中的数据更新的

                    # 演示悲观锁:连个用户秒杀一个鸡腿, 一个用户先拿到锁,释放之后另一个才能拿到锁
                    # print('user:%d times:%d stock:%d'%(user.id, i, sku.stock))
                    # import time
                    # time.sleep(10)

                    # update df_goods_sku set stock=new_stock, sales=new_sales
                    # where id=sku_id and stock = origin_stock
                    # 意思就是判断更新的库存是否和原始库存一致的
                    # 返回一个整数:受影响的行数, 现在只操作一行,要么返回1,要么返回0,返回0就更新失败
                    res = GoodsSKU.objects.filter(id=sku_id, stock=origin_stock).update(stock=new_stock,
                                                                                        sales=new_sales)
                    if res == 0:
                        if i == 2:
                            # 尝试第三次下单失败才是真正返回下单失败, 否则继续判断
                            transaction.savepoint_rollback(save_id)
                            return JsonResponse({'res': 7, 'errmsg': '下单失败2'})
                        continue

                    # todo:向df_order_goods表中添加一条记录,放在后面是为了防止重复添加数据
                    OrderGoods.objects.create(order=order,
                                              sku=sku,
                                              count=count,
                                              price=sku.price)

                    # todo: 累加更新计算订单商品的总数量和总价格
                    amount = sku.price * int(count)
                    total_count += int(count)
                    total_price += amount

                    # 一次成功就跳出循环
                    break

            # todo: 更新订单信息表中的商品的总数量和总价格
            order.total_count = total_count
            order.total_price = total_price
            order.save()
        except Exception as e:
            transaction.savepoint_rollback(save_id)
            return JsonResponse({'res': 7, 'errmsg': '下单失败'})

        # 数据操作都没有问题之后需要进行数据的提交
        transaction.savepoint_commit(save_id)

        # todo: 清除用户购物车中的对应的记录 [1,3], *号会将列表拆分
        # print(*sku_ids) # 2 3
        conn.hdel(cart_key, *sku_ids)

        # 返回应答
        return JsonResponse({'res': 5, 'message': '创建成功'})


# 请求方式:ajax post
# 前端请求参数:订单id(order_id)
# /order/pay/
class OrderPayView(View):
    '''订单支付'''

    def post(self, request):

        # 用户是否登录
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

        # 接收参数
        order_id = request.POST.get('order_id')

        # 校验参数
        if not order_id:
            return JsonResponse({'res': 1, 'errmsg': '无效的订单'})

        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=user,
                                          pay_method=3,
                                          order_status=1)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '订单错误'})

        # 业务处理:使用python sdk 调用支付宝的支付接口
        # alipay初始化
        app_private_key_string = open("apps/order/app_private_key.pem").read()
        alipay_public_key_string = open("apps/order/alipay_public_key.pem").read()
        # app_private_key_string = os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem')
        # alipay_public_key_string = os.path.join(settings.BASE_DIR, 'apps/order/alipay_public_key.pem')

        alipay = AliPay(
            appid="2016101300679257",
            app_notify_url=None,  # 默认回调url
            app_private_key_string=app_private_key_string,
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_string=alipay_public_key_string,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=True  # 默认False, 此处沙箱模拟True
        )

        # 调用支付接口
        # 电脑网站支付，需要跳转到https://openapi.alipaydev.com/gateway.do? + order_string
        total_pay = order.total_price + order.transit_price  # 定义Model的是一个decimal类型,需要转成字符串
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,
            total_amount=str(total_pay),  # 支付的总金额
            subject='天天生鲜%s' % order_id,
            return_url=None,
            notify_url=None  # 可选, 不填则使用默认notify url
        )

        # 返回应答:引导用户到支付页面
        pay_url = 'https://openapi.alipaydev.com/gateway.do?' + order_string
        return JsonResponse({'res': 3, 'pay_url': pay_url})


# ajax post
# 前端请求参数:订单id(order_id)
# /order/check/
# 检查支付的结果
class CheckPayView(View):
    '''查看订单支付的结果'''

    def post(self, request):
        '''查询支付的结果'''
        # 用户是否登录
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

        # 接收参数
        order_id = request.POST.get('order_id')

        # 校验参数
        if not order_id:
            return JsonResponse({'res': 1, 'errmsg': '无效的订单'})

        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=user,
                                          pay_method=3,
                                          order_status=1)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '订单错误'})

        # 业务处理:使用python sdk 调用支付宝的支付接口
        # alipay初始化
        app_private_key_string = open("apps/order/app_private_key.pem").read()
        alipay_public_key_string = open("apps/order/alipay_public_key.pem").read()
        # app_private_key_string = os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem')
        # alipay_public_key_string = os.path.join(settings.BASE_DIR, 'apps/order/alipay_public_key.pem')

        alipay = AliPay(
            appid="2016101300679257",
            app_notify_url=None,  # 默认回调url
            app_private_key_string=app_private_key_string,
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_string=alipay_public_key_string,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=True  # 默认False, 此处沙箱模拟True
        )

        # 调用支付宝的交易查询接口
        while True:
            response = alipay.api_alipay_trade_query(order_id)

            # 返回字典的格式
            # response = {
            #         "trade_no": "2017032121001004070200176844", # 支付宝交易号
            #         "code": "10000",  # 接口调用是否成功
            #         "invoice_amount": "20.00",
            #         "open_id": "20880072506750308812798160715407",
            #         "fund_bill_list": [
            #             {
            #                 "amount": "20.00",
            #                 "fund_channel": "ALIPAYACCOUNT"
            #             }
            #         ],
            #         "buyer_logon_id": "csq***@sandbox.com",
            #         "send_pay_date": "2017-03-21 13:29:17",
            #         "receipt_amount": "20.00",
            #         "out_trade_no": "out_trade_no15",
            #         "buyer_pay_amount": "20.00",
            #         "buyer_user_id": "2088102169481075",
            #         "msg": "Success",
            #         "point_amount": "0.00",
            #         "trade_status": "TRADE_SUCCESS", # 支付结果
            #         "total_amount": "20.00"
            # }

            # 获取支付宝的支付代码
            code = response.get('code')

            if code == '10000' and response.get('trade_status') == 'TRADE_SUCCESS':
                # 支付成功
                # 获取支付宝的交易号
                trade_no = response.get('trade_no')
                # 更新订单的状态
                order.trade_no = trade_no
                order.order_status = 4  # 直接设置为4的待评价,跳过待发货,待收货
                order.save()
                # 返回结果
                return JsonResponse({'res': 3, 'message': '支付成功!'})

            elif code == '40004' or (code == '10000' and response.get('trade_status') == 'WAIT_BUYER_PAY'):
                # 等待买家付款, 间隔5秒之后再次查询
                import time
                time.sleep(5)
                continue

            else:
                # 其他情况
                print(code)
                return JsonResponse({'res': 4, 'message': '支付失败!'})
