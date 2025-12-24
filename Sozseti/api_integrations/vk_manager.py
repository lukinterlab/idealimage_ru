"""
VK Manager - Управление публикациями в VK
"""
import logging
import requests
from django.conf import settings
from django.utils import timezone
from ..models import SocialChannel, PostPublication, SocialPlatform


logger = logging.getLogger(__name__)


class VKManager:
    """
    Менеджер для управления публикациями в VK
    """
    
    def __init__(self, access_token=None, group_id=None):
        """
        Инициализация VK Manager
        
        Args:
            access_token: VK API access token
            group_id: ID группы/сообщества
        """
        self.access_token = access_token or getattr(settings, 'VK_API_TOKEN', None)
        self.group_id = group_id or getattr(settings, 'VK_GROUP_ID', None)
        self.api_version = '5.131'
        self.base_url = 'https://api.vk.com/method/'
    
    def get_vk_platform(self):
        """Получить или создать платформу VK"""
        platform, created = SocialPlatform.objects.get_or_create(
            name='vk',
            defaults={
                'is_active': True,
                'icon_class': 'fab fa-vk',
            }
        )
        return platform
    
    def sync_groups_to_db(self):
        """
        Синхронизирует VK группы с базой данных
        """
        if not self.access_token or not self.group_id:
            logger.warning("[WARN] VK API не настроен")
            return 0
        
        platform = self.get_vk_platform()
        
        # Получаем информацию о группе
        try:
            group_info = self.get_group_info()
            
            if group_info:
                channel, created = SocialChannel.objects.get_or_create(
                    platform=platform,
                    channel_id=str(self.group_id),
                    defaults={
                        'channel_name': group_info.get('name', 'VK Group'),
                        'channel_type': 'beauty',
                        'channel_url': f"https://vk.com/club{self.group_id}",
                        'is_active': True,
                        'subscribers_count': group_info.get('members_count', 0),
                    }
                )
                
                if created:
                    logger.info(f"[OK] Синхронизирована VK группа: {channel.channel_name}")
                    return 1
        
        except Exception as e:
            logger.error(f"[ERROR] Ошибка синхронизации VK группы: {e}")
        
        return 0
    
    def get_group_info(self):
        """Получает информацию о группе"""
        try:
            url = f"{self.base_url}groups.getById"
            params = {
                'group_id': self.group_id,
                'fields': 'members_count,description',
                'access_token': self.access_token,
                'v': self.api_version
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if 'error' in data:
                logger.error(f"[ERROR] VK API error: {data['error']}")
                return None
            
            if 'response' in data and data['response']:
                group = data['response'][0]
                return {
                    'name': group.get('name'),
                    'members_count': group.get('members_count', 0),
                    'description': group.get('description', ''),
                }
            
        except Exception as e:
            logger.error(f"[ERROR] Ошибка получения информации о группе VK: {e}")
        
        return None
    
    def publish_to_wall(self, post, image_url=None):
        """
        Публикует статью на стену VK группы
        
        Args:
            post: Объект blog.Post
            image_url: URL изображения
        
        Returns:
            dict: {'success': bool, 'post_id': int, 'post_url': str}
        """
        if not self.access_token or not self.group_id:
            logger.warning("[WARN] VK API не настроен")
            return {'success': False, 'error': 'VK API not configured'}
        
        try:
            # Формируем текст поста
            post_text = f"""
{post.title}

{post.description[:300] if post.description else post.content[:300]}...

Читать полностью: {settings.SITE_URL}{post.get_absolute_url()}

#красота #мода #стиль #IdealImage
"""
            
            # Загружаем изображение если есть
            attachment = None
            if image_url:
                attachment = self._upload_image(image_url)
            
            # Публикуем на стену
            url = f"{self.base_url}wall.post"
            params = {
                'owner_id': f'-{self.group_id}',
                'message': post_text,
                'attachments': attachment,
                'access_token': self.access_token,
                'v': self.api_version
            }
            
            response = requests.post(url, data=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            if 'error' in data:
                logger.error(f"[ERROR] VK API error: {data['error']}")
                return {'success': False, 'error': data['error'].get('error_msg')}
            
            post_id = data.get('response', {}).get('post_id')
            vk_post_url = f"https://vk.com/wall-{self.group_id}_{post_id}"
            
            logger.info(f"[OK] VK: опубликована статья '{post.title}'")
            logger.info(f"     URL: {vk_post_url}")
            
            return {
                'success': True,
                'platform': 'vk',
                'post_id': post_id,
                'post_url': vk_post_url
            }
            
        except Exception as e:
            logger.error(f"[ERROR] Ошибка публикации в VK: {e}")
            return {'success': False, 'error': str(e)}
    
    def _upload_image(self, image_url):
        """Загружает изображение на VK сервер"""
        try:
            # Получаем адрес для загрузки
            upload_url_response = requests.post(
                f"{self.base_url}photos.getWallUploadServer",
                data={
                    'group_id': self.group_id,
                    'access_token': self.access_token,
                    'v': self.api_version
                },
                timeout=10
            )
            
            upload_data = upload_url_response.json()
            
            if 'error' in upload_data:
                logger.error(f"[ERROR] VK upload server error: {upload_data['error']}")
                return None
            
            upload_url = upload_data.get('response', {}).get('upload_url')
            
            if not upload_url:
                return None
            
            # Скачиваем изображение
            image_response = requests.get(image_url, timeout=10)
            image_response.raise_for_status()
            
            # Загружаем на VK сервер
            files = {'photo': ('image.jpg', image_response.content)}
            upload_response = requests.post(upload_url, files=files, timeout=20)
            upload_result = upload_response.json()
            
            # Сохраняем фото на стене
            save_response = requests.post(
                f"{self.base_url}photos.saveWallPhoto",
                data={
                    'group_id': self.group_id,
                    'photo': upload_result.get('photo'),
                    'server': upload_result.get('server'),
                    'hash': upload_result.get('hash'),
                    'access_token': self.access_token,
                    'v': self.api_version
                },
                timeout=10
            )
            
            save_data = save_response.json()
            
            if 'response' in save_data and save_data['response']:
                photo = save_data['response'][0]
                attachment = f"photo{photo['owner_id']}_{photo['id']}"
                return attachment
            
        except Exception as e:
            logger.error(f"[ERROR] Ошибка загрузки изображения в VK: {e}")
        
        return None
    
    def publish_to_db_channel(self, channel_obj, post, image_url=None):
        """
        Публикует статью в канал VK из БД и сохраняет результат
        
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
            result = self.publish_to_wall(post, image_url=image_url)
            
            if result['success']:
                publication.status = 'published'
                publication.published_at = timezone.now()
                publication.platform_post_id = str(result.get('post_id', ''))
                publication.platform_url = result.get('post_url', '')
                logger.info(f"[OK] VK публикация сохранена в БД: {publication.id}")
            else:
                publication.status = 'failed'
                publication.error_log = result.get('error', 'Unknown error')
                logger.error(f"[ERROR] VK публикация failed: {result.get('error')}")
            
            publication.save()
            
        except Exception as e:
            publication.status = 'failed'
            publication.error_log = str(e)
            publication.save()
            logger.error(f"[ERROR] Исключение при публикации в VK: {e}")
        
        return publication


def get_vk_manager():
    """Возвращает экземпляр VKManager"""
    return VKManager()

