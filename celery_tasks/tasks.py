#!/usr/bin/env python
# -*-encoding:UTF-8-*-
from django.core.mail import send_mail
from django.conf import settings

from celery import Celery
import time

# django 环境的初始化,在任务处理者worker一端需要加上下面几句
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mydailyfresh.settings')
django.setup()

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
    time.sleep(5)
