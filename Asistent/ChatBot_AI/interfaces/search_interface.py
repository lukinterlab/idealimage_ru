"""
Интерфейс для поиска по контенту

Абстракция для различных систем поиска статей/постов
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from django.db.models import Q, Case, When, IntegerField, Value
import logging

logger = logging.getLogger(__name__)


class BaseSearchProvider(ABC):
    """Базовый класс для провайдеров поиска"""
    
    @abstractmethod
    def search_articles(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Поиск статей по запросу
        
        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов
            
        Returns:
            List[Dict] с ключами:
                - id: ID статьи
                - title: Заголовок
                - url: URL статьи
                - description: Описание (опционально)
        """
        pass


class BlogSearchProvider(BaseSearchProvider):
    """Провайдер поиска по статьям блога"""
    
    def search_articles(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Поиск статей блога с приоритетами:
        1. Категория (+50)
        2. Теги (+30)
        3. Заголовок (+20)
        4. Описание (+10)
        5. Контент (+1)
        
        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов
            
        Returns:
            List словарей с данными статей
        """
        try:
            from blog.models import Post
            
            # Разбиваем запрос на слова
            words = [w.lower() for w in query.lower().split() if len(w) >= 3]
            
            if not words:
                return []
            
            # Строим Q-объекты для разных полей
            q_category = Q()
            q_tags = Q()
            q_title = Q()
            q_desc = Q()
            q_content = Q()
            
            for word in words:
                q_category |= Q(category__title__icontains=word) | Q(category__slug__icontains=word)
                q_tags |= Q(tags__name__icontains=word) | Q(tags__slug__icontains=word)
                q_title |= Q(title__icontains=word)
                q_desc |= Q(description__icontains=word)
                q_content |= Q(content__icontains=word)
            
            # Объединяем условия
            combined_q = q_category | q_tags | q_title | q_desc | q_content
            
            # Ищем опубликованные статьи с расчётом релевантности
            articles = Post.objects.filter(
                combined_q,
                status='published'
            ).select_related('category', 'author').prefetch_related('tags').annotate(
                relevance=
                    Case(When(q_category, then=Value(50)), default=Value(0), output_field=IntegerField()) +
                    Case(When(q_tags, then=Value(30)), default=Value(0), output_field=IntegerField()) +
                    Case(When(q_title, then=Value(20)), default=Value(0), output_field=IntegerField()) +
                    Case(When(q_desc, then=Value(10)), default=Value(0), output_field=IntegerField()) +
                    Case(When(q_content, then=Value(1)), default=Value(0), output_field=IntegerField())
            ).filter(
                relevance__gt=0
            ).order_by('-relevance', '-views', '-created').distinct()[:limit]
            
            # Преобразуем в стандартный формат
            results = []
            for article in articles:
                results.append({
                    'id': article.id,
                    'title': article.title,
                    'url': article.get_absolute_url(),
                    'description': article.description if article.description else ''
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Ошибка поиска статей: {e}")
            return []

