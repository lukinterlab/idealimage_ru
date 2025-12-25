"""
Модели: AIConversation, AIMessage, AITask
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class AIConversation(models.Model):
    
    admin = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ai_conversations',
        verbose_name='Администратор'
    )
    
    title = models.CharField(
        max_length=200,
        default='Новый диалог',
        verbose_name='Название диалога'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен',
        help_text='Активный диалог отображается в списке'
    )
    
    class Meta:
        verbose_name = '🤖 AI-Агент: Диалоги'
        verbose_name_plural = '🤖 AI-Агент: Диалоги'
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.title} ({self.admin.username})"
    
    def get_messages_count(self):
        """Количество сообщений в диалоге"""
        return self.messages.count()
    
    def get_last_message(self):
        """Последнее сообщение в диалоге"""
        return self.messages.order_by('-timestamp').first()



class AIMessage(models.Model):
    
    ROLE_CHOICES = [
        ('admin', 'Администратор'),
        ('assistant', 'AI-ассистент'),
        ('system', 'Система'),
    ]
    
    conversation = models.ForeignKey(
        'AIConversation',
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='Диалог'
    )
    
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        verbose_name='Роль'
    )
    
    content = models.TextField(
        verbose_name='Содержание сообщения'
    )
    
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Время отправки'
    )
    
    metadata = models.JSONField(
        default=dict,
        verbose_name='Метаданные',
        help_text='Дополнительная информация: задачи, команды, результаты'
    )
    
    embedding = models.JSONField(
        null=True,
        blank=True,
        verbose_name='Векторное представление',
        help_text='Для поиска похожих диалогов (генерируется для admin-сообщений)'
    )
    
    class Meta:
        verbose_name = '🤖 AI-Агент: Сообщения'
        verbose_name_plural = '🤖 AI-Агент: Сообщения'
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['conversation', 'timestamp'], name='aimsg_conv_time_idx'),
            models.Index(fields=['role', 'timestamp'], name='aimsg_role_time_idx'),
        ]
    
    def __str__(self):
        return f"{self.get_role_display()}: {self.content[:50]}..."



class AITask(models.Model):
    
    STATUS_CHOICES = [
        ('pending', 'В очереди'),
        ('in_progress', 'Выполняется'),
        ('completed', 'Выполнено'),
        ('failed', 'Ошибка'),
        ('cancelled', 'Отменено'),
    ]
    
    TASK_TYPE_CHOICES = [
        ('generate_article', 'Генерация статьи'),
        ('parse_video', 'Парсинг видео'),
        ('parse_audio', 'Парсинг аудио'),
        ('distribute_bonuses', 'Распределение бонусов'),
        ('optimize_schedule', 'Оптимизация расписания'),
        # Социальные сети
        ('publish_to_social', 'Публикация в соцсети'),
        ('schedule_posts', 'Создание расписания публикаций'),
        ('reply_to_comment', 'Ответ на комментарий в соцсети'),
        ('reply_to_message', 'Ответ в переписке'),
        ('analyze_channel', 'Анализ канала'),
        ('optimize_posting', 'Оптимизация времени публикации'),
        ('create_ad_campaign', 'Создание рекламной кампании'),
        ('crosspost_content', 'Кросс-постинг контента'),
        # Реклама
        ('ad_show_places', 'Показать рекламные места'),
        ('ad_statistics', 'Статистика рекламы'),
        ('ad_activate_banner', 'Активировать баннер'),
        ('ad_deactivate_banner', 'Деактивировать баннер'),
        ('ad_list_banners', 'Список баннеров'),
        ('ad_insert_in_article', 'Вставить рекламу в статью'),
    ]
    
    conversation = models.ForeignKey(
        'AIConversation',
        on_delete=models.CASCADE,
        related_name='tasks',
        verbose_name='Диалог'
    )
    
    command = models.CharField(
        max_length=500,
        verbose_name='Исходная команда',
        help_text='Команда от администратора'
    )
    
    task_type = models.CharField(
        max_length=50,
        choices=TASK_TYPE_CHOICES,
        verbose_name='Тип задачи'
    )
    
    parameters = models.JSONField(
        default=dict,
        verbose_name='Параметры',
        help_text='Параметры выполнения задачи'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Статус'
    )
    
    progress_description = models.TextField(
        blank=True,
        verbose_name='Описание прогресса',
        help_text='Текущее состояние выполнения'
    )
    
    result = models.JSONField(
        null=True,
        blank=True,
        verbose_name='Результат',
        help_text='Результат выполнения задачи'
    )
    
    error_message = models.TextField(
        blank=True,
        verbose_name='Сообщение об ошибке'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата начала выполнения'
    )
    
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата завершения'
    )
    
    class Meta:
        verbose_name = '🤖 AI-Агент: Задачи'
        verbose_name_plural = '🤖 AI-Агент: Задачи'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_task_type_display()} - {self.get_status_display()}"
    
    def start(self):
        """Начать выполнение задачи"""
        self.status = 'in_progress'
        self.started_at = timezone.now()
        self.save()
    
    def complete(self, result=None):
        """Завершить задачу успешно"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        if result:
            self.result = result
        self.save()
    
    def fail(self, error_message):
        """Завершить задачу с ошибкой"""
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.save()




