from django.contrib import admin
from django.core.cache import cache
from apps.goods.models import GoodsType, IndexGoodsBanner, IndexTypeGoodsBanner, IndexPromotionBanner, Goods, GoodsSKU


# Register your models here.

class BaseModelAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        '''新增或者更新表中的数据的时候调用'''
        super().save_model(request, obj, form, change)
        # 发出任务,让celery worker重新生成首页静态页面
        from celery_tasks.tasks import generate_static_index_html
        generate_static_index_html.delay()

        # 清除首页的缓存数据, 用户重新加载之后就又回来了
        cache.delete('index_page_data')

    def delete_model(self, request, obj):
        '''删除表中的数据的时候调用'''
        super().delete_model(request, obj)
        # 发出任务,让celery worker重新生成首页静态页面
        from celery_tasks.tasks import generate_static_index_html
        generate_static_index_html.delay()

        # 清除首页的缓存数据, 用户重新加载之后就又回来了
        cache.delete('index_page_data')


class GoodsTypeAdmin(BaseModelAdmin):
    pass


class IndexGoodsBannerAdmin(BaseModelAdmin):
    pass


class IndexTypeGoodsBannerAdmin(BaseModelAdmin):
    pass


class IndexPromotionBannerAdmin(BaseModelAdmin):
    pass


class GoodsSPUAdmin(BaseModelAdmin):
    pass


class GoodsSKUAdmin(BaseModelAdmin):
    pass


admin.site.register(GoodsType, GoodsTypeAdmin)  # 商品类型模型类
admin.site.register(IndexGoodsBanner, IndexGoodsBannerAdmin)  # 首页轮播商品展示模型类
admin.site.register(IndexTypeGoodsBanner, IndexTypeGoodsBannerAdmin)  # 首页分类商品展示模型类
admin.site.register(IndexPromotionBanner, IndexPromotionBannerAdmin)  # 首页促销活动模型类
admin.site.register(Goods, GoodsSPUAdmin)
admin.site.register(GoodsSKU, GoodsSKUAdmin)
