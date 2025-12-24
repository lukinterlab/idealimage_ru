"""Конфигурация приложения модерации."""
from django.apps import AppConfig


class ModerationConfig(AppConfig):
    """Конфигурация для отдельной группы Moderation в Django Admin."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Asistent.moderations'
    label = 'Moderation'
    verbose_name = '🛡️ МОДЕРАЦИЯ'
    
    def ready(self):
        """Регистрация админок и сигналов при старте приложения."""
        # Импортируем админки чтобы они зарегистрировались
        from . import admin  # noqa
        # Импортируем сигналы для автоматической модерации
        from . import signals  # noqa

