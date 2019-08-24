from django.urls import path
from apps.goods.views import indexView


urlpatterns = [
    # 加上index的时候只是为了在部署的时候加以区分
    path('index/',indexView.as_view(), name='index'),  # 显示首页
]
