from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("Asistent", "0057_fill_schedule_defaults"),
    ]

    operations = [
        migrations.AddField(
            model_name="gigachatsettings",
            name="lite_daily_limit",
            field=models.IntegerField(
                default=2000000,
                help_text="0 = без ограничения",
                verbose_name="Дневной лимит Lite (токены)",
            ),
        ),
        migrations.AddField(
            model_name="gigachatsettings",
            name="pro_daily_limit",
            field=models.IntegerField(
                default=1000000,
                help_text="0 = без ограничения",
                verbose_name="Дневной лимит Pro (токены)",
            ),
        ),
        migrations.AddField(
            model_name="gigachatsettings",
            name="max_daily_limit",
            field=models.IntegerField(
                default=500000,
                help_text="0 = без ограничения",
                verbose_name="Дневной лимит Max (токены)",
            ),
        ),
        migrations.AddField(
            model_name="gigachatsettings",
            name="task_failure_limit",
            field=models.IntegerField(
                default=5,
                help_text="Сколько ошибок подряд допускается для одного типа задачи",
                verbose_name="Порог ошибок на задачу",
            ),
        ),
        migrations.AddField(
            model_name="gigachatsettings",
            name="task_failure_window",
            field=models.IntegerField(
                default=30,
                help_text="За какой период анализировать ошибки для circuit breaker",
                verbose_name="Окно ошибок (минуты)",
            ),
        ),
    ]

