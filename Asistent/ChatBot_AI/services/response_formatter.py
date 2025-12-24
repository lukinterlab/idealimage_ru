"""
Сервис форматирования ответов
"""

from typing import Any, List
import logging

logger = logging.getLogger(__name__)


class ResponseFormatter:
    """Форматирование ответов чат-бота"""
    
    @staticmethod
    def format_articles(articles: Any) -> str:
        """
        Форматирование ответа со списком статей
        
        Args:
            articles: Список статей (QuerySet или list)
            
        Returns:
            Форматированный HTML ответ
        """
        if not articles:
            return ""
        
        response = "Я нашла несколько статей, которые могут быть вам полезны:\n\n"
        
        for i, article in enumerate(articles, 1):
            # Если это dict из SearchProvider
            if isinstance(article, dict):
                title = article.get('title', 'Без названия')
                url = article.get('url', '#')
                description = article.get('description', '')
            else:
                # Если это модель Post
                title = article.title
                url = article.get_absolute_url()
                description = article.description if hasattr(article, 'description') and article.description else ''
            
            response += f"{i}. <strong><a href='{url}' target='_blank'>{title}</a></strong>\n"
            
            if description:
                # Ограничиваем описание 100 символами
                desc = description[:100] + '...' if len(description) > 100 else description
                response += f"   <em>{desc}</em>\n"
            response += "\n"
        
        return response
    
    @staticmethod
    def format_error(error_message: str = None) -> str:
        """
        Форматирование сообщения об ошибке
        
        Args:
            error_message: Текст ошибки (опционально)
            
        Returns:
            Форматированное сообщение
        """
        if error_message:
            return f"Произошла ошибка: {error_message}"
        return "К сожалению, я не могу найти ответ на ваш вопрос. Хотите связаться с администратором?"

