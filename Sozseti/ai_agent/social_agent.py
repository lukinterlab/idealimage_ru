"""
Social Media AI Agent - AI-агент для управления публикациями в соцсетях
"""
import logging
import json
from django.conf import settings
from django.utils import timezone
from ..models import SocialChannel, PostPublication, PublicationSchedule
from ..api_integrations.telegram_manager import TelegramChannelManager
from ..api_integrations.vk_manager import VKManager
from ..api_integrations.rutube_manager import RutubeManager
from ..api_integrations.dzen_manager import DzenManager


logger = logging.getLogger(__name__)


class SocialMediaAgent:
    """
    AI-агент для интеллектуального управления социальными сетями
    """
    
    def __init__(self):
        """Инициализация агента"""
        self.telegram = TelegramChannelManager()
        self.vk = VKManager()
        self.rutube = RutubeManager()
        self.dzen = DzenManager()
    
    def distribute_post(self, post, strategy='auto'):
        """
        AI решает в какие каналы постить статью
        
        Args:
            post: Объект blog.Post
            strategy: Стратегия распределения
                - 'auto': автоматический выбор по категории
                - 'all': во все активные каналы
                - 'main': только в главные каналы
        
        Returns:
            dict: {platform: [channels]}
        """
        logger.info(f"[*] AI распределяет статью: {post.title}")
        logger.info(f"    Стратегия: {strategy}")
        
        distribution = {
            'telegram': [],
            'vk': [],
            'rutube': [],
            'dzen': [],
        }
        
        # Telegram - умный выбор каналов
        if strategy == 'auto':
            telegram_channels = self.telegram.select_channels_by_category(post)
            distribution['telegram'] = telegram_channels
        elif strategy == 'all':
            # Все активные Telegram каналы
            platform = self.telegram.get_telegram_platform()
            all_channels = SocialChannel.objects.filter(
                platform=platform,
                is_active=True
            ).values_list('channel_id', flat=True)
            distribution['telegram'] = list(all_channels)
        elif strategy == 'main':
            # Только главный канал
            distribution['telegram'] = ['ideal_image_ru']
        
        # VK - если настроен
        if self.vk.access_token:
            distribution['vk'] = ['main']
        
        # Rutube - если настроен
        if self.rutube.api_key:
            distribution['rutube'] = ['main']
        
        # Dzen - если настроен
        if self.dzen.token:
            distribution['dzen'] = ['main']
        
        logger.info(f"[OK] Распределение готово:")
        for platform, channels in distribution.items():
            if channels:
                logger.info(f"     {platform}: {len(channels)} каналов")
        
        return distribution
    
    def optimize_posting_time(self, channel, post):
        """
        AI определяет лучшее время публикации на основе статистики
        
        Args:
            channel: Объект SocialChannel
            post: Объект blog.Post
        
        Returns:
            datetime: Оптимальное время публикации
        """
        from datetime import datetime, timedelta
        
        logger.info(f"[*] AI оптимизирует время публикации для {channel.channel_name}")
        
        # Анализируем историю публикаций
        recent_publications = PostPublication.objects.filter(
            channel=channel,
            status='published',
            published_at__gte=timezone.now() - timedelta(days=30)
        ).order_by('-engagement_score')[:20]
        
        if recent_publications.exists():
            # Находим наиболее успешные часы
            best_hours = {}
            
            for pub in recent_publications:
                hour = pub.published_at.hour
                if hour not in best_hours:
                    best_hours[hour] = []
                best_hours[hour].append(pub.engagement_score)
            
            # Вычисляем средний engagement для каждого часа
            avg_engagement = {
                hour: sum(scores) / len(scores)
                for hour, scores in best_hours.items()
            }
            
            # Находим лучший час
            best_hour = max(avg_engagement, key=avg_engagement.get)
            
            logger.info(f"[OK] Оптимальное время: {best_hour}:00")
            logger.info(f"     Средний engagement в этот час: {avg_engagement[best_hour]:.2f}")
            
            # Возвращаем следующее вхождение этого часа
            now = timezone.now()
            optimal_time = now.replace(hour=best_hour, minute=0, second=0, microsecond=0)
            
            if optimal_time < now:
                optimal_time += timedelta(days=1)
            
            return optimal_time
        else:
            # Нет истории - используем стандартное время (14:00)
            logger.info("[INFO] Нет истории публикаций, использую стандартное время: 14:00")
            
            now = timezone.now()
            optimal_time = now.replace(hour=14, minute=0, second=0, microsecond=0)
            
            if optimal_time < now:
                optimal_time += timedelta(days=1)
            
            return optimal_time
    
    def generate_post_content(self, post, platform_name):
        """
        AI адаптирует контент статьи под конкретную платформу
        
        Args:
            post: Объект blog.Post
            platform_name: Название платформы (telegram, vk, pinterest, etc.)
        
        Returns:
            str: Адаптированный текст
        """
        logger.info(f"[*] AI адаптирует контент для {platform_name}")
        
        # Базовый URL статьи
        article_url = f"{settings.SITE_URL}{post.get_absolute_url()}"
        
        # Шаблоны для разных платформ
        templates = {
            'telegram': f"""
<b>{post.title}</b>

{post.description[:400] if post.description else post.content[:400]}...

<a href="{article_url}">Читать полностью на IdealImage.ru</a>

#IdealImage #красота #мода
""",
            'vk': f"""
{post.title}

{post.description[:500] if post.description else post.content[:500]}...

Читать полностью: {article_url}

#красота #мода #стиль #IdealImage #женскийжурнал
""",
            'pinterest': f"""
{post.title}

{post.description[:450] if post.description else post.content[:450]}

Подробнее: {article_url}
""",
            'rutube': f"""
{post.title}

{post.description[:300] if post.description else post.content[:300]}

Читать на IdealImage.ru: {article_url}
""",
            'dzen': f"""
<h2>{post.title}</h2>

<p>{post.content[:800]}</p>

<p><a href="{article_url}">Читать полностью на IdealImage.ru</a></p>
""",
        }
        
        content = templates.get(platform_name, templates['telegram'])
        
        logger.info(f"[OK] Контент адаптирован для {platform_name} ({len(content)} символов)")
        
        return content
    
    def respond_to_comment(self, comment):
        """
        AI отвечает на комментарий в соцсети
        
        Args:
            comment: Объект SocialComment
        
        Returns:
            str: Текст ответа
        """
        logger.info("[INFO] AI генерация ответа на комментарий (в разработке)")
        
        # TODO: Интеграция с GigaChat для генерации умных ответов
        # Пока заглушка
        
        return "Спасибо за комментарий!"
    
    def monitor_conversations(self):
        """
        AI мониторит все переписки в соцсетях
        
        Returns:
            dict: Статистика мониторинга
        """
        from ..models import SocialConversation
        
        logger.info("[*] AI мониторит переписки...")
        
        # Получаем активные переписки
        active_conversations = SocialConversation.objects.filter(
            status='active',
            ai_responded=False
        )
        
        logger.info(f"[INFO] Найдено {active_conversations.count()} непрочитанных переписок")
        
        # TODO: Автоматические ответы через GigaChat
        
        return {
            'active': active_conversations.count(),
            'needs_admin': active_conversations.filter(needs_admin=True).count()
        }
    
    def suggest_improvements(self, channel):
        """
        AI анализирует канал и предлагает улучшения
        
        Args:
            channel: Объект SocialChannel
        
        Returns:
            dict: Рекомендации
        """
        from django.db.models import Avg
        
        logger.info(f"[*] AI анализирует канал: {channel.channel_name}")
        
        suggestions = {
            'channel': channel.channel_name,
            'recommendations': []
        }
        
        # Анализ частоты публикаций
        from datetime import timedelta
        week_ago = timezone.now() - timedelta(days=7)
        
        weekly_posts = PostPublication.objects.filter(
            channel=channel,
            published_at__gte=week_ago,
            status='published'
        ).count()
        
        if weekly_posts < 3:
            suggestions['recommendations'].append({
                'type': 'frequency',
                'message': 'Рекомендуется увеличить частоту публикаций до 3-5 постов в неделю',
                'priority': 'high'
            })
        
        # Анализ вовлечённости
        avg_engagement = PostPublication.objects.filter(
            channel=channel,
            status='published'
        ).aggregate(avg=Avg('engagement_score'))['avg']
        
        if avg_engagement and avg_engagement < 1.0:
            suggestions['recommendations'].append({
                'type': 'engagement',
                'message': 'Низкая вовлечённость. Попробуйте более интерактивный контент',
                'priority': 'medium'
            })
        
        # Анализ времени публикаций
        optimal_time = self.optimize_posting_time(channel, None)
        suggestions['optimal_posting_time'] = optimal_time.strftime('%H:%M')
        
        logger.info(f"[OK] Сгенерировано {len(suggestions['recommendations'])} рекомендаций")
        
        return suggestions
    
    def plan_ad_campaign(self, budget, goal, platforms=None):
        """
        AI планирует рекламную кампанию
        
        Args:
            budget: Бюджет в рублях
            goal: Цель (subscribers/traffic/engagement)
            platforms: Список платформ или None для автовыбора
        
        Returns:
            dict: План кампании
        """
        logger.info(f"[*] AI планирует рекламную кампанию: {budget} руб., цель: {goal}")
        
        campaign_plan = {
            'budget': budget,
            'goal': goal,
            'platforms': {},
            'recommendations': []
        }
        
        # Распределение бюджета по платформам
        if platforms is None or 'telegram' in platforms:
            campaign_plan['platforms']['telegram'] = {
                'budget': budget * 0.4,  # 40% на Telegram
                'strategy': 'Продвижение постов в каналах',
            }
        
        if platforms is None or 'vk' in platforms:
            campaign_plan['platforms']['vk'] = {
                'budget': budget * 0.35,  # 35% на VK
                'strategy': 'VK Ads таргетированная реклама',
            }
        
        if platforms is None or 'dzen' in platforms:
            campaign_plan['platforms']['dzen'] = {
                'budget': budget * 0.25,  # 25% на Дзен
                'strategy': 'Продвижение статей в рекомендациях',
            }
        
        campaign_plan['recommendations'].append({
            'type': 'targeting',
            'message': 'Рекомендуемая аудитория: женщины 18-45, интересы: красота, мода, здоровье'
        })
        
        campaign_plan['recommendations'].append({
            'type': 'duration',
            'message': f'Рекомендуемая длительность: {max(7, int(budget / 500))} дней'
        })
        
        logger.info(f"[OK] План кампании готов для {len(campaign_plan['platforms'])} платформ")
        
        return campaign_plan


def get_social_agent():
    """Возвращает экземпляр SocialMediaAgent"""
    return SocialMediaAgent()

