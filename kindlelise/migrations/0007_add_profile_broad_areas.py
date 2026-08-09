# KEYWORD: migration — a numbered database change applied in the same order everywhere the site runs.

from django.contrib.postgres.fields import ArrayField
from django.db import migrations, models


# WHY: Keeps the copy primary area to broad areas steps in one named place so they can be understood, checked, and reused.
def copy_primary_area_to_broad_areas(apps, _schema_editor):
    Profile = apps.get_model("kindlelise", "Profile")
    for profile in Profile.objects.exclude(broad_area="").iterator():
        profile.broad_areas = [profile.broad_area]
        profile.save(update_fields=["broad_areas"])


# WHY: Records this numbered database change so every copy of the site applies it in the same order.
class Migration(migrations.Migration):

    dependencies = [
        ("kindlelise", "0006_add_profile_title_statement"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="broad_areas",
            field=ArrayField(
                base_field=models.CharField(max_length=20),
                blank=True,
                default=list,
                size=None,
            ),
        ),
        migrations.RunPython(
            copy_primary_area_to_broad_areas,
            migrations.RunPython.noop,
        ),
    ]
