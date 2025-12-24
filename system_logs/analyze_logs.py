"""
Функции для анализа логов из базы данных.

Используйте эти функции для анализа ошибок и статистики!
"""
from django.utils import timezone
from datetime import timedelta
from typing import List, Dict, Any, Optional
from collections import Counter
from Asistent.models import SystemLog


def analyze_errors(hours: int = 24, limit: int = 100) -> Dict[str, Any]:
    """
    Анализирует ошибки за указанный период.
    
    Args:
        hours: За какой период в часах
        limit: Максимальное количество ошибок для анализа
    
    Returns:
        Словарь с анализом:
        {
            'total_errors': количество,
            'by_level': {level: count},
            'by_module': {module: count},
            'by_logger': {logger: count},
            'most_common_messages': [(message, count), ...],
            'recent_errors': [SystemLog, ...]
        }
    """
    since = timezone.now() - timedelta(hours=hours)
    errors = SystemLog.objects.filter(
        timestamp__gte=since,
        level__in=['ERROR', 'CRITICAL']
    ).order_by('-timestamp')[:limit]
    
    errors_list = list(errors)
    
    analysis = {
        'total_errors': len(errors_list),
        'by_level': Counter(log.level for log in errors_list),
        'by_module': Counter(log.module for log in errors_list if log.module),
        'by_logger': Counter(log.logger_name for log in errors_list),
        'most_common_messages': Counter(
            log.message[:100] for log in errors_list
        ).most_common(10),
        'recent_errors': errors_list[:20]
    }
    
    return analysis


def get_error_statistics(hours: int = 24) -> Dict[str, Any]:
    """
    Получить статистику по ошибкам.
    
    Args:
        hours: За какой период в часах
    
    Returns:
        Словарь со статистикой
    """
    since = timezone.now() - timedelta(hours=hours)
    
    total = SystemLog.objects.filter(timestamp__gte=since).count()
    errors = SystemLog.objects.filter(
        timestamp__gte=since,
        level__in=['ERROR', 'CRITICAL']
    ).count()
    warnings = SystemLog.objects.filter(
        timestamp__gte=since,
        level='WARNING'
    ).count()
    
    error_rate = (errors / total * 100) if total > 0 else 0
    
    return {
        'total_logs': total,
        'errors': errors,
        'warnings': warnings,
        'error_rate_percent': round(error_rate, 2),
        'period_hours': hours
    }


def get_module_statistics(hours: int = 24, top_n: int = 10) -> List[Dict[str, Any]]:
    """
    Получить статистику по модулям (какие модули генерируют больше всего логов).
    
    Args:
        hours: За какой период в часах
        top_n: Топ N модулей
    
    Returns:
        Список словарей с статистикой по модулям
    """
    since = timezone.now() - timedelta(hours=hours)
    
    from django.db.models import Count, Q
    
    stats = SystemLog.objects.filter(
        timestamp__gte=since,
        module__isnull=False
    ).exclude(module='').values('module').annotate(
        total=Count('id'),
        errors=Count('id', filter=Q(level__in=['ERROR', 'CRITICAL'])),
        warnings=Count('id', filter=Q(level='WARNING'))
    ).order_by('-total')[:top_n]
    
    return list(stats)


def get_level_statistics(hours: int = 24) -> Dict[str, int]:
    """
    Получить статистику по уровням логирования.
    
    Args:
        hours: За какой период в часах
    
    Returns:
        Словарь {level: count}
    """
    since = timezone.now() - timedelta(hours=hours)
    
    from django.db.models import Count
    
    stats = SystemLog.objects.filter(
        timestamp__gte=since
    ).values('level').annotate(count=Count('id'))
    
    return {item['level']: item['count'] for item in stats}


def find_common_errors(hours: int = 24, min_occurrences: int = 2) -> List[Dict[str, Any]]:
    """
    Найти часто повторяющиеся ошибки.
    
    Args:
        hours: За какой период в часах
        min_occurrences: Минимальное количество повторений
    
    Returns:
        Список словарей с информацией об ошибках
    """
    since = timezone.now() - timedelta(hours=hours)
    
    errors = SystemLog.objects.filter(
        timestamp__gte=since,
        level__in=['ERROR', 'CRITICAL']
    )
    
    # Группируем по первым 100 символам сообщения
    from django.db.models import Count, Min
    
    grouped = errors.values('message').annotate(
        count=Count('id'),
        first_occurrence=Min('timestamp'),
        last_occurrence=Min('timestamp')
    ).filter(count__gte=min_occurrences).order_by('-count')
    
    result = []
    for item in grouped:
        # Получаем пример ошибки
        example = errors.filter(message=item['message']).first()
        result.append({
            'message': item['message'][:200],
            'count': item['count'],
            'first_occurrence': item['first_occurrence'],
            'last_occurrence': item['last_occurrence'],
            'module': example.module if example else '',
            'logger': example.logger_name if example else '',
        })
    
    return result

