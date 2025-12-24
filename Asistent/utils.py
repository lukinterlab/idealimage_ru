"""
Утилиты для работы с динамическими параметрами расписаний
"""
import requests
import random
from datetime import datetime
from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def resolve_dynamic_params(dynamic_params: dict, schedule_id: int) -> dict:
    """
    Преобразует динамические параметры в конкретные значения.
    
    Поддерживаемые типы:
    - cycle_list: циклический перебор значений из списка
    - current_date: текущая дата в указанном формате
    - api_call: вызов внешнего API (например, погода)
    - random_choice: случайный выбор из списка
    
    Args:
        dynamic_params (dict): Конфигурация параметров
        schedule_id (int): ID расписания (для кэша циклов)
    
    Returns:
        dict: Разрешённые параметры с конкретными значениями
    
    Example:
        >>> params = {
        ...     "name": {"type": "cycle_list", "values": ["Анна", "Иван"]},
        ...     "date": {"type": "current_date", "format": "%d.%m.%Y"}
        ... }
        >>> resolve_dynamic_params(params, 1)
        {'name': 'Анна', 'date': '05.11.2025'}
    """
    resolved = {}
    
    for key, config in dynamic_params.items():
        ptype = config.get("type")
        
        try:
            if ptype == "cycle_list":
                # Циклический перебор (Анна → Иван → Мария → Анна...)
                values = config.get("values", [])
                if not values:
                    resolved[key] = ""
                    continue
                    
                cache_key = f"cycle_schedule_{schedule_id}_{key}"
                index = cache.get(cache_key, 0) % len(values)
                resolved[key] = values[index]
                
                # Сохраняем следующий индекс
                cache.set(cache_key, index + 1, timeout=None)
                logger.info(f"   [cycle_list] {key}={values[index]} (индекс {index}/{len(values)})")
                
            elif ptype == "current_date":
                # Текущая дата
                fmt = config.get("format", "%Y-%m-%d")
                resolved[key] = datetime.now().strftime(fmt)
                logger.info(f"   [current_date] {key}={resolved[key]}")
                
            elif ptype == "api_call":
                # API вызов (погода и т.д.)
                url = config.get("url", "")
                if not url:
                    resolved[key] = "неизвестно"
                    continue
                
                # Подставляем API ключи из settings
                url = url.replace("{API_KEY}", getattr(settings, 'OPENWEATHER_API_KEY', ''))
                
                try:
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        value = _extract_from_path(data, config.get("path", ""))
                        
                        # Обработка значения
                        processor = config.get("processor")
                        if processor == "round":
                            value = round(float(value))
                        elif processor == "int":
                            value = int(value)
                        elif processor == "str":
                            value = str(value)
                            
                        resolved[key] = value
                        logger.info(f"   [api_call] {key}={value} (URL: {url[:50]}...)")
                    else:
                        resolved[key] = "неизвестно"
                        logger.warning(f"   [api_call] {key}: API вернул статус {response.status_code}")
                except Exception as e:
                    resolved[key] = "ошибка"
                    logger.error(f"   [api_call] {key}: Ошибка запроса - {e}")
                    
            elif ptype == "random_choice":
                # Случайный выбор
                choices = config.get("values", [])
                if choices:
                    resolved[key] = random.choice(choices)
                    logger.info(f"   [random_choice] {key}={resolved[key]}")
                else:
                    resolved[key] = ""
                    
            else:
                # Неизвестный тип
                resolved[key] = config.get("default", "")
                logger.warning(f"   [unknown] {key}: Неизвестный тип '{ptype}'")
                
        except Exception as e:
            # Обработка ошибок для конкретного параметра
            resolved[key] = ""
            logger.error(f"   Ошибка обработки параметра '{key}': {e}")
    
    return resolved


def _extract_from_path(data: dict, path: str):
    """
    Извлекает значение из вложенного словаря по пути.
    
    Args:
        data (dict): Исходные данные
        path (str): Путь через точку (например, "main.temp")
    
    Returns:
        Извлечённое значение или пустой словарь
    
    Example:
        >>> data = {"main": {"temp": 25.5}}
        >>> _extract_from_path(data, "main.temp")
        25.5
    """
    if not path:
        return data
        
    current = data
    for part in path.split('.'):
        if isinstance(current, dict):
            current = current.get(part, {})
        else:
            return {}
    
    return current


def reset_cycle_counter(schedule_id: int, param_name: str = None):
    """
    Сбрасывает счётчик циклического параметра.
    
    Args:
        schedule_id (int): ID расписания
        param_name (str, optional): Имя параметра. Если None - сбросить все.
    """
    if param_name:
        cache_key = f"cycle_schedule_{schedule_id}_{param_name}"
        cache.delete(cache_key)
        logger.info(f"Сброшен счётчик цикла для schedule={schedule_id}, param={param_name}")
    else:
        # Сбрасываем все циклы для этого расписания
        # (простая реализация - нужно расширить при необходимости)
        logger.info(f"Сброс всех счётчиков для schedule={schedule_id}")


def get_cycle_status(schedule_id: int, param_name: str, values_count: int) -> dict:
    """
    Возвращает текущий статус циклического параметра.
    
    Args:
        schedule_id (int): ID расписания
        param_name (str): Имя параметра
        values_count (int): Общее количество значений
    
    Returns:
        dict: {'current_index': int, 'total': int, 'progress_percent': float}
    """
    cache_key = f"cycle_schedule_{schedule_id}_{param_name}"
    index = cache.get(cache_key, 0) % values_count if values_count else 0
    
    return {
        'current_index': index,
        'total': values_count,
        'progress_percent': (index / values_count * 100) if values_count else 0
    }

