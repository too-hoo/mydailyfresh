from django.urls import path
from apps.cart.views import CartAddView, CartInfoView
urlpatterns = [
    path('add/', CartAddView.as_view(), name = 'add'), # 购物车记录添加
    path('', CartInfoView.as_view(), name = 'show'), # 购物差信息显示也页
]
