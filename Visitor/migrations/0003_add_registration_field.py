# Generated manually on 2025-09-29 17:00

from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):

    dependencies = [
        ('Visitor', '0002_feedback'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='registration',
            field=models.DateTimeField(default=timezone.now, verbose_name='Время регистрации на сайте'),
        ),
    ]

