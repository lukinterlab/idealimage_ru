"""
Модуль расчета бонусов для авторов
"""
from decimal import Decimal
from django.db.models import Count, Sum, Q
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime
import logging

from .models import (
    Donation, AuthorRole, BonusFormula, AuthorStats,
    AuthorBonus, AuthorPenaltyReward
)
from blog.models import Post
from Asistent.models import TaskAssignment

logger = logging.getLogger(__name__)


def calculate_author_stats(author, period_start, period_end, period_type='week'):
    """
    Рассчитать статистику автора за период
    
    Args:
        author: User объект автора
        period_start: datetime начала периода
        period_end: datetime конца периода
        period_type: тип периода ('week', 'month', 'all_time')
    
    Returns:
        AuthorStats объект с рассчитанной статистикой
    """
    logger.info(f'Расчет статистики для {author.username} за период {period_start} - {period_end}')
    
    # Получаем или создаем запись статистики
    stats, created = AuthorStats.objects.get_or_create(
        author=author,
        period_type=period_type,
        period_start=period_start,
        defaults={
            'period_end': period_end
        }
    )
    
    # Если не создана новая запись, обновляем период
    if not created:
        stats.period_end = period_end
    
    # Получаем статьи автора за период
    articles = Post.objects.filter(
        author=author,
        status='published',
        created__gte=period_start,
        created__lte=period_end
    )
    
    # Подсчет статистики по статьям
    stats.articles_count = articles.count()
    
    # Собираем детальную информацию по статьям
    articles_detail = []
    total_likes = 0
    total_comments = 0
    total_views = 0
    
    for article in articles:
        article_likes = article.likes.count()
        article_comments = article.comments.filter(active=True).count()
        article_views = article.views
        
        total_likes += article_likes
        total_comments += article_comments
        total_views += article_views
        
        articles_detail.append({
            'id': article.id,
            'title': article.title,
            'slug': article.slug,
            'created': article.created.isoformat(),
            'likes': article_likes,
            'comments': article_comments,
            'views': article_views,
        })
    
    stats.total_likes = total_likes
    stats.total_comments = total_comments
    stats.total_views = total_views
    stats.articles_detail = articles_detail
    
    # Подсчет статистики по заданиям
    completed_tasks = TaskAssignment.objects.filter(
        author=author,
        status='approved',
        completed_at__gte=period_start,
        completed_at__lte=period_end
    ).select_related('task')
    
    stats.completed_tasks_count = completed_tasks.count()
    
    # Собираем детальную информацию по заданиям
    tasks_detail = []
    tasks_reward_total = Decimal('0.00')
    
    for assignment in completed_tasks:
        reward = assignment.task.reward
        tasks_reward_total += reward
        
        tasks_detail.append({
            'task_id': assignment.task.id,
            'task_title': assignment.task.title,
            'completed_at': assignment.completed_at.isoformat() if assignment.completed_at else None,
            'reward': float(reward),
        })
    
    stats.tasks_reward_total = tasks_reward_total
    stats.tasks_detail = tasks_detail
    
    # Сохраняем статистику перед расчетом роли
    stats.save()
    
    # Определяем роль и рассчитываем баллы
    role, points = calculate_role(author, stats)
    
    stats.current_role = role
    stats.calculated_points = Decimal(str(points))
    stats.save()
    
    logger.info(f'Статистика для {author.username}: статей={stats.articles_count}, '
                f'лайков={stats.total_likes}, комментариев={stats.total_comments}, '
                f'просмотров={stats.total_views}, заданий={stats.completed_tasks_count}, '
                f'баллов={stats.calculated_points}, роль={stats.current_role}')
    
    return stats


def calculate_role(author, stats):
    """
    Определить роль автора на основе его статистики
    
    Args:
        author: User объект автора
        stats: AuthorStats объект со статистикой
    
    Returns:
        tuple: (AuthorRole, calculated_points)
    """
    # Получаем все активные формулы, отсортированные по уровню роли (от высшего к низшему)
    formulas = BonusFormula.objects.filter(
        is_active=True
    ).select_related('role').order_by('-role__level')
    
    if not formulas.exists():
        logger.warning('Нет активных формул для расчета роли. Создайте формулы через админ-панель.')
        # Возвращаем роль стажера по умолчанию, если нет формул
        default_role = AuthorRole.objects.filter(level=1).first()
        return default_role, 0
    
    # Рассчитываем баллы для каждой формулы
    max_points = 0
    best_role = None
    
    for formula in formulas:
        # Рассчитываем баллы
        points = formula.calculate_points(
            articles=stats.articles_count,
            likes=stats.total_likes,
            comments=stats.total_comments,
            views=stats.total_views,
            tasks=stats.completed_tasks_count
        )
        
        # Проверяем, соответствует ли автор требованиям роли
        if points >= float(formula.min_points_required):
            if stats.articles_count >= formula.min_articles_required:
                # Автор соответствует требованиям этой роли
                if best_role is None or formula.role.level > best_role.level:
                    best_role = formula.role
                    max_points = points
    
    # Если не нашли подходящую роль, берем самую низкую (Стажёр)
    if best_role is None:
        best_role = AuthorRole.objects.order_by('level').first()
        # Рассчитываем баллы по формуле стажера
        if best_role and hasattr(best_role, 'formula'):
            max_points = best_role.formula.calculate_points(
                articles=stats.articles_count,
                likes=stats.total_likes,
                comments=stats.total_comments,
                views=stats.total_views,
                tasks=stats.completed_tasks_count
            )
    
    return best_role, max_points


def calculate_bonus(author, period_start, period_end):
    """
    Рассчитать бонус автора за период
    
    Args:
        author: User объект автора
        period_start: datetime начала периода
        period_end: datetime конца периода
    
    Returns:
        AuthorBonus объект с рассчитанным бонусом
    """
    logger.info(f'Расчет бонуса для {author.username} за период {period_start} - {period_end}')
    
    # Сначала рассчитываем статистику
    stats = calculate_author_stats(author, period_start, period_end)
    
    # Получаем или создаем запись бонуса
    bonus, created = AuthorBonus.objects.get_or_create(
        author=author,
        period_start=period_start,
        period_end=period_end,
        defaults={
            'role_at_calculation': stats.current_role
        }
    )
    
    # Обновляем роль, если запись уже существовала
    if not created:
        bonus.role_at_calculation = stats.current_role
    
    # 1. Рассчитываем бонус от донатов
    donations = Donation.objects.filter(
        article_author=author,
        status='succeeded',
        completed_at__gte=period_start,
        completed_at__lte=period_end
    )
    
    donations_amount = donations.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    bonus.donations_amount = donations_amount
    
    # Получаем процент бонуса из роли
    if stats.current_role:
        bonus.bonus_percentage = stats.current_role.bonus_percentage
        bonus.calculated_bonus = donations_amount * (stats.current_role.bonus_percentage / 100)
    else:
        bonus.bonus_percentage = Decimal('0.00')
        bonus.calculated_bonus = Decimal('0.00')
    
    # 2. Добавляем вознаграждение за задания
    bonus.tasks_reward = stats.tasks_reward_total
    
    # 3. Рассчитываем бонус от баллов
    bonus.points_earned = stats.calculated_points
    
    if stats.current_role:
        bonus.point_value = stats.current_role.point_value
        bonus.bonus_from_points = stats.calculated_points * stats.current_role.point_value
    else:
        bonus.point_value = Decimal('1.00')
        bonus.bonus_from_points = stats.calculated_points
    
    # 4. Считаем общий бонус до применения штрафов/премий
    total_before_adjustments = (
        bonus.calculated_bonus + 
        bonus.tasks_reward + 
        bonus.bonus_from_points
    )
    
    # 5. Применяем штрафы и премии
    adjusted_amount = apply_penalties_rewards(author, total_before_adjustments, period_start, period_end)
    
    bonus.total_bonus = adjusted_amount
    bonus.save()
    
    logger.info(f'Бонус для {author.username}: донаты={bonus.calculated_bonus}₽, '
                f'задания={bonus.tasks_reward}₽, баллы={bonus.bonus_from_points}₽, '
                f'итого={bonus.total_bonus}₽')
    
    return bonus


def apply_penalties_rewards(author, base_amount, period_start, period_end):
    """
    Применить штрафы и премии к базовой сумме бонуса
    
    Args:
        author: User объект автора
        base_amount: Decimal базовая сумма бонуса
        period_start: datetime начала периода
        period_end: datetime конца периода
    
    Returns:
        Decimal: скорректированная сумма
    """
    adjusted_amount = Decimal(str(base_amount))
    
    # Получаем активные штрафы и премии для автора
    penalties_rewards = AuthorPenaltyReward.objects.filter(
        author=author,
        is_active=True,
        applied_from__lte=period_end
    ).filter(
        Q(applied_until__isnull=True) | Q(applied_until__gte=period_start)
    )
    
    for pr in penalties_rewards:
        # Проверяем, применяется ли к этому периоду
        should_apply = False
        
        if pr.applied_to == 'one_time':
            # Разовый - применяется только если период включает дату создания
            if pr.applied_from >= period_start and pr.applied_from <= period_end:
                should_apply = True
        elif pr.applied_to == 'weekly':
            # Еженедельный - применяется всегда в рамках действия
            should_apply = True
        elif pr.applied_to == 'monthly':
            # Ежемесячный - применяется всегда в рамках действия
            should_apply = True
        
        if should_apply:
            amount = Decimal(str(pr.calculate_amount(base_amount)))
            
            if pr.type == 'penalty':
                adjusted_amount -= amount
                logger.info(f'Применен штраф для {author.username}: -{amount}₽ ({pr.reason[:50]})')
            else:  # reward
                adjusted_amount += amount
                logger.info(f'Применена премия для {author.username}: +{amount}₽ ({pr.reason[:50]})')
    
    # Не даем бонусу уйти в минус
    if adjusted_amount < 0:
        adjusted_amount = Decimal('0.00')
    
    return adjusted_amount


def recalculate_all_authors_stats(period_start, period_end, period_type='week'):
    """
    Пересчитать статистику для всех авторов за период
    
    Args:
        period_start: datetime начала периода
        period_end: datetime конца периода
        period_type: тип периода
    
    Returns:
        list: список AuthorStats объектов
    """
    logger.info(f'Пересчет статистики всех авторов за период {period_start} - {period_end}')
    
    # Получаем всех авторов, у которых есть статьи за период
    authors_with_articles = User.objects.filter(
        author_posts__status='published',
        author_posts__created__gte=period_start,
        author_posts__created__lte=period_end
    ).distinct()
    
    # Также добавляем авторов, у которых есть выполненные задания
    authors_with_tasks = User.objects.filter(
        task_assignments__status='approved',
        task_assignments__completed_at__gte=period_start,
        task_assignments__completed_at__lte=period_end
    ).distinct()
    
    # Объединяем списки авторов
    all_authors = set(authors_with_articles) | set(authors_with_tasks)
    
    stats_list = []
    for author in all_authors:
        try:
            stats = calculate_author_stats(author, period_start, period_end, period_type)
            stats_list.append(stats)
        except Exception as e:
            logger.error(f'Ошибка при расчете статистики для {author.username}: {str(e)}')
    
    logger.info(f'Пересчитана статистика для {len(stats_list)} авторов')
    return stats_list


def recalculate_all_authors_bonuses(period_start, period_end):
    """
    Пересчитать бонусы для всех авторов за период
    
    Args:
        period_start: datetime начала периода
        period_end: datetime конца периода
    
    Returns:
        list: список AuthorBonus объектов
    """
    logger.info(f'Пересчет бонусов всех авторов за период {period_start} - {period_end}')
    
    # Сначала пересчитываем статистику
    stats_list = recalculate_all_authors_stats(period_start, period_end)
    
    # Затем рассчитываем бонусы
    bonuses_list = []
    for stats in stats_list:
        try:
            bonus = calculate_bonus(stats.author, period_start, period_end)
            bonuses_list.append(bonus)
        except Exception as e:
            logger.error(f'Ошибка при расчете бонуса для {stats.author.username}: {str(e)}')
    
    logger.info(f'Пересчитаны бонусы для {len(bonuses_list)} авторов')
    return bonuses_list


def get_author_stats_summary(author, period_type='week'):
    """
    Получить сводку статистики автора за последний период
    
    Args:
        author: User объект автора
        period_type: тип периода
    
    Returns:
        dict: сводка статистики
    """
    stats = AuthorStats.objects.filter(
        author=author,
        period_type=period_type
    ).order_by('-period_start').first()
    
    if not stats:
        return {
            'exists': False,
            'message': 'Статистика еще не рассчитана'
        }
    
    bonus = AuthorBonus.objects.filter(
        author=author,
        period_start=stats.period_start,
        period_end=stats.period_end
    ).first()
    
    return {
        'exists': True,
        'period_start': stats.period_start,
        'period_end': stats.period_end,
        'articles_count': stats.articles_count,
        'total_likes': stats.total_likes,
        'total_comments': stats.total_comments,
        'total_views': stats.total_views,
        'completed_tasks_count': stats.completed_tasks_count,
        'tasks_reward_total': float(stats.tasks_reward_total),
        'calculated_points': float(stats.calculated_points),
        'current_role': stats.current_role.name if stats.current_role else None,
        'role_level': stats.current_role.level if stats.current_role else None,
        'bonus': {
            'donations_amount': float(bonus.donations_amount) if bonus else 0,
            'calculated_bonus': float(bonus.calculated_bonus) if bonus else 0,
            'tasks_reward': float(bonus.tasks_reward) if bonus else 0,
            'bonus_from_points': float(bonus.bonus_from_points) if bonus else 0,
            'total_bonus': float(bonus.total_bonus) if bonus else 0,
            'status': bonus.get_status_display() if bonus else 'Не рассчитан'
        } if bonus else None
    }

