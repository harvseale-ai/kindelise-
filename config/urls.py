"""Mount Django Admin and the implemented Kindelise application routes."""

# KEYWORD: route — a web address connected to the page code that should answer it.

# WHY: Sends staff addresses to Django Admin and every other address to the Kindelise routes.
from django.contrib import admin
from django.urls import include, path

# WHY: Keeps the two top-level address choices explicit and easy to check.
urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("kindlelise.urls")),
]
