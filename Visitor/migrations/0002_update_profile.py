# Generated manually on 2025-09-29 16:59

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()


class Migration(migrations.Migration):

    dependencies = [
        ('Visitor', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Добавляем поле spez
        migrations.AddField(
            model_name='profile',
            name='spez',
            field=models.CharField(max_length=80, verbose_name='cпециальность', blank=True, default=''),
        ),
        # Переименовываем поле user в vizitor
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name='profile',
                    name='vizitor',
                    field=models.OneToOneField(
                        to=settings.AUTH_USER_MODEL,
                        on_delete=models.CASCADE,
                        related_name='profile'
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]
