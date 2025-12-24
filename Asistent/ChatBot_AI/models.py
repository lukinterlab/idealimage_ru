"""
Модели чат-бота

Перенесены из Asistent.models для автономности модуля
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class ChatbotSettings(models.Model):
    """Настройки чат-бота"""
    
    # Системный промпт
    system_prompt = models.TextField(
        default="""Ты дружелюбный менеджер сайта IdealImage.ru - женского портала о красоте, моде и здоровье.
        Твоя задача:
        - Отвечать на вопросы о сайте вежливо и по-русски
        - Помогать пользователям найти нужную информацию
        - Объяснять, как стать автором
        - Предоставлять ссылки на полезные статьи
        - При необходимости предлагать связаться с администратором
        
        Стиль общения: дружелюбный, позитивный, но профессиональный.
        Всегда используй русский язык.""",
        verbose_name="Системный промпт",
        help_text="Инструкция для чат-бота: как себя вести, стиль общения"
    )
    
    # Приветствие
    welcome_message = models.TextField(
        default="Здравствуйте! 👋 Я помощник IdealImage.ru. Чем могу помочь?",
        verbose_name="Приветственное сообщение",
        help_text="Первое сообщение при открытии чата"
    )
    
    # Режимы работы
    use_ai = models.BooleanField(
        default=False,
        verbose_name="Использовать GigaChat AI",
        help_text="⚠️ Если выключено - только FAQ и поиск статей (экономия токенов)"
    )
    
    search_articles = models.BooleanField(
        default=True,
        verbose_name="Искать по статьям",
        help_text="Предлагать ссылки на релевантные статьи блога"
    )
    
    max_search_results = models.IntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        verbose_name="Макс. результатов поиска",
        help_text="Сколько статей показывать в ответе (1-10)"
    )
    
    # Контакт с админом
    admin_contact_enabled = models.BooleanField(
        default=True,
        verbose_name="Разрешить связь с админом",
        help_text="Показывать кнопку 'Связаться с администратором'"
    )
    
    admin_email = models.EmailField(
        default="admin@idealimage.ru",
        verbose_name="Email администратора",
        help_text="Куда отправлять сообщения от пользователей"
    )
    
    # Ограничения
    rate_limit_messages = models.IntegerField(
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        verbose_name="Лимит сообщений в час",
        help_text="Для защиты от спама (на одну сессию)"
    )
    
    # Активность
    is_active = models.BooleanField(
        default=True,
        verbose_name="Чат-бот активен",
        help_text="Глобальное включение/выключение чат-бота"
    )
    
    # Метаданные
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Последнее обновление"
    )
    
    class Meta:
        app_label = 'ChatBot_AI'
        db_table = 'ChatBot_AI_chatbotsettings'
        verbose_name = "💬 Чат-бот: Настройки"
        verbose_name_plural = "💬 Чат-бот: Настройки"
    
    def __str__(self):
        status = "✅ Активен" if self.is_active else "❌ Выключен"
        return f"Настройки чат-бота ({status})"
    
    def save(self, *args, **kwargs):
        # Singleton pattern - только одна запись настроек
        if not self.pk and ChatbotSettings.objects.exists():
            raise ValueError('Настройки чат-бота уже существуют. Редактируйте существующие.')
        return super().save(*args, **kwargs)


class ChatbotFAQ(models.Model):
    """Часто задаваемые вопросы для чат-бота"""
    
    question = models.CharField(
        max_length=500,
        verbose_name="Вопрос",
        help_text="Вопрос пользователя или ключевые слова"
    )
    
    answer = models.TextField(
        verbose_name="Ответ",
        help_text="Готовый ответ чат-бота (можно использовать HTML)"
    )
    
    keywords = models.JSONField(
        default=list,
        verbose_name="Ключевые слова",
        help_text="Список слов для поиска: ['автор', 'заявка', 'статья']"
    )
    
    related_url = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Ссылка",
        help_text="Ссылка на статью или страницу (например: /visitor/apply-role/)"
    )
    
    priority = models.IntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Приоритет",
        help_text="Чем выше - тем важнее (90+ критичные, показываются первыми)"
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активен",
        help_text="Использовать этот FAQ"
    )
    
    usage_count = models.IntegerField(
        default=0,
        verbose_name="Количество использований",
        help_text="Сколько раз был показан этот ответ"
    )
    
    embedding = models.JSONField(
        null=True,
        blank=True,
        verbose_name='Векторное представление',
        help_text='Для семантического поиска FAQ (автогенерируется)'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления"
    )
    
    class Meta:
        app_label = 'ChatBot_AI'
        db_table = 'ChatBot_AI_chatbotfaq'
        verbose_name = "💬 Чат-бот: FAQ"
        verbose_name_plural = "💬 Чат-бот: FAQ"
        ordering = ['-priority', '-usage_count']
        indexes = [
            models.Index(fields=['is_active', '-priority'], name='chatbot_faq_active_prior_idx'),
            models.Index(fields=['-usage_count'], name='chatbot_faq_usage_idx'),
        ]
    
    def __str__(self):
        return f"{self.question[:50]}{'...' if len(self.question) > 50 else ''}"
    
    def increment_usage(self):
        """Увеличивает счетчик использования"""
        self.usage_count += 1
        self.save(update_fields=['usage_count'])


class ChatMessage(models.Model):
    """История сообщений чата"""
    
    # Идентификация пользователя
    session_key = models.CharField(
        max_length=255, 
        db_index=True,
        verbose_name="Ключ сессии"
    )
    user = models.ForeignKey(
        User, 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL,
        verbose_name="Пользователь",
        related_name='chatbot_messages'
    )
    
    # Сообщения
    message = models.TextField(
        verbose_name="Сообщение пользователя"
    )
    response = models.TextField(
        verbose_name="Ответ чат-бота"
    )
    
    # Источник ответа
    SOURCE_CHOICES = [
        ('faq', 'FAQ'),
        ('article_search', 'Поиск по статьям'),
        ('ai', 'GigaChat AI'),
        ('error', 'Ошибка'),
    ]
    source = models.CharField(
        max_length=20, 
        choices=SOURCE_CHOICES,
        verbose_name="Источник ответа"
    )
    
    # Метаданные
    found_articles = models.JSONField(
        default=list, 
        blank=True,
        verbose_name="Найденные статьи",
        help_text="Список статей, предложенных в ответе"
    )
    
    processing_time = models.FloatField(
        default=0,
        verbose_name="Время обработки (сек)",
        help_text="Сколько времени заняла генерация ответа"
    )
    
    # IP и User Agent
    ip_address = models.GenericIPAddressField(
        null=True, 
        blank=True,
        verbose_name="IP-адрес"
    )
    
    user_agent = models.TextField(
        blank=True,
        verbose_name="User Agent"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания",
        db_index=True
    )
    
    class Meta:
        app_label = 'ChatBot_AI'
        db_table = 'ChatBot_AI_chatmessage'
        verbose_name = "💬 Чат-бот: Сообщения"
        verbose_name_plural = "💬 Чат-бот: Сообщения"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['session_key', '-created_at'], name='chatbot_msg_session_idx'),
            models.Index(fields=['user', '-created_at'], name='chatbot_msg_user_idx'),
        ]
    
    def __str__(self):
        username = self.user.username if self.user else 'Гость'
        return f"{username}: {self.message[:30]}... ({self.created_at.strftime('%d.%m %H:%M')})"

