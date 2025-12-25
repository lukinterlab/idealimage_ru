"""
Модели: PromptTemplate, PromptTemplateVersion
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class PromptTemplate(models.Model):
    
    CATEGORY_CHOICES = [
        ('article_single', 'Генерация статьи'),
        ('article_series', 'Генерация серии статей'),
        ('horoscope', 'Генерация гороскопа'),
        ('faq', 'Генерация FAQ'),
        ('comments', 'Генерация комментариев'),
    ]
    
    category = models.CharField(
        blank=True,
        default='article_single',
        null=True,
        max_length=50,
        choices=CATEGORY_CHOICES,
        verbose_name='Категория'
    )
    name = models.CharField(blank=True, null=True, default='', max_length=200, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    debug_script = models.TextField(blank=True, null=True, default='', verbose_name='Скрипт отладки', help_text='Используйте {переменные} для подстановки')    
    template = models.TextField(blank=True, null=True, default='', verbose_name='Шаблон промпта', help_text='Используйте {переменные} для подстановки')
    variables = models.JSONField(default=list, verbose_name='Переменные', help_text='Список доступных переменных')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    usage_count = models.IntegerField(default=0, verbose_name='Количество использований')
    current_version = models.IntegerField(default=1, verbose_name='Текущая версия')
    last_change_summary = models.TextField(blank=True, verbose_name='Последнее описание изменений')
    success_rate = models.FloatField(default=0.0, verbose_name='Процент успеха', help_text='От 0.0 до 1.0')
    created_by = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='prompt_templates', verbose_name='Создал')
    updated_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_prompt_templates', verbose_name='Последний редактор')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    # Поля для полного контроля генерации статей
    blog_category = models.ForeignKey('blog.Category', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Категория в блоге', help_text='В какую категорию публиковать статью')
    default_author = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='authored_prompt_templates', verbose_name='Автор статей', help_text='Кто будет автором сгенерированных статей (если пусто - используется ai_assistant или текущий пользователь)')
    title_criteria = models.TextField(blank=True, verbose_name='Критерии для заголовка', help_text='Инструкции AI как формировать заголовок. Переменные: {zodiac_sign}, {date}, {category}')
    image_source_type = models.CharField(max_length=20, choices=[('upload', 'Загрузить (модератор загружает)'), ('search_db', 'Поиск в нашей базе'), ('parse_web', 'Парсинг из интернета'), ('generate_auto', 'Генерация - на усмотрение AI'), ('generate_custom', 'Генерация - с кастомным промптом'), ('none', 'Без изображения')], default='generate_auto', blank=True, verbose_name='Источник главного изображения')
    image_search_criteria = models.TextField(blank=True, null=True, default='', verbose_name='Критерии поиска изображения', help_text='По каким критериям искать. Если пусто - AI выбирает по категории и названию. Переменные: {zodiac_sign}, {category}, {title}')
    image_generation_criteria = models.TextField(blank=True, null=True, default='', verbose_name='Критерии генерации изображения', help_text='Промпт для генерации. Если пусто - AI выбирает сам. Переменные: {zodiac_sign}, {season}, {category}, {title}')
    auto_process_image = models.BooleanField(default=True, verbose_name='AI обработка изображения', help_text='Переименование по-английски, оптимизация размера, формат, индексация')
    tags_criteria = models.TextField(blank=True, null=True, default='', verbose_name='Критерии для тегов', help_text='Через запятую. В кавычках "слово" = буквально, без кавычек знак_зодиака = подобрать по смыслу. Переменные: {zodiac_sign}, {category}')
    content_source_type = models.CharField(max_length=20, choices=[('parse', 'Парсить из источников + переписать'), ('generate', 'Полностью генерировать AI'), ('hybrid', 'Гибрид: парсить темы + генерировать текст')], default='hybrid', blank=True, verbose_name='Источник контента')
    content_source_urls = models.TextField(blank=True, null=True, default='', verbose_name='URL источников для контента', help_text='По одному на строке. Если пусто - используется из AISchedule')
    parse_first_paragraph = models.BooleanField(default=False, verbose_name='Парсить первый абзац из источников', help_text='Спарсить первый абзац с сайтов и использовать как основу')
    uploaded_media = models.FileField(upload_to='prompt_templates/', null=True, blank=True, verbose_name='Загруженный файл (изображение/видео)', help_text='Для режима "Загрузить (модератор загружает)". AI обработает автоматически')
    
    class Meta:
        verbose_name = 'Шаблон промпта'
        verbose_name_plural = 'Шаблоны промптов'
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        change_summary = kwargs.pop('change_summary', '')
        
        is_new = self.pk is None
        previous_state = None
        
        if not is_new:
            previous_state = PromptTemplate.objects.get(pk=self.pk)
        
        fields_for_version = [
            'template',
            'variables',
            'description',
            'title_criteria',
            'image_search_criteria',
            'image_generation_criteria',
            'tags_criteria',
        ]
        
        has_changes = is_new
        if previous_state:
            for field in fields_for_version:
                if getattr(previous_state, field) != getattr(self, field):
                    has_changes = True
                    break
        
        if is_new:
            self.current_version = 1
            if user and not self.created_by_id:
                self.created_by = user
        elif has_changes:
            self.current_version = previous_state.current_version + 1
        else:
            # Версия не изменилась — сохраняем метаданные и выходим
            if user:
                self.updated_by = user
            super().save(*args, **kwargs)
            return
        
        if user:
            if not self.created_by_id:
                self.created_by = user
            self.updated_by = user
        if change_summary:
            self.last_change_summary = change_summary
        
        super().save(*args, **kwargs)
        
        # Создаём запись об изменениях
        PromptTemplateVersion.objects.create(
            template=self,
            version=self.current_version,
            template_text=self.template,
            variables=self.variables,
            description=self.description,
            title_criteria=self.title_criteria,
            image_search_criteria=self.image_search_criteria,
            image_generation_criteria=self.image_generation_criteria,
            tags_criteria=self.tags_criteria,
            change_summary=change_summary,
            created_by=user
        )
    
    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"




class PromptTemplateVersion(models.Model):
    """История изменений шаблонов промптов"""
    
    template = models.ForeignKey(
        'PromptTemplate',
        on_delete=models.CASCADE,
        related_name='versions',
        verbose_name='Шаблон'
    )
    
    version = models.IntegerField(
        verbose_name='Версия'
    )
    
    template_text = models.TextField(
        verbose_name='Текст промпта'
    )
    
    variables = models.JSONField(
        default=list,
        verbose_name='Переменные'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='Описание'
    )
    
    title_criteria = models.TextField(
        blank=True,
        verbose_name='Критерии заголовка'
    )
    
    image_search_criteria = models.TextField(
        blank=True,
        verbose_name='Критерии поиска изображения'
    )
    
    image_generation_criteria = models.TextField(
        blank=True,
        verbose_name='Критерии генерации изображения'
    )
    
    tags_criteria = models.TextField(
        blank=True,
        verbose_name='Критерии тегов'
    )
    
    change_summary = models.TextField(
        blank=True,
        verbose_name='Описание изменений'
    )
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prompt_template_versions',
        verbose_name='Автор версии'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    
    class Meta:
        verbose_name = 'Версия промпта'
        verbose_name_plural = 'Версии промптов'
        ordering = ['-created_at']
        unique_together = [('template', 'version')]
    
    def __str__(self):
        return f"{self.template.name} v{self.version}"
    
    def increment_usage(self, success: bool = True):
        """Увеличивает счетчик использований и обновляет success_rate"""
        self.usage_count += 1
        if self.usage_count == 1:
            self.success_rate = 1.0 if success else 0.0
        else:
            # Экспоненциальное скользящее среднее
            alpha = 0.1
            self.success_rate = alpha * (1.0 if success else 0.0) + (1 - alpha) * self.success_rate
        self.save(update_fields=['usage_count', 'success_rate'])



