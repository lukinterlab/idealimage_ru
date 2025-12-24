from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("Asistent", "0046_merge_20251110_1200"),
    ]

    operations = [
        migrations.AddField(
            model_name="moderationcriteria",
            name="slug",
            field=models.SlugField(
                max_length=100,
                blank=True,
                null=True,
                unique=True,
                verbose_name="Человекочитаемый код",
            ),
        ),
        migrations.AddField(
            model_name="moderationcriteria",
            name="description",
            field=models.TextField(
                blank=True,
                verbose_name="Описание",
            ),
        ),
        migrations.AddField(
            model_name="moderationcriteria",
            name="rule_config",
            field=models.JSONField(
                default=dict,
                blank=True,
                verbose_name="Матрица правил",
                help_text="Структура global/roles/categories с параметрами правил.",
            ),
        ),
    ]


