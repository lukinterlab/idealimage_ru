"""
Система метрик производительности для генерации статей.
Отслеживает время выполнения каждого этапа и сохраняет в БД.

ВАЖНО: Модель ArticleGenerationMetric определена в Asistent/models.py
"""
import logging
import time
from contextlib import contextmanager
from typing import Optional, Dict, List
from datetime import datetime

from django.utils import timezone

logger = logging.getLogger(__name__)


# ============================================================================
# МЕНЕДЖЕР МЕТРИК (использует модель из Asistent.models)
# ============================================================================

class MetricsManager:
    """Менеджер для работы с метриками генерации"""
    
    def __init__(self, template, user_id: Optional[int] = None):
        self.template = template
        self.user_id = user_id
        self.metric = None
    
    def start(self) -> 'MetricsManager':
        """Начало отслеживания метрик"""
        from Asistent.models import ArticleGenerationMetric
        
        try:
            self.metric = ArticleGenerationMetric.objects.create(
                template=self.template,
                user_id=self.user_id
            )
            logger.info(f"📊 Метрика создана: ID={self.metric.id}")
        except Exception as e:
            logger.error(f"Ошибка создания метрики: {e}")
            self.metric = None
        
        return self
    
    @contextmanager
    def measure(self, operation: str):
        """
        Контекстный менеджер для измерения времени операции.
        
        Usage:
            with metrics.measure('content_generation'):
                content = generate_content()
        """
        start_time = time.time()
        operation_display = operation.replace('_', ' ').title()
        
        logger.info(f"⏱️ Начало: {operation_display}")
        
        try:
            yield
        finally:
            duration = time.time() - start_time
            logger.info(f"✅ Завершено: {operation_display} за {duration:.2f}s")
            
            # Сохраняем метрику
            if self.metric:
                self._save_duration(operation, duration)
    
    def _save_duration(self, operation: str, duration: float):
        """Сохранение длительности операции"""
        if not self.metric:
            return
        
        try:
            # Маппинг операций на поля модели
            field_mapping = {
                'context_build': 'context_build_duration',
                'content_generation': 'content_generation_duration',
                'title_generation': 'title_generation_duration',
                'image_processing': 'image_processing_duration',
                'tags_generation': 'tags_generation_duration',
            }
            
            field_name = field_mapping.get(operation)
            if field_name:
                setattr(self.metric, field_name, duration)
                self.metric.save(update_fields=[field_name])
        
        except Exception as e:
            logger.warning(f"Не удалось сохранить метрику {operation}: {e}")
    
    def set_result_metrics(
        self,
        content_length: int,
        word_count: int,
        tags_count: int,
        has_image: bool,
        image_source_type: str,
        gigachat_model: str = ''
    ):
        """Установка метрик результата"""
        if not self.metric:
            return
        
        try:
            self.metric.content_length = content_length
            self.metric.word_count = word_count
            self.metric.tags_count = tags_count
            self.metric.has_image = has_image
            self.metric.image_source_type = image_source_type
            self.metric.gigachat_model = gigachat_model
            self.metric.save(update_fields=[
                'content_length', 'word_count', 'tags_count',
                'has_image', 'image_source_type', 'gigachat_model'
            ])
        except Exception as e:
            logger.warning(f"Не удалось сохранить метрики результата: {e}")
    
    def complete(self, success: bool = True, error_message: str = ''):
        """Завершение отслеживания метрик"""
        if self.metric:
            self.metric.complete(success, error_message)
    
    def get_summary(self) -> Dict[str, float]:
        """Получение сводки метрик"""
        if not self.metric:
            return {}
        
        return {
            'total': self.metric.total_duration or 0,
            'context_build': self.metric.context_build_duration or 0,
            'content_generation': self.metric.content_generation_duration or 0,
            'title_generation': self.metric.title_generation_duration or 0,
            'image_processing': self.metric.image_processing_duration or 0,
            'tags_generation': self.metric.tags_generation_duration or 0,
        }


# ============================================================================
# АНАЛИТИКА МЕТРИК
# ============================================================================

class MetricsAnalyzer:
    """Анализ метрик производительности"""
    
    @staticmethod
    def get_template_stats(template_id: int, days: int = 30) -> Dict:
        from Asistent.models import ArticleGenerationMetric
        """
        Статистика по шаблону за последние N дней.
        
        Returns:
            Dict с avg/min/max для каждого этапа
        """
        from django.db.models import Avg, Min, Max, Count
        from datetime import timedelta
        
        since = timezone.now() - timedelta(days=days)
        
        metrics = ArticleGenerationMetric.objects.filter(
            template_id=template_id,
            started_at__gte=since,
            success=True
        )
        
        if not metrics.exists():
            return {}
        
        stats = metrics.aggregate(
            count=Count('id'),
            avg_total=Avg('total_duration'),
            min_total=Min('total_duration'),
            max_total=Max('total_duration'),
            avg_content=Avg('content_generation_duration'),
            avg_title=Avg('title_generation_duration'),
            avg_image=Avg('image_processing_duration'),
            avg_word_count=Avg('word_count'),
        )
        
        success_rate = metrics.filter(success=True).count() / metrics.count() * 100
        
        return {
            'count': stats['count'],
            'success_rate': success_rate,
            'avg_total_duration': stats['avg_total'] or 0,
            'min_total_duration': stats['min_total'] or 0,
            'max_total_duration': stats['max_total'] or 0,
            'avg_content_duration': stats['avg_content'] or 0,
            'avg_title_duration': stats['avg_title'] or 0,
            'avg_image_duration': stats['avg_image'] or 0,
            'avg_word_count': stats['avg_word_count'] or 0,
        }
    
    @staticmethod
    def get_slowest_operations(days: int = 7, limit: int = 10) -> List[Dict]:
        from Asistent.models import ArticleGenerationMetric
        """Самые медленные операции за последние N дней"""
        from datetime import timedelta
        
        since = timezone.now() - timedelta(days=days)
        
        slowest = ArticleGenerationMetric.objects.filter(
            started_at__gte=since,
            success=True,
            total_duration__isnull=False
        ).order_by('-total_duration')[:limit]
        
        return [
            {
                'id': m.id,
                'template': m.template.name,
                'duration': m.total_duration,
                'started_at': m.started_at,
                'content_duration': m.content_generation_duration,
                'image_duration': m.image_processing_duration,
            }
            for m in slowest
        ]
    
    @staticmethod
    def get_failure_rate(days: int = 7) -> Dict:
        from Asistent.models import ArticleGenerationMetric
        """Процент ошибок за последние N дней"""
        from datetime import timedelta
        from django.db.models import Count, Q
        
        since = timezone.now() - timedelta(days=days)
        
        metrics = ArticleGenerationMetric.objects.filter(started_at__gte=since)
        
        total = metrics.count()
        if total == 0:
            return {'total': 0, 'success': 0, 'failed': 0, 'success_rate': 0}
        
        success_count = metrics.filter(success=True).count()
        failed_count = metrics.filter(success=False).count()
        
        return {
            'total': total,
            'success': success_count,
            'failed': failed_count,
            'success_rate': (success_count / total * 100) if total > 0 else 0,
        }

