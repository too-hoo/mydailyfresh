# -*-coding:utf-8-*-
from django.db import models
from django.contrib.auth.models import AbstractUser  # 继承封装好的抽象用户类
from db.base_model import BaseModel


class User(AbstractUser, BaseModel):  # 继承抽像用户类和自定义的三个基础的字段类模型
    """用户模型类"""

    class Meta:
        db_table = 'df_user'
        verbose_name = '用户'
        verbose_name_plural = verbose_name


class AddressManager(models.Manager):
    """地址模型管理器类"""

    # 1. 改变原有查询的结果集:all()
    # 2. 封装方法:用户操作模型类对应的数据表(增删查改)

    def get_default_address(self, user):
        # 获取用户的默认收货地址
        try:
            address = self.get(user=user, is_default=True)
        except self.model.DoesNotExist:
            address = None  # 不存在默认地址

        return address


class Address(BaseModel):
    """地址模型类"""
    user = models.ForeignKey('User', on_delete=models.CASCADE, verbose_name='所属用户')
    receiver = models.CharField(max_length=20, verbose_name='收件人')
    addr = models.CharField(max_length=256, verbose_name='收件地址')
    zip_code = models.CharField(max_length=6, null=True, verbose_name='邮政编码')
    phone = models.CharField(max_length=11, verbose_name='联系电话')
    is_default = models.BooleanField(default=False, verbose_name='是否默认')

    # 自定义一个模型管理器类
    objects = AddressManager()

    # 元类中定义表格名称
    # Django模型中的verbose_name我们常常可能需要使用。比如将数据库里面的数据导出成csv文件，那么csv文件的表头的名字可以通过取每个字段的verbose_name来获取，数据可以通过queryset语句来获取。
    # 这样制作出来的csv表就能想数据库一样，字段名和字段值一一对应了。
    class Meta:
        db_table = 'df_address'
        verbose_name = '地址'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.user.username
