"""
RSS/Atom feeds для блога IdealImage.ru
"""
from django.contrib.syndication.views import Feed
from django.urls import reverse
from django.utils.feedgenerator import Atom1Feed
from django.conf import settings
from .models import Post


class LatestPostsFeed(Feed):
    """
    RSS-лента последних статей блога
    """
    title = "IdealImage.ru - Блог"
    link = "/blog/"
    description = "Последние статьи о моде, красоте, здоровье и стиле жизни"
    feed_type = Atom1Feed  # Используем Atom вместо RSS 2.0 (более современный формат)
    
    # SEO настройки
    author_name = "IdealImage.ru"
    author_email = settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else None
    author_link = "https://idealimage.ru"
    
    # Настройки фида
    feed_copyright = f"Copyright (c) 2025, IdealImage.ru"
    ttl = 600  # Time to live в минутах (10 часов)
    
    def items(self):
        """
        Возвращает последние 20 опубликованных статей
        """
        return Post.objects.filter(status='published').select_related('author', 'category').order_by('-created')[:20]
    
    def item_title(self, item):
        """Заголовок статьи"""
        return item.title
    
    def item_description(self, item):
        """Описание статьи (первые 300 символов контента)"""
        if item.description:
            return item.description
        # Убираем HTML-теги для description
        from django.utils.html import strip_tags
        content = strip_tags(item.content)
        return content[:300] + '...' if len(content) > 300 else content
    
    def item_link(self, item):
        """Ссылка на статью"""
        return item.get_absolute_url()
    
    def item_pubdate(self, item):
        """Дата публикации"""
        return item.created
    
    def item_updateddate(self, item):
        """Дата обновления"""
        return item.updated
    
    def item_author_name(self, item):
        """Имя автора"""
        if item.author:
            return item.author.get_full_name() or item.author.username
        return "IdealImage.ru"
    
    def item_categories(self, item):
        """Категории и теги"""
        categories = [item.category.title] if item.category else []
        # Добавляем теги
        tags = [tag.name for tag in item.tags.all()]
        return categories + tags
    
    def item_enclosure_url(self, item):
        """URL изображения для медиа-вложения"""
        if item.kartinka:
            return f"{settings.SITE_URL}{item.kartinka.url}"
        return None
    
    def item_enclosure_length(self, item):
        """Размер файла (если есть изображение)"""
        if item.kartinka:
            try:
                return item.kartinka.size
            except:
                return 0
        return 0
    
    def item_enclosure_mime_type(self, item):
        """MIME-тип файла"""
        if item.kartinka:
            # Определяем тип по расширению
            if item.kartinka.name.lower().endswith(('.jpg', '.jpeg')):
                return "image/jpeg"
            elif item.kartinka.name.lower().endswith('.png'):
                return "image/png"
            elif item.kartinka.name.lower().endswith('.webp'):
                return "image/webp"
            elif item.kartinka.name.lower().endswith(('.mp4', '.webm', '.mov')):
                return "video/mp4"
        return "image/jpeg"


class CategoryPostsFeed(Feed):
    """
    RSS-лента статей по категории
    """
    feed_type = Atom1Feed
    
    def get_object(self, request, slug):
        """Получаем категорию по slug"""
        from .models import Category
        return Category.objects.get(slug=slug)
    
    def title(self, obj):
        return f"IdealImage.ru - {obj.title}"
    
    def link(self, obj):
        return obj.get_absolute_url()
    
    def description(self, obj):
        return f"Последние статьи в категории {obj.title}"
    
    def items(self, obj):
        """Статьи категории"""
        return Post.objects.filter(
            status='published',
            category=obj
        ).select_related('author', 'category').order_by('-created')[:20]
    
    # Используем те же методы что и в LatestPostsFeed
    item_title = LatestPostsFeed.item_title
    item_description = LatestPostsFeed.item_description
    item_link = LatestPostsFeed.item_link
    item_pubdate = LatestPostsFeed.item_pubdate
    item_updateddate = LatestPostsFeed.item_updateddate
    item_author_name = LatestPostsFeed.item_author_name
    item_categories = LatestPostsFeed.item_categories
    item_enclosure_url = LatestPostsFeed.item_enclosure_url
    item_enclosure_length = LatestPostsFeed.item_enclosure_length
    item_enclosure_mime_type = LatestPostsFeed.item_enclosure_mime_type

