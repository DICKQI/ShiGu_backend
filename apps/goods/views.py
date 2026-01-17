from django.db.models import Count
from django_filters import FilterSet, ModelMultipleChoiceFilter, NumberFilter, CharFilter, BaseInFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters as drf_filters, status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from .bgm_service import search_ip_characters
from .models import Category, Character, Goods, GuziImage, IP
from .serializers import (
    BGMCreateCharactersRequestSerializer,
    BGMSearchRequestSerializer,
    BGMSearchResponseSerializer,
    CategorySimpleSerializer,
    CharacterSimpleSerializer,
    GoodsDetailSerializer,
    GoodsListSerializer,
    IPDetailSerializer,
    IPSimpleSerializer,
)
from .utils import compress_image
class GoodsFilter(FilterSet):
    """谷子过滤集，正确处理多对多字段characters"""
    
    ip = NumberFilter(field_name="ip", lookup_expr="exact")
    category = NumberFilter(field_name="category", lookup_expr="exact")
    location = NumberFilter(field_name="location", lookup_expr="exact")
    status = CharFilter(field_name="status", lookup_expr="exact")
    status__in = BaseInFilter(field_name="status", lookup_expr="in")
    
    # 单个角色筛选：?character=1387（精确匹配包含该角色的谷子）
    character = ModelMultipleChoiceFilter(
        field_name="characters",
        queryset=Character.objects.all(),
        conjoined=False,  # False表示"包含任意指定角色"（OR）
        help_text="单个角色ID，例如：?character=1387（包含该角色的谷子）"
    )
    
    class Meta:
        model = Goods
        fields = ["ip", "category", "location", "status", "character"]


class GoodsViewSet(viewsets.ModelViewSet):
    """
    谷子检索核心接口。

    - list: 高性能检索列表（瘦身字段），支持多维过滤 & 搜索。
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

    # 限流：专门给检索接口一个 scope，具体速率在 settings.REST_FRAMEWORK.THROTTLE_RATES 中配置
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "goods_search"
    parser_classes = (MultiPartParser, FormParser, JSONParser)

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

        serializer.save()

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


class IPViewSet(viewsets.ModelViewSet):
    """
    IP作品CRUD接口。

    - list: 获取所有IP作品列表（包含关键词）
    - retrieve: 获取单个IP作品详情（包含关键词）
    - create: 创建新IP作品（支持同时创建关键词）
    - update: 更新IP作品（支持同时更新关键词）
    - partial_update: 部分更新IP作品（支持同时更新关键词）
    - destroy: 删除IP作品
    - characters: 获取指定IP下的所有角色列表（/api/ips/{id}/characters/）
    """

    filter_backends = (DjangoFilterBackend, drf_filters.SearchFilter)
    search_fields = ("name", "keywords__value")
    filterset_fields = {
        "name": ["exact", "icontains"],
        "subject_type": ["exact", "in"],  # exact: 精确匹配，in: 多值筛选（逗号分隔）
    }

    def get_queryset(self):
        """优化查询，预加载关键词并统计角色数量"""
        return (
            IP.objects.all()
            .prefetch_related("keywords")
            .annotate(character_count=Count("characters"))
            .order_by("created_at")
        )

    def get_serializer_class(self):
        """根据操作类型选择序列化器"""
        if self.action in ("create", "update", "partial_update"):
            return IPDetailSerializer
        return IPSimpleSerializer

    @action(detail=True, methods=["get"], url_path="characters")
    def characters(self, request, pk=None):
        """
        获取指定IP下的所有角色列表
        URL: /api/ips/{id}/characters/
        """
        ip = self.get_object()
        characters = ip.characters.all().select_related("ip").order_by("created_at")
        serializer = CharacterSimpleSerializer(
            characters, many=True, context={"request": request}
        )
        return Response(serializer.data)


class CharacterViewSet(viewsets.ModelViewSet):
    """
    角色CRUD接口。

    - list: 获取所有角色列表，支持按IP过滤
    - retrieve: 获取单个角色详情
    - create: 创建新角色
    - update: 更新角色
    - partial_update: 部分更新角色
    - destroy: 删除角色
    """

    queryset = Character.objects.all().select_related("ip").order_by("created_at")
    serializer_class = CharacterSimpleSerializer
    filter_backends = (DjangoFilterBackend, drf_filters.SearchFilter)
    search_fields = ("name", "ip__name", "ip__keywords__value")
    filterset_fields = {
        "ip": ["exact"],
        "name": ["exact", "icontains"],
    }


class CategoryViewSet(viewsets.ModelViewSet):
    """
    品类CRUD接口。

    - list: 获取所有品类列表
    - retrieve: 获取单个品类详情
    - create: 创建新品类
    - update: 更新品类
    - partial_update: 部分更新品类
    - destroy: 删除品类
    """

    queryset = Category.objects.all().order_by("created_at")
    serializer_class = CategorySimpleSerializer
    filter_backends = (DjangoFilterBackend, drf_filters.SearchFilter)
    search_fields = ("name",)
    filterset_fields = {
        "name": ["exact", "icontains"],
    }


# ==================== BGM API 视图 ====================

@api_view(['POST'])
def bgm_search_characters(request):
    """
    搜索IP作品并获取角色列表
    
    POST /api/bgm/search-characters/
    
    请求体:
    {
        "ip_name": "崩坏：星穹铁道",
        "subject_type": 4  // 可选，作品类型：1=书籍, 2=动画, 3=音乐, 4=游戏, 6=三次元
    }
    
    响应:
    {
        "ip_name": "崩坏：星穹铁道",
        "characters": [
            {
                "name": "流萤",
                "relation": "主角",
                "avatar": "https://..."
            },
            ...
        ]
    }
    """
    serializer = BGMSearchRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    ip_name = serializer.validated_data['ip_name']
    subject_type = serializer.validated_data.get('subject_type')
    
    try:
        display_name, characters = search_ip_characters(ip_name, subject_type)
        
        if display_name is None:
            return Response(
                {"detail": f"未找到与 '{ip_name}' 相关的作品"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        response_data = {
            "ip_name": display_name,
            "characters": characters
        }
        
        response_serializer = BGMSearchResponseSerializer(data=response_data)
        response_serializer.is_valid(raise_exception=True)
        
        return Response(response_serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {"detail": f"搜索失败: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def bgm_create_characters(request):
    """
    根据角色列表创建IP和角色到数据库
    
    POST /api/bgm/create-characters/
    
    请求体:
    {
        "characters": [
            {
                "ip_name": "崩坏：星穹铁道",
                "character_name": "流萤"
            },
            {
                "ip_name": "崩坏：星穹铁道",
                "character_name": "花火"
            }
        ]
    }
    
    响应:
    {
        "created": 2,
        "skipped": 0,
        "details": [
            {
                "ip_name": "崩坏：星穹铁道",
                "character_name": "流萤",
                "status": "created",
                "ip_id": 1,
                "character_id": 1
            },
            ...
        ]
    }
    """
    serializer = BGMCreateCharactersRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    characters_data = serializer.validated_data['characters']
    
    created_count = 0
    skipped_count = 0
    details = []
    
    for char_data in characters_data:
        ip_name = char_data['ip_name']
        character_name = char_data['character_name']
        subject_type = char_data.get('subject_type')  # 可选字段
        avatar = char_data.get('avatar')  # 可选字段，头像URL
        
        try:
            # 获取或创建IP
            # 如果提供了 subject_type，在创建新 IP 时使用它
            ip_obj, ip_created = IP.objects.get_or_create(
                name=ip_name,
                defaults={'subject_type': subject_type} if subject_type else {}
            )
            # 如果 IP 已存在但 subject_type 为空，且提供了 subject_type，则更新它
            if not ip_created and ip_obj.subject_type is None and subject_type:
                ip_obj.subject_type = subject_type
                ip_obj.save(update_fields=['subject_type'])
            
            # 获取或创建角色（使用unique_together约束避免重复）
            character_obj, char_created = Character.objects.get_or_create(
                ip=ip_obj,
                name=character_name,
                defaults={'avatar': avatar.strip() if avatar and avatar.strip() else None} if avatar else {}
            )
            
            # 如果角色已存在，但提供了头像URL且角色当前没有头像，则更新头像
            if not char_created and avatar and avatar.strip():
                if not character_obj.avatar:
                    character_obj.avatar = avatar.strip()
                    character_obj.save(update_fields=['avatar'])
            
            if char_created:
                created_count += 1
                status_msg = "created"
            else:
                skipped_count += 1
                status_msg = "already_exists"
            
            details.append({
                "ip_name": ip_name,
                "character_name": character_name,
                "status": status_msg,
                "ip_id": ip_obj.id,
                "character_id": character_obj.id
            })
            
        except Exception as e:
            details.append({
                "ip_name": ip_name,
                "character_name": character_name,
                "status": "error",
                "error": str(e)
            })
    
    return Response({
        "created": created_count,
        "skipped": skipped_count,
        "details": details
    }, status=status.HTTP_200_OK)
