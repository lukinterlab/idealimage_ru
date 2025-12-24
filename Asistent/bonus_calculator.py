"""
Калькулятор бонусов для авторов статей
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum, Avg, Count, Q

logger = logging.getLogger(__name__)


class BonusCalculator:
    """Калькулятор бонусов для авторов"""
    
    # Стандартная формула бонусов (может быть переопределена из БД)
    DEFAULT_FORMULA = {
        'views_coefficient': 0.1,
        'likes_coefficient': 2.0,
        'comments_coefficient': 5.0,
        'shares_coefficient': 10.0,
        'reading_time_coefficient': 0.5,
        'unique_visitors_coefficient': 1.5,
        'engagement_rate_coefficient': 20.0,
        'quality_multiplier': 1.0,  # От 0.5 до 2.0
        'freshness_bonus': 1.2,  # Бонус для свежих статей (до 7 дней)
        'trending_bonus': 1.5,  # Бонус для трендовых статей
    }
    
    def __init__(self, formula: Dict = None):
        """
        Args:
            formula: Кастомная формула расчета (опционально)
        """
        if formula:
            self.formula = {**self.DEFAULT_FORMULA, **formula}
        else:
            # Пробуем загрузить из БД
            self.formula = self._load_formula_from_db() or self.DEFAULT_FORMULA
    
    def calculate_article_bonus(self, article) -> Dict:
        """
        Рассчитывает бонус за статью
        
        Args:
            article: Объект статьи (blog.Post)
        
        Returns:
            Dict с детальной разбивкой бонуса
        """
        try:
            # Базовые метрики
            views = article.views or 0
            likes = article.total_likes() if hasattr(article, 'total_likes') else 0
            comments_count = article.comments.filter(active=True).count()
            shares = getattr(article, 'shares', 0)
            
            # Расчет времени чтения (примерно 200 слов в минуту)
            word_count = len(article.content.split())
            reading_time = word_count / 200
            
            # Уникальные посетители (если есть)
            unique_visitors = getattr(article, 'unique_visitors', views * 0.7)
            
            # Engagement rate
            total_interactions = likes + comments_count + shares
            engagement_rate = (total_interactions / max(views, 1)) * 100
            
            # Качество статьи (оценка AI или модератора)
            quality_score = self._calculate_quality_score(article)
            
            # Свежесть статьи
            age_days = (timezone.now() - article.created_at).days
            is_fresh = age_days <= 7
            
            # Трендовость (быстрый рост просмотров)
            is_trending = self._is_trending(article)
            
            # Расчет по формуле
            base_bonus = (
                views * self.formula['views_coefficient'] +
                likes * self.formula['likes_coefficient'] +
                comments_count * self.formula['comments_coefficient'] +
                shares * self.formula['shares_coefficient'] +
                reading_time * self.formula['reading_time_coefficient'] +
                unique_visitors * self.formula['unique_visitors_coefficient'] +
                engagement_rate * self.formula['engagement_rate_coefficient']
            )
            
            # Применяем множители
            bonus = base_bonus * quality_score
            
            if is_fresh:
                bonus *= self.formula['freshness_bonus']
            
            if is_trending:
                bonus *= self.formula['trending_bonus']
            
            # Округляем до 2 знаков
            bonus = round(bonus, 2)
            
            result = {
                'article_id': article.id,
                'article_title': article.title,
                'total_bonus': bonus,
                'base_bonus': round(base_bonus, 2),
                'metrics': {
                    'views': views,
                    'likes': likes,
                    'comments': comments_count,
                    'shares': shares,
                    'reading_time': round(reading_time, 2),
                    'unique_visitors': int(unique_visitors),
                    'engagement_rate': round(engagement_rate, 2),
                },
                'multipliers': {
                    'quality_score': quality_score,
                    'is_fresh': is_fresh,
                    'is_trending': is_trending,
                },
                'breakdown': {
                    'from_views': round(views * self.formula['views_coefficient'], 2),
                    'from_likes': round(likes * self.formula['likes_coefficient'], 2),
                    'from_comments': round(comments_count * self.formula['comments_coefficient'], 2),
                    'from_shares': round(shares * self.formula['shares_coefficient'], 2),
                    'from_reading_time': round(reading_time * self.formula['reading_time_coefficient'], 2),
                    'from_unique_visitors': round(unique_visitors * self.formula['unique_visitors_coefficient'], 2),
                    'from_engagement': round(engagement_rate * self.formula['engagement_rate_coefficient'], 2),
                },
                'calculated_at': timezone.now().isoformat()
            }
            
            logger.info(f"Рассчитан бонус для статьи {article.id}: {bonus} баллов")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка расчета бонуса для статьи {article.id}: {e}")
            return {
                'article_id': article.id,
                'total_bonus': 0,
                'error': str(e)
            }
    
    def calculate_author_bonus(self, author: User, period_days: int = 30) -> Dict:
        """
        Рассчитывает общий бонус автора за период
        
        Args:
            author: Пользователь-автор
            period_days: Период расчета в днях
        
        Returns:
            Dict с детальной информацией о бонусах
        """
        try:
            from blog.models import Post
            
            # Получаем статьи автора за период
            start_date = timezone.now() - timedelta(days=period_days)
            articles = Post.objects.filter(
                author=author,
                is_published=True,
                created_at__gte=start_date
            )
            
            total_bonus = 0
            articles_bonuses = []
            
            for article in articles:
                article_bonus = self.calculate_article_bonus(article)
                total_bonus += article_bonus['total_bonus']
                articles_bonuses.append(article_bonus)
            
            # Статистика автора
            stats = {
                'total_articles': articles.count(),
                'total_views': articles.aggregate(Sum('views'))['views__sum'] or 0,
                'avg_views_per_article': articles.aggregate(Avg('views'))['views__avg'] or 0,
                'total_comments': sum(a.comments.filter(active=True).count() for a in articles),
            }
            
            result = {
                'author_id': author.id,
                'author_username': author.username,
                'period_days': period_days,
                'total_bonus': round(total_bonus, 2),
                'articles_count': len(articles_bonuses),
                'articles_bonuses': articles_bonuses,
                'statistics': stats,
                'calculated_at': timezone.now().isoformat()
            }
            
            logger.info(f"Рассчитан бонус для автора {author.username}: {total_bonus} баллов")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка расчета бонуса для автора {author.id}: {e}")
            return {
                'author_id': author.id,
                'total_bonus': 0,
                'error': str(e)
            }
    
    def calculate_all_authors_bonuses(self, period_days: int = 30) -> List[Dict]:
        """
        Рассчитывает бонусы для всех авторов за период
        
        Args:
            period_days: Период расчета в днях
        
        Returns:
            Список результатов для каждого автора
        """
        from blog.models import Post
        
        # Получаем уникальных авторов, которые публиковали за период
        start_date = timezone.now() - timedelta(days=period_days)
        authors = User.objects.filter(
            posts__is_published=True,
            posts__created_at__gte=start_date
        ).distinct()
        
        results = []
        for author in authors:
            author_result = self.calculate_author_bonus(author, period_days)
            results.append(author_result)
        
        # Сортируем по убыванию бонуса
        results.sort(key=lambda x: x.get('total_bonus', 0), reverse=True)
        
        logger.info(f"Рассчитаны бонусы для {len(results)} авторов")
        return results
    
    def _calculate_quality_score(self, article) -> float:
        """
        Рассчитывает оценку качества статьи
        
        Returns:
            Число от 0.5 до 2.0
        """
        # Базовая оценка
        score = 1.0
        
        # Проверяем наличие AI-оценки
        if hasattr(article, 'ai_quality_score'):
            ai_score = getattr(article, 'ai_quality_score', 0)
            if ai_score > 0:
                # Нормализуем AI-оценку (предполагаем шкалу 0-10)
                score = 0.5 + (ai_score / 10.0) * 1.5
        else:
            # Эвристическая оценка
            word_count = len(article.content.split())
            
            # Длина статьи
            if word_count < 300:
                score *= 0.8  # Короткая статья
            elif word_count > 1000:
                score *= 1.2  # Длинная статья
            
            # Наличие изображений
            if hasattr(article, 'featured_image') and article.featured_image:
                score *= 1.1
            
            # Engagement
            if hasattr(article, 'views') and article.views > 0:
                likes = article.total_likes() if hasattr(article, 'total_likes') else 0
                comments = article.comments.filter(active=True).count()
                engagement = (likes + comments) / article.views
                
                if engagement > 0.1:  # Высокий engagement
                    score *= 1.3
                elif engagement < 0.01:  # Низкий engagement
                    score *= 0.9
        
        # Ограничиваем диапазон
        return max(0.5, min(2.0, score))
    
    def _is_trending(self, article) -> bool:
        """Определяет, является ли статья трендовой"""
        # Простая эвристика: статья трендовая если за последние 24 часа
        # набрала больше 50% от всех просмотров
        
        if not hasattr(article, 'views') or article.views < 100:
            return False
        
        # Можно добавить более сложную логику с отслеживанием просмотров по времени
        # Пока используем простую проверку: свежая статья с большим количеством просмотров
        age_hours = (timezone.now() - article.created_at).total_seconds() / 3600
        
        if age_hours < 24 and article.views > 500:
            return True
        
        if age_hours < 48 and article.views > 1000:
            return True
        
        return False
    
    def _load_formula_from_db(self) -> Optional[Dict]:
        """Загружает формулу расчета из базы данных"""
        try:
            from .models import BonusFormula
            
            # Получаем активную формулу
            formula = BonusFormula.objects.filter(is_active=True).first()
            if formula:
                return formula.coefficients
        except:
            pass
        
        return None
    
    def save_calculation_result(self, author: User, result: Dict):
        """Сохраняет результат расчета в БД"""
        try:
            from .models import BonusCalculation
            
            BonusCalculation.objects.create(
                author=author,
                period_days=result.get('period_days', 30),
                total_bonus=result.get('total_bonus', 0),
                articles_count=result.get('articles_count', 0),
                details=result,
                formula_snapshot=self.formula
            )
            
            logger.info(f"Сохранен результат расчета бонуса для {author.username}")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения расчета: {e}")
    
    def get_bonus_leaderboard(self, period_days: int = 30, limit: int = 10) -> List[Dict]:
        """
        Получает топ авторов по бонусам
        
        Args:
            period_days: Период
            limit: Количество авторов
        
        Returns:
            Список топ авторов
        """
        results = self.calculate_all_authors_bonuses(period_days)
        return results[:limit]
    
    def export_bonuses_to_csv(self, period_days: int = 30, filepath: str = None) -> str:
        """Экспортирует бонусы в CSV файл"""
        import csv
        from datetime import datetime
        
        if not filepath:
            filepath = f"bonuses_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        results = self.calculate_all_authors_bonuses(period_days)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Автор', 'Статей', 'Бонус', 'Просмотров', 'Комментариев'])
            
            for result in results:
                writer.writerow([
                    result['author_username'],
                    result['articles_count'],
                    result['total_bonus'],
                    result['statistics']['total_views'],
                    result['statistics']['total_comments']
                ])
        
        logger.info(f"Экспортированы бонусы в {filepath}")
        return filepath
