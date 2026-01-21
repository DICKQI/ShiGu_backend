"""
谷子（Goods）相关的序列化器
"""
from rest_framework import serializers

from ..models import Category, Character, Goods, GuziImage, IP
from ..utils import compress_image
from .category import CategorySimpleSerializer
from .character import CharacterSimpleSerializer
from .ip import IPSimpleSerializer


class GuziImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuziImage
        fields = ("id", "image", "label")

    def create(self, validated_data):
        """创建补充图片时自动压缩"""
        image = validated_data.get('image')
        if image:
            compressed_image = compress_image(image, max_size_kb=300)
            if compressed_image:
                validated_data['image'] = compressed_image
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """更新补充图片时自动压缩"""
        image = validated_data.get('image')
        if image:
            compressed_image = compress_image(image, max_size_kb=300)
            if compressed_image:
                validated_data['image'] = compressed_image
        return super().update(instance, validated_data)


class GoodsListSerializer(serializers.ModelSerializer):
    """
    列表用"瘦身"序列化器，仅返回检索页所需字段。
    """

    ip = IPSimpleSerializer(read_only=True)
    characters = CharacterSimpleSerializer(many=True, read_only=True)
    category = CategorySimpleSerializer(read_only=True)
    location_path = serializers.SerializerMethodField()

    class Meta:
        model = Goods
        fields = (
            "id",
            "name",
            "ip",
            "characters",
            "category",
            "location_path",
            "main_photo",
            "status",
            "quantity",
            "is_official",
            "order",  # 自定义排序值
        )

    def get_location_path(self, obj):
        if obj.location:
            return obj.location.path_name or obj.location.name
        return None


class GoodsDetailSerializer(serializers.ModelSerializer):
    """
    详情页序列化器，返回完整信息及补充图片。
    """

    ip = IPSimpleSerializer(read_only=True)
    ip_id = serializers.PrimaryKeyRelatedField(
        queryset=IP.objects.all(),
        source="ip",
        write_only=True,
        required=False,
        help_text="所属IP作品ID",
    )
    characters = CharacterSimpleSerializer(many=True, read_only=True)
    character_ids = serializers.PrimaryKeyRelatedField(
        queryset=Character.objects.all(),
        many=True,
        source="characters",
        write_only=True,
        required=False,
        help_text="关联角色ID列表，例如：[5, 6] 表示同时关联流萤和花火",
    )
    category = CategorySimpleSerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="category",
        write_only=True,
        required=False,
        help_text="品类ID",
    )
    location_path = serializers.SerializerMethodField()
    additional_photos = GuziImageSerializer(many=True, read_only=True)

    class Meta:
        model = Goods
        fields = (
            "id",
            "name",
            "ip_id",
            "ip",
            "character_ids",
            "characters",
            "category_id",
            "category",
            "location_path",
            "location",
            "main_photo",
            "quantity",
            "price",
            "purchase_date",
            "is_official",
            "status",
            "notes",
            "created_at",
            "updated_at",
            "additional_photos",
            "order",  # 自定义排序值
        )

    def get_location_path(self, obj):
        if obj.location:
            return obj.location.path_name or obj.location.name
        return None

    def validate(self, attrs):
        """
        保证创建时必填外键，更新时允许部分字段缺省。
        """
        if self.instance is None:
            required_fields = {
                "ip": "ip_id",
                "characters": "character_ids",
                "category": "category_id",
            }
            missing = [
                alias for key, alias in required_fields.items() if key not in attrs
            ]
            if missing:
                raise serializers.ValidationError(
                    {field: "创建时必填" for field in missing}
                )
            # 验证角色列表不为空
            if "characters" in attrs and not attrs["characters"]:
                raise serializers.ValidationError(
                    {"character_ids": "至少需要关联一个角色"}
                )
        return attrs

    def create(self, validated_data):
        """创建谷子时自动压缩主图并处理多对多关系"""
        # 提取多对多关系数据
        characters = validated_data.pop("characters", [])
        
        # 处理主图压缩
        main_photo = validated_data.get('main_photo')
        if main_photo:
            compressed_image = compress_image(main_photo, max_size_kb=300)
            if compressed_image:
                validated_data['main_photo'] = compressed_image
        
        # 创建谷子实例
        instance = super().create(validated_data)
        
        # 设置多对多关系
        if characters:
            instance.characters.set(characters)
        
        return instance

    def update(self, instance, validated_data):
        """更新谷子时自动压缩主图并处理多对多关系"""
        # 提取多对多关系数据
        characters = validated_data.pop("characters", None)
        
        # 处理主图压缩
        main_photo = validated_data.get('main_photo')
        if main_photo:
            compressed_image = compress_image(main_photo, max_size_kb=300)
            if compressed_image:
                validated_data['main_photo'] = compressed_image
        
        # 更新其他字段
        instance = super().update(instance, validated_data)
        
        # 更新多对多关系（如果提供了）
        if characters is not None:
            instance.characters.set(characters)
        
        return instance


class GoodsMoveSerializer(serializers.Serializer):
    """谷子排序移动请求序列化器"""

    anchor_id = serializers.UUIDField(
        required=True,
        help_text="锚点谷子ID（即要移动到哪个谷子的前面或后面）",
    )
    position = serializers.ChoiceField(
        choices=["before", "after"],
        required=True,
        help_text="移动位置：before(之前) / after(之后)",
    )
