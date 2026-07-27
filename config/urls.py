"""Mount only Django Admin until the mapped application routes are implemented."""

from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
]
