"""
Быстрый анализ логов - удобная функция для диагностики проблем.

Использование:
    from system_logs.quick_analysis import quick_check
    
    # Быстрая проверка последних ошибок
    quick_check()
    
    # Детальный анализ за последние 24 часа
    quick_check(hours=24, detailed=True)
"""
from datetime import timedelta
from django.utils import timezone
from .read_logs import get_recent_logs, get_errors, get_warnings
from .analyze_logs import analyze_errors, get_error_statistics, find_common_errors
from Asistent.models import SystemLog


def quick_check(hours=1, detailed=False):
    """
    Быстрая проверка состояния системы по логам.
    
    Args:
        hours: За какой период проверять (по умолчанию 1 час)
        detailed: Показывать детальную информацию
    """
    print("=" * 70)
    print(f"БЫСТРАЯ ПРОВЕРКА ЛОГОВ (последние {hours} ч.)")
    print("=" * 70)
    
    # Общая статистика
    stats = get_error_statistics(hours=hours)
    print(f"\n[STATS] ОБЩАЯ СТАТИСТИКА:")
    print(f"   Всего логов: {stats['total_logs']}")
    print(f"   Ошибок: {stats['errors']}")
    print(f"   Предупреждений: {stats['warnings']}")
    print(f"   Процент ошибок: {stats['error_rate_percent']}%")
    
    # Последние ошибки
    errors = get_errors(limit=10, hours=hours)
    if errors:
        print(f"\n[ERROR] ПОСЛЕДНИЕ ОШИБКИ ({len(errors)}):")
        print("-" * 70)
        for i, log in enumerate(errors[:10], 1):
            timestamp = log.timestamp.strftime("%H:%M:%S")
            module = log.module or "N/A"
            message_short = log.message[:60] + "..." if len(log.message) > 60 else log.message
            print(f"   {i:2}. [{log.level:8}] {timestamp} | {module:25} | {message_short}")
    else:
        print("\n[OK] Ошибок не найдено!")
    
    # Последние предупреждения (если нужно)
    if detailed:
        warnings = get_warnings(limit=5, hours=hours)
        if warnings:
            print(f"\n[WARN] ПОСЛЕДНИЕ ПРЕДУПРЕЖДЕНИЯ ({len(warnings)}):")
            print("-" * 70)
            for i, log in enumerate(warnings[:5], 1):
                timestamp = log.timestamp.strftime("%H:%M:%S")
                message_short = log.message[:60] + "..." if len(log.message) > 60 else log.message
                print(f"   {i}. {timestamp} | {log.logger_name:15} | {message_short}")
    
    # Частые ошибки
    if detailed and errors:
        print(f"\n[ANALYSIS] АНАЛИЗ ЧАСТЫХ ОШИБОК:")
        print("-" * 70)
        common = find_common_errors(hours=hours, min_occurrences=2)
        if common:
            for i, error in enumerate(common[:5], 1):
                print(f"   {i}. Повторений: {error['count']}")
                print(f"      Модуль: {error['module'] or 'N/A'}")
                print(f"      Сообщение: {error['message'][:80]}...")
                print()
        else:
            print("   Частых повторяющихся ошибок не найдено")
    
    # Анализ по модулям
    if detailed:
        from .analyze_logs import get_module_statistics
        print(f"\n[MODULES] ТОП МОДУЛЕЙ ПО ЛОГАМ:")
        print("-" * 70)
        modules = get_module_statistics(hours=hours, top_n=5)
        for i, mod in enumerate(modules, 1):
            print(f"   {i}. {mod['module']:30} | Всего: {mod['total']:4} | Ошибок: {mod['errors']:3}")
    
    print("\n" + "=" * 70)
    
    # Возвращаем результат для программного использования
    return {
        'stats': stats,
        'errors': errors,
        'has_errors': len(errors) > 0,
    }


def check_gigachat_errors(hours=24):
    """
    Специальная проверка ошибок GigaChat.
    
    Args:
        hours: За какой период проверять
    """
    from .filter_logs import filter_by_text, combine_filters
    
    print("=" * 70)
    print("ПРОВЕРКА ОШИБОК GIGACHAT")
    print("=" * 70)
    
    # Ищем логи связанные с GigaChat
    gigachat_logs = combine_filters(
        search_text='gigachat',
        hours=hours,
        limit=50
    )
    
    errors = [log for log in gigachat_logs if log.level in ['ERROR', 'CRITICAL']]
    
    if errors:
        print(f"\n[ERROR] Найдено ошибок GigaChat: {len(errors)}")
        print("-" * 70)
        for i, log in enumerate(errors[:10], 1):
            timestamp = log.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            print(f"   {i:2}. [{log.level}] {timestamp}")
            print(f"       {log.message[:100]}...")
            print()
    else:
        print("\n[OK] Ошибок GigaChat не найдено")
    
    print("=" * 70)
    
    return errors

