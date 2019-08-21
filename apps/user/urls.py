from django.urls import path, re_path
from apps.user.views import RegisterView, ActiveView, LoginView, LogoutView, UserInfoView, UserOrderView, AddressView
from django.contrib.auth.decorators import login_required

urlpatterns = [
    # path('register/', views.register, name='register'), # 注册
    # path('register_handle/', views.register_handle, name='register_handle'), # 注册处理

    path('register/', RegisterView.as_view(), name='register'),  # 注册
    re_path(r'^active/(?P<token>.*)$', ActiveView.as_view(), name='active'),  # 用户邮箱激活,token是取到口令的名字
    path('login/', LoginView.as_view(), name='login'),  # 登录
    path('logout/', LogoutView.as_view(), name='logout'), # 注销登录

    # 使用登录验证login_required来限制用户访问的页面,在settings里面设置需要跳转的地址
    # path('', login_required(UserInfoView.as_view()), name='user'), # 用户中心-信息页
    # path('order/', login_required(UserOrderView.as_view()), name='order'), # 用户中心-订单页
    # path('address', login_required(AddressView.as_view()), name='address'), # 用户中心-地址页

    # 统一加上一层包装
    path('', UserInfoView.as_view(), name='user'), # 用户中心-信息页
    path('order/', UserOrderView.as_view(), name='order'), # 用户中心-订单页
    path('address', AddressView.as_view(), name='address'), # 用户中心-地址页

]















