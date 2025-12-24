"""
YouTube Manager - Будущая интеграция (требует VPN)
"""
import logging
from django.conf import settings
from ...models import SocialPlatform


logger = logging.getLogger(__name__)


class YouTubeManager:
    """
    Менеджер для будущей интеграции с YouTube
    Требует VPN для работы из России
    """
    
    def __init__(self, api_key=None, channel_id=None):
        """
        Инициализация YouTube Manager
        
        Args:
            api_key: YouTube Data API key
            channel_id: ID канала YouTube
        """
        self.api_key = api_key or getattr(settings, 'YOUTUBE_API_KEY', None)
        self.channel_id = channel_id or getattr(settings, 'YOUTUBE_CHANNEL_ID', None)
        self.base_url = "https://www.googleapis.com/youtube/v3"
        
        # VPN настройки
        self.vpn_host = getattr(settings, 'VPN_PROXY_HOST', None)
    
    def get_youtube_platform(self):
        """Получить или создать платформу YouTube"""
        platform, created = SocialPlatform.objects.get_or_create(
            name='youtube',
            defaults={
                'is_active': False,  # Требует настройки VPN
                'requires_vpn': True,
                'icon_class': 'fab fa-youtube',
            }
        )
        return platform
    
    def is_available(self):
        """Проверка доступности (требуется VPN)"""
        if not self.vpn_host:
            logger.warning("[WARN] YouTube требует VPN. Настройте VPN_PROXY_HOST")
            return False
        return True
    
    def upload_video(self, post, video_file=None):
        """
        Загрузка видео на YouTube (заглушка)
        
        Args:
            post: Объект blog.Post
            video_file: Путь к видео файлу
        
        Returns:
            dict: Результат
        """
        logger.warning("[WARN] YouTube API требует настройки VPN и OAuth")
        
        return {
            'success': False,
            'error': 'YouTube интеграция в разработке. Требуется: VPN, YouTube Data API v3, OAuth токен'
        }


def get_youtube_manager():
    """Возвращает экземпляр YouTubeManager"""
    return YouTubeManager()

