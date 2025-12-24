"""
Интеграция Sozseti с AI-Ассистентом
"""
import logging
from django.conf import settings
from .api_integrations.telegram_manager import TelegramChannelManager
from .api_integrations.vk_manager import VKManager
from .api_integrations.rutube_manager import RutubeManager
from .api_integrations.dzen_manager import DzenManager


logger = logging.getLogger(__name__)


def publish_ai_article_to_social(post, schedule):
    """
    Публикует AI-сгенерированную статью в соцсети согласно настройкам расписания
    
    Args:
        post: Объект blog.Post (только что созданная AI статья)
        schedule: Объект Asistent.AISchedule
    
    Returns:
        dict: Результаты публикации
    """
    results = {
        'telegram': None,
        'vk': None,
        'rutube': None,
        'dzen': None,
    }
    
    # Получаем URL изображения
    image_url = None
    if post.kartinka:
        image_url = f"{settings.SITE_URL}{post.kartinka.url}"
    
    # Публикация в Telegram
    if hasattr(schedule, 'telegram_channels') and schedule.telegram_channels:
        try:
            logger.info("[*] Публикация AI-статьи в Telegram...")
            telegram = TelegramChannelManager()
            
            # Публикуем в указанные каналы из расписания
            channel_ids = schedule.telegram_channels
            
            # Если каналы не указаны, используем умный выбор
            if not channel_ids or len(channel_ids) == 0:
                selected_channels = telegram.select_channels_by_category(post)
                results['telegram'] = telegram.publish_to_multiple_channels(
                    post,
                    channels=selected_channels,
                    image_url=image_url
                )
            else:
                # Публикуем в указанные каналы
                from .models import SocialChannel
                platform = telegram.get_telegram_platform()
                
                for channel_id in channel_ids:
                    try:
                        channel = SocialChannel.objects.get(
                            platform=platform,
                            channel_id=channel_id
                        )
                        telegram.publish_to_db_channel(channel, post, image_url)
                    except SocialChannel.DoesNotExist:
                        logger.warning(f"[WARN] Канал {channel_id} не найден в БД")
                
                results['telegram'] = {'success': True}
            
            logger.info("[OK] Публикация в Telegram завершена")
        
        except Exception as e:
            logger.error(f"[ERROR] Ошибка публикации в Telegram: {e}")
            results['telegram'] = {'success': False, 'error': str(e)}
    
    # Публикация в VK
    if hasattr(schedule, 'vk_enabled') and schedule.vk_enabled:
        try:
            logger.info("[*] Публикация AI-статьи в VK...")
            vk = VKManager()
            
            if vk.access_token and vk.group_id:
                result = vk.publish_to_wall(post, image_url)
                results['vk'] = result
                
                if result['success']:
                    logger.info("[OK] Публикация в VK завершена")
                else:
                    logger.error(f"[ERROR] VK: {result.get('error')}")
            else:
                logger.warning("[WARN] VK не настроен")
                results['vk'] = {'success': False, 'error': 'Not configured'}
        
        except Exception as e:
            logger.error(f"[ERROR] Ошибка публикации в VK: {e}")
            results['vk'] = {'success': False, 'error': str(e)}
    
    # Публикация на Rutube
    if hasattr(schedule, 'rutube_enabled') and schedule.rutube_enabled:
        try:
            logger.info("[*] Публикация AI-статьи на Rutube...")
            rutube = RutubeManager()
            
            if rutube.api_key:
                result = rutube.publish_announcement(post, image_url)
                results['rutube'] = result
                
                if result['success']:
                    logger.info("[OK] Публикация на Rutube завершена")
                else:
                    logger.error(f"[ERROR] Rutube: {result.get('error')}")
            else:
                logger.warning("[WARN] Rutube не настроен")
                results['rutube'] = {'success': False, 'error': 'Not configured'}
        
        except Exception as e:
            logger.error(f"[ERROR] Ошибка публикации на Rutube: {e}")
            results['rutube'] = {'success': False, 'error': str(e)}
    
    # Публикация в Дзен
    if hasattr(schedule, 'dzen_enabled') and schedule.dzen_enabled:
        try:
            logger.info("[*] Публикация AI-статьи в Дзен...")
            dzen = DzenManager()
            
            if dzen.token:
                result = dzen.publish_article(post, image_url)
                results['dzen'] = result
                
                if result['success']:
                    logger.info("[OK] Публикация в Дзен завершена")
                else:
                    logger.error(f"[ERROR] Dzen: {result.get('error')}")
            else:
                logger.warning("[WARN] Dzen не настроен")
                results['dzen'] = {'success': False, 'error': 'Not configured'}
        
        except Exception as e:
            logger.error(f"[ERROR] Ошибка публикации в Дзен: {e}")
            results['dzen'] = {'success': False, 'error': str(e)}
    
    # Подсчёт успешных публикаций
    successful = sum(
        1 for result in results.values()
        if result and isinstance(result, dict) and result.get('success')
    )
    
    logger.info(f"[OK] AI-статья опубликована в {successful} соцсетей")
    
    return results

