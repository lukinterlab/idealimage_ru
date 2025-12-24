"""
Низкоуровневый клиент для работы с GigaChat API
Отделяет работу с API от бизнес-логики выбора модели
"""
import os
import json
import logging
import time
import asyncio
from typing import Dict, List, Optional, Any
from django.conf import settings
from django.core.cache import cache
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class GigaChatAPIClient:
    """
    Низкоуровневый клиент для работы с GigaChat API
    Отвечает только за сетевые вызовы и обработку ошибок API
    """
    
    def __init__(self):
        self.base_url = "https://gigachat.devices.sberbank.ru/api/v1"
        self.token = self._get_token()
        self.session = self._create_session()
        
    def _get_token(self) -> str:
        """Получение токена из настроек"""
        token = getattr(settings, 'GIGACHAT_CREDENTIALS', None)
        if not token:
            token = os.getenv('GIGACHAT_CREDENTIALS')
        if not token:
            raise ValueError("GIGACHAT_CREDENTIALS не найдены в настройках или переменных окружения")
        return token
    
    def _create_session(self) -> requests.Session:
        """Создание сессии с повторными попытками"""
        session = requests.Session()
        
        # Настройка повторных попыток
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        # Установка заголовков по умолчанию
        session.headers.update({
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
        })
        
        return session
    
    def chat(self, message: str, system_prompt: Optional[str] = None, timeout: int = 30) -> str:
        """
        Вызов чат-модели GigaChat
        
        Args:
            message: Сообщение пользователя
            system_prompt: Системный промпт (необязательно)
            timeout: Таймаут запроса в секундах
        
        Returns:
            Ответ модели
            
        Raises:
            requests.RequestException: При ошибках API
        """
        url = f"{self.base_url}/chat/completions"
        
        messages = [{"role": "user", "content": message}]
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})
        
        payload = {
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2048,
            "stream": False
        }
        
        try:
            response = self.session.post(url, json=payload, timeout=timeout)
            response.raise_for_status()
            
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                raise RateLimitExceeded("Превышен лимит запросов к GigaChat API", retry_after=300)
            elif response.status_code == 401:
                raise AuthenticationError("Неверные учетные данные для GigaChat API")
            elif response.status_code == 400:
                error_detail = response.text
                logger.error(f"GigaChat API error 400: {error_detail}")
                raise APIError(f"Ошибка API: {error_detail}")
            else:
                logger.error(f"GigaChat API error {response.status_code}: {response.text}")
                raise APIError(f"Ошибка API: {response.status_code} - {response.text}")
                
        except requests.exceptions.Timeout:
            logger.error(f"GigaChat API timeout after {timeout} seconds")
            raise APIError(f"Таймаут запроса к API ({timeout} секунд)")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"GigaChat API request error: {e}")
            raise APIError(f"Ошибка запроса к API: {str(e)}")
    
    async def generate_and_save_image(self, prompt: str, timeout: int = 60) -> Optional[str]:
        """
        Асинхронная генерация изображения
        
        Args:
            prompt: Промпт для генерации изображения
            timeout: Таймаут в секундах
        
        Returns:
            Путь к сохраненному изображению или None
        """
        try:
            # Сначала генерируем изображение
            image_url = await self._generate_image_sync(prompt, timeout)
            
            if not image_url:
                return None
            
            # Загружаем и сохраняем изображение
            import requests
            image_response = requests.get(image_url, timeout=timeout)
            image_response.raise_for_status()
            
            # Сохраняем изображение
            from django.core.files.base import ContentFile
            from django.core.files.storage import default_storage
            import uuid
            from datetime import datetime
            
            # Создаем имя файла
            filename = f"gigachat_images/{datetime.now().strftime('%Y/%m/%d')}/{uuid.uuid4()}.png"
            
            # Сохраняем файл
            path = default_storage.save(filename, ContentFile(image_response.content))
            
            logger.info(f"Generated and saved image: {path}")
            return path
            
        except Exception as e:
            logger.error(f"Error generating and saving image: {e}")
            raise
    
    async def _generate_image_sync(self, prompt: str, timeout: int) -> Optional[str]:
        """
        Синхронная генерация изображения через API
        """
        # Этот метод будет использовать синхронный вызов, но в асинхронной обертке
        # для совместимости с существующим кодом
        return self._generate_image_sync_impl(prompt, timeout)
    
    def _generate_image_sync_impl(self, prompt: str, timeout: int) -> Optional[str]:
        """
        Реализация генерации изображения
        """
        # URL для генерации изображений (фиктивный - заменить на реальный если есть)
        url = f"{self.base_url}/images/generate"
        
        payload = {
            "prompt": prompt,
            "size": "1024x1024",
            "n": 1
        }
        
        try:
            response = self.session.post(url, json=payload, timeout=timeout)
            response.raise_for_status()
            
            result = response.json()
            # Возвращаем URL первого сгенерированного изображения
            if 'data' in result and len(result['data']) > 0:
                return result['data'][0].get('url')
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Image generation API error: {e}")
            if response.status_code == 429:
                raise RateLimitExceeded("Превышен лимит запросов к GigaChat API для генерации изображений", retry_after=300)
        except Exception as e:
            logger.error(f"Image generation error: {e}")
        
        return None


class RateLimitExceeded(Exception):
    """Исключение при превышении лимита запросов"""
    def __init__(self, message: str, retry_after: int = 300):
        super().__init__(message)
        self.retry_after = retry_after


class AuthenticationError(Exception):
    """Исключение при ошибке аутентификации"""
    pass


class APIError(Exception):
    """Общее исключение для ошибок API"""
    pass


# Глобальный клиент для совместимости
def get_gigachat_client():
    """Возвращает экземпляр GigaChat клиента"""
    return GigaChatAPIClient()