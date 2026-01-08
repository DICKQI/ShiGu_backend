from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from .bgm_service import search_ip_characters
from .models import Category, Character, Goods, IP
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
        filters.SearchFilter,
    )

    # 复合过滤：/api/goods/?ip=1&characters=5&category=2&status=in_cabinet
    # 支持多角色筛选：/api/goods/?characters__in=5,6 表示包含任意角色的谷子
    # 支持多状态筛选：/api/goods/?status__in=in_cabinet,sold
    filterset_fields = {
        "ip": ["exact"],
        "characters": ["exact", "in"],  # exact: 精确匹配，in: 包含任意指定角色
        "category": ["exact"],
        # status 支持 exact 和 in，in 用 status__in 参数，值用英文逗号分隔
        "status": ["exact", "in"],
        "location": ["exact"],
    }

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

    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    search_fields = ("name", "keywords__value")
    filterset_fields = {
        "name": ["exact", "icontains"],
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
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
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
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
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
        "ip_name": "崩坏：星穹铁道"
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
    
    try:
        display_name, characters = search_ip_characters(ip_name)
        
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
        
        try:
            # 获取或创建IP
            ip_obj, ip_created = IP.objects.get_or_create(name=ip_name)
            
            # 获取或创建角色（使用unique_together约束避免重复）
            character_obj, char_created = Character.objects.get_or_create(
                ip=ip_obj,
                name=character_name
            )
            
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
