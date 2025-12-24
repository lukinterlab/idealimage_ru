"""
🚀 Автоматическая внутренняя перелинковка для SEO
Находит релевантные статьи и добавляет ссылки
"""
import logging
from typing import List, Dict, Optional
from django.db.models import Q, Count
from django.utils.html import strip_tags
from django.core.cache import cache

logger = logging.getLogger(__name__)


class InternalLinker:
    """
    Автоматическая система внутренней перелинковки
    """
    
    def __init__(self):
        pass
    
    def find_related_posts(self, post, limit: int = 5) -> List:
        """
        Находит релевантные статьи для перелинковки
        
        Args:
            post: Текущая статья
            limit: Количество статей
        
        Returns:
            Список релевантных статей
        """
        from blog.models import Post
        
        cache_key = f'related_posts_{post.id}_{limit}'
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        related_posts = []
        
        # 1. Статьи из той же категории (приоритет)
        category_posts = Post.objects.filter(
            category=post.category,
            status='published'
        ).exclude(id=post.id).order_by('-views', '-created')[:limit * 2]
        
        related_posts.extend(list(category_posts))
        
        # 2. Статьи с общими тегами
        if hasattr(post, 'tags') and post.tags.exists():
            tag_ids = list(post.tags.values_list('id', flat=True))
            
            tagged_posts = Post.objects.filter(
                tags__id__in=tag_ids,
                status='published'
            ).exclude(id=post.id).annotate(
                common_tags=Count('tags', filter=Q(tags__id__in=tag_ids))
            ).order_by('-common_tags', '-views').exclude(
                id__in=[p.id for p in related_posts]
            )[:limit]
            
            related_posts.extend(list(tagged_posts))
        
        # 3. Популярные статьи (fallback)
        if len(related_posts) < limit:
            popular_posts = Post.objects.filter(
                status='published'
            ).exclude(
                id__in=[p.id for p in related_posts] + [post.id]
            ).order_by('-views', '-created')[:limit - len(related_posts)]
            
            related_posts.extend(list(popular_posts))
        
        # Убираем дубликаты и ограничиваем
        seen = set()
        unique_posts = []
        for p in related_posts:
            if p.id not in seen:
                seen.add(p.id)
                unique_posts.append(p)
                if len(unique_posts) >= limit:
                    break
        
        # Кэшируем на 1 час
        cache.set(cache_key, unique_posts, 3600)
        
        return unique_posts
    
    def generate_internal_links_html(self, post, related_posts: List, count: int = 3) -> str:
        """
        Генерирует HTML блок с внутренними ссылками
        
        Args:
            post: Текущая статья
            related_posts: Список релевантных статей
            count: Количество ссылок
        
        Returns:
            HTML строка с ссылками
        """
        if not related_posts:
            return ''
        
        # Берем первые N статей
        posts_to_link = related_posts[:count]
        
        html_parts = ['<div class="internal-links-block mt-8 p-6 bg-gray-50 dark:bg-gray-800 rounded-lg">']
        html_parts.append('<h3 class="text-xl font-bold mb-4">📚 Читайте также:</h3>')
        html_parts.append('<ul class="space-y-3">')
        
        for related_post in posts_to_link:
            html_parts.append(f'''
                <li class="flex items-start">
                    <span class="text-primary mr-2">→</span>
                    <a href="{related_post.get_absolute_url()}" 
                       class="text-primary hover:text-secondary font-medium transition-colors"
                       title="{related_post.title}">
                        {related_post.title}
                    </a>
                </li>
            ''')
        
        html_parts.append('</ul>')
        html_parts.append('</div>')
        
        return '\n'.join(html_parts)
    
    def add_links_to_content(self, post, content: str, max_links: int = 3) -> str:
        """
        Добавляет внутренние ссылки в контент статьи
        
        Args:
            post: Текущая статья
            content: HTML контент статьи
            max_links: Максимальное количество ссылок
        
        Returns:
            Контент с добавленными ссылками
        """
        from bs4 import BeautifulSoup
        
        try:
            soup = BeautifulSoup(content, 'html.parser')
            
            # Находим релевантные статьи
            related_posts = self.find_related_posts(post, limit=max_links * 2)
            
            if not related_posts:
                return content
            
            # Находим все параграфы
            paragraphs = soup.find_all('p')
            
            links_added = 0
            used_posts = set()
            
            for p in paragraphs:
                if links_added >= max_links:
                    break
                
                text = p.get_text()
                if len(text) < 50:  # Пропускаем короткие параграфы
                    continue
                
                # Ищем подходящую статью для ссылки
                for related_post in related_posts:
                    if related_post.id in used_posts:
                        continue
                    
                    # Ищем ключевые слова из заголовка статьи
                    keywords = related_post.title.lower().split()[:3]  # Первые 3 слова
                    
                    # Проверяем есть ли эти слова в параграфе
                    paragraph_lower = text.lower()
                    if any(keyword in paragraph_lower for keyword in keywords if len(keyword) > 3):
                        # Добавляем ссылку
                        link_text = related_post.title
                        link = soup.new_tag('a', href=related_post.get_absolute_url())
                        link.string = link_text
                        link['class'] = 'internal-link text-primary hover:text-secondary font-medium'
                        link['title'] = related_post.title
                        
                        # Вставляем ссылку в конец параграфа
                        p.append(' — ')
                        p.append(link)
                        
                        used_posts.add(related_post.id)
                        links_added += 1
                        break
            
            return str(soup)
            
        except Exception as e:
            logger.error(f"Ошибка добавления внутренних ссылок: {e}")
            return content


def get_internal_links_block(post, count: int = 3) -> str:
    """
    Вспомогательная функция для получения блока внутренних ссылок
    
    Args:
        post: Текущая статья
        count: Количество ссылок
    
    Returns:
        HTML блок с ссылками
    """
    linker = InternalLinker()
    related_posts = linker.find_related_posts(post, limit=count)
    return linker.generate_internal_links_html(post, related_posts, count)

