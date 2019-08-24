from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.generic import View
from django.core.cache import cache
from django.core.paginator import Paginator  # Django里面的分页模块
from apps.goods.models import GoodsType, GoodsSKU, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner
from django_redis import get_redis_connection
from apps.order.models import OrderGoods


# Create your views here.

# index : http://127.0.0.1:8000
class indexView(View):
    '''显示首页'''

    def get(self, request):
        '''显示首页'''
        # 先判断缓存中是否有数据,没有数据不会报错,只返回None
        context = cache.get('index_page_data')

        if context is None:
            print('设置缓存')  # 测试是否成功缓存到redis里面,重复两次访问首页,原理是将对象的内容设置成为字符串缓存到数据库里面
            # 获取商品的种类信息
            types = GoodsType.objects.all()

            # 获取首页轮播商品信息
            good_banners = IndexGoodsBanner.objects.all().order_by('index')

            # 获取首页促销活动信息
            promotion_banners = IndexPromotionBanner.objects.all().order_by('index')

            # 获取首页分类商品展示信息
            # 不能简单的将所有的信息都查询出来:type_good_banners = IndexTypeGoodsBanner.objects.all()
            # 要分开查询
            for type in types:
                # 获取type种类首页分类的商品的图片展示信息
                image_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1).order_by('index')
                # 获取type种类首页分类商品的文字展示信息
                title_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by('index')

                # 动态给type增加属性, 分别保存首页分类商品的图片展示信息和文字展示信息
                type.image_banners = image_banners
                type.title_banners = title_banners

            # 组织上下文
            context = {
                'types': types,
                'index_banner': good_banners,
                'promotion_banner': promotion_banners,
            }

            # 设置缓存数据,缓存的名字,内容和过期时间,设置缓存的过期时间是为了配合开发
            cache.set('index_page_data', context, 3600)

        # 获取用户购物车中商品的数目
        user = request.user
        # 初始值设置为0,如果购物车有商品就返回对应的商品,否则返回0
        cart_count = 0
        if user.is_authenticated:
            # 用户已经登录
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id

            # 获取用户购物车中的商品条目数
            cart_count = conn.hlen(cart_key)  # hlen hash中的条目

            # 最终还是一个字典,需要更新一下上下文的字典
            context.update(cart_count=cart_count)

        # 使用模板
        return render(request, 'index.html', context)


# /goods/商品id
class DetailView(View):
    '''详情页面'''

    def get(self, request, goods_id):
        '''显示详情页面'''
        try:
            # sku是一个具体的商品
            sku = GoodsSKU.objects.get(id=goods_id)
        except GoodsSKU.DoesNotExist:
            # 商品不存在,就返回首页
            return redirect(reverse('goods:index'))

        # 获取商品的分类信息
        types = GoodsType.objects.all()

        # 获取商品的评论信息, exclude除去评论为空的信息
        sku_orders = OrderGoods.objects.filter(sku=sku).exclude(comment='')

        # 获取新品的信息,切片显示连个新品
        new_skus = GoodsSKU.objects.filter(type=sku.type).order_by('-create_time')[:2]

        # 获取同一个SPU的其他规格商品, 查询出来的商品的sku应该个上面的sku是一样的,但是又不能是其本身,所以做一个排除
        same_spu_skus = GoodsSKU.objects.filter(goods=sku.goods).exclude(id=goods_id)

        # 获取用户购物车中商品的数目
        user = request.user
        # 初始值设置为0,如果购物车有商品就返回对应的商品,否则返回0
        cart_count = 0
        if user.is_authenticated:
            # 用户已经登录
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            # 获取用户购物车中的商品条目数
            cart_count = conn.hlen(cart_key)  # hlen hash中的条目

            # 添加用户的历史记录, 记录保存到列表里面去
            conn = get_redis_connection('default')
            history_key = 'history_%d' % user.id
            # 移除列表中的goods_id, 0表示移除所有相等的值
            conn.lrem(history_key, 0, goods_id)
            # 把goods_id 插入到列表的左侧
            conn.lpush(history_key, goods_id)
            # 只保存用户的最新的浏览的5条信息
            conn.ltrim(history_key, 0, 4)

        # 组织模板上下文
        context = {'sku': sku, 'types': types,
                   'sku_orders': sku_orders,
                   'new_skus': new_skus,
                   'same_spu_skus': same_spu_skus,
                   'cart_count': cart_count}

        return render(request, 'detail.html', context)


# 种类id & 页码 & 排序的方式
# restful api -> 请求一种资源
# /list?type_id=种类id&page=页码&sort=排序方式
# /list/种类id/页码/排序方式

# /list/种类id/页码?sort=排序方式  <--
class ListView(View):
    '''列表页'''

    def get(self, request, type_id, page):
        '''显示列表页'''
        # 对type_id进行校验
        try:
            type = GoodsType.objects.get(id=type_id)
        except GoodsType.DoesNotExist:
            # 种类不存在
            return redirect(reverse('goods:index'))

        # 获取商品的分类信息
        types = GoodsType.objects.all()

        # 获取排序方式 获取分类商品的信息
        # sort=default, 按照默认的id排序;sort=price,按照价格; sort=hot, 按照销量;
        sort = request.GET.get('sort')

        if sort == 'price':
            skus = GoodsSKU.objects.filter(type=type).order_by('price')
        elif sort == 'hot':
            skus = GoodsSKU.objects.filter(type=type).order_by('-sales')
        else:
            # 最后要赋值为Default,否则sort=None
            sort = 'default'
            skus = GoodsSKU.objects.filter(type=type).order_by('-id')

        # 对数据进行分页处理,这里设置每页显示几条数据,例如每页显示2条
        paginator = Paginator(skus, 1)

        try:
            page = int(page)
        except Exception as e:
            page = 1
        # 使用paginator 内置的模块总页数来限定查询的页数
        if page > paginator.num_pages or page <= 0:
            page = 1

        # 获取第page页的Page实例对象
        skus_page = paginator.page(page)

        # TODO:进行页码的控制.每页最多显示5个页码
        # 1.总页数小于5页,页面上显示所有的页码
        # 2.如果当前页是前3页,显示1-5页
        # 3.如果当前页是后3页,显示后五页
        # 4.其他情况,显示当前页的前两页,当前页,当前页的后五页
        num_pages = paginator.num_pages
        if num_pages < 5:
            pages = range(1, num_pages + 1)
        elif page <= 3:
            pages = range(1, 6)
        elif num_pages - page <= 2: # 10 9 8 相差2, 后-前 得到相差页数
            pages = range(num_pages - 4, num_pages + 1)
        else:
            pages = range(page - 2, page + 3)

        # 获取新品信息
        new_skus = GoodsSKU.objects.filter(type=type).order_by('-create_time')

        # 获取登录用户的额购物车中的商品的数量
        user = request.user
        cart_count = 0
        if user.is_authenticated:
            # 用户已经登录
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id

            # 获取用户购物车中的商品条目数
            cart_count = conn.hlen(cart_key)  # hlen hash中的数目

        # 组织模板上下文
        context = {'type': type, 'types': types,
                   'sort': sort,
                   'skus_page': skus_page,
                   'new_skus': new_skus,
                   'pages': pages,
                   'cart_count': cart_count}
        # 使用模板
        return render(request, 'list.html', context)
