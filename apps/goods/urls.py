from django.urls import path, re_path
from apps.goods.views import indexView, DetailView


urlpatterns = [
    # 加上index的时候只是为了在部署的时候加以区分
    path('',indexView.as_view(), name='index'),  # 显示首页
    re_path(r'^goods/(?P<goods_id>\d+)$', DetailView.as_view(), name='detail'), # 详情页面,获取id,数字,一个或者多个
]
