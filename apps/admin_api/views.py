from __future__ import annotations

from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.users.models import Role, User
from core.permissions import IsAdmin

from .serializers import (
    AdminRoleSerializer,
    AdminUserCreateSerializer,
    AdminUserSerializer,
    AdminUserUpdateSerializer,
)


class AdminPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


@extend_schema_view(
    list=extend_schema(
        responses={200: OpenApiResponse(AdminUserSerializer(many=True))},
    ),
    retrieve=extend_schema(
        responses={200: OpenApiResponse(AdminUserSerializer())},
    ),
    create=extend_schema(
        request=AdminUserCreateSerializer,
        responses={201: OpenApiResponse(AdminUserSerializer())},
    ),
    update=extend_schema(
        request=AdminUserUpdateSerializer,
        responses={200: OpenApiResponse(AdminUserSerializer())},
    ),
    partial_update=extend_schema(
        request=AdminUserUpdateSerializer,
        responses={200: OpenApiResponse(AdminUserSerializer())},
    ),
)
@extend_schema(
    tags=["Admin"],
    summary="管理员：用户列表与账号维护",
    description=(
        "仅 `role.name` 为 Admin 的账号可访问。\n\n"
        "- 支持分页：`?page=`、`?page_size=`（最大 100）。\n"
        "- 不提供 DELETE：请使用 PATCH 将 `is_active` 设为 false 停用账号。"
    ),
)
class AdminUserViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = AdminPagination
    queryset = User.objects.select_related("role").order_by("id")

    def get_serializer_class(self):
        if self.action == "create":
            return AdminUserCreateSerializer
        if self.action in ("update", "partial_update"):
            return AdminUserUpdateSerializer
        return AdminUserSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        out = AdminUserSerializer(user, context=self.get_serializer_context())
        headers = self.get_success_headers(out.data)
        return Response(out.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        user = User.objects.select_related("role").get(pk=instance.pk)
        return Response(
            AdminUserSerializer(user, context=self.get_serializer_context()).data
        )


@extend_schema_view(
    list=extend_schema(
        responses={200: OpenApiResponse(AdminRoleSerializer(many=True))},
    ),
)
@extend_schema(
    tags=["Admin"],
    summary="管理员：账号角色枚举",
    description="返回 `users.Role` 表记录，供后台分配用户角色时下拉使用（如 Admin、User）。",
)
class AdminRoleViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = AdminRoleSerializer
    queryset = Role.objects.order_by("id")
