"""
Система очередей для управления параллельными генерациями.
Перенесено из Asistent/tasks.py (функции _add_to_horoscope_queue, _wait_for_queue_turn и т.д.)
"""

import time
import logging
from datetime import date
from typing import Optional
from django.core.cache import cache

logger = logging.getLogger(__name__)


class QueueManager:
    """
    Менеджер очередей для предотвращения конфликтов параллельных запусков.
    
    Основано на логике из tasks.py:
    - horoscope_queue с кешем
    - Блокировки с TTL
    - Heartbeat для отслеживания зависших задач
    """
    
    def __init__(self, queue_name: str = 'content_generation'):
        """
        Args:
            queue_name: Имя очереди (для разных типов контента)
        """
        self.queue_name = queue_name
        self.queue_key = self._get_queue_key()
        self.lock_key = self._get_lock_key()
    
    def add_to_queue(self, task_id: int) -> int:
        """
        Добавление задачи в очередь.
        
        Args:
            task_id: ID задачи (schedule_id или уникальный идентификатор)
        
        Returns:
            Позиция в очереди (1-based)
        """
        queue = cache.get(self.queue_key, [])
        
        if task_id not in queue:
            queue.append(task_id)
            cache.set(self.queue_key, queue, timeout=60 * 60 * 24)  # 24 часа
        
        position = queue.index(task_id) + 1
        logger.info(f"   📋 Задача {task_id} добавлена в очередь '{self.queue_name}', позиция: {position}")
        return position
    
    def wait_for_turn(self, task_id: int, max_wait: int = 3600) -> bool:
        """
        Ожидание своей очереди.
        
        Args:
            task_id: ID задачи
            max_wait: Максимальное время ожидания в секундах
        
        Returns:
            True если очередь пришла, False если таймаут
        """
        start_time = time.time()
        last_stale_check = start_time
        
        logger.info(f"   ⏳ Задача {task_id} ожидает очереди (макс. {max_wait} сек)")
        
        while time.time() - start_time < max_wait:
            queue = cache.get(self.queue_key, [])
            
            # Если очередь пуста или мы первые
            if not queue or (queue and queue[0] == task_id):
                # Пытаемся получить блокировку
                if cache.add(self.lock_key, task_id, timeout=1800):  # 30 минут
                    # Устанавливаем heartbeat
                    heartbeat_key = f"{self.lock_key}:heartbeat"
                    cache.set(heartbeat_key, time.time(), timeout=300)  # 5 минут
                    
                    logger.info(f"   ✅ Задача {task_id} получила блокировку очереди '{self.queue_name}'")
                    return True
            
            # Проверка зависших блокировок каждые 30 секунд
            if time.time() - last_stale_check > 30:
                self._check_and_release_stale_lock()
                last_stale_check = time.time()
            
            # Ждём 5 секунд перед следующей проверкой
            time.sleep(5)
        
        logger.error(f"   ❌ Таймаут ожидания очереди для задачи {task_id}")
        return False
    
    def remove_from_queue(self, task_id: int):
        """
        Удаление задачи из очереди и освобождение блокировки.
        
        Args:
            task_id: ID задачи
        """
        # Удаляем из очереди
        queue = cache.get(self.queue_key, [])
        if task_id in queue:
            queue.remove(task_id)
            cache.set(self.queue_key, queue, timeout=60 * 60 * 24)
        
        # Освобождаем блокировку
        lock_holder = cache.get(self.lock_key)
        if lock_holder == task_id:
            cache.delete(self.lock_key)
            cache.delete(f"{self.lock_key}:heartbeat")
            logger.info(f"   🔓 Задача {task_id} освободила блокировку очереди '{self.queue_name}'")
    
    def update_heartbeat(self, task_id: int):
        """
        Обновление heartbeat для активной задачи.
        
        Args:
            task_id: ID задачи
        """
        lock_holder = cache.get(self.lock_key)
        if lock_holder == task_id:
            heartbeat_key = f"{self.lock_key}:heartbeat"
            cache.set(heartbeat_key, time.time(), timeout=300)  # 5 минут
    
    def _check_and_release_stale_lock(self):
        """Проверка и освобождение зависших блокировок"""
        heartbeat_key = f"{self.lock_key}:heartbeat"
        last_heartbeat = cache.get(heartbeat_key)
        
        if last_heartbeat is None:
            # Нет heartbeat - возможно зависла
            lock_holder = cache.get(self.lock_key)
            if lock_holder is not None:
                # Проверяем как долго держится блокировка
                # Если heartbeat отсутствует, считаем что задача зависла
                logger.warning(f"   ⚠️ Обнаружена блокировка без heartbeat (holder: {lock_holder}), освобождаю")
                cache.delete(self.lock_key)
                cache.delete(heartbeat_key)
        else:
            # Проверяем свежесть heartbeat
            if time.time() - last_heartbeat > 180:  # 3 минуты без обновления
                lock_holder = cache.get(self.lock_key)
                logger.warning(f"   ⚠️ Обнаружена устаревшая блокировка (holder: {lock_holder}), освобождаю")
                cache.delete(self.lock_key)
                cache.delete(heartbeat_key)
    
    def _get_queue_key(self) -> str:
        """Получение ключа очереди"""
        date_str = date.today().isoformat()
        return f"queue:{self.queue_name}:{date_str}"
    
    def _get_lock_key(self) -> str:
        """Получение ключа блокировки"""
        date_str = date.today().isoformat()
        return f"queue_lock:{self.queue_name}:{date_str}"
    
    def get_queue_status(self) -> dict:
        """
        Получение статуса очереди.
        
        Returns:
            Словарь с информацией об очереди
        """
        queue = cache.get(self.queue_key, [])
        lock_holder = cache.get(self.lock_key)
        heartbeat_key = f"{self.lock_key}:heartbeat"
        last_heartbeat = cache.get(heartbeat_key)
        
        return {
            'queue_name': self.queue_name,
            'queue_length': len(queue),
            'tasks_in_queue': queue,
            'lock_holder': lock_holder,
            'last_heartbeat': last_heartbeat,
            'has_active_task': lock_holder is not None,
        }


