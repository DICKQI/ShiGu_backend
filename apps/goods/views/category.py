"""
品类（Category）相关的视图
"""
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters as drf_filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import Category, Goods
from ..serializers import (
    CategoryBatchUpdateOrderSerializer,
    CategoryDetailSerializer,
    CategorySimpleSerializer,
    CategoryTreeSerializer,
)


class CategoryViewSet(viewsets.ModelViewSet):
    """
    品类CRUD接口，支持树形结构。

    - list: 获取所有品类列表（支持按父节点过滤）
    - retrieve: 获取单个品类详情
    - create: 创建新品类（支持树形结构）
    - update: 更新品类
    - partial_update: 部分更新品类
    - destroy: 删除品类（会级联删除所有子节点）
    - tree: 获取品类树（扁平列表，前端组装为树）
    - batch_update_order: 批量更新品类排序（用于拖拽排序等功能）
    """

    queryset = Category.objects.all().order_by("order", "id")
    filter_backends = (DjangoFilterBackend, drf_filters.SearchFilter)
    search_fields = ("name", "path_name")
    filterset_fields = {
        "name": ["exact", "icontains"],
        "parent": ["exact", "isnull"],
    }
    
    def get_queryset(self):
        """优化查询，预加载父节点和子节点"""
        return Category.objects.select_related("parent").prefetch_related("children")
    
    def get_serializer_class(self):
        """根据操作类型选择序列化器"""
        if self.action in ("create", "update", "partial_update"):
            return CategoryDetailSerializer
        if self.action == "tree":
            return CategoryTreeSerializer
        return CategorySimpleSerializer
    
    def get_all_descendants(self, category):
        """
        递归获取品类的所有后代节点（包括子节点、子节点的子节点等）
        返回包含该节点及其所有后代的列表
        """
        descendants = [category]
        children = category.children.all()
        for child in children:
            descendants.extend(self.get_all_descendants(child))
        return descendants
    
    @action(detail=False, methods=["get"], url_path="tree")
    def tree(self, request):
        """
        获取品类树一次性下发接口
        URL: /api/categories/tree/
        
        返回所有节点的扁平列表（带 parent），前端在内存中组装为树。
        """
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=["post"], url_path="batch-update-order")
    def batch_update_order(self, request):
        """
        批量更新品类排序接口
        URL: /api/categories/batch-update-order/
        
        用于前端通过拖拽等方式调整品类顺序后，批量更新排序值。
        支持同时更新多个品类的order字段。
        """
        serializer = CategoryBatchUpdateOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        items = serializer.validated_data['items']
        
        # 验证所有品类ID是否存在
        category_ids = [item['id'] for item in items]
        existing_categories = Category.objects.filter(id__in=category_ids)
        existing_ids = set(existing_categories.values_list('id', flat=True))
        
        missing_ids = set(category_ids) - existing_ids
        if missing_ids:
            return Response(
                {"detail": f"以下品类ID不存在: {sorted(missing_ids)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        # 批量更新排序值（使用事务保证原子性）
        try:
            with transaction.atomic():
                # 创建字典以便快速查找
                category_dict = {cat.id: cat for cat in existing_categories}
                
                # 更新每个品类的order值
                updated_categories = []
                for item in items:
                    category = category_dict[item['id']]
                    category.order = item['order']
                    category.save(update_fields=['order'])
                    updated_categories.append(category)
                
                # 返回更新后的品类列表（按新的order排序）
                updated_ids = [cat.id for cat in updated_categories]
                result_categories = Category.objects.filter(id__in=updated_ids).order_by('order', 'id')
                result_serializer = CategorySimpleSerializer(result_categories, many=True)
                
                return Response({
                    "detail": f"成功更新 {len(updated_categories)} 个品类的排序",
                    "updated_count": len(updated_categories),
                    "categories": result_serializer.data
                }, status=status.HTTP_200_OK)
                
        except Exception as e:
            return Response(
                {"detail": f"更新排序失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    
    def destroy(self, request, *args, **kwargs):
        """
        删除品类时：
        1. 递归获取所有子节点（包括子节点的子节点）
        2. 检查是否有商品关联到这些品类（包括子节点）
        3. 如果有商品关联，返回错误
        4. 删除根节点（由于 CASCADE，删除父节点会自动删除所有子节点）
        """
        instance = self.get_object()
        
        # 获取所有要删除的节点（包括当前节点及其所有后代）
        nodes_to_delete = self.get_all_descendants(instance)
        node_ids = [node.id for node in nodes_to_delete]
        
        # 检查是否有商品关联到这些品类
        goods_count = Goods.objects.filter(category_id__in=node_ids).count()
        if goods_count > 0:
            return Response(
                {"detail": f"无法删除：有 {goods_count} 个商品关联到此品类或其子品类，请先解除关联"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        # 删除根节点（由于 parent 字段使用了 on_delete=models.CASCADE，
        # 删除父节点时，Django 会自动删除所有子节点）
        with transaction.atomic():
            instance.delete()
        
        return Response(status=status.HTTP_204_NO_CONTENT)
