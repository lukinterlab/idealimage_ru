"""Конфигурация приложения парсеров."""
from django.apps import AppConfig


class ParsersConfig(AppConfig):
    """Конфигурация для приложения парсеров."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Asistent.parsers'
    label = 'Parsers'
    verbose_name = '📰 ПАРСИНГ СТАТЕЙ'
    
    def ready(self):
        """Регистрация админок при старте приложения."""
        from . import admin  # noqa

