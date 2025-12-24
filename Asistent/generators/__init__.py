"""
Универсальный генератор контента для idealimage.ru

Объединяет:
- Test_Promot (модульная архитектура)
- tasks.py (очереди, heartbeat, приоритизация)
- schedule (интеграция с расписаниями)

Режимы работы:
- AUTO: Полная автоматизация
- INTERACTIVE: Ручной запуск с предпросмотром
- BATCH: Массовая генерация
- SCHEDULED: Через систему schedule
"""

from .base import GeneratorMode, GeneratorConfig, GenerationResult
from .universal import UniversalContentGenerator

__all__ = [
    'GeneratorMode',
    'GeneratorConfig',
    'GenerationResult',
    'UniversalContentGenerator',
]


