from django.urls import path
from apps.cart.views import CartAddView, CartInfoView, CartUpdateView, CartDeleteView
urlpatterns = [
    path('add/', CartAddView.as_view(), name = 'add'), # 购物车记录添加
    path('', CartInfoView.as_view(), name = 'show'), # 购物车信息显示也页
    path('update/', CartUpdateView.as_view(), name='update'), # 购物车记录更新
    path('delete/', CartDeleteView.as_view(), name='delete'), # 购物车数据删除
]
