from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import User
from .serializers import (
    LoginSerializer,
    RegisterSerializer,
    TokenResponseSerializer,
    UserMeSerializer,
    build_token_response,
)

@extend_schema(
    tags=["Auth"],
    summary="账号注册（获取 Token）",
    description=(
        "创建新用户并返回用于后续调用的访问令牌（access_token）。\n\n"
        "- 无需携带 Authorization 头。\n"
        "- 注册成功后可直接使用返回的 Token 调用其它需要登录的接口。"
    ),
    request=RegisterSerializer,
    responses={
        201: OpenApiResponse(TokenResponseSerializer, description="注册成功，返回访问令牌"),
        400: OpenApiResponse(description="参数校验失败，例如 username 已存在"),
    },
)
@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()

    secret = getattr(settings, "JWT_SECRET", settings.SECRET_KEY)
    ttl = int(getattr(settings, "JWT_ACCESS_TTL_SECONDS", 7 * 24 * 3600))
    data = build_token_response(user=user, secret=secret, ttl_seconds=ttl)
    return Response(data, status=status.HTTP_201_CREATED)

@extend_schema(
    tags=["Auth"],
    summary="账号登录（获取 Token）",
    description=(
        "使用已注册的账号和密码获取新的访问令牌（access_token）。\n\n"
        "- 无需携带 Authorization 头。\n"
        "- 如果账号被停用，返回 403；用户名或密码错误返回 400。"
    ),
    request=LoginSerializer,
    responses={
        200: OpenApiResponse(TokenResponseSerializer, description="登录成功，返回访问令牌"),
        400: OpenApiResponse(description="用户名或密码错误，或请求参数不合法"),
        403: OpenApiResponse(description="账号已停用"),
    },
)
@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    username = (serializer.validated_data.get("username") or "").strip()
    password = serializer.validated_data.get("password") or ""

    try:
        user = User.objects.select_related("role").get(username=username)
    except User.DoesNotExist:
        return Response({"detail": "用户名或密码错误"}, status=status.HTTP_400_BAD_REQUEST)

    if not user.is_active:
        return Response({"detail": "账号已停用"}, status=status.HTTP_403_FORBIDDEN)

    if not user.check_password(password):
        return Response({"detail": "用户名或密码错误"}, status=status.HTTP_400_BAD_REQUEST)

    secret = getattr(settings, "JWT_SECRET", settings.SECRET_KEY)
    ttl = int(getattr(settings, "JWT_ACCESS_TTL_SECONDS", 7 * 24 * 3600))
    data = build_token_response(user=user, secret=secret, ttl_seconds=ttl)
    return Response(data, status=status.HTTP_200_OK)

@extend_schema(
    tags=["Auth"],
    summary="获取当前登录用户信息",
    description=(
        "根据请求头中的 JWT Token 返回当前登录用户的基础信息。\n\n"
        "- 必须在 Header 中携带 `Authorization: Bearer <access_token>`。\n"
        "- 未携带或 Token 无效时由全局认证返回 401。"
    ),
    responses={
        200: OpenApiResponse(UserMeSerializer, description="当前登录用户信息"),
        401: OpenApiResponse(description="未认证或 Token 无效"),
    },
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    user = request.user
    payload = {
        "id": user.id,
        "username": getattr(user, "username", ""),
        "role": getattr(getattr(user, "role", None), "name", None),
    }
    return Response(UserMeSerializer(payload).data, status=status.HTTP_200_OK)


@extend_schema(
    tags=["Auth"],
    summary="账号登出（前端删除 Token）",
    description=(
        "使用请求头中的 JWT Token 执行登出操作。\n\n"
        "- 必须在 Header 中携带 `Authorization: Bearer <access_token>`。\n"
        "- 当前系统采用无状态 JWT，本接口不会在后端记录会话或黑名单，仅用于前端统一触发登出逻辑；\n"
        "  调用成功后请在前端删除本地缓存的 Token（如 LocalStorage 中的 access_token）。\n"
        "- 未携带或 Token 无效时由全局认证返回 401。"
    ),
    responses={
        204: OpenApiResponse(description="登出成功，无返回体"),
        401: OpenApiResponse(description="未认证或 Token 无效"),
    },
)
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def logout(request):
    # 无状态 JWT：不维护服务端会话或黑名单，交由前端删除 Token
    return Response(status=status.HTTP_204_NO_CONTENT)


