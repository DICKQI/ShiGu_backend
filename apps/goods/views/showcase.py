"""
展柜相关的视图
"""
from django.db import transaction
from django.db.models import Min, Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
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

    # 稀疏排序步长
    ORDER_STEP = 1000

    def get_serializer_class(self):
        if self.action == "list":
            return ShowcaseListSerializer
        return ShowcaseDetailSerializer

    pagination_class = ShowcasePagination

    def get_queryset(self):
        """优化查询，避免 N+1 问题"""
        return (
            Showcase.objects.all()
            .prefetch_related(
                "showcase_goods__goods__ip",
                "showcase_goods__goods__characters__ip",
                "showcase_goods__goods__category",
                "showcase_goods__goods__theme",
            )
            .select_related()
        )

    def perform_create(self, serializer):
        """创建展柜时自动分配排序值"""
        min_order = Showcase.objects.aggregate(min_order=Min("order")).get(
            "min_order"
        )
        next_order = (min_order or 0) - self.ORDER_STEP
        serializer.save(order=next_order)

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
            goods = Goods.objects.get(id=goods_id)
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
