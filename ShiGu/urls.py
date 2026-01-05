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
from rest_framework.routers import DefaultRouter

from apps.goods.views import (
    CategoryViewSet,
    CharacterViewSet,
    GoodsViewSet,
    IPViewSet,
)
from apps.location.views import StorageNodeListCreateView, StorageNodeTreeView

router = DefaultRouter()
router.register("goods", GoodsViewSet, basename="goods")
router.register("ips", IPViewSet, basename="ips")
router.register("characters", CharacterViewSet, basename="characters")
router.register("categories", CategoryViewSet, basename="categories")

urlpatterns = [
    path('admin/', admin.site.urls),
    # 核心检索接口
    path("api/", include(router.urls)),
    # 位置相关接口
    path("api/location/nodes/", StorageNodeListCreateView.as_view(), name="location-nodes"),
    path("api/location/tree/", StorageNodeTreeView.as_view(), name="location-tree"),
]

# 开发环境：提供媒体文件访问服务
# 生产环境应使用 Web 服务器（如 Nginx）来提供媒体文件
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
