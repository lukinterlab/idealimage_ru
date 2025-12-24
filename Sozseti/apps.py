from django.apps import AppConfig


class SozsetiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Sozseti'
    verbose_name = '📱 Социальные сети'
    
    def ready(self):
        # Импортируем signals когда они будут созданы
        try:
            import Sozseti.signals
        except ImportError:
            pass
