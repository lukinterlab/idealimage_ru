"""
Метрики и статистика для расписаний AI
"""
import logging
from typing import Dict
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


def get_horoscope_metrics(days: int = 30) -> Dict:
    """
    Метрики по гороскопам для Dashboard
    
    Args:
        days: За сколько дней собирать статистику
    
    Returns:
        Dict с метриками гороскопов
    """
    from .models import AISchedule, AIScheduleRun
    from Asistent.models import AIGeneratedArticle
    from blog.models import Post
    
    try:
        period_start = timezone.now() - timedelta(days=days)
        
        # Получаем все расписания гороскопов
        horoscope_schedules = AISchedule.objects.filter(
            prompt_template__category='horoscope'
        )
        
        active_schedules = horoscope_schedules.filter(is_active=True).count()
        total_schedules = horoscope_schedules.count()
        
        # Запуски расписаний гороскопов за период
        horoscope_runs = AIScheduleRun.objects.filter(
            schedule__in=horoscope_schedules,
            started_at__gte=period_start
        )
        
        runs_total = horoscope_runs.count()
        runs_success = horoscope_runs.filter(status='success').count()
        runs_failed = horoscope_runs.filter(status='failed').count()
        runs_partial = horoscope_runs.filter(status='partial').count()
        runs_running = horoscope_runs.filter(status='running').count()
        
        # Сгенерированные статьи-гороскопы за период
        horoscope_articles = AIGeneratedArticle.objects.filter(
            schedule__in=horoscope_schedules,
            created_at__gte=period_start
        )
        
        articles_total = horoscope_articles.count()
        
        # Опубликованные статьи-гороскопы
        published_articles = Post.objects.filter(
            ai_generation_info__schedule__in=horoscope_schedules,
            ai_generation_info__created_at__gte=period_start,
            status='published'
        ).count()
        
        # Статистика по расписаниям
        schedule_stats = []
        for schedule in horoscope_schedules:
            schedule_runs = AIScheduleRun.objects.filter(
                schedule=schedule,
                started_at__gte=period_start
            )
            schedule_articles = AIGeneratedArticle.objects.filter(
                schedule=schedule,
                created_at__gte=period_start
            ).count()
            
            schedule_stats.append({
                'name': schedule.name,
                'is_active': schedule.is_active,
                'runs_count': schedule_runs.count(),
                'success_count': schedule_runs.filter(status='success').count(),
                'articles_count': schedule_articles,
            })
        
        # Процент успешности
        success_rate = (runs_success / runs_total * 100) if runs_total > 0 else 0
        
        return {
            'active_schedules': active_schedules,
            'total_schedules': total_schedules,
            'runs': {
                'total': runs_total,
                'success': runs_success,
                'failed': runs_failed,
                'partial': runs_partial,
                'running': runs_running,
                'success_rate': round(success_rate, 1),
            },
            'articles': {
                'total': articles_total,
                'published': published_articles,
                'draft': articles_total - published_articles,
            },
            'schedule_stats': schedule_stats,
            'period_days': days,
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения метрик гороскопов: {e}", exc_info=True)
        return {
            'active_schedules': 0,
            'total_schedules': 0,
            'runs': {
                'total': 0,
                'success': 0,
                'failed': 0,
                'partial': 0,
                'running': 0,
                'success_rate': 0,
            },
            'articles': {
                'total': 0,
                'published': 0,
                'draft': 0,
            },
            'schedule_stats': [],
            'period_days': days,
        }

