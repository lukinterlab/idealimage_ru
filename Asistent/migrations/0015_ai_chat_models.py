# Generated manually on 2025-10-14

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('Asistent', '0014_add_performance_indexes'),
    ]

    operations = [
        migrations.CreateModel(
            name='AIConversation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(default='Новый диалог', max_length=200, verbose_name='Название диалога')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Дата обновления')),
                ('is_active', models.BooleanField(default=True, help_text='Активный диалог отображается в списке', verbose_name='Активен')),
                ('admin', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ai_conversations', to=settings.AUTH_USER_MODEL, verbose_name='Администратор')),
            ],
            options={
                'verbose_name': 'Диалог с AI',
                'verbose_name_plural': 'Диалоги с AI',
                'ordering': ['-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='AIKnowledgeBase',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(choices=[('промпты', 'Промпты'), ('правила', 'Правила'), ('примеры', 'Примеры'), ('команды', 'Команды'), ('faq', 'Частые вопросы'), ('инструкции', 'Инструкции')], max_length=100, verbose_name='Категория')),
                ('title', models.CharField(max_length=300, verbose_name='Заголовок')),
                ('content', models.TextField(verbose_name='Содержание')),
                ('tags', models.JSONField(default=list, help_text='Список тегов для поиска', verbose_name='Теги')),
                ('embedding', models.JSONField(blank=True, help_text='Для семантического поиска (опционально)', null=True, verbose_name='Векторное представление')),
                ('is_active', models.BooleanField(default=True, verbose_name='Активен')),
                ('usage_count', models.IntegerField(default=0, verbose_name='Количество использований')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Дата обновления')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='knowledge_entries', to=settings.AUTH_USER_MODEL, verbose_name='Создал')),
            ],
            options={
                'verbose_name': 'Запись базы знаний',
                'verbose_name_plural': 'База знаний AI',
                'ordering': ['-usage_count', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='AIMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('admin', 'Администратор'), ('assistant', 'AI-ассистент'), ('system', 'Система')], max_length=20, verbose_name='Роль')),
                ('content', models.TextField(verbose_name='Содержание сообщения')),
                ('timestamp', models.DateTimeField(auto_now_add=True, verbose_name='Время отправки')),
                ('metadata', models.JSONField(default=dict, help_text='Дополнительная информация: задачи, команды, результаты', verbose_name='Метаданные')),
                ('conversation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='Asistent.aiconversation', verbose_name='Диалог')),
            ],
            options={
                'verbose_name': 'Сообщение AI',
                'verbose_name_plural': 'Сообщения AI',
                'ordering': ['timestamp'],
            },
        ),
        migrations.CreateModel(
            name='AITask',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('command', models.CharField(help_text='Команда от администратора', max_length=500, verbose_name='Исходная команда')),
                ('task_type', models.CharField(choices=[('generate_article', 'Генерация статьи'), ('parse_video', 'Парсинг видео'), ('parse_audio', 'Парсинг аудио'), ('distribute_bonuses', 'Распределение бонусов'), ('distribute_donations', 'Распределение донатов'), ('create_schedule', 'Создание расписания'), ('post_comment', 'Публикация комментария'), ('add_like', 'Добавление лайка'), ('moderate_content', 'Модерация контента'), ('analyze_statistics', 'Анализ статистики'), ('optimize_schedule', 'Оптимизация расписания')], max_length=50, verbose_name='Тип задачи')),
                ('parameters', models.JSONField(default=dict, help_text='Параметры выполнения задачи', verbose_name='Параметры')),
                ('status', models.CharField(choices=[('pending', 'В очереди'), ('in_progress', 'Выполняется'), ('completed', 'Выполнено'), ('failed', 'Ошибка'), ('cancelled', 'Отменено')], default='pending', max_length=20, verbose_name='Статус')),
                ('progress_description', models.TextField(blank=True, help_text='Текущее состояние выполнения', verbose_name='Описание прогресса')),
                ('result', models.JSONField(blank=True, help_text='Результат выполнения задачи', null=True, verbose_name='Результат')),
                ('error_message', models.TextField(blank=True, verbose_name='Сообщение об ошибке')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('started_at', models.DateTimeField(blank=True, null=True, verbose_name='Дата начала выполнения')),
                ('completed_at', models.DateTimeField(blank=True, null=True, verbose_name='Дата завершения')),
                ('conversation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tasks', to='Asistent.aiconversation', verbose_name='Диалог')),
            ],
            options={
                'verbose_name': 'Задача AI',
                'verbose_name_plural': 'Задачи AI',
                'ordering': ['-created_at'],
            },
        ),
    ]

