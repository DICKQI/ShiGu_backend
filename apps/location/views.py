from django.db import transaction
from rest_framework import generics, status
from rest_framework.response import Response

from apps.goods.models import Goods
from apps.goods.serializers import GoodsListSerializer

from .models import StorageNode
from .serializers import StorageNodeSerializer, StorageNodeTreeSerializer


class StorageNodeListCreateView(generics.ListCreateAPIView):
    """
    基础的收纳节点列表 / 创建接口。
    一般后台维护使用，非高频调用。
    """

    queryset = StorageNode.objects.all().order_by("order", "id")
    serializer_class = StorageNodeSerializer


class StorageNodeDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    收纳节点详情 / 更新 / 删除接口。
    
    - GET: 获取单个节点详情
    - PUT/PATCH: 更新节点信息
    - DELETE: 删除节点及其所有子节点，并取消关联的商品
    """

    queryset = StorageNode.objects.all()
    serializer_class = StorageNodeSerializer

    def get_queryset(self):
        """优化查询，预加载父节点和子节点"""
        return StorageNode.objects.select_related("parent").prefetch_related("children")

    def get_all_descendants(self, node):
        """
        递归获取节点的所有后代节点（包括子节点、子节点的子节点等）
        返回包含该节点及其所有后代的列表
        """
        descendants = [node]
        children = node.children.all()
        for child in children:
            descendants.extend(self.get_all_descendants(child))
        return descendants

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        """
        删除节点时：
        1. 递归获取所有子节点（包括子节点的子节点）
        2. 取消所有节点关联的商品（将商品的 location 设置为 null）
        3. 删除根节点（由于 CASCADE，删除父节点会自动删除所有子节点）
        """
        instance = self.get_object()
        
        # 获取所有要删除的节点（包括当前节点及其所有后代）
        nodes_to_delete = self.get_all_descendants(instance)
        node_ids = [node.id for node in nodes_to_delete]
        
        # 取消所有关联的商品（将 location 设置为 null）
        # 虽然 Goods 的 location 使用了 on_delete=models.SET_NULL，
        # 但为了确保在删除前显式处理，我们先取消关联
        from apps.goods.models import Goods
        Goods.objects.filter(location_id__in=node_ids).update(location=None)
        
        # 删除根节点（由于 parent 字段使用了 on_delete=models.CASCADE，
        # 删除父节点时，Django 会自动删除所有子节点）
        instance.delete()
        
        return Response(status=status.HTTP_204_NO_CONTENT)


class StorageNodeTreeView(generics.ListAPIView):
    """
    位置树一次性下发接口：
    - 返回所有节点的扁平列表（带 parent），前端在 Pinia 中组装为树。
    - 更新频率极低，后续可在此视图外层加缓存（例如 Redis）。
    """

    queryset = StorageNode.objects.all().order_by("path_name", "order")
    serializer_class = StorageNodeTreeSerializer


class StorageNodeGoodsView(generics.ListAPIView):
    """
    获取收纳节点下的所有商品接口。
    
    - GET: 获取指定节点下的所有商品列表
    - 支持查询参数 include_children：是否包含子节点下的商品（默认 false，只查询当前节点）
    """

    serializer_class = GoodsListSerializer

    def get_queryset(self):
        """
        根据节点 ID 获取商品列表。
        如果 include_children=true，则包含所有子节点下的商品。
        """
        node_id = self.kwargs.get("pk")
        include_children = self.request.query_params.get("include_children", "false").lower() == "true"

        try:
            node = StorageNode.objects.get(pk=node_id)
        except StorageNode.DoesNotExist:
            return Goods.objects.none()

        # 如果包含子节点，需要获取所有子节点 ID
        if include_children:
            # 获取所有子节点（包括子节点的子节点）
            all_nodes = self.get_all_descendants(node)
            node_ids = [n.id for n in all_nodes]
        else:
            # 只查询当前节点
            node_ids = [node.id]

        # 查询商品，使用优化查询避免 N+1 问题
        queryset = (
            Goods.objects.filter(location_id__in=node_ids)
            .select_related("ip", "category", "location")
            .prefetch_related("characters__ip", "additional_photos")
            .order_by("-created_at")
        )

        return queryset

    def get_all_descendants(self, node):
        """
        递归获取节点的所有后代节点（包括子节点、子节点的子节点等）
        返回包含该节点及其所有后代的列表
        """
        descendants = [node]
        children = node.children.all()
        for child in children:
            descendants.extend(self.get_all_descendants(child))
        return descendants

