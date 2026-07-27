"""
URL configuration for simulador_examenes project.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Frontend pages at root
    path("", include("apps.exams.urls", namespace="exams")),
    # Legacy API endpoints
    path("api/users/", include("apps.users.urls", namespace="users")),
]
