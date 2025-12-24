"""
Сервис семантического поиска через embeddings
"""

import math
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Вычисление косинусного сходства между двумя векторами
    
    Args:
        vec1: Первый вектор
        vec2: Второй вектор
        
    Returns:
        float: Сходство от 0 (нет сходства) до 1 (идентичны)
    """
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    
    try:
        # Скалярное произведение
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        
        # Нормы векторов
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        # Косинусное сходство
        return dot_product / (norm1 * norm2)
    except Exception as e:
        logger.error(f"Ошибка вычисления cosine_similarity: {e}")
        return 0.0


class SemanticSearchService:
    """Семантический поиск через embeddings"""
    
    @staticmethod
    def generate_query_embedding(query: str) -> List[float]:
        """
        Генерация embedding для поискового запроса
        
        Args:
            query: Запрос пользователя
            
        Returns:
            List[float]: Вектор embeddings
        """
        try:
            from Asistent.gigachat_api import get_embeddings
            return get_embeddings(query)
        except Exception as e:
            logger.error(f"Ошибка генерации embedding для запроса: {e}")
            return []
    
    @staticmethod
    def search_faq_semantic(query: str, min_similarity: float = 0.65, limit: int = 5) -> List[Tuple[any, float]]:
        """
        Семантический поиск FAQ по embeddings
        
        Args:
            query: Запрос пользователя
            min_similarity: Минимальный порог сходства (0.0-1.0)
            limit: Максимум результатов
            
        Returns:
            List[Tuple[FAQ, similarity_score]]: Список (FAQ, оценка сходства)
        """
        from ..models import ChatbotFAQ
        
        # Генерируем embedding для запроса
        query_embedding = SemanticSearchService.generate_query_embedding(query)
        if not query_embedding:
            logger.warning("Не удалось сгенерировать embedding для запроса")
            return []
        
        # Получаем все FAQ с embeddings
        faqs = ChatbotFAQ.objects.filter(
            is_active=True,
            embedding__isnull=False
        ).exclude(embedding=[])
        
        # Вычисляем сходство для каждого FAQ
        results = []
        for faq in faqs:
            if not faq.embedding:
                continue
            
            similarity = cosine_similarity(query_embedding, faq.embedding)
            
            # Фильтруем по порогу
            if similarity >= min_similarity:
                results.append((faq, similarity))
        
        # Сортируем по убыванию сходства
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:limit]
    
    @staticmethod
    def hybrid_search_faq(query: str) -> Optional[dict]:
        """
        Гибридный поиск: keyword + semantic
        
        Args:
            query: Запрос пользователя
            
        Returns:
            Dict с answer, url, faq_obj или None
        """
        from ..services.faq_service import FAQSearchService
        
        # 1. Сначала пробуем keyword-поиск (быстро, точно)
        keyword_result = FAQSearchService.search(query)
        if keyword_result:
            logger.info(f"✅ FAQ найден через keywords")
            return keyword_result
        
        # 2. Если не нашли - семантический поиск (умнее, дороже)
        semantic_results = SemanticSearchService.search_faq_semantic(query, min_similarity=0.65, limit=1)
        
        if semantic_results:
            faq, similarity = semantic_results[0]
            logger.info(f"✅ FAQ найден через semantic search (сходство: {similarity:.2%})")
            return {
                'answer': faq.answer,
                'url': faq.related_url if faq.related_url else None,
                'faq_obj': faq,
                'similarity': similarity
            }
        
        return None

