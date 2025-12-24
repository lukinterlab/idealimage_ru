from django.apps import AppConfig


class DonationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'donations'
    verbose_name = 'Система донатов'
    
    def ready(self):
        # Импортируем сигналы, если они будут использоваться
        pass