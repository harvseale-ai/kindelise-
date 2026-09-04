import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


def create_chats_for_existing_confirmed_plans(apps, schema_editor):
    Participation = apps.get_model("kindlelise", "Participation")
    PlanChat = apps.get_model("kindlelise", "PlanChat")
    confirmed_plan_ids = Participation.objects.filter(status="joined").values_list(
        "plan_id",
        flat=True,
    )
    PlanChat.objects.bulk_create(
        [PlanChat(plan_id=plan_id) for plan_id in set(confirmed_plan_ids)],
        ignore_conflicts=True,
    )


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("kindlelise", "0009_plan_participation_approval"),
    ]

    operations = [
        migrations.CreateModel(
            name="PlanChat",
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
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "plan",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="chat",
                        to="kindlelise.plan",
                    ),
                ),
            ],
        ),
        migrations.RunPython(
            create_chats_for_existing_confirmed_plans,
            migrations.RunPython.noop,
        ),
        migrations.CreateModel(
            name="PlanChatMessage",
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
                ("body", models.TextField(max_length=1000)),
                ("sent_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "chat",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="messages",
                        to="kindlelise.planchat",
                    ),
                ),
                (
                    "sender",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="sent_plan_chat_messages",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["chat", "sent_at"],
                        name="plan_chat_message_sent_idx",
                    )
                ],
            },
        ),
    ]
