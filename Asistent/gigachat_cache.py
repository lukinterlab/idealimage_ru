"""
Кэширование результатов GigaChat для экономии токенов
Экономия: 30-50% повторных запросов

ВАЖНО: Можно отключить через DISABLE_CACHE_FOR_TESTING=True в settings
для тестирования промтов без использования кэша
"""
import logging
import hashlib
from typing import Dict
from django.core.cache import cache
from django.conf import settings
from functools import wraps

logger = logging.getLogger(__name__)


def is_cache_disabled():
    """
    Проверяет отключен ли кэш для тестирования
    """
    return getattr(settings, 'DISABLE_CACHE_FOR_TESTING', False)


def gigachat_cache(ttl=604800, key_prefix='gigachat', skip_cache_if_disabled=True):
    """
    Декоратор для кэширования результатов GigaChat функций
    
    Args:
        ttl: Time to live в секундах (по умолчанию 7 дней)
        key_prefix: Префикс ключа кэша
        skip_cache_if_disabled: Пропускать кэш если DISABLE_CACHE_FOR_TESTING=True
    
    Usage:
        @gigachat_cache(ttl=86400, key_prefix='seo')
        def generate_seo(post_id):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Если кэш отключен для тестирования - пропускаем кэширование
            if skip_cache_if_disabled and is_cache_disabled():
                logger.info(f"[CACHE SKIP] {func.__name__}: кэш отключен для тестирования")
                return func(*args, **kwargs)
            
            # Генерируем уникальный ключ на основе функции и аргументов
            cache_key = _generate_cache_key(key_prefix, func.__name__, args, kwargs)
            
            # Проверяем кэш
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.info(f"[CACHE HIT] {func.__name__}: использован кэш")
                return cached_result
            
            # Кэша нет - выполняем функцию
            logger.info(f"[CACHE MISS] {func.__name__}: выполняю запрос к GigaChat")
            result = func(*args, **kwargs)
            
            # Сохраняем в кэш
            cache.set(cache_key, result, ttl)
            logger.info(f"[CACHE SAVE] {func.__name__}: результат сохранен на {ttl}s")
            
            return result
        return wrapper
    return decorator


def _generate_cache_key(prefix: str, func_name: str, args, kwargs) -> str:
    """
    Генерирует уникальный ключ кэша на основе функции и параметров
    
    Args:
        prefix: Префикс ключа
        func_name: Название функции
        args: Позиционные аргументы
        kwargs: Именованные аргументы
    
    Returns:
        Строка ключа кэша
    """
    # Сериализуем аргументы
    args_str = str(args) + str(sorted(kwargs.items()))
    
    # Создаем hash для компактности
    args_hash = hashlib.md5(args_str.encode()).hexdigest()[:12]
    
    return f"{prefix}:{func_name}:{args_hash}"


def check_and_use_cache(cache_key: str, generator_func, ttl: int = 604800, skip_if_disabled=True):
    """
    Универсальная функция кэширования
    
    Args:
        cache_key: Ключ кэша
        generator_func: Функция генерации результата (вызывается если кэша нет)
        ttl: Время жизни кэша в секундах
        skip_if_disabled: Пропускать кэш если DISABLE_CACHE_FOR_TESTING=True
    
    Returns:
        tuple: (result, from_cache: bool)
    """
    # Если кэш отключен для тестирования - пропускаем кэширование
    if skip_if_disabled and is_cache_disabled():
        logger.info(f"[CACHE SKIP] Генерирую без кэша (отключен для тестирования): {cache_key}")
        result = generator_func()
        return result, False
    
    # Проверяем кэш
    cached = cache.get(cache_key)
    if cached is not None:
        logger.info(f"[CACHE] Использован кэш: {cache_key}")
        return cached, True
    
    # Генерируем результат
    logger.info(f"[CACHE] Генерирую новый результат: {cache_key}")
    result = generator_func()
    
    # Сохраняем в кэш
    cache.set(cache_key, result, ttl)
    
    return result, False


def cache_seo_metadata(post_id: int) -> str:
    """
    Специализированный кэш для SEO метаданных
    TTL: 7 дней (метаданные редко меняются)
    
    Args:
        post_id: ID статьи
    
    Returns:
        Ключ кэша для SEO метаданных этой статьи
    """
    return f"seo_metadata:post_{post_id}"


def cache_faq_block(post_id: int) -> str:
    """
    Специализированный кэш для FAQ блоков
    TTL: 30 дней (FAQ редко меняется)
    
    Args:
        post_id: ID статьи
    
    Returns:
        Ключ кэша для FAQ этой статьи
    """
    return f"faq_block:post_{post_id}"


def cache_alt_tags(post_id: int) -> str:
    """
    Специализированный кэш для alt-тегов
    TTL: 30 дней (alt-теги не меняются)
    
    Args:
        post_id: ID статьи
    
    Returns:
        Ключ кэша для alt-тегов этой статьи
    """
    return f"alt_tags:post_{post_id}"


def invalidate_post_cache(post_id: int):
    """
    Инвалидация всех кэшей связанных со статьей
    Вызывать при обновлении статьи
    
    Args:
        post_id: ID статьи
    """
    keys_to_delete = [
        cache_seo_metadata(post_id),
        cache_faq_block(post_id),
        cache_alt_tags(post_id),
    ]
    
    for key in keys_to_delete:
        cache.delete(key)
        logger.info(f"[CACHE] Инвалидирован: {key}")


def should_generate_faq(post) -> bool:
    """
    Проверяет нужно ли генерировать FAQ для статьи
    
    Args:
        post: Объект статьи
    
    Returns:
        True если нужно генерировать, False если уже есть
    """
    # Проверяем есть ли уже FAQ блок в контенте
    if 'faq-section' in post.content.lower():
        return False
    
    if 'часто задаваемые вопросы' in post.content.lower():
        return False
    
    return True


def cached_faq_block(post_id: int, generator_func):
    """
    Кэшированная генерация FAQ блока
    
    Args:
        post_id: ID статьи
        generator_func: Функция генерации FAQ
    
    Returns:
        tuple: (result, from_cache: bool)
    """
    cache_key = f"faq_block:post_{post_id}"
    return check_and_use_cache(cache_key, generator_func, ttl=2592000)  # 30 дней


def get_cache_stats() -> Dict:
    """
    Статистика использования кэша
    
    Returns:
        Dict с метриками кэша
    """
    # Django cache не предоставляет детальной статистики
    # Возвращаем базовую информацию
    return {
        'backend': cache.__class__.__name__,
        'location': getattr(cache, '_cache', {}).get('LOCATION', 'unknown'),
        'timeout': cache.default_timeout,
    }


def clear_gigachat_cache(prefix='gigachat'):
    """
    Очищает весь кэш GigaChat по префиксу
    
    Args:
        prefix: Префикс для поиска ключей кэша (по умолчанию 'gigachat')
    
    Returns:
        int: Количество удаленных ключей
    """
    # Для DB кэша нужно использовать другой подход
    # К сожалению Django не предоставляет метод для поиска ключей по паттерну
    # Поэтому очищаем только известные ключи
    # В будущем можно добавить таблицу отслеживания ключей
    
    # Пока что возвращаем 0 - требуется ручная очистка через admin
    logger.warning(f"[CACHE CLEAR] Очистка кэша по префиксу '{prefix}' не поддерживается для DB кэша")
    logger.warning(f"[CACHE CLEAR] Используйте python manage.py clear_cache_gigachat для полной очистки")
    return 0


def clear_all_caches():
    """
    Очищает ВСЕ кэши Django
    ОСТОРОЖНО: Использовать только для тестирования!
    """
    from django.core.cache import caches
    try:
        cache.clear()
        logger.info("[CACHE CLEAR] Весь кэш очищен")
        return True
    except Exception as e:
        logger.error(f"[CACHE CLEAR] Ошибка очистки кэша: {e}")
        return False
