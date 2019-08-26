from django.urls import path
from apps.order.views import OrderPlaceView, OrderCommitView

urlpatterns = [
    path('place/', OrderPlaceView.as_view(), name='place'), # 提交订单页面显示
    path('commit/', OrderCommitView.as_view(), name='commit'), # 订单创建
]
