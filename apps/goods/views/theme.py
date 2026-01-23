"""
主题（Theme）相关的视图
"""
from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters as drf_filters, viewsets
from rest_framework.response import Response

from ..models import Theme
from ..serializers import ThemeDetailSerializer, ThemeSimpleSerializer


class ThemeViewSet(viewsets.ModelViewSet):
    """
    主题CRUD接口。

    - list: 获取所有主题列表
    - retrieve: 获取单个主题详情
    - create: 创建新主题
    - update: 更新主题
    - partial_update: 部分更新主题
    - destroy: 删除主题
    """

    queryset = Theme.objects.all().order_by("created_at")
    filter_backends = (DjangoFilterBackend, drf_filters.SearchFilter)
    search_fields = ("name", "description")
    filterset_fields = {
        "name": ["exact", "icontains"],
    }

    def get_queryset(self):
        """优化查询，统计关联的谷子数量"""
        return (
            Theme.objects.all()
            .annotate(goods_count=Count("goods"))
            .order_by("created_at")
        )

    def get_serializer_class(self):
        """根据操作类型选择序列化器"""
        if self.action in ("create", "update", "partial_update"):
            return ThemeDetailSerializer
        return ThemeSimpleSerializer


