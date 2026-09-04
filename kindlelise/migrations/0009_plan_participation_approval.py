# KEYWORD: migration — a numbered database change applied in the same order everywhere the site runs.

import django.utils.timezone
from django.db import migrations, models


def preserve_existing_participation_times(apps, schema_editor):
    """Give existing joined and left rows explicit request and decision times."""
    Participation = apps.get_model("kindlelise", "Participation")
    for participation in Participation.objects.all().iterator():
        participation.requested_at = participation.joined_at
        participation.decided_at = participation.joined_at
        participation.save(update_fields=["requested_at", "decided_at"])


class Migration(migrations.Migration):
    dependencies = [("kindlelise", "0008_add_notification")]

    operations = [
        migrations.RemoveConstraint(
            model_name="participation",
            name="participation_left_at_matches_status",
        ),
        migrations.AddField(
            model_name="participation",
            name="requested_at",
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name="participation",
            name="decided_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="participation",
            name="joined_at",
            field=models.DateTimeField(
                blank=True,
                default=django.utils.timezone.now,
                null=True,
            ),
        ),
        migrations.RunPython(
            preserve_existing_participation_times,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="participation",
            name="decided_at",
            field=models.DateTimeField(
                blank=True,
                default=django.utils.timezone.now,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="participation",
            name="requested_at",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name="participation",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("joined", "Confirmed"),
                    ("declined", "Declined"),
                    ("left", "Left"),
                ],
                default="joined",
                max_length=8,
            ),
        ),
        migrations.AddConstraint(
            model_name="participation",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(
                        status="pending",
                        joined_at__isnull=True,
                        decided_at__isnull=True,
                        left_at__isnull=True,
                    )
                    | models.Q(
                        status="joined",
                        joined_at__isnull=False,
                        decided_at__isnull=False,
                        left_at__isnull=True,
                    )
                    | models.Q(
                        status="declined",
                        joined_at__isnull=True,
                        decided_at__isnull=False,
                        left_at__isnull=True,
                    )
                    | models.Q(status="left", left_at__isnull=False)
                ),
                name="participation_timestamps_match_status",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="notification",
            name="notification_context_matches_kind",
        ),
        migrations.AlterField(
            model_name="notification",
            name="kind",
            field=models.CharField(
                choices=[
                    ("message", "Message"),
                    ("plan_join", "Plan join"),
                    ("plan_request", "Plan request"),
                    ("plan_confirmed", "Plan confirmed"),
                    ("plan_declined", "Plan declined"),
                ],
                max_length=14,
            ),
        ),
        migrations.AddConstraint(
            model_name="notification",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(
                        kind="message",
                        message__isnull=False,
                        participation__isnull=True,
                    )
                    | models.Q(
                        kind__in=(
                            "plan_join",
                            "plan_request",
                            "plan_confirmed",
                            "plan_declined",
                        ),
                        message__isnull=True,
                        participation__isnull=False,
                    )
                ),
                name="notification_context_matches_kind",
            ),
        ),
    ]
