"""
Модели: ArticleGenerationMetric, GigaChatUsageStats
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class ArticleGenerationMetric(models.Model):
    """Метрики производительности генерации статей"""
    
    # Идентификаторы
    template = models.ForeignKey(
        'Asistent.PromptTemplate',
        on_delete=models.CASCADE,
        related_name='generation_metrics',
        verbose_name='Шаблон промпта'
    )
    
    # Временные метки
    started_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Начало генерации',
        db_index=True
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Завершение генерации'
    )
    
    # Общие метрики
    total_duration = models.FloatField(
        null=True,
        blank=True,
        verbose_name='Общее время (сек)',
        help_text='Время от начала до конца генерации'
    )
    success = models.BooleanField(
        default=False,
        verbose_name='Успешно',
        db_index=True
    )
    error_message = models.TextField(
        blank=True,
        verbose_name='Сообщение об ошибке'
    )
    
    # Метрики этапов (в секундах)
    context_build_duration = models.FloatField(
        null=True,
        blank=True,
        verbose_name='Построение контекста (сек)'
    )
    content_generation_duration = models.FloatField(
        null=True,
        blank=True,
        verbose_name='Генерация контента (сек)'
    )
    title_generation_duration = models.FloatField(
        null=True,
        blank=True,
        verbose_name='Генерация заголовка (сек)'
    )
    image_processing_duration = models.FloatField(
        null=True,
        blank=True,
        verbose_name='Обработка изображения (сек)'
    )
    tags_generation_duration = models.FloatField(
        null=True,
        blank=True,
        verbose_name='Генерация тегов (сек)'
    )
    
    # Метрики результата
    content_length = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Длина контента (символов)'
    )
    word_count = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Количество слов'
    )
    tags_count = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Количество тегов'
    )
    has_image = models.BooleanField(
        default=False,
        verbose_name='Есть изображение'
    )
    image_source_type = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Тип источника изображения'
    )
    
    # Метаданные
    gigachat_model = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Модель GigaChat'
    )
    user_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='ID пользователя'
    )
    
    class Meta:
        verbose_name = '📊 Метрика генерации статьи'
        verbose_name_plural = '📊 Метрики генерации статей'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['-started_at']),
            models.Index(fields=['template', '-started_at']),
            models.Index(fields=['success', '-started_at']),
        ]
    
    def __str__(self):
        status = "✅" if self.success else "❌"
        duration = f"{self.total_duration:.1f}s" if self.total_duration else "N/A"
        return f"{status} {self.template.name} - {duration} ({self.started_at.strftime('%d.%m %H:%M')})"
    
    def complete(self, success: bool = True, error_message: str = ''):
        """Завершение метрики с расчётом общего времени"""
        self.completed_at = timezone.now()
        self.success = success
        self.error_message = error_message
        
        if self.started_at:
            delta = self.completed_at - self.started_at
            self.total_duration = delta.total_seconds()
        
        self.save()




class GigaChatUsageStats(models.Model):
    
    model_name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Название модели",
        help_text="GigaChat, GigaChat-Max, GigaChat-Pro"
    )
    
    tokens_used = models.IntegerField(
        default=0,
        verbose_name="Токенов использовано"
    )
    
    tokens_remaining = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Токенов осталось"
    )
    
    total_requests = models.IntegerField(
        default=0,
        verbose_name="Всего запросов"
    )
    
    successful_requests = models.IntegerField(
        default=0,
        verbose_name="Успешных запросов"
    )
    
    failed_requests = models.IntegerField(
        default=0,
        verbose_name="Неудачных запросов"
    )
    
    # ============================================================================
    # НОВЫЕ ПОЛЯ: Дневная статистика и стоимость
    # ============================================================================
    
    tokens_used_today = models.IntegerField(
        default=0,
        verbose_name="Токенов использовано сегодня",
        help_text="Счетчик токенов за текущий день (сбрасывается в 00:00)"
    )
    
    cost_today = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name="Стоимость сегодня (₽)",
        help_text="Расходы на API за текущий день"
    )
    
    cost_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name="Общая стоимость (₽)",
        help_text="Все расходы на API за все время"
    )
    
    last_daily_reset = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Последний сброс дневной статистики",
        help_text="Дата последнего сброса tokens_used_today и cost_today (в 00:00)"
    )
    
    last_check_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Последняя проверка"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )
    
    class Meta:
        verbose_name = "🤖 GigaChat: Статистика модели"
        verbose_name_plural = "🤖 GigaChat: Статистика моделей"
        ordering = ['model_name']
    
    def __str__(self):
        return f"{self.model_name}: {self.tokens_remaining or 0} токенов"
    
    @property
    def success_rate(self):
        """Процент успешных запросов"""
        if self.total_requests == 0:
            return 0
        return round((self.successful_requests / self.total_requests) * 100, 2)

    def reset_daily_counters_if_needed(self, save=True):
        """Сбрасывает дневные счетчики, если наступил новый день."""
        now = timezone.now()
        if not self.last_daily_reset or self.last_daily_reset.date() != now.date():
            self.tokens_used_today = 0
            self.cost_today = Decimal("0.00")
            self.last_daily_reset = now
            if save:
                self.save(update_fields=["tokens_used_today", "cost_today", "last_daily_reset"])

    def register_usage(self, tokens_used: int, price_per_million: Decimal) -> None:
        """Фиксирует расход токенов и стоимость запроса."""
        if tokens_used <= 0:
            return
        self.reset_daily_counters_if_needed(save=False)
        self.tokens_used += tokens_used
        self.tokens_used_today += tokens_used
        cost_increment = (Decimal(tokens_used) / Decimal(1_000_000)) * price_per_million
        self.cost_today += cost_increment
        self.cost_total += cost_increment
        self.last_check_at = timezone.now()
        self.save(
            update_fields=[
                "tokens_used",
                "tokens_used_today",
                "cost_today",
                "cost_total",
                "last_daily_reset",
                "last_check_at",
            ]
        )



