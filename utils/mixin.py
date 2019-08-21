#!/usr/bin/env python
# -*-encoding:UTF-8-*-

from django.contrib.auth.decorators import login_required


# 统一处理登录验证
class LoginRequiredMixin(object):
    @classmethod
    def as_view(cls, **initkwargs):
        # 调用父类的as_view
        view = super(LoginRequiredMixin, cls).as_view(**initkwargs)
        return login_required(view)
