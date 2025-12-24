"""
MAX Manager - Заглушка для будущей интеграции с MAX
API в разработке: https://business.max.ru/
"""
import logging
from django.conf import settings
from ..models import SocialPlatform


logger = logging.getLogger(__name__)


class MAXManager:
    """
    Менеджер для будущей интеграции с MAX
    API пока недоступен, готовим структуру
    """
    
    def __init__(self, api_token=None):
        """
        Инициализация MAX Manager
        
        Args:
            api_token: MAX API токен (будет доступен позже)
        """
        self.api_token = api_token or getattr(settings, 'MAX_API_TOKEN', None)
        self.base_url = "https://api.max.ru/v1"  # Предполагаемый URL
    
    def get_max_platform(self):
        """Получить или создать платформу MAX"""
        platform, created = SocialPlatform.objects.get_or_create(
            name='max',
            defaults={
                'is_active': False,  # Пока неактивна
                'icon_class': 'fas fa-comment',
            }
        )
        return platform
    
    def is_available(self):
        """Проверка доступности API"""
        logger.info("[INFO] MAX API пока недоступен - ожидаем открытия")
        return False
    
    def publish_announcement(self, post, image_url=None):
        """
        Публикация в MAX (заглушка)
        
        Args:
            post: Объект blog.Post
            image_url: URL изображения
        
        Returns:
            dict: Результат (всегда False пока)
        """
        logger.warning("[WARN] MAX API пока недоступен")
        
        return {
            'success': False,
            'error': 'MAX API в разработке. Следите за обновлениями на https://business.max.ru/'
        }


def get_max_manager():
    """Возвращает экземпляр MAXManager"""
    return MAXManager()

