from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("Asistent", "0058_gigachat_limits"),
    ]

    operations = [
        migrations.CreateModel(
            name="IntegrationEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now, verbose_name="Дата")),
                ("service", models.CharField(choices=[("telegram", "Telegram"), ("gigachat", "GigaChat"), ("storage", "Хранилище"), ("other", "Другое")], default="other", max_length=32, verbose_name="Сервис")),
                ("code", models.CharField(max_length=64, verbose_name="Код/статус")),
                ("message", models.TextField(verbose_name="Сообщение")),
                ("severity", models.CharField(choices=[("info", "Info"), ("warning", "Warning"), ("error", "Error")], default="warning", max_length=16, verbose_name="Уровень")),
                ("extra", models.JSONField(blank=True, default=dict, verbose_name="Доп. данные")),
            ],
            options={
                "verbose_name": "⚙️ Интеграция: событие",
                "verbose_name_plural": "⚙️ Интеграции: события",
                "ordering": ["-created_at"],
            },
        ),
    ]

