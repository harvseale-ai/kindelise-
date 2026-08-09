"""Define the Kindelise Django application metadata."""

# KEYWORD: app configuration — the name Django uses to recognise and prepare this part of the site.


from django.apps import AppConfig


# WHY: Keeps the KindleliseConfig information and its rules together so they stay consistent.
class KindleliseConfig(AppConfig):
    """Configure the single Kindelise application without signal workflows."""

    # WHY: Gives new saved rows large automatic numeric identifiers by default.
    default_auto_field = "django.db.models.BigAutoField"

    # WHY: Tells Django the exact Python package that belongs to this application.
    name = "kindlelise"

    # WHY: Shows the correctly spelled product name in Django Admin without renaming the Python package.
    verbose_name = "Kindelise"
