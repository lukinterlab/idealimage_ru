"""
Модели системы расписаний и задач.
Автономное Django-приложение для управления расписаниями AI-генерации контента.
"""
from datetime import datetime, timedelta
from typing import Optional
import logging

from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

logger = logging.getLogger(__name__)


class AISchedule(models.Model):
    """
    Модель расписания для автоматической генерации контента.
    Поддерживает различные стратегии: промпт-шаблоны, системные задачи, пайплайны.
    """
    
    FREQUENCY_CHOICES = [
        ('daily', 'Ежедневно'),
        ('weekly', 'Еженедельно'),
        ('biweekly', 'Раз в две недели'),
        ('monthly', 'Ежемесячно'),
    ]
    
    STRATEGY_CHOICES = [
        ('prompt', 'Промпт-шаблон'),
        ('system', 'Системная задача'),
        ('manual', 'Ручной режим'),
        ('pipeline', 'Пайплайн автоматизации'),
    ]

    SCHEDULE_KIND_CHOICES = [
        ('daily', 'Ежедневно в указанное время'),
        ('weekly', 'Раз в неделю'),
        ('interval', 'Через каждые N минут'),
        ('cron', 'По cron-выражению'),
    ]

    WEEKDAY_CHOICES = [
        (0, 'Понедельник'),
        (1, 'Вторник'),
        (2, 'Среда'),
        (3, 'Четверг'),
        (4, 'Пятница'),
        (5, 'Суббота'),
        (6, 'Воскресенье'),
    ]
    
    # Основные поля
    name = models.CharField(max_length=200, verbose_name="Название расписания")
    strategy_type = models.CharField(
        max_length=20, 
        choices=STRATEGY_CHOICES, 
        default='prompt', 
        verbose_name="Тип стратегии"
    )
    strategy_options = models.JSONField(
        default=dict, 
        blank=True, 
        verbose_name="Опции стратегии"
    )
    
    # Источники и параметры контента
    source_urls = models.TextField(
        blank=True, 
        verbose_name="URL источников (по одному на строке)"
    )
    category = models.ForeignKey(
        'blog.Category', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="Категория для публикации"
    )
    tags = models.CharField(
        max_length=500,
        blank=True, 
        verbose_name="Теги (через запятую)"
    )
    
    # Параметры генерации
    posting_frequency = models.CharField(
        max_length=20, 
        choices=FREQUENCY_CHOICES, 
        default='daily', 
        verbose_name="Частота публикаций"
    )
    articles_per_run = models.IntegerField(
        default=1, 
        validators=[MinValueValidator(1)], 
        verbose_name="Статей за раз"
    )
    min_word_count = models.IntegerField(
        default=1000, 
        validators=[MinValueValidator(100)], 
        verbose_name="Минимум слов в статье"
    )
    max_word_count = models.IntegerField(
        default=1500, 
        validators=[MinValueValidator(100)], 
        verbose_name="Максимум слов в статье"
    )
    keywords = models.TextField(
        blank=True, 
        verbose_name="Ключевые фразы для включения"
    )
    tone = models.CharField(
        max_length=200, 
        default="дружелюбный и экспертный", 
        verbose_name="Тон статьи"
    )
    
    # Статусы и время
    is_active = models.BooleanField(
        default=True, 
        verbose_name="Активно"
    )
    last_run = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Последний запуск"
    )
    next_run = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Следующий запуск"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="Дата создания"
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name="Дата обновления"
    )
    
    # Видео интеграция
    video_sources_enabled = models.BooleanField(
        default=False, 
        verbose_name='Использовать видеоисточники'
    )
    video_platforms = models.JSONField(
        default=list, 
        verbose_name='Видеоплатформы для парсинга'
    )
    auto_publish_to_platforms = models.JSONField(
        default=list, 
        verbose_name='Автопубликация анонсов'
    )
    video_embed_in_articles = models.BooleanField(
        default=False, 
        verbose_name='Встраивать видео в статьи'
    )
    telegram_channels = models.JSONField(
        default=list, 
        verbose_name='Telegram каналы'
    )
    
    # Дополнительные платформы
    rutube_enabled = models.BooleanField(
        default=False, 
        verbose_name='Публиковать на Rutube'
    )
    dzen_enabled = models.BooleanField(
        default=False, 
        verbose_name='Публиковать в Дзен'
    )
    vk_enabled = models.BooleanField(
        default=False, 
        verbose_name='Публиковать в VK'
    )
    
    # Имитация стиля автора
    mimic_author_style = models.ForeignKey(
        'auth.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='mimicked_by_ai', 
        verbose_name='Писать в стиле автора'
    )
    style_strength = models.IntegerField(
        default=5, 
        validators=[MinValueValidator(1), MaxValueValidator(10)], 
        verbose_name='Сила имитации стиля'
    )
    
    # Система промптов и параметров
    prompt_template = models.ForeignKey(
        'Asistent.PromptTemplate', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='schedules', 
        verbose_name='Шаблон промпта'
    )
    scheduled_time = models.TimeField(
        null=True, 
        blank=True, 
        verbose_name='Точное время запуска'
    )
    task_type = models.CharField(
        max_length=50, 
        default='generate_article', 
        choices=[
            ('generate_article', 'Генерация статей'), 
            ('add_likes', 'Лайки (случайные статьи)'), 
            ('add_comments', 'Комментарии (случайные статьи)')
        ], 
        verbose_name='Тип задачи'
    )
    static_params = models.JSONField(
        default=dict, 
        blank=True, 
        verbose_name='Статические параметры'
    )
    dynamic_params = models.JSONField(
        default=dict, 
        blank=True, 
        verbose_name='Динамические параметры'
    )
    max_runs = models.IntegerField(
        null=True, 
        blank=True, 
        verbose_name='Максимум запусков'
    )
    current_run_count = models.IntegerField(
        default=0, 
        verbose_name='Текущий счётчик запусков'
    )
    
    # Архитектура пайплайнов
    payload_template = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Payload для пайплайна',
        help_text='JSON-данные, которые будут переданы в пайплайн при запуске',
    )
    schedule_kind = models.CharField(
        max_length=16,
        choices=SCHEDULE_KIND_CHOICES,
        default='daily',
        verbose_name='Тип расписания',
    )
    cron_expression = models.CharField(
        max_length=120,
        blank=True,
        default='',
        verbose_name='CRON выражение',
        help_text='Используется, если выбран тип "По cron-выражению"',
    )
    interval_minutes = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        verbose_name='Интервал, минут',
    )
    weekday = models.IntegerField(
        null=True,
        blank=True,
        choices=WEEKDAY_CHOICES,
        verbose_name='День недели (для еженедельных запусков)',
    )
    
    class Meta:
        verbose_name = "📋 Задания: Расписание AI"
        verbose_name_plural = "📋 Задания: Расписания AI"
        ordering = ['-created_at']
        db_table = 'Asistent_aischedule'  # Сохраняем старое имя таблицы
    
    def __str__(self):
        return f"{self.name} ({self.get_posting_frequency_display()})"
    
    def get_source_urls_list(self):
        """Возвращает список URL"""
        return [url.strip() for url in self.source_urls.split('\n') if url.strip()]
    
    def get_keywords_list(self):
        """Возвращает список ключевых фраз"""
        return [kw.strip() for kw in self.keywords.split('\n') if kw.strip()]

    def get_pipeline_slug(self) -> Optional[str]:
        """Возвращает slug пайплайна, если используется"""
        # Эти поля есть в старой версии, но не в текущей
        # Оставляем для обратной совместимости
        if hasattr(self, 'pipeline') and self.pipeline:
            return self.pipeline.slug
        if hasattr(self, 'pipeline_slug') and self.pipeline_slug:
            return self.pipeline_slug
        return None

    def build_pipeline_payload(self, **extra_context) -> dict:
        """Формирует payload для запуска пайплайна"""
        payload = dict(self.payload_template or {})
        payload.update(extra_context)
        payload.setdefault("schedule_id", self.id)
        payload.setdefault("schedule_name", self.name)
        if self.category_id:
            payload.setdefault("category_id", self.category_id)
        if self.tags:
            payload.setdefault("tags", self.tags)
        
        # Автоматически добавляем проверку времени для расписаний автопостинга гороскопов
        pipeline_slug = self.get_pipeline_slug()
        if (pipeline_slug == "daily-horoscope-flow" and 
            "Автопостинг гороскопов" in self.name):
            payload.setdefault("check_autopost_time", True)
        
        return payload

    def uses_pipeline(self) -> bool:
        """Проверяет, использует ли расписание пайплайн"""
        return bool(self.get_pipeline_slug())

    def calculate_next_run(self, from_time: Optional[datetime] = None) -> Optional[datetime]:
        """Вычисляет время следующего запуска"""
        from django.utils import timezone

        now = from_time or timezone.now()
        if not self.is_active:
            return None

        if self.schedule_kind == 'interval':
            minutes = self.interval_minutes or 60
            return now + timedelta(minutes=minutes)

        if self.schedule_kind == 'weekly':
            target_weekday = self.weekday if self.weekday is not None else 0
            time_of_day = self.scheduled_time or datetime.strptime('08:00', '%H:%M').time()
            days_ahead = (target_weekday - now.weekday()) % 7
            if days_ahead == 0 and time_of_day <= now.time():
                days_ahead = 7
            next_date = (now + timedelta(days=days_ahead)).replace(
                hour=time_of_day.hour,
                minute=time_of_day.minute,
                second=time_of_day.second,
                microsecond=0,
            )
            return next_date

        if self.schedule_kind == 'cron' and self.cron_expression:
            # Используем croniter для правильного расчёта следующего запуска по CRON
            try:
                from croniter import croniter
                cron = croniter(self.cron_expression, now)
                next_run = cron.get_next(datetime)
                return next_run
            except ImportError:
                # Если croniter недоступен, используем fallback
                logger.warning(f"croniter недоступен для расписания {self.id}, используется fallback")
                return now + timedelta(hours=1)
            except Exception as e:
                # Если ошибка парсинга CRON, используем fallback
                logger.error(f"Ошибка парсинга CRON '{self.cron_expression}' для расписания {self.id}: {e}")
                return now + timedelta(hours=1)

        # daily/default fallback
        time_of_day = self.scheduled_time or datetime.strptime('08:00', '%H:%M').time()
        candidate = now.replace(
            hour=time_of_day.hour,
            minute=time_of_day.minute,
            second=time_of_day.second,
            microsecond=0,
        )
        if candidate <= now:
            candidate = candidate + timedelta(days=1)
        return candidate

    def update_next_run(self, commit: bool = True) -> None:
        """Обновляет время следующего запуска"""
        self.next_run = self.calculate_next_run()
        if commit:
            self.save(update_fields=['next_run'])


class AIScheduleRun(models.Model):
    """
    Журнал выполнения расписаний AI.
    Хранит информацию о каждом запуске: статус, результаты, ошибки.
    """
    
    STATUS_CHOICES = [
        ('running', 'Выполняется'),
        ('success', 'Успешно'),
        ('failed', 'Ошибка'),
        ('partial', 'Частично'),
    ]
    
    schedule = models.ForeignKey(
        'AISchedule', 
        on_delete=models.CASCADE, 
        related_name='runs', 
        verbose_name="Расписание"
    )
    strategy_type = models.CharField(
        max_length=20, 
        choices=AISchedule.STRATEGY_CHOICES, 
        verbose_name="Стратегия"
    )
    started_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="Начало"
    )
    finished_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Завершение"
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='running', 
        verbose_name="Статус"
    )
    created_count = models.IntegerField(
        default=0, 
        verbose_name="Создано объектов"
    )
    errors = models.JSONField(
        default=list, 
        blank=True, 
        verbose_name="Ошибки"
    )
    context_snapshot = models.JSONField(
        default=dict, 
        blank=True, 
        verbose_name="Контекст"
    )
    result_payload = models.JSONField(
        default=dict, 
        blank=True, 
        verbose_name="Результат"
    )
    
    class Meta:
        verbose_name = "AI расписание: запуск"
        verbose_name_plural = "AI расписание: запуски"
        ordering = ['-started_at']
        db_table = 'Asistent_aischedulerun'  # Сохраняем старое имя таблицы
    
    def __str__(self):
        return f"Запуск #{self.id} — {self.schedule.name}"
    
    @property
    def duration(self):
        """Длительность выполнения"""
        if self.finished_at:
            return self.finished_at - self.started_at
        return None

