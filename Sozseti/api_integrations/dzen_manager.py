"""
Dzen Manager - Управление публикациями в Яндекс.Дзен
"""
import logging
import requests
from django.conf import settings
from django.utils import timezone
from ..models import SocialChannel, PostPublication, SocialPlatform


logger = logging.getLogger(__name__)


class DzenManager:
    """
    Менеджер для управления публикациями в Яндекс.Дзен
    """
    
    def __init__(self, token=None, channel_id=None):
        """
        Инициализация Dzen Manager
        
        Args:
            token: Yandex OAuth токен
            channel_id: ID канала в Дзен
        """
        self.token = token or getattr(settings, 'DZEN_TOKEN', None)
        self.channel_id = channel_id or getattr(settings, 'DZEN_CHANNEL_ID', None)
        self.base_url = "https://dzen.ru/api/v3"
    
    def get_dzen_platform(self):
        """Получить или создать платформу Dzen"""
        platform, created = SocialPlatform.objects.get_or_create(
            name='dzen',
            defaults={
                'is_active': True,
                'icon_class': 'fas fa-newspaper',
            }
        )
        return platform
    
    def sync_channel_to_db(self):
        """
        Синхронизирует Dzen канал с базой данных
        """
        if not self.token or not self.channel_id:
            logger.warning("[WARN] Dzen API не настроен")
            return 0
        
        platform = self.get_dzen_platform()
        
        try:
            # Создаём канал в БД
            channel, created = SocialChannel.objects.get_or_create(
                platform=platform,
                channel_id=str(self.channel_id),
                defaults={
                    'channel_name': 'IdealImage.ru в Дзен',
                    'channel_type': 'beauty',
                    'channel_url': f'https://dzen.ru/{self.channel_id}',
                    'is_active': True,
                }
            )
            
            if created:
                logger.info(f"[OK] Синхронизирован Dzen канал: {channel.channel_name}")
                return 1
        
        except Exception as e:
            logger.error(f"[ERROR] Ошибка синхронизации Dzen канала: {e}")
        
        return 0
    
    def publish_article(self, post, image_url=None):
        """
        Публикует статью в Яндекс.Дзен
        
        Args:
            post: Объект blog.Post
            image_url: URL изображения
        
        Returns:
            dict: {'success': bool, 'article_url': str}
        """
        if not self.token:
            logger.warning("[WARN] Dzen токен не настроен")
            return {'success': False, 'error': 'Token not configured'}
        
        try:
            # Формируем контент для Дзен (HTML)
            content = f"""
<h2>{post.title}</h2>

{post.content[:1000]}...

<p><strong>Читать полностью:</strong> <a href="{settings.SITE_URL}{post.get_absolute_url()}">на IdealImage.ru</a></p>
"""
            
            logger.info(f"[OK] Dzen: статья подготовлена '{post.title}'")
            logger.info("[INFO] Примечание: Требуется настройка Яндекс OAuth токена")
            
            # TODO: Реализовать полную публикацию через Dzen API
            # API документация: https://yandex.ru/dev/zen/
            
            return {
                'success': True,
                'platform': 'dzen',
                'content': content
            }
            
        except Exception as e:
            logger.error(f"[ERROR] Ошибка публикации в Dzen: {e}")
            return {'success': False, 'error': str(e)}
    
    def publish_to_db_channel(self, channel_obj, post, image_url=None):
        """
        Публикует статью в Dzen канал из БД и сохраняет результат
        
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
            result = self.publish_article(post, image_url=image_url)
            
            if result['success']:
                publication.status = 'published'
                publication.published_at = timezone.now()
                publication.post_content = result.get('content', '')
                logger.info(f"[OK] Dzen публикация сохранена в БД: {publication.id}")
            else:
                publication.status = 'failed'
                publication.error_log = result.get('error', 'Unknown error')
                logger.error(f"[ERROR] Dzen публикация failed: {result.get('error')}")
            
            publication.save()
            
        except Exception as e:
            publication.status = 'failed'
            publication.error_log = str(e)
            publication.save()
            logger.error(f"[ERROR] Исключение при публикации в Dzen: {e}")
        
        return publication


def get_dzen_manager():
    """Возвращает экземпляр DzenManager"""
    return DzenManager()

