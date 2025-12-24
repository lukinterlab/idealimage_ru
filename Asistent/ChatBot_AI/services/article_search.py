"""
Сервис для поиска статей
"""

from typing import Any
from django.db.models import QuerySet
import logging

logger = logging.getLogger(__name__)


class ArticleSearchService:
    """Сервис поиска статей через интерфейс"""
    
    def __init__(self, search_provider=None):
        """
        Инициализация сервиса
        
        Args:
            search_provider: Провайдер поиска (из config)
        """
        if search_provider is None:
            from ..config import SEARCH_PROVIDER
            search_provider = SEARCH_PROVIDER
        
        self.provider = search_provider()
    
    def search(self, query: str, limit: int = 3) -> Any:
        """
        Поиск статей по запросу
        
        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов
            
        Returns:
            Результаты поиска (формат зависит от провайдера)
        """
        try:
            return self.provider.search_articles(query, limit)
        except Exception as e:
            logger.error(f"Ошибка поиска статей: {e}")
            return []

