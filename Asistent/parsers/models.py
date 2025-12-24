"""
Модели для системы парсинга популярных статей.
"""
from django.db import models
from django.utils import timezone


class ParsingCategory(models.Model):
    """Категория/тематика для парсинга статей."""
    
    name = models.CharField(
        max_length=200,
        verbose_name='Название категории',
        help_text='Название категории или тематики для парсинга (например: "Мода", "Красота", "Здоровье")'
    )
    
    search_queries = models.JSONField(
        default=list,
        verbose_name='Поисковые запросы',
        help_text='Список поисковых запросов для поиска статей (JSON массив строк)'
    )
    
    sources = models.JSONField(
        default=list,
        verbose_name='Источники',
        help_text='Список источников для парсинга: ["google", "yandex", "rss", "social"]'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активна',
        help_text='Включена ли эта категория для парсинга'
    )
    
    articles_per_day = models.IntegerField(
        default=5,
        verbose_name='Статей в день',
        help_text='Количество статей для парсинга в день по этой категории'
    )
    
    # Связь с категорией сайта (для распределения спаршенных статей)
    site_category = models.ForeignKey(
        'blog.Category',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='parsing_categories',
        verbose_name='Категория сайта',
        help_text='В какую категорию сайта распределять спаршенные статьи'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Создана'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Обновлена'
    )
    
    class Meta:
        db_table = 'asistent_parsingcategory'
        verbose_name = '📰 Категория парсинга'
        verbose_name_plural = '📰 Категории парсинга'
        ordering = ['-is_active', 'name']
    
    def __str__(self):
        status = "✅" if self.is_active else "⏸"
        return f"{status} {self.name}"


class ParsedArticle(models.Model):
    """Спаршенная статья из интернета."""
    
    STATUS_CHOICES = [
        ('pending', 'На модерации'),
        ('approved', 'Одобрена'),
        ('rejected', 'Отклонена'),
        ('published', 'Опубликована'),
    ]
    
    title = models.CharField(
        max_length=500,
        verbose_name='Заголовок'
    )
    
    content = models.TextField(
        verbose_name='Содержание',
        help_text='Спаршенный текст статьи (~200 слов)'
    )
    
    source_url = models.URLField(
        max_length=1000,
        verbose_name='URL источника'
    )
    
    source_name = models.CharField(
        max_length=200,
        verbose_name='Название источника',
        help_text='Название сайта или источника (например: "vc.ru", "Yandex")'
    )
    
    category = models.ForeignKey(
        'blog.Category',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='parsed_articles',
        verbose_name='Категория сайта'
    )
    
    parsing_category = models.ForeignKey(
        ParsingCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='parsed_articles',
        verbose_name='Категория парсинга'
    )
    
    parsed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата парсинга'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Статус'
    )
    
    selected_for_posting = models.BooleanField(
        default=False,
        verbose_name='Выбрана для публикации',
        help_text='Отмечена модератором для автопостинга'
    )
    
    published_article = models.ForeignKey(
        'blog.Post',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='parsed_source',
        verbose_name='Опубликованная статья',
        help_text='Ссылка на опубликованную статью на сайте'
    )
    
    popularity_score = models.IntegerField(
        default=0,
        verbose_name='Популярность',
        help_text='Оценка популярности статьи (лайки, просмотры и т.д.)'
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name='Заметки',
        help_text='Дополнительные заметки модератора'
    )
    
    class Meta:
        db_table = 'asistent_parsedarticle'
        verbose_name = '📄 Спаршенная статья'
        verbose_name_plural = '📄 Спаршенные статьи'
        ordering = ['-parsed_at', '-popularity_score']
        indexes = [
            models.Index(fields=['-parsed_at']),
            models.Index(fields=['status']),
            models.Index(fields=['selected_for_posting']),
            models.Index(fields=['category', '-parsed_at']),
        ]
    
    def __str__(self):
        status_icon = {
            'pending': '⏳',
            'approved': '✅',
            'rejected': '❌',
            'published': '📤'
        }.get(self.status, '❓')
        return f"{status_icon} {self.title[:50]}..."

