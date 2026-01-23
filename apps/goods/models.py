from uuid import uuid4

from django.db import models
from django.utils import timezone


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
    
    # 作品类型：1=书籍, 2=动画, 3=音乐, 4=游戏, 6=三次元/特摄
    SUBJECT_TYPE_CHOICES = (
        (1, "书籍"),
        (2, "动画"),
        (3, "音乐"),
        (4, "游戏"),
        (6, "三次元/特摄"),
    )
    subject_type = models.IntegerField(
        choices=SUBJECT_TYPE_CHOICES,
        null=True,
        blank=True,
        verbose_name="作品类型",
        help_text="1=书籍, 2=动画, 3=音乐, 4=游戏, 6=三次元/特摄",
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,
        blank=True,
        verbose_name="创建时间",
    )

    class Meta:
        verbose_name = "IP作品"
        verbose_name_plural = "IP作品"
        ordering = ["created_at"]

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
    avatar = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="角色头像",
        help_text="角色头像路径或URL。可以是服务器内的相对路径（如 characters/xxx.jpg）或外部URL（如 https://example.com/avatar.jpg）",
    )
    
    GENDER_CHOICES = (
        ("male", "男"),
        ("female", "女"),
        ("other", "其他"),
    )
    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        default="other",
        verbose_name="角色性别",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,
        blank=True,
        verbose_name="创建时间",
    )

    class Meta:
        verbose_name = "角色"
        verbose_name_plural = "角色"
        unique_together = ("ip", "name")
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.ip.name} - {self.name}"


class Category(models.Model):
    """
    品类表，例如：吧唧、色纸、立牌、挂件
    采用自关联设计，支持无限级层级。
    """

    name = models.CharField(max_length=50, verbose_name="类型名")
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="父级品类",
    )
    path_name = models.CharField(
        max_length=200,
        db_index=True,
        null=True,
        blank=True,
        verbose_name="完整路径",
        help_text="冗余字段，例如：周边/吧唧/圆形吧唧",
    )
    color_tag = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="颜色标签",
        help_text="用于UI展示的颜色标识，例如：#FF5733",
    )
    order = models.IntegerField(
        default=0,
        verbose_name="排序值",
        help_text="控制同级节点的展示顺序，值越小越靠前",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,
        blank=True,
        verbose_name="创建时间",
    )

    class Meta:
        verbose_name = "品类"
        verbose_name_plural = "品类"
        ordering = ["order", "id"]

    def __str__(self):
        return self.path_name or self.name


class Theme(models.Model):
    """
    主题表，例如：夏日主题、节日主题、限定主题等
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name="主题名称",
    )
    description = models.TextField(
        null=True,
        blank=True,
        verbose_name="主题描述",
        help_text="主题的详细描述信息",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,
        blank=True,
        verbose_name="创建时间",
    )

    class Meta:
        verbose_name = "主题"
        verbose_name_plural = "主题"
        ordering = ["created_at"]

    def __str__(self):
        return self.name


class Goods(models.Model):
    """
    谷子核心表，关联 IP / 角色 / 品类 / 主题 以及 物理位置 StorageNode。
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
    theme = models.ForeignKey(
        Theme,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="goods",
        verbose_name="主题",
        help_text="谷子所属主题，例如：夏日主题、节日主题等",
    )
    characters = models.ManyToManyField(
        Character,
        related_name="goods",
        verbose_name="角色",
        help_text="可关联多个角色，例如双人立牌可以关联流萤和花火",
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

    # 自定义排序字段：值越小越靠前，默认0
    order = models.BigIntegerField(
        default=0,
        db_index=True,
        verbose_name="自定义排序值",
        help_text="值越小越靠前，默认0",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "谷子"
        verbose_name_plural = "谷子"
        # 默认排序：先按自定义顺序值从小到大，其次按创建时间倒序（保证新建未手动排序的谷子有稳定顺序）
        ordering = ["order", "-created_at"]

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
