"""
Модели для системы управления рекламой
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.urls import reverse
from decimal import Decimal

User = get_user_model()


class AdPlace(models.Model):
    """Рекламные места на сайте"""
    
    PLACEMENT_TYPES = [
        ('banner', 'Баннер'),
        ('context', 'Контекстная реклама'),
        ('ticker', 'Бегущая строка'),
        ('popup', 'Всплывающее окно'),
        ('overlay', 'Наложение'),
    ]
    
    name = models.CharField(
        max_length=200,
        verbose_name='Название места'
    )
    code = models.SlugField(
        max_length=100,
        unique=True,
        verbose_name='Код места',
        help_text='Уникальный идентификатор: header_banner, sidebar_top и т.д.'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание'
    )
    placement_type = models.CharField(
        max_length=20,
        choices=PLACEMENT_TYPES,
        default='banner',
        verbose_name='Тип размещения'
    )
    recommended_size = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Рекомендуемый размер',
        help_text='Например: 728x90, 300x250'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активно'
    )
    position_order = models.IntegerField(
        default=0,
        verbose_name='Порядок показа',
        help_text='Чем меньше число, тем выше в списке'
    )
    max_ads_per_rotation = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name='Максимум объявлений в ротации'
    )
    
    # Настройки для всплывающей рекламы (popup_modal)
    popup_test_mode = models.BooleanField(
        default=False,
        verbose_name='🧪 Тестовый режим popup',
        help_text='Если включено: popup всплывает каждые N секунд (для тестирования). Если выключено: стандартный режим с cookie'
    )
    popup_test_interval_seconds = models.IntegerField(
        default=15,
        validators=[MinValueValidator(5), MaxValueValidator(300)],
        verbose_name='Интервал в тестовом режиме (сек)',
        help_text='Каждые сколько секунд всплывает popup в тестовом режиме (5-300 сек)'
    )
    popup_delay_seconds = models.IntegerField(
        default=5,
        validators=[MinValueValidator(0), MaxValueValidator(60)],
        verbose_name='⏱️ Задержка первого всплывания (сек)',
        help_text='Через сколько секунд после загрузки страницы показать popup (0-60 сек)'
    )
    popup_cookie_hours = models.IntegerField(
        default=24,
        validators=[MinValueValidator(1), MaxValueValidator(168)],
        verbose_name='🍪 Cookie на сколько часов',
        help_text='Как долго не показывать popup после закрытия в стандартном режиме (1-168 часов = 1-7 дней)'
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
        verbose_name = 'Рекламное место'
        verbose_name_plural = 'Рекламные места'
        ordering = ['position_order', 'name']
        db_table = 'advertising_ad_place'
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    def get_public_page_url(self):
        """Получить URL публичной страницы где отображается баннер"""
        url_mapping = {
            'header_banner': '/',
            'sidebar_top': '/blog/',
            'in_post_middle': '/blog/',
            'footer_banner': '/',
            'popup_modal': '/',
            'ticker_line': '/',
            'before_article_content': '/blog/',
            'after_comments': '/blog/',
            'sidebar_after_author': '/blog/',
            'sidebar_after_popular': '/blog/',
        }
        return url_mapping.get(self.code, '/')


class Advertiser(models.Model):
    """Рекламодатели"""
    
    name = models.CharField(
        max_length=200,
        verbose_name='Название компании'
    )
    contact_email = models.EmailField(
        verbose_name='Email для связи'
    )
    contact_phone = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Телефон'
    )
    company_info = models.TextField(
        blank=True,
        verbose_name='Информация о компании'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен'
    )
    total_spent = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Общая потраченная сумма',
        help_text='Автоматически рассчитывается'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата регистрации'
    )
    
    class Meta:
        verbose_name = 'Рекламодатель'
        verbose_name_plural = 'Рекламодатели'
        ordering = ['-created_at']
        db_table = 'advertising_advertiser'
    
    def __str__(self):
        return self.name
    
    def update_total_spent(self):
        """Обновить общую потраченную сумму"""
        total = self.campaigns.aggregate(
            total=models.Sum('spent_amount')
        )['total'] or Decimal('0.00')
        self.total_spent = total
        self.save(update_fields=['total_spent'])


class AdCampaign(models.Model):
    """Рекламные кампании"""
    
    advertiser = models.ForeignKey(
        Advertiser,
        on_delete=models.CASCADE,
        related_name='campaigns',
        verbose_name='Рекламодатель'
    )
    name = models.CharField(
        max_length=200,
        verbose_name='Название кампании'
    )
    budget = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Бюджет',
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    spent_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Потрачено',
        help_text='Автоматически рассчитывается'
    )
    cost_per_click = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Стоимость за клик (CPC)',
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    cost_per_impression = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Стоимость за 1000 показов (CPM)',
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    start_date = models.DateField(
        verbose_name='Дата начала'
    )
    end_date = models.DateField(
        verbose_name='Дата окончания'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активна'
    )
    target_audience = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Целевая аудитория',
        help_text='JSON с параметрами таргетинга'
    )
    notes = models.TextField(
        blank=True,
        verbose_name='Заметки'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_campaigns',
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
        verbose_name = 'Рекламная кампания'
        verbose_name_plural = 'Рекламные кампании'
        ordering = ['-created_at']
        db_table = 'advertising_campaign'
    
    def __str__(self):
        return f"{self.name} ({self.advertiser.name})"
    
    def is_active_now(self):
        """Проверка, активна ли кампания сейчас"""
        today = timezone.now().date()
        return (
            self.is_active and
            self.start_date <= today <= self.end_date and
            self.spent_amount < self.budget
        )
    
    def get_remaining_budget(self):
        """Получить остаток бюджета"""
        return self.budget - self.spent_amount
    
    def get_budget_usage_percent(self):
        """Получить процент использования бюджета"""
        if self.budget == 0:
            return 0
        return (self.spent_amount / self.budget) * 100


class AdBanner(models.Model):
    """Баннеры"""
    
    BANNER_TYPES = [
        ('image', 'Изображение'),
        ('video', 'Видео'),
        ('html', 'HTML'),
        ('animated', 'Анимированный'),
    ]
    
    campaign = models.ForeignKey(
        AdCampaign,
        on_delete=models.CASCADE,
        related_name='banners',
        verbose_name='Кампания'
    )
    place = models.ForeignKey(
        AdPlace,
        on_delete=models.CASCADE,
        related_name='banners',
        verbose_name='Место размещения'
    )
    name = models.CharField(
        max_length=200,
        verbose_name='Название баннера'
    )
    banner_type = models.CharField(
        max_length=20,
        choices=BANNER_TYPES,
        default='image',
        verbose_name='Тип баннера'
    )
    image = models.ImageField(
        upload_to='advertising/banners/',
        blank=True,
        null=True,
        verbose_name='Изображение'
    )
    video = models.FileField(
        upload_to='advertising/videos/',
        blank=True,
        null=True,
        verbose_name='Видео'
    )
    html_content = models.TextField(
        blank=True,
        verbose_name='HTML контент',
        help_text='Для баннеров типа HTML'
    )
    external_code = models.TextField(
        blank=True,
        verbose_name='Внешний код рекламы',
        help_text='Код от Google AdSense, Яндекс.Директ и других сетей'
    )
    use_external_code = models.BooleanField(
        default=False,
        verbose_name='Использовать внешний код',
        help_text='Если True, будет показан external_code вместо image/video'
    )
    
    # Наложение текста для основного контента (popup, sidebar, ticker)
    main_text_overlay = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Текст поверх основного изображения/видео',
        help_text='{"text": "Текст", "color": "#ffffff", "size": 32, "x": 50, "y": 50, "align": "center"}'
    )
    
    target_url = models.URLField(
        verbose_name='Целевой URL',
        help_text='Куда перейдет пользователь при клике'
    )
    alt_text = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Альтернативный текст'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен'
    )
    unlimited_impressions = models.BooleanField(
        default=True,
        verbose_name='Безлимитное отображение',
        help_text='Если включено, баннер будет показываться без ограничений по количеству показов и времени. Расписание можно не заполнять. При снятии галочки вступает в силу расписание (если заполнено) или безлимитное отображение по умолчанию'
    )
    banner_height = models.IntegerField(
        default=100,
        validators=[MinValueValidator(50), MaxValueValidator(500)],
        verbose_name='Высота баннера (px)',
        help_text='Высота отображения баннера в пикселях (от 50 до 500)'
    )
    
    # Поля для 4 карточек (для header_banner и footer_banner)
    # Карточка 1
    card1_type = models.CharField(
        max_length=20,
        choices=[('image', 'Изображение'), ('video', 'Видео'), ('text', 'Текст')],
        default='text',
        blank=True,
        verbose_name='Тип карточки 1'
    )
    card1_title = models.CharField(max_length=100, blank=True, verbose_name='Заголовок карточки 1', default='Изображение')
    card1_text = models.CharField(max_length=200, blank=True, verbose_name='Текст карточки 1', default='Карточка 1')
    card1_image = models.ImageField(upload_to='advertising/cards/', blank=True, null=True, verbose_name='Изображение карточки 1')
    card1_video = models.FileField(upload_to='advertising/cards/', blank=True, null=True, verbose_name='Видео карточки 1')
    card1_icon = models.CharField(max_length=10, blank=True, verbose_name='Иконка карточки 1', default='📸')
    card1_text_overlay = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Текст поверх изображения/видео 1',
        help_text='{"text": "Текст", "color": "#ffffff", "size": 24, "x": 50, "y": 50}'
    )
    
    # Карточка 2
    card2_type = models.CharField(
        max_length=20,
        choices=[('image', 'Изображение'), ('video', 'Видео'), ('text', 'Текст')],
        default='text',
        blank=True,
        verbose_name='Тип карточки 2'
    )
    card2_title = models.CharField(max_length=100, blank=True, verbose_name='Заголовок карточки 2', default='Видео')
    card2_text = models.CharField(max_length=200, blank=True, verbose_name='Текст карточки 2', default='Карточка 2')
    card2_image = models.ImageField(upload_to='advertising/cards/', blank=True, null=True, verbose_name='Изображение карточки 2')
    card2_video = models.FileField(upload_to='advertising/cards/', blank=True, null=True, verbose_name='Видео карточки 2')
    card2_icon = models.CharField(max_length=10, blank=True, verbose_name='Иконка карточки 2', default='🎥')
    card2_text_overlay = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Текст поверх изображения/видео 2',
        help_text='{"text": "Текст", "color": "#ffffff", "size": 24, "x": 50, "y": 50}'
    )
    
    # Карточка 3
    card3_type = models.CharField(
        max_length=20,
        choices=[('image', 'Изображение'), ('video', 'Видео'), ('text', 'Текст')],
        default='text',
        blank=True,
        verbose_name='Тип карточки 3'
    )
    card3_title = models.CharField(max_length=100, blank=True, verbose_name='Заголовок карточки 3', default='Дизайн')
    card3_text = models.CharField(max_length=200, blank=True, verbose_name='Текст карточки 3', default='Карточка 3')
    card3_image = models.ImageField(upload_to='advertising/cards/', blank=True, null=True, verbose_name='Изображение карточки 3')
    card3_video = models.FileField(upload_to='advertising/cards/', blank=True, null=True, verbose_name='Видео карточки 3')
    card3_icon = models.CharField(max_length=10, blank=True, verbose_name='Иконка карточки 3', default='🎨')
    card3_text_overlay = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Текст поверх изображения/видео 3',
        help_text='{"text": "Текст", "color": "#ffffff", "size": 24, "x": 50, "y": 50}'
    )
    
    # Карточка 4
    card4_type = models.CharField(
        max_length=20,
        choices=[('image', 'Изображение'), ('video', 'Видео'), ('text', 'Текст')],
        default='text',
        blank=True,
        verbose_name='Тип карточки 4'
    )
    card4_title = models.CharField(max_length=100, blank=True, verbose_name='Заголовок карточки 4', default='Стиль')
    card4_text = models.CharField(max_length=200, blank=True, verbose_name='Текст карточки 4', default='Карточка 4')
    card4_image = models.ImageField(upload_to='advertising/cards/', blank=True, null=True, verbose_name='Изображение карточки 4')
    card4_video = models.FileField(upload_to='advertising/cards/', blank=True, null=True, verbose_name='Видео карточки 4')
    card4_icon = models.CharField(max_length=10, blank=True, verbose_name='Иконка карточки 4', default='✨')
    card4_text_overlay = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Текст поверх изображения/видео 4',
        help_text='{"text": "Текст", "color": "#ffffff", "size": 24, "x": 50, "y": 50}'
    )
    
    # URL для карточек (если не указан - используется target_url баннера)
    card1_url = models.URLField(
        blank=True,
        null=True,
        verbose_name='Ссылка карточки 1',
        help_text='Если не указана, используется общая ссылка баннера'
    )
    card2_url = models.URLField(
        blank=True,
        null=True,
        verbose_name='Ссылка карточки 2',
        help_text='Если не указана, используется общая ссылка баннера'
    )
    card3_url = models.URLField(
        blank=True,
        null=True,
        verbose_name='Ссылка карточки 3',
        help_text='Если не указана, используется общая ссылка баннера'
    )
    card4_url = models.URLField(
        blank=True,
        null=True,
        verbose_name='Ссылка карточки 4',
        help_text='Если не указана, используется общая ссылка баннера'
    )
    
    priority = models.IntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        verbose_name='Приоритет',
        help_text='От 1 (низкий) до 10 (высокий)'
    )
    weight = models.IntegerField(
        default=100,
        validators=[MinValueValidator(1)],
        verbose_name='Вес в ротации',
        help_text='Для A/B тестирования. Чем больше, тем чаще показывается'
    )
    impressions = models.IntegerField(
        default=0,
        verbose_name='Показов'
    )
    clicks = models.IntegerField(
        default=0,
        verbose_name='Кликов'
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
        verbose_name = 'Баннер'
        verbose_name_plural = 'Баннеры'
        ordering = ['-priority', '-created_at']
        db_table = 'advertising_banner'
    
    def __str__(self):
        return f"{self.name} - {self.place.name}"
    
    def get_ctr(self):
        """Рассчитать CTR (Click-Through Rate)"""
        if self.impressions == 0:
            return 0
        return (self.clicks / self.impressions) * 100
    
    def get_cost(self):
        """Рассчитать стоимость"""
        cpc = self.campaign.cost_per_click
        cpm = self.campaign.cost_per_impression
        
        cost_from_clicks = Decimal(str(self.clicks)) * cpc
        cost_from_impressions = (Decimal(str(self.impressions)) / 1000) * cpm
        
        return cost_from_clicks + cost_from_impressions
    
    def get_revenue(self):
        """Получить доход (для сайта)"""
        return self.get_cost()


class AdSchedule(models.Model):
    """Расписание показа баннеров"""
    
    DAYS_OF_WEEK = [
        (0, 'Понедельник'),
        (1, 'Вторник'),
        (2, 'Среда'),
        (3, 'Четверг'),
        (4, 'Пятница'),
        (5, 'Суббота'),
        (6, 'Воскресенье'),
    ]
    
    banner = models.ForeignKey(
        AdBanner,
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name='Баннер'
    )
    day_of_week = models.IntegerField(
        choices=DAYS_OF_WEEK,
        null=True,
        blank=True,
        verbose_name='День недели',
        help_text='Оставьте пустым для показа каждый день'
    )
    start_time = models.TimeField(
        verbose_name='Время начала показа'
    )
    end_time = models.TimeField(
        verbose_name='Время окончания показа'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активно'
    )
    max_impressions_per_day = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        verbose_name='Лимит показов в день',
        help_text='Оставьте пустым для неограниченных показов'
    )
    current_impressions = models.IntegerField(
        default=0,
        verbose_name='Текущие показы за день'
    )
    last_reset_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Дата последнего сброса'
    )
    
    class Meta:
        verbose_name = 'Расписание показа'
        verbose_name_plural = 'Расписания показа'
        ordering = ['banner', 'day_of_week', 'start_time']
        db_table = 'advertising_schedule'
    
    def __str__(self):
        day_str = dict(self.DAYS_OF_WEEK).get(self.day_of_week, 'Каждый день')
        return f"{self.banner.name} - {day_str} {self.start_time}-{self.end_time}"
    
    def should_reset_counter(self):
        """Проверить, нужно ли сбросить счетчик показов"""
        today = timezone.now().date()
        return self.last_reset_date is None or self.last_reset_date < today
    
    def reset_counter_if_needed(self):
        """Сбросить счетчик если нужно"""
        if self.should_reset_counter():
            self.current_impressions = 0
            self.last_reset_date = timezone.now().date()
            self.save(update_fields=['current_impressions', 'last_reset_date'])
    
    def can_show(self):
        """Проверить, можно ли показывать баннер сейчас"""
        if not self.is_active:
            return False
        
        now = timezone.now()
        current_time = now.time()
        current_day = now.weekday()
        
        # Проверка дня недели
        if self.day_of_week is not None and self.day_of_week != current_day:
            return False
        
        # Проверка времени
        if not (self.start_time <= current_time <= self.end_time):
            return False
        
        # Проверка лимита показов
        if self.max_impressions_per_day is not None:
            self.reset_counter_if_needed()
            if self.current_impressions >= self.max_impressions_per_day:
                return False
        
        return True


class ContextAd(models.Model):
    """Контекстная реклама в статьях"""
    
    INSERTION_TYPES = [
        ('permanent', 'Постоянная'),
        ('temporary', 'Временная'),
    ]
    
    campaign = models.ForeignKey(
        AdCampaign,
        on_delete=models.CASCADE,
        related_name='context_ads',
        verbose_name='Кампания'
    )
    keyword_phrase = models.CharField(
        max_length=200,
        verbose_name='Ключевая фраза',
        help_text='Фраза для поиска в тексте статей'
    )
    anchor_text = models.CharField(
        max_length=200,
        verbose_name='Текст ссылки',
        help_text='Текст, который будет отображаться как ссылка'
    )
    target_url = models.URLField(
        verbose_name='Целевой URL'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активно'
    )
    insertion_type = models.CharField(
        max_length=20,
        choices=INSERTION_TYPES,
        default='permanent',
        verbose_name='Тип вставки'
    )
    expire_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Дата истечения',
        help_text='Для временных вставок'
    )
    cost_per_click = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Стоимость за клик',
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    priority = models.IntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        verbose_name='Приоритет'
    )
    max_insertions_per_article = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name='Макс. вставок в одной статье'
    )
    clicks = models.IntegerField(
        default=0,
        verbose_name='Кликов'
    )
    impressions = models.IntegerField(
        default=0,
        verbose_name='Показов'
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
        verbose_name = 'Контекстная реклама'
        verbose_name_plural = 'Контекстная реклама'
        ordering = ['-priority', '-created_at']
        db_table = 'advertising_context_ad'
    
    def __str__(self):
        return f"{self.keyword_phrase} → {self.anchor_text}"
    
    def is_active_now(self):
        """Проверка, активна ли реклама сейчас"""
        if not self.is_active:
            return False
        if self.insertion_type == 'temporary' and self.expire_date:
            return timezone.now().date() <= self.expire_date
        return True
    
    def get_ctr(self):
        """Рассчитать CTR"""
        if self.impressions == 0:
            return 0
        return (self.clicks / self.impressions) * 100


class AdInsertion(models.Model):
    """Таблица вставок контекстной рекламы в статьи"""
    
    context_ad = models.ForeignKey(
        ContextAd,
        on_delete=models.CASCADE,
        related_name='insertions',
        verbose_name='Контекстная реклама'
    )
    post = models.ForeignKey(
        'blog.Post',
        on_delete=models.CASCADE,
        related_name='ad_insertions',
        verbose_name='Статья'
    )
    inserted_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата вставки'
    )
    inserted_by = models.CharField(
        max_length=100,
        verbose_name='Кто вставил',
        help_text='Имя пользователя или "AI"'
    )
    insertion_position = models.IntegerField(
        verbose_name='Позиция в тексте',
        help_text='Номер параграфа или позиция символа'
    )
    anchor_text_used = models.CharField(
        max_length=200,
        verbose_name='Использованный текст'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активна'
    )
    clicks = models.IntegerField(
        default=0,
        verbose_name='Кликов по этой вставке'
    )
    views = models.IntegerField(
        default=0,
        verbose_name='Показов'
    )
    removed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата удаления'
    )
    removal_reason = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Причина удаления'
    )
    
    class Meta:
        verbose_name = 'Вставка рекламы'
        verbose_name_plural = 'Вставки рекламы'
        ordering = ['-inserted_at']
        db_table = 'advertising_insertion'
    
    def __str__(self):
        return f"{self.context_ad.anchor_text} в {self.post.title}"
    
    def get_article_link(self):
        """Ссылка на статью с якорем к месту вставки"""
        return f"{self.post.get_absolute_url()}#ad-insertion-{self.id}"
    
    def get_ctr(self):
        """CTR для конкретной вставки"""
        if self.views == 0:
            return 0
        return (self.clicks / self.views) * 100


class AdClick(models.Model):
    """Отслеживание кликов по рекламе"""
    
    ad_banner = models.ForeignKey(
        AdBanner,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='click_records',
        verbose_name='Баннер'
    )
    context_ad = models.ForeignKey(
        ContextAd,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='click_records',
        verbose_name='Контекстная реклама'
    )
    ad_insertion = models.ForeignKey(
        AdInsertion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='click_records',
        verbose_name='Вставка'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Пользователь'
    )
    session_key = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Ключ сессии'
    )
    ip_address = models.GenericIPAddressField(
        verbose_name='IP адрес'
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name='User Agent'
    )
    clicked_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата клика',
        db_index=True
    )
    referer = models.URLField(
        blank=True,
        verbose_name='Откуда пришел'
    )
    redirect_url = models.URLField(
        verbose_name='Куда перешел'
    )
    
    class Meta:
        verbose_name = 'Клик по рекламе'
        verbose_name_plural = 'Клики по рекламе'
        ordering = ['-clicked_at']
        db_table = 'advertising_click'
        indexes = [
            models.Index(fields=['-clicked_at']),
            models.Index(fields=['ip_address', '-clicked_at']),
        ]
    
    def __str__(self):
        if self.ad_banner:
            return f"Клик по баннеру {self.ad_banner.name} в {self.clicked_at}"
        elif self.context_ad:
            return f"Клик по контексту {self.context_ad.anchor_text} в {self.clicked_at}"
        return f"Клик в {self.clicked_at}"


class AdImpression(models.Model):
    """Отслеживание показов рекламы"""
    
    VIEWPORT_POSITIONS = [
        ('top', 'Вверху'),
        ('middle', 'В середине'),
        ('bottom', 'Внизу'),
    ]
    
    ad_banner = models.ForeignKey(
        AdBanner,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='impression_records',
        verbose_name='Баннер'
    )
    context_ad = models.ForeignKey(
        ContextAd,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='impression_records',
        verbose_name='Контекстная реклама'
    )
    ad_insertion = models.ForeignKey(
        AdInsertion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='impression_records',
        verbose_name='Вставка'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Пользователь'
    )
    session_key = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Ключ сессии'
    )
    ip_address = models.GenericIPAddressField(
        verbose_name='IP адрес'
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name='User Agent'
    )
    shown_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата показа',
        db_index=True
    )
    viewport_position = models.CharField(
        max_length=10,
        choices=VIEWPORT_POSITIONS,
        blank=True,
        verbose_name='Позиция во viewport'
    )
    time_visible = models.IntegerField(
        default=0,
        verbose_name='Время видимости (сек)'
    )
    
    class Meta:
        verbose_name = 'Показ рекламы'
        verbose_name_plural = 'Показы рекламы'
        ordering = ['-shown_at']
        db_table = 'advertising_impression'
        indexes = [
            models.Index(fields=['-shown_at']),
            models.Index(fields=['ip_address', '-shown_at']),
        ]
    
    def __str__(self):
        if self.ad_banner:
            return f"Показ баннера {self.ad_banner.name} в {self.shown_at}"
        elif self.context_ad:
            return f"Показ контекста {self.context_ad.anchor_text} в {self.shown_at}"
        return f"Показ в {self.shown_at}"


class AdPerformanceML(models.Model):
    """Данные для машинного обучения"""
    
    DEVICE_TYPES = [
        ('desktop', 'Desktop'),
        ('mobile', 'Mobile'),
        ('tablet', 'Tablet'),
    ]
    
    USER_TYPES = [
        ('guest', 'Гость'),
        ('registered', 'Зарегистрирован'),
        ('author', 'Автор'),
    ]
    
    ad_place = models.ForeignKey(
        AdPlace,
        on_delete=models.CASCADE,
        related_name='ml_records',
        verbose_name='Место размещения'
    )
    banner = models.ForeignKey(
        AdBanner,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='ml_records',
        verbose_name='Баннер'
    )
    context_ad = models.ForeignKey(
        ContextAd,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='ml_records',
        verbose_name='Контекстная реклама'
    )
    date = models.DateField(
        verbose_name='Дата',
        db_index=True
    )
    hour = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(23)],
        verbose_name='Час'
    )
    day_of_week = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(6)],
        verbose_name='День недели'
    )
    impressions = models.IntegerField(
        default=0,
        verbose_name='Показы'
    )
    clicks = models.IntegerField(
        default=0,
        verbose_name='Клики'
    )
    ctr = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='CTR (%)'
    )
    revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Доход'
    )
    category = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Категория статьи'
    )
    device_type = models.CharField(
        max_length=10,
        choices=DEVICE_TYPES,
        default='desktop',
        verbose_name='Тип устройства'
    )
    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPES,
        default='guest',
        verbose_name='Тип пользователя'
    )
    effectiveness_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Оценка эффективности'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Создано'
    )
    
    class Meta:
        verbose_name = 'Данные ML'
        verbose_name_plural = 'Данные для ML'
        ordering = ['-date', '-hour']
        db_table = 'advertising_ml_performance'
        indexes = [
            models.Index(fields=['date', 'hour']),
            models.Index(fields=['ad_place', 'date']),
        ]
    
    def __str__(self):
        return f"{self.ad_place.name} - {self.date} {self.hour}:00"


class AdRecommendation(models.Model):
    """Рекомендации AI по размещению рекламы"""
    
    RECOMMENDATION_TYPES = [
        ('banner', 'Баннер'),
        ('context', 'Контекстная реклама'),
    ]
    
    recommended_for = models.CharField(
        max_length=20,
        choices=RECOMMENDATION_TYPES,
        verbose_name='Для чего'
    )
    place = models.ForeignKey(
        AdPlace,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='recommendations',
        verbose_name='Место размещения'
    )
    post = models.ForeignKey(
        'blog.Post',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='ad_recommendations',
        verbose_name='Статья'
    )
    campaign = models.ForeignKey(
        AdCampaign,
        on_delete=models.CASCADE,
        related_name='recommendations',
        verbose_name='Кампания'
    )
    confidence_score = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Уверенность AI (%)'
    )
    predicted_ctr = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name='Предсказанный CTR (%)'
    )
    predicted_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Предсказанный доход'
    )
    recommendation_reason = models.TextField(
        verbose_name='Причина рекомендации'
    )
    is_applied = models.BooleanField(
        default=False,
        verbose_name='Применена'
    )
    actual_ctr = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Фактический CTR (%)'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    applied_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата применения'
    )
    
    class Meta:
        verbose_name = 'Рекомендация AI'
        verbose_name_plural = 'Рекомендации AI'
        ordering = ['-confidence_score', '-predicted_revenue']
        db_table = 'advertising_recommendation'
    
    def __str__(self):
        return f"Рекомендация для {self.campaign.name} (уверенность: {self.confidence_score}%)"
    
    def apply_recommendation(self):
        """Применить рекомендацию"""
        self.is_applied = True
        self.applied_at = timezone.now()
        self.save(update_fields=['is_applied', 'applied_at'])


class AdActionLog(models.Model):
    """Журнал действий с рекламой"""
    
    ACTION_TYPES = [
        ('create', 'Создание'),
        ('update', 'Изменение'),
        ('delete', 'Удаление'),
        ('activate', 'Активация'),
        ('deactivate', 'Деактивация'),
        ('insert', 'Вставка в статью'),
        ('remove', 'Удаление из статьи'),
    ]
    
    action_type = models.CharField(
        max_length=20,
        choices=ACTION_TYPES,
        verbose_name='Тип действия'
    )
    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Кто выполнил',
        help_text='Пользователь, выполнивший действие'
    )
    performed_by_ai = models.BooleanField(
        default=False,
        verbose_name='Выполнено AI',
        help_text='True если действие выполнено AI-агентом'
    )
    
    target_type = models.CharField(
        max_length=50,
        verbose_name='Тип объекта',
        help_text='banner, context_ad, insertion, campaign и т.д.'
    )
    target_id = models.IntegerField(
        verbose_name='ID объекта'
    )
    target_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Название объекта',
        help_text='Для удобства отображения'
    )
    
    old_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name='Старые данные',
        help_text='JSON со старыми значениями полей'
    )
    new_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name='Новые данные',
        help_text='JSON с новыми значениями полей'
    )
    
    description = models.TextField(
        verbose_name='Описание действия'
    )
    can_revert = models.BooleanField(
        default=True,
        verbose_name='Можно отменить',
        help_text='True если действие можно отменить'
    )
    reverted = models.BooleanField(
        default=False,
        verbose_name='Отменено'
    )
    reverted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата отмены'
    )
    reverted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reverted_ad_actions',
        verbose_name='Кто отменил'
    )
    
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата и время',
        db_index=True
    )
    
    class Meta:
        verbose_name = 'Действие с рекламой'
        verbose_name_plural = 'Журнал действий с рекламой'
        ordering = ['-timestamp']
        db_table = 'advertising_action_log'
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['target_type', 'target_id']),
            models.Index(fields=['performed_by_ai', '-timestamp']),
        ]
    
    def __str__(self):
        actor = "AI" if self.performed_by_ai else (self.performed_by.username if self.performed_by else "Система")
        return f"{self.get_action_type_display()} - {self.target_type} #{self.target_id} [{actor}] {self.timestamp.strftime('%d.%m.%Y %H:%M')}"
    
    def can_be_reverted(self):
        """Проверить, можно ли отменить действие"""
        return self.can_revert and not self.reverted
    
    def revert(self, user=None):
        """Отменить действие"""
        if not self.can_be_reverted():
            return False, "Действие не может быть отменено"
        
        # Помечаем как отменённое
        self.reverted = True
        self.reverted_at = timezone.now()
        self.reverted_by = user
        self.save(update_fields=['reverted', 'reverted_at', 'reverted_by'])
        
        return True, "Действие отменено"


class ExternalScript(models.Model):
    """Внешние скрипты (счетчики, реклама от других сетей)"""
    
    SCRIPT_POSITIONS = [
        ('head_start', 'Начало <head>'),
        ('head_end', 'Конец <head>'),
        ('body_start', 'Начало <body>'),
        ('body_end', 'Конец <body>'),
    ]
    
    SCRIPT_TYPES = [
        ('analytics', 'Аналитика/Счетчик'),
        ('advertising', 'Реклама'),
        ('pixel', 'Пиксель отслеживания'),
        ('other', 'Другое'),
    ]
    
    name = models.CharField(
        max_length=200,
        verbose_name='Название',
        help_text='Название скрипта для внутреннего использования'
    )
    script_type = models.CharField(
        max_length=20,
        choices=SCRIPT_TYPES,
        default='other',
        verbose_name='Тип скрипта'
    )
    code = models.TextField(
        verbose_name='Код скрипта',
        help_text='Полный HTML/JavaScript код для вставки'
    )
    position = models.CharField(
        max_length=20,
        choices=SCRIPT_POSITIONS,
        default='head_end',
        verbose_name='Позиция на странице'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен',
        help_text='Включить/выключить скрипт на сайте'
    )
    priority = models.IntegerField(
        default=10,
        verbose_name='Приоритет',
        help_text='Порядок загрузки (меньше = раньше)'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание',
        help_text='Для чего этот скрипт'
    )
    provider = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Провайдер',
        help_text='Название сервиса (например, ACINT, Google Analytics)'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата добавления'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата изменения'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Кто добавил'
    )
    
    class Meta:
        verbose_name = 'Внешний скрипт'
        verbose_name_plural = 'Внешние скрипты'
        ordering = ['position', 'priority', '-created_at']
        db_table = 'advertising_external_script'
    
    def __str__(self):
        return f"{self.name} ({self.get_script_type_display()})"
    
    def get_safe_code(self):
        """Получить код для безопасной вставки в шаблон"""
        return self.code.strip()


class AdsTxtSettings(models.Model):
    """Настройки и содержимое файла ads.txt для Ezoic"""
    
    # Основные настройки
    domain = models.CharField(
        max_length=200,
        default='idealimage.ru',
        verbose_name='Домен',
        help_text='Домен сайта для ads.txt'
    )
    
    ezoic_manager_url = models.URLField(
        max_length=500,
        default='https://srv.adstxtmanager.com/19390/idealimage.ru',
        verbose_name='URL менеджера Ezoic',
        help_text='URL для получения ads.txt от Ezoic'
    )
    
    # Содержимое файла
    content = models.TextField(
        blank=True,
        verbose_name='Содержимое ads.txt',
        help_text='Текущее содержимое файла ads.txt'
    )
    
    # Настройки обновления
    auto_update = models.BooleanField(
        default=True,
        verbose_name='Автоматическое обновление',
        help_text='Автоматически обновлять файл от Ezoic'
    )
    
    update_interval_hours = models.IntegerField(
        default=24,
        verbose_name='Интервал обновления (часы)',
        help_text='Как часто обновлять файл (в часах)'
    )
    
    # Статус
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен',
        help_text='Включить/выключить ads.txt'
    )
    
    # Логирование
    last_update_attempt = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Последняя попытка обновления'
    )
    
    last_successful_update = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Последнее успешное обновление'
    )
    
    last_error = models.TextField(
        blank=True,
        verbose_name='Последняя ошибка',
        help_text='Текст последней ошибки при обновлении'
    )
    
    update_count = models.IntegerField(
        default=0,
        verbose_name='Количество обновлений',
        help_text='Счётчик успешных обновлений'
    )
    
    # Даты
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    
    class Meta:
        verbose_name = 'Настройки ads.txt'
        verbose_name_plural = 'Настройки ads.txt'
        db_table = 'advertising_ads_txt_settings'
    
    def __str__(self):
        return f"ads.txt для {self.domain}"
    
    def update_from_ezoic(self):
        """Обновить содержимое файла от Ezoic"""
        try:
            import requests
        except ImportError:
            # Если requests не установлен, используем urllib
            try:
                from urllib.request import urlopen
                from urllib.error import URLError
            except ImportError:
                return False, "Не установлены библиотеки для HTTP запросов (requests или urllib)"
        
        from django.utils import timezone
        
        self.last_update_attempt = timezone.now()
        
        try:
            # Пробуем использовать requests
            if 'requests' in globals() or 'requests' in __import__('sys').modules:
                response = requests.get(
                    self.ezoic_manager_url,
                    timeout=10,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (compatible; IdealImage.ru ads.txt updater)'
                    }
                )
                response.raise_for_status()
                new_content = response.text.strip()
            else:
                # Fallback на urllib
                from urllib.request import urlopen, Request
                from urllib.error import URLError
                
                req = Request(
                    self.ezoic_manager_url,
                    headers={'User-Agent': 'Mozilla/5.0 (compatible; IdealImage.ru ads.txt updater)'}
                )
                with urlopen(req, timeout=10) as response:
                    new_content = response.read().decode('utf-8').strip()
            
            # Проверяем, что это валидный ads.txt
            if not new_content or len(new_content) < 10:
                raise ValueError("Получено пустое или слишком короткое содержимое")
            
            # Сохраняем
            self.content = new_content
            self.last_successful_update = timezone.now()
            self.last_error = ''
            self.update_count += 1
            self.save(update_fields=[
                'content', 'last_successful_update', 'last_update_attempt',
                'last_error', 'update_count', 'updated_at'
            ])
            
            return True, "Файл успешно обновлён"
            
        except Exception as e:
            error_msg = f"Ошибка: {str(e)}"
            self.last_error = error_msg
            self.save(update_fields=['last_update_attempt', 'last_error', 'updated_at'])
            return False, error_msg
    
    def needs_update(self):
        """Проверить, нужно ли обновление (оптимизировано)"""
        if not self.auto_update:
            return False
        
        if not self.last_successful_update:
            return True
        
        from django.utils import timezone
        from datetime import timedelta
        
        # Кэшируем результат проверки на 1 минуту
        from django.core.cache import cache
        cache_key = f'ads_txt_needs_update_{self.id}'
        cached_result = cache.get(cache_key)
        
        if cached_result is not None:
            return cached_result
        
        next_update = self.last_successful_update + timedelta(hours=self.update_interval_hours)
        result = timezone.now() >= next_update
        
        # Кэшируем на 1 минуту
        cache.set(cache_key, result, 60)
        
        return result
    
    def get_content(self):
        """Получить содержимое файла (с fallback)"""
        if self.content:
            return self.content
        
        # Fallback на дефолтное содержимое Ezoic
        return f"""# ads.txt для {self.domain}
# Автоматически управляется Ezoic
# Обновление: {self.last_successful_update.strftime('%Y-%m-%d %H:%M') if self.last_successful_update else 'Никогда'}
"""