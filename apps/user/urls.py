from django.urls import path, re_path
from apps.user.views import RegisterView, ActiveView, LoginView

urlpatterns = [
    # path('register/', views.register, name='register'), # 注册
    # path('register_handle/', views.register_handle, name='register_handle'), # 注册处理

    path('register/', RegisterView.as_view(), name='register'),  # 注册
    re_path(r'^active/(?P<token>.*)$', ActiveView.as_view(), name='active'),  # 用户邮箱激活,token是取到口令的名字
    path('login/', LoginView.as_view(), name='login'),  # 登录
]
