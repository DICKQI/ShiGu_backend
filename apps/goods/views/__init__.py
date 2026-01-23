"""
Goods app views module.
导出所有视图类和函数，保持向后兼容。
"""
from .goods import GoodsFilter, GoodsPagination, GoodsViewSet
from .ip import IPViewSet
from .character import CharacterViewSet
from .category import CategoryViewSet
from .theme import ThemeViewSet
from .bgm import bgm_create_characters, bgm_search_characters

__all__ = [
    "GoodsViewSet",
    "GoodsFilter",
    "GoodsPagination",
    "IPViewSet",
    "CharacterViewSet",
    "CategoryViewSet",
    "ThemeViewSet",
    "bgm_search_characters",
    "bgm_create_characters",
]
