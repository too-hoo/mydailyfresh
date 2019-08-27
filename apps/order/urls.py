from django.urls import path
from apps.order.views import OrderPlaceView, OrderCommitView, OrderPayView, CheckPayView

urlpatterns = [
    path('place/', OrderPlaceView.as_view(), name='place'), # 提交订单页面显示
    path('commit/', OrderCommitView.as_view(), name='commit'), # 订单创建
    path('pay/', OrderPayView.as_view(), name='pay'), # 订单创建
    path('check/', CheckPayView.as_view(), name='check' ), # 查询支付交易的结果
]
