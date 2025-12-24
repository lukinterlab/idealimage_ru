from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator
from django.urls import reverse
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from datetime import date, timedelta
from urllib.parse import quote
import os
from utilits.utils import image_compress, unique_slugify

User = get_user_model()

class Pisaka(models.Model):
    """Модель ПИСАТЕЛЕЙ"""
    psevdonim = models.ForeignKey(User, verbose_name='Псевдоним',related_name='pisakas', on_delete=models.SET_NULL, null=True, blank=True)
    rekvisit = models.CharField(max_length=80, verbose_name='реквизиты к оплате', blank=True)
    slug = models.SlugField(verbose_name='URL', max_length=255, blank=True, unique=True)
    prais = models.IntegerField(verbose_name='расценка', blank=True)
    active = models.BooleanField(default=True)
    description = models.TextField(verbose_name='Характеристика', blank=True)
    

    class Meta:
        db_table = 'app_pisaka'
        ordering = ['psevdonim']
        verbose_name = 'Писатель'
        verbose_name_plural = 'Писатели'

    
    
    def get_absolute_url(self):
        return reverse('Visitor:post_list_by_pisaka',
                       kwargs={'slug': self.slug})  # args=[self.slug])



class Profile(models.Model):

    class ProfileManager(models.Manager):
      #  Кастомный менеджер для модели профиля

        def all(self):
           # Список статей (SQL запрос с фильтрацией для страницы списка статей)nk/
            return self.get_queryset().select_related('vizitor')

    objects = ProfileManager()


    vizitor = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    slug = models.SlugField(verbose_name='адресс', max_length=100, blank=True, unique=True)
    avatar = models.ImageField(
        verbose_name='Аватар',
        upload_to='images/avatars/',
        default='images/avatar.png',
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=('png', 'jpg', 'jpeg'))])
    bio = models.TextField(max_length=500, blank=True, verbose_name='Информация о себе')
    birth_date = models.DateField(null=True, blank=True, verbose_name='Дата рождения')
    registration = models.DateTimeField(auto_now_add=True, verbose_name='Время регистрации на сайте', blank=True)
    spez = models.CharField(max_length=80, verbose_name='cпециальность', blank=True)
    
    # Новые поля для системы ролей и уведомлений
    telegram_id = models.CharField(max_length=100, blank=True, null=True, verbose_name='Telegram ID')
    agreed_to_terms = models.BooleanField(default=False, verbose_name='Согласие на обработку данных')
    agreed_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата согласия')
    
    # Роли
    is_author = models.BooleanField(default=False, verbose_name='Автор')
    is_moderator = models.BooleanField(default=False, verbose_name='Модератор')
    is_marketer = models.BooleanField(default=False, verbose_name='Маркетолог')
    is_admin = models.BooleanField(default=False, verbose_name='Администратор')
    
    # Статистика и премии
    total_bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Накопленная премия')
    last_bonus_calculated = models.DateTimeField(null=True, blank=True, verbose_name='Последний расчет премии')
    completed_tasks_count = models.IntegerField(default=0, verbose_name='Выполнено заданий AI')

    class Meta:
        """
        Сортировка, название таблицы в базе данных
        """
        db_table = 'app_profiles'
        ordering = ('vizitor',)
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'

    def save(self, *args, **kwargs):
        """   Сохранение полей модели при их отсутствии заполнения   """
        if not self.slug:
            self.slug = unique_slugify(self, self.vizitor)
        super().save(*args, **kwargs)

    def __str__(self):
        """
        Возвращение строки
        """
        return self.vizitor.username

    def get_absolute_url(self):
        """
        Ссылка на профиль
        """
        return reverse('Visitor:profile_detail', kwargs={'slug': self.slug})

    @property
    def get_avatar(self):
        """
        Возвращает URL аватара пользователя.
        Если аватар не загружен или файл не существует, возвращает сгенерированный аватар через API.
        """
        if self.avatar and self.avatar.name:
            # Проверяем, что файл существует
            try:
                avatar_path = os.path.join(settings.MEDIA_ROOT, self.avatar.name)
                if os.path.exists(avatar_path):
                    return self.avatar.url
            except (ValueError, AttributeError):
                # Если возникла ошибка при получении пути или URL
                pass
        
        # Если аватар не загружен или файл не существует, используем API для генерации
        # Используем username вместо slug для более читаемого имени
        name = self.vizitor.username if hasattr(self, 'vizitor') and self.vizitor else (self.slug or 'User')
        # URL-кодируем имя для безопасности
        encoded_name = quote(name)
        return f'https://ui-avatars.com/api/?size=150&background=random&name={encoded_name}'


@receiver(post_save, sender=User)
def create_vizitor_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(vizitor=instance)


@receiver(post_save, sender=User)
def save_vizitor_profile(sender, instance, **kwargs):
    instance.profile.save()


class Feedback(models.Model):
    """
    Модель обратной связи
    """
    subject = models.CharField(max_length=255, verbose_name='Тема письма')
    email = models.EmailField(max_length=255, verbose_name='Электронный адрес (email)')
    content = models.TextField(verbose_name='Содержимое письма')
    time_create = models.DateTimeField(auto_now_add=True, verbose_name='Дата отправки')
    ip_address = models.GenericIPAddressField(verbose_name='IP отправителя', blank=True, null=True)
    user = models.ForeignKey(User, verbose_name='Пользователь', on_delete=models.CASCADE, null=True, blank=True, related_name='fedbacks')

    class Meta:
        verbose_name = 'Обратная связь'
        verbose_name_plural = 'Обратная связь'
        ordering = ['-time_create']
        db_table = 'app_feedback'

    def __str__(self):
        return f'Вам письмо от {self.email}'


class RoleApplication(models.Model):
    """
    Модель заявки на получение роли
    """
    ROLE_CHOICES = [
        ('author', 'Автор'),
        ('moderator', 'Модератор'),
        ('marketer', 'Маркетолог'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'На рассмотрении'),
        ('approved', 'Одобрена'),
        ('rejected', 'Отклонена'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь', related_name='role_applications')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, verbose_name='Роль')
    applied_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата подачи')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Статус')
    admin_response = models.TextField(blank=True, null=True, verbose_name='Ответ администратора')
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата обработки')
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_applications', verbose_name='Обработал')

    class Meta:
        verbose_name = 'Заявка на роль'
        verbose_name_plural = 'Заявки на роли'
        ordering = ['-applied_at']
        db_table = 'app_role_applications'
        
    def __str__(self):
        return f'{self.user.username} - {self.get_role_display()} ({self.get_status_display()})'


class Subscription(models.Model):
    """
    Модель подписки на автора
    """
    subscriber = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions', verbose_name='Подписчик')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscribers', verbose_name='Автор')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата подписки')
    
    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        ordering = ['-created_at']
        db_table = 'app_subscriptions'
        unique_together = ('subscriber', 'author')
        
    def __str__(self):
        return f'{self.subscriber.username} подписан на {self.author.username}'


class Like(models.Model):
    """
    Модель лайков к статьям
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_likes', verbose_name='Пользователь')
    post = models.ForeignKey('blog.Post', on_delete=models.CASCADE, related_name='post_likes', verbose_name='Статья')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата лайка')
    
    class Meta:
        verbose_name = 'Лайк'
        verbose_name_plural = 'Лайки'
        ordering = ['-created_at']
        db_table = 'app_visitor_likes'
        unique_together = ('user', 'post')
        
    def __str__(self):
        return f'{self.user.username} лайкнул {self.post.title}'


class Donation(models.Model):
    """
    Модель донатов к статьям
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='donations_made', verbose_name='Пользователь')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='donations_received', verbose_name='Автор')
    post = models.ForeignKey('blog.Post', on_delete=models.CASCADE, null=True, blank=True, related_name='post_donations', verbose_name='Статья')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Сумма')
    message = models.TextField(blank=True, verbose_name='Сообщение')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата доната')
    is_anonymous = models.BooleanField(default=False, verbose_name='Анонимный донат')
    
    class Meta:
        verbose_name = 'Донат'
        verbose_name_plural = 'Донаты'
        ordering = ['-created_at']
        db_table = 'app_donations'
        
    def __str__(self):
        if self.is_anonymous:
            return f'Анонимный донат {self.amount} руб. для {self.author.username}'
        return f'{self.user.username if self.user else "Аноним"} отправил {self.amount} руб. для {self.author.username}'


class ActivityLog(models.Model):
    """
    Модель логирования активности пользователей
    """
    ACTION_TYPES = [
        ('article_created', 'Создана статья'),
        ('article_liked', 'Лайк статьи'),
        ('article_viewed', 'Просмотр статьи'),
        ('comment_added', 'Добавлен комментарий'),
        ('donation_received', 'Получен донат'),
        ('user_registered', 'Регистрация пользователя'),
        ('role_applied', 'Подана заявка на роль'),
        ('role_granted', 'Получена роль'),
        ('subscription_added', 'Новая подписка'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='activities', verbose_name='Пользователь')
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES, verbose_name='Тип действия')
    target_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='target_activities', verbose_name='Целевой пользователь')
    target_content_type = models.CharField(max_length=50, blank=True, verbose_name='Тип объекта')
    target_object_id = models.PositiveIntegerField(null=True, blank=True, verbose_name='ID объекта')
    description = models.TextField(blank=True, verbose_name='Описание')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата действия')
    
    class Meta:
        verbose_name = 'Лог активности'
        verbose_name_plural = 'Логи активности'
        ordering = ['-created_at']
        db_table = 'app_activity_logs'
        
    def __str__(self):
        return f'{self.user.username if self.user else "Система"} - {self.get_action_type_display()} - {self.created_at.strftime("%d.%m.%Y %H:%M")}'


class CookieConsent(models.Model):
    """Согласие пользователя на использование cookies (по закону РФ)"""
    
    session_key = models.CharField(
        max_length=255, 
        unique=True, 
        verbose_name='Ключ сессии',
        help_text='Уникальный идентификатор сессии пользователя'
    )
    user = models.ForeignKey(
        User, 
        null=True, 
        blank=True, 
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
        help_text='Если пользователь авторизован'
    )
    
    # Категории согласия (по GDPR/закону РФ)
    necessary = models.BooleanField(
        default=True, 
        verbose_name='Обязательные cookies',
        help_text='Необходимы для работы сайта'
    )
    functional = models.BooleanField(
        default=False, 
        verbose_name='Функциональные cookies',
        help_text='Улучшают функциональность сайта'
    )
    analytics = models.BooleanField(
        default=False, 
        verbose_name='Аналитические cookies',
        help_text='Для анализа посещаемости'
    )
    advertising = models.BooleanField(
        default=False, 
        verbose_name='Рекламные cookies',
        help_text='Для показа персонализированной рекламы'
    )
    
    # Метаданные
    ip_address = models.GenericIPAddressField(
        null=True, 
        blank=True, 
        verbose_name='IP-адрес'
    )
    user_agent = models.TextField(
        blank=True, 
        verbose_name='User Agent',
        help_text='Браузер и ОС пользователя'
    )
    consent_date = models.DateTimeField(
        auto_now_add=True, 
        verbose_name='Дата согласия'
    )
    
    class Meta:
        verbose_name = 'Согласие на Cookie'
        verbose_name_plural = 'Согласия на Cookie'
        ordering = ['-consent_date']
        db_table = 'app_cookie_consent'
        
    def __str__(self):
        username = self.user.username if self.user else 'Гость'
        return f'{username} - {self.consent_date.strftime("%d.%m.%Y %H:%M")}'
