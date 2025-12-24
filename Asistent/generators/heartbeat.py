"""
Heartbeat механизм для отслеживания активных задач.
Перенесено из Asistent/tasks.py (функция _update_lock_heartbeat)
"""

import time
import logging
from typing import Optional
from django.core.cache import cache

logger = logging.getLogger(__name__)


class HeartbeatManager:
    """
    Менеджер heartbeat для отслеживания долгоживущих задач.
    
    Основано на логике из tasks.py:
    - Обновление heartbeat каждые 30 секунд
    - TTL 5 минут для автоматической очистки
    - Интеграция с системой очередей
    """
    
    def __init__(self, task_id: int, update_interval: int = 30):
        """
        Args:
            task_id: ID задачи (schedule_id или уникальный идентификатор)
            update_interval: Интервал обновления в секундах (по умолчанию 30)
        """
        self.task_id = task_id
        self.update_interval = update_interval
        self.heartbeat_key = f"task_heartbeat:{task_id}"
        self.last_update = 0
    
    def start(self):
        """Начало отслеживания задачи"""
        self.update(force=True)
        logger.debug(f"   💓 Heartbeat запущен для задачи {self.task_id}")
    
    def update(self, force: bool = False):
        """
        Обновление heartbeat.
        
        Args:
            force: Принудительное обновление (игнорируя интервал)
        """
        current_time = time.time()
        
        if force or current_time - self.last_update >= self.update_interval:
            cache.set(self.heartbeat_key, current_time, timeout=300)  # 5 минут TTL
            self.last_update = current_time
            logger.debug(f"   💓 Heartbeat обновлён для задачи {self.task_id}")
    
    def stop(self):
        """Остановка отслеживания и очистка"""
        cache.delete(self.heartbeat_key)
        logger.debug(f"   💓 Heartbeat остановлен для задачи {self.task_id}")
    
    def is_alive(self) -> bool:
        """
        Проверка активности задачи.
        
        Returns:
            True если heartbeat активен, False если задача зависла
        """
        last_beat = cache.get(self.heartbeat_key)
        if last_beat is None:
            return False
        
        # Если последнее обновление было более 3 минут назад - задача зависла
        return time.time() - last_beat < 180
    
    def get_last_update(self) -> Optional[float]:
        """
        Получение времени последнего обновления.
        
        Returns:
            Unix timestamp последнего обновления или None
        """
        return cache.get(self.heartbeat_key)
    
    def cleanup(self):
        """Очистка heartbeat (алиас для stop)"""
        self.stop()


