"""
Модели: AuthorNotification
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class AuthorNotification(models.Model):
    
    NOTIFICATION_TYPES = [
        ('task_available', 'Новое задание'),
        ('task_taken', 'Задание взято'),
        ('moderation_passed', 'Модерация пройдена'),
        ('moderation_failed', 'Модерация не пройдена'),
        ('task_approved', 'Задание одобрено'),
        ('task_rejected', 'Задание отклонено'),
        ('payment', 'Начисление средств'),
        ('system', 'Системное уведомление'),
    ]
    
    recipient = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name="Получатель",
    )
    notification_type = models.CharField(
        max_length=30,
        choices=NOTIFICATION_TYPES,
        verbose_name="Тип уведомления",
    )
    title = models.CharField(max_length=200, verbose_name="Заголовок")
    message = models.TextField(verbose_name="Сообщение")
    related_task = models.ForeignKey(
        'Asistent.ContentTask',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name="Связанное задание",
    )
    related_article = models.ForeignKey(
        'blog.Post',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name="Связанная статья",
    )
    is_read = models.BooleanField(default=False, verbose_name="Прочитано")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    read_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата прочтения")
    
    class Meta:
        verbose_name = "📬 Уведомления для авторов"
        verbose_name_plural = "📬 Уведомления для авторов"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.recipient.username} - {self.title}"
    
    def mark_as_read(self):
        """Отметить как прочитанное"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])



