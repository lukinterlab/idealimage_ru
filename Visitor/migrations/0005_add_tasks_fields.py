# Generated migration for adding AI-Assistant fields to Profile

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Visitor', '0004_add_roles_and_new_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='completed_tasks_count',
            field=models.IntegerField(default=0, verbose_name='Р’С‹РїРѕР»РЅРµРЅРѕ Р·Р°РґР°РЅРёР№ AI'),
        ),
        migrations.AlterField(
            model_name='activitylog',
            name='action_type',
            field=models.CharField(
                choices=[
                    ('article_created', 'РЎРѕР·РґР°РЅР° СЃС‚Р°С‚СЊСЏ'),
                    ('article_liked', 'Р›Р°Р№Рє СЃС‚Р°С‚СЊРё'),
                    ('article_viewed', 'РџСЂРѕСЃРјРѕС‚СЂ СЃС‚Р°С‚СЊРё'),
                    ('comment_added', 'Р”РѕР±Р°РІР»РµРЅ РєРѕРјРјРµРЅС‚Р°СЂРёР№'),
                    ('donation_received', 'РџРѕР»СѓС‡РµРЅ РґРѕРЅР°С‚'),
                    ('user_registered', 'Р РµРіРёСЃС‚СЂР°С†РёСЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ'),
                    ('role_applied', 'РџРѕРґР°РЅР° Р·Р°СЏРІРєР° РЅР° СЂРѕР»СЊ'),
                    ('role_granted', 'РџРѕР»СѓС‡РµРЅР° СЂРѕР»СЊ'),
                    ('subscription_added', 'РќРѕРІР°СЏ РїРѕРґРїРёСЃРєР°'),
                    ('task_completed', 'Р’С‹РїРѕР»РЅРµРЅРѕ Р·Р°РґР°РЅРёРµ AI'),
                ],
                max_length=50,
                verbose_name='РўРёРї РґРµР№СЃС‚РІРёСЏ'
            ),
        ),
    ]
