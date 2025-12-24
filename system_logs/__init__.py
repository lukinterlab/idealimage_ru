"""
Утилиты для работы с системными логами из базы данных.

Все функции для чтения, анализа и фильтрации логов находятся здесь.
Используйте эти функции вместо создания временных скриптов!
"""

from .read_logs import (
    get_recent_logs,
    get_errors,
    get_warnings,
    get_logs_by_module,
    get_logs_by_logger,
    get_logs_by_level,
    get_logs_by_time_range,
)

from .analyze_logs import (
    analyze_errors,
    get_error_statistics,
    get_module_statistics,
    get_level_statistics,
    find_common_errors,
)

from .filter_logs import (
    filter_by_level,
    filter_by_time,
    filter_by_text,
    filter_by_module,
    filter_by_logger,
    combine_filters,
)

from .quick_analysis import (
    quick_check,
    check_gigachat_errors,
)

__all__ = [
    # Чтение логов
    'get_recent_logs',
    'get_errors',
    'get_warnings',
    'get_logs_by_module',
    'get_logs_by_logger',
    'get_logs_by_level',
    'get_logs_by_time_range',
    # Анализ логов
    'analyze_errors',
    'get_error_statistics',
    'get_module_statistics',
    'get_level_statistics',
    'find_common_errors',
    # Фильтрация логов
    'filter_by_level',
    'filter_by_time',
    'filter_by_text',
    'filter_by_module',
    'filter_by_logger',
    'combine_filters',
    # Быстрый анализ
    'quick_check',
    'check_gigachat_errors',
]

