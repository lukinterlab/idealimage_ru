"""
Модели для системы лайков и реакций
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()


class Like(models.Model):
    """Модель лайков для статей"""
    
    REACTION_TYPES = (
        ('like', '👍 Нравится'),
        ('love', '❤️ Люблю'),
        ('laugh', '😂 Смешно'),
        ('wow', '😮 Удивляюсь'),
        ('sad', '😢 Грустно'),
        ('angry', '😠 Злюсь'),
    )
    
    post = models.ForeignKey('blog.Post', on_delete=models.CASCADE, related_name='likes', verbose_name='Статья')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='likes', verbose_name='Пользователь', null=True, blank=True)
    session_key = models.CharField(max_length=40, verbose_name='Ключ сессии', null=True, blank=True)
    reaction_type = models.CharField(max_length=10, choices=REACTION_TYPES, default='like', verbose_name='Тип реакции')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    
    def __str__(self):
        if self.user:
            return f'{self.user.username} - {self.get_reaction_type_display()} на {self.post.title}'
        else:
            return f'Анонимный пользователь ({self.session_key[:8]}...) - {self.get_reaction_type_display()} на {self.post.title}'
    
    class Meta:
        db_table = 'app_likes'
        constraints = [
            # Один зарегистрированный пользователь может поставить только одну реакцию
            models.UniqueConstraint(
                fields=['post', 'user'],
                condition=models.Q(user__isnull=False),
                name='unique_like_per_user'
            ),
            # Один анонимный пользователь (по session_key) может поставить только одну реакцию
            models.UniqueConstraint(
                fields=['post', 'session_key'],
                condition=models.Q(session_key__isnull=False),
                name='unique_like_per_session'
            ),
        ]
        indexes = [
            models.Index(fields=['post', 'reaction_type']),
            models.Index(fields=['user', 'created']),
            models.Index(fields=['post', 'session_key']),
        ]
        verbose_name = 'Лайк'
        verbose_name_plural = 'Лайки'


class PostRating(models.Model):
    """Модель рейтинга статей"""
    
    post = models.ForeignKey('blog.Post', on_delete=models.CASCADE, related_name='ratings', verbose_name='Статья')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ratings', verbose_name='Пользователь')
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Рейтинг'
    )
    created = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    class Meta:
        db_table = 'app_post_ratings'
        unique_together = ('post', 'user')  # Один пользователь может поставить только один рейтинг
        indexes = [
            models.Index(fields=['post', 'rating']),
            models.Index(fields=['user', 'created']),
        ]
        verbose_name = 'Рейтинг статьи'
        verbose_name_plural = 'Рейтинги статей'
    
    def __str__(self):
        return f'{self.user.username} - {self.rating}/5 для {self.post.title}'


class Bookmark(models.Model):
    """Модель закладок для статей"""
    
    post = models.ForeignKey('blog.Post', on_delete=models.CASCADE, related_name='bookmarks', verbose_name='Статья')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks', verbose_name='Пользователь')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    
    class Meta:
        db_table = 'app_bookmarks'
        unique_together = ('post', 'user')  # Один пользователь может добавить статью в закладки только один раз
        indexes = [
            models.Index(fields=['user', 'created']),
            models.Index(fields=['post']),
        ]
        verbose_name = 'Закладка'
        verbose_name_plural = 'Закладки'
    
    def __str__(self):
        return f'{self.user.username} - закладка {self.post.title}'
