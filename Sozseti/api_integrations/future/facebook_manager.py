"""
Facebook Manager - Будущая интеграция (требует VPN)
"""
import logging
from django.conf import settings
from ...models import SocialPlatform


logger = logging.getLogger(__name__)


class FacebookManager:
    """
    Менеджер для будущей интеграции с Facebook
    Требует VPN для работы из России
    """
    
    def __init__(self, access_token=None, page_id=None):
        """
        Инициализация Facebook Manager
        
        Args:
            access_token: Facebook access token
            page_id: ID страницы Facebook
        """
        self.access_token = access_token or getattr(settings, 'FACEBOOK_ACCESS_TOKEN', None)
        self.page_id = page_id or getattr(settings, 'FACEBOOK_PAGE_ID', None)
        self.api_version = 'v18.0'
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        
        # VPN настройки
        self.vpn_host = getattr(settings, 'VPN_PROXY_HOST', None)
    
    def get_facebook_platform(self):
        """Получить или создать платформу Facebook"""
        platform, created = SocialPlatform.objects.get_or_create(
            name='facebook',
            defaults={
                'is_active': False,  # Требует настройки VPN
                'requires_vpn': True,
                'icon_class': 'fab fa-facebook',
            }
        )
        return platform
    
    def is_available(self):
        """Проверка доступности (требуется VPN)"""
        if not self.vpn_host:
            logger.warning("[WARN] Facebook требует VPN. Настройте VPN_PROXY_HOST")
            return False
        return True
    
    def publish_post(self, post, image_url=None):
        """
        Публикация в Facebook (заглушка)
        
        Args:
            post: Объект blog.Post
            image_url: URL изображения
        
        Returns:
            dict: Результат
        """
        logger.warning("[WARN] Facebook API требует настройки VPN и токена")
        
        return {
            'success': False,
            'error': 'Facebook интеграция в разработке. Требуется: VPN, Facebook Page Access Token'
        }


def get_facebook_manager():
    """Возвращает экземпляр FacebookManager"""
    return FacebookManager()

