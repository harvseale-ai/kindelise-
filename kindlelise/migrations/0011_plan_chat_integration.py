import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("kindlelise", "0010_plan_chat"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="plan_chat_message",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="notifications",
                to="kindlelise.planchatmessage",
            ),
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
                    ("plan_chat_message", "Plan chat message"),
                ],
                max_length=17,
            ),
        ),
        migrations.RemoveConstraint(
            model_name="notification",
            name="notification_context_matches_kind",
        ),
        migrations.AddConstraint(
            model_name="notification",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(
                        kind="message",
                        message__isnull=False,
                        participation__isnull=True,
                        plan_chat_message__isnull=True,
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
                        plan_chat_message__isnull=True,
                    )
                    | models.Q(
                        kind="plan_chat_message",
                        message__isnull=True,
                        participation__isnull=True,
                        plan_chat_message__isnull=False,
                    )
                ),
                name="notification_context_matches_kind",
            ),
        ),
        migrations.AddField(
            model_name="report",
            name="reported_plan_chat_message",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="reports",
                to="kindlelise.planchatmessage",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="report",
            name="report_at_most_one_context",
        ),
        migrations.AddConstraint(
            model_name="report",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(
                        reported_plan__isnull=True,
                        reported_conversation__isnull=True,
                        reported_message__isnull=True,
                        reported_plan_chat_message__isnull=True,
                    )
                    | models.Q(
                        reported_plan__isnull=False,
                        reported_conversation__isnull=True,
                        reported_message__isnull=True,
                        reported_plan_chat_message__isnull=True,
                    )
                    | models.Q(
                        reported_plan__isnull=True,
                        reported_conversation__isnull=False,
                        reported_message__isnull=True,
                        reported_plan_chat_message__isnull=True,
                    )
                    | models.Q(
                        reported_plan__isnull=True,
                        reported_conversation__isnull=True,
                        reported_message__isnull=False,
                        reported_plan_chat_message__isnull=True,
                    )
                    | models.Q(
                        reported_plan__isnull=True,
                        reported_conversation__isnull=True,
                        reported_message__isnull=True,
                        reported_plan_chat_message__isnull=False,
                    )
                ),
                name="report_at_most_one_context",
            ),
        ),
    ]
