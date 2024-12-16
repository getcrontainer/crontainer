"""
URL configuration for crontainer project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
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

from apps.core.views import (CredentialCreateView, CredentialDeleteView, CredentialListView, CredentialUpdateView,
                             DescribeCronView,
                             JobListView, JobLogDetailView,
                             ScheduleCreateView, ScheduleDeleteView, ScheduleListView, ScheduleUpdateView)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", ScheduleListView.as_view(), name="schedule-list"),
    path("create/", ScheduleCreateView.as_view()),
    path("update/<uuid:pk>/", ScheduleUpdateView.as_view(), name="schedule-update"),
    path("delete/<uuid:pk>/", ScheduleDeleteView.as_view(), name="schedule-delete"),
    path("job/", JobListView.as_view(), name="job-list"),
    path("job/log/<uuid:pk>/", JobLogDetailView.as_view(), name="job-log"),
    path("credentials/", CredentialListView.as_view(), name="credential-list"),
    path(
        "credentials/create/", CredentialCreateView.as_view(), name="credential-create"
    ),
    path(
        "credentials/update/<uuid:pk>/",
        CredentialUpdateView.as_view(),
        name="credential-update",
    ),
    path(
        "credentials/delete/<uuid:pk>/",
        CredentialDeleteView.as_view(),
        name="credential-delete",
    ),
    path("describe_cron/", DescribeCronView.as_view(), name="describe_cron"),
    path("node/", include("apps.node.urls")),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


if settings.DEBUG:
    from debug_toolbar.toolbar import debug_toolbar_urls

    urlpatterns += debug_toolbar_urls()
