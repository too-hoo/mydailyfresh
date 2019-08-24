from django.shortcuts import render
from django.views.generic import View
from django.core.cache import cache
from apps.goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner
from django_redis import get_redis_connection


# Create your views here.

# index : http://127.0.0.1:8000
class indexView(View):
    '''显示首页'''

    def get(self, request):
        '''显示首页'''
        # 先判断缓存中是否有数据,没有数据不会报错,只返回None
        context = cache.get('index_page_data')

        if context is None:
            print('设置缓存') # 测试是否成功缓存到redis里面,重复两次访问首页,原理是将对象的内容设置成为字符串缓存到数据库里面
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
