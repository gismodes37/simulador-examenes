"""
URL configuration for simulador_examenes project.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/users/", include("apps.users.urls", namespace="users")),
    path("api/exams/", include("apps.exams.urls", namespace="exams")),
]
