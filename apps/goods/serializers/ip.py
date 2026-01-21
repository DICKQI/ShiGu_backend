"""
IP作品相关的序列化器
"""
from rest_framework import serializers

from ..models import IP, IPKeyword
from .fields import KeywordsField


class IPKeywordSerializer(serializers.ModelSerializer):
    """IP关键词序列化器"""

    class Meta:
        model = IPKeyword
        fields = ("id", "value")


class IPSimpleSerializer(serializers.ModelSerializer):
    """IP简单序列化器（用于列表和嵌套显示）"""

    keywords = IPKeywordSerializer(many=True, read_only=True, help_text="IP关键词列表")
    character_count = serializers.SerializerMethodField(help_text="该IP下的角色数量")

    class Meta:
        model = IP
        fields = ("id", "name", "subject_type", "keywords", "character_count")

    def get_character_count(self, obj):
        """统计IP下的角色数量"""
        # 如果使用了annotate预计算，直接使用结果
        if hasattr(obj, 'character_count'):
            return obj.character_count
        # 否则查询数据库
        return obj.characters.count()


class IPDetailSerializer(serializers.ModelSerializer):
    """IP详情序列化器（用于创建和更新，支持关键词操作）"""

    keywords = KeywordsField(required=False, allow_null=True, help_text="关键词列表，例如：['星铁', '崩铁', 'HSR']")

    class Meta:
        model = IP
        fields = ("id", "name", "subject_type", "keywords")

    def create(self, validated_data):
        """创建IP时同时创建关键词"""
        keywords_data = validated_data.pop("keywords", [])
        ip = IP.objects.create(**validated_data)

        # 创建关键词
        if keywords_data:
            for keyword_value in keywords_data:
                if keyword_value and keyword_value.strip():  # 忽略空字符串
                    IPKeyword.objects.get_or_create(ip=ip, value=keyword_value.strip())

        return ip

    def update(self, instance, validated_data):
        """更新IP时同步更新关键词"""
        keywords_data = validated_data.pop("keywords", None)

        # 更新IP基本信息
        instance.name = validated_data.get("name", instance.name)
        # 更新 subject_type（如果提供了）
        if "subject_type" in validated_data:
            instance.subject_type = validated_data.get("subject_type")
        instance.save()

        # 如果提供了keywords字段，则更新关键词
        if keywords_data is not None:
            # 获取当前关键词值集合
            existing_keywords = set(instance.keywords.values_list("value", flat=True))
            new_keywords = {kw.strip() for kw in keywords_data if kw and kw.strip()}

            # 删除不再存在的关键词
            to_delete = existing_keywords - new_keywords
            if to_delete:
                instance.keywords.filter(value__in=to_delete).delete()

            # 添加新关键词
            to_add = new_keywords - existing_keywords
            for keyword_value in to_add:
                IPKeyword.objects.get_or_create(ip=instance, value=keyword_value)

        return instance
