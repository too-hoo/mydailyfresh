from django.contrib import admin
from apps.goods.models import GoodsType, IndexPromotionBanner


# Register your models here.

# class IndexPromotionBannerAdmin(admin.ModelAdmin):
#     def save_model(self, request, obj, form, change):
#         '''新增或者更新表中的数据的时候调用'''
#         super().save_model(request, obj, form, change)
#         # 发出任务,让celery worker重新生成首页静态页面
#         from celery_tasks.tasks import generate_static_index_html
#         generate_static_index_html.delay()
#
#     def delete_model(self, request, obj):
#         '''删除表中的数据的时候调用'''
#         super().delete_model(request, obj)
#         # 发出任务,让celery worker重新生成首页静态页面
#         from celery_tasks.tasks import generate_static_index_html
#         generate_static_index_html.delay()

class IndexPromotionBannerAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        """新增或更新表中的数据时调用"""
        super().save_model(request, obj, form, change)

        # 发出任务，让celery worker 重新生成首页静态页
        # 为何在顶部导入不可以，执行celery会出错
        from celery_tasks.tasks import generate_static_index_html
        generate_static_index_html.delay()

    def delete_model(self, request, obj):
        """删除表中的数据时调用"""
        super().delete_model(request, obj)
        # 发出任务，让celery worker 重新生成首页静态页
        from celery_tasks.tasks import generate_static_index_html
        generate_static_index_html.delay()


admin.site.register(GoodsType)
admin.site.register(IndexPromotionBanner, IndexPromotionBannerAdmin)
