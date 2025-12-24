"""
Сборщик аналитики из социальных сетей
"""
import logging
from django.utils import timezone
from datetime import timedelta
from ..models import ChannelAnalytics, SocialChannel, PostPublication


logger = logging.getLogger(__name__)


def collect_telegram_analytics():
    """
    Собирает аналитику из Telegram каналов
    
    Returns:
        dict: Результаты сбора
    """
    logger.info("📊 Сбор Telegram аналитики...")
    
    from ..api_integrations.telegram_manager import TelegramChannelManager
    
    telegram = TelegramChannelManager()
    platform = telegram.get_telegram_platform()
    
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    
    channels = SocialChannel.objects.filter(
        platform=platform,
        is_active=True
    )
    
    collected = 0
    
    for channel in channels:
        try:
            # Получаем статистику канала
            stats = telegram.get_channel_statistics(channel.channel_id)
            
            if stats:
                # Обновляем количество подписчиков
                old_subscribers = channel.subscribers_count
                new_subscribers = stats.get('subscribers', 0)
                channel.subscribers_count = new_subscribers
                channel.save(update_fields=['subscribers_count'])
                
                # Подсчитываем прирост
                subscribers_gained = new_subscribers - old_subscribers
                
                # Получаем публикации за вчера
                yesterday_pubs = PostPublication.objects.filter(
                    channel=channel,
                    published_at__date=yesterday,
                    status='published'
                )
                
                # Суммируем метрики
                total_views = sum(p.views_count for p in yesterday_pubs)
                total_engagement = sum(p.likes_count + p.comments_count + p.shares_count for p in yesterday_pubs)
                
                # Находим топ пост
                top_post = yesterday_pubs.order_by('-engagement_score').first()
                
                # Создаём или обновляем аналитику
                analytics, created = ChannelAnalytics.objects.get_or_create(
                    channel=channel,
                    date=yesterday,
                    defaults={
                        'subscribers_gained': subscribers_gained,
                        'posts_published': yesterday_pubs.count(),
                        'total_views': total_views,
                        'total_engagement': total_engagement,
                        'top_post': top_post,
                    }
                )
                
                if not created:
                    analytics.subscribers_gained = subscribers_gained
                    analytics.posts_published = yesterday_pubs.count()
                    analytics.total_views = total_views
                    analytics.total_engagement = total_engagement
                    analytics.top_post = top_post
                    analytics.save()
                
                collected += 1
                logger.info(f"✅ Собрана аналитика: {channel.channel_name}")
        
        except Exception as e:
            logger.error(f"❌ Ошибка сбора аналитики для {channel.channel_name}: {e}")
    
    logger.info(f"📊 Собрана аналитика для {collected} каналов")
    
    return {'success': True, 'collected': collected}


def collect_vk_analytics():
    """
    Собирает аналитику из VK (будет реализовано)
    """
    logger.info("📊 Сбор VK аналитики (в разработке)...")
    return {'success': False, 'error': 'Not implemented yet'}


def collect_all_analytics():
    """
    Собирает аналитику из всех платформ
    """
    results = {}
    
    results['telegram'] = collect_telegram_analytics()
    # results['vk'] = collect_vk_analytics()
    # results['rutube'] = collect_rutube_analytics()
    # results['dzen'] = collect_dzen_analytics()
    
    return results

