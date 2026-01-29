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
from .theme import (
    ThemeDetailSerializer,
    ThemeSimpleSerializer,
)
from .goods import (
    GoodsDetailSerializer,
    GoodsListSerializer,
    GoodsMoveSerializer,
    GuziImageSerializer,
)
from .showcase import (
    AddGoodsToShowcaseSerializer,
    MoveGoodsInShowcaseSerializer,
    RemoveGoodsFromShowcaseSerializer,
    ShowcaseDetailSerializer,
    ShowcaseGoodsSerializer,
    ShowcaseListSerializer,
)
from .bgm import (
    BGMCharacterSerializer,
    BGMCreateCharacterRequestSerializer,
    BGMCreateCharactersRequestSerializer,
    BGMSearchRequestSerializer,
    BGMSearchResponseSerializer,
    BGMSubjectSerializer,
    BGMSearchSubjectsRequestSerializer,
    BGMSearchSubjectsResponseSerializer,
    BGMGetCharactersBySubjectIdRequestSerializer,
    BGMGetCharactersBySubjectIdResponseSerializer,
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
    # Theme
    "ThemeSimpleSerializer",
    "ThemeDetailSerializer",
    # Goods
    "GuziImageSerializer",
    "GoodsListSerializer",
    "GoodsDetailSerializer",
    "GoodsMoveSerializer",
    # Showcase
    "ShowcaseListSerializer",
    "ShowcaseDetailSerializer",
    "ShowcaseGoodsSerializer",
    "AddGoodsToShowcaseSerializer",
    "RemoveGoodsFromShowcaseSerializer",
    "MoveGoodsInShowcaseSerializer",
    # BGM
    "BGMSearchRequestSerializer",
    "BGMCharacterSerializer",
    "BGMSearchResponseSerializer",
    "BGMCreateCharacterRequestSerializer",
    "BGMCreateCharactersRequestSerializer",
    "BGMSubjectSerializer",
    "BGMSearchSubjectsRequestSerializer",
    "BGMSearchSubjectsResponseSerializer",
    "BGMGetCharactersBySubjectIdRequestSerializer",
    "BGMGetCharactersBySubjectIdResponseSerializer",
]
