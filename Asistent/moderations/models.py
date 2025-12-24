"""
Упрощённые модели модерации без излишеств.

Убраны:
- Сложные JSON-конфигурации
- Матрицы правил
- Множественные наборы критериев

Оставлено:
- Простые настройки с чекбоксами
- Простой журнал проверок
"""
from django.db import models
from django.contrib.auth.models import User


class ArticleModerationSettings(models.Model):
    """Простые настройки модерации статей - только чекбоксы и пороги."""
    
    # Основное
    name = models.CharField(
        max_length=200,
        verbose_name="Название профиля",
        default="Основной профиль"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активен",
        help_text="Будет использоваться для проверки статей"
    )
    
    # Простые проверки (чекбоксы)
    check_title = models.BooleanField(
        default=True,
        verbose_name="Проверять заголовок",
        help_text="Заголовок не должен быть пустым"
    )
    check_image = models.BooleanField(
        default=True,
        verbose_name="Проверять наличие изображения",
        help_text="Статья должна содержать изображение"
    )
    check_category = models.BooleanField(
        default=True,
        verbose_name="Проверять категорию",
        help_text="У статьи должна быть выбрана категория"
    )
    check_length = models.BooleanField(
        default=True,
        verbose_name="Проверять длину текста",
        help_text="Проверять минимальное количество слов"
    )
    check_profanity = models.BooleanField(
        default=False,
        verbose_name="Проверять мат",
        help_text="Простая проверка на наличие матерных слов"
    )
    
    # Простые пороги
    min_words = models.IntegerField(
        default=300,
        verbose_name="Минимум слов",
        help_text="Минимальное количество слов в статье"
    )
    min_title_length = models.IntegerField(
        default=10,
        verbose_name="Минимум символов в заголовке",
        help_text="Минимальная длина заголовка"
    )
    
    # Даты
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлён")
    
    class Meta:
        app_label = "Moderation"
        db_table = "asistent_articlemoderationsettings"
        verbose_name = "📝 Модерация: Настройки статей"
        verbose_name_plural = "📝 Модерация: Настройки статей"
        ordering = ["-is_active", "-updated_at"]
    
    def __str__(self):
        status = "✅" if self.is_active else "⏸"
        return f"{status} {self.name}"


class CommentModerationSettings(models.Model):
    """Простые настройки модерации комментариев - только чекбоксы."""
    
    # Основное
    name = models.CharField(
        max_length=200,
        verbose_name="Название профиля",
        default="Основной профиль"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активен",
        help_text="Будет использоваться для проверки комментариев"
    )
    
    # Простые проверки
    block_urls = models.BooleanField(
        default=True,
        verbose_name="Блокировать ссылки",
        help_text="Запретить комментарии с http://, https://, www."
    )
    block_html = models.BooleanField(
        default=True,
        verbose_name="Блокировать HTML-теги",
        help_text="Запретить комментарии с HTML-разметкой"
    )
    block_short = models.BooleanField(
        default=True,
        verbose_name="Блокировать короткие",
        help_text="Запретить слишком короткие комментарии"
    )
    check_spam = models.BooleanField(
        default=True,
        verbose_name="Проверять на спам",
        help_text="Простая проверка спам-слов"
    )
    
    # Простые пороги
    min_length = models.IntegerField(
        default=10,
        verbose_name="Минимум символов",
        help_text="Минимальная длина комментария"
    )
    
    # Простой список стоп-слов
    forbidden_words = models.TextField(
        blank=True,
        verbose_name="Запрещённые слова",
        help_text="Список через запятую: купить, казино, спам, реклама"
    )
    
    # Даты
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлён")
    
    class Meta:
        app_label = "Moderation"
        db_table = "asistent_commentmoderationsettings"
        verbose_name = "💬 Модерация: Настройки комментариев"
        verbose_name_plural = "💬 Модерация: Настройки комментариев"
        ordering = ["-is_active", "-updated_at"]
    
    def __str__(self):
        status = "✅" if self.is_active else "⏸"
        return f"{status} {self.name}"


class ModerationLog(models.Model):
    """Простой журнал проверок модерации."""
    
    CONTENT_TYPE_CHOICES = [
        ('article', 'Статья'),
        ('comment', 'Комментарий'),
    ]
    
    # Что проверяли
    content_type = models.CharField(
        max_length=20,
        choices=CONTENT_TYPE_CHOICES,
        default='article',
        verbose_name="Тип контента"
    )
    object_id = models.IntegerField(
        default=0,
        verbose_name="ID объекта",
        help_text="ID статьи или комментария"
    )
    
    # Результат
    passed = models.BooleanField(
        default=False,
        verbose_name="Пройдена",
        help_text="True = пройдена, False = отклонена"
    )
    problems = models.TextField(
        blank=True,
        verbose_name="Список проблем",
        help_text="Причины отклонения (по одной на строке)"
    )
    
    # Кто/когда
    moderator = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Модератор",
        help_text="Кто выполнил проверку (NULL = автомат)"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата проверки"
    )
    
    class Meta:
        app_label = "Moderation"
        db_table = "asistent_moderationlog"
        verbose_name = "📋 Модерация: Журнал проверок"
        verbose_name_plural = "📋 Модерация: Журнал проверок"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['passed']),
        ]
    
    def __str__(self):
        icon = "✅" if self.passed else "❌"
        return f"{icon} {self.get_content_type_display()} #{self.object_id}"
    
    def get_problems_list(self):
        """Возвращает список проблем как список строк."""
        if not self.problems:
            return []
        return [p.strip() for p in self.problems.split('\n') if p.strip()]


class ArticleRegeneration(models.Model):
    """Модель для отслеживания регенерации старых статей."""
    
    STATUS_CHOICES = [
        ('pending', 'В обработке'),
        ('completed', 'Завершено'),
        ('failed', 'Ошибка'),
    ]
    
    original_article = models.ForeignKey(
        'blog.Post',
        on_delete=models.CASCADE,
        related_name='regenerations',
        verbose_name='Оригинальная статья'
    )
    
    regenerated_article = models.ForeignKey(
        'blog.Post',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='regenerated_from',
        verbose_name='Регенерированная статья'
    )
    
    regenerated_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата регенерации'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Статус'
    )
    
    regeneration_notes = models.TextField(
        blank=True,
        verbose_name='Заметки о регенерации',
        help_text='Дополнительная информация о процессе регенерации'
    )
    
    class Meta:
        app_label = "Moderation"
        db_table = "asistent_articleregeneration"
        verbose_name = "🔄 Регенерация статей"
        verbose_name_plural = "🔄 Регенерация статей"
        ordering = ['-regenerated_at']
        indexes = [
            models.Index(fields=['-regenerated_at']),
            models.Index(fields=['status']),
            models.Index(fields=['original_article']),
        ]
    
    def __str__(self):
        status_icon = {
            'pending': '⏳',
            'completed': '✅',
            'failed': '❌'
        }.get(self.status, '❓')
        return f"{status_icon} {self.original_article.title} → {self.regenerated_at.strftime('%d.%m.%Y')}"