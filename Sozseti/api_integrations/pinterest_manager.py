"""
Pinterest Manager - Управление публикациями в Pinterest
"""
import logging
import requests
from django.conf import settings
from django.utils import timezone
from ..models import SocialChannel, PostPublication, SocialPlatform


logger = logging.getLogger(__name__)


class PinterestManager:
    """
    Менеджер для управления публикациями в Pinterest
    """
    
    def __init__(self, access_token=None, board_id=None):
        """
        Инициализация Pinterest Manager
        
        Args:
            access_token: Pinterest access token
            board_id: ID доски Pinterest
        """
        self.access_token = access_token or getattr(settings, 'PINTEREST_ACCESS_TOKEN', None)
        self.board_id = board_id or getattr(settings, 'PINTEREST_BOARD_ID', None)
        self.api_version = 'v5'
        self.base_url = f"https://api.pinterest.com/{self.api_version}"
    
    def get_pinterest_platform(self):
        """Получить или создать платформу Pinterest"""
        platform, created = SocialPlatform.objects.get_or_create(
            name='pinterest',
            defaults={
                'is_active': False,  # Активируем после настройки
                'icon_class': 'fab fa-pinterest',
            }
        )
        return platform
    
    def sync_board_to_db(self):
        """
        Синхронизирует Pinterest доску с базой данных
        """
        if not self.access_token or not self.board_id:
            logger.warning("[WARN] Pinterest API не настроен")
            return 0
        
        platform = self.get_pinterest_platform()
        
        try:
            # Создаём доску в БД
            channel, created = SocialChannel.objects.get_or_create(
                platform=platform,
                channel_id=str(self.board_id),
                defaults={
                    'channel_name': 'IdealImage.ru Board',
                    'channel_type': 'beauty',
                    'channel_url': f'https://pinterest.com/board/{self.board_id}',
                    'is_active': False,  # Активируем вручную после проверки
                }
            )
            
            if created:
                logger.info(f"[OK] Синхронизирована Pinterest доска: {channel.channel_name}")
                return 1
        
        except Exception as e:
            logger.error(f"[ERROR] Ошибка синхронизации Pinterest: {e}")
        
        return 0
    
    def create_pin(self, post, image_url):
        """
        Создаёт пин в Pinterest
        
        Args:
            post: Объект blog.Post
            image_url: URL изображения (обязательно!)
        
        Returns:
            dict: {'success': bool, 'pin_id': str, 'pin_url': str}
        """
        if not self.access_token or not self.board_id:
            logger.warning("[WARN] Pinterest API не настроен")
            return {'success': False, 'error': 'API not configured'}
        
        if not image_url:
            logger.warning("[WARN] Pinterest требует изображение")
            return {'success': False, 'error': 'Image required'}
        
        try:
            # Формируем описание пина
            description = f"""
{post.title}

{post.description[:400] if post.description else post.content[:400]}...

Читать полностью: {settings.SITE_URL}{post.get_absolute_url()}
"""
            
            # Создаём пин через Pinterest API
            url = f"{self.base_url}/pins"
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
            }
            
            data = {
                'board_id': self.board_id,
                'title': post.title,
                'description': description,
                'link': f"{settings.SITE_URL}{post.get_absolute_url()}",
                'media_source': {
                    'source_type': 'image_url',
                    'url': image_url
                }
            }
            
            logger.info(f"[INFO] Pinterest: создание пина для '{post.title}'")
            logger.info("[INFO] Примечание: Требуется Pinterest Access Token")
            
            # TODO: Реализовать полную публикацию после получения токена
            # response = requests.post(url, json=data, headers=headers, timeout=15)
            
            return {
                'success': False,
                'error': 'Pinterest API требует настройки токена. См. https://developers.pinterest.com/'
            }
            
        except Exception as e:
            logger.error(f"[ERROR] Ошибка создания пина в Pinterest: {e}")
            return {'success': False, 'error': str(e)}
    
    def publish_to_db_channel(self, channel_obj, post, image_url=None):
        """
        Публикует статью в Pinterest из БД и сохраняет результат
        
        Args:
            channel_obj: Объект SocialChannel
            post: Объект blog.Post
            image_url: URL изображения
        
        Returns:
            PostPublication object
        """
        # Создаём запись о публикации
        publication = PostPublication.objects.create(
            post=post,
            channel=channel_obj,
            status='publishing',
            scheduled_at=timezone.now()
        )
        
        try:
            # Публикуем
            result = self.create_pin(post, image_url=image_url)
            
            if result['success']:
                publication.status = 'published'
                publication.published_at = timezone.now()
                publication.platform_post_id = result.get('pin_id', '')
                publication.platform_url = result.get('pin_url', '')
                logger.info(f"[OK] Pinterest публикация сохранена в БД: {publication.id}")
            else:
                publication.status = 'failed'
                publication.error_log = result.get('error', 'Unknown error')
                logger.error(f"[ERROR] Pinterest публикация failed: {result.get('error')}")
            
            publication.save()
            
        except Exception as e:
            publication.status = 'failed'
            publication.error_log = str(e)
            publication.save()
            logger.error(f"[ERROR] Исключение при публикации в Pinterest: {e}")
        
        return publication


def get_pinterest_manager():
    """Возвращает экземпляр PinterestManager"""
    return PinterestManager()

