from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.urls import reverse  # 想让Django帮我们反向解析地址,引入反向解析函数
from django.views.generic import View  # 使用类视图处理地址请求
from django.conf import settings
from django.http import HttpResponse  # 返回响应
from django.contrib.auth import authenticate, login, logout  # 内置的验证登录登出函数模块

from apps.user.models import User, Address
from apps.goods.models import GoodsSKU  # 具体的商品
from celery_tasks.tasks import send_register_active_email
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired  # 口令过期异常
from django_redis import get_redis_connection

from utils.mixin import LoginRequiredMixin

import re


# Create your views here.

# user/register
# 显示注册页面和注册处理为同一个url地址
def register(request):
    '''显示注册页面'''
    # GET请求就是显示注册页面,POST请求就是处理注册业务
    if request.method == 'GET':
        return render(request, 'register.html')
    else:
        # 处理注册的业务
        # 接收数据
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')
        print(username, password, email, allow)

        # 使用all校验数据是否完整,里面保存的是一个可迭代的列表
        if not all([username, password, email]):
            # 数据教研
            return render(request, 'register.html', {'errmsg': '数据不完整'})

        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '邮箱格式不正确'})

        # 校验协议是否同意
        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '请同意协议'})

        # 校验用户是否重复
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # 用户名不存在
            user = None

        if user:
            return render(request, 'register.html', {'errmsg': '用户已存在'})

        # 进行业务处理
        user = User.objects.create_user(username, email, password)
        user.is_active = 0
        user.save()

        # 返回相应,跳转到首页
        # reverse(对应url对应的apps,里面的name对应的值)
        return redirect(reverse('goods:index'))


# user/register_handle/
def register_handle(request):
    '''注册处理页面'''
    # 进行注册处理
    # 接收数据
    username = request.POST.get('user_name')
    password = request.POST.get('pwd')
    email = request.POST.get('email')
    allow = request.POST.get('allow')
    print(username, password, email, allow)

    # 使用all校验数据是否完整,里面保存的是一个可迭代的列表
    if not all([username, password, email]):
        # 数据教研
        return render(request, 'register.html', {'errmsg': '数据不完整'})

    if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
        return render(request, 'register.html', {'errmsg': '邮箱格式不正确'})

    # 校验协议是否同意
    if allow != 'on':
        return render(request, 'register.html', {'errmsg': '请同意协议'})

    # 校验用户是否重复
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        # 用户名不存在
        user = None

    if user:
        return render(request, 'register.html', {'errmsg': '用户已存在'})

    # 进行业务处理
    user = User.objects.create_user(username, email, password)
    user.is_active = 0
    user.save()

    # 返回相应,跳转到首页
    # reverse(对应url对应的apps,里面的name对应的值)
    return redirect(reverse('goods:index'))


# 使用地址处理函数的时候就使用类视图,明确什么样的请求方式对应什么样的处理方法
class RegisterView(View):
    '''注册'''

    def get(self, request):
        '''显示注册页面'''
        return render(request, 'register.html')

    def post(self, request):
        '''进行注册处理'''
        # 接收数据
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')
        print(username, password, email, allow)

        # 使用all校验数据是否完整,里面保存的是一个可迭代的列表
        if not all([username, password, email]):
            # 数据教研
            return render(request, 'register.html', {'errmsg': '数据不完整'})

        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '邮箱格式不正确'})

        # 校验协议是否同意
        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '请同意协议'})

        # 校验用户是否重复
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # 用户名不存在
            user = None

        if user:
            return render(request, 'register.html', {'errmsg': '用户已存在'})

        # 进行业务处理
        user = User.objects.create_user(username, email, password)
        user.is_active = 0
        user.save()

        # 发送激活链接,包含激活链接为:http://127.0.0.1:8000/user/active/5
        # 激活链接中需要包含用户的身份信息，并要把身份信息进行加密
        # 激活链接格式: /user/active/用户身份加密后的信息 /user/active/token

        # 加密用户的身份信息,生成激活的token
        serializer = Serializer(settings.SECRET_KEY, 3600)
        info = {'confirm': user.id}
        token = serializer.dumps(info)  # bytes类型的数据,需要加密成为utf8,这样就不会在激活链接里面出现b''.
        token = token.decode('utf8')  # 解码, str

        # 发邮箱
        # subject = '天天生鲜欢迎信息'
        # message = ''  # 发件内容,入股欧内容中包含HTML的应该使用html_message来传输
        # sender = settings.EMAIL_PROM  # 发送人
        # receiver = [email] # 邮箱接收地址
        # html_message = '<h1>%s, 欢迎您成为天天生鲜注册会员' \
        #                '</h1>请点击下面链接激活您的账户<br/>' \
        #                '<a href="http://127.0.0.1:8000/user/active/%s">' \
        #                'http://127.0.0.1:8000/user/active/%s' \
        #                '</a>' % (username, token, token)
        #
        # # 前面的4个参数是按照顺序传递的,不能直接传入html_message,要设置一个参数来接收
        # send_mail(subject, message, sender, receiver, html_message=html_message)

        # 使用Celery帮助发邮件
        send_register_active_email.delay(email, username, token)

        # 返回相应,跳转到首页
        # reverse(对应url对应的apps,里面的name对应的值)
        return redirect(reverse('goods:index'))


class ActiveView(View):
    '''用户邮箱激活'''

    def get(self, request, token):
        # 进行用户激活
        # 进行解密,获取需要激活的用户信息
        serializer = Serializer(settings.SECRET_KEY, 3600)
        try:
            info = serializer.loads(token)
            # 获取待激活用户的id
            user_id = info['confirm']

            # 根据id获取用户信息
            user = User.objects.get(id=user_id)
            user.is_active = 1
            user.save()

            # 激活成功之后跳转到登录页面,配置好之后就进行反向解析
            return redirect(reverse('user:login'))
        except SignatureExpired as e:
            # 激活链接已过期
            return HttpResponse('激活链接已失效')


class LoginView(View):
    '''登录'''

    def get(self, request):
        '''显示登录页面'''
        # 判断是否记住密码
        if 'username' in request.COOKIES:
            username = request.COOKIES.get('username')  # request.COOKIES['username']
            checked = 'checked'
        else:
            username = ''
            checked = ''
        # 返回对应的值, 页面通过模板进行显示
        return render(request, "login.html", {'username': username, 'checked': checked})

    def post(self, request):
        '''登录校验'''
        # 接收数据
        username = request.POST.get('username')
        password = request.POST.get('pwd')

        # 数据校验
        if not all([username, password]):
            return render(request, 'login.html', {'errmsg': '数据不完整!'})
        print(username, password)

        # 业务处理:登录校验
        user = authenticate(username=username, password=password)
        print(user)
        if user is not None:
            if user.is_active:
                # print("User is valid, active and authenticated")
                login(request, user)  # 登录并记录用户的登录状态

                # 获取登陆之后所要跳转的地址,优化用户体验,在地址栏里面的是使用get方法进行请求的.
                # 默认是跳转到首页,如果有next参数就跳转到next对应的地址
                next_url = request.GET.get('next', reverse('goods:index'))

                # 跳转到next_url
                response = redirect(next_url)  # HttpResponseRedirect

                # 设置cookie,需要通过HttpResponse类的实例对象,set_cookie
                # HttpResponseRedirect JsonResponse

                # 判断是否需要记住用户名
                remember = request.POST.get('remember')
                if remember == 'on':
                    response.set_cookie('username', username, max_age=7 * 24 * 3600)
                else:
                    response.delete_cookie('username')

                # 跳转到首页
                return response
            else:
                # print("The passwoed is valid, but the account has been disabled!")
                return render(request, 'login.html', {'errmsg': '账户未激活'})
        else:
            return render(request, 'login.html', {'errmsg': '用户名或密码错误或者账户未激活'})


# /user/logout
class LogoutView(View):
    """退出登录"""

    def get(self, request):
        logout(request)
        # 使用django内部的认证系统的退出功能,返回首页
        return redirect(reverse('goods:index'))


# /user
# 继承LoginRequiredMixin,帮助验证登录才能访问的页面
class UserInfoView(LoginRequiredMixin, View):
    '''用户中心-信息页'''

    def get(self, request):
        '''显示'''
        # page = 'user'
        # request.user
        # 如果用户未登录->返回Anonymous类的一个实例
        # 如果用户登录->返回User类的一个实例
        # request.user.is_authenticated() 验证用户

        # 获取用户的个人信息
        user = request.user  # 直接从request中获取
        address = Address.objects.get_default_address(user)

        # 获取用户的历史浏览记录
        # 1.常规连接方法
        # from redis import StrictRedis
        # con = StrictRedis(host='127.0.0.1', port='6379', db=9)

        # 2.推荐方法,default的意思就是配置文件里面的数据库链接的键名
        con = get_redis_connection('default')

        # 用户浏览历史记录id
        history_key = 'history_%d' % user.id

        # 获取用户最新浏览的5个商品的id
        sku_ids = con.lrange(history_key, 0, 4)

        # 从数据库中查询用户浏览的商品的具体信息,双下划线表示在里面的意思
        # goods_li = GoodsSKU.objects.filter(id__in=sku_ids)
        #
        # # 注意这里的MySQL查询数据库的时候不是按照你给定顺序查询,而是从前向后遍历,是就拿出来
        # # 1.通过两重循环查询
        # goods_res = []
        # for a_id in sku_ids:
        #     for goods in goods_li:
        #         if a_id == goods.id:
        #             goods_res.append(goods)

        # 2.遍历获取用户浏览的商品信息, 取一个遍历一个,再添加到列表里面去
        goods_li = []
        for id in  sku_ids:
            goods = GoodsSKU.objects.get(id=id)
            goods_li.append(goods)

        # 组织上下文
        context = {'page': 'user',
                   'address': address,
                   'goods_li':goods_li}

        # 除了你给模板文件传递的模板变量之外,django框架会把request.user也传递给模板文件
        return render(request, 'user_center_info.html', context)


# /user/order
class UserOrderView(LoginRequiredMixin, View):
    '''用户中心-订单页'''

    def get(self, request):
        '''显示'''
        # 获取用户的订单信息

        return render(request, 'user_center_order.html', {'page': 'order'})


# /user/address
class AddressView(LoginRequiredMixin, View):
    '''用户中心-地址页'''

    def get(self, request):
        '''显示'''
        # 获取登录的用户对应的User对象
        user = request.user

        # 获取用户的默认收货地址
        # try:
        #     address = Address.objects.get(user=user, is_default=True)
        # except Address.DoesNotExist:
        #     # 不存在默认的收货地址
        #     address = None
        # 将上面的方法封装成为一个model中的AddressManager类,直接使用address调用即可
        address = Address.objects.get_default_address(user)

        # 使用模板
        return render(request, 'user_center_site.html', {'page': 'address', 'address': address})

    def post(self, request):
        '''地址的添加'''
        receiver = request.POST.get('receiver')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')

        # 业务处理:地址添加
        # 如果用户已经存在默认的收货地址,添加的地址不作为默认的收货地址,否则作为默认收货地址
        # 获取登录用户的User对象, 能够访问到post方法的都是已经登录了的用户的了,存在request.user
        user = request.user

        # model里面设置默认是False,所以这里查询出来的是True
        # try:
        #     address = Address.objects.get(user=user, is_default=True)
        # except Address.DoesNotExist:
        #     # 如果不存在默认的收货地址,设置为None
        #     address = None
        # 将上面的方法封装成为一个model中的AddressManager类,直接使用address调用即可
        address = Address.objects.get_default_address(user)

        if address:
            is_default = False
        else:
            is_default = True

        # 数据校验, 邮编可以是为空,不做数据校验,因为在model里面已经定义默认为空
        if not all([receiver, addr, phone]):
            return render(request, 'user_center_site.html',
                          {'page': 'address',
                           'address': address,
                           'errmsg': '数据不完整'})
        # 校验手机号
        if not re.match(r'^1([3-8][0-9]|5[189]|8[6789])[0-9]{8}$', phone):
            return render(request, 'user_center_site.html',
                          {'page': 'address',
                           'address': address,
                           'errmsg': '手机号格式不合法'})

        # 添加收货地址, 设置默认的收货地址,其实可以扩展一下功能的
        Address.objects.create(user=user,
                               receiver=receiver,
                               addr=addr,
                               zip_code=zip_code,
                               phone=phone,
                               is_default=is_default)
        # 反回应答,刷新地址页面
        return redirect(reverse('user:address'))  # get请求方法
