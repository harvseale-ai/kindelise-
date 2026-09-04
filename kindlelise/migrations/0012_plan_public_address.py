from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("kindlelise", "0011_plan_chat_integration"),
    ]

    operations = [
        migrations.AddField(
            model_name="plan",
            name="public_address",
            field=models.CharField(blank=True, default="", max_length=300),
        ),
    ]
