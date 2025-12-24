from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0027_add_ai_help_uniqueness'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='ai_improvement_task_id',
            field=models.CharField(
                blank=True,
                help_text='Идентификатор последней задачи django-q для улучшения текста',
                max_length=36,
                verbose_name='ID задачи AI-улучшения',
            ),
        ),
        migrations.AddField(
            model_name='post',
            name='ai_improvement_requested_at',
            field=models.DateTimeField(
                blank=True,
                help_text='Когда автор инициировал работу AI-помощника',
                null=True,
                verbose_name='Время запроса AI-улучшения',
            ),
        ),
    ]

