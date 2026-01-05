from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.throttling import ScopedRateThrottle

from .models import Category, Character, Goods, IP
from .serializers import (
    CategorySimpleSerializer,
    CharacterSimpleSerializer,
    GoodsDetailSerializer,
    GoodsListSerializer,
    IPSimpleSerializer,
)


class GoodsViewSet(viewsets.ModelViewSet):
    """
    谷子检索核心接口。

    - list: 高性能检索列表（瘦身字段），支持多维过滤 & 搜索。
    - retrieve: 详情接口，返回完整信息及补充图片。
    """

    queryset = (
        Goods.objects.all()
        .select_related("ip", "character__ip", "category", "location")
        .prefetch_related("additional_photos")
    )

    # 列表接口瘦身：只返回必要字段；详情接口使用完整序列化器
    def get_serializer_class(self):
        if self.action == "list":
            return GoodsListSerializer
        return GoodsDetailSerializer

    # 过滤 & 搜索
    filter_backends = (
        DjangoFilterBackend,
        filters.SearchFilter,
    )

    # 复合过滤：/api/goods/?ip=1&character=5&category=2&status=in_cabinet
    filterset_fields = {
        "ip": ["exact"],
        "character": ["exact"],
        "category": ["exact"],
        "status": ["exact"],
        "location": ["exact"],
    }

    # 轻量搜索：
    # - 对 Goods.name 走索引（已在模型上 db_index=True）
    # - 同时支持按 IP 名称 / 多关键词(IPKeyword) 搜索
    search_fields = (
        "name",
        "ip__name",
        "ip__keywords__value",
    )

    # 限流：专门给检索接口一个 scope，具体速率在 settings.REST_FRAMEWORK.THROTTLE_RATES 中配置
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "goods_search"

    def get_queryset(self):
        """
        使用 select_related / prefetch_related 彻底解决 N+1 查询问题。
        """

        qs = (
            Goods.objects.all()
            .select_related("ip", "character__ip", "category", "location")
            .prefetch_related("additional_photos")
        )
        return qs

    def perform_create(self, serializer):
        """
        简单幂等性：避免重复录入完全相同的谷子。

        规则示例（可按业务后续调整）：
        - 同一 IP + 角色 + 名称 + 入手日期 + 单价 认为是同一条资产。
        """

        validated = serializer.validated_data
        ip = validated.get("ip")
        character = validated.get("character")
        name = validated.get("name")
        purchase_date = validated.get("purchase_date")
        price = validated.get("price")

        exists = Goods.objects.filter(
            ip=ip,
            character=character,
            name=name,
            purchase_date=purchase_date,
            price=price,
        ).exists()

        if exists:
            # 如果已经存在，则直接返回原有实例（保证幂等）
            instance = Goods.objects.get(
                ip=ip,
                character=character,
                name=name,
                purchase_date=purchase_date,
                price=price,
            )
            serializer.instance = instance
            return

        serializer.save()


class IPViewSet(viewsets.ModelViewSet):
    """
    IP作品CRUD接口。

    - list: 获取所有IP作品列表
    - retrieve: 获取单个IP作品详情
    - create: 创建新IP作品
    - update: 更新IP作品
    - partial_update: 部分更新IP作品
    - destroy: 删除IP作品
    """

    queryset = IP.objects.all().order_by("name")
    serializer_class = IPSimpleSerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    search_fields = ("name", "keywords__value")
    filterset_fields = {
        "name": ["exact", "icontains"],
    }


class CharacterViewSet(viewsets.ModelViewSet):
    """
    角色CRUD接口。

    - list: 获取所有角色列表，支持按IP过滤
    - retrieve: 获取单个角色详情
    - create: 创建新角色
    - update: 更新角色
    - partial_update: 部分更新角色
    - destroy: 删除角色
    """

    queryset = Character.objects.all().select_related("ip").order_by("ip__name", "name")
    serializer_class = CharacterSimpleSerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    search_fields = ("name", "ip__name", "ip__keywords__value")
    filterset_fields = {
        "ip": ["exact"],
        "name": ["exact", "icontains"],
    }


class CategoryViewSet(viewsets.ModelViewSet):
    """
    品类CRUD接口。

    - list: 获取所有品类列表
    - retrieve: 获取单个品类详情
    - create: 创建新品类
    - update: 更新品类
    - partial_update: 部分更新品类
    - destroy: 删除品类
    """

    queryset = Category.objects.all().order_by("name")
    serializer_class = CategorySimpleSerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    search_fields = ("name",)
    filterset_fields = {
        "name": ["exact", "icontains"],
    }
