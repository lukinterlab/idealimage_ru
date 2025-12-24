"""
Конфигурация Django-приложения Schedule.
Автономная система управления расписаниями и задачами.
"""
from django.apps import AppConfig


class ScheduleConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Asistent.schedule'
    verbose_name = '📅 Система расписаний и задач'
    
    def ready(self):
        """
        Инициализация приложения.
        Подключает signals для синхронизации с Django-Q.
        """
        # Импортируем сигналы для автоматической регистрации
        # Импорт внутри ready() безопасен, так как Django уже загружен
        try:
            from . import signals
        except ImportError:
            pass

