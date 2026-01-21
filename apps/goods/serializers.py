import os
from uuid import uuid4
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
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


class AvatarField(serializers.Field):
    """
    自定义头像字段：
    - 支持文件上传（保存到服务器并存储相对路径）
    - 支持URL字符串（直接存储）
    - 返回时：本地路径返回完整URL，外部URL直接返回
    """
    
    def to_representation(self, value):
        """读取时：本地路径返回完整URL，外部URL直接返回"""
        if not value:
            return None
        
        # 判断是否为外部URL（以http://或https://开头）
        if value.startswith('http://') or value.startswith('https://'):
            return value
        
        # 本地路径，构建完整URL
        request = self.context.get('request')
        if request:
            # 使用MEDIA_URL构建完整URL
            from django.conf import settings
            if value.startswith(settings.MEDIA_URL):
                return request.build_absolute_uri(value)
            else:
                # 确保路径以MEDIA_URL开头
                media_url = settings.MEDIA_URL
                if not value.startswith(media_url):
                    value = media_url + value.lstrip('/')
                return request.build_absolute_uri(value)
        else:
            # 没有request对象时，返回原始值
            from django.conf import settings
            if not value.startswith('http'):
                media_url = settings.MEDIA_URL
                if not value.startswith(media_url):
                    value = media_url + value.lstrip('/')
            return value
    
    def to_internal_value(self, data):
        """写入时：处理文件上传或URL字符串"""
        if data is None or data == '':
            return None
        
        # 如果是文件上传对象
        if hasattr(data, 'read'):
            # 压缩图片
            compressed_image = compress_image(data, max_size_kb=300) or data
            
            # 保存文件到服务器
            upload_to = "characters/"
            
            # 获取原始文件名
            original_name = compressed_image.name if hasattr(compressed_image, 'name') else 'avatar.jpg'
            file_name = os.path.basename(original_name)
            
            # 生成唯一文件名（避免覆盖）
            name, ext = os.path.splitext(file_name)
            unique_name = f"{name}_{uuid4().hex[:8]}{ext}"
            
            # 构建保存路径
            file_path = os.path.join(upload_to, unique_name)
            
            # 保存文件
            saved_path = default_storage.save(file_path, compressed_image)
            
            # 返回相对路径（相对于MEDIA_ROOT）
            return saved_path
        
        # 如果是URL字符串
        if isinstance(data, str):
            data = data.strip()
            if not data:
                return None
            
            # 如果是外部URL，直接返回
            if data.startswith('http://') or data.startswith('https://'):
                return data
            
            # 如果是相对路径，确保格式正确
            # 移除开头的斜杠和MEDIA_URL前缀（如果存在）
            from django.conf import settings
            if data.startswith(settings.MEDIA_URL):
                data = data[len(settings.MEDIA_URL):]
            data = data.lstrip('/')
            
            return data
        
        raise serializers.ValidationError("头像必须是文件或URL字符串")


class IPSimpleSerializer(serializers.ModelSerializer):
    """IP简单序列化器（用于列表和嵌套显示）"""

    keywords = IPKeywordSerializer(many=True, read_only=True, help_text="IP关键词列表")
    character_count = serializers.SerializerMethodField(help_text="该IP下的角色数量")

    class Meta:
        model = IP
        fields = ("id", "name", "subject_type", "keywords", "character_count")

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
        fields = ("id", "name", "subject_type", "keywords")

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
        # 更新 subject_type（如果提供了）
        if "subject_type" in validated_data:
            instance.subject_type = validated_data.get("subject_type")
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
    avatar = AvatarField(
        required=False,
        allow_null=True,
        help_text="角色头像。可以是文件上传（multipart/form-data）或URL字符串（如 https://example.com/avatar.jpg）",
    )

    class Meta:
        model = Character
        fields = ("id", "name", "ip", "ip_id", "avatar", "gender")


class CategorySimpleSerializer(serializers.ModelSerializer):
    """品类简单序列化器（用于列表和嵌套显示）"""
    parent = serializers.PrimaryKeyRelatedField(read_only=True, help_text="父级品类ID")
    
    class Meta:
        model = Category
        fields = ("id", "name", "parent", "path_name", "color_tag", "order")


class CategoryTreeSerializer(serializers.ModelSerializer):
    """
    品类树一次性下发用序列化器。
    前端可根据 parent/id 在内存中自行组装为树结构。
    """
    
    class Meta:
        model = Category
        fields = ("id", "name", "parent", "path_name", "color_tag", "order")


class CategoryOrderItemSerializer(serializers.Serializer):
    """品类排序项序列化器（用于批量更新排序）"""
    id = serializers.IntegerField(help_text="品类ID")
    order = serializers.IntegerField(help_text="排序值，值越小越靠前")


class CategoryBatchUpdateOrderSerializer(serializers.Serializer):
    """批量更新品类排序序列化器"""
    items = CategoryOrderItemSerializer(
        many=True,
        required=True,
        help_text="品类排序项列表，每个项包含id和order字段"
    )
    
    def validate_items(self, value):
        """验证items列表"""
        if not value:
            raise serializers.ValidationError("items列表不能为空")
        
        # 检查是否有重复的ID
        ids = [item['id'] for item in value]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("items列表中不能有重复的品类ID")
        
        return value


class CategoryDetailSerializer(serializers.ModelSerializer):
    """品类详情序列化器（用于创建和更新，支持树形结构）"""
    
    path_name = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="完整路径，如果不提供则根据父节点自动生成，例如：周边/吧唧/圆形吧唧",
    )
    
    class Meta:
        model = Category
        fields = ("id", "name", "parent", "path_name", "color_tag", "order")
    
    def create(self, validated_data):
        """创建品类时，如果未提供 path_name，则根据父节点自动生成"""
        path_name = validated_data.get("path_name")
        parent = validated_data.get("parent")
        name = validated_data.get("name")
        
        # 如果 path_name 为空或未提供，则根据父节点自动生成
        if not path_name:
            if parent:
                # 有父节点：父节点路径 + "/" + 当前节点名称
                parent_path = parent.path_name or parent.name
                path_name = f"{parent_path}/{name}"
            else:
                # 无父节点（根节点）：直接使用节点名称
                path_name = name
        
        validated_data["path_name"] = path_name
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """更新品类时，如果父节点或名称改变，自动更新 path_name"""
        parent = validated_data.get("parent", instance.parent)
        name = validated_data.get("name", instance.name)
        path_name = validated_data.get("path_name")
        
        # 如果用户明确提供了 path_name，使用用户提供的值
        # 如果未提供 path_name，但父节点或名称改变了，需要重新生成
        if path_name is None:
            # 检查是否需要重新生成 path_name
            parent_changed = parent != instance.parent
            name_changed = name != instance.name
            
            if parent_changed or name_changed:
                # 重新生成 path_name
                if parent:
                    parent_path = parent.path_name or parent.name
                    path_name = f"{parent_path}/{name}"
                else:
                    path_name = name
                validated_data["path_name"] = path_name
        
        return super().update(instance, validated_data)


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


# ==================== Goods 自定义排序 / 移动接口序列化器 ====================

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


# ==================== BGM API 序列化器 ====================

class BGMSearchRequestSerializer(serializers.Serializer):
    """BGM搜索IP角色请求序列化器"""
    ip_name = serializers.CharField(
        max_length=200,
        required=True,
        help_text="IP作品名称，例如：崩坏：星穹铁道"
    )
    subject_type = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="作品类型筛选：1=书籍, 2=动画, 3=音乐, 4=游戏, 6=三次元。不传则搜索所有类型"
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
    subject_type = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="作品类型：1=书籍, 2=动画, 3=音乐, 4=游戏, 6=三次元/特摄。可选，创建IP时使用"
    )
    avatar = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="角色头像URL。可以是BGM返回的头像URL（如 https://lain.bgm.tv/pic/crt/l/xx/xx/12345.jpg）或其他外部URL。可选"
    )


class BGMCreateCharactersRequestSerializer(serializers.Serializer):
    """BGM批量创建角色请求序列化器"""
    characters = BGMCreateCharacterRequestSerializer(
        many=True,
        required=True,
        help_text="角色列表，每个角色包含ip_name和character_name"
    )


