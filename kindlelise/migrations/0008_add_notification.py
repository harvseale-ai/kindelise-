import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("kindlelise", "0007_add_profile_broad_areas"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Notification",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "kind",
                    models.CharField(
                        choices=[("message", "Message"), ("plan_join", "Plan join")],
                        max_length=9,
                    ),
                ),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("read_at", models.DateTimeField(blank=True, null=True)),
                (
                    "message",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="notifications",
                        to="kindlelise.message",
                    ),
                ),
                (
                    "participation",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="notifications",
                        to="kindlelise.participation",
                    ),
                ),
                (
                    "recipient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="notifications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["recipient", "read_at", "created_at"],
                        name="notification_unread_idx",
                    )
                ],
                "constraints": [
                    models.CheckConstraint(
                        condition=(
                            models.Q(
                                kind="message",
                                message__isnull=False,
                                participation__isnull=True,
                            )
                            | models.Q(
                                kind="plan_join",
                                message__isnull=True,
                                participation__isnull=False,
                            )
                        ),
                        name="notification_context_matches_kind",
                    )
                ],
            },
        ),
    ]
