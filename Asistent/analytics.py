"""
Модуль аналитики и метрик для AI-ассистента
"""
from django.db.models import Avg, Count, Sum, Q
from django.utils import timezone
from datetime import timedelta, datetime
from .models import AIGeneratedArticle, AISchedule
from blog.models import Post
from django.contrib.auth.models import User


class AIMetricsDashboard:
    """Dashboard для мониторинга метрик AI-ассистента"""
    
    def __init__(self):
        """Инициализация с определением AI пользователя"""
        try:
            self.ai_user = User.objects.get(username='ai_assistant')
        except User.DoesNotExist:
            self.ai_user = None
    
    def get_daily_stats(self):
        """
        Получить статистику за сегодня
        
        Returns:
            dict: Статистика за текущий день
        """
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = timezone.now()
        
        # Количество статей сгенерированных сегодня
        today_articles = AIGeneratedArticle.objects.filter(
            created_at__gte=today_start,
            created_at__lte=today_end
        )
        
        generated_count = today_articles.count()
        
        # Среднее время генерации
        avg_time_data = today_articles.aggregate(avg_time=Avg('generation_time_seconds'))
        avg_time = avg_time_data['avg_time'] or 0
        
        # Форматируем время
        if avg_time > 0:
            minutes = int(avg_time // 60)
            seconds = int(avg_time % 60)
            avg_generation_time = f"{minutes} мин {seconds} сек"
        else:
            avg_generation_time = "N/A"
        
        # Success rate (статьи с успешной публикацией)
        published_count = today_articles.filter(
            article__status='published'
        ).count()
        
        if generated_count > 0:
            success_rate = round((published_count / generated_count) * 100, 1)
        else:
            success_rate = 0
        
        # Средняя длина статей (в словах)
        if self.ai_user:
            today_posts = Post.objects.filter(
                author=self.ai_user,
                created__gte=today_start,
                created__lte=today_end
            )
            
            total_words = 0
            posts_count = today_posts.count()
            
            if posts_count > 0:
                for post in today_posts:
                    # Подсчет слов в контенте
                    import re
                    clean_text = re.sub(r'<[^>]+>', ' ', post.content)
                    words = len(clean_text.split())
                    total_words += words
                
                avg_words = round(total_words / posts_count)
            else:
                avg_words = 0
        else:
            avg_words = 0
        
        # Общее количество API вызовов
        total_api_calls = today_articles.aggregate(
            total_calls=Sum('api_calls_count')
        )['total_calls'] or 0
        
        return {
            'generated_today': generated_count,
            'avg_generation_time': avg_generation_time,
            'avg_generation_time_raw': int(avg_time),
            'success_rate': success_rate,
            'avg_word_count': avg_words,
            'total_api_calls': total_api_calls,
            'published_count': published_count,
        }
    
    def get_quality_metrics(self):
        """
        Получить метрики качества контента AI
        
        Returns:
            dict: Метрики качества
        """
        if not self.ai_user:
            return self._empty_quality_metrics()
        
        # Все AI статьи
        ai_posts = Post.objects.filter(author=self.ai_user, status='published')
        total_ai_posts = ai_posts.count()
        
        if total_ai_posts == 0:
            return self._empty_quality_metrics()
        
        # Средние просмотры
        avg_views = ai_posts.aggregate(avg=Avg('views'))['avg'] or 0
        
        # Средние лайки (из модели blog.models_likes)
        from blog.models_likes import Like
        total_likes = Like.objects.filter(post__in=ai_posts).count()
        avg_likes = round(total_likes / total_ai_posts, 1) if total_ai_posts > 0 else 0
        
        # Средние комментарии
        from blog.models import Comment
        total_comments = Comment.objects.filter(
            post__in=ai_posts,
            active=True
        ).count()
        avg_comments = round(total_comments / total_ai_posts, 1) if total_ai_posts > 0 else 0
        
        # Engagement rate: (лайки + комментарии) / просмотры * 100
        total_views = ai_posts.aggregate(total=Sum('views'))['total'] or 0
        if total_views > 0:
            engagement_rate = round(((total_likes + total_comments) / total_views) * 100, 2)
        else:
            engagement_rate = 0
        
        # Средний рейтинг (если есть система рейтингов)
        from blog.models_likes import PostRating
        ratings = PostRating.objects.filter(post__in=ai_posts)
        if ratings.exists():
            avg_rating = round(ratings.aggregate(avg=Avg('rating'))['avg'] or 0, 1)
        else:
            avg_rating = 0
        
        return {
            'total_posts': total_ai_posts,
            'avg_views': round(avg_views, 1),
            'avg_likes': avg_likes,
            'avg_comments': avg_comments,
            'avg_rating': avg_rating,
            'engagement_rate': engagement_rate,
            'total_views': total_views,
            'total_likes': total_likes,
            'total_comments': total_comments,
        }
    
    def compare_ai_vs_human(self):
        """
        Сравнение метрик AI vs живые авторы
        
        Returns:
            dict: Сравнительная статистика
        """
        if not self.ai_user:
            return self._empty_comparison()
        
        # AI статьи
        ai_posts = Post.objects.filter(author=self.ai_user, status='published')
        
        # Статьи живых авторов
        human_posts = Post.objects.filter(status='published').exclude(author=self.ai_user)
        
        # Подсчет метрик для AI
        ai_count = ai_posts.count()
        ai_views = ai_posts.aggregate(avg=Avg('views'), total=Sum('views'))
        
        # Подсчет метрик для авторов
        human_count = human_posts.count()
        human_views = human_posts.aggregate(avg=Avg('views'), total=Sum('views'))
        
        # Лайки
        from blog.models_likes import Like
        ai_likes = Like.objects.filter(post__in=ai_posts).count()
        human_likes = Like.objects.filter(post__in=human_posts).count()
        
        # Комментарии
        from blog.models import Comment
        ai_comments = Comment.objects.filter(post__in=ai_posts, active=True).count()
        human_comments = Comment.objects.filter(post__in=human_posts, active=True).count()
        
        # Средние значения
        ai_avg_likes = round(ai_likes / ai_count, 1) if ai_count > 0 else 0
        human_avg_likes = round(human_likes / human_count, 1) if human_count > 0 else 0
        
        ai_avg_comments = round(ai_comments / ai_count, 1) if ai_count > 0 else 0
        human_avg_comments = round(human_comments / human_count, 1) if human_count > 0 else 0
        
        # Engagement rate
        ai_total_views = ai_views['total'] or 0
        human_total_views = human_views['total'] or 0
        
        if ai_total_views > 0:
            ai_engagement = round(((ai_likes + ai_comments) / ai_total_views) * 100, 2)
        else:
            ai_engagement = 0
        
        if human_total_views > 0:
            human_engagement = round(((human_likes + human_comments) / human_total_views) * 100, 2)
        else:
            human_engagement = 0
        
        # Топ-10 AI статей
        top_ai_posts = ai_posts.order_by('-views')[:10].values(
            'id', 'title', 'views', 'created'
        )
        
        # Топ-10 статей авторов
        top_human_posts = human_posts.order_by('-views')[:10].values(
            'id', 'title', 'views', 'created', 'author__username'
        )
        
        return {
            'ai': {
                'count': ai_count,
                'avg_views': round(ai_views['avg'] or 0, 1),
                'total_views': ai_total_views,
                'avg_likes': ai_avg_likes,
                'total_likes': ai_likes,
                'avg_comments': ai_avg_comments,
                'total_comments': ai_comments,
                'engagement_rate': ai_engagement,
            },
            'human': {
                'count': human_count,
                'avg_views': round(human_views['avg'] or 0, 1),
                'total_views': human_total_views,
                'avg_likes': human_avg_likes,
                'total_likes': human_likes,
                'avg_comments': human_avg_comments,
                'total_comments': human_comments,
                'engagement_rate': human_engagement,
            },
            'top_ai_posts': list(top_ai_posts),
            'top_human_posts': list(top_human_posts),
        }
    
    def get_schedule_performance(self):
        """
        Получить производительность по расписаниям
        
        Returns:
            dict: Статистика по расписаниям
        """
        schedules = AISchedule.objects.all()
        
        schedule_stats = []
        
        for schedule in schedules:
            # Количество сгенерированных статей
            generated = AIGeneratedArticle.objects.filter(schedule=schedule)
            total_generated = generated.count()
            
            # Количество опубликованных
            published = generated.filter(article__status='published').count()
            
            # Success rate
            if total_generated > 0:
                success_rate = round((published / total_generated) * 100, 1)
            else:
                success_rate = 0
            
            # Среднее время генерации
            avg_time = generated.aggregate(avg=Avg('generation_time_seconds'))['avg'] or 0
            
            # Последний запуск
            last_run = schedule.last_run
            next_run = schedule.next_run
            
            # Средние просмотры статей из этого расписания
            if published > 0:
                posts = Post.objects.filter(
                    id__in=generated.values_list('article_id', flat=True),
                    status='published'
                )
                avg_views = posts.aggregate(avg=Avg('views'))['avg'] or 0
            else:
                avg_views = 0
            
            schedule_stats.append({
                'id': schedule.id,
                'name': schedule.name,
                'frequency': schedule.get_posting_frequency_display(),
                'is_active': schedule.is_active,
                'total_generated': total_generated,
                'published': published,
                'success_rate': success_rate,
                'avg_generation_time': int(avg_time),
                'avg_views': round(avg_views, 1),
                'last_run': last_run,
                'next_run': next_run,
                'category': schedule.category.title if schedule.category else 'N/A',
            })
        
        # Сортируем по количеству сгенерированных статей
        schedule_stats.sort(key=lambda x: x['total_generated'], reverse=True)
        
        # Лучшее и худшее расписание (по success rate)
        active_schedules = [s for s in schedule_stats if s['total_generated'] > 0]
        
        if active_schedules:
            best_schedule = max(active_schedules, key=lambda x: x['success_rate'])
            worst_schedule = min(active_schedules, key=lambda x: x['success_rate'])
        else:
            best_schedule = None
            worst_schedule = None
        
        return {
            'schedules': schedule_stats,
            'total_schedules': len(schedule_stats),
            'active_schedules': sum(1 for s in schedule_stats if s['is_active']),
            'best_schedule': best_schedule,
            'worst_schedule': worst_schedule,
        }
    
    def get_cost_analysis(self):
        """
        Анализ затрат на AI генерацию
        
        Returns:
            dict: Анализ стоимости и ROI
        """
        # Всего сгенерированных статей
        total_articles = AIGeneratedArticle.objects.count()
        
        # Всего API вызовов
        total_api_calls = AIGeneratedArticle.objects.aggregate(
            total=Sum('api_calls_count')
        )['total'] or 0
        
        # Примерная стоимость (условно: 1 токен = 0.0001 руб, средний запрос = 1000 токенов)
        # Это примерные расчеты, нужно заменить на реальные из API
        TOKENS_PER_CALL = 1500  # Средний промпт + ответ
        COST_PER_1K_TOKENS = 0.10  # руб (для GigaChat Pro)
        
        estimated_cost = (total_api_calls * TOKENS_PER_CALL / 1000) * COST_PER_1K_TOKENS
        
        # Стоимость одной статьи от живого автора (условно)
        AUTHOR_COST_PER_ARTICLE = 500  # руб
        
        # Экономия
        savings = (total_articles * AUTHOR_COST_PER_ARTICLE) - estimated_cost
        
        # ROI
        if estimated_cost > 0:
            roi = round((savings / estimated_cost) * 100, 1)
        else:
            roi = 0
        
        # Стоимость за последние 30 дней
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_articles = AIGeneratedArticle.objects.filter(
            created_at__gte=thirty_days_ago
        )
        recent_count = recent_articles.count()
        recent_api_calls = recent_articles.aggregate(
            total=Sum('api_calls_count')
        )['total'] or 0
        
        recent_cost = (recent_api_calls * TOKENS_PER_CALL / 1000) * COST_PER_1K_TOKENS
        
        return {
            'total_articles': total_articles,
            'total_api_calls': total_api_calls,
            'estimated_cost': round(estimated_cost, 2),
            'cost_per_article': round(estimated_cost / total_articles, 2) if total_articles > 0 else 0,
            'author_cost_equivalent': total_articles * AUTHOR_COST_PER_ARTICLE,
            'savings': round(savings, 2),
            'roi': roi,
            'last_30_days': {
                'articles': recent_count,
                'cost': round(recent_cost, 2),
                'api_calls': recent_api_calls,
            }
        }
    
    def get_trends(self, days=30):
        """
        Получить тренды за указанный период
        
        Args:
            days: Количество дней для анализа
            
        Returns:
            dict: Данные для графиков
        """
        start_date = timezone.now() - timedelta(days=days)
        
        # Генерация статей по дням
        daily_generation = []
        
        for i in range(days):
            day_start = start_date + timedelta(days=i)
            day_end = day_start + timedelta(days=1)
            
            count = AIGeneratedArticle.objects.filter(
                created_at__gte=day_start,
                created_at__lt=day_end
            ).count()
            
            daily_generation.append({
                'date': day_start.strftime('%Y-%m-%d'),
                'count': count
            })
        
        return {
            'daily_generation': daily_generation,
        }
    
    def _empty_quality_metrics(self):
        """Пустые метрики качества"""
        return {
            'total_posts': 0,
            'avg_views': 0,
            'avg_likes': 0,
            'avg_comments': 0,
            'avg_rating': 0,
            'engagement_rate': 0,
            'total_views': 0,
            'total_likes': 0,
            'total_comments': 0,
        }
    
    def _empty_comparison(self):
        """Пустое сравнение"""
        return {
            'ai': {
                'count': 0,
                'avg_views': 0,
                'total_views': 0,
                'avg_likes': 0,
                'total_likes': 0,
                'avg_comments': 0,
                'total_comments': 0,
                'engagement_rate': 0,
            },
            'human': {
                'count': 0,
                'avg_views': 0,
                'total_views': 0,
                'avg_likes': 0,
                'total_likes': 0,
                'avg_comments': 0,
                'total_comments': 0,
                'engagement_rate': 0,
            },
            'top_ai_posts': [],
            'top_human_posts': [],
        }


def get_analytics_data(period_days=30):
    """
    Получить полные аналитические данные для dashboard
    
    Args:
        period_days (int): Количество дней для анализа трендов
        
    Returns:
        dict: Словарь со всеми метриками и статистикой
    """
    dashboard = AIMetricsDashboard()
    
    return {
        'daily_stats': dashboard.get_daily_stats(),
        'quality_metrics': dashboard.get_quality_metrics(),
        'ai_vs_human': dashboard.compare_ai_vs_human(),
        'schedule_performance': dashboard.get_schedule_performance(),
        'cost_analysis': dashboard.get_cost_analysis(),
        'trends': dashboard.get_trends(days=period_days),
    }