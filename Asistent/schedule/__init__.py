"""
Автономная система управления расписаниями и задачами AI.
Содержит контекст выполнения расписаний, стратегии, сервисы и модели.

Использование в других проектах:
    1. Добавить 'Asistent.schedule' в INSTALLED_APPS
    2. Запустить миграции: python manage.py migrate
    3. Настроить зависимости через ServiceLocator (см. interfaces.py)
"""

# Модели
# Модели импортируются лениво, чтобы избежать циклических импортов
# Используйте: from Asistent.schedule.models import AISchedule, AIScheduleRun

# Контекст и логирование
from .context import ScheduleContext
# RunLogger импортируется лениво, чтобы избежать раннего импорта моделей

# Все импорты делаются лениво через __getattr__ для избежания циклических импортов

# Ленивый импорт для всех компонентов
def __getattr__(name):
    """Ленивый импорт для избежания циклических импортов и AppRegistryNotReady"""
    # Модели
    if name == 'AISchedule':
        from .models import AISchedule
        return AISchedule
    elif name == 'AIScheduleRun':
        from .models import AIScheduleRun
        return AIScheduleRun
    # Контекст и логирование
    elif name == 'ScheduleContext':
        from .context import ScheduleContext
        return ScheduleContext
    elif name == 'RunLogger':
        from .logger import RunLogger
        return RunLogger
    # Стратегии
    elif name == 'ScheduleStrategy':
        from .strategies import ScheduleStrategy
        return ScheduleStrategy
    elif name == 'PromptScheduleStrategy':
        from .strategies import PromptScheduleStrategy
        return PromptScheduleStrategy
    elif name == 'SystemScheduleStrategy':
        from .strategies import SystemScheduleStrategy
        return SystemScheduleStrategy
    elif name == 'ManualScheduleStrategy':
        from .strategies import ManualScheduleStrategy
        return ManualScheduleStrategy
    elif name == 'HoroscopeScheduleStrategy':
        from .strategies import HoroscopeScheduleStrategy
        return HoroscopeScheduleStrategy
    # Задачи
    elif name == 'run_specific_schedule':
        from .tasks import run_specific_schedule
        return run_specific_schedule
    elif name == 'calculate_next_run_delta':
        from .tasks import calculate_next_run_delta
        return calculate_next_run_delta
    elif name == 'run_prompt_schedule':
        from .tasks import run_prompt_schedule
        return run_prompt_schedule
    elif name == 'run_system_task':
        from .tasks import run_system_task
        return run_system_task
    elif name == 'generate_horoscope_from_prompt_template':
        from .horoscope import generate_horoscope_from_prompt_template
        return generate_horoscope_from_prompt_template
    # Интерфейсы
    elif name == 'ServiceLocator':
        from .interfaces import ServiceLocator
        return ServiceLocator
    elif name == 'get_content_generator':
        from .interfaces import get_content_generator
        return get_content_generator
    elif name == 'get_seo_optimizer':
        from .interfaces import get_seo_optimizer
        return get_seo_optimizer
    elif name == 'get_content_parser':
        from .interfaces import get_content_parser
        return get_content_parser
    elif name == 'get_telegram_client':
        from .interfaces import get_telegram_client
        return get_telegram_client
    elif name == 'get_formatter':
        from .interfaces import get_formatter
        return get_formatter
    elif name == 'get_utils':
        from .interfaces import get_utils
        return get_utils
    # Метрики
    elif name == 'get_horoscope_metrics':
        from .metrics import get_horoscope_metrics
        return get_horoscope_metrics
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    # Модели (ленивый импорт)
    "AISchedule",
    "AIScheduleRun",
    # Контекст
    "ScheduleContext",
    "RunLogger",  # Ленивый импорт
    # Стратегии
    "ScheduleStrategy",
    "PromptScheduleStrategy",
    "SystemScheduleStrategy",
    "ManualScheduleStrategy",
    "HoroscopeScheduleStrategy",
    # Задачи
    "run_specific_schedule",
    "calculate_next_run_delta",
    "run_prompt_schedule",
    "run_system_task",
    "generate_horoscope_from_prompt_template",
    # Интерфейсы
    "ServiceLocator",
    "get_content_generator",
    "get_seo_optimizer",
    "get_content_parser",
    "get_telegram_client",
    "get_formatter",
    "get_utils",
    # Метрики
    "get_horoscope_metrics",
]

# Версия модуля
__version__ = "1.0.0"

