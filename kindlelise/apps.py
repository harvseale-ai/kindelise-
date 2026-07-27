"""Define the Kindlelise Django application metadata."""

from django.apps import AppConfig


class KindleliseConfig(AppConfig):
    """Configure the single Kindlelise application without signal workflows."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "kindlelise"
