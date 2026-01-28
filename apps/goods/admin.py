from django.contrib import admin

from .models import (
    Category,
    Character,
    Goods,
    GuziImage,
    IP,
    IPKeyword,
    Showcase,
    ShowcaseGoods,
    Theme,
)



class IPKeywordInline(admin.TabularInline):
    model = IPKeyword
    extra = 1


@admin.register(IP)
class IPAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "subject_type")
    list_filter = ("subject_type",)
    search_fields = ("name", "keywords__value")
    ordering = ("name",)
    inlines = [IPKeywordInline]


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "ip")
    list_filter = ("ip",)
    search_fields = ("name", "ip__name", "ip__keywords__value")
    autocomplete_fields = ("ip",)
    ordering = ("ip__name", "name")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "path_name", "color_tag", "order", "created_at")
    list_filter = ("parent", "created_at")
    search_fields = ("name", "path_name")
    autocomplete_fields = ("parent",)
    list_display = ("id", "name")
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(Theme)
class ThemeAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at")
    search_fields = ("name", "description")
    ordering = ("name",)


class GuziImageInline(admin.TabularInline):
    model = GuziImage
    extra = 1


@admin.register(Goods)
class GoodsAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "ip",
        "get_characters",
        "category",
        "location",
        "status",
        "quantity",
        "price",
        "purchase_date",
        "is_official",
        "created_at",
        "order",
    )
    list_filter = (
        "ip",
        "characters",
        "category",
        "status",
        "is_official",
        "location",
        "purchase_date",
        "created_at",
    )
    search_fields = (
        "name",
        "ip__name",
        "ip__keywords__value",
        "characters__name",
        "category__name",
        "location__path_name",
    )
    autocomplete_fields = ("ip", "characters", "category", "location")
    inlines = [GuziImageInline]
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)
    list_per_page = 50
    filter_horizontal = ("characters",)  # 使用水平选择器显示多对多关系

    def get_characters(self, obj):
        """显示所有关联的角色名称"""
        return ", ".join([char.name for char in obj.characters.all()])

    get_characters.short_description = "角色"


class ShowcaseGoodsInline(admin.TabularInline):
    model = ShowcaseGoods
    extra = 1
    autocomplete_fields = ("goods",)


@admin.register(Showcase)
class ShowcaseAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "order", "is_public", "created_at")
    list_filter = ("is_public", "created_at")
    search_fields = ("name", "description")
    ordering = ("order", "-created_at")
    readonly_fields = ("created_at", "updated_at")
    inlines = [ShowcaseGoodsInline]


@admin.register(ShowcaseGoods)
class ShowcaseGoodsAdmin(admin.ModelAdmin):
    list_display = ("id", "showcase", "goods", "order", "created_at")
    list_filter = ("showcase", "created_at")
    search_fields = ("showcase__name", "goods__name")
    autocomplete_fields = ("showcase", "goods")
    ordering = ("showcase", "order", "-created_at")

