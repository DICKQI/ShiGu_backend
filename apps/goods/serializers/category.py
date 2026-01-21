"""
品类相关的序列化器
"""
from rest_framework import serializers

from ..models import Category


class CategorySimpleSerializer(serializers.ModelSerializer):
    """品类简单序列化器（用于列表和嵌套显示）"""
    parent = serializers.PrimaryKeyRelatedField(read_only=True, help_text="父级品类ID")
    
    class Meta:
        model = Category
        fields = ("id", "name", "parent", "path_name", "color_tag", "order")


class CategoryTreeSerializer(serializers.ModelSerializer):
    """
    品类树一次性下发用序列化器。
    前端可根据 parent/id 在内存中自行组装为树结构。
    """
    
    class Meta:
        model = Category
        fields = ("id", "name", "parent", "path_name", "color_tag", "order")


class CategoryOrderItemSerializer(serializers.Serializer):
    """品类排序项序列化器（用于批量更新排序）"""
    id = serializers.IntegerField(help_text="品类ID")
    order = serializers.IntegerField(help_text="排序值，值越小越靠前")


class CategoryBatchUpdateOrderSerializer(serializers.Serializer):
    """批量更新品类排序序列化器"""
    items = CategoryOrderItemSerializer(
        many=True,
        required=True,
        help_text="品类排序项列表，每个项包含id和order字段"
    )
    
    def validate_items(self, value):
        """验证items列表"""
        if not value:
            raise serializers.ValidationError("items列表不能为空")
        
        # 检查是否有重复的ID
        ids = [item['id'] for item in value]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("items列表中不能有重复的品类ID")
        
        return value


class CategoryDetailSerializer(serializers.ModelSerializer):
    """品类详情序列化器（用于创建和更新，支持树形结构）"""
    
    path_name = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="完整路径，如果不提供则根据父节点自动生成，例如：周边/吧唧/圆形吧唧",
    )
    
    class Meta:
        model = Category
        fields = ("id", "name", "parent", "path_name", "color_tag", "order")
    
    def create(self, validated_data):
        """创建品类时，如果未提供 path_name，则根据父节点自动生成"""
        path_name = validated_data.get("path_name")
        parent = validated_data.get("parent")
        name = validated_data.get("name")
        
        # 如果 path_name 为空或未提供，则根据父节点自动生成
        if not path_name:
            if parent:
                # 有父节点：父节点路径 + "/" + 当前节点名称
                parent_path = parent.path_name or parent.name
                path_name = f"{parent_path}/{name}"
            else:
                # 无父节点（根节点）：直接使用节点名称
                path_name = name
        
        validated_data["path_name"] = path_name
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """更新品类时，如果父节点或名称改变，自动更新 path_name"""
        parent = validated_data.get("parent", instance.parent)
        name = validated_data.get("name", instance.name)
        path_name = validated_data.get("path_name")
        
        # 如果用户明确提供了 path_name，使用用户提供的值
        # 如果未提供 path_name，但父节点或名称改变了，需要重新生成
        if path_name is None:
            # 检查是否需要重新生成 path_name
            parent_changed = parent != instance.parent
            name_changed = name != instance.name
            
            if parent_changed or name_changed:
                # 重新生成 path_name
                if parent:
                    parent_path = parent.path_name or parent.name
                    path_name = f"{parent_path}/{name}"
                else:
                    path_name = name
                validated_data["path_name"] = path_name
        
        return super().update(instance, validated_data)
