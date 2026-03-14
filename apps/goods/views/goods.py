"""
谷子（Goods）相关的视图和过滤器
"""
from django.db import transaction
from django.db.models import Count, DateField, DecimalField, ExpressionWrapper, F, Min, Q, Sum, Value
from django.db.models.functions import Cast, Coalesce, TruncDate, TruncMonth, TruncWeek
from django.db import connection
from drf_spectacular.utils import OpenApiResponse, extend_schema
from django_filters import (
    BaseInFilter,
    BooleanFilter,
    CharFilter,
    FilterSet,
    ModelMultipleChoiceFilter,
    NumberFilter,
)
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters as drf_filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

import datetime
import hashlib
import random
from decimal import Decimal

from django.core.cache import cache

from ..models import Category, Character, Goods, GuziImage
from apps.location.models import StorageNode
from ..serializers import (
    GoodsDetailSerializer,
    GoodsDuplicateCandidateSerializer,
    GoodsListSerializer,
    GoodsMoveSerializer,
)
from ..utils import compress_image
from ..similarity import GoodsSimilarityCalculator, SeedSelector, SimilarityGroupBuilder
from core.permissions import IsOwnerOnly, is_admin


class GoodsPagination(PageNumberPagination):
    """
    谷子列表分页类
    返回格式：
    {
        "count": 总数,
        "page": 当前页码,
        "page_size": 每页数量,
        "next": 下一页页码（如果没有则为null）,
        "previous": 上一页页码（如果没有则为null）,
        "results": [...]
    }
    """
    page_size = 18  # 默认每页18条
    page_size_query_param = 'page_size'  # 允许客户端通过 ?page_size=xxx 自定义每页数量
    max_page_size = 100  # 最大每页数量限制
    
    def get_paginated_response(self, data):
        """
        自定义分页响应格式
        """
        return Response({
            'count': self.page.paginator.count,  # 总数
            'page': self.page.number,  # 当前页码
            'page_size': self.page_size,  # 每页数量
            'next': self.get_next_page_number(),  # 下一页页码
            'previous': self.get_previous_page_number(),  # 上一页页码
            'results': data  # 数据列表
        })
    
    def get_next_page_number(self):
        """
        获取下一页页码，如果没有则返回 None
        """
        if not self.page.has_next():
            return None
        return self.page.next_page_number()
    
    def get_previous_page_number(self):
        """
        获取上一页页码，如果没有则返回 None
        """
        if not self.page.has_previous():
            return None
        return self.page.previous_page_number()


class GoodsFilter(FilterSet):
    """谷子过滤集，正确处理多对多字段characters"""
    
    ip = NumberFilter(field_name="ip", lookup_expr="exact")
    # 树形品类筛选：?category=2 （筛选该品类及其所有子品类下的谷子）
    category = NumberFilter(method="filter_category_tree")
    # 树形位置筛选：?location=5 （筛选该位置及其所有子节点下的谷子）
    location = NumberFilter(method="filter_location_tree")
    theme = NumberFilter(field_name="theme", lookup_expr="exact")
    status = CharFilter(field_name="status", lookup_expr="exact")
    status__in = BaseInFilter(field_name="status", lookup_expr="in")
    is_official = BooleanFilter(field_name="is_official", lookup_expr="exact")
    
    # 单个角色筛选：?character=1387（精确匹配包含该角色的谷子）
    character = ModelMultipleChoiceFilter(
        field_name="characters",
        queryset=Character.objects.all(),
        conjoined=False,  # False表示"包含任意指定角色"（OR）
        help_text="单个角色ID，例如：?character=1387（包含该角色的谷子）"
    )
    
    class Meta:
        model = Goods
        fields = ["ip", "category", "location", "theme", "status", "status__in", "is_official", "character"]

    def _get_category_descendant_ids(self, category: Category) -> list[int]:
        """
        获取指定品类的所有后代品类ID（包含自身）。
        由于品类层级通常不深，这里用递归即可。
        """
        ids: list[int] = []

        def dfs(node: Category):
            ids.append(node.id)
            for child in node.children.all():
                dfs(child)

        # 预加载 children，避免递归过程中 N+1
        category = Category.objects.prefetch_related("children").get(pk=category.pk)
        dfs(category)
        return ids

    def _get_location_descendant_ids(self, node: StorageNode) -> list[int]:
        """
        获取指定物理位置节点的所有后代节点 ID（包含自身）。
        与品类类似，同样采用自关联树结构。
        """
        ids: list[int] = []

        def dfs(n: StorageNode):
            ids.append(n.id)
            for child in n.children.all():
                dfs(child)

        # 预加载 children，避免递归过程中 N+1
        node = StorageNode.objects.prefetch_related("children").get(pk=node.pk)
        dfs(node)
        return ids

    def filter_category_tree(self, queryset, name, value):
        """
        树形品类筛选：
        - ?category=<id>：返回该品类及其所有子品类下的谷子
        """
        if not value:
            return queryset
        try:
            category = Category.objects.get(pk=value)
        except Category.DoesNotExist:
            return queryset.none()

        ids = self._get_category_descendant_ids(category)
        return queryset.filter(category_id__in=ids)

    def filter_location_tree(self, queryset, name, value):
        """
        树形位置筛选：
        - ?location=<id>：返回该位置及其所有子节点下的谷子
        """
        if not value:
            return queryset
        try:
            node_qs = StorageNode.objects.all()
            req_user = getattr(self, "request", None) and getattr(self.request, "user", None)
            if req_user is not None and not is_admin(req_user):
                node_qs = node_qs.filter(user=req_user)
            node = node_qs.get(pk=value)
        except StorageNode.DoesNotExist:
            return queryset.none()

        ids = self._get_location_descendant_ids(node)
        return queryset.filter(location_id__in=ids)


class GoodsViewSet(viewsets.ModelViewSet):
    """
    谷子检索核心接口。

    - list: 高性能检索列表（瘦身字段），支持多维过滤 & 搜索，支持分页。
    - retrieve: 详情接口，返回完整信息及补充图片。
    """

    queryset = (
        Goods.objects.all()
        .select_related("ip", "category", "location", "theme")
        .prefetch_related("characters__ip", "additional_photos")
    )
    permission_classes = [IsOwnerOnly]

    # 列表接口瘦身：只返回必要字段；详情接口使用完整序列化器
    def get_serializer_class(self):
        if self.action == "list":
            return GoodsListSerializer
        return GoodsDetailSerializer

    # 过滤 & 搜索
    filter_backends = (
        DjangoFilterBackend,
        drf_filters.SearchFilter,
    )

    # 使用自定义FilterSet来正确处理多对多字段characters
    filterset_class = GoodsFilter

    # 轻量搜索：
    # - 对 Goods.name 走索引（已在模型上 db_index=True）
    # - 同时支持按 IP 名称 / 多关键词(IPKeyword) 搜索
    search_fields = (
        "name",
        "ip__name",
        "ip__keywords__value",
        'characters__name',
    )

    # 分页配置
    pagination_class = GoodsPagination

    # 限流：专门给检索接口一个 scope，具体速率在 settings.REST_FRAMEWORK.THROTTLE_RATES 中配置
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "goods_search"
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    # 稀疏排序步长（避免频繁重排）
    ORDER_STEP = 1000

    def get_queryset(self):
        """
        使用 select_related / prefetch_related 彻底解决 N+1 查询问题。
        """
        qs = (
            Goods.objects.all()
            .select_related("ip", "category", "location", "theme")
            .prefetch_related("characters__ip", "additional_photos")
        )
        user = getattr(self.request, "user", None)
        if not user or not getattr(user, "id", None):
            return qs.none()
        if is_admin(user):
            return qs
        return qs.filter(user=user)

    def _find_duplicate_candidates(self, user, validated_data):
        """
        根据「用户 + IP + 名称 + 角色集合 + 入手日期 + 单价」查找可能重复的谷子，返回候选列表。
        """
        ip = validated_data.get("ip")
        characters = validated_data.get("characters", [])
        name = validated_data.get("name")
        purchase_date = validated_data.get("purchase_date")
        price = validated_data.get("price")

        query = Goods.objects.filter(
            user=user,
            ip=ip,
            name=name,
            purchase_date=purchase_date,
            price=price,
        )

        if characters:
            character_ids = sorted([c.id for c in characters])
            query = query.annotate(character_count=Count("characters")).filter(
                character_count=len(character_ids)
            )
            candidates = []
            for candidate in query.prefetch_related("characters"):
                candidate_ids = sorted([c.id for c in candidate.characters.all()])
                if candidate_ids == character_ids:
                    candidates.append(candidate)
            return candidates

        if query.exists():
            first = query.first()
            if first.characters.count() == 0:
                return [first]
        return []

    @extend_schema(
        responses={
            201: GoodsDetailSerializer,
            409: OpenApiResponse(
                description="检测到可能重复的谷子，body 含 code=goods_duplicate 与 candidates 列表（含 main_photo_url 主图链接）",
                response={
                    "type": "object",
                    "properties": {
                        "detail": {"type": "string"},
                        "code": {"type": "string", "example": "goods_duplicate"},
                        "candidates": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "main_photo_url": {"type": "string", "description": "重复谷子的主图链接（绝对 URL）"},
                                },
                            },
                        },
                    },
                },
            ),
        },
        request=GoodsDetailSerializer,
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data
        merge_strategy = validated.get("merge_strategy", "auto")
        merge_target_id = validated.get("merge_target_id")
        user = request.user

        if merge_strategy == "new":
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        candidates = self._find_duplicate_candidates(user, validated)

        if merge_strategy == "auto" and candidates:
            candidate_serializer = GoodsDuplicateCandidateSerializer(
                candidates, many=True, context=self.get_serializer_context()
            )
            return Response(
                {
                    "detail": "检测到可能重复的谷子，请选择合并或新建",
                    "code": "goods_duplicate",
                    "candidates": candidate_serializer.data,
                },
                status=status.HTTP_409_CONFLICT,
            )

        if merge_strategy == "merge":
            if not candidates:
                self.perform_create(serializer)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            if len(candidates) == 1:
                target = candidates[0]
            else:
                if not merge_target_id:
                    return Response(
                        {
                            "detail": "存在多条可能重复的谷子，请指定 merge_target_id 选择要合并到的记录",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                target = next((c for c in candidates if str(c.id) == str(merge_target_id)), None)
                if not target:
                    return Response(
                        {"detail": "merge_target_id 不在候选列表中或不存在"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            add_qty = validated.get("quantity", 1)
            target.quantity += add_qty
            target.save(update_fields=["quantity", "updated_at"])
            detail_serializer = GoodsDetailSerializer(
                target, context=self.get_serializer_context()
            )
            return Response(
                {"merged": True, **detail_serializer.data},
                status=status.HTTP_200_OK,
            )

        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        """
        仅负责新建时的 order 分配与保存，去重与合并逻辑已移至 create()。
        """
        user = self.request.user
        min_order = (
            Goods.objects.filter(user=user)
            .aggregate(min_order=Min("order"))
            .get("min_order")
        )
        next_order = (min_order or 0) - self.ORDER_STEP
        serializer.save(user=user, order=next_order)

    @action(detail=True, methods=["post"], url_path="move")
    def move(self, request, pk=None):
        """
        移动谷子排序接口：
        将当前谷子移动到指定锚点谷子的前面或后面。
        """
        current_goods = self.get_object()
        owner_user = current_goods.user
        serializer = GoodsMoveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        anchor_id = serializer.validated_data["anchor_id"]
        position = serializer.validated_data["position"]

        try:
            with transaction.atomic():
                # 加锁当前与锚点，避免并发错位
                current_locked = Goods.objects.select_for_update().get(
                    id=current_goods.id
                )
                anchor_goods = Goods.objects.select_for_update().get(
                    id=anchor_id, user=owner_user
                )
        except Goods.DoesNotExist:
            return Response(
                {"detail": "锚点谷子不存在"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 如果锚点就是自己，无需移动
        if current_goods.id == anchor_goods.id:
            return Response({"detail": "无需移动"}, status=status.HTTP_200_OK)

        def _ordering_fields():
            # 确保全序：order, -created_at, id
            return ["order", "-created_at", "id"]

        def _prev_item(obj, exclude_ids):
            """获取 obj 前一个元素（按 ordering）"""
            return (
                Goods.objects.filter(user=owner_user).exclude(id__in=exclude_ids)
                .filter(
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
            """获取 obj 后一个元素（按 ordering）"""
            return (
                Goods.objects.filter(user=owner_user).exclude(id__in=exclude_ids)
                .filter(
                    Q(order__gt=obj.order)
                    | Q(order=obj.order, created_at__lt=obj.created_at)
                    | Q(
                        order=obj.order,
                        created_at=obj.created_at,
                        id__lt=obj.id,
                    )
                )
                .order_by(*_ordering_fields())
                .first()
            )

        def _rebalance_around(center: Goods, exclude_ids, window: int = 100):
            """
            在锚点附近拉开稀疏间距，防止无空隙时无法插入。
            仅重排局部窗口，避免大范围更新。
            """
            before_qs = (
                Goods.objects.filter(user=owner_user).exclude(
                    id__in=exclude_ids | {center.id}
                )
                .filter(
                    Q(order__lt=center.order)
                    | Q(order=center.order, created_at__gt=center.created_at)
                    | Q(order=center.order, created_at=center.created_at, id__gt=center.id)
                )
                .order_by("-order", "created_at", "-id")[:window]
            )
            after_qs = (
                Goods.objects.filter(user=owner_user).exclude(
                    id__in=exclude_ids | {center.id}
                )
                .filter(
                    Q(order__gt=center.order)
                    | Q(order=center.order, created_at__lt=center.created_at)
                    | Q(order=center.order, created_at=center.created_at, id__lt=center.id)
                )
                .order_by(*_ordering_fields())[:window]
            )

            before_list = list(before_qs)
            after_list = list(after_qs)
            ordered = list(reversed(before_list)) + [center] + after_list

            # 以锚点为中心重新赋值稀疏 order
            base = center.order - len(before_list) * self.ORDER_STEP
            updates = []
            for idx, obj in enumerate(ordered):
                new_val = base + idx * self.ORDER_STEP
                if obj.order != new_val:
                    obj.order = new_val
                    updates.append(obj)
            if updates:
                Goods.objects.bulk_update(updates, ["order"])

        def _compute_new_order(prev_obj, next_obj):
            if prev_obj and next_obj:
                # 两者之间有空隙
                if prev_obj.order + 1 < next_obj.order:
                    return (prev_obj.order + next_obj.order) // 2
                # 无空隙，返回 None 触发重排
                return None
            if prev_obj and not next_obj:
                return prev_obj.order + self.ORDER_STEP
            if next_obj and not prev_obj:
                return next_obj.order - self.ORDER_STEP
            # 列表为空的极端场景
            return 0

        with transaction.atomic():
            # 重新加锁防止与上面 select_for_update 间隔（事务块）
            current_locked = Goods.objects.select_for_update().get(id=current_goods.id)
            anchor_locked = Goods.objects.select_for_update().get(
                id=anchor_id, user=owner_user
            )

            if position == "before":
                prev_obj = _prev_item(anchor_locked, exclude_ids={current_locked.id})
                next_obj = anchor_locked
            else:  # after
                prev_obj = anchor_locked
                next_obj = _next_item(anchor_locked, exclude_ids={current_locked.id})

            new_order = _compute_new_order(prev_obj, next_obj)

            if new_order is None:
                # 无空隙，先重排再算一次
                _rebalance_around(anchor_locked, exclude_ids={current_locked.id})

                if position == "before":
                    prev_obj = _prev_item(anchor_locked, exclude_ids={current_locked.id})
                    next_obj = anchor_locked
                else:
                    prev_obj = anchor_locked
                    next_obj = _next_item(anchor_locked, exclude_ids={current_locked.id})

                new_order = _compute_new_order(prev_obj, next_obj)

                # 仍然为 None（极端情况）：再 fallback 一次
                if new_order is None:
                    new_order = anchor_locked.order + (
                        self.ORDER_STEP if position == "after" else -self.ORDER_STEP
                    )

            current_locked.order = new_order
            current_locked.save(update_fields=["order"])

        return Response(
            {
                "detail": "排序更新成功",
                "id": str(current_goods.id),
                "new_order": current_locked.order,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="upload-main-photo",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_main_photo(self, request, pk=None):
        """
        独立上传/更新主图接口，使用 multipart/form-data，字段名：main_photo
        """
        instance = self.get_object()
        main_photo = request.FILES.get("main_photo")

        if not main_photo:
            return Response(
                {"detail": "请通过 form-data 提供 main_photo 文件"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        compressed = compress_image(main_photo, max_size_kb=300)
        instance.main_photo = compressed or main_photo
        instance.save(update_fields=["main_photo", "updated_at"])

        serializer = GoodsDetailSerializer(
            instance, context=self.get_serializer_context()
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["post"],
        url_path="upload-additional-photos",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_additional_photos(self, request, pk=None):
        """
        独立上传/更新附加图片接口，使用 multipart/form-data，支持一次上传多张图片。
        字段名：
        - additional_photos（文件数组，可选）：可一次上传多张图片
        - photo_ids（整数数组，可选）：图片ID数组，用于更新已有图片
        - label（字符串，可选）：为本次上传的所有图片添加统一标签，例如："背板细节"、"瑕疵点"等
        
        使用场景：
        1. 创建新图片：只提供 additional_photos（不提供 photo_ids）
        2. 更新图片和标签：同时提供 additional_photos 和 photo_ids（数量必须一致）
        3. 只更新标签：只提供 photo_ids 和 label（不提供 additional_photos）
        """
        instance = self.get_object()
        additional_photos = request.FILES.getlist("additional_photos")
        photo_ids = request.data.getlist("photo_ids")  # 图片ID数组，用于更新
        label = request.data.get("label", "").strip()

        # 如果既没有提供图片文件，也没有提供 photo_ids，则返回错误
        if not additional_photos and not photo_ids:
            return Response(
                {"detail": "请提供 additional_photos 文件或 photo_ids 参数"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 如果同时提供了 photo_ids 和 additional_photos，数量必须一致
        if photo_ids and additional_photos and len(photo_ids) != len(additional_photos):
            return Response(
                {"detail": "photo_ids 数量必须与 additional_photos 数量一致"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 情况1：只更新 label（提供 photo_ids，但不提供图片文件）
        if photo_ids and not additional_photos:
            updated_images = []
            for photo_id_str in photo_ids:
                try:
                    photo_id = int(photo_id_str)
                    guzi_image = GuziImage.objects.get(id=photo_id, guzi=instance)
                    # 只更新标签
                    if label:
                        guzi_image.label = label
                    else:
                        guzi_image.label = None
                    guzi_image.save()
                    updated_images.append(guzi_image)
                except (GuziImage.DoesNotExist, ValueError):
                    return Response(
                        {"detail": f"图片 ID {photo_id_str} 不存在或不属于该谷子"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            
            # 更新谷子的 updated_at 时间戳
            instance.save(update_fields=["updated_at"])
            serializer = GoodsDetailSerializer(
                instance, context=self.get_serializer_context()
            )
            return Response(serializer.data, status=status.HTTP_200_OK)

        # 情况2：创建新图片或同时更新图片和 label
        updated_images = []
        for idx, photo in enumerate(additional_photos):
            compressed = compress_image(photo, max_size_kb=300)
            image_file = compressed or photo
            
            # 如果提供了 photo_id，则更新；否则创建新图片
            if photo_ids and idx < len(photo_ids):
                try:
                    photo_id = int(photo_ids[idx])
                    guzi_image = GuziImage.objects.get(id=photo_id, guzi=instance)
                    # 更新图片和标签
                    guzi_image.image = image_file
                    if label:
                        guzi_image.label = label
                    else:
                        guzi_image.label = None
                    guzi_image.save()
                    updated_images.append(guzi_image)
                except (GuziImage.DoesNotExist, ValueError):
                    return Response(
                        {"detail": f"图片 ID {photo_ids[idx]} 不存在或不属于该谷子"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                # 创建新图片
                guzi_image = GuziImage.objects.create(
                    guzi=instance,
                    image=image_file,
                    label=label if label else None,
                )
                updated_images.append(guzi_image)

        # 更新谷子的 updated_at 时间戳
        instance.save(update_fields=["updated_at"])

        serializer = GoodsDetailSerializer(
            instance, context=self.get_serializer_context()
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["delete"],
        url_path="additional-photos/(?P<photo_id>[^/.]+)",
    )
    def delete_additional_photo(self, request, pk=None, photo_id=None):
        """
        删除单张附加图片接口
        URL: /api/goods/{id}/additional-photos/{photo_id}/
        """
        instance = self.get_object()
        try:
            photo_id = int(photo_id)
            guzi_image = GuziImage.objects.get(id=photo_id, guzi=instance)
            guzi_image.delete()
        except (GuziImage.DoesNotExist, ValueError):
            return Response(
                {"detail": "附加图片不存在或不属于该谷子"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 更新谷子的 updated_at 时间戳
        instance.save(update_fields=["updated_at"])

        serializer = GoodsDetailSerializer(
            instance, context=self.get_serializer_context()
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["delete"],
        url_path="additional-photos",
    )
    def delete_additional_photos(self, request, pk=None):
        """
        批量删除附加图片接口
        URL: /api/goods/{id}/additional-photos/?photo_ids=10,11,12
        查询参数：photo_ids（整数数组，必填），多个ID用逗号分隔
        """
        instance = self.get_object()
        photo_ids_param = request.query_params.get("photo_ids", "").strip()

        if not photo_ids_param:
            return Response(
                {"detail": "请提供 photo_ids 查询参数，多个ID用逗号分隔，例如：?photo_ids=10,11,12"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # 解析 photo_ids
            photo_ids = [int(pid.strip()) for pid in photo_ids_param.split(",") if pid.strip()]
            if not photo_ids:
                return Response(
                    {"detail": "photo_ids 参数格式错误，请使用逗号分隔的整数ID"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # 查询并删除图片
            guzi_images = GuziImage.objects.filter(id__in=photo_ids, guzi=instance)
            deleted_count = guzi_images.count()

            # 检查是否有不存在的图片
            if deleted_count != len(photo_ids):
                found_ids = set(guzi_images.values_list("id", flat=True))
                missing_ids = [pid for pid in photo_ids if pid not in found_ids]
                return Response(
                    {"detail": f"以下图片ID不存在或不属于该谷子: {missing_ids}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            guzi_images.delete()

            # 更新谷子的 updated_at 时间戳
            instance.save(update_fields=["updated_at"])

            serializer = GoodsDetailSerializer(
                instance, context=self.get_serializer_context()
            )
            return Response(serializer.data, status=status.HTTP_200_OK)

        except ValueError:
            return Response(
                {"detail": "photo_ids 参数格式错误，请使用逗号分隔的整数ID"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        """
        统计图表数据接口（用于前端 dashboard / 图表展示）。

        - 复用 list 的过滤/搜索能力（GoodsFilter + SearchFilter），包括：
          ip / category(树形) / location(树形) / theme / status / status__in / is_official / character / search
        - 额外支持时间范围（purchase_date 为主）：
          ?purchase_start=YYYY-MM-DD&purchase_end=YYYY-MM-DD
          ?created_start=YYYY-MM-DD&created_end=YYYY-MM-DD
        - 支持 topN 与趋势粒度：
          ?top=10&group_by=month|week|day
        """

        def _parse_int(val: str | None, default: int) -> int:
            try:
                n = int(val) if val is not None and str(val).strip() != "" else default
                return max(1, min(n, 50))  # 避免过大 topN
            except Exception:
                return default

        def _parse_date(val: str | None) -> datetime.date | None:
            if not val:
                return None
            try:
                return datetime.date.fromisoformat(val)
            except Exception:
                return None

        def _choice_map(choices: tuple[tuple[object, str], ...]) -> dict[object, str]:
            return {k: v for k, v in choices}

        top_n = _parse_int(request.query_params.get("top"), default=10)
        group_by = (request.query_params.get("group_by") or "month").lower().strip()
        if group_by not in ("month", "week", "day"):
            group_by = "month"

        purchase_start = _parse_date(request.query_params.get("purchase_start"))
        purchase_end = _parse_date(request.query_params.get("purchase_end"))
        created_start = _parse_date(request.query_params.get("created_start"))
        created_end = _parse_date(request.query_params.get("created_end"))

        qs = self.filter_queryset(self.get_queryset())

        # 额外时间范围过滤（不影响其他维度）
        if purchase_start:
            qs = qs.filter(purchase_date__gte=purchase_start)
        if purchase_end:
            qs = qs.filter(purchase_date__lte=purchase_end)
        if created_start:
            qs = qs.filter(created_at__date__gte=created_start)
        if created_end:
            qs = qs.filter(created_at__date__lte=created_end)

        zero = Value(Decimal("0.00"))
        value_expr = ExpressionWrapper(
            F("quantity") * Coalesce(F("price"), zero),
            output_field=DecimalField(max_digits=20, decimal_places=2),
        )

        # 概览卡片（overview）
        overview = qs.aggregate(
            goods_count=Count("id", distinct=True),
            quantity_sum=Coalesce(Sum("quantity"), Value(0)),
            # 估算总金额：quantity * price（price 为空按 0 计）
            value_sum=Coalesce(Sum(value_expr), zero),
            with_price_count=Count("id", filter=Q(price__isnull=False), distinct=True),
            missing_price_count=Count("id", filter=Q(price__isnull=True), distinct=True),
            with_purchase_date_count=Count(
                "id", filter=Q(purchase_date__isnull=False), distinct=True
            ),
            missing_purchase_date_count=Count(
                "id", filter=Q(purchase_date__isnull=True), distinct=True
            ),
            with_location_count=Count("id", filter=Q(location__isnull=False), distinct=True),
            missing_location_count=Count(
                "id", filter=Q(location__isnull=True), distinct=True
            ),
            with_main_photo_count=Count(
                "id", filter=Q(main_photo__isnull=False), distinct=True
            ),
            missing_main_photo_count=Count(
                "id", filter=Q(main_photo__isnull=True), distinct=True
            ),
        )

        status_label_map = _choice_map(Goods.STATUS_CHOICES)
        subject_type_label_map = _choice_map(getattr(Goods.ip.field.related_model, "SUBJECT_TYPE_CHOICES", ()))  # type: ignore[attr-defined]

        # 分布：状态 / 官非 / 品类 / IP / 位置
        status_dist = list(
            qs.values("status")
            .annotate(goods_count=Count("id", distinct=True), quantity_sum=Sum("quantity"))
            .order_by("-goods_count")
        )
        for item in status_dist:
            item["label"] = status_label_map.get(item["status"], item["status"])

        official_dist = list(
            qs.values("is_official")
            .annotate(goods_count=Count("id", distinct=True), quantity_sum=Sum("quantity"))
            .order_by("-goods_count")
        )
        for item in official_dist:
            item["label"] = "官谷" if item["is_official"] else "同人/非官谷"

        category_top = list(
            qs.values("category_id", "category__name", "category__path_name", "category__color_tag")
            .annotate(
                goods_count=Count("id", distinct=True),
                quantity_sum=Sum("quantity"),
                value_sum=Coalesce(Sum(value_expr), zero),
            )
            .order_by("-goods_count")[:top_n]
        )

        ip_top = list(
            qs.values("ip_id", "ip__name", "ip__subject_type")
            .annotate(
                goods_count=Count("id", distinct=True),
                quantity_sum=Sum("quantity"),
                value_sum=Coalesce(Sum(value_expr), zero),
            )
            .order_by("-goods_count")[:top_n]
        )
        for item in ip_top:
            st = item.get("ip__subject_type")
            item["subject_type_label"] = subject_type_label_map.get(st, None)

        location_top = list(
            qs.values("location_id", "location__name", "location__path_name")
            .annotate(
                goods_count=Count("id", distinct=True),
                quantity_sum=Sum("quantity"),
                value_sum=Coalesce(Sum(value_expr), zero),
            )
            .order_by("-goods_count")[:top_n]
        )

        # 多对多：角色 TopN（按“包含该角色的商品数”计）
        character_top = list(
            qs.values("characters__id", "characters__name", "characters__ip__id", "characters__ip__name")
            .annotate(
                goods_count=Count("id", distinct=True),
                quantity_sum=Sum("quantity"),
                value_sum=Coalesce(Sum(value_expr), zero),
            )
            .order_by("-goods_count")[:top_n]
        )

        # IP 作品类型分布（适合饼图/堆叠柱状图）
        ip_subject_type_dist = list(
            qs.values("ip__subject_type")
            .annotate(goods_count=Count("id", distinct=True), quantity_sum=Sum("quantity"))
            .order_by("-goods_count")
        )
        for item in ip_subject_type_dist:
            st = item.get("ip__subject_type")
            item["label"] = subject_type_label_map.get(st, "未知")

        # 趋势：按 purchase_date（主）与 created_at（辅助）
        # 对于 SQLite，当 group_by=day 时，使用 Cast 而不是 TruncDate，避免 django_datetime_cast_date 函数的问题
        is_sqlite = connection.vendor == 'sqlite'
        
        if group_by == "month":
            trunc_purchase = TruncMonth("purchase_date")
            trunc_created = TruncMonth("created_at")
        elif group_by == "week":
            trunc_purchase = TruncWeek("purchase_date")
            trunc_created = TruncWeek("created_at")
        else:
            # SQLite 的 TruncDate 使用 django_datetime_cast_date 函数，可能有 NULL 值处理问题
            # 对于 DateField (purchase_date)，使用 Cast 来转换为日期类型，更安全
            # 对于 DateTimeField (created_at)，仍然使用 TruncDate，因为它可能不会有问题
            if is_sqlite:
                trunc_purchase = Cast("purchase_date", DateField())
                trunc_created = TruncDate("created_at")  # DateTimeField 使用 TruncDate
            else:
                trunc_purchase = TruncDate("purchase_date")
                trunc_created = TruncDate("created_at")

        # 先过滤掉 NULL 值，然后再进行 annotate，避免 SQLite 的 TruncDate 函数接收到 NULL 值
        # 创建一个新的 queryset，显式移除默认排序，避免 SQLite 的 date() 函数接收到 NULL 值
        # 使用 Goods.objects 而不是 qs，避免继承默认排序和复杂的 JOIN
        # 显式调用 order_by() 来移除模型的默认排序
        purchase_trend_qs = (
            Goods.objects
            .filter(purchase_date__isnull=False)
            .filter(id__in=qs.values_list('id', flat=True))  # 应用之前的过滤条件
            .order_by()  # 显式移除默认排序
        )
        
        purchase_trend = list(
            purchase_trend_qs
            .annotate(bucket=trunc_purchase)
            .values("bucket")
            .annotate(
                goods_count=Count("id", distinct=True),
                quantity_sum=Sum("quantity"),
                value_sum=Coalesce(Sum(value_expr), zero),
            )
            .order_by("bucket")
        )
        for item in purchase_trend:
            # JSON 友好化：datetime/date -> ISO 字符串
            b = item.get("bucket")
            item["bucket"] = b.isoformat() if b else None

        created_trend = list(
            qs.annotate(bucket=trunc_created)
            .values("bucket")
            .annotate(
                goods_count=Count("id", distinct=True),
                quantity_sum=Sum("quantity"),
            )
            .order_by("bucket")
        )
        for item in created_trend:
            b = item.get("bucket")
            item["bucket"] = b.isoformat() if b else None

        payload = {
            "meta": {
                "top": top_n,
                "group_by": group_by,
                "purchase_start": purchase_start.isoformat() if purchase_start else None,
                "purchase_end": purchase_end.isoformat() if purchase_end else None,
                "created_start": created_start.isoformat() if created_start else None,
                "created_end": created_end.isoformat() if created_end else None,
            },
            "overview": overview,
            "distributions": {
                "status": status_dist,
                "is_official": official_dist,
                "ip_subject_type": ip_subject_type_dist,
                "category_top": category_top,
                "ip_top": ip_top,
                "character_top": character_top,
                "location_top": location_top,
            },
            "trends": {
                "purchase_date": purchase_trend,
                "created_at": created_trend,
            },
        }

        return Response(payload, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="similar-random")
    def similar_random(self, request):
        """
        相似谷子随机展示接口

        返回按相似度分组的谷子列表，而非完全随机。
        通过多维度加权评分算法将相似的谷子整理在一起，提供更好的浏览体验。

        查询参数：
        - 所有标准过滤器（ip, category, theme, status等）
        - seed_strategy: 种子选择策略（diverse/popular/recent，默认diverse）
        - page, page_size: 标准分页参数

        响应格式与列表接口相同。
        """
        # 1. 获取过滤后的queryset并优化查询
        qs = self.filter_queryset(self.get_queryset())

        # 边界情况：谷子太少，直接随机打乱
        total_count = qs.count()
        if total_count < 18:
            goods_list = list(qs)
            random.shuffle(goods_list)
            page = self.paginate_queryset(goods_list)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            serializer = self.get_serializer(goods_list, many=True)
            return Response(serializer.data)

        # 2. 检查缓存中的现有排序
        cache_key = self._get_similarity_cache_key(request)
        cached_ids = cache.get(cache_key)

        if cached_ids:
            # 使用缓存的排序
            ordered_goods = self._order_by_ids(qs, cached_ids)
        else:
            # 计算新的相似度排序
            ordered_goods = self._compute_similarity_ordering(qs, request)
            # 缓存ID列表（5分钟TTL）
            cache.set(cache_key, [str(g.id) for g in ordered_goods], timeout=300)

        # 3. 分页并返回
        page = self.paginate_queryset(ordered_goods)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(ordered_goods, many=True)
        return Response(serializer.data)

    def _get_similarity_cache_key(self, request):
        """
        生成缓存键（用户ID + 过滤器哈希）

        Args:
            request: HTTP请求对象

        Returns:
            str: 缓存键
        """
        user_id = request.user.id
        filter_params = {
            'ip': request.query_params.get('ip'),
            'category': request.query_params.get('category'),
            'status': request.query_params.get('status'),
            'theme': request.query_params.get('theme'),
            'search': request.query_params.get('search'),
            'seed_strategy': request.query_params.get('seed_strategy', 'diverse'),
        }
        # 移除None值
        filter_params = {k: v for k, v in filter_params.items() if v}
        filter_hash = hashlib.md5(str(sorted(filter_params.items())).encode()).hexdigest()
        return f"similar_random:{user_id}:{filter_hash}"

    def _compute_similarity_ordering(self, qs, request):
        """
        计算基于相似度的排序

        Args:
            qs: 查询集
            request: HTTP请求对象

        Returns:
            list: 排序后的谷子列表
        """
        # 预加载所有关联数据
        goods_list = list(
            qs.select_related('ip', 'category', 'theme', 'location')
              .prefetch_related('characters')
        )

        # 获取种子策略
        seed_strategy = request.query_params.get('seed_strategy', 'diverse')

        # 初始化组件
        calculator = GoodsSimilarityCalculator()
        selector = SeedSelector()
        builder = SimilarityGroupBuilder(calculator)

        # 选择种子
        seeds = selector.select_seeds(goods_list, strategy=seed_strategy)

        # 构建分组
        ordered_goods = builder.build_groups(seeds, goods_list)

        # 强制多样性
        ordered_goods = builder.enforce_variety(ordered_goods)

        return ordered_goods

    def _order_by_ids(self, qs, id_list):
        """
        按ID列表排序查询集

        Args:
            qs: 查询集
            id_list: ID列表

        Returns:
            list: 排序后的谷子列表
        """
        # 创建ID到位置的映射
        id_to_position = {str(id_val): pos for pos, id_val in enumerate(id_list)}

        # 获取谷子并按位置排序
        goods_dict = {str(g.id): g for g in qs}
        ordered_goods = []
        for id_val in id_list:
            if id_val in goods_dict:
                ordered_goods.append(goods_dict[id_val])

        return ordered_goods
