from django.urls import path
from apps.goods import views

urlpatterns = [
    path('', views.index, name='index'),  # 显示首页
]
