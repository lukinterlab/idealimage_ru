"""
Django-Q задачи для автоматической публикации в соцсети
"""
import logging
from django.utils import timezone
from django.conf import settings
from .api_integrations.telegram_manager import TelegramChannelManager
from .models import PostPublication, PublicationSchedule, SocialChannel


logger = logging.getLogger(__name__)


def publish_post_to_social(post_id, platforms=None, channels=None):
    """
    Публикует статью в социальные сети
    
    Args:
        post_id: ID статьи (blog.Post)
        platforms: List платформ ['telegram', 'vk', etc.] или None для всех
        channels: List ID каналов или None для автовыбора
    
    Returns:
        dict: Результаты публикации
    """
    from blog.models import Post
    
    try:
        post = Post.objects.get(id=post_id)
    except Post.DoesNotExist:
        logger.error(f"❌ Статья с ID {post_id} не найдена")
        return {'success': False, 'error': 'Post not found'}
    
    logger.info(f"📤 Начинаем публикацию: {post.title}")
    
    results = {}
    
    # Определяем платформы
    if platforms is None:
        platforms = ['telegram']  # По умолчанию только Telegram
    
    # Получаем URL изображения
    image_url = None
    if post.kartinka:
        image_url = f"{settings.SITE_URL}{post.kartinka.url}"
    
    # Публикация в Telegram
    if 'telegram' in platforms:
        telegram = TelegramChannelManager()
        
        if channels:
            # Публикация в указанные каналы
            results['telegram'] = telegram.publish_to_multiple_channels(
                post,
                channels=channels,
                image_url=image_url
            )
        else:
            # Умный выбор каналов по категории — публикуем ТОЛЬКО в первый подходящий канал
            selected_channels = telegram.select_channels_by_category(post)
            first_channel_only = selected_channels[:1] if isinstance(selected_channels, list) else [selected_channels][0:1]
            results['telegram'] = telegram.publish_to_multiple_channels(
                post,
                channels=first_channel_only,
                image_url=image_url
            )
    
    # TODO: Добавить публикацию в Rutube, Dzen (VK исключен)
    
    # Подсчёт успешных публикаций
    total_success = 0
    total_failed = 0
    
    for platform, platform_results in results.items():
        for channel_id, result in platform_results.items():
            if result.get('success'):
                total_success += 1
            else:
                total_failed += 1
    
    logger.info(f"✅ Публикация завершена: {total_success} успешно, {total_failed} ошибок")
    
    # Обновляем статью - помечаем что опубликовано
    if total_success > 0:
        from django.utils import timezone
        post.fixed = True  # Галочка "отправлено в ТГ"
        post.telegram_posted_at = timezone.now()
        post.save(update_fields=['fixed', 'telegram_posted_at'])
        logger.info(f"✅ Статья помечена как опубликованная в телеграмм (fixed=True)")
    
    return {
        'success': total_success > 0,
        'total_success': total_success,
        'total_failed': total_failed,
        'results': results
    }


def sync_telegram_channels():
    """
    Синхронизирует все Telegram каналы с базой данных
    """
    logger.info("🔄 Синхронизация Telegram каналов...")
    
    telegram = TelegramChannelManager()
    synced = telegram.sync_channels_to_db()
    
    logger.info(f"✅ Синхронизировано {synced} каналов")
    
    return {'success': True, 'synced': synced}


def update_channels_statistics():
    """
    Обновляет статистику всех каналов
    """
    logger.info("📊 Обновление статистики каналов...")
    
    telegram = TelegramChannelManager()
    updated = telegram.update_all_channels_statistics()
    
    # TODO: Добавить обновление статистики для Rutube, Dzen (VK исключен)
    
    logger.info(f"✅ Статистика обновлена для {updated} каналов")
    
    return {'success': True, 'updated': updated}


def process_publication_schedules():
    """
    Обрабатывает активные расписания публикаций
    """
    logger.info("⏰ Проверка расписаний публикаций...")
    
    now = timezone.now()
    
    # Получаем активные расписания, которые пора запустить
    schedules = PublicationSchedule.objects.filter(
        is_active=True,
        next_run__lte=now
    )
    
    processed = 0
    
    for schedule in schedules:
        try:
            logger.info(f"📅 Обработка расписания: {schedule.name}")
            
            # Получаем категории для публикации
            categories = schedule.categories.all()
            
            # Получаем неопубликованные статьи из этих категорий
            from blog.models import Post
            
            posts = Post.objects.filter(
                category__in=categories,
                status='published',
                auto_publish_social=True
            ).exclude(
                social_publications__channel__in=schedule.channels.all()
            )[:5]  # Ограничиваем количество
            
            # Публикуем каждую статью
            for post in posts:
                channels = schedule.channels.filter(is_active=True)
                
                for channel in channels:
                    if channel.platform.name == 'telegram':
                        telegram = TelegramChannelManager()
                        
                        image_url = None
                        if post.kartinka:
                            image_url = f"{settings.SITE_URL}{post.kartinka.url}"
                        
                        telegram.publish_to_db_channel(channel, post, image_url)
            
            # Обновляем время следующего запуска
            schedule.last_run = now
            
            # Вычисляем следующий запуск на основе частоты
            if schedule.posting_frequency == 'hourly':
                from datetime import timedelta
                schedule.next_run = now + timedelta(hours=1)
            elif schedule.posting_frequency == '3times_day':
                from datetime import timedelta
                schedule.next_run = now + timedelta(hours=8)
            elif schedule.posting_frequency == 'daily':
                from datetime import timedelta
                schedule.next_run = now + timedelta(days=1)
            elif schedule.posting_frequency == 'weekly':
                from datetime import timedelta
                schedule.next_run = now + timedelta(weeks=1)
            
            schedule.save()
            processed += 1
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки расписания {schedule.id}: {e}")
    
    logger.info(f"✅ Обработано расписаний: {processed}")
    
    return {'success': True, 'processed': processed}


def collect_social_analytics():
    """
    Собирает аналитику из всех соцсетей
    """
    logger.info("📊 Сбор аналитики из соцсетей...")
    
    from .analytics.collector import collect_telegram_analytics
    
    results = {}
    
    try:
        results['telegram'] = collect_telegram_analytics()
    except Exception as e:
        logger.error(f"❌ Ошибка сбора Telegram аналитики: {e}")
        results['telegram'] = {'success': False, 'error': str(e)}
    
    # TODO: Добавить сбор аналитики для Rutube, Dzen (VK исключен)
    
    return results

