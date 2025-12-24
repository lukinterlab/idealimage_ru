"""
Template tags для SEO-оптимизации и перелинковки
"""
from django import template
from django.db.models import Q, Count
from django.core.cache import cache
from blog.models import Post
import random

register = template.Library()

# Импортируем функции для внутренних ссылок
try:
    from blog.services.internal_linking import get_internal_links_block
except ImportError:
    def get_internal_links_block(post, count=3):
        return ''


@register.inclusion_tag('blog/partials/related_posts.html')
def show_related_posts(post, limit=6):
    """
    Показывает похожие статьи на основе:
    1. Общих тегов
    2. Той же категории
    3. Похожих заголовков (ключевые слова)
    
    Args:
        post: Текущая статья
        limit: Количество похожих статей
    """
    # Кэшируем похожие статьи на 30 минут
    cache_key = f'related_posts_{post.id}_{limit}'
    related_posts = cache.get(cache_key)
    
    if related_posts is None:
        # Получаем ID всех тегов текущего поста
        post_tags = post.tags.values_list('id', flat=True)
        
        # Находим статьи с общими тегами
        related_posts = Post.objects.filter(
            status='published'
        ).exclude(id=post.id)
        
        # Приоритет 1: Статьи с общими тегами
        if post_tags:
            related_by_tags = related_posts.filter(
                tags__in=post_tags
            ).annotate(
                same_tags=Count('id')
            ).order_by('-same_tags', '-views')[:limit]
            
            if related_by_tags.count() >= limit:
                related_posts = list(related_by_tags)
                cache.set(cache_key, related_posts, 1800)  # 30 минут
                return {'posts': related_posts, 'title': 'Похожие статьи'}
        
        # Приоритет 2: Статьи из той же категории
        related_by_category = related_posts.filter(
            category=post.category
        ).order_by('-views', '-created')[:limit]
        
        if related_by_category.count() >= limit:
            related_posts = list(related_by_category)
            cache.set(cache_key, related_posts, 1800)
            return {'posts': related_posts, 'title': 'Из той же категории'}
        
        # Приоритет 3: Популярные статьи из категории
        related_posts = list(related_by_category)
        
        # Если не хватает, добавляем популярные из других категорий
        if len(related_posts) < limit:
            additional = Post.objects.filter(
                status='published'
            ).exclude(
                id__in=[p.id for p in related_posts] + [post.id]
            ).order_by('-views')[:limit - len(related_posts)]
            
            related_posts.extend(list(additional))
        
        cache.set(cache_key, related_posts, 1800)
    
    return {
        'posts': related_posts[:limit],
        'title': 'Рекомендуем почитать'
    }


@register.inclusion_tag('blog/partials/breadcrumbs.html')
def show_breadcrumbs(breadcrumbs):
    """
    Отображает хлебные крошки
    
    Args:
        breadcrumbs: Список кортежей (название, url)
    """
    return {'breadcrumbs': breadcrumbs}


@register.filter
def add_internal_links(content, post=None):
    """
    Автоматически добавляет внутренние ссылки на ключевые слова
    
    Args:
        content: HTML контент статьи
        post: Текущая статья (чтобы исключить ссылку на саму себя)
    """
    if not content:
        return content
    
    # Кэшируем на 1 час
    cache_key = f'linked_content_{post.id if post else "none"}'
    linked_content = cache.get(cache_key)
    
    if linked_content is not None:
        return linked_content
    
    # Получаем топ популярные статьи для перелинковки
    top_posts = Post.objects.filter(
        status='published'
    ).exclude(
        id=post.id if post else None
    ).order_by('-views')[:20]
    
    # Создаем словарь: ключевое слово -> URL статьи
    link_map = {}
    for p in top_posts:
        # Используем заголовок как ключевое слово
        keywords = [p.title]
        
        # Добавляем теги
        if hasattr(p, 'tags'):
            keywords.extend([tag.name for tag in p.tags.all()[:3]])
        
        # Добавляем фокус-слово если есть
        if hasattr(p, 'focus_keyword') and p.focus_keyword:
            keywords.append(p.focus_keyword)
        
        for keyword in keywords:
            if len(keyword) > 10 and keyword not in link_map:  # Только длинные ключевые слова
                link_map[keyword] = p.get_absolute_url()
    
    # Добавляем ссылки (максимум 3-5 на статью)
    import re
    links_added = 0
    max_links = 5
    
    for keyword, url in link_map.items():
        if links_added >= max_links:
            break
        
        # Ищем первое вхождение ключевого слова (не в HTML тегах)
        pattern = rf'(?<!<[^>]*)\b({re.escape(keyword)})\b(?![^<]*>)'
        
        # Проверяем, есть ли это слово в тексте
        if re.search(pattern, content, re.IGNORECASE):
            # Заменяем только первое вхождение
            content = re.sub(
                pattern,
                rf'<a href="{url}" class="internal-link text-primary">\1</a>',
                content,
                count=1,
                flags=re.IGNORECASE
            )
            links_added += 1
    
    cache.set(cache_key, content, 3600)  # Кэш на 1 час
    return content


@register.simple_tag
def get_popular_tags(limit=10):
    """
    Возвращает популярные теги для сайдбара
    """
    cache_key = f'popular_tags_{limit}'
    tags = cache.get(cache_key)
    
    if tags is None:
        from taggit.models import Tag
        from django.db.models import Count
        
        tags = Tag.objects.filter(
            taggit_taggeditem_items__content_type__model='post'
        ).annotate(
            posts_count=Count('taggit_taggeditem_items')
        ).order_by('-posts_count')[:limit]
        
        cache.set(cache_key, tags, 1800)  # 30 минут
    
    return tags


@register.simple_tag
def get_category_top_posts(category, limit=5):
    """
    Возвращает топ статей из категории
    """
    cache_key = f'category_top_{category.id}_{limit}'
    posts = cache.get(cache_key)
    
    if posts is None:
        posts = Post.objects.filter(
            category=category,
            status='published'
        ).order_by('-views')[:limit]
        
        cache.set(cache_key, posts, 1800)
    
    return posts


@register.filter
def lazy_load_images(content):
    """
    Добавляет lazy loading для всех изображений в контенте
    УЛУЧШЕНО: Первое изображение получает loading="eager" для LCP
    """
    import re
    
    # Находим все img теги
    img_pattern = r'<img(?![^>]*loading=)([^>]*)>'
    matches = list(re.finditer(img_pattern, content, re.IGNORECASE))
    
    if not matches:
        return content
    
    # Заменяем с учетом позиции
    for i, match in enumerate(matches):
        img_attrs = match.group(1)
        
        # Первое изображение - eager (для LCP)
        if i == 0:
            replacement = r'<img loading="eager" decoding="async"\1>'
        else:
            # Остальные - lazy
            replacement = r'<img loading="lazy" decoding="async"\1>'
        
        old_tag = match.group(0)
        new_tag = re.sub(img_pattern, replacement, old_tag, count=1)
        content = content.replace(old_tag, new_tag, 1)
    
    # Добавляем класс для плавной загрузки (только для lazy)
    content = re.sub(r'<img([^>]*loading="lazy"[^>]*)>', r'<img class="lazy-image"\1>', content)
    
    return content


@register.inclusion_tag('blog/partials/schema_org.html')
def render_schema_org(structured_data):
    """
    Рендерит Schema.org structured data
    """
    return {'structured_data': structured_data}


@register.inclusion_tag('blog/partials/category_tree.html')
def show_category_tree():
    """
    Отображает дерево категорий для навигации
    """
    from blog.models import Category
    
    cache_key = 'category_tree'
    categories = cache.get(cache_key)
    
    if categories is None:
        # Получаем только корневые категории с потомками
        categories = Category.objects.filter(
            parent=None
        ).prefetch_related('children')
        
        cache.set(cache_key, categories, 3600)  # 1 час
    
    return {'categories': categories}


