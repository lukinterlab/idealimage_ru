"""
Кэширование векторов базы знаний в памяти для быстрого поиска
Поддерживает in-memory кэш (single process) и Django cache (multi-process)
"""
import numpy as np
import logging
from typing import List, Tuple, Optional
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)

# Глобальный кэш векторов в памяти процесса (для single-process)
_KNOWLEDGE_VECTORS_CACHE = None
_CACHE_VERSION = 0

# Ключ для Django cache (для multi-process)
DJANGO_CACHE_KEY = "ai_knowledge_vectors_v1"
DJANGO_CACHE_TIMEOUT = 60 * 15  # 15 минут

# Режим кэширования: 'memory' или 'django'
USE_DJANGO_CACHE = getattr(settings, 'AI_USE_DJANGO_CACHE', False)


def load_knowledge_vectors(force_reload=False, use_django_cache=None):
    """
    Загружает все векторы из БД в память для быстрого поиска
    
    Args:
        force_reload: Принудительная перезагрузка из БД
        use_django_cache: True - Django cache (multi-process), False - in-memory
                         None - автоопределение из settings
        
    Returns:
        List[dict]: Список словарей с id, embedding, data
    """
    global _KNOWLEDGE_VECTORS_CACHE, _CACHE_VERSION
    
    # Определяем режим кэширования
    if use_django_cache is None:
        use_django_cache = USE_DJANGO_CACHE
    
    # Режим 1: Django cache (для multi-process: gunicorn, uwsgi)
    if use_django_cache:
        return _load_from_django_cache(force_reload)
    
    # Режим 2: In-memory cache (для single-process: runserver)
    return _load_from_memory_cache(force_reload)


def _load_from_memory_cache(force_reload=False):
    """Загрузка из in-memory кэша (single-process)"""
    global _KNOWLEDGE_VECTORS_CACHE, _CACHE_VERSION
    
    # Проверяем нужна ли перезагрузка
    if not force_reload and _KNOWLEDGE_VECTORS_CACHE is not None:
        logger.info(f"📦 In-memory кэш: {len(_KNOWLEDGE_VECTORS_CACHE)} записей")
        return _KNOWLEDGE_VECTORS_CACHE
    
    vectors = _fetch_vectors_from_db()
    
    if vectors:
        _KNOWLEDGE_VECTORS_CACHE = vectors
        _CACHE_VERSION += 1
        logger.info(f"✅ In-memory кэш обновлён: {len(vectors)} векторов (v{_CACHE_VERSION})")
    
    return vectors


def _load_from_django_cache(force_reload=False):
    """Загрузка из Django cache (multi-process)"""
    
    # Проверяем кэш
    if not force_reload:
        cached = cache.get(DJANGO_CACHE_KEY)
        if cached:
            logger.info(f"📦 Django cache: {len(cached)} записей")
            return cached
    
    vectors = _fetch_vectors_from_db()
    
    if vectors:
        # Сохраняем в Django cache
        cache.set(DJANGO_CACHE_KEY, vectors, DJANGO_CACHE_TIMEOUT)
        logger.info(f"✅ Django cache обновлён: {len(vectors)} векторов (TTL {DJANGO_CACHE_TIMEOUT}s)")
    
    return vectors


def _fetch_vectors_from_db():
    """Общая функция загрузки векторов из БД"""
    try:
        from .models import AIKnowledgeBase
        
        logger.info("🔄 Загрузка векторов из БД...")
        
        items = AIKnowledgeBase.objects.filter(
            is_active=True,
            embedding__isnull=False
        ).exclude(embedding=[])
        
        vectors = []
        for item in items:
            try:
                # Преобразуем в numpy array
                embedding_array = np.array(item.embedding)
                
                if len(embedding_array) == 0:
                    continue
                
                vectors.append({
                    'id': item.id,
                    'embedding': embedding_array,
                    'item': item,
                    'title': item.title,
                    'category': item.category,
                    'priority': item.priority
                })
            except Exception as e:
                logger.warning(f"Ошибка загрузки вектора для {item.id}: {e}")
                continue
        
        logger.info(f"📊 Загружено {len(vectors)} векторов из БД")
        return vectors
        
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки векторов: {e}")
        return []


def find_similar_cached(query_embedding: np.ndarray, top_k: int = 5, 
                       category: Optional[str] = None, min_similarity: float = 0.0):
    """
    Быстрый поиск похожих записей по кэшированным векторам
    
    Args:
        query_embedding: Вектор запроса (numpy array)
        top_k: Количество результатов
        category: Фильтр по категории
        min_similarity: Минимальный порог сходства
        
    Returns:
        List[Tuple[AIKnowledgeBase, float]]: Список (запись, схожесть)
    """
    # Загружаем кэш если ещё не загружен
    vectors_cache = load_knowledge_vectors()
    
    if not vectors_cache:
        logger.warning("Кэш векторов пуст")
        return []
    
    similarities = []
    
    try:
        # Нормализуем запросный вектор один раз
        query_norm = np.linalg.norm(query_embedding)
        if query_norm == 0:
            return []
        
        query_normalized = query_embedding / query_norm
        
        for vec_data in vectors_cache:
            # Фильтр по категории
            if category and vec_data['category'] != category:
                continue
            
            try:
                item_embedding = vec_data['embedding']
                
                # Проверяем размерность
                if item_embedding.shape != query_embedding.shape:
                    continue
                
                # Нормализуем вектор записи
                item_norm = np.linalg.norm(item_embedding)
                if item_norm == 0:
                    continue
                
                item_normalized = item_embedding / item_norm
                
                # Косинусная близость = скалярное произведение нормализованных векторов
                similarity = float(np.dot(query_normalized, item_normalized))
                
                # Фильтруем по порогу
                if similarity >= min_similarity:
                    similarities.append((vec_data['item'], similarity))
                    
            except Exception as e:
                logger.warning(f"Ошибка расчёта similarity для {vec_data['id']}: {e}")
                continue
        
        # Сортируем по убыванию
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        logger.info(f"🎯 Найдено {len(similarities[:top_k])} похожих записей (кэшированный поиск)")
        return similarities[:top_k]
        
    except Exception as e:
        logger.error(f"❌ Ошибка кэшированного поиска: {e}")
        return []


def clear_knowledge_cache():
    """
    Очищает кэш векторов (при обновлении базы знаний)
    Очищает и in-memory, и Django cache
    """
    global _KNOWLEDGE_VECTORS_CACHE, _CACHE_VERSION
    
    count = 0
    
    # Очищаем in-memory кэш
    if _KNOWLEDGE_VECTORS_CACHE is not None:
        count = len(_KNOWLEDGE_VECTORS_CACHE)
        _KNOWLEDGE_VECTORS_CACHE = None
        _CACHE_VERSION += 1
        logger.info(f"🗑️ In-memory кэш очищен ({count} записей, v{_CACHE_VERSION})")
    
    # Очищаем Django cache
    try:
        cache.delete(DJANGO_CACHE_KEY)
        logger.info(f"🗑️ Django cache очищен (ключ: {DJANGO_CACHE_KEY})")
    except Exception as e:
        logger.warning(f"Ошибка очистки Django cache: {e}")


def get_cache_stats():
    """
    Возвращает статистику кэша
    
    Returns:
        dict: Статистика кэша
    """
    global _KNOWLEDGE_VECTORS_CACHE, _CACHE_VERSION
    
    if _KNOWLEDGE_VECTORS_CACHE is None:
        return {
            'loaded': False,
            'count': 0,
            'version': _CACHE_VERSION,
            'memory_mb': 0
        }
    
    # Приблизительный расчёт памяти
    memory_bytes = sum(
        vec['embedding'].nbytes 
        for vec in _KNOWLEDGE_VECTORS_CACHE
    )
    
    return {
        'loaded': True,
        'count': len(_KNOWLEDGE_VECTORS_CACHE),
        'version': _CACHE_VERSION,
        'memory_mb': round(memory_bytes / (1024 * 1024), 2)
    }


def warmup_cache():
    """
    Прогрев кэша при старте приложения
    Можно вызвать в apps.py -> ready()
    """
    logger.info("🔥 Прогрев кэша векторов...")
    load_knowledge_vectors(force_reload=True)
    
    stats = get_cache_stats()
    if stats['loaded']:
        logger.info(
            f"✅ Кэш прогрет: {stats['count']} векторов, "
            f"{stats['memory_mb']} MB, версия {stats['version']}"
        )
    else:
        logger.warning("⚠️ Не удалось прогреть кэш")

