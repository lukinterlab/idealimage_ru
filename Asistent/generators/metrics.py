"""
Сбор и сохранение метрик генерации контента.
Интеграция с AIGeneratedArticle и расширенная аналитика.
"""

import time
import logging
from typing import Dict, Optional, Any
from django.utils import timezone

logger = logging.getLogger(__name__)


class MetricsTracker:
    """
    Трекер метрик для генерации контента.
    
    Собирает:
    - Время генерации
    - Количество API calls
    - Использованные модели
    - Ошибки и retry
    - Токены (если доступно)
    """
    
    def __init__(self):
        self.start_time = time.time()
        self.metrics = {
            'generation_start': timezone.now().isoformat(),
            'api_calls': 0,
            'retry_count': 0,
            'errors': [],
            'model_used': None,
            'tokens_used': 0,
            'queue_position': None,
            'heartbeat_updates': 0,
        }
    
    def record_api_call(self, model: Optional[str] = None):
        """
        Запись API вызова.
        
        Args:
            model: Название использованной модели
        """
        self.metrics['api_calls'] += 1
        if model:
            self.metrics['model_used'] = model
    
    def record_retry(self):
        """Запись повторной попытки"""
        self.metrics['retry_count'] += 1
    
    def record_error(self, error: str):
        """
        Запись ошибки.
        
        Args:
            error: Описание ошибки
        """
        self.metrics['errors'].append(error)
    
    def record_tokens(self, tokens: int):
        """
        Запись использованных токенов.
        
        Args:
            tokens: Количество токенов
        """
        self.metrics['tokens_used'] += tokens
    
    def record_queue_position(self, position: int):
        """
        Запись позиции в очереди.
        
        Args:
            position: Позиция в очереди
        """
        self.metrics['queue_position'] = position
    
    def record_heartbeat_update(self):
        """Запись обновления heartbeat"""
        self.metrics['heartbeat_updates'] += 1
    
    def get_generation_time(self) -> int:
        """
        Получение времени генерации в секундах.
        
        Returns:
            Время генерации в секундах
        """
        return int(time.time() - self.start_time)
    
    def get_data(self) -> Dict[str, Any]:
        """
        Получение всех метрик.
        
        Returns:
            Словарь с метриками
        """
        return {
            **self.metrics,
            'generation_time_seconds': self.get_generation_time(),
            'generation_end': timezone.now().isoformat(),
        }
    
    def save_to_database(
        self,
        schedule=None,
        post=None,
        prompt_text: str = '',
        ai_response: str = '',
        source_urls: list = None
    ):
        """
        Сохранение метрик в базу данных (AIGeneratedArticle).
        
        Args:
            schedule: Объект AISchedule (если есть)
            post: Объект Post
            prompt_text: Текст промпта
            ai_response: Ответ AI
            source_urls: Использованные источники
        """
        try:
            from Asistent.models import AIGeneratedArticle
            
            ai_article = AIGeneratedArticle.objects.create(
                schedule=schedule,
                article=post,
                prompt=prompt_text[:5000],  # Ограничиваем длину
                ai_response=ai_response[:10000],  # Ограничиваем длину
                generation_time_seconds=self.get_generation_time(),
                api_calls_count=self.metrics['api_calls'],
                source_urls=source_urls or [],
            )
            
            logger.info(
                f"   📊 Метрики сохранены: "
                f"время={self.get_generation_time()}с, "
                f"API вызовов={self.metrics['api_calls']}, "
                f"retry={self.metrics['retry_count']}"
            )
            
            return ai_article
            
        except Exception as e:
            logger.warning(f"   ⚠️ Не удалось сохранить метрики: {e}")
            return None
    
    def log_summary(self):
        """Вывод summary метрик в лог"""
        logger.info(f"   📊 МЕТРИКИ ГЕНЕРАЦИИ:")
        logger.info(f"      Время: {self.get_generation_time()} сек")
        logger.info(f"      API вызовов: {self.metrics['api_calls']}")
        logger.info(f"      Retry: {self.metrics['retry_count']}")
        logger.info(f"      Модель: {self.metrics['model_used'] or 'N/A'}")
        logger.info(f"      Токены: {self.metrics['tokens_used']}")
        if self.metrics['errors']:
            logger.info(f"      Ошибки: {len(self.metrics['errors'])}")


