"""
Интеграция системы рекламы с AI-агентом
"""
import logging
from django.utils import timezone
from django.db.models import Q
from .models import ContextAd, AdInsertion
from blog.models import Post

logger = logging.getLogger(__name__)


class AdAIIntegration:
    """Класс для интеграции рекламы с AI-агентом"""
    
    @staticmethod
    def insert_context_ads_in_article(article_id, context_ads=None):
        """
        Вставить контекстную рекламу в статью
        
        Args:
            article_id: ID статьи
            context_ads: Список объектов ContextAd (если None - выбираются автоматически)
        
        Returns:
            dict: Результат операции
        """
        try:
            post = Post.objects.get(id=article_id)
        except Post.DoesNotExist:
            return {
                'success': False,
                'error': f'Статья с ID {article_id} не найдена'
            }
        
        # Если не указаны объявления - выбираем автоматически
        if context_ads is None:
            context_ads = ContextAd.objects.filter(
                is_active=True,
                campaign__is_active=True
            ).select_related('campaign').order_by('-priority')[:10]
        
        if not context_ads:
            return {
                'success': False,
                'error': 'Нет активных контекстных объявлений'
            }
        
        content = post.content
        insertions_made = []
        
        for ad in context_ads:
            # Проверяем лимит вставок на статью
            existing_insertions = AdInsertion.objects.filter(
                post=post,
                context_ad=ad,
                is_active=True
            ).count()
            
            if existing_insertions >= ad.max_insertions_per_article:
                continue
            
            # Ищем ключевую фразу в тексте
            if ad.keyword_phrase.lower() in content.lower():
                # Создаем запись о вставке
                insertion = AdInsertion.objects.create(
                    context_ad=ad,
                    post=post,
                    inserted_by='AI',
                    insertion_position=content.lower().find(ad.keyword_phrase.lower()),
                    anchor_text_used=ad.anchor_text
                )
                
                insertions_made.append({
                    'ad_id': ad.id,
                    'keyword': ad.keyword_phrase,
                    'anchor_text': ad.anchor_text,
                    'insertion_id': insertion.id
                })
                
                logger.info(f"AI вставил рекламу '{ad.anchor_text}' в статью '{post.title}'")
        
        return {
            'success': True,
            'insertions_count': len(insertions_made),
            'insertions': insertions_made
        }
    
    @staticmethod
    def bulk_insert_context_ads(filters):
        """
        Массовая вставка контекстной рекламы в статьи
        
        Args:
            filters: dict с параметрами фильтрации статей
                - category_id: ID категории
                - author_id: ID автора
                - date_from: дата от
                - date_to: дата до
                - exclude_posts: список ID статей для исключения
        
        Returns:
            dict: Результат операции
        """
        # Формируем запрос для статей
        posts_query = Post.objects.filter(status='published')
        
        if filters.get('category_id'):
            posts_query = posts_query.filter(category_id=filters['category_id'])
        
        if filters.get('author_id'):
            posts_query = posts_query.filter(author_id=filters['author_id'])
        
        if filters.get('date_from'):
            posts_query = posts_query.filter(created__gte=filters['date_from'])
        
        if filters.get('date_to'):
            posts_query = posts_query.filter(created__lte=filters['date_to'])
        
        if filters.get('exclude_posts'):
            posts_query = posts_query.exclude(id__in=filters['exclude_posts'])
        
        posts = posts_query[:100]  # Ограничение на 100 статей за раз
        
        total_insertions = 0
        processed_posts = 0
        errors = []
        
        for post in posts:
            result = AdAIIntegration.insert_context_ads_in_article(post.id)
            
            if result['success']:
                total_insertions += result['insertions_count']
                processed_posts += 1
            else:
                errors.append({
                    'post_id': post.id,
                    'error': result['error']
                })
        
        return {
            'success': True,
            'processed_posts': processed_posts,
            'total_insertions': total_insertions,
            'errors': errors
        }
    
    @staticmethod
    def remove_expired_context_ads():
        """
        Удалить просроченные контекстные объявления
        
        Returns:
            dict: Результат операции
        """
        today = timezone.now().date()
        
        # Находим просроченные вставки
        expired_insertions = AdInsertion.objects.filter(
            is_active=True,
            context_ad__insertion_type='temporary',
            context_ad__expire_date__lt=today
        )
        
        count = expired_insertions.count()
        
        # Деактивируем вставки
        expired_insertions.update(
            is_active=False,
            removed_at=timezone.now(),
            removal_reason='Истек срок действия'
        )
        
        logger.info(f"AI удалил {count} просроченных рекламных вставок")
        
        return {
            'success': True,
            'removed_count': count
        }
    
    @staticmethod
    def get_active_context_ads_for_new_article(content, category=None):
        """
        Получить подходящие контекстные объявления для новой статьи
        
        Args:
            content: текст статьи
            category: категория статьи (опционально)
        
        Returns:
            list: Список подходящих объявлений
        """
        # Получаем активные объявления
        ads = ContextAd.objects.filter(
            is_active=True,
            campaign__is_active=True
        ).select_related('campaign').order_by('-priority')
        
        suitable_ads = []
        
        for ad in ads:
            # Проверяем, есть ли ключевая фраза в тексте
            if ad.keyword_phrase.lower() in content.lower():
                suitable_ads.append(ad)
                
                # Ограничиваем количество
                if len(suitable_ads) >= 5:
                    break
        
        return suitable_ads
    
    @staticmethod
    def auto_insert_ads_in_new_article(post_id):
        """
        Автоматическая вставка рекламы в новую статью при публикации
        
        Args:
            post_id: ID статьи
        
        Returns:
            dict: Результат операции
        """
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            return {
                'success': False,
                'error': 'Статья не найдена'
            }
        
        # Получаем подходящие объявления
        suitable_ads = AdAIIntegration.get_active_context_ads_for_new_article(
            post.content,
            post.category
        )
        
        if not suitable_ads:
            return {
                'success': True,
                'insertions_count': 0,
                'message': 'Подходящих объявлений не найдено'
            }
        
        # Вставляем рекламу
        result = AdAIIntegration.insert_context_ads_in_article(
            post_id,
            suitable_ads
        )
        
        return result

