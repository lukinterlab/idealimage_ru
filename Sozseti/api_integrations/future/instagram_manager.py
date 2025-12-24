"""
Instagram Manager - Будущая интеграция (требует VPN)
"""
import logging
from django.conf import settings
from ...models import SocialPlatform


logger = logging.getLogger(__name__)


class InstagramManager:
    """
    Менеджер для будущей интеграции с Instagram
    Требует VPN для работы из России
    """
    
    def __init__(self, username=None, password=None):
        """
        Инициализация Instagram Manager
        
        Args:
            username: Instagram username
            password: Instagram password
        """
        self.username = username or getattr(settings, 'INSTAGRAM_USERNAME', None)
        self.password = password or getattr(settings, 'INSTAGRAM_PASSWORD', None)
        
        # VPN настройки
        self.vpn_host = getattr(settings, 'VPN_PROXY_HOST', None)
        self.vpn_port = getattr(settings, 'VPN_PROXY_PORT', None)
    
    def get_instagram_platform(self):
        """Получить или создать платформу Instagram"""
        platform, created = SocialPlatform.objects.get_or_create(
            name='instagram',
            defaults={
                'is_active': False,  # Требует настройки VPN
                'requires_vpn': True,
                'icon_class': 'fab fa-instagram',
            }
        )
        return platform
    
    def is_available(self):
        """Проверка доступности (требуется VPN)"""
        if not self.vpn_host:
            logger.warning("[WARN] Instagram требует VPN. Настройте VPN_PROXY_HOST")
            return False
        return True
    
    def publish_post(self, post, image_url=None):
        """
        Публикация в Instagram (заглушка)
        
        Args:
            post: Объект blog.Post
            image_url: URL изображения
        
        Returns:
            dict: Результат
        """
        logger.warning("[WARN] Instagram API требует настройки VPN и авторизации")
        
        return {
            'success': False,
            'error': 'Instagram интеграция в разработке. Требуется: VPN, Instagram Business Account'
        }


def get_instagram_manager():
    """Возвращает экземпляр InstagramManager"""
    return InstagramManager()

