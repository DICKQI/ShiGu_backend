"""
展柜相关的序列化器（不含“展柜分类”功能）
"""
from rest_framework import serializers

from ..models import Goods, Showcase, ShowcaseGoods
from ..utils import compress_image
from .goods import GoodsListSerializer


class ShowcaseGoodsSerializer(serializers.ModelSerializer):
    """展柜谷子关联序列化器"""

    goods = GoodsListSerializer(read_only=True)
    goods_id = serializers.PrimaryKeyRelatedField(
        queryset=Goods.objects.all(),
        source="goods",
        write_only=True,
        required=False,
        help_text="关联谷子ID",
    )

    class Meta:
        model = ShowcaseGoods
        fields = (
            "id",
            "goods_id",
            "goods",
            "order",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class ShowcaseListSerializer(serializers.ModelSerializer):
    """展柜列表序列化器（瘦身版）"""

    class Meta:
        model = Showcase
        fields = (
            "id",
            "name",
            "description",
            "cover_image",
            "order",
            "created_at",
        )
        read_only_fields = ("id", "created_at")


class ShowcaseDetailSerializer(serializers.ModelSerializer):
    """展柜详情序列化器（包含谷子）"""

    showcase_goods = ShowcaseGoodsSerializer(many=True, read_only=True)

    class Meta:
        model = Showcase
        fields = (
            "id",
            "name",
            "description",
            "cover_image",
            "order",
            "is_public",
            "showcase_goods",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def create(self, validated_data):
        """创建展柜时自动压缩封面图片"""
        cover_image = validated_data.get("cover_image")
        if cover_image:
            compressed_image = compress_image(cover_image, max_size_kb=300)
            if compressed_image:
                validated_data["cover_image"] = compressed_image
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """更新展柜时自动压缩封面图片"""
        cover_image = validated_data.get("cover_image")
        if cover_image:
            compressed_image = compress_image(cover_image, max_size_kb=300)
            if compressed_image:
                validated_data["cover_image"] = compressed_image
        return super().update(instance, validated_data)


class AddGoodsToShowcaseSerializer(serializers.Serializer):
    """添加谷子到展柜的请求序列化器"""

    goods_id = serializers.UUIDField(required=True, help_text="谷子ID")
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="备注（可选）",
    )


class RemoveGoodsFromShowcaseSerializer(serializers.Serializer):
    """从展柜移除谷子的请求序列化器"""

    goods_id = serializers.UUIDField(required=True, help_text="谷子ID")


class MoveGoodsInShowcaseSerializer(serializers.Serializer):
    """移动展柜中谷子位置的请求序列化器"""

    goods_id = serializers.UUIDField(required=True, help_text="要移动的谷子ID")
    anchor_goods_id = serializers.UUIDField(
        required=True, help_text="锚点谷子ID（即要移动到哪个谷子的前面或后面）"
    )
    position = serializers.ChoiceField(
        choices=["before", "after"],
        required=True,
        help_text="移动位置：before(之前) / after(之后)",
    )

