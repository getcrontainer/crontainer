"""URL configuration for the JSON-only Django API."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.core.api import (
    CredentialViewSet,
    JobViewSet,
    ScheduleViewSet,
    UserViewSet,
    csrf,
    current_user,
    describe_cron,
    login_view,
    logout_view,
)
from apps.node.api import NodeViewSet

router = DefaultRouter()
router.register("schedules", ScheduleViewSet)
router.register("jobs", JobViewSet)
router.register("credentials", CredentialViewSet)
router.register("users", UserViewSet)
router.register("nodes", NodeViewSet)

urlpatterns = [
    path("api/auth/csrf/", csrf, name="csrf"),
    path("api/auth/login/", login_view, name="api-login"),
    path("api/auth/logout/", logout_view, name="api-logout"),
    path("api/auth/me/", current_user, name="api-current-user"),
    path("api/describe-cron/", describe_cron, name="describe-cron"),
    path("api/", include(router.urls)),
]
