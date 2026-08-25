"""URL configuration for the Django API and Vue single-page application."""

from django.urls import include, path, re_path
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter

from apps.core.api import (
    CredentialViewSet,
    JobViewSet,
    ScheduleViewSet,
    UserViewSet,
    csrf,
    current_user,
    dashboard_summary,
    describe_cron,
    health,
    login_view,
    logout_view,
    recreate_cron_files,
)
from apps.node.api import NodeViewSet

router = DefaultRouter()
router.register("schedules", ScheduleViewSet)
router.register("jobs", JobViewSet)
router.register("credentials", CredentialViewSet)
router.register("users", UserViewSet)
router.register("nodes", NodeViewSet)

urlpatterns = [
    path("api/health/", health, name="health"),
    path("api/health/cron-files/recreate/", recreate_cron_files, name="recreate-cron-files"),
    path("api/dashboard/summary/", dashboard_summary, name="dashboard-summary"),
    path("api/auth/csrf/", csrf, name="csrf"),
    path("api/auth/login/", login_view, name="api-login"),
    path("api/auth/logout/", logout_view, name="api-logout"),
    path("api/auth/me/", current_user, name="api-current-user"),
    path("api/describe-cron/", describe_cron, name="describe-cron"),
    path("api/", include(router.urls)),
    re_path(r"^(?!api(?:/|$)|assets(?:/|$)).*$", TemplateView.as_view(template_name="index.html"), name="spa"),
]
