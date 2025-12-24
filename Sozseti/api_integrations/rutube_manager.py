"""
Rutube Manager - Управление публикациями на Rutube
"""
import logging
import requests
from django.conf import settings
from django.utils import timezone
from ..models import SocialChannel, PostPublication, SocialPlatform


logger = logging.getLogger(__name__)


class RutubeManager:
    """
    Менеджер для управления публикациями на Rutube
    """
    
    def __init__(self, api_key=None, channel_id=None):
        """
        Инициализация Rutube Manager
        
        Args:
            api_key: Rutube API key
            channel_id: ID канала на Rutube
        """
        self.api_key = api_key or getattr(settings, 'RUTUBE_API_KEY', None)
        self.channel_id = channel_id or getattr(settings, 'RUTUBE_CHANNEL_ID', None)
        self.base_url = "https://rutube.ru/api"
    
    def get_rutube_platform(self):
        """Получить или создать платформу Rutube"""
        platform, created = SocialPlatform.objects.get_or_create(
            name='rutube',
            defaults={
                'is_active': True,
                'icon_class': 'fas fa-video',  # Font Awesome иконка
            }
        )
        return platform
    
    def sync_channel_to_db(self):
        """
        Синхронизирует Rutube канал с базой данных
        """
        if not self.api_key or not self.channel_id:
            logger.warning("[WARN] Rutube API не настроен")
            return 0
        
        platform = self.get_rutube_platform()
        
        try:
            # Создаём канал в БД
            channel, created = SocialChannel.objects.get_or_create(
                platform=platform,
                channel_id=str(self.channel_id),
                defaults={
                    'channel_name': 'IdealImage.ru на Rutube',
                    'channel_type': 'beauty',
                    'channel_url': f'https://rutube.ru/channel/{self.channel_id}/',
                    'is_active': True,
                }
            )
            
            if created:
                logger.info(f"[OK] Синхронизирован Rutube канал: {channel.channel_name}")
                return 1
        
        except Exception as e:
            logger.error(f"[ERROR] Ошибка синхронизации Rutube канала: {e}")
        
        return 0
    
    def publish_announcement(self, post, image_url=None):
        """
        Публикует анонс статьи как пост в сообществе Rutube
        
        Args:
            post: Объект blog.Post
            image_url: URL изображения
        
        Returns:
            dict: {'success': bool, 'announcement_text': str}
        """
        if not self.api_key:
            logger.warning("[WARN] Rutube API key не настроен")
            return {'success': False, 'error': 'API key not configured'}
        
        try:
            # Формируем текст анонса
            announcement_text = f"""
{post.title}

{post.description[:200] if post.description else post.content[:200]}...

Читать полностью: {settings.SITE_URL}{post.get_absolute_url()}

#красота #мода #стиль #IdealImage
"""
            
            logger.info(f"[OK] Rutube: анонс подготовлен для статьи '{post.title}'")
            logger.info("[INFO] Примечание: Для автопубликации требуется OAuth токен Rutube")
            
            # TODO: Реализовать полную публикацию через Rutube API
            # Требуется OAuth авторизация и permissions
            
            return {
                'success': True,
                'platform': 'rutube',
                'announcement_text': announcement_text
            }
            
        except Exception as e:
            logger.error(f"[ERROR] Ошибка публикации на Rutube: {e}")
            return {'success': False, 'error': str(e)}
    
    def publish_to_db_channel(self, channel_obj, post, image_url=None):
        """
        Публикует статью в Rutube канал из БД и сохраняет результат
        
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
            result = self.publish_announcement(post, image_url=image_url)
            
            if result['success']:
                publication.status = 'published'
                publication.published_at = timezone.now()
                publication.post_content = result.get('announcement_text', '')
                logger.info(f"[OK] Rutube публикация сохранена в БД: {publication.id}")
            else:
                publication.status = 'failed'
                publication.error_log = result.get('error', 'Unknown error')
                logger.error(f"[ERROR] Rutube публикация failed: {result.get('error')}")
            
            publication.save()
            
        except Exception as e:
            publication.status = 'failed'
            publication.error_log = str(e)
            publication.save()
            logger.error(f"[ERROR] Исключение при публикации на Rutube: {e}")
        
        return publication


def get_rutube_manager():
    """Возвращает экземпляр RutubeManager"""
    return RutubeManager()

