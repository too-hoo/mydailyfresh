#!/usr/bin/env python
# -*-encoding:UTF-8-*-
from django.core.mail import send_mail
from django.conf import settings
from django.template import loader, RequestContext
from celery import Celery
import time

# django 环境的初始化,在任务处理者worker一端需要加上下面几句
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mydailyfresh.settings')
django.setup()
from apps.goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner

# 名字是可以任意指定的,但是一般取个有意义的名字, broker是中间人
app = Celery('celery_tasks.tasks', broker='redis://127.0.0.1:6379/8')


# 启动任务处理者:celery -A celery_tasks.tasks worker -l info
# 定义任务函数,并开启任务
@app.task
def send_register_active_email(to_email, username, token):
    '''发送激活邮件'''
    # 组织邮件信息
    subject = '天天生鲜欢迎信息'
    message = ''  # 发件内容,入股欧内容中包含HTML的应该使用html_message来传输
    sender = settings.EMAIL_PROM  # 发送人
    receiver = [to_email]  # 邮箱接收地址
    html_message = '<h1>%s, 欢迎您成为天天生鲜注册会员' \
                   '</h1>请点击下面链接激活您的账户<br/>' \
                   '<a href="http://127.0.0.1:8000/user/active/%s">' \
                   'http://127.0.0.1:8000/user/active/%s' \
                   '</a>' % (username, token, token)

    # 前面的4个参数是按照顺序传递的,不能直接传入html_message,要设置一个参数来接收
    send_mail(subject, message, sender, receiver, html_message=html_message)
    # time.sleep(5)


@app.task
def generate_static_index_html():
    '''产生首页静态页面'''
    # 获取商品的种类信息
    types = GoodsType.objects.all()

    # 获取首页轮播商品信息
    good_banners = IndexGoodsBanner.objects.all().order_by('index')

    # 获取首页促销活动信息
    promotion_banners = IndexPromotionBanner.objects.all().order_by('index')

    # 获取首页分类商品展示信息
    # 不能简单的将所有的信息都查询出来:type_good_banners = IndexTypeGoodsBanner.objects.all()
    # 要分开查询
    for type in types:
        # 获取type种类首页分类的商品的图片展示信息
        image_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1).order_by('index')
        # 获取type种类首页分类商品的文字展示信息
        title_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by('index')

        # 动态给type增加属性, 分别保存首页分类商品的图片展示信息和文字展示信息
        type.image_banners = image_banners
        type.title_banners = title_banners

    # 组织模板上下文
    context = {'types': types,
               'goods_banners': good_banners,
               'promotion_banners': promotion_banners}

    # 使用模板(原始)
    # 1.加载模板文件,返回模板对象
    temp = loader.get_template('static_index.html')
    # 2.定义模板上下文 这步可以直接不写
    # context = RequestContext(request, context)
    # 3.模板渲染
    static_index_html = temp.render(context)
    # print(static_index_html)

    # 生成首页对应的静态文件
    save_path = os.path.join(settings.BASE_DIR, 'static/index.html')
    # print(save_path)
    with open(save_path, 'w') as f:
        f.write(static_index_html)
