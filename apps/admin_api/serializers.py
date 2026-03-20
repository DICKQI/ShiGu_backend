from __future__ import annotations

from django.db import transaction
from rest_framework import serializers

from apps.users.models import Role, User


class AdminRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ("id", "name", "created_at")


class AdminUserSerializer(serializers.ModelSerializer):
    """列表 / 详情：不含密码。"""

    role = AdminRoleSerializer(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "role",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class AdminUserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(min_length=6, max_length=128, write_only=True)
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(),
        source="role",
        write_only=True,
    )

    class Meta:
        model = User
        fields = ("username", "password", "role_id")

    def validate_username(self, value: str) -> str:
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("username 不能为空")
        if User.objects.filter(username=v).exists():
            raise serializers.ValidationError("username 已存在")
        return v

    @transaction.atomic
    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(),
        source="role",
        required=False,
        allow_null=False,
    )
    password = serializers.CharField(
        min_length=6,
        max_length=128,
        write_only=True,
        required=False,
        allow_blank=False,
    )

    class Meta:
        model = User
        fields = ("role_id", "is_active", "password")

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
