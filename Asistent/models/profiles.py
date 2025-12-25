"""
Модели: AuthorStyleProfile, BotProfile, BotActivity
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class AuthorStyleProfile(models.Model):
    
    profile = models.OneToOneField(
        'Visitor.Profile',
        on_delete=models.CASCADE,
        related_name='style_profile',
        verbose_name="Профиль",
        null=True,
        blank=True,
    )
    style_name = models.CharField(max_length=200, blank=True, null=True, default='', verbose_name="Название стиля", help_text='Например: "Легкий и вдохновляющий", "Экспертный научный"')
    style_analysis = models.JSONField(default=dict, blank=True, null=True, verbose_name="Анализ стиля", help_text="Результат автоматического анализа статей автора")
    top_articles = models.ManyToManyField('blog.Post', blank=True, verbose_name="Лучшие статьи для обучения")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    usage_count = models.IntegerField(default=0, verbose_name="Использований")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")   
    
    def get_style_prompt(self):
        """
        Генерирует текст для промпта на основе анализа
        
        Returns:
            str: Описание стиля для AI
        """
        from Asistent.style_analyzer import StyleAnalyzer
        
        analyzer = StyleAnalyzer()
        return analyzer.generate_style_prompt(self.style_analysis)
    
    def update_analysis(self, limit=10):
        """
        Обновляет анализ стиля на основе последних статей
        
        Args:
            limit: Количество статей для анализа
        """
        from Asistent.style_analyzer import StyleAnalyzer
        import logging
        
        logger = logging.getLogger(__name__)
        analyzer = StyleAnalyzer()
        self.style_analysis = analyzer.analyze_author_style(self.author, limit=limit)
        self.save()
        
        logger.info(f"✅ Обновлен профиль стиля @{self.author.username}")



class BotProfile(models.Model):
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='bot_profile',
        verbose_name='Пользователь'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен'
    )
    
    bot_name = models.CharField(
        max_length=100,
        verbose_name='Имя бота',
        help_text='Отображаемое имя для комментариев'
    )
    
    comment_style = models.CharField(
        max_length=50,
        choices=[
            ('formal', 'Формальный'),
            ('casual', 'Неформальный'),
            ('friendly', 'Дружелюбный'),
            ('expert', 'Экспертный'),
            ('humorous', 'Юмористический'),
        ],
        default='friendly',
        verbose_name='Стиль комментирования'
    )
    
    comment_templates = models.JSONField(
        default=list,
        verbose_name='Шаблоны комментариев',
        help_text='Список шаблонов для генерации комментариев'
    )
    
    max_comments_per_day = models.IntegerField(
        default=10,
        verbose_name='Максимум комментариев в день'
    )
    
    max_likes_per_day = models.IntegerField(
        default=20,
        verbose_name='Максимум лайков в день'
    )
    
    preferred_categories = models.JSONField(
        default=list,
        verbose_name='Предпочитаемые категории',
        help_text='Категории статей для комментирования'
    )
    
    avoid_categories = models.JSONField(
        default=list,
        verbose_name='Избегаемые категории',
        help_text='Категории статей, которые бот не комментирует'
    )
    
    min_article_views = models.IntegerField(
        default=100,
        verbose_name='Минимальные просмотры статьи',
        help_text='Комментировать только статьи с таким количеством просмотров'
    )
    
    comment_probability = models.FloatField(
        default=0.3,
        verbose_name='Вероятность комментирования',
        help_text='От 0.0 до 1.0'
    )
    
    like_probability = models.FloatField(
        default=0.5,
        verbose_name='Вероятность лайка',
        help_text='От 0.0 до 1.0'
    )
    
    last_activity = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Последняя активность'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    
    class Meta:
        verbose_name = 'Профиль бота'
        verbose_name_plural = 'Профили ботов'
    
    def __str__(self):
        return f"{self.bot_name} ({self.user.username})"
    
    def can_comment_today(self):
        """Можно ли комментировать сегодня"""
        from django.utils import timezone
        from django.db.models import Count
        
        today = timezone.now().date()
        today_comments = self.user.comments.filter(
            created_at__date=today
        ).count()
        
        return today_comments < self.max_comments_per_day
    
    def can_like_today(self):
        """Можно ли лайкать сегодня"""
        from django.utils import timezone
        from blog.models import PostLike
        
        today = timezone.now().date()
        today_likes = PostLike.objects.filter(
            user=self.user,
            created_at__date=today
        ).count()
        
        return today_likes < self.max_likes_per_day
    
    def get_random_comment_template(self):
        """Получить случайный шаблон комментария"""
        import random
        
        if not self.comment_templates:
            return "Интересная статья!"
        
        return random.choice(self.comment_templates)



class BotActivity(models.Model):
    
    ACTION_CHOICES = [
        ('comment', 'Комментарий'),
        ('like', 'Лайк'),
        ('skip', 'Пропуск'),
    ]
    
    bot_profile = models.ForeignKey(
        BotProfile,
        on_delete=models.CASCADE,
        related_name='activities',
        verbose_name='Профиль бота'
    )
    
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        verbose_name='Действие'
    )
    
    article = models.ForeignKey(
        'blog.Post',
        on_delete=models.CASCADE,
        related_name='bot_activities',
        verbose_name='Статья'
    )
    
    content = models.TextField(
        blank=True,
        verbose_name='Содержание',
        help_text='Текст комментария или причина пропуска'
    )
    
    success = models.BooleanField(
        default=True,
        verbose_name='Успешно'
    )
    
    error_message = models.TextField(
        blank=True,
        verbose_name='Сообщение об ошибке'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата действия'
    )
    
    class Meta:
        verbose_name = 'Активность бота'
        verbose_name_plural = 'Активности ботов'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.bot_profile.bot_name} - {self.get_action_display()} - {self.article.title[:50]}"




