"""
角色（Character）相关的视图
"""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters as drf_filters, viewsets

from ..models import Character
from ..serializers import CharacterSimpleSerializer


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

    queryset = Character.objects.all().select_related("ip").order_by("created_at")
    serializer_class = CharacterSimpleSerializer
    filter_backends = (DjangoFilterBackend, drf_filters.SearchFilter)
    search_fields = ("name", "ip__name", "ip__keywords__value")
    filterset_fields = {
        "ip": ["exact"],
        "name": ["exact", "icontains"],
    }
