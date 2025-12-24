"""
Функции для чтения логов из базы данных.

Используйте эти функции для получения логов вместо создания временных скриптов!
"""
from django.utils import timezone
from datetime import timedelta
from typing import List, Optional, Dict, Any
from Asistent.models import SystemLog


def get_recent_logs(limit: int = 100, hours: Optional[int] = None) -> List[SystemLog]:
    """
    Получить последние логи из базы данных.
    
    Args:
        limit: Максимальное количество логов
        hours: За какой период (если None - все доступные, но не более 24 часов)
    
    Returns:
        Список объектов SystemLog
    """
    queryset = SystemLog.objects.all()
    
    if hours:
        since = timezone.now() - timedelta(hours=hours)
        queryset = queryset.filter(timestamp__gte=since)
    else:
        # По умолчанию - последние 24 часа (максимум хранения)
        since = timezone.now() - timedelta(hours=24)
        queryset = queryset.filter(timestamp__gte=since)
    
    return list(queryset.order_by('-timestamp')[:limit])


def get_errors(limit: int = 50, hours: Optional[int] = 24) -> List[SystemLog]:
    """
    Получить только ошибки (ERROR и CRITICAL).
    
    Args:
        limit: Максимальное количество логов
        hours: За какой период в часах
    
    Returns:
        Список объектов SystemLog с уровнем ERROR или CRITICAL
    """
    since = timezone.now() - timedelta(hours=hours) if hours else timezone.now() - timedelta(hours=24)
    
    return list(
        SystemLog.objects.filter(
            timestamp__gte=since,
            level__in=['ERROR', 'CRITICAL']
        ).order_by('-timestamp')[:limit]
    )


def get_warnings(limit: int = 50, hours: Optional[int] = 24) -> List[SystemLog]:
    """
    Получить только предупреждения (WARNING).
    
    Args:
        limit: Максимальное количество логов
        hours: За какой период в часах
    
    Returns:
        Список объектов SystemLog с уровнем WARNING
    """
    since = timezone.now() - timedelta(hours=hours) if hours else timezone.now() - timedelta(hours=24)
    
    return list(
        SystemLog.objects.filter(
            timestamp__gte=since,
            level='WARNING'
        ).order_by('-timestamp')[:limit]
    )


def get_logs_by_module(module_name: str, limit: int = 100, hours: Optional[int] = 24) -> List[SystemLog]:
    """
    Получить логи по имени модуля.
    
    Args:
        module_name: Имя модуля (например: 'Asistent.views', 'blog.models')
        limit: Максимальное количество логов
        hours: За какой период в часах
    
    Returns:
        Список объектов SystemLog
    """
    since = timezone.now() - timedelta(hours=hours) if hours else timezone.now() - timedelta(hours=24)
    
    return list(
        SystemLog.objects.filter(
            timestamp__gte=since,
            module__icontains=module_name
        ).order_by('-timestamp')[:limit]
    )


def get_logs_by_logger(logger_name: str, limit: int = 100, hours: Optional[int] = 24) -> List[SystemLog]:
    """
    Получить логи по имени логгера.
    
    Args:
        logger_name: Имя логгера (например: 'django', 'Asistent', 'django-q')
        limit: Максимальное количество логов
        hours: За какой период в часах
    
    Returns:
        Список объектов SystemLog
    """
    since = timezone.now() - timedelta(hours=hours) if hours else timezone.now() - timedelta(hours=24)
    
    return list(
        SystemLog.objects.filter(
            timestamp__gte=since,
            logger_name=logger_name
        ).order_by('-timestamp')[:limit]
    )


def get_logs_by_level(level: str, limit: int = 100, hours: Optional[int] = 24) -> List[SystemLog]:
    """
    Получить логи по уровню.
    
    Args:
        level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        limit: Максимальное количество логов
        hours: За какой период в часах
    
    Returns:
        Список объектов SystemLog
    """
    since = timezone.now() - timedelta(hours=hours) if hours else timezone.now() - timedelta(hours=24)
    
    return list(
        SystemLog.objects.filter(
            timestamp__gte=since,
            level=level.upper()
        ).order_by('-timestamp')[:limit]
    )


def get_logs_by_time_range(start_time, end_time, limit: int = 1000) -> List[SystemLog]:
    """
    Получить логи за указанный период времени.
    
    Args:
        start_time: Начало периода (datetime)
        end_time: Конец периода (datetime)
        limit: Максимальное количество логов
    
    Returns:
        Список объектов SystemLog
    """
    return list(
        SystemLog.objects.filter(
            timestamp__gte=start_time,
            timestamp__lte=end_time
        ).order_by('-timestamp')[:limit]
    )

