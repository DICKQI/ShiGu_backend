from uuid import uuid4

from django.db import models


class IP(models.Model):
    """
    作品来源表，例如：崩坏：星穹铁道
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name="作品名",
    )

    class Meta:
        verbose_name = "IP作品"
        verbose_name_plural = "IP作品"

    def __str__(self):
        return self.name


class IPKeyword(models.Model):
    """
    IP 多关键词 / 别名表，例如：星铁、崩铁、HSR 等。
    """

    ip = models.ForeignKey(
        IP,
        on_delete=models.CASCADE,
        related_name="keywords",
        verbose_name="所属作品",
    )
    value = models.CharField(
        max_length=50,
        db_index=True,
        verbose_name="关键词",
        help_text="IP 的别名或搜索关键字，例如：星铁、崩铁、HSR",
    )

    class Meta:
        verbose_name = "IP关键词"
        verbose_name_plural = "IP关键词"
        unique_together = ("ip", "value")

    def __str__(self):
        return f"{self.ip.name} - {self.value}"


class Character(models.Model):
    """
    角色表，例如：流萤
    """

    ip = models.ForeignKey(
        IP,
        on_delete=models.CASCADE,
        related_name="characters",
        verbose_name="所属作品",
    )
    name = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name="角色名",
    )
    avatar = models.ImageField(
        upload_to="characters/",
        null=True,
        blank=True,
        verbose_name="角色头像",
    )

    class Meta:
        verbose_name = "角色"
        verbose_name_plural = "角色"
        unique_together = ("ip", "name")

    def __str__(self):
        return f"{self.ip.name} - {self.name}"


class Category(models.Model):
    """
    品类表，例如：吧唧、色纸、立牌、挂件
    """

    name = models.CharField(max_length=50, unique=True, verbose_name="类型名")

    class Meta:
        verbose_name = "品类"
        verbose_name_plural = "品类"

    def __str__(self):
        return self.name


class Goods(models.Model):
    """
    谷子核心表，关联 IP / 角色 / 品类 以及 物理位置 StorageNode。
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid4,
        editable=False,
        verbose_name="资产ID",
    )

    name = models.CharField(
        max_length=200,
        db_index=True,
        verbose_name="谷子名称",
    )

    # 多维关联
    ip = models.ForeignKey(
        IP,
        on_delete=models.PROTECT,
        related_name="goods",
        verbose_name="IP作品",
    )
    character = models.ForeignKey(
        Character,
        on_delete=models.PROTECT,
        related_name="goods",
        verbose_name="角色",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="goods",
        verbose_name="品类",
    )
    location = models.ForeignKey(
        "location.StorageNode",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="goods",
        verbose_name="物理位置",
    )

    # 资产细节
    main_photo = models.ImageField(
        upload_to="goods/main/",
        null=True,
        blank=True,
        verbose_name="主图",
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name="数量")
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="购入单价",
    )
    purchase_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="入手时间",
    )
    is_official = models.BooleanField(
        default=True,
        verbose_name="是否官谷",
    )

    STATUS_CHOICES = (
        ("in_cabinet", "在馆"),
        ("outdoor", "出街中"),
        ("sold", "已售出"),
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="in_cabinet",
        verbose_name="状态",
    )

    notes = models.TextField(
        null=True,
        blank=True,
        verbose_name="备注",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "谷子"
        verbose_name_plural = "谷子"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class GuziImage(models.Model):
    """
    谷子补充图片表，例如背板细节、瑕疵点等。
    """

    guzi = models.ForeignKey(
        Goods,
        on_delete=models.CASCADE,
        related_name="additional_photos",
        verbose_name="关联谷子",
    )
    image = models.ImageField(
        upload_to="goods/extra/",
        verbose_name="补充图片",
    )
    label = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="图片标签",
        help_text="如：背板细节、瑕疵点",
    )

    class Meta:
        verbose_name = "谷子补充图片"
        verbose_name_plural = "谷子补充图片"

    def __str__(self):
        return f"{self.guzi.name} - {self.label or '补充图'}"
