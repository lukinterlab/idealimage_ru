"""
Модели: IntegrationEvent, SystemLog
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class IntegrationEvent(models.Model):
    
    SERVICE_CHOICES = [
        ("telegram", "Telegram"),
        ("gigachat", "GigaChat"),
        ("storage", "Хранилище"),
        ("other", "Другое"),
    ]
    
    SEVERITY_CHOICES = [
        ("info", "Info"),
        ("warning", "Warning"),
        ("error", "Error"),
    ]
    
    created_at = models.DateTimeField(default=timezone.now, db_index=True, verbose_name="Дата")
    service = models.CharField(max_length=32, choices=SERVICE_CHOICES, default="other", verbose_name="Сервис")
    code = models.CharField(max_length=64, verbose_name="Код/статус")
    message = models.TextField(verbose_name="Сообщение")
    severity = models.CharField(max_length=16, choices=SEVERITY_CHOICES, default="warning", verbose_name="Уровень")
    extra = models.JSONField(default=dict, blank=True, verbose_name="Доп. данные")
    
    class Meta:
        verbose_name = "⚙️ Интеграция: событие"
        verbose_name_plural = "⚙️ Интеграции: события"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"[{self.service}] {self.code} ({self.severity})"



class SystemLog(models.Model):
    """
    Модель для хранения всех системных логов в базе данных.
    Логи хранятся не более 24 часов (автоматическая очистка).
    """
    
    LEVEL_CHOICES = [
        ('DEBUG', 'DEBUG'),
        ('INFO', 'INFO'),
        ('WARNING', 'WARNING'),
        ('ERROR', 'ERROR'),
        ('CRITICAL', 'CRITICAL'),
    ]
    
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        verbose_name='Время события'
    )
    
    level = models.CharField(
        max_length=10,
        choices=LEVEL_CHOICES,
        db_index=True,
        verbose_name='Уровень'
    )
    
    logger_name = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name='Имя логгера',
        help_text='Например: django, Asistent, django-q'
    )
    
    message = models.TextField(
        verbose_name='Сообщение'
    )
    
    module = models.CharField(
        max_length=200,
        blank=True,
        db_index=True,
        verbose_name='Модуль',
        help_text='Имя модуля где произошло событие'
    )
    
    function = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Функция',
        help_text='Имя функции где произошло событие'
    )
    
    line = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Номер строки'
    )
    
    process_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='ID процесса'
    )
    
    thread_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name='ID потока'
    )
    
    extra_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Дополнительные данные',
        help_text='Дополнительная информация в формате JSON'
    )
    
    class Meta:
        verbose_name = '📋 Системный лог'
        verbose_name_plural = '📋 Системные логи'
        ordering = ['-timestamp']
        db_table = 'asistent_systemlog'
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['level', '-timestamp']),
            models.Index(fields=['logger_name', '-timestamp']),
            models.Index(fields=['module', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.level} [{self.logger_name}] {self.message[:50]}... ({self.timestamp.strftime('%Y-%m-%d %H:%M:%S')})"




