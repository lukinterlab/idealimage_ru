"""
Конфигурация приложения утилит
"""
from django.apps import AppConfig


class UtilitsConfig(AppConfig):
    """Конфигурация приложения Utilits"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'utilits'
    verbose_name = 'Утилиты'

