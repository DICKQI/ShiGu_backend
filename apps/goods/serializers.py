from rest_framework import serializers

from .models import Category, Character, Goods, GuziImage, IP


class IPSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = IP
        fields = ("id", "name")


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
        fields = ("id", "name", "ip", "ip_id", "avatar")


class CategorySimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name")


class GuziImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuziImage
        fields = ("id", "image", "label")


class GoodsListSerializer(serializers.ModelSerializer):
    """
    列表用“瘦身”序列化器，仅返回检索页所需字段。
    """

    ip = IPSimpleSerializer(read_only=True)
    character = CharacterSimpleSerializer(read_only=True)
    category = CategorySimpleSerializer(read_only=True)
    location_path = serializers.SerializerMethodField()

    class Meta:
        model = Goods
        fields = (
            "id",
            "name",
            "ip",
            "character",
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
    character = CharacterSimpleSerializer(read_only=True)
    category = CategorySimpleSerializer(read_only=True)
    location_path = serializers.SerializerMethodField()
    additional_photos = GuziImageSerializer(many=True, read_only=True)

    class Meta:
        model = Goods
        fields = (
            "id",
            "name",
            "ip",
            "character",
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


