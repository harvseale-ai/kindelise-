# KEYWORD: migration — a numbered database change applied in the same order everywhere the site runs.

from django.db import migrations, models
from django.db.models import Q


# WHY: Removes expiry values in a deliberate, repeatable way.
def clear_expiry_values(apps, schema_editor):
    """Prevent old expiry timestamps from becoming misleading start signals."""
    profile_model = apps.get_model("kindlelise", "Profile")
    profile_model.objects.update(available_until=None)


# WHY: Records this numbered database change so every copy of the site applies it in the same order.
class Migration(migrations.Migration):
    dependencies = [("kindlelise", "0002_seed_initial_interests")]

    operations = [
        migrations.RunPython(clear_expiry_values, migrations.RunPython.noop),
        migrations.RenameField(
            model_name="profile",
            old_name="available_until",
            new_name="available_from",
        ),
        migrations.AddField(
            model_name="profile",
            name="availability_start",
            field=models.CharField(
                blank=True,
                choices=[
                    ("today", "Today"),
                    ("tomorrow", "Tomorrow"),
                    ("this_week", "This week"),
                    ("as_and_when", "As and when"),
                ],
                default="",
                max_length=11,
            ),
        ),
        migrations.AddConstraint(
            model_name="profile",
            constraint=models.CheckConstraint(
                condition=(
                    Q(availability_start="", available_from__isnull=True)
                    | (~Q(availability_start="") & Q(available_from__isnull=False))
                ),
                name="profile_availability_fields_match",
            ),
        ),
    ]
