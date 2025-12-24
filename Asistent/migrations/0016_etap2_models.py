# Generated manually for ЭТАП 2

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('Asistent', '0015_ai_chat_models'),
        ('blog', '0001_initial'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='UploadedMedia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=300, verbose_name='Название')),
                ('description', models.TextField(blank=True, verbose_name='Описание')),
                ('media_type', models.CharField(choices=[('audio', 'Аудио'), ('video', 'Видео'), ('image', 'Изображение')], max_length=20, verbose_name='Тип медиа')),
                ('file', models.FileField(upload_to='ai_uploads/%Y/%m/%d/', verbose_name='Файл')),
                ('file_size', models.BigIntegerField(verbose_name='Размер файла (байты)')),
                ('duration', models.IntegerField(blank=True, null=True, verbose_name='Длительность (секунды)')),
                ('status', models.CharField(choices=[('uploaded', 'Загружено'), ('processing', 'Обрабатывается'), ('processed', 'Обработано'), ('failed', 'Ошибка')], default='uploaded', max_length=20, verbose_name='Статус')),
                ('transcript_text', models.TextField(blank=True, verbose_name='Транскрипция')),
                ('metadata', models.JSONField(default=dict, help_text='Дополнительная информация о файле', verbose_name='Метаданные')),
                ('processing_log', models.TextField(blank=True, verbose_name='Лог обработки')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата загрузки')),
                ('processed_at', models.DateTimeField(blank=True, null=True, verbose_name='Дата обработки')),
                ('uploaded_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='uploaded_media', to='auth.user', verbose_name='Загрузил')),
            ],
            options={
                'verbose_name': 'Загруженное медиа',
                'verbose_name_plural': 'Загруженные медиа',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='BotProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_active', models.BooleanField(default=True, verbose_name='Активен')),
                ('bot_name', models.CharField(help_text='Отображаемое имя для комментариев', max_length=100, verbose_name='Имя бота')),
                ('comment_style', models.CharField(choices=[('formal', 'Формальный'), ('casual', 'Неформальный'), ('friendly', 'Дружелюбный'), ('expert', 'Экспертный'), ('humorous', 'Юмористический')], default='friendly', max_length=50, verbose_name='Стиль комментирования')),
                ('comment_templates', models.JSONField(default=list, help_text='Список шаблонов для генерации комментариев', verbose_name='Шаблоны комментариев')),
                ('max_comments_per_day', models.IntegerField(default=10, verbose_name='Максимум комментариев в день')),
                ('max_likes_per_day', models.IntegerField(default=20, verbose_name='Максимум лайков в день')),
                ('preferred_categories', models.JSONField(default=list, help_text='Категории статей для комментирования', verbose_name='Предпочитаемые категории')),
                ('avoid_categories', models.JSONField(default=list, help_text='Категории статей, которые бот не комментирует', verbose_name='Избегаемые категории')),
                ('min_article_views', models.IntegerField(default=100, help_text='Комментировать только статьи с таким количеством просмотров', verbose_name='Минимальные просмотры статьи')),
                ('comment_probability', models.FloatField(default=0.3, help_text='От 0.0 до 1.0', verbose_name='Вероятность комментирования')),
                ('like_probability', models.FloatField(default=0.5, help_text='От 0.0 до 1.0', verbose_name='Вероятность лайка')),
                ('last_activity', models.DateTimeField(blank=True, null=True, verbose_name='Последняя активность')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='bot_profile', to='auth.user', verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Профиль бота',
                'verbose_name_plural': 'Профили ботов',
            },
        ),
        migrations.CreateModel(
            name='BotActivity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('comment', 'Комментарий'), ('like', 'Лайк'), ('skip', 'Пропуск')], max_length=20, verbose_name='Действие')),
                ('content', models.TextField(blank=True, help_text='Текст комментария или причина пропуска', verbose_name='Содержание')),
                ('success', models.BooleanField(default=True, verbose_name='Успешно')),
                ('error_message', models.TextField(blank=True, verbose_name='Сообщение об ошибке')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата действия')),
                ('article', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bot_activities', to='blog.post', verbose_name='Статья')),
                ('bot_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='activities', to='Asistent.botprofile', verbose_name='Профиль бота')),
            ],
            options={
                'verbose_name': 'Активность бота',
                'verbose_name_plural': 'Активности ботов',
                'ordering': ['-created_at'],
            },
        ),
    ]
