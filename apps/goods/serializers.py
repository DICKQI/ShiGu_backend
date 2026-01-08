from rest_framework import serializers

from .models import Category, Character, Goods, GuziImage, IP, IPKeyword
from .utils import compress_image


class IPKeywordSerializer(serializers.ModelSerializer):
    """IP关键词序列化器"""

    class Meta:
        model = IPKeyword
        fields = ("id", "value")


class KeywordsField(serializers.Field):
    """自定义关键词字段：读取时返回对象数组，写入时接收字符串数组"""

    def to_representation(self, value):
        """读取时：返回关键词对象数组"""
        if value is None:
            return []
        # value是RelatedManager，需要调用all()获取查询集
        return [{"id": kw.id, "value": kw.value} for kw in value.all()]

    def to_internal_value(self, data):
        """写入时：接收字符串数组"""
        if data is None:
            return []
        if not isinstance(data, list):
            raise serializers.ValidationError("关键词必须是数组格式")
        # 去重、去空、去除前后空格
        keywords = [str(item).strip() for item in data if item and str(item).strip()]
        # 去重（保持顺序）
        seen = set()
        result = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                result.append(kw)
        return result


class IPSimpleSerializer(serializers.ModelSerializer):
    """IP简单序列化器（用于列表和嵌套显示）"""

    keywords = IPKeywordSerializer(many=True, read_only=True, help_text="IP关键词列表")
    character_count = serializers.SerializerMethodField(help_text="该IP下的角色数量")

    class Meta:
        model = IP
        fields = ("id", "name", "keywords", "character_count")

    def get_character_count(self, obj):
        """统计IP下的角色数量"""
        # 如果使用了annotate预计算，直接使用结果
        if hasattr(obj, 'character_count'):
            return obj.character_count
        # 否则查询数据库
        return obj.characters.count()


class IPDetailSerializer(serializers.ModelSerializer):
    """IP详情序列化器（用于创建和更新，支持关键词操作）"""

    keywords = KeywordsField(required=False, allow_null=True, help_text="关键词列表，例如：['星铁', '崩铁', 'HSR']")

    class Meta:
        model = IP
        fields = ("id", "name", "keywords")

    def create(self, validated_data):
        """创建IP时同时创建关键词"""
        keywords_data = validated_data.pop("keywords", [])
        ip = IP.objects.create(**validated_data)

        # 创建关键词
        if keywords_data:
            for keyword_value in keywords_data:
                if keyword_value and keyword_value.strip():  # 忽略空字符串
                    IPKeyword.objects.get_or_create(ip=ip, value=keyword_value.strip())

        return ip

    def update(self, instance, validated_data):
        """更新IP时同步更新关键词"""
        keywords_data = validated_data.pop("keywords", None)

        # 更新IP基本信息
        instance.name = validated_data.get("name", instance.name)
        instance.save()

        # 如果提供了keywords字段，则更新关键词
        if keywords_data is not None:
            # 获取当前关键词值集合
            existing_keywords = set(instance.keywords.values_list("value", flat=True))
            new_keywords = {kw.strip() for kw in keywords_data if kw and kw.strip()}

            # 删除不再存在的关键词
            to_delete = existing_keywords - new_keywords
            if to_delete:
                instance.keywords.filter(value__in=to_delete).delete()

            # 添加新关键词
            to_add = new_keywords - existing_keywords
            for keyword_value in to_add:
                IPKeyword.objects.get_or_create(ip=instance, value=keyword_value)

        return instance


class CharacterSimpleSerializer(serializers.ModelSerializer):
    ip = IPSimpleSerializer(read_only=True)
    ip_id = serializers.PrimaryKeyRelatedField(
        queryset=IP.objects.all(),
        source="ip",
        write_only=True,
        required=True,
        help_text="所属IP作品ID",
    )

    class Meta:
        model = Character
        fields = ("id", "name", "ip", "ip_id", "avatar", "gender")
        extra_kwargs = {
            "avatar": {"read_only": False, "required": False},
        }
    
    def to_representation(self, instance):
        """构建完整的头像URL"""
        representation = super().to_representation(instance)
        if instance.avatar:
            request = self.context.get('request')
            if request:
                representation['avatar'] = request.build_absolute_uri(instance.avatar.url)
            else:
                representation['avatar'] = instance.avatar.url
        return representation

    def create(self, validated_data):
        """创建角色时自动压缩头像"""
        avatar = validated_data.get('avatar')
        if avatar:
            compressed_image = compress_image(avatar, max_size_kb=300)
            if compressed_image:
                validated_data['avatar'] = compressed_image
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """更新角色时自动压缩头像"""
        avatar = validated_data.get('avatar')
        if avatar:
            compressed_image = compress_image(avatar, max_size_kb=300)
            if compressed_image:
                validated_data['avatar'] = compressed_image
        return super().update(instance, validated_data)


class CategorySimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name")


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


# ==================== BGM API 序列化器 ====================

class BGMSearchRequestSerializer(serializers.Serializer):
    """BGM搜索IP角色请求序列化器"""
    ip_name = serializers.CharField(
        max_length=200,
        required=True,
        help_text="IP作品名称，例如：崩坏：星穹铁道"
    )


class BGMCharacterSerializer(serializers.Serializer):
    """BGM角色信息序列化器（用于搜索接口返回）"""
    name = serializers.CharField(help_text="角色名称")
    relation = serializers.CharField(help_text="角色关系，如：主角、配角、客串")
    avatar = serializers.CharField(allow_blank=True, help_text="角色头像URL")


class BGMSearchResponseSerializer(serializers.Serializer):
    """BGM搜索IP角色响应序列化器"""
    ip_name = serializers.CharField(help_text="IP作品名称")
    characters = BGMCharacterSerializer(many=True, help_text="角色列表")


class BGMCreateCharacterRequestSerializer(serializers.Serializer):
    """BGM创建角色请求序列化器"""
    ip_name = serializers.CharField(
        max_length=100,
        required=True,
        help_text="IP作品名称"
    )
    character_name = serializers.CharField(
        max_length=100,
        required=True,
        help_text="角色名称"
    )


class BGMCreateCharactersRequestSerializer(serializers.Serializer):
    """BGM批量创建角色请求序列化器"""
    characters = BGMCreateCharacterRequestSerializer(
        many=True,
        required=True,
        help_text="角色列表，每个角色包含ip_name和character_name"
    )


