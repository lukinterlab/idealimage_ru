"""
Telegram Channel Manager - Управление 18 Telegram каналами
"""
import logging
from django.conf import settings
from django.utils import timezone
from ..models import SocialChannel, PostPublication, SocialPlatform


logger = logging.getLogger(__name__)

from Asistent.services.telegram_client import get_telegram_client


class TelegramChannelManager:
    """
    Расширенный менеджер для управления всеми Telegram каналами
    """
    
    def __init__(self, bot_token=None):
        """
        Инициализация менеджера
        
        Args:
            bot_token: Telegram Bot API token (опционально)
        """
        self.bot_token = bot_token or getattr(settings, 'BOT_TOKEN', None)
        self.client = get_telegram_client()
        
        # Словарь всех 18 каналов из settings
        self.all_channels = {
            'fizkult_hello_beauty': getattr(settings, 'CHAT_ID1', None),      # @fizkult_hello_beauty
            'eat_love_live': getattr(settings, 'CHAT_ID2', None),             # @eat_love_live
            'ideal_image_ru': getattr(settings, 'CHAT_ID3', None),            # @ideal_image_ru (главный)
            'the_best_hairstyles': getattr(settings, 'CHAT_ID4', None),       # @the_best_hairstyles
            'kosichki_girls': getattr(settings, 'CHAT_ID5', None),            # @KOSICHKI_GIRLS
            'fashion_couture_ru': getattr(settings, 'CHAT_ID6', None),        # @Fashion_Couture_ru
            'posecretulive': getattr(settings, 'CHAT_ID7', None),             # @posecretulive
            'lukinterlab_news': getattr(settings, 'CHAT_ID8', None),          # @LukInterLab_News
            'nlpnlpnlpnlpnlpp': getattr(settings, 'CHAT_ID9', None),          # @nlpnlpnlpnlpnlpp
            'chtotopropsy': getattr(settings, 'CHAT_ID10', None),             # @chtotopropsy
            'magicstudyy': getattr(settings, 'CHAT_ID11', None),              # @magicstudyy
            'tarolives': getattr(settings, 'CHAT_ID12', None),                # @tarolives
            'matrizalive': getattr(settings, 'CHAT_ID13', None),              # @matrizalive
            'posecretulive_2': getattr(settings, 'CHAT_ID14', None),          # @posecretulive (дубль)
            'meikapps': getattr(settings, 'CHAT_ID15', None),                 # @Meikapps
            'little_mommys_ru': getattr(settings, 'CHAT_ID16', None),         # @Little_mommys_ru
            'lapabеbi': getattr(settings, 'CHAT_ID17', None),                 # @LapaBebi
            'lackomca': getattr(settings, 'CHAT_ID18', None),                 # @Lackomca
        }
        
        # Категоризация каналов
        self.channel_categories = {
            'beauty': ['fizkult_hello_beauty', 'meikapps'],
            'lifestyle': ['eat_love_live', 'posecretulive', 'posecretulive_2'],
            'hair': ['the_best_hairstyles', 'kosichki_girls'],
            'fashion': ['fashion_couture_ru'],
            'family': ['little_mommys_ru', 'lapabеbi'],
            'psychology': ['chtotopropsy', 'nlpnlpnlpnlpnlpp'],
            'mysticism': ['tarolives', 'matrizalive'],
            'education': ['magicstudyy'],
            'news': ['lukinterlab_news'],
            'food': ['lackomca'],
            'main': ['ideal_image_ru'],
        }
    
    def get_telegram_platform(self):
        """Получить или создать платформу Telegram"""
        platform, created = SocialPlatform.objects.get_or_create(
            name='telegram',
            defaults={
                'is_active': True,
                'icon_class': 'fab fa-telegram',
            }
        )
        return platform
    
    def sync_channels_to_db(self):
        """
        Синхронизирует все 18 каналов с базой данных
        """
        platform = self.get_telegram_platform()
        synced_count = 0
        
        channel_info = {
            'fizkult_hello_beauty': ('Красота и здоровье', 'beauty', 'https://t.me/fizkult_hello_beauty'),
            'eat_love_live': ('Здоровый образ жизни', 'lifestyle', 'https://t.me/eat_love_live'),
            'ideal_image_ru': ('IdealImage.ru - Главный', 'beauty', 'https://t.me/ideal_image_ru'),
            'the_best_hairstyles': ('Лучшие прически', 'beauty', 'https://t.me/the_best_hairstyles'),
            'kosichki_girls': ('Косы для девочек', 'beauty', 'https://t.me/KOSICHKI_GIRLS'),
            'fashion_couture_ru': ('Мода и стиль', 'fashion', 'https://t.me/Fashion_Couture_ru'),
            'posecretulive': ('По секрету', 'lifestyle', 'https://t.me/posecretulive'),
            'lukinterlab_news': ('Новости', 'lifestyle', 'https://t.me/LukInterLab_News'),
            'nlpnlpnlpnlpnlpp': ('NLP', 'psychology', 'https://t.me/nlpnlpnlpnlpnlpp'),
            'chtotopropsy': ('Психология', 'psychology', 'https://t.me/chtotopropsy'),
            'magicstudyy': ('Магическое обучение', 'other', 'https://t.me/magicstudyy'),
            'tarolives': ('Таро', 'other', 'https://t.me/tarolives'),
            'matrizalive': ('Матрица судьбы', 'other', 'https://t.me/matrizalive'),
            'posecretulive_2': ('По секрету (2)', 'lifestyle', 'https://t.me/posecretulive'),
            'meikapps': ('Макияж', 'beauty', 'https://t.me/Meikapps'),
            'little_mommys_ru': ('Мамы', 'family', 'https://t.me/Little_mommys_ru'),
            'lapabеbi': ('Дети', 'family', 'https://t.me/LapaBebi'),
            'lackomca': ('Сладости', 'lifestyle', 'https://t.me/Lackomca'),
        }
        
        for key, channel_id in self.all_channels.items():
            if channel_id:
                name, ch_type, url = channel_info.get(key, (key, 'other', ''))
                
                channel, created = SocialChannel.objects.get_or_create(
                    platform=platform,
                    channel_id=channel_id,
                    defaults={
                        'channel_name': name,
                        'channel_type': ch_type,
                        'channel_url': url,
                        'is_active': True,
                    }
                )
                
                if created:
                    synced_count += 1
                    logger.info(f"✅ Синхронизирован канал: {name} ({channel_id})")
        
        logger.info(f"📊 Всего синхронизировано каналов: {synced_count}")
        return synced_count
    
    def publish_to_channel(self, channel_id, post, image_url=None, custom_text=None):
        """
        Публикует статью в конкретный Telegram канал
        
        Args:
            channel_id: ID канала (@ideal_image_ru или числовой ID)
            post: Объект blog.Post
            image_url: URL изображения (опционально)
            custom_text: Кастомный текст (иначе генерируется автоматически)
        
        Returns:
            dict: {'success': bool, 'message_id': int, 'error': str}
        """
        if not self.bot_token:
            logger.warning("⚠️ Telegram bot token не настроен")
            return {'success': False, 'error': 'Bot token not configured'}

        try:
            if custom_text:
                announcement_text = custom_text
            else:
                announcement_text = f"""
📝 <b>{post.title}</b>

{post.description[:400] if post.description else post.content[:400]}...

👉 <a href="{settings.SITE_URL}{post.get_absolute_url()}">Читать полностью на IdealImage.ru</a>

#IdealImage #красота #мода #стиль
"""

            if image_url:
                sent = self.client.send_photo(
                    channel_id,
                    image_url,
                    caption=announcement_text,
                    parse_mode='HTML'
                )
            else:
                sent = self.client.send_message(
                    channel_id,
                    announcement_text,
                    parse_mode='HTML',
                    disable_web_page_preview=False
                )

            if not sent:
                logger.error("Telegram API error при публикации в %s", channel_id)
                return {'success': False, 'error': 'Telegram API error'}

            logger.info(f"✅ Telegram: опубликовано в {channel_id}")

            return {
                'success': True,
                'platform': 'telegram',
                'channel_id': channel_id,
            }

        except Exception as e:
            logger.error(f"❌ Ошибка публикации в Telegram: {e}")
            return {'success': False, 'error': str(e)}
    
    def publish_to_db_channel(self, channel_obj, post, image_url=None):
        """
        Публикует статью в канал из БД и сохраняет результат
        
        Args:
            channel_obj: Объект SocialChannel
            post: Объект blog.Post
            image_url: URL изображения
        
        Returns:
            PostPublication object
        """
        # Дедупликация: если уже публиковали пост с таким же названием в этот канал — пропускаем
        try:
            if PostPublication.objects.filter(
                channel=channel_obj,
                post__title=post.title,
                status='published'
            ).exists():
                logger.info(f"🔁 Пропуск: уже опубликовано в {channel_obj.channel_id} — '{post.title}'")
                # Возвращаем квазирезультат без создания новой записи
                dummy = PostPublication(
                    post=post,
                    channel=channel_obj,
                    status='published'
                )
                dummy.id = 0
                return dummy
        except Exception:
            pass

        # Создаём запись о публикации
        publication = PostPublication.objects.create(
            post=post,
            channel=channel_obj,
            status='publishing',
            scheduled_at=timezone.now()
        )
        
        try:
            # Публикуем
            result = self.publish_to_channel(
                channel_obj.channel_id,
                post,
                image_url=image_url
            )
            
            if result['success']:
                publication.status = 'published'
                publication.published_at = timezone.now()
                publication.platform_post_id = str(result.get('message_id', ''))
                publication.platform_url = result.get('url', '')
                publication.post_content = result.get('text', '')
                logger.info(f"✅ Публикация сохранена в БД: {publication.id}")
            else:
                publication.status = 'failed'
                publication.error_log = result.get('error', 'Unknown error')
                logger.error(f"❌ Ошибка публикации: {result.get('error')}")
            
            publication.save()
            
        except Exception as e:
            publication.status = 'failed'
            publication.error_log = str(e)
            publication.save()
            logger.error(f"❌ Исключение при публикации: {e}")
        
        return publication
    
    def publish_to_multiple_channels(self, post, channels=None, image_url=None):
        """
        Публикует статью в несколько каналов
        
        Args:
            post: Объект blog.Post
            channels: List[str] - список ключей каналов из self.all_channels
                     None = все активные каналы из БД
            image_url: URL изображения
        
        Returns:
            dict: {channel_id: result}
        """
        results = {}
        
        if channels is None:
            # Получаем все активные Telegram каналы из БД
            platform = self.get_telegram_platform()
            channel_objects = SocialChannel.objects.filter(
                platform=platform,
                is_active=True
            )
        else:
            # Публикуем в указанные каналы
            channel_ids = [self.all_channels.get(ch) for ch in channels if self.all_channels.get(ch)]
            platform = self.get_telegram_platform()
            channel_objects = SocialChannel.objects.filter(
                platform=platform,
                channel_id__in=channel_ids,
                is_active=True
            )
        
        for channel_obj in channel_objects:
            publication = self.publish_to_db_channel(channel_obj, post, image_url)
            results[channel_obj.channel_id] = {
                'success': publication.status == 'published',
                'publication_id': publication.id,
                'error': publication.error_log if publication.status == 'failed' else None
            }
        
        successful = sum(1 for r in results.values() if r.get('success'))
        logger.info(f"📊 Telegram: опубликовано в {successful}/{len(results)} каналов")
        
        return results
    
    def select_channels_by_category(self, post):
        """
        Умный выбор каналов на основе категории статьи
        
        Args:
            post: Объект blog.Post
        
        Returns:
            list: Список ключей каналов для публикации
        """
        selected_channels = []
        
        # Всегда публикуем в главный канал
        selected_channels.append('ideal_image_ru')
        
        # Определяем категорию статьи
        category_name = post.category.title.lower() if post.category else ''
        
        # Маппинг категорий на каналы
        if 'красот' in category_name or 'макияж' in category_name:
            selected_channels.extend(['fizkult_hello_beauty', 'meikapps'])
        
        if 'волос' in category_name or 'причес' in category_name or 'косы' in category_name or 'коса' in category_name:
            selected_channels.extend(['the_best_hairstyles', 'kosichki_girls'])
        
        if 'мод' in category_name or 'стиль' in category_name or 'одежд' in category_name:
            selected_channels.append('fashion_couture_ru')
        
        if 'здоров' in category_name or 'фитнес' in category_name or 'питан' in category_name:
            selected_channels.extend(['eat_love_live', 'fizkult_hello_beauty'])
        
        if 'психолог' in category_name or 'отношен' in category_name:
            selected_channels.extend(['chtotopropsy', 'posecretulive'])
        
        if 'дет' in category_name or 'мам' in category_name or 'семь' in category_name:
            selected_channels.extend(['little_mommys_ru', 'lapabеbi'])
        
        if 'таро' in category_name or 'астролог' in category_name or 'гороскоп' in category_name:
            selected_channels.extend(['tarolives', 'matrizalive'])
        
        if 'рецепт' in category_name or 'еда' in category_name or 'кулинар' in category_name:
            selected_channels.append('lackomca')
        
        # Убираем дубликаты
        selected_channels = list(set(selected_channels))
        
        logger.info(f"🎯 Выбрано каналов для '{post.title}': {len(selected_channels)}")
        logger.info(f"   Каналы: {', '.join(selected_channels)}")
        
        return selected_channels
    
    def get_channel_statistics(self, channel_id):
        """
        Получает статистику канала через Telegram API
        
        Args:
            channel_id: ID канала
        
        Returns:
            dict: {subscribers: int, ...}
        """
        try:
            # ИСПРАВЛЕНО: Используем getChatMemberCount для получения количества подписчиков
            # Этот метод работает для каналов где бот - администратор
            count_response = self.client.send_request('getChatMemberCount', {'chat_id': channel_id})
            
            subscribers = 0
            if count_response and count_response.get('ok'):
                subscribers = count_response.get('result', 0)
                logger.info(f"✅ Получено подписчиков для {channel_id}: {subscribers}")
            else:
                description = count_response.get('description') if count_response else 'нет ответа'
                logger.warning(f"⚠️ Не удалось получить количество подписчиков: {description}")
            
            info_response = self.client.send_request('getChat', {'chat_id': channel_id})
            
            result_dict = {'subscribers': subscribers}
            
            if info_response and info_response.get('ok'):
                chat_info = info_response.get('result', {})
                result_dict.update({
                    'title': chat_info.get('title', ''),
                    'username': chat_info.get('username', ''),
                    'description': chat_info.get('description', ''),
                    'type': chat_info.get('type', ''),
                })
            
            return result_dict
                
        except Exception as e:
            logger.error(f"❌ Исключение при получении статистики: {e}")
            return {'subscribers': 0}
    
    def update_all_channels_statistics(self):
        """
        Обновляет статистику для всех каналов в БД
        """
        platform = self.get_telegram_platform()
        channels = SocialChannel.objects.filter(platform=platform, is_active=True)
        
        updated = 0
        for channel in channels:
            stats = self.get_channel_statistics(channel.channel_id)
            if stats:
                channel.subscribers_count = stats.get('subscribers', 0)
                channel.save(update_fields=['subscribers_count'])
                updated += 1
                logger.info(f"📊 Обновлена статистика: {channel.channel_name} - {stats['subscribers']} подписчиков")
        
        logger.info(f"✅ Статистика обновлена для {updated} каналов")
        return updated


# Convenience function
def get_telegram_manager():
    """Возвращает экземпляр TelegramChannelManager"""
    return TelegramChannelManager()

