# Generated manually on 2025-10-14

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('Asistent', '0017_etap3_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='aiknowledgebase',
            name='priority',
            field=models.IntegerField(
                default=50,
                help_text='0-100, чем выше - тем важнее (используется первым)',
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MaxValueValidator(100)
                ],
                verbose_name='Приоритет'
            ),
        ),
        migrations.AlterModelOptions(
            name='aiknowledgebase',
            options={
                'ordering': ['-priority', '-usage_count', '-created_at'],
                'verbose_name': 'Запись базы знаний',
                'verbose_name_plural': 'База знаний AI'
            },
        ),
    ]

