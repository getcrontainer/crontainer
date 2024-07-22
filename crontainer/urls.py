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
from django.urls import path

from apps.core.views import (
    ScheduleCreateView,
    ScheduleListView,
    ScheduleDeleteView,
    JobListView,
    JobLogDetailView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", ScheduleListView.as_view()),
    path("history/", JobListView.as_view(), name="job-list"),
    path("job/log/<uuid:pk>/", JobLogDetailView.as_view(), name="job-log"),
    path("create/", ScheduleCreateView.as_view()),
    path("delete/<uuid:pk>/", ScheduleDeleteView.as_view(), name="schedule-delete"),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
