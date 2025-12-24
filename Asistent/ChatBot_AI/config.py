"""
Конфигурация провайдеров для ChatBot_AI

При переносе на другой проект - измените здесь реализации
"""

from .interfaces.ai_interface import GigaChatProvider
from .interfaces.search_interface import BlogSearchProvider

# Текущие реализации для IdealImage.ru
AI_PROVIDER = GigaChatProvider
SEARCH_PROVIDER = BlogSearchProvider

# Пример переопределения для другого проекта:
# from .interfaces.ai_interface import OpenAIProvider
# AI_PROVIDER = OpenAIProvider

