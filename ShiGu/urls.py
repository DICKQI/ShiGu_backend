"""
URL configuration for ShiGu project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from apps.goods.views import (
    bgm_create_characters,
    bgm_search_characters,
    bgm_search_subjects,
    bgm_get_characters_by_subject_id,
    CategoryViewSet,
    CharacterViewSet,
    GoodsViewSet,
    IPViewSet,
    ShowcaseViewSet,
    ThemeViewSet,
)
from apps.location.views import (
    StorageNodeDetailView,
    StorageNodeGoodsView,
    StorageNodeListCreateView,
    StorageNodeTreeView,
)
from apps.users import views as user_views

router = DefaultRouter()
router.register("goods", GoodsViewSet, basename="goods")
router.register("ips", IPViewSet, basename="ips")
router.register("characters", CharacterViewSet, basename="characters")
router.register("categories", CategoryViewSet, basename="categories")
router.register("themes", ThemeViewSet, basename="themes")
router.register("showcases", ShowcaseViewSet, basename="showcases")

urlpatterns = [
    path('admin/', admin.site.urls),
    # Auth
    path("api/auth/register/", user_views.register, name="auth-register"),
    path("api/auth/login/", user_views.login, name="auth-login"),
    path("api/auth/me/", user_views.me, name="auth-me"),
    path("api/auth/logout/", user_views.logout, name="auth-logout"),
    # 展柜独立接口
    path("api/showcases/public/", ShowcaseViewSet.as_view({"get": "public_list"}), name="showcases-public"),
    path("api/showcases/private/", ShowcaseViewSet.as_view({"get": "private_list"}), name="showcases-private"),
    # 核心检索接口
    path("api/", include(router.urls)),
    # BGM API接口
    path("api/bgm/search-characters/", bgm_search_characters, name="bgm-search-characters"),
    path("api/bgm/create-characters/", bgm_create_characters, name="bgm-create-characters"),
    # BGM 两步式搜索接口
    path("api/bgm/search-subjects/", bgm_search_subjects, name="bgm-search-subjects"),
    path("api/bgm/get-characters-by-id/", bgm_get_characters_by_subject_id, name="bgm-get-characters-by-id"),
    # 位置相关接口
    path("api/location/nodes/", StorageNodeListCreateView.as_view(), name="location-nodes"),
    path("api/location/nodes/<int:pk>/", StorageNodeDetailView.as_view(), name="location-node-detail"),
    path("api/location/nodes/<int:pk>/goods/", StorageNodeGoodsView.as_view(), name="location-node-goods"),
    path("api/location/tree/", StorageNodeTreeView.as_view(), name="location-tree"),
    # 导出 Schema 文件 (YAML格式)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    # 导出 Swagger UI 和 Redoc 界面
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# 开发环境：提供媒体文件访问服务
# 生产环境应使用 Web 服务器（如 Nginx）来提供媒体文件
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
