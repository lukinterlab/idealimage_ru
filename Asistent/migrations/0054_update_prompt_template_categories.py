from django.db import migrations, models


CATEGORY_MAPPING = {
    'article_generation': 'article_single',
    'moderation': 'faq',
    'commenting': 'comments',
    'analysis': 'article_series',
    'scheduling': 'article_series',
    'system': 'article_single',
    None: 'article_single',
    '': 'article_single',
}

REVERSE_MAPPING = {
    'article_single': 'article_generation',
    'article_series': 'analysis',
    'horoscope': 'article_generation',
    'faq': 'moderation',
    'comments': 'commenting',
}


def forwards(apps, schema_editor):
    PromptTemplate = apps.get_model('Asistent', 'PromptTemplate')
    for template in PromptTemplate.objects.all():
        new_value = CATEGORY_MAPPING.get(template.category, 'article_single')
        if template.category != new_value:
            template.category = new_value
            template.save(update_fields=['category'])


def backwards(apps, schema_editor):
    PromptTemplate = apps.get_model('Asistent', 'PromptTemplate')
    for template in PromptTemplate.objects.all():
        original_value = REVERSE_MAPPING.get(template.category, 'article_generation')
        if template.category != original_value:
            template.category = original_value
            template.save(update_fields=['category'])


class Migration(migrations.Migration):

    dependencies = [
        ('Asistent', '0053_seed_horoscope_pipeline'),
    ]

    operations = [
        migrations.AlterField(
            model_name='prompttemplate',
            name='category',
            field=models.CharField(
                blank=True,
                choices=[
                    ('article_single', 'Генерация статьи'),
                    ('article_series', 'Генерация серии статей'),
                    ('horoscope', 'Генерация гороскопа'),
                    ('faq', 'Генерация FAQ'),
                    ('comments', 'Генерация комментариев'),
                ],
                default='article_single',
                max_length=50,
                null=True,
                verbose_name='Категория'
            ),
        ),
        migrations.RunPython(forwards, backwards),
    ]

