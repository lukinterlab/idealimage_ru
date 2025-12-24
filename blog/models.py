from django.db import models
from django.core.validators import FileExtensionValidator
from django.contrib.auth import get_user_model
from django.urls import reverse
from mptt.models import MPTTModel, TreeForeignKey
from ckeditor_uploader.fields import RichTextUploadingField
from ckeditor.fields import RichTextField
from taggit.managers import TaggableManager
from unidecode import unidecode
from utilits.utils import image_compress, unique_slugify

User = get_user_model()


class Post(models.Model):
    """  Модель статей для сайта """

    class PostManager(models.Manager):
        """  Кастомный менеджер для модели статей      """

        def all(self):
            """ Список статей (SQL запрос с фильтрацией для страницы списка статей)  """
            return self.get_queryset().select_related('author', 'category')
        
        def detail(self):
            """
            Детальная статья (SQL запрос с фильтрацией для страницы со статьёй)
            """
            return self.get_queryset() \
                .select_related('author', 'category') \
                .prefetch_related('comments', 'comments__author', 'comments__author__profile') \
                .filter(status='published')

    objects = PostManager()
            
        

    STATUS_OPTIONS = (
        ('published', 'Опубликовано'),
        ('draft', 'Черновик')
    )
    title = models.CharField(verbose_name='Заголовок cтатьи', max_length=100)
    category = TreeForeignKey('Category', on_delete=models.PROTECT, related_name='posts', verbose_name='Категория')
    slug = models.SlugField(verbose_name='URL', max_length=255, blank=True, unique=True)
    description = models.TextField(verbose_name='ПОСТ для ТЕЛЕГРАММА', blank=True)
    content = RichTextField(verbose_name='Полное описание', blank=True)
    kartinka = models.FileField(
        verbose_name='Превью поста (изображение/видео)',
        blank=True,
        upload_to='images/',
        max_length=500,
        help_text='Загрузите изображение или видео (mp4, webm, mov)'
    )
    video_url = models.URLField(
        verbose_name='Ссылка на видео',
        blank=True,
        help_text='Если не удается загрузить видео - укажите ссылку (приоритет над изображением)'
    )
    status = models.CharField(choices=STATUS_OPTIONS, default='draft', verbose_name='Статус поста', max_length=10)
    created = models.DateTimeField(auto_now_add=True, verbose_name='Время добавления')
    updated = models.DateTimeField(auto_now=True, verbose_name='Время обновления')
    author = models.ForeignKey(User, verbose_name='Автор', on_delete=models.CASCADE, related_name='author_posts',
                               default=1)
    updater = models.ForeignKey(User, verbose_name='Обновил', on_delete=models.SET_NULL, null=True,
                                related_name='updater_posts', blank=True)
    telegram_posted_at = models.DateTimeField(verbose_name='Опубликованно в Телеграмме', blank=True, null=True)
    fixed = models.BooleanField(verbose_name='ФИКСА', default=False)
    views = models.IntegerField(verbose_name='просмотров', default=0)
    tags = TaggableManager(blank=True)
    
    # AI Moderation fields
    moderation_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'На модерации AI'),
            ('approved', 'Одобрено AI'),
            ('rejected', 'Отклонено AI'),
            ('skipped', 'Пропущено'),
        ],
        default='pending',
        verbose_name='Статус модерации AI'
    )
    ai_moderation_notes = models.TextField(blank=True, verbose_name='Замечания AI')
    
    # AI Help & Penalty System
    ai_help_image = models.BooleanField(
        default=False,
        verbose_name='AI подобрал изображение',
        help_text='AI автоматически нашел и добавил изображение (-30% баллов)'
    )
    ai_help_text = models.BooleanField(
        default=False,
        verbose_name='AI дополнил текст',
        help_text='AI дополнил статью до минимума (-30% баллов)'
    )
    ai_help_profanity = models.BooleanField(
        default=False,
        verbose_name='AI убрал мат',
        help_text='AI удалил ненормативную лексику (-30% баллов)'
    )
    ai_help_uniqueness = models.BooleanField(
        default=False,
        verbose_name='AI переделал текст для уникальности',
        help_text='AI переписал статью для уникальности (-10% баллов)'
    )
    ai_penalty_percent = models.IntegerField(
        default=0,
        verbose_name='Штраф от AI (%)',
        help_text='Общий процент штрафа за помощь AI'
    )
    
    content_task = models.ForeignKey(
        'Asistent.ContentTask',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='task_articles',
        verbose_name='Связанное задание'
    )
    
    # SEO fields
    meta_title = models.CharField(
        max_length=60,
        blank=True,
        verbose_name='SEO заголовок',
        help_text='Оптимизированный заголовок для поисковиков (до 60 символов)'
    )
    meta_description = models.CharField(
        max_length=160,
        blank=True,
        verbose_name='SEO описание',
        help_text='Краткое описание для поисковиков (до 160 символов)'
    )
    focus_keyword = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Главное ключевое слово',
        help_text='Основное ключевое слово для SEO'
    )
    og_title = models.CharField(
        max_length=60,
        blank=True,
        verbose_name='Open Graph заголовок',
        help_text='Заголовок для соцсетей (до 60 символов)'
    )
    og_description = models.CharField(
        max_length=160,
        blank=True,
        verbose_name='Open Graph описание',
        help_text='Описание для соцсетей (до 160 символов)'
    )
    og_preview = models.ImageField(
        verbose_name='OG-превью (1200x630px)',
        blank=True,
        null=True,
        upload_to='og_previews/',
        help_text='Автоматически генерируется из основного изображения для соцсетей'
    )
    
    # AI Co-author fields
    ai_draft_improvement_requested = models.BooleanField(
        default=False,
        verbose_name='Запрошено улучшение AI',
        help_text='Автор запросил AI помочь с улучшением черновика'
    )
    ai_draft_original = models.TextField(
        blank=True,
        verbose_name='Оригинальный черновик',
        help_text='Версия текста до улучшения AI'
    )
    ai_draft_improved = models.TextField(
        blank=True,
        verbose_name='Улучшенная версия',
        help_text='Версия текста после улучшения AI'
    )
    ai_improvement_notes = models.TextField(
        blank=True,
        verbose_name='Заметки AI об улучшениях',
        help_text='Что именно улучшил AI'
    )
    ai_improvement_style = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ('literary', 'Литературный'),
            ('seo', 'SEO-оптимизированный'),
            ('emotional', 'Эмоциональный'),
            ('balanced', 'Сбалансированный'),
        ],
        verbose_name='Стиль улучшения AI'
    )
    ai_improvement_status = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ('pending', 'В обработке'),
            ('ready', 'Готово к проверке'),
            ('accepted', 'Принято'),
            ('rejected', 'Отклонено'),
        ],
        verbose_name='Статус улучшения AI'
    )
    ai_improvement_task_id = models.CharField(
        max_length=36,
        blank=True,
        verbose_name='ID задачи AI-улучшения',
        help_text='Идентификатор последней задачи django-q для улучшения текста'
    )
    ai_improvement_requested_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Время запроса AI-улучшения',
        help_text='Когда автор инициировал работу AI-помощника'
    )
    
    # Social Media fields
    auto_publish_social = models.BooleanField(
        default=True,
        verbose_name='Автопубликация в соцсетях',
        help_text='Автоматически публиковать при статусе "Опубликовано"'
    )
    social_platforms = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Платформы для публикации',
        help_text='["telegram", "vk", "pinterest", "rutube", "dzen"]'
    )
    
    # Поля для оптимизации видео
    video_optimized = models.BooleanField(
        default=False,
        verbose_name='Видео оптимизировано',
        help_text='Автоматически устанавливается после оптимизации видео'
    )
    video_poster = models.ImageField(
        blank=True,
        null=True,
        upload_to='video_posters/',
        verbose_name='Poster изображение для видео',
        help_text='Автоматически создается из первого кадра видео'
    )
    video_duration = models.FloatField(
        blank=True,
        null=True,
        verbose_name='Длительность видео (секунды)',
        help_text='Автоматически определяется при обработке'
    )
    video_processing_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'В очереди'),
            ('processing', 'Обрабатывается'),
            ('completed', 'Завершено'),
            ('failed', 'Ошибка'),
        ],
        default='pending',
        blank=True,
        verbose_name='Статус обработки видео'
    )
    
    # Поле для thumbnail изображения (для списков и главной страницы)
    thumbnail = models.ImageField(
        blank=True,
        null=True,
        upload_to='thumbnails/',
        verbose_name='Thumbnail изображение',
        help_text='Автоматически создается из основного изображения для быстрой загрузки в списках (600x400 WebP)'
    )

    class Meta:
        db_table = 'app_posts'
        ordering = [ '-updated']
        indexes = [
            models.Index(fields=['-fixed', '-created', 'status']),  # Существующий
            models.Index(fields=['slug'], name='post_slug_idx'),  # Для get_by_slug
            models.Index(fields=['status', '-views'], name='post_popular_idx'),  # Для популярных
            models.Index(fields=['category', 'status', '-created'], name='post_category_idx'),  # Фильтры по категории
            models.Index(fields=['author', 'status', '-created'], name='post_author_idx'),  # Посты автора
            models.Index(fields=['video_url'], name='post_video_idx'),  # Быстрый поиск статей с видео
        ]
        verbose_name = 'Статья'
        verbose_name_plural = 'Статьи'

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        """Метод получения URL-адреса объекта"""
        return reverse('blog:post_detail', kwargs={'slug': self.slug})  # args=[self.id, self.slug])
    
    def get_next_post(self):
        """Метод получения следующего поста"""
        try:
            return self.get_next_by_publish(category=self.category)
        except Post.DoesNotExist:
            return None

    def get_previous_post(self):
        """Метод получения предыдущего поста"""
        try:
            return self.get_previous_by_publish(category=self.category)
        except Post.DoesNotExist:
            return None
    
    def get_likes_count(self):
        """Получить количество лайков"""
        return self.likes.count()
    
    def get_likes_by_type(self):
        """Получить лайки по типам"""
        from django.db.models import Count
        return self.likes.values('reaction_type').annotate(count=Count('reaction_type'))
    
    def get_average_rating(self):
        """Получить средний рейтинг статьи"""
        from django.db.models import Avg
        avg_rating = self.ratings.aggregate(avg=Avg('rating'))['avg']
        return round(avg_rating, 1) if avg_rating else 0
    
    def get_ratings_count(self):
        """Получить количество оценок"""
        return self.ratings.count()
    
    def get_bookmarks_count(self):
        """Получить количество закладок"""
        return self.bookmarks.count()
    
    def is_liked_by_user(self, user):
        """Проверить, лайкнул ли пользователь статью"""
        if not user.is_authenticated:
            return False
        return self.likes.filter(user=user).exists()
    
    def get_user_reaction(self, user):
        """Получить реакцию пользователя на статью"""
        if not user.is_authenticated:
            return None
        like = self.likes.filter(user=user).first()
        return like.reaction_type if like else None
    
    def get_user_reaction_by_session(self, session_key):
        """Получить реакцию анонимного пользователя на статью по session_key"""
        if not session_key:
            return None
        like = self.likes.filter(session_key=session_key).first()
        return like.reaction_type if like else None
    
    def is_rated_by_user(self, user):
        """Проверить, оценил ли пользователь статью"""
        if not user.is_authenticated:
            return False
        return self.ratings.filter(user=user).exists()
    
    def get_user_rating(self, user):
        """Получить оценку пользователя"""
        if not user.is_authenticated:
            return None
        rating = self.ratings.filter(user=user).first()
        return rating.rating if rating else None
    
    def is_bookmarked_by_user(self, user):
        """Проверить, добавлена ли статья в закладки пользователем"""
        if not user.is_authenticated:
            return False
        return self.bookmarks.filter(user=user).exists()
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__kartinka = self.kartinka if self.pk else None
    
    
    def save(self, *args, **kwargs):
        """   Сохранение полей модели при их отсутствии заполнения   """
        if not self.slug:
            self.slug = unique_slugify(self, self.title)
        
        # АВТОЗАПОЛНЕНИЕ: description для телеграмма (первые 120 слов из content)
        if self.content and not self.description:
            from django.utils.html import strip_tags
            
            # Получаем чистый текст без HTML
            clean_text = strip_tags(self.content)
            
            # Берем первые 120 слов
            words = clean_text.split()[:120]
            self.description = ' '.join(words)
        
        super().save(*args, **kwargs)
        
        

class Category(MPTTModel):
    """ Модель категорий с вложенностью """
    kartinka = models.FileField(
        verbose_name='картинка телеграмма',
        blank=True,
        upload_to='Telega/',
        max_length=500,
    )
    title = models.CharField(max_length=255, verbose_name='Название категории')
    slug = models.SlugField(max_length=255, verbose_name='URL категории', blank=True, unique=True)
    chat_id = models.CharField(verbose_name='id канала', max_length=100, null=True, blank=True)
    chat_url = models.CharField(verbose_name='url канала', max_length=100, null=True, blank=True)
    description = models.TextField(verbose_name='Описание категории', max_length=300, null=True, blank=True)
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True,
                            db_index=True,
                            related_name='children',
                            verbose_name='Родительская категория'
                            )

    class MPTTMeta:
        """Сортировка по вложенности"""
        order_insertion_by = ('title',)

    class Meta:
        """Сортировка, название модели в админ панели, таблица в данными"""
        ordering = ['title']
        indexes = [models.Index(fields=['title'])]
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        db_table = 'app_categories'

    def __str__(self):
        """Возвращение заголовка статьи"""
        return self.title
        
    
    def save(self, *args, **kwargs):
        """   Сохранение полей модели при их отсутствии заполнения   """
        if not self.slug:
            self.slug = unique_slugify(self, self.title)
        super().save(*args, **kwargs)
        

    def get_absolute_url(self):
        return reverse('blog:post_list_by_category',
                       kwargs={'slug': self.slug})  # args=[self.slug])


class Comment(models.Model):
    """Модель комментариев"""

    post = models.ForeignKey(Post, on_delete=models.CASCADE, verbose_name='Статья', related_name='comments')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, verbose_name='Родительский комментарий', related_name='replies', null=True, blank=True)
    author_comment = models.CharField(max_length=80, verbose_name='Автор комментария')
    content = models.TextField(verbose_name='Текст комментария', max_length=3000)
    created = models.DateTimeField(verbose_name='Время добавления', auto_now_add=True)
    updated = models.DateTimeField(verbose_name='Время обновления', auto_now=True)
    active = models.BooleanField(default=True)
    email = models.EmailField()


    class MTTMeta:
        order_insertion_by = ('-created',)

    class Meta:
        db_table = 'app_comments'
        indexes = [models.Index(fields=['-created', 'updated', 'active'])]
        ordering = ['-created']
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'

    def __str__(self):
        return 'Комментарий от {} на {}'.format(self.author_comment, self.post)


class URLRedirect(models.Model):
    """
    Модель для хранения редиректов и истории 404 ошибок
    """
    old_url = models.CharField(
        max_length=500,
        unique=True,
        verbose_name='Старый URL',
        db_index=True
    )
    new_url = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='Новый URL (редирект)',
        help_text='Если пусто - возвращается 410 Gone'
    )
    redirect_type = models.IntegerField(
        choices=[(301, '301 Permanent'), (302, '302 Temporary'), (410, '410 Gone')],
        default=301,
        verbose_name='Тип редиректа'
    )
    hits_count = models.IntegerField(
        default=0,
        verbose_name='Количество обращений'
    )
    first_seen = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Первое обращение'
    )
    last_seen = models.DateTimeField(
        auto_now=True,
        verbose_name='Последнее обращение'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен'
    )
    notes = models.TextField(
        blank=True,
        verbose_name='Заметки'
    )
    
    class Meta:
        db_table = 'app_url_redirects'
        verbose_name = 'Редирект URL'
        verbose_name_plural = 'Редиректы URL'
        ordering = ['-last_seen']
        indexes = [
            models.Index(fields=['old_url']),
            models.Index(fields=['-hits_count']),
        ]
    
    def __str__(self):
        return f"{self.old_url} -> {self.new_url or '410 Gone'}"
