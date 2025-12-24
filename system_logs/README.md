# Утилиты для работы с системными логами

Все логи системы хранятся в базе данных в модели `SystemLog` (`asistent_systemlog`).

## Быстрый старт

```python
from system_logs import get_recent_logs, get_errors, analyze_errors

# Получить последние 100 логов
logs = get_recent_logs(limit=100)

# Получить только ошибки за последние 24 часа
errors = get_errors(limit=50)

# Анализ ошибок
analysis = analyze_errors(hours=24)
print(f"Всего ошибок: {analysis['total_errors']}")
print(f"По модулям: {analysis['by_module']}")
```

## Основные функции

### Чтение логов (`read_logs.py`)

- `get_recent_logs(limit=100, hours=None)` - последние логи
- `get_errors(limit=50, hours=24)` - только ошибки (ERROR, CRITICAL)
- `get_warnings(limit=50, hours=24)` - только предупреждения
- `get_logs_by_module(module_name, limit=100, hours=24)` - по модулю
- `get_logs_by_logger(logger_name, limit=100, hours=24)` - по логгеру
- `get_logs_by_level(level, limit=100, hours=24)` - по уровню
- `get_logs_by_time_range(start_time, end_time, limit=1000)` - по периоду

### Анализ логов (`analyze_logs.py`)

- `analyze_errors(hours=24, limit=100)` - полный анализ ошибок
- `get_error_statistics(hours=24)` - статистика по ошибкам
- `get_module_statistics(hours=24, top_n=10)` - статистика по модулям
- `get_level_statistics(hours=24)` - статистика по уровням
- `find_common_errors(hours=24, min_occurrences=2)` - частые ошибки

### Фильтрация логов (`filter_logs.py`)

- `filter_by_level(level, hours=24, limit=100)` - по уровню
- `filter_by_time(start_time, end_time=None, limit=1000)` - по времени
- `filter_by_text(search_text, hours=24, limit=100)` - по тексту
- `filter_by_module(module_name, hours=24, limit=100)` - по модулю
- `filter_by_logger(logger_name, hours=24, limit=100)` - по логгеру
- `combine_filters(...)` - комбинировать несколько фильтров

## Примеры использования

### Поиск ошибок в конкретном модуле

```python
from system_logs import get_logs_by_module, get_errors

# Ошибки в модуле Asistent.views
errors = get_logs_by_module('Asistent.views', limit=50)
for error in errors:
    if error.level in ['ERROR', 'CRITICAL']:
        print(f"{error.timestamp}: {error.message}")
```

### Анализ частых ошибок

```python
from system_logs import find_common_errors

common = find_common_errors(hours=24, min_occurrences=3)
for error in common:
    print(f"Ошибка: {error['message'][:100]}")
    print(f"Повторений: {error['count']}")
    print(f"Модуль: {error['module']}")
```

### Поиск по тексту

```python
from system_logs import filter_by_text

# Найти все логи с упоминанием "GigaChat"
gigachat_logs = filter_by_text('GigaChat', hours=12, limit=100)
```

### Комбинированный поиск

```python
from system_logs import combine_filters

# Ошибки в Asistent за последний час
logs = combine_filters(
    level='ERROR',
    module='Asistent',
    hours=1,
    limit=50
)
```

## Структура SystemLog

- `timestamp` - время события
- `level` - уровень (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `logger_name` - имя логгера (django, Asistent, django-q)
- `message` - текст сообщения
- `module` - имя модуля
- `function` - имя функции
- `line` - номер строки
- `process_id` - ID процесса
- `thread_id` - ID потока
- `extra_data` - дополнительные данные (JSON)

## Автоочистка

Логи автоматически удаляются через 24 часа задачей `clean_old_system_logs()`.

## Важно!

- **ВСЕГДА** используйте функции из `system_logs` вместо создания временных скриптов
- **НЕ ЧИТАЙТЕ** файлы логов напрямую - они могут быть неактуальными
- Логи хранятся **ТОЛЬКО** в базе данных в модели `SystemLog`

