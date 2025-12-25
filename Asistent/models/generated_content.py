"""
Модели: AIGeneratedArticle
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class AIGeneratedArticle(models.Model):
    
    schedule = models.ForeignKey('schedule.AISchedule', on_delete=models.SET_NULL, null=True, blank=True, related_name='generated_articles', verbose_name="Расписание")
    article = models.ForeignKey('blog.Post', on_delete=models.CASCADE, related_name='ai_generation_info', verbose_name="Статья")
    source_urls = models.TextField(blank=True, verbose_name="Источники")
    prompt = models.TextField(blank=True, verbose_name="Промпт")
    ai_response = models.TextField(blank=True, verbose_name="Ответ AI")
    generation_time_seconds = models.IntegerField(default=0, verbose_name="Время генерации (сек)")
    api_calls_count = models.IntegerField(default=0, verbose_name="Количество API вызовов")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата генерации")
    
    class Meta:
        verbose_name = "AI-статья"
        verbose_name_plural = "AI-статьи"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"AI: {self.article.title}"



