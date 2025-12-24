"""Интерфейсы для внешних зависимостей"""

from .ai_interface import BaseAIProvider, GigaChatProvider
from .search_interface import BaseSearchProvider, BlogSearchProvider

__all__ = [
    'BaseAIProvider',
    'GigaChatProvider',
    'BaseSearchProvider',
    'BlogSearchProvider',
]

