"""
Сервис для поиска в FAQ
"""

from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class FAQSearchService:
    """Сервис поиска ответов в FAQ"""
    
    @staticmethod
    def search(message: str) -> Optional[Dict]:
        """
        Поиск ответа в FAQ по ключевым словам
        
        Args:
            message: Сообщение пользователя
            
        Returns:
            Dict с ключами answer, url, faq_obj или None если не найдено
        """
        from ..models import ChatbotFAQ
        
        message_lower = message.lower()
        
        # Получаем активные FAQ, отсортированные по приоритету
        faqs = ChatbotFAQ.objects.filter(is_active=True).order_by('-priority', '-usage_count')
        
        for faq in faqs:
            # Проверяем совпадение ключевых слов
            if faq.keywords:
                for keyword in faq.keywords:
                    if keyword.lower() in message_lower:
                        return {
                            'answer': faq.answer,
                            'url': faq.related_url if faq.related_url else None,
                            'faq_obj': faq
                        }
            
            # Проверяем совпадение с вопросом
            if faq.question.lower() in message_lower or message_lower in faq.question.lower():
                return {
                    'answer': faq.answer,
                    'url': faq.related_url if faq.related_url else None,
                    'faq_obj': faq
                }
        
        return None

