"""
Кастомные handlers для логирования
"""
import logging
from collections import deque
import os
from django.utils import timezone
from django.db import transaction


class LastLinesFileHandler(logging.Handler):
    """
    Handler который хранит только последние N строк в файле.
    При достижении лимита - старые строки удаляются, остаются только новые.
    """
    
    def __init__(self, filename, maxlines=1000, encoding='utf-8', write_every=10):
        super().__init__()
        self.filename = filename
        self.maxlines = maxlines
        self.encoding = encoding
        self.buffer = deque(maxlen=maxlines)
        self._counter = 0
        self._write_every = max(1, write_every)  # Записывать в файл каждые N строк
        
        # Создаем директорию если не существует
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Загружаем существующие логи при запуске (последние N строк)
        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding=encoding, errors='ignore') as f:
                    lines = f.readlines()
                    # Берем только последние maxlines строк
                    for line in lines[-maxlines:]:
                        self.buffer.append(line.rstrip('\n'))
            except Exception:
                pass  # Если не удалось прочитать - начинаем с пустого буфера
    
    def emit(self, record):
        try:
            msg = self.format(record)
            self.buffer.append(msg)
            
            # Записываем в файл не каждый раз, а пачками для оптимизации
            self._counter += 1
            if self._counter >= self._write_every:
                self._write_to_file()
                self._counter = 0
                
        except Exception:
            self.handleError(record)
    
    def _write_to_file(self):
        """Перезаписывает файл содержимым буфера"""
        try:
            with open(self.filename, 'w', encoding=self.encoding) as f:
                for line in self.buffer:
                    f.write(line + '\n')
        except Exception:
            pass  # Игнорируем ошибки записи
    
    def close(self):
        """При закрытии - сохраняем все что в буфере"""
        self._write_to_file()
        super().close()


class DatabaseLogHandler(logging.Handler):
    """
    Handler для сохранения логов в базу данных через модель SystemLog.
    Использует батчинг для оптимизации производительности.
    """
    
    def __init__(self, batch_size=50, flush_interval=5):
        """
        Args:
            batch_size: Количество логов для сохранения за раз
            flush_interval: Интервал в секундах для принудительной записи
        """
        super().__init__()
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.buffer = []
        self._last_flush = timezone.now()
        self._lock = False  # Простая защита от параллельных записей
    
    def emit(self, record):
        """Сохраняет лог в буфер, при достижении batch_size - записывает в БД"""
        try:
            # Извлекаем информацию из record
            log_data = {
                'timestamp': timezone.now(),
                'level': record.levelname,
                'logger_name': record.name,
                'message': self.format(record),
                'module': record.module if hasattr(record, 'module') else '',
                'function': record.funcName if hasattr(record, 'funcName') else '',
                'line': record.lineno if hasattr(record, 'lineno') else None,
                'process_id': record.process if hasattr(record, 'process') else None,
                'thread_id': record.thread if hasattr(record, 'thread') else None,
                'extra_data': getattr(record, 'extra_data', {})
            }
            
            self.buffer.append(log_data)
            
            # Проверяем нужно ли записать в БД
            should_flush = (
                len(self.buffer) >= self.batch_size or
                (timezone.now() - self._last_flush).total_seconds() >= self.flush_interval
            )
            
            if should_flush:
                self._flush_to_db()
                
        except Exception:
            # Игнорируем ошибки логирования, чтобы не создавать бесконечный цикл
            self.handleError(record)
    
    def _flush_to_db(self):
        """Записывает накопленные логи в базу данных"""
        if self._lock or not self.buffer:
            return
        
        self._lock = True
        try:
            # Импортируем модель только здесь, чтобы избежать circular imports
            from Asistent.models import SystemLog
            
            # Создаём объекты для массовой вставки
            logs_to_create = [
                SystemLog(**log_data)
                for log_data in self.buffer
            ]
            
            # Массовая вставка через bulk_create
            if logs_to_create:
                SystemLog.objects.bulk_create(logs_to_create, ignore_conflicts=True)
            
            # Очищаем буфер
            self.buffer = []
            self._last_flush = timezone.now()
            
        except Exception as e:
            # Если не удалось записать - просто очищаем буфер
            # чтобы не накапливать логи в памяти
            self.buffer = []
        finally:
            self._lock = False
    
    def close(self):
        """При закрытии - записываем все накопленные логи"""
        self._flush_to_db()
        super().close()

