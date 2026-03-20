"""
主题相关的序列化器
"""
from rest_framework import serializers

from apps.users.models import User as UserModel
from core.permissions import is_admin

from ..models import Theme, ThemeImage
from ..utils import compress_image


class ThemeImageSerializer(serializers.ModelSerializer):
    """主题附加图片序列化器"""

    class Meta:
        model = ThemeImage
        fields = ("id", "image", "label")

    def create(self, validated_data):
        """创建时自动压缩图片"""
        image = validated_data.get("image")
        if image:
            compressed_image = compress_image(image, max_size_kb=300)
            if compressed_image:
                validated_data["image"] = compressed_image
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """更新时自动压缩图片"""
        image = validated_data.get("image")
        if image:
            compressed_image = compress_image(image, max_size_kb=300)
            if compressed_image:
                validated_data["image"] = compressed_image
        return super().update(instance, validated_data)


class ThemeSimpleSerializer(serializers.ModelSerializer):
    """主题简单序列化器（用于列表和嵌套显示）"""

    class Meta:
        model = Theme
        fields = ("id", "name", "description", "created_at")


class ThemeDetailSerializer(serializers.ModelSerializer):
    """主题详情序列化器（用于创建和更新）"""

    images = ThemeImageSerializer(many=True, read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=UserModel.objects.all(),
        write_only=True,
        required=False,
        help_text="仅管理员：指定主题归属用户；省略则归属当前登录用户",
    )

    class Meta:
        model = Theme
        fields = ("id", "name", "description", "created_at", "images", "user_id")

    def validate_user_id(self, value):
        request = self.context.get("request")
        if not request or not is_admin(request.user):
            raise serializers.ValidationError("仅管理员可指定 user_id")
        return value

    def create(self, validated_data):
        validated_data.pop("user_id", None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("user_id", None)
        return super().update(instance, validated_data)


