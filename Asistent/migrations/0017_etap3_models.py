# Generated manually for ЭТАП 3

from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('Asistent', '0016_etap2_models'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        # Модели бонусов
        migrations.CreateModel(
            name='BonusFormula',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Название формулы')),
                ('description', models.TextField(blank=True, verbose_name='Описание')),
                ('coefficients', models.JSONField(default=dict, help_text='Словарь с коэффициентами для расчета', verbose_name='Коэффициенты')),
                ('is_active', models.BooleanField(default=False, verbose_name='Активна')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bonus_formulas', to='auth.user', verbose_name='Создал')),
            ],
            options={
                'verbose_name': 'Формула бонусов',
                'verbose_name_plural': 'Формулы бонусов',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='BonusCalculation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('period_days', models.IntegerField(default=30, verbose_name='Период (дней)')),
                ('total_bonus', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Общий бонус')),
                ('articles_count', models.IntegerField(default=0, verbose_name='Количество статей')),
                ('details', models.JSONField(default=dict, verbose_name='Детали расчета')),
                ('formula_snapshot', models.JSONField(default=dict, help_text='Формула, использованная для расчета', verbose_name='Снимок формулы')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата расчета')),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bonus_calculations', to='auth.user', verbose_name='Автор')),
            ],
            options={
                'verbose_name': 'Расчет бонуса',
                'verbose_name_plural': 'Расчеты бонусов',
                'ordering': ['-created_at'],
            },
        ),
        
        # Модели донатов
        migrations.CreateModel(
            name='DonationDistribution',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pool_amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Сумма фонда')),
                ('distributed_amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Распределено')),
                ('authors_count', models.IntegerField(default=0, verbose_name='Количество авторов')),
                ('period_days', models.IntegerField(default=30, verbose_name='Период анализа (дней)')),
                ('weights', models.JSONField(default=dict, verbose_name='Веса распределения')),
                ('distributions_data', models.JSONField(default=list, verbose_name='Данные распределения')),
                ('is_completed', models.BooleanField(default=False, verbose_name='Завершено')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='donation_distributions', to='auth.user', verbose_name='Создал')),
            ],
            options={
                'verbose_name': 'Распределение донатов',
                'verbose_name_plural': 'Распределения донатов',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='AuthorDonationShare',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('share_percentage', models.DecimalField(decimal_places=2, max_digits=5, verbose_name='Доля (%)')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Сумма')),
                ('metrics', models.JSONField(default=dict, verbose_name='Метрики автора')),
                ('is_paid', models.BooleanField(default=False, verbose_name='Выплачено')),
                ('paid_at', models.DateTimeField(blank=True, null=True, verbose_name='Дата выплаты')),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='donation_shares', to='auth.user', verbose_name='Автор')),
                ('distribution', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='author_shares', to='Asistent.donationdistribution', verbose_name='Распределение')),
            ],
            options={
                'verbose_name': 'Доля автора',
                'verbose_name_plural': 'Доли авторов',
                'unique_together': {('distribution', 'author')},
            },
        ),
        
        # Модели промптов
        migrations.CreateModel(
            name='PromptTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(choices=[('article_generation', 'Генерация статей'), ('moderation', 'Модерация'), ('commenting', 'Комментирование'), ('analysis', 'Анализ'), ('scheduling', 'Расписание'), ('system', 'Системные')], max_length=50, verbose_name='Категория')),
                ('name', models.CharField(max_length=200, verbose_name='Название')),
                ('description', models.TextField(blank=True, verbose_name='Описание')),
                ('template', models.TextField(help_text='Используйте {переменные} для подстановки', verbose_name='Шаблон промпта')),
                ('variables', models.JSONField(default=list, help_text='Список доступных переменных', verbose_name='Переменные')),
                ('is_active', models.BooleanField(default=True, verbose_name='Активен')),
                ('usage_count', models.IntegerField(default=0, verbose_name='Количество использований')),
                ('success_rate', models.FloatField(default=0.0, help_text='От 0.0 до 1.0', verbose_name='Процент успеха')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Дата обновления')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='prompt_templates', to='auth.user', verbose_name='Создал')),
            ],
            options={
                'verbose_name': 'Шаблон промпта',
                'verbose_name_plural': 'Шаблоны промптов',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PromptVersion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('version_number', models.IntegerField(verbose_name='Номер версии')),
                ('template_text', models.TextField(verbose_name='Текст промпта')),
                ('is_testing', models.BooleanField(default=False, verbose_name='Тестируется')),
                ('test_group_percentage', models.FloatField(default=0.5, help_text='От 0.0 до 1.0', verbose_name='Процент тестовой группы')),
                ('usage_count', models.IntegerField(default=0, verbose_name='Использований')),
                ('success_count', models.IntegerField(default=0, verbose_name='Успешных')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='versions', to='Asistent.prompttemplate', verbose_name='Шаблон')),
            ],
            options={
                'verbose_name': 'Версия промпта',
                'verbose_name_plural': 'Версии промптов',
                'ordering': ['-version_number'],
                'unique_together': {('template', 'version_number')},
            },
        ),
        
        # Модели обучения
        migrations.CreateModel(
            name='AIFeedback',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.IntegerField(choices=[(1, '👎 Плохо'), (2, '😐 Нормально'), (3, '👍 Хорошо'), (4, '🌟 Отлично')], verbose_name='Оценка')),
                ('comment', models.TextField(blank=True, verbose_name='Комментарий')),
                ('auto_generated', models.BooleanField(default=False, help_text='Оценка сгенерирована автоматически на основе метрик', verbose_name='Автоматическая оценка')),
                ('metrics', models.JSONField(default=dict, help_text='Метрики, на основе которых сделана оценка', verbose_name='Метрики')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата оценки')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ai_feedbacks', to='auth.user', verbose_name='Создал')),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='feedbacks', to='Asistent.aitask', verbose_name='Задача')),
            ],
            options={
                'verbose_name': 'Обратная связь AI',
                'verbose_name_plural': 'Обратная связь AI',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='AIMemory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('memory_type', models.CharField(choices=[('strategy', 'Стратегия'), ('preference', 'Предпочтение'), ('context', 'Контекст'), ('pattern', 'Паттерн'), ('rule', 'Правило')], max_length=50, verbose_name='Тип памяти')),
                ('key', models.CharField(help_text='Уникальный идентификатор памяти', max_length=200, verbose_name='Ключ')),
                ('value', models.JSONField(verbose_name='Значение')),
                ('confidence', models.FloatField(default=1.0, help_text='От 0.0 до 1.0', verbose_name='Уверенность')),
                ('usage_count', models.IntegerField(default=0, verbose_name='Использований')),
                ('last_used_at', models.DateTimeField(blank=True, null=True, verbose_name='Последнее использование')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Дата обновления')),
            ],
            options={
                'verbose_name': 'Память AI',
                'verbose_name_plural': 'Память AI',
                'unique_together': {('memory_type', 'key')},
            },
        ),
        
        # Обновление модели AISchedule
        migrations.AddField(
            model_name='aischedule',
            name='optimization_rules',
            field=models.JSONField(blank=True, default=dict, help_text='Правила оптимизации расписания', verbose_name='Правила оптимизации'),
        ),
        migrations.AddField(
            model_name='aischedule',
            name='ai_generated',
            field=models.BooleanField(default=False, help_text='Расписание создано AI автоматически', verbose_name='Создано AI'),
        ),
    ]
