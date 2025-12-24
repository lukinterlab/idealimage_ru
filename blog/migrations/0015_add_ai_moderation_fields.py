# Generated migration for adding AI moderation fields to Post

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0014_comment_parent'),
        ('Asistent', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='moderation_status',
            field=models.CharField(
                choices=[
                    ('pending', 'РќР° РјРѕРґРµСЂР°С†РёРё AI'),
                    ('approved', 'РћРґРѕР±СЂРµРЅРѕ AI'),
                    ('rejected', 'РћС‚РєР»РѕРЅРµРЅРѕ AI'),
                    ('skipped', 'РџСЂРѕРїСѓС‰РµРЅРѕ'),
                ],
                default='pending',
                max_length=20,
                verbose_name='РЎС‚Р°С‚СѓСЃ РјРѕРґРµСЂР°С†РёРё AI'
            ),
        ),
        migrations.AddField(
            model_name='post',
            name='ai_moderation_notes',
            field=models.TextField(blank=True, verbose_name='Р—Р°РјРµС‡Р°РЅРёСЏ AI'),
        ),
        migrations.AddField(
            model_name='post',
            name='content_task',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='task_articles',
                to='Asistent.contenttask',
                verbose_name='РЎРІСЏР·Р°РЅРЅРѕРµ Р·Р°РґР°РЅРёРµ'
            ),
        ),
    ]
