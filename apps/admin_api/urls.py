from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AdminRoleViewSet, AdminUserViewSet

router = DefaultRouter()
router.register("users", AdminUserViewSet, basename="admin-users")
router.register("roles", AdminRoleViewSet, basename="admin-roles")

urlpatterns = [
    path("", include(router.urls)),
]
