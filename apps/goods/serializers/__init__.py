"""
Goods app serializers module.
导出所有序列化器，保持向后兼容。
"""
from .fields import AvatarField, KeywordsField
from .ip import (
    IPDetailSerializer,
    IPKeywordSerializer,
    IPSimpleSerializer,
)
from .character import CharacterSimpleSerializer
from .category import (
    CategoryBatchUpdateOrderSerializer,
    CategoryDetailSerializer,
    CategoryOrderItemSerializer,
    CategorySimpleSerializer,
    CategoryTreeSerializer,
)
from .goods import (
    GoodsDetailSerializer,
    GoodsListSerializer,
    GoodsMoveSerializer,
    GuziImageSerializer,
)
from .bgm import (
    BGMCharacterSerializer,
    BGMCreateCharacterRequestSerializer,
    BGMCreateCharactersRequestSerializer,
    BGMSearchRequestSerializer,
    BGMSearchResponseSerializer,
)

__all__ = [
    # Fields
    "KeywordsField",
    "AvatarField",
    # IP
    "IPKeywordSerializer",
    "IPSimpleSerializer",
    "IPDetailSerializer",
    # Character
    "CharacterSimpleSerializer",
    # Category
    "CategorySimpleSerializer",
    "CategoryTreeSerializer",
    "CategoryOrderItemSerializer",
    "CategoryBatchUpdateOrderSerializer",
    "CategoryDetailSerializer",
    # Goods
    "GuziImageSerializer",
    "GoodsListSerializer",
    "GoodsDetailSerializer",
    "GoodsMoveSerializer",
    # BGM
    "BGMSearchRequestSerializer",
    "BGMCharacterSerializer",
    "BGMSearchResponseSerializer",
    "BGMCreateCharacterRequestSerializer",
    "BGMCreateCharactersRequestSerializer",
]
