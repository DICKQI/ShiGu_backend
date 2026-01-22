"""
谷子（Goods）相关的视图和过滤器
"""
from django.db import transaction
from django.db.models import Count, Min, Q
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

from ..models import Category, Character, Goods, GuziImage
from apps.location.models import StorageNode
from ..serializers import (
    GoodsDetailSerializer,
    GoodsListSerializer,
    GoodsMoveSerializer,
)
from ..utils import compress_image


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
        fields = ["ip", "category", "location", "status", "status__in", "is_official", "character"]

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
            node = StorageNode.objects.get(pk=value)
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
        .select_related("ip", "category", "location")
        .prefetch_related("characters__ip", "additional_photos")
    )

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
            .select_related("ip", "category", "location")
            .prefetch_related("characters__ip", "additional_photos")
        )
        return qs

    def perform_create(self, serializer):
        """
        简单幂等性：避免重复录入完全相同的谷子。

        规则示例（可按业务后续调整）：
        - 同一 IP + 相同角色集合（顺序无关） + 名称 + 入手日期 + 单价 认为是同一条资产。
        """

        validated = serializer.validated_data
        ip = validated.get("ip")
        characters = validated.get("characters", [])
        name = validated.get("name")
        purchase_date = validated.get("purchase_date")
        price = validated.get("price")

        # 构建查询条件
        query = Goods.objects.filter(
            ip=ip,
            name=name,
            purchase_date=purchase_date,
            price=price,
        )

        # 如果有角色数据，检查角色集合是否相同
        if characters:
            # 将角色ID列表排序后转为元组，用于比较
            character_ids = sorted([c.id for c in characters])
            # 过滤出角色数量相同的谷子
            query = query.annotate(character_count=Count("characters")).filter(
                character_count=len(character_ids)
            )

            # 遍历查询结果，检查角色集合是否完全相同
            for candidate in query.prefetch_related("characters"):
                candidate_ids = sorted([c.id for c in candidate.characters.all()])
                if candidate_ids == character_ids:
                    # 找到了完全匹配的实例
                    serializer.instance = candidate
                    return
        else:
            # 没有角色数据时，检查是否有完全相同的记录（不含角色）
            if query.exists():
                # 如果存在完全相同的记录（包括角色也为空），返回该实例
                candidate = query.first()
                if candidate.characters.count() == 0:
                    serializer.instance = candidate
                    return

        # 为新建的谷子分配稀疏的 order：当前最小值 - ORDER_STEP，让新建的谷子排在最前面
        min_order = Goods.objects.aggregate(min_order=Min("order")).get("min_order")
        next_order = (min_order or 0) - self.ORDER_STEP
        serializer.save(order=next_order)

    @action(detail=True, methods=["post"], url_path="move")
    def move(self, request, pk=None):
        """
        移动谷子排序接口：
        将当前谷子移动到指定锚点谷子的前面或后面。
        """
        current_goods = self.get_object()
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
                anchor_goods = Goods.objects.select_for_update().get(id=anchor_id)
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
                Goods.objects.exclude(id__in=exclude_ids)
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
                Goods.objects.exclude(id__in=exclude_ids)
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
                Goods.objects.exclude(id__in=exclude_ids | {center.id})
                .filter(
                    Q(order__lt=center.order)
                    | Q(order=center.order, created_at__gt=center.created_at)
                    | Q(order=center.order, created_at=center.created_at, id__gt=center.id)
                )
                .order_by("-order", "created_at", "-id")[:window]
            )
            after_qs = (
                Goods.objects.exclude(id__in=exclude_ids | {center.id})
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
            current_locked = Goods.objects.select_for_update().get(
                id=current_goods.id
            )
            anchor_locked = Goods.objects.select_for_update().get(id=anchor_id)

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
