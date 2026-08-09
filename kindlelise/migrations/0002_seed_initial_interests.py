"""Seed the reviewed student-MVP discovery interest vocabulary."""

# KEYWORD: migration — a numbered database change applied in the same order everywhere the site runs.


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


# WHY: Adds the starting initial interests records needed by a new database.
def seed_initial_interests(apps, schema_editor):
    """Create each reviewed interest once on the migration database alias."""
    interest_model = apps.get_model("kindlelise", "Interest")
    for name in INTEREST_NAMES:
        interest_model.objects.using(schema_editor.connection.alias).get_or_create(
            name=name
        )


# WHY: Removes initial interests in a deliberate, repeatable way.
def remove_initial_interests(apps, schema_editor):
    """Remove only the exact vocabulary created by this data migration."""
    interest_model = apps.get_model("kindlelise", "Interest")
    interest_model.objects.using(schema_editor.connection.alias).filter(
        name__in=INTEREST_NAMES
    ).delete()


# WHY: Records this numbered database change so every copy of the site applies it in the same order.
class Migration(migrations.Migration):
    dependencies = [
        ("kindlelise", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_initial_interests, remove_initial_interests),
    ]
