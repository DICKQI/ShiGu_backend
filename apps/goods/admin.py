from django.contrib import admin

from .models import Category, Character, Goods, GuziImage, IP, IPKeyword



class IPKeywordInline(admin.TabularInline):
    model = IPKeyword
    extra = 1


@admin.register(IP)
class IPAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
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
    list_display = ("id", "name")
    search_fields = ("name",)
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
        "character",
        "category",
        "location",
        "status",
        "quantity",
        "price",
        "purchase_date",
        "is_official",
        "created_at",
    )
    list_filter = (
        "ip",
        "character",
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
        "character__name",
        "category__name",
        "location__path_name",
    )
    autocomplete_fields = ("ip", "character", "category", "location")
    inlines = [GuziImageInline]
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)
    list_per_page = 50

