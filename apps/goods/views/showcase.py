"""
展柜相关的视图
"""
from django.db import transaction
from django.db.models import Min, Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from ..models import Goods, Showcase, ShowcaseGoods
from ..serializers.showcase import (
    AddGoodsToShowcaseSerializer,
    MoveGoodsInShowcaseSerializer,
    RemoveGoodsFromShowcaseSerializer,
    ShowcaseDetailSerializer,
    ShowcaseGoodsSerializer,
    ShowcaseListSerializer,
)
from ..utils import compress_image
from core.permissions import IsOwnerOrPublicReadOnly, is_admin


class ShowcasePagination(PageNumberPagination):
    """展柜列表分页类"""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "count": self.page.paginator.count,
                "page": self.page.number,
                "page_size": self.page_size,
                "next": self.page.next_page_number() if self.page.has_next() else None,
                "previous": self.page.previous_page_number()
                if self.page.has_previous()
                else None,
                "results": data,
            }
        )


class ShowcaseViewSet(viewsets.ModelViewSet):
    """展柜视图集"""

    queryset = Showcase.objects.all().prefetch_related(
        "showcase_goods__goods__ip", "showcase_goods__goods__characters"
    )
    permission_classes = [IsOwnerOrPublicReadOnly]

    # 稀疏排序步长
    ORDER_STEP = 1000

    def get_serializer_class(self):
        if self.action in ["list", "public_list", "private_list"]:
            return ShowcaseListSerializer
        return ShowcaseDetailSerializer

    pagination_class = ShowcasePagination

    def get_queryset(self):
        """优化查询，避免 N+1 问题"""
        qs = (
            Showcase.objects.all()
            .prefetch_related(
                "showcase_goods__goods__ip",
                "showcase_goods__goods__characters__ip",
                "showcase_goods__goods__category",
                "showcase_goods__goods__theme",
            )
            .select_related()
        )
        
        # 如果是公共列表动作，直接返回公开的展柜
        if self.action in ['public_list', 'public']:
            return qs.filter(is_public=True)
            
        # 如果是私有列表动作，返回当前用户的展柜
        if self.action in ['private_list', 'private']:
            if self.request.user.is_authenticated:
                return qs.filter(user=self.request.user)
            return qs.none()

        user = getattr(self.request, "user", None)
        if not user or not getattr(user, "id", None):
            # 对于匿名用户，如果是获取详情且该展柜是公开的，允许访问
            if self.action == 'retrieve':
                return qs.filter(is_public=True)
            return qs.none()
            
        if is_admin(user):
            return qs
        return qs.filter(Q(user=user) | Q(is_public=True))

    @action(detail=False, methods=["get"], url_path="public", permission_classes=[AllowAny])
    def public_list(self, request):
        """获取公共展柜列表"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="private", permission_classes=[IsAuthenticated])
    def private_list(self, request):
        """获取私有展柜列表（我的展柜）"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        """创建展柜时自动分配排序值"""
        user = self.request.user
        min_order = (
            Showcase.objects.filter(user=user)
            .aggregate(min_order=Min("order"))
            .get("min_order")
        )
        next_order = (min_order or 0) - self.ORDER_STEP
        serializer.save(user=user, order=next_order)

    @action(
        detail=True,
        methods=["post"],
        url_path="upload-cover-image",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_cover_image(self, request, pk=None):
        """
        独立上传/更新展柜封面接口，使用 multipart/form-data，字段名：cover_image
        """
        instance = self.get_object()
        cover_image = request.FILES.get("cover_image")

        if not cover_image:
            return Response(
                {"detail": "请通过 form-data 提供 cover_image 文件"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        compressed = compress_image(cover_image, max_size_kb=300)
        instance.cover_image = compressed or cover_image
        instance.save(update_fields=["cover_image", "updated_at"])

        serializer = ShowcaseDetailSerializer(
            instance, context=self.get_serializer_context()
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="goods")
    def goods(self, request, pk=None):
        """获取展柜中的所有谷子"""
        showcase = self.get_object()

        queryset = ShowcaseGoods.objects.filter(showcase=showcase).select_related(
            "goods__ip",
            "goods__category",
            "goods__theme",
        ).prefetch_related("goods__characters__ip")

        serializer = ShowcaseGoodsSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="add-goods")
    def add_goods(self, request, pk=None):
        """添加谷子到展柜"""
        showcase = self.get_object()
        serializer = AddGoodsToShowcaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        goods_id = serializer.validated_data["goods_id"]
        notes = serializer.validated_data.get("notes", "")

        # 验证谷子存在
        try:
            goods_qs = Goods.objects.all()
            if not is_admin(request.user):
                goods_qs = goods_qs.filter(user=showcase.user)
            goods = goods_qs.get(id=goods_id)
        except Goods.DoesNotExist:
            return Response(
                {"detail": "谷子不存在"}, status=status.HTTP_404_NOT_FOUND
            )

        # 验证同一谷子在同一展柜中不重复
        if ShowcaseGoods.objects.filter(showcase=showcase, goods=goods).exists():
            return Response(
                {"detail": "该谷子已在此展柜中"}, status=status.HTTP_400_BAD_REQUEST
            )

        # 计算排序值：该展柜下的最小值 - ORDER_STEP
        min_order = (
            ShowcaseGoods.objects.filter(showcase=showcase)
            .aggregate(min_order=Min("order"))
            .get("min_order")
        )
        next_order = (min_order or 0) - self.ORDER_STEP

        # 创建关联
        showcase_goods = ShowcaseGoods.objects.create(
            showcase=showcase,
            goods=goods,
            order=next_order,
            notes=notes,
        )

        serializer = ShowcaseGoodsSerializer(showcase_goods)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="remove-goods")
    def remove_goods(self, request, pk=None):
        """从展柜移除谷子"""
        showcase = self.get_object()
        serializer = RemoveGoodsFromShowcaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        goods_id = serializer.validated_data["goods_id"]

        try:
            showcase_goods = ShowcaseGoods.objects.get(
                showcase=showcase, goods_id=goods_id
            )
            showcase_goods.delete()
            return Response({"detail": "已从展柜移除"}, status=status.HTTP_200_OK)
        except ShowcaseGoods.DoesNotExist:
            return Response(
                {"detail": "该谷子不在此展柜中"},
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=True, methods=["post"], url_path="move-goods")
    def move_goods(self, request, pk=None):
        """移动展柜中谷子的位置（类似 GoodsViewSet.move）"""
        showcase = self.get_object()
        serializer = MoveGoodsInShowcaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        goods_id = serializer.validated_data["goods_id"]
        anchor_goods_id = serializer.validated_data["anchor_goods_id"]
        position = serializer.validated_data["position"]

        try:
            current_sg = ShowcaseGoods.objects.get(
                showcase=showcase, goods_id=goods_id
            )
            anchor_sg = ShowcaseGoods.objects.get(
                showcase=showcase, goods_id=anchor_goods_id
            )
        except ShowcaseGoods.DoesNotExist:
            return Response(
                {"detail": "谷子不存在或不在该展柜中"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 如果移动到自己，无需操作
        if current_sg.id == anchor_sg.id:
            return Response({"detail": "无需移动"}, status=status.HTTP_200_OK)

        # 使用稀疏排序算法（参考 GoodsViewSet.move）
        with transaction.atomic():
            current_locked = ShowcaseGoods.objects.select_for_update().get(
                id=current_sg.id
            )
            anchor_locked = ShowcaseGoods.objects.select_for_update().get(
                id=anchor_sg.id
            )

            def _prev_item(obj, exclude_ids):
                """获取 obj 前一个元素"""
                qs = ShowcaseGoods.objects.filter(
                    showcase=showcase
                ).exclude(id__in=exclude_ids)
                return (
                    qs.filter(
                        Q(order__lt=obj.order)
                        | Q(order=obj.order, created_at__gt=obj.created_at)
                        | Q(
                            order=obj.order,
                            created_at=obj.created_at,
                            id__gt=obj.id,
                        )
                    )
                    .order_by("-order", "created_at", "-id")
                    .first()
                )

            def _next_item(obj, exclude_ids):
                """获取 obj 后一个元素"""
                qs = ShowcaseGoods.objects.filter(
                    showcase=showcase
                ).exclude(id__in=exclude_ids)
                return (
                    qs.filter(
                        Q(order__gt=obj.order)
                        | Q(order=obj.order, created_at__lt=obj.created_at)
                        | Q(
                            order=obj.order,
                            created_at=obj.created_at,
                            id__lt=obj.id,
                        )
                    )
                    .order_by("order", "created_at", "id")
                    .first()
                )

            def _compute_new_order(prev_obj, next_obj):
                if prev_obj and next_obj:
                    if prev_obj.order + 1 < next_obj.order:
                        return (prev_obj.order + next_obj.order) // 2
                    return None
                if prev_obj and not next_obj:
                    return prev_obj.order + self.ORDER_STEP
                if next_obj and not prev_obj:
                    return next_obj.order - self.ORDER_STEP
                return 0

            if position == "before":
                prev_obj = _prev_item(anchor_locked, exclude_ids={current_locked.id})
                next_obj = anchor_locked
            else:  # after
                prev_obj = anchor_locked
                next_obj = _next_item(anchor_locked, exclude_ids={current_locked.id})

            new_order = _compute_new_order(prev_obj, next_obj)

            if new_order is None:
                # 无空隙，使用简单策略
                new_order = anchor_locked.order + (
                    self.ORDER_STEP if position == "after" else -self.ORDER_STEP
                )

            current_locked.order = new_order
            current_locked.save(update_fields=["order"])

        return Response(
            {
                "detail": "排序更新成功",
                "id": str(current_sg.id),
                "new_order": current_locked.order,
            },
            status=status.HTTP_200_OK,
        )
