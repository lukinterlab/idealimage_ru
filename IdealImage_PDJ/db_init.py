"""
Инициализация SQLite для shared hosting.

Автоматически настраивает SQLite при каждом подключении:
- Отключает WAL-режим (не работает на NFS)
- Устанавливает DELETE журналирование
- Оптимизирует производительность
"""

from django.db.backends.signals import connection_created
from django.dispatch import receiver


@receiver(connection_created)
def setup_sqlite(sender, connection, **kwargs):
    """
    Настройка SQLite при каждом новом подключении.
    
    ВАЖНО: Работает ТОЛЬКО для SQLite (не для MySQL/PostgreSQL)!
    Для shared hosting где WAL-режим не поддерживается.
    """
    # КРИТИЧНО: Применять ТОЛЬКО к SQLite!
    if connection.vendor == 'sqlite':
        try:
            cursor = connection.cursor()
            
            # DELETE режим вместо WAL (для NFS на shared hosting)
            cursor.execute('PRAGMA journal_mode=DELETE;')
            
            # Полная синхронизация для надёжности
            cursor.execute('PRAGMA synchronous=FULL;')
            
            # Временные данные в памяти
            cursor.execute('PRAGMA temp_store=MEMORY;')
            
            # Кэш (5000 страниц ≈ 20 MB)
            cursor.execute('PRAGMA cache_size=5000;')
            
            # Таймаут при блокировке
            cursor.execute('PRAGMA busy_timeout=30000;')
            
            cursor.close()
        except Exception as e:
            # Игнорировать ошибки (не критично)
            pass
    # Для MySQL/PostgreSQL ничего не делаем - они настроены правильно из коробки!

