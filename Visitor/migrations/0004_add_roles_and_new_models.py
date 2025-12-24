# Generated manually on 2025-10-08

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('Visitor', '0003_add_registration_field'),
        ('blog', '0001_initial'),  # Зависимость от blog приложения
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Добавляем новые поля в Profile
        migrations.AddField(
            model_name='profile',
            name='telegram_id',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Telegram ID'),
        ),
        migrations.AddField(
            model_name='profile',
            name='agreed_to_terms',
            field=models.BooleanField(default=False, verbose_name='Согласие на обработку данных'),
        ),
        migrations.AddField(
            model_name='profile',
            name='agreed_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Дата согласия'),
        ),
        migrations.AddField(
            model_name='profile',
            name='is_author',
            field=models.BooleanField(default=False, verbose_name='Автор'),
        ),
        migrations.AddField(
            model_name='profile',
            name='is_moderator',
            field=models.BooleanField(default=False, verbose_name='Модератор'),
        ),
        migrations.AddField(
            model_name='profile',
            name='is_marketer',
            field=models.BooleanField(default=False, verbose_name='Маркетолог'),
        ),
        migrations.AddField(
            model_name='profile',
            name='is_admin',
            field=models.BooleanField(default=False, verbose_name='Администратор'),
        ),
        migrations.AddField(
            model_name='profile',
            name='total_bonus',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Накопленная премия'),
        ),
        migrations.AddField(
            model_name='profile',
            name='last_bonus_calculated',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Последний расчет премии'),
        ),
        
        # Создаем модель RoleApplication
        migrations.CreateModel(
            name='RoleApplication',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('author', 'Автор'), ('moderator', 'Модератор'), ('marketer', 'Маркетолог'), ('admin', 'Администратор')], max_length=20, verbose_name='Роль')),
                ('applied_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата подачи')),
                ('status', models.CharField(choices=[('pending', 'На рассмотрении'), ('approved', 'Одобрена'), ('rejected', 'Отклонена')], default='pending', max_length=20, verbose_name='Статус')),
                ('admin_response', models.TextField(blank=True, null=True, verbose_name='Ответ администратора')),
                ('processed_at', models.DateTimeField(blank=True, null=True, verbose_name='Дата обработки')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='role_applications', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
                ('processed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='processed_applications', to=settings.AUTH_USER_MODEL, verbose_name='Обработал')),
            ],
            options={
                'verbose_name': 'Заявка на роль',
                'verbose_name_plural': 'Заявки на роли',
                'db_table': 'app_role_applications',
                'ordering': ['-applied_at'],
            },
        ),
        
        # Создаем модель Subscription
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата подписки')),
                ('subscriber', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subscriptions', to=settings.AUTH_USER_MODEL, verbose_name='Подписчик')),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subscribers', to=settings.AUTH_USER_MODEL, verbose_name='Автор')),
            ],
            options={
                'verbose_name': 'Подписка',
                'verbose_name_plural': 'Подписки',
                'db_table': 'app_subscriptions',
                'ordering': ['-created_at'],
                'unique_together': {('subscriber', 'author')},
            },
        ),
        
        # Создаем модель Like с уникальными related_name
        migrations.CreateModel(
            name='Like',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата лайка')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_likes', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='post_likes', to='blog.post', verbose_name='Статья')),
            ],
            options={
                'verbose_name': 'Лайк',
                'verbose_name_plural': 'Лайки',
                'db_table': 'app_visitor_likes',
                'ordering': ['-created_at'],
                'unique_together': {('user', 'post')},
            },
        ),
        
        # Создаем модель Donation
        migrations.CreateModel(
            name='Donation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Сумма')),
                ('message', models.TextField(blank=True, verbose_name='Сообщение')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата доната')),
                ('is_anonymous', models.BooleanField(default=False, verbose_name='Анонимный донат')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='donations_made', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='donations_received', to=settings.AUTH_USER_MODEL, verbose_name='Автор')),
                ('post', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='post_donations', to='blog.post', verbose_name='Статья')),
            ],
            options={
                'verbose_name': 'Донат',
                'verbose_name_plural': 'Донаты',
                'db_table': 'app_donations',
                'ordering': ['-created_at'],
            },
        ),
        
        # Создаем модель ActivityLog
        migrations.CreateModel(
            name='ActivityLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action_type', models.CharField(choices=[('article_created', 'Создана статья'), ('article_liked', 'Лайк статьи'), ('article_viewed', 'Просмотр статьи'), ('comment_added', 'Добавлен комментарий'), ('donation_received', 'Получен донат'), ('user_registered', 'Регистрация пользователя'), ('role_applied', 'Подана заявка на роль'), ('role_granted', 'Получена роль'), ('subscription_added', 'Новая подписка')], max_length=50, verbose_name='Тип действия')),
                ('target_content_type', models.CharField(blank=True, max_length=50, verbose_name='Тип объекта')),
                ('target_object_id', models.PositiveIntegerField(blank=True, null=True, verbose_name='ID объекта')),
                ('description', models.TextField(blank=True, verbose_name='Описание')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата действия')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='activities', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
                ('target_user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='target_activities', to=settings.AUTH_USER_MODEL, verbose_name='Целевой пользователь')),
            ],
            options={
                'verbose_name': 'Лог активности',
                'verbose_name_plural': 'Логи активности',
                'db_table': 'app_activity_logs',
                'ordering': ['-created_at'],
            },
        ),
    ]

