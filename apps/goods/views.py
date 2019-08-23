from django.shortcuts import render
from django.views.generic import View
from apps.goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner
from django_redis import get_redis_connection


# Create your views here.

# index : http://127.0.0.1:8000
class indexView(View):
    '''显示首页'''

    def get(self, request):
        '''显示首页'''
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

        # 获取用户购物车中商品的数目
        user = request.user
        # 初始值设置为0,如果购物车有商品就返回对应的商品,否则返回0
        cart_count = 0
        if user.is_authenticated:
            # 用户已经登录
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_count = conn.hlen(cart_key)

        # 组织模板上下文
        context = {'types': types,
                   'goods_banners': good_banners,
                   'promotion_banners': promotion_banners,
                   'cart_count': cart_count}

        # 使用模板
        return render(request, 'index.html', context)
