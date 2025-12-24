"""
Утилита для перевода названий задач Django-Q на русский язык
Используется для отображения понятных описаний в админ-панели
"""

# Словарь переводов названий задач Django-Q
TASK_TRANSLATIONS = {
    # === ЗАДАЧИ АСИСТЕНТА (Asistent/tasks.py) ===
    
    # Базовые задачи AI
    'moderate_article_task': 'Модерация статьи через AI',
    'generate_and_publish_articles': 'Генерация и публикация статей AI',
    'run_specific_schedule': 'Запуск конкретного расписания',
    'parse_news_sources': 'Парсинг новостных источников',
    'check_overdue_tasks': 'Проверка просроченных заданий',
    'cleanup_old_notifications': 'Очистка старых уведомлений',
    'moderate_task_article_task': 'Модерация задания автора',
    'improve_author_draft_task': 'Улучшение черновика автора',
    'monitor_system_health_task': 'Мониторинг здоровья системы',
    'moderate_comments_task': 'Модерация комментариев',
    'monitor_djangoq_cluster': 'Проверка кластера Django-Q',
    
    # Обработчики задач AI-агента
    'execute_generate_article': 'Генерация статьи AI-агентом',
    'execute_parse_video': 'Парсинг видео AI-агентом',
    'execute_parse_audio': 'Парсинг аудио AI-агентом',
    'execute_distribute_bonuses': 'Распределение бонусов AI-агентом',
    'execute_post_comment': 'Публикация комментария AI-агентом',
    'execute_add_like': 'Добавление лайка AI-агентом',
    'execute_optimize_schedule': 'Оптимизация расписания AI-агентом',
    'execute_manage_schedules': 'Управление расписаниями AI-агентом',
    'execute_run_schedule': 'Запуск расписания AI-агентом',
    'execute_sync_schedules': 'Синхронизация расписаний',
    'execute_add_knowledge': 'Добавление знаний в базу',
    'execute_show_knowledge': 'Показ базы знаний',
    'run_pipeline_by_slug_task': 'Запуск пайплайна по идентификатору',
    'trigger_donations_pipeline_task': 'Пайплайн донатов (отчёты и напоминания)',
    'trigger_seo_pipeline_task': 'Пайплайн SEO-переиндексации',
    'trigger_distribution_pipeline_task': 'Пайплайн дистрибуции статьи',
    
    # === ЗАДАЧИ ДОНАТОВ (donations/tasks.py) ===
    'weekly_report_task': 'Генерация еженедельного отчета',
    'daily_stats_update': 'Ежедневное обновление статистики',
    'monthly_stats_update': 'Ежемесячное обновление статистики',
    'send_weekly_report_notification': 'Отправка уведомления о отчете',
    'send_payment_reminder': 'Напоминание о платежах',
    'cleanup_old_stats': 'Очистка старой статистики',
    
    # === ЗАДАЧИ БЛОГА (blog/tasks.py) ===
    'auto_publish_scheduled_posts': 'Автопубликация отложенных постов',
    'cleanup_old_drafts': 'Очистка старых черновиков',
    'update_post_statistics': 'Обновление статистики постов',
    'generate_sitemap': 'Генерация карты сайта',
    
    # === СПЕЦИАЛЬНЫЕ ФУНКЦИИ ===
    'Asistent.tasks.moderate_article_task': 'Модерация статьи через AI',
    'Asistent.tasks.generate_and_publish_articles': 'Генерация и публикация статей AI',
    'Asistent.tasks.run_specific_schedule': 'Запуск конкретного расписания',
    'Asistent.tasks.parse_news_sources': 'Парсинг новостных источников',
    'Asistent.tasks.check_overdue_tasks': 'Проверка просроченных заданий',
    'Asistent.tasks.cleanup_old_notifications': 'Очистка старых уведомлений',
    'Asistent.tasks.moderate_task_article_task': 'Модерация задания автора',
    'Asistent.tasks.improve_author_draft_task': 'Улучшение черновика автора',
    'Asistent.tasks.monitor_system_health_task': 'Мониторинг здоровья системы',
    'Asistent.tasks.moderate_comments_task': 'Модерация комментариев',
    'Asistent.tasks.monitor_djangoq_cluster': 'Проверка кластера Django-Q',
    'Asistent.tasks.execute_generate_article': 'Генерация статьи AI-агентом',
    'Asistent.tasks.execute_parse_video': 'Парсинг видео AI-агентом',
    'Asistent.tasks.execute_parse_audio': 'Парсинг аудио AI-агентом',
    'Asistent.tasks.execute_distribute_bonuses': 'Распределение бонусов AI-агентом',
    'Asistent.tasks.execute_post_comment': 'Публикация комментария AI-агентом',
    'Asistent.tasks.execute_add_like': 'Добавление лайка AI-агентом',
    'Asistent.tasks.execute_optimize_schedule': 'Оптимизация расписания AI-агентом',
    'Asistent.tasks.execute_manage_schedules': 'Управление расписаниями AI-агентом',
    'Asistent.tasks.execute_run_schedule': 'Запуск расписания AI-агентом',
    'Asistent.tasks.execute_sync_schedules': 'Синхронизация расписаний',
    'Asistent.tasks.execute_add_knowledge': 'Добавление знаний в базу',
    'Asistent.tasks.execute_show_knowledge': 'Показ базы знаний',
    
    'donations.tasks.weekly_report_task': 'Генерация еженедельного отчета',
    'donations.tasks.daily_stats_update': 'Ежедневное обновление статистики',
    'donations.tasks.monthly_stats_update': 'Ежемесячное обновление статистики',
    'donations.tasks.send_weekly_report_notification': 'Отправка уведомления о отчете',
    'donations.tasks.send_payment_reminder': 'Напоминание о платежах',
    'donations.tasks.cleanup_old_stats': 'Очистка старой статистики',
}


def get_task_description(task_name):
    """
    Получить русское описание задачи по её имени
    
    Args:
        task_name (str): Имя функции задачи или полный путь (например, 'moderate_article_task' или 'Asistent.tasks.moderate_article_task')
        
    Returns:
        str: Русское описание задачи или оригинальное имя, если перевод не найден
    
    Examples:
        >>> get_task_description('moderate_article_task')
        'Модерация статьи через AI'
        
        >>> get_task_description('Asistent.tasks.moderate_article_task')
        'Модерация статьи через AI'
        
        >>> get_task_description('unknown_task')
        'unknown_task'
    """
    if not task_name:
        return ''
    
    # Проверяем прямое совпадение
    if task_name in TASK_TRANSLATIONS:
        return TASK_TRANSLATIONS[task_name]
    
    # Если это полный путь, пробуем извлечь только имя функции
    if '.' in task_name:
        function_name = task_name.split('.')[-1]
        if function_name in TASK_TRANSLATIONS:
            return TASK_TRANSLATIONS[function_name]
    
    # Если это просто имя функции, пробуем найти с префиксами
    for key in TASK_TRANSLATIONS:
        if key.endswith('.' + task_name):
            return TASK_TRANSLATIONS[key]
    
    # Если перевод не найден, возвращаем оригинальное имя
    return task_name


def format_task_with_description(task_name):
    """
    Форматирует имя задачи с русским описанием
    
    Args:
        task_name (str): Имя функции задачи
        
    Returns:
        str: Отформатированная строка вида "function_name() - Русское описание"
    
    Examples:
        >>> format_task_with_description('moderate_article_task')
        'moderate_article_task() - Модерация статьи через AI'
    """
    if not task_name:
        return ''
    
    # Извлекаем имя функции из полного пути
    function_name = task_name.split('.')[-1] if '.' in task_name else task_name
    
    # Получаем описание
    description = get_task_description(task_name)
    
    # Если описание отличается от имени (т.е. найден перевод)
    if description != task_name and description != function_name:
        return f"{function_name}() - {description}"
    else:
        return f"{function_name}()"


def get_all_tasks_translations():
    """
    Получить весь словарь переводов
    
    Returns:
        dict: Словарь с переводами всех задач
    """
    return TASK_TRANSLATIONS.copy()


def add_custom_translation(task_name, description):
    """
    Добавить кастомный перевод для задачи
    
    Args:
        task_name (str): Имя функции задачи
        description (str): Русское описание
    """
    TASK_TRANSLATIONS[task_name] = description

