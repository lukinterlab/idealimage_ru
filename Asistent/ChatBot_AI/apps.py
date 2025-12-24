"""
Django app config для ChatBot_AI
"""

from django.apps import AppConfig


class ChatBotAIConfig(AppConfig):
    """Конфигурация приложения чат-бота"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Asistent.ChatBot_AI'
    verbose_name = '💬 Чат-бот AI'
    
    def ready(self):
        """Импортируем signals при запуске приложения"""
        import Asistent.ChatBot_AI.signals  # noqa

