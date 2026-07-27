"""Seed the reviewed student-MVP discovery interest vocabulary."""

from django.db import migrations

INTEREST_NAMES = (
    "Coffee",
    "Walking",
    "Museums",
    "Live music",
    "Cinema",
    "Food",
    "Games",
    "Study",
)


def seed_initial_interests(apps, schema_editor):
    """Create each reviewed interest once on the migration database alias."""
    interest_model = apps.get_model("kindlelise", "Interest")
    for name in INTEREST_NAMES:
        interest_model.objects.using(schema_editor.connection.alias).get_or_create(
            name=name
        )


def remove_initial_interests(apps, schema_editor):
    """Remove only the exact vocabulary created by this data migration."""
    interest_model = apps.get_model("kindlelise", "Interest")
    interest_model.objects.using(schema_editor.connection.alias).filter(
        name__in=INTEREST_NAMES
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("kindlelise", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_initial_interests, remove_initial_interests),
    ]
