"""
主题相关的序列化器
"""
from rest_framework import serializers

from ..models import Theme


class ThemeSimpleSerializer(serializers.ModelSerializer):
    """主题简单序列化器（用于列表和嵌套显示）"""
    
    class Meta:
        model = Theme
        fields = ("id", "name", "description", "created_at")


class ThemeDetailSerializer(serializers.ModelSerializer):
    """主题详情序列化器（用于创建和更新）"""
    
    class Meta:
        model = Theme
        fields = ("id", "name", "description", "created_at")


