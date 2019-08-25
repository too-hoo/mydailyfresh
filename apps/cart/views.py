from django.http import JsonResponse
from django.shortcuts import render
from django.views.generic import View
from django_redis import get_redis_connection
from utils.mixin import LoginRequiredMixin

from apps.goods.models import GoodsSKU
# Create your views here.
# 添加商品到购物车:
# 1)请求方式,采用ajax 的 post方式
# 如果涉及到数据的修改(新增,更新,删除),采用post
# 如果只涉及到数据的获取,采用get
# 2) 传递参数:商品的id, 商品的数量

# Ajax发送的请求都是后台的,浏览器是不会显示的,所以不能使用LoginRequireMixin
# /cart/add
class CartAddView(View):
    '''购物车的记录添加'''

    def post(self, request):
        '''购物车记录添加'''
        user = request.user
        if not user.is_authenticated:
            # 用户未登录
            return JsonResponse({'res':0, 'errmsg':'请先登录'})

        # 接收数据
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        # 数据校验
        if not all([sku_id, count]):
            return JsonResponse({'res':1, 'errmsg':'数据不完整'})

        # 校验添加的商品数量,非整数就会出错
        try:
            count = int(count)
        except Exception as e:
            # 数目出错
            return JsonResponse({'res':2, 'errmsg':'商品数目出错'})

        # 校验商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            # 商品不存在
            return JsonResponse({'res':3, 'errmsg':'商品不存在'})

        # 业务处理:添加购物车记录
        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%user.id
        # 先尝试获取sku_id的值-> hget cart_key 属性
        # 如果sku_id 在hash中不存在, hget返回None, 参考相关文档
        # 下面设置,该用户的redis购物车有就获取,没有就添加
        cart_count = conn.hget(cart_key, sku_id)
        # print(1, cart_count)
        if cart_count:
            # 累加购物车中的商品的数目
            count += int(cart_count)

        # 校验商品的库存
        if count > sku.stock:
            return JsonResponse({'res':4, 'errmsg':'商品库存不足'})
        # print(2, count)
        # 设置hash中sku_id对应的值
        # hset -> 如果已经存在,更新数据, 如果sku_id不存在,添加数据
        conn.hset(cart_key, sku_id, count)

        # 计算用户购物车中的商品的条目数
        total_count = conn.hlen(cart_key)

        # 返回应答
        return JsonResponse({'res':5, 'total_count':total_count, 'message':'添加成功'})


# 这里不是Ajax,所以可以使用LoginRequiredMixin
class CartInfoView(LoginRequiredMixin,View):
    '''购物车显示信息页'''
    def get(self, request):
        '''显示购物车信息'''
        # 获取登录的用户
        user = request.user
        # 获取用户购物车中商品的信息
        conn = get_redis_connection('default')
        # 根据用户的id拼接出购物车的键
        cart_key = 'cart_%d'%user.id
        # hgetall查询出所有的商品信息返回的是一个字典 {'商品id':商品的数量}
        cart_dict = conn.hgetall(cart_key)

        skus = []
        # 保存用户购物车中商品的总数目和价格
        total_count = 0
        total_price = 0
        # 遍历获取商品的信息
        for sku_id, count in cart_dict.items():
            # 根据商品的id获取商品的信息
            sku = GoodsSKU.objects.get(id=sku_id)
            # 计算商品的小计
            amount = sku.price * int(count)
            # 动态给sku对象增加一个属性的amount,保存商品的小计(这里又用到动态给对象增加属性)
            sku.amount = amount
            # 动态给sku对象增加一个属性的count,保存购物车中的对应的商品的数量
            sku.count = int(count)
            # 添加
            skus.append(sku)

            # 累加计算商品的总数目和价格
            total_count += int(count)
            total_price += amount

        # 组织上下文
        context = {'total_count':total_count,
                   'total_price':total_price,
                   'skus':skus}

        return  render(request, 'cart.html', context)














