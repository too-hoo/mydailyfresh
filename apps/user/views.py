from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.urls import reverse  # 想让Django帮我们反向解析地址,引入反向解析函数
from django.views.generic import View  # 使用类视图处理地址请求
from django.conf import settings
from django.http import HttpResponse  # 返回响应
from django.contrib.auth import authenticate, login, logout  # 内置的验证登录登出函数模块

from apps.user.models import User
from celery_tasks.tasks import send_register_active_email
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired  # 口令过期异常

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
        return render(request, "login.html")

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

                # 跳转到首页
                return redirect(reverse('goods:index'))
            else:
                # print("The passwoed is valid, but the account has been disabled!")
                return render(request, 'login.html', {'errmsg': '账户未激活'})
        else:
            return render(request, 'login.html', {'errmsg': '用户名或密码错误或者账户未激活'})
