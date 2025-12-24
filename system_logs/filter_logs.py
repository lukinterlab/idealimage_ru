"""
Функции для фильтрации логов из базы данных.

Используйте эти функции для поиска конкретных логов!
"""
from django.utils import timezone
from datetime import timedelta, datetime
from typing import List, Optional, Callable
from django.db.models import Q
from Asistent.models import SystemLog


def filter_by_level(
    level: str,
    hours: Optional[int] = 24,
    limit: int = 100
) -> List[SystemLog]:
    """
    Фильтровать логи по уровню.
    
    Args:
        level: Уровень (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        hours: За какой период в часах (None = все доступные)
        limit: Максимальное количество
    
    Returns:
        Список объектов SystemLog
    """
    queryset = SystemLog.objects.filter(level=level.upper())
    
    if hours:
        since = timezone.now() - timedelta(hours=hours)
        queryset = queryset.filter(timestamp__gte=since)
    
    return list(queryset.order_by('-timestamp')[:limit])


def filter_by_time(
    start_time: datetime,
    end_time: Optional[datetime] = None,
    limit: int = 1000
) -> List[SystemLog]:
    """
    Фильтровать логи по времени.
    
    Args:
        start_time: Начало периода
        end_time: Конец периода (если None - до текущего момента)
        limit: Максимальное количество
    
    Returns:
        Список объектов SystemLog
    """
    queryset = SystemLog.objects.filter(timestamp__gte=start_time)
    
    if end_time:
        queryset = queryset.filter(timestamp__lte=end_time)
    
    return list(queryset.order_by('-timestamp')[:limit])


def filter_by_text(
    search_text: str,
    hours: Optional[int] = 24,
    limit: int = 100
) -> List[SystemLog]:
    """
    Фильтровать логи по тексту в сообщении.
    
    Args:
        search_text: Текст для поиска
        hours: За какой период в часах
        limit: Максимальное количество
    
    Returns:
        Список объектов SystemLog
    """
    queryset = SystemLog.objects.filter(message__icontains=search_text)
    
    if hours:
        since = timezone.now() - timedelta(hours=hours)
        queryset = queryset.filter(timestamp__gte=since)
    
    return list(queryset.order_by('-timestamp')[:limit])


def filter_by_module(
    module_name: str,
    hours: Optional[int] = 24,
    limit: int = 100
) -> List[SystemLog]:
    """
    Фильтровать логи по модулю.
    
    Args:
        module_name: Имя модуля (частичное совпадение)
        hours: За какой период в часах
        limit: Максимальное количество
    
    Returns:
        Список объектов SystemLog
    """
    queryset = SystemLog.objects.filter(module__icontains=module_name)
    
    if hours:
        since = timezone.now() - timedelta(hours=hours)
        queryset = queryset.filter(timestamp__gte=since)
    
    return list(queryset.order_by('-timestamp')[:limit])


def filter_by_logger(
    logger_name: str,
    hours: Optional[int] = 24,
    limit: int = 100
) -> List[SystemLog]:
    """
    Фильтровать логи по имени логгера.
    
    Args:
        logger_name: Имя логгера
        hours: За какой период в часах
        limit: Максимальное количество
    
    Returns:
        Список объектов SystemLog
    """
    queryset = SystemLog.objects.filter(logger_name=logger_name)
    
    if hours:
        since = timezone.now() - timedelta(hours=hours)
        queryset = queryset.filter(timestamp__gte=since)
    
    return list(queryset.order_by('-timestamp')[:limit])


def combine_filters(
    level: Optional[str] = None,
    logger_name: Optional[str] = None,
    module: Optional[str] = None,
    search_text: Optional[str] = None,
    hours: Optional[int] = 24,
    limit: int = 100
) -> List[SystemLog]:
    """
    Комбинировать несколько фильтров.
    
    Args:
        level: Уровень логирования
        logger_name: Имя логгера
        module: Имя модуля
        search_text: Текст для поиска в сообщении
        hours: За какой период в часах
        limit: Максимальное количество
    
    Returns:
        Список объектов SystemLog
    """
    queryset = SystemLog.objects.all()
    
    if level:
        queryset = queryset.filter(level=level.upper())
    
    if logger_name:
        queryset = queryset.filter(logger_name=logger_name)
    
    if module:
        queryset = queryset.filter(module__icontains=module)
    
    if search_text:
        queryset = queryset.filter(message__icontains=search_text)
    
    if hours:
        since = timezone.now() - timedelta(hours=hours)
        queryset = queryset.filter(timestamp__gte=since)
    
    return list(queryset.order_by('-timestamp')[:limit])

