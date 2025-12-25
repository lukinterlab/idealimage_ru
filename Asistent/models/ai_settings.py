"""
Модели: GigaChatSettings
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class GigaChatSettings(models.Model):
    
    # УСТАРЕВШИЕ ПОЛЯ (не используются в логике, оставлены для совместимости)
    check_balance_after_requests = models.IntegerField(default=1, validators=[MinValueValidator(1)], verbose_name="Проверять баланс после N запросов", help_text="[УСТАРЕЛО] Только для ручной проверки в дашборде")
    current_model = models.CharField(max_length=50, default='GigaChat', verbose_name="Текущая модель", help_text="[УСТАРЕЛО] Только для отображения, не используется в логике")
    auto_switch_enabled = models.BooleanField(default=True, verbose_name="Автопереключение моделей", help_text="[УСТАРЕЛО] Не используется - переключения отключены")
    models_priority = models.JSONField(default=list, verbose_name="Приоритет моделей", help_text="[УСТАРЕЛО] Только для отображения")
    request_counter = models.IntegerField(default=0, verbose_name="Счётчик запросов", help_text="[УСТАРЕЛО] Не используется")
    # ============================================================================
    # НОВЫЕ ПОЛЯ: Включение моделей и прайс-лист
    # ============================================================================
    embeddings_enabled = models.BooleanField(default=True, verbose_name="Embeddings включен", help_text="Использовать GigaChat-Embeddings для RAG и векторного поиска")
    lite_enabled = models.BooleanField(default=True, verbose_name="Lite включен", help_text="Использовать GigaChat Lite для простых задач")
    pro_enabled = models.BooleanField(default=True, verbose_name="Pro включен", help_text="Использовать GigaChat Pro для средних задач")
    max_enabled = models.BooleanField(default=True, verbose_name="Max включен", help_text="Использовать GigaChat Max для сложных задач")
    # Прайс-лист (₽ за 1M токенов) для расчета стоимости
    price_embeddings = models.DecimalField(max_digits=10, decimal_places=2, default=40.00, verbose_name="Цена Embeddings (₽/1M)", help_text="10M токенов = 400₽ → 1M = 40₽")
    price_lite = models.DecimalField(max_digits=10, decimal_places=2, default=194.00, verbose_name="Цена Lite (₽/1M)", help_text="30M токенов = 5,820₽ → 1M = 194₽")
    price_pro = models.DecimalField(max_digits=10, decimal_places=2, default=1500.00, verbose_name="Цена Pro (₽/1M)", help_text="1M токенов = 1,500₽")
    price_max = models.DecimalField(max_digits=10, decimal_places=2, default=1950.00, verbose_name="Цена Max (₽/1M)", help_text="1M токенов = 1,950₽")
    # УСТАРЕВШИЕ ПОЛЯ (не используются - проверки лимитов отключены)
    lite_daily_limit = models.IntegerField(default=2_000_000, verbose_name="Дневной лимит Lite (токены)", help_text="[УСТАРЕЛО] Не используется - проверки лимитов отключены")
    pro_daily_limit = models.IntegerField(default=1_000_000, verbose_name="Дневной лимит Pro (токены)", help_text="[УСТАРЕЛО] Не используется - проверки лимитов отключены")
    max_daily_limit = models.IntegerField(default=500_000, verbose_name="Дневной лимит Max (токены)", help_text="[УСТАРЕЛО] Не используется - проверки лимитов отключены")
    task_failure_limit = models.IntegerField(default=5, verbose_name="Порог ошибок на задачу", help_text="Сколько ошибок подряд допускается для одного типа задачи")
    task_failure_window = models.IntegerField(default=30, verbose_name="Окно ошибок (минуты)", help_text="За какой период анализировать ошибки для circuit breaker")
    # Пороги для алертов (только для дашборда)
    alert_threshold_percent = models.IntegerField(default=20, validators=[MinValueValidator(1), MaxValueValidator(100)], verbose_name="Порог алерта (%)", help_text="Только для отображения в Dashboard")
    # УСТАРЕВШЕЕ ПОЛЕ (не используется - переключения отключены)
    preventive_switch_threshold = models.IntegerField(default=10, validators=[MinValueValidator(1), MaxValueValidator(100)], verbose_name="Порог превентивного переключения (%)", help_text="[УСТАРЕЛО] Не используется - переключения отключены")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Последнее обновление")
    
    class Meta:
        verbose_name = "🤖 GigaChat: Настройки"
        verbose_name_plural = "🤖 GigaChat: Настройки"
    
    def __str__(self):
        return f"GigaChat Settings (текущая модель: {self.current_model})"
    
    def save(self, *args, **kwargs):
        # Гарантируем что всегда существует только одна запись с pk=1
        self.pk = 1
        super().save(*args, **kwargs)




