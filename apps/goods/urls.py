from django.urls import path
from apps.goods.views import indexView


urlpatterns = [
    path('',indexView.as_view(), name='index'),  # 显示首页
]
