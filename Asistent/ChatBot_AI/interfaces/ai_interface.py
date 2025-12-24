"""
Интерфейс для AI провайдеров

Абстракция для различных AI систем (GigaChat, OpenAI, Claude и т.д.)
"""

from abc import ABC, abstractmethod
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class BaseAIProvider(ABC):
    """Базовый класс для AI провайдеров"""
    
    @abstractmethod
    def get_response(self, prompt: str, system_prompt: str = None) -> Dict:
        """
        Получить ответ от AI
        
        Args:
            prompt: Запрос пользователя
            system_prompt: Системный промпт (опционально)
            
        Returns:
            Dict с ключами:
                - success (bool): Успешность запроса
                - text (str): Текст ответа
                - error (str): Текст ошибки (если есть)
        """
        pass


class GigaChatProvider(BaseAIProvider):
    """Провайдер для GigaChat API"""
    
    def get_response(self, prompt: str, system_prompt: str = None) -> Dict:
        """
        Получить ответ от GigaChat
        
        Args:
            prompt: Запрос пользователя
            system_prompt: Системный промпт
            
        Returns:
            Dict с результатом вызова GigaChat
        """
        try:
            from Asistent.gigachat_api import call_gigachat_api
            return call_gigachat_api(prompt, system_prompt)
        except Exception as e:
            logger.error(f"Ошибка вызова GigaChat: {e}")
            return {
                'success': False,
                'text': '',
                'error': str(e)
            }

