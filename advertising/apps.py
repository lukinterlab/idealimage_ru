from django.apps import AppConfig


class AdvertisingConfig(AppConfig):
    """Конфигурация приложения Advertising"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'advertising'
    verbose_name = 'Управление рекламой'
    
    def ready(self):
        """Импортируем сигналы и регистрируем фоновые задачи при загрузке приложения"""
        try:
            import advertising.signals
        except ImportError:
            pass
        
        # ОТКЛЮЧЕНО: Автогенерация рекламных задач
        # Теперь задачи создаются вручную через админку
        # Раскомментируйте когда реклама будет активна:
        
        # try:
        #     from advertising.models import AdPlace
        #     from advertising.tasks import schedule_advertising_tasks
        #     
        #     if AdPlace.objects.filter(is_active=True).exists():
        #         schedule_advertising_tasks()
        # except Exception as e:
        #     pass
