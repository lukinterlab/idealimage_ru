"""
Интерфейсы (абстракции) для внедрения зависимостей.
Позволяет приложению schedule работать с внешними сервисами без жёсткой привязки.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime


class ContentGeneratorInterface(ABC):
    """Интерфейс для генерации контента через AI"""
    
    @abstractmethod
    def chat(self, message: str, **kwargs) -> str:
        """Генерирует текст на основе промпта"""
        pass
    
    @abstractmethod
    def get_usage_stats(self) -> Dict[str, Any]:
        """Возвращает статистику использования API"""
        pass


class SEOOptimizerInterface(ABC):
    """Интерфейс для SEO-оптимизации контента"""
    
    @abstractmethod
    def optimize_content(self, content: str, **kwargs) -> Dict[str, Any]:
        """Оптимизирует контент для SEO"""
        pass
    
    @abstractmethod
    def generate_meta_tags(self, title: str, content: str) -> Dict[str, str]:
        """Генерирует мета-теги"""
        pass
    
    @abstractmethod
    def generate_faq_block(self, post, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Генерирует блок FAQ для статьи"""
        pass


class ContentParserInterface(ABC):
    """Интерфейс для парсинга контента с внешних источников"""
    
    @abstractmethod
    def parse_url(self, url: str, **kwargs) -> Dict[str, Any]:
        """Парсит контент по URL"""
        pass
    
    @abstractmethod
    def extract_metadata(self, url: str) -> Dict[str, Any]:
        """Извлекает метаданные со страницы"""
        pass


class NotificationInterface(ABC):
    """Интерфейс для отправки уведомлений"""
    
    @abstractmethod
    def send(self, message: str, recipients: List[str], **kwargs) -> bool:
        """Отправляет уведомление"""
        pass
    
    @abstractmethod
    def send_to_telegram(self, message: str, chat_id: Optional[str] = None) -> bool:
        """Отправляет уведомление в Telegram"""
        pass


class TelegramClientInterface(ABC):
    """Интерфейс для работы с Telegram API"""
    
    @abstractmethod
    def send_message(self, chat_id: str, text: str, **kwargs) -> bool:
        """Отправляет сообщение в Telegram"""
        pass
    
    @abstractmethod
    def send_photo(self, chat_id: str, photo_path: str, caption: str = "", **kwargs) -> bool:
        """Отправляет фото в Telegram"""
        pass


class ImageGeneratorInterface(ABC):
    """Интерфейс для генерации изображений"""
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> Optional[str]:
        """Генерирует изображение по промпту, возвращает путь к файлу"""
        pass
    
    @abstractmethod
    def optimize_image(self, image_path: str, **kwargs) -> str:
        """Оптимизирует изображение"""
        pass


class WebmasterInterface(ABC):
    """Интерфейс для работы с Яндекс.Вебмастер и другими вебмастер-сервисами"""
    
    @abstractmethod
    def submit_url(self, url: str) -> Dict[str, Any]:
        """Отправляет URL на индексацию"""
        pass
    
    @abstractmethod
    def check_indexing_status(self, url: str) -> Dict[str, Any]:
        """Проверяет статус индексации"""
        pass


class FormatterInterface(ABC):
    """Интерфейс для форматирования контента (Markdown, HTML и т.д.)"""
    
    @abstractmethod
    def render_markdown(self, text: str, preset: Optional[str] = None) -> str:
        """Преобразует Markdown в HTML"""
        pass
    
    @abstractmethod
    def strip_html(self, text: str) -> str:
        """Удаляет HTML-теги"""
        pass


class UtilsInterface(ABC):
    """Интерфейс для вспомогательных утилит"""
    
    @abstractmethod
    def resolve_dynamic_params(self, params: Dict[str, Any], schedule_id: int) -> Dict[str, Any]:
        """Разрешает динамические параметры"""
        pass


# ============================================================================
# Базовый класс для сервис-локатора (Service Locator pattern)
# ============================================================================

class ServiceLocator:
    """
    Сервис-локатор для получения реализаций интерфейсов.
    Позволяет настраивать зависимости через settings.py или вручную.
    """
    
    _services: Dict[str, Any] = {}
    
    @classmethod
    def register(cls, interface_name: str, implementation: Any) -> None:
        """Регистрирует реализацию интерфейса"""
        cls._services[interface_name] = implementation
    
    @classmethod
    def get(cls, interface_name: str, default: Any = None) -> Any:
        """Получает реализацию интерфейса"""
        return cls._services.get(interface_name, default)
    
    @classmethod
    def has(cls, interface_name: str) -> bool:
        """Проверяет наличие реализации"""
        return interface_name in cls._services
    
    @classmethod
    def clear(cls) -> None:
        """Очищает все зарегистрированные сервисы"""
        cls._services.clear()


# ============================================================================
# Функции-хелперы для получения сервисов
# ============================================================================

def get_content_generator() -> ContentGeneratorInterface:
    """Возвращает реализацию генератора контента"""
    generator = ServiceLocator.get('content_generator')
    if not generator:
        # Fallback: импортируем из Asistent
        from Asistent.gigachat_api import get_gigachat_client
        generator = get_gigachat_client()
        ServiceLocator.register('content_generator', generator)
    return generator


def get_seo_optimizer() -> SEOOptimizerInterface:
    """Возвращает реализацию SEO-оптимизатора"""
    optimizer = ServiceLocator.get('seo_optimizer')
    if not optimizer:
        # Fallback: импортируем из Asistent
        from Asistent.seo_advanced import AdvancedSEOOptimizer
        optimizer = AdvancedSEOOptimizer()
        ServiceLocator.register('seo_optimizer', optimizer)
    return optimizer


def get_content_parser() -> ContentParserInterface:
    """Возвращает реализацию парсера контента"""
    parser = ServiceLocator.get('content_parser')
    if not parser:
        # Fallback: импортируем из Asistent
        from Asistent.parsers.universal_parser import UniversalParser
        parser = UniversalParser()
        ServiceLocator.register('content_parser', parser)
    return parser


def get_telegram_client() -> TelegramClientInterface:
    """Возвращает реализацию Telegram-клиента"""
    client = ServiceLocator.get('telegram_client')
    if not client:
        # Fallback: импортируем из Asistent
        from Asistent.services.telegram_client import get_telegram_client as get_tg
        client = get_tg()
        ServiceLocator.register('telegram_client', client)
    return client


def get_formatter():
    """Возвращает реализацию форматтера"""
    formatter = ServiceLocator.get('formatter')
    if not formatter:
        # Fallback: импортируем из Asistent
        from Asistent import formatting
        ServiceLocator.register('formatter', formatting)
    return formatter


def get_utils():
    """Возвращает реализацию утилит"""
    utils = ServiceLocator.get('utils')
    if not utils:
        # Fallback: импортируем из Asistent
        from Asistent import utils as asistent_utils
        ServiceLocator.register('utils', asistent_utils)
    return utils

