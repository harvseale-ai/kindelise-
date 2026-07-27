"""Mount Django Admin and the implemented Kindlelise application routes."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("kindlelise.urls")),
]
