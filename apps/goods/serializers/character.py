"""
角色相关的序列化器
"""
from rest_framework import serializers

from ..models import Character, IP
from .fields import AvatarField
from .ip import IPSimpleSerializer


class CharacterSimpleSerializer(serializers.ModelSerializer):
    ip = IPSimpleSerializer(read_only=True)
    ip_id = serializers.PrimaryKeyRelatedField(
        queryset=IP.objects.all(),
        source="ip",
        write_only=True,
        required=True,
        help_text="所属IP作品ID",
    )
    avatar = AvatarField(
        required=False,
        allow_null=True,
        help_text="角色头像。可以是文件上传（multipart/form-data）或URL字符串（如 https://example.com/avatar.jpg）",
    )

    class Meta:
        model = Character
        fields = ("id", "name", "ip", "ip_id", "avatar", "gender")
