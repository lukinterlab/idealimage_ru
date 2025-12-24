"""
Модели для управления публикациями в социальных сетях
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


class SocialPlatform(models.Model):
    """Платформы социальных сетей"""
    
    PLATFORM_CHOICES = [
        ('telegram', 'Telegram'),
        ('vk', 'VK'),
        ('pinterest', 'Pinterest'),
        ('rutube', 'Rutube'),
        ('dzen', 'Яндекс.Дзен'),
        ('whatsapp', 'WhatsApp'),
        ('max', 'MAX'),
        ('instagram', 'Instagram'),
        ('facebook', 'Facebook'),
        ('youtube', 'YouTube'),
    ]
    
    name = models.CharField(
        max_length=50,
        choices=PLATFORM_CHOICES,
        unique=True,
        verbose_name='Платформа'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активна'
    )
    
    api_credentials = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='API учётные данные',
        help_text='JSON с токенами и ключами'
    )
    
    rate_limits = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Лимиты API',
        help_text='Ограничения на количество запросов'
    )
    
    last_sync = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Последняя синхронизация'
    )
    
    requires_vpn = models.BooleanField(
        default=False,
        verbose_name='Требуется VPN',
        help_text='Для Instagram, Facebook, YouTube'
    )
    
    icon_class = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='CSS класс иконки',
        help_text='Например: fab fa-telegram'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    
    class Meta:
        verbose_name = '📱 Соцсети: Платформа'
        verbose_name_plural = '📱 Соцсети: Платформы'
        ordering = ['name']
    
    def __str__(self):
        status = '✅' if self.is_active else '❌'
        vpn = ' 🔒VPN' if self.requires_vpn else ''
        return f"{status} {self.get_name_display()}{vpn}"


class SocialChannel(models.Model):
    """Каналы/группы в социальных сетях"""
    
    CHANNEL_TYPE_CHOICES = [
        ('beauty', 'Красота'),
        ('fashion', 'Мода'),
        ('health', 'Здоровье'),
        ('lifestyle', 'Образ жизни'),
        ('psychology', 'Психология'),
        ('kids', 'Дети'),
        ('family', 'Семья'),
        ('other', 'Другое'),
    ]
    
    platform = models.ForeignKey(
        SocialPlatform,
        on_delete=models.CASCADE,
        related_name='channels',
        verbose_name='Платформа'
    )
    
    channel_id = models.CharField(
        max_length=200,
        verbose_name='ID канала',
        help_text='@ideal_image_ru или числовой ID'
    )
    
    channel_name = models.CharField(
        max_length=200,
        verbose_name='Название канала'
    )
    
    channel_type = models.CharField(
        max_length=50,
        choices=CHANNEL_TYPE_CHOICES,
        default='other',
        verbose_name='Тип канала'
    )
    
    channel_url = models.URLField(
        blank=True,
        verbose_name='URL канала'
    )
    
    subscribers_count = models.IntegerField(
        default=0,
        verbose_name='Количество подписчиков'
    )
    
    engagement_rate = models.FloatField(
        default=0.0,
        verbose_name='Вовлечённость',
        help_text='Процент активных подписчиков'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен для автопостинга'
    )
    
    posting_rules = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Правила постинга',
        help_text='Частота, категории, время'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    
    class Meta:
        verbose_name = '📢 Соцсети: Канал'
        verbose_name_plural = '📢 Соцсети: Каналы'
        ordering = ['platform', 'channel_name']
        unique_together = ['platform', 'channel_id']
    
    def __str__(self):
        status = '✅' if self.is_active else '❌'
        return f"{status} {self.channel_name} ({self.platform.get_name_display()})"


class TelegramChannelGroup(models.Model):
    """Группы Telegram каналов для удобного управления"""
    
    name = models.CharField(
        max_length=200,
        verbose_name='Название группы',
        help_text='Основные, Тематические, Экспериментальные'
    )
    
    channels = models.ManyToManyField(
        SocialChannel,
        limit_choices_to={'platform__name': 'telegram'},
        related_name='telegram_groups',
        verbose_name='Каналы'
    )
    
    posting_strategy = models.CharField(
        max_length=50,
        choices=[
            ('all', 'Во все каналы'),
            ('random', 'Случайный выбор'),
            ('by_type', 'По типу контента'),
            ('best_performing', 'В лучшие по метрикам'),
        ],
        default='by_type',
        verbose_name='Стратегия распределения'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активна'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    
    class Meta:
        verbose_name = '📱 Telegram: Группа каналов'
        verbose_name_plural = '📱 Telegram: Группы каналов'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.channels.count()} каналов)"


class PostPublication(models.Model):
    """История публикаций в соцсетях"""
    
    STATUS_CHOICES = [
        ('scheduled', 'Запланировано'),
        ('publishing', 'Публикуется'),
        ('published', 'Опубликовано'),
        ('failed', 'Ошибка'),
        ('deleted', 'Удалено'),
    ]
    
    post = models.ForeignKey(
        'blog.Post',
        on_delete=models.CASCADE,
        related_name='social_publications',
        verbose_name='Статья'
    )
    
    channel = models.ForeignKey(
        SocialChannel,
        on_delete=models.CASCADE,
        related_name='publications',
        verbose_name='Канал'
    )
    
    scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Запланировано на'
    )
    
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Опубликовано'
    )
    
    platform_post_id = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='ID поста в соцсети'
    )
    
    platform_url = models.URLField(
        blank=True,
        verbose_name='URL поста'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='scheduled',
        verbose_name='Статус'
    )
    
    # Метрики
    views_count = models.IntegerField(
        default=0,
        verbose_name='Просмотры'
    )
    
    likes_count = models.IntegerField(
        default=0,
        verbose_name='Лайки'
    )
    
    comments_count = models.IntegerField(
        default=0,
        verbose_name='Комментарии'
    )
    
    shares_count = models.IntegerField(
        default=0,
        verbose_name='Репосты'
    )
    
    engagement_score = models.FloatField(
        default=0.0,
        verbose_name='Показатель вовлечённости'
    )
    
    # Контент публикации
    post_content = models.TextField(
        blank=True,
        verbose_name='Текст публикации',
        help_text='Адаптированный контент для платформы'
    )
    
    error_log = models.TextField(
        blank=True,
        verbose_name='Логи ошибок'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    
    class Meta:
        verbose_name = '📊 Соцсети: Публикация'
        verbose_name_plural = '📊 Соцсети: Публикации'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['post', 'channel']),
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.post.title} → {self.channel.channel_name} ({self.get_status_display()})"
    
    def calculate_engagement(self):
        """Расчёт показателя вовлечённости"""
        if self.views_count > 0:
            engagement = (
                (self.likes_count * 1.0 + 
                 self.comments_count * 2.0 + 
                 self.shares_count * 3.0) / self.views_count
            ) * 100
            self.engagement_score = round(engagement, 2)
            self.save(update_fields=['engagement_score'])


class PublicationSchedule(models.Model):
    """Расписание автоматического постинга"""
    
    FREQUENCY_CHOICES = [
        ('hourly', 'Каждый час'),
        ('3times_day', '3 раза в день'),
        ('daily', 'Ежедневно'),
        ('weekly', 'Еженедельно'),
    ]
    
    name = models.CharField(
        max_length=200,
        verbose_name='Название расписания'
    )
    
    channels = models.ManyToManyField(
        SocialChannel,
        related_name='schedules',
        verbose_name='Каналы'
    )
    
    categories = models.ManyToManyField(
        'blog.Category',
        blank=True,
        related_name='social_schedules',
        verbose_name='Категории статей',
        help_text='Какие категории постить'
    )
    
    posting_frequency = models.CharField(
        max_length=20,
        choices=FREQUENCY_CHOICES,
        default='daily',
        verbose_name='Частота публикаций'
    )
    
    optimal_times = models.JSONField(
        default=list,
        verbose_name='Оптимальные часы',
        help_text='Список часов [10, 14, 19]'
    )
    
    content_template = models.TextField(
        blank=True,
        verbose_name='Шаблон поста',
        help_text='Используйте {title}, {url}, {description}'
    )
    
    hashtags = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='Хештеги',
        help_text='Через пробел: #красота #мода'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активно'
    )
    
    ai_optimization = models.BooleanField(
        default=False,
        verbose_name='AI оптимизация времени',
        help_text='AI определяет лучшее время'
    )
    
    last_run = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Последний запуск'
    )
    
    next_run = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Следующий запуск'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    
    class Meta:
        verbose_name = '📅 Соцсети: Расписание'
        verbose_name_plural = '📅 Соцсети: Расписания'
        ordering = ['-created_at']
    
    def __str__(self):
        status = '✅' if self.is_active else '❌'
        return f"{status} {self.name} ({self.get_posting_frequency_display()})"


class SocialConversation(models.Model):
    """Переписка в соцсетях"""
    
    STATUS_CHOICES = [
        ('active', 'Активна'),
        ('archived', 'В архиве'),
        ('spam', 'Спам'),
    ]
    
    channel = models.ForeignKey(
        SocialChannel,
        on_delete=models.CASCADE,
        related_name='conversations',
        verbose_name='Канал'
    )
    
    user_id = models.CharField(
        max_length=200,
        verbose_name='ID пользователя'
    )
    
    user_name = models.CharField(
        max_length=200,
        verbose_name='Имя пользователя'
    )
    
    message_thread = models.JSONField(
        default=list,
        verbose_name='История сообщений'
    )
    
    last_message_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Последнее сообщение'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name='Статус'
    )
    
    ai_responded = models.BooleanField(
        default=False,
        verbose_name='AI ответил'
    )
    
    needs_admin = models.BooleanField(
        default=False,
        verbose_name='Требуется админ'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    
    class Meta:
        verbose_name = '💬 Соцсети: Переписка'
        verbose_name_plural = '💬 Соцсети: Переписка'
        ordering = ['-last_message_at']
    
    def __str__(self):
        return f"{self.user_name} в {self.channel.channel_name}"


class SocialComment(models.Model):
    """Комментарии из соцсетей"""
    
    SENTIMENT_CHOICES = [
        ('positive', 'Позитивный'),
        ('neutral', 'Нейтральный'),
        ('negative', 'Негативный'),
    ]
    
    publication = models.ForeignKey(
        PostPublication,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Публикация'
    )
    
    comment_id = models.CharField(
        max_length=200,
        verbose_name='ID комментария'
    )
    
    author_id = models.CharField(
        max_length=200,
        verbose_name='ID автора'
    )
    
    author_name = models.CharField(
        max_length=200,
        verbose_name='Имя автора'
    )
    
    text = models.TextField(
        verbose_name='Текст комментария'
    )
    
    is_moderated = models.BooleanField(
        default=False,
        verbose_name='Промодерирован'
    )
    
    ai_reply = models.TextField(
        blank=True,
        verbose_name='Ответ AI'
    )
    
    sentiment = models.CharField(
        max_length=20,
        choices=SENTIMENT_CHOICES,
        default='neutral',
        verbose_name='Тональность'
    )
    
    created_at = models.DateTimeField(
        verbose_name='Дата создания'
    )
    
    class Meta:
        verbose_name = '💬 Соцсети: Комментарий'
        verbose_name_plural = '💬 Соцсети: Комментарии'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.author_name}: {self.text[:50]}..."


class AdCampaign(models.Model):
    """Рекламные кампании"""
    
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('active', 'Активна'),
        ('paused', 'Приостановлена'),
        ('completed', 'Завершена'),
    ]
    
    name = models.CharField(
        max_length=200,
        verbose_name='Название кампании'
    )
    
    platforms = models.ManyToManyField(
        SocialPlatform,
        related_name='ad_campaigns',
        verbose_name='Платформы'
    )
    
    budget = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Бюджет (руб.)'
    )
    
    spent = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Потрачено (руб.)'
    )
    
    target_audience = models.JSONField(
        default=dict,
        verbose_name='Целевая аудитория',
        help_text='Таргетинг: возраст, пол, интересы'
    )
    
    ad_content = models.TextField(
        verbose_name='Контент рекламы'
    )
    
    start_date = models.DateField(
        verbose_name='Дата начала'
    )
    
    end_date = models.DateField(
        verbose_name='Дата окончания'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='Статус'
    )
    
    metrics = models.JSONField(
        default=dict,
        verbose_name='Метрики',
        help_text='Показы, клики, конверсии'
    )
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ad_campaigns',
        verbose_name='Создал'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    
    class Meta:
        verbose_name = '💰 Соцсети: Рекламная кампания'
        verbose_name_plural = '💰 Соцсети: Рекламные кампании'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
    
    def get_roi(self):
        """Расчёт ROI"""
        if self.spent > 0 and 'revenue' in self.metrics:
            revenue = Decimal(str(self.metrics['revenue']))
            roi = ((revenue - self.spent) / self.spent) * 100
            return round(roi, 2)
        return 0


class ChannelAnalytics(models.Model):
    """Аналитика каналов (суточная)"""
    
    channel = models.ForeignKey(
        SocialChannel,
        on_delete=models.CASCADE,
        related_name='analytics',
        verbose_name='Канал'
    )
    
    date = models.DateField(
        verbose_name='Дата'
    )
    
    subscribers_gained = models.IntegerField(
        default=0,
        verbose_name='Прирост подписчиков'
    )
    
    subscribers_lost = models.IntegerField(
        default=0,
        verbose_name='Отток подписчиков'
    )
    
    posts_published = models.IntegerField(
        default=0,
        verbose_name='Опубликовано постов'
    )
    
    total_views = models.IntegerField(
        default=0,
        verbose_name='Всего просмотров'
    )
    
    total_engagement = models.IntegerField(
        default=0,
        verbose_name='Всего взаимодействий'
    )
    
    top_post = models.ForeignKey(
        PostPublication,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='top_analytics',
        verbose_name='Топ пост дня'
    )
    
    ai_insights = models.JSONField(
        default=dict,
        verbose_name='Рекомендации AI'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    
    class Meta:
        verbose_name = '📈 Соцсети: Аналитика канала'
        verbose_name_plural = '📈 Соцсети: Аналитика каналов'
        ordering = ['-date']
        unique_together = ['channel', 'date']
    
    def __str__(self):
        return f"{self.channel.channel_name} - {self.date}"


class CrossPostingRule(models.Model):
    """Правила кросс-постинга между каналами"""
    
    name = models.CharField(
        max_length=200,
        verbose_name='Название правила'
    )
    
    source_channel = models.ForeignKey(
        SocialChannel,
        on_delete=models.CASCADE,
        related_name='crosspost_source',
        verbose_name='Исходный канал'
    )
    
    target_channels = models.ManyToManyField(
        SocialChannel,
        related_name='crosspost_target',
        verbose_name='Целевые каналы'
    )
    
    conditions = models.JSONField(
        default=dict,
        verbose_name='Условия',
        help_text='Когда применять: min_views, categories'
    )
    
    transform_content = models.BooleanField(
        default=False,
        verbose_name='Трансформировать контент',
        help_text='Адаптировать под целевую платформу'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активно'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    
    class Meta:
        verbose_name = '🔄 Соцсети: Правило кросс-постинга'
        verbose_name_plural = '🔄 Соцсети: Правила кросс-постинга'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.source_channel} → {self.target_channels.count()} каналов)"
