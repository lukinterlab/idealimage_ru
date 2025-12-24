"""
Модуль еженедельной обработки отчетов по бонусам
"""
from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import datetime, timedelta
import pytz
import logging

from .models import (
    WeeklyReport, AuthorBonus, BonusPaymentRegistry, Donation
)
from .bonus_calculator import recalculate_all_authors_bonuses

logger = logging.getLogger(__name__)


def get_week_boundaries(date=None):
    """
    Получить границы недели (понедельник 12:00 - следующий понедельник 12:00 МСК)
    
    Args:
        date: datetime объект (если None, используется текущая дата)
    
    Returns:
        tuple: (week_start, week_end)
    """
    if date is None:
        date = timezone.now()
    
    # Устанавливаем московский часовой пояс
    moscow_tz = pytz.timezone('Europe/Moscow')
    
    # Конвертируем в московское время, если нужно
    if timezone.is_aware(date):
        date = date.astimezone(moscow_tz)
    else:
        date = moscow_tz.localize(date)
    
    # Находим последний понедельник в 12:00
    days_since_monday = date.weekday()  # 0 = Monday, 6 = Sunday
    
    # Если сегодня понедельник и время до 12:00, берем прошлый понедельник
    if days_since_monday == 0 and date.hour < 12:
        days_since_monday = 7
    
    last_monday = date - timedelta(days=days_since_monday)
    week_start = moscow_tz.localize(
        datetime(last_monday.year, last_monday.month, last_monday.day, 12, 0, 0)
    )
    
    # Следующий понедельник в 12:00
    week_end = week_start + timedelta(days=7)
    
    return week_start, week_end


def get_previous_week_boundaries():
    """
    Получить границы прошлой недели
    
    Returns:
        tuple: (week_start, week_end)
    """
    current_start, _ = get_week_boundaries()
    previous_week_end = current_start
    previous_week_start = previous_week_end - timedelta(days=7)
    
    return previous_week_start, previous_week_end


def generate_weekly_report(week_start=None, week_end=None, force=False):
    """
    Сгенерировать недельный отчет
    
    Args:
        week_start: datetime начала недели (если None, используется прошлая неделя)
        week_end: datetime конца недели
        force: bool, если True - пересоздать отчет, даже если он уже существует
    
    Returns:
        WeeklyReport объект
    """
    # Если границы не указаны, используем прошлую неделю
    if week_start is None or week_end is None:
        week_start, week_end = get_previous_week_boundaries()
    
    logger.info(f'Генерация недельного отчета за {week_start} - {week_end}')
    
    # Проверяем, нет ли уже отчета за этот период
    existing_report = WeeklyReport.objects.filter(
        week_start=week_start,
        week_end=week_end
    ).first()
    
    if existing_report:
        if existing_report.is_finalized and not force:
            logger.warning(f'Отчет за этот период уже зафиксирован и не может быть пересоздан')
            return existing_report
        
        if not force:
            logger.info(f'Отчет за этот период уже существует, обновляем его')
            report = existing_report
        else:
            logger.info(f'Принудительное пересоздание отчета')
            existing_report.delete()
            report = WeeklyReport.objects.create(
                week_start=week_start,
                week_end=week_end
            )
    else:
        report = WeeklyReport.objects.create(
            week_start=week_start,
            week_end=week_end
        )
    
    # Пересчитываем бонусы для всех авторов
    bonuses_list = recalculate_all_authors_bonuses(week_start, week_end)
    
    # Формируем данные отчета
    report_data = {
        'authors': [],
        'summary': {}
    }
    
    total_donations = Decimal('0.00')
    total_bonuses = Decimal('0.00')
    total_tasks_rewards = Decimal('0.00')
    
    for bonus in bonuses_list:
        author_data = {
            'author_id': bonus.author.id,
            'author_username': bonus.author.username,
            'author_full_name': bonus.author.get_full_name() or bonus.author.username,
            'role': bonus.role_at_calculation.name if bonus.role_at_calculation else 'Стажёр',
            'role_level': bonus.role_at_calculation.level if bonus.role_at_calculation else 1,
            'donations_amount': float(bonus.donations_amount),
            'bonus_percentage': float(bonus.bonus_percentage),
            'calculated_bonus': float(bonus.calculated_bonus),
            'tasks_reward': float(bonus.tasks_reward),
            'points_earned': float(bonus.points_earned),
            'bonus_from_points': float(bonus.bonus_from_points),
            'total_bonus': float(bonus.total_bonus),
            'status': bonus.status
        }
        
        report_data['authors'].append(author_data)
        
        total_donations += bonus.donations_amount
        total_bonuses += bonus.total_bonus
        total_tasks_rewards += bonus.tasks_reward
    
    # Добавляем сводную информацию
    report_data['summary'] = {
        'total_authors': len(bonuses_list),
        'total_donations': float(total_donations),
        'total_bonuses': float(total_bonuses),
        'total_tasks_rewards': float(total_tasks_rewards),
        'period_start': week_start.isoformat(),
        'period_end': week_end.isoformat(),
        'generated_at': timezone.now().isoformat()
    }
    
    # Сохраняем отчет
    report.report_data = report_data
    report.total_donations = total_donations
    report.total_bonuses = total_bonuses
    report.total_tasks_rewards = total_tasks_rewards
    report.authors_count = len(bonuses_list)
    report.save()
    
    logger.info(f'Отчет сгенерирован: авторов={report.authors_count}, '
                f'донатов={report.total_donations}₽, бонусов={report.total_bonuses}₽')
    
    return report


def finalize_weekly_report(report, finalized_by):
    """
    Зафиксировать недельный отчет (после этого его нельзя изменить)
    
    Args:
        report: WeeklyReport объект
        finalized_by: User, кто фиксирует отчет
    
    Returns:
        WeeklyReport объект
    """
    if report.is_finalized:
        logger.warning(f'Отчет уже зафиксирован {report.finalized_at}')
        return report
    
    logger.info(f'Фиксация отчета за {report.week_start} - {report.week_end}')
    
    report.is_finalized = True
    report.finalized_at = timezone.now()
    report.finalized_by = finalized_by
    report.save()
    
    # Утверждаем все бонусы в отчете
    bonuses = AuthorBonus.objects.filter(
        period_start=report.week_start,
        period_end=report.week_end,
        status='pending'
    )
    
    for bonus in bonuses:
        bonus.status = 'approved'
        bonus.approved_at = timezone.now()
        bonus.save()
    
    # Создаем реестр выплат
    create_payment_registry(report)
    
    logger.info(f'Отчет зафиксирован, утверждено {bonuses.count()} бонусов')
    
    return report


def create_payment_registry(report):
    """
    Создать реестр выплат на основе отчета
    
    Args:
        report: WeeklyReport объект
    
    Returns:
        list: список BonusPaymentRegistry объектов
    """
    logger.info(f'Создание реестра выплат для отчета {report}')
    
    # Получаем все утвержденные бонусы за период отчета
    bonuses = AuthorBonus.objects.filter(
        period_start=report.week_start,
        period_end=report.week_end,
        status='approved'
    ).select_related('author')
    
    registry_entries = []
    
    for bonus in bonuses:
        # Проверяем, нет ли уже записи в реестре
        existing_entry = BonusPaymentRegistry.objects.filter(
            week_report=report,
            author=bonus.author
        ).first()
        
        if existing_entry:
            # Обновляем существующую запись
            existing_entry.bonus = bonus
            existing_entry.amount_to_pay = bonus.total_bonus
            existing_entry.save()
            registry_entries.append(existing_entry)
        else:
            # Создаем новую запись
            entry = BonusPaymentRegistry.objects.create(
                week_report=report,
                author=bonus.author,
                bonus=bonus,
                amount_to_pay=bonus.total_bonus
            )
            registry_entries.append(entry)
    
    logger.info(f'Создано {len(registry_entries)} записей в реестре выплат')
    
    return registry_entries


def mark_payment_as_paid(registry_entry, paid_amount, payment_method, payment_note, marked_by):
    """
    Отметить выплату как оплаченную
    
    Args:
        registry_entry: BonusPaymentRegistry объект
        paid_amount: Decimal сумма выплаты
        payment_method: str способ оплаты
        payment_note: str примечание
        marked_by: User, кто отметил
    
    Returns:
        BonusPaymentRegistry объект
    """
    logger.info(f'Отметка оплаты для {registry_entry.author.username}: {paid_amount}₽')
    
    registry_entry.paid_amount = paid_amount
    registry_entry.payment_method = payment_method
    registry_entry.payment_note = payment_note
    registry_entry.payment_date = timezone.now()
    registry_entry.marked_by = marked_by
    
    # Определяем статус
    if paid_amount >= registry_entry.amount_to_pay:
        registry_entry.status = 'paid'
    elif paid_amount > 0:
        registry_entry.status = 'partial'
    else:
        registry_entry.status = 'pending'
    
    registry_entry.save()
    
    # Обновляем статус бонуса
    if registry_entry.status == 'paid':
        registry_entry.bonus.status = 'paid'
        registry_entry.bonus.paid_at = timezone.now()
        registry_entry.bonus.save()
    
    logger.info(f'Выплата отмечена, статус: {registry_entry.get_status_display()}')
    
    return registry_entry


def get_current_week_boundaries():
    """
    Получить границы текущей недели
    
    Returns:
        tuple: (week_start, week_end)
    """
    return get_week_boundaries()


def get_current_week_summary():
    """
    Получить сводку за текущую неделю (еще не зафиксированную)
    
    Returns:
        dict: сводка с данными
    """
    week_start, week_end = get_week_boundaries()
    
    # Донаты за текущую неделю
    donations = Donation.objects.filter(
        status='succeeded',
        completed_at__gte=week_start,
        completed_at__lt=week_end
    )
    
    total_donations = donations.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    donations_count = donations.count()
    
    # Авторы с активностью
    active_authors = set()
    
    # Авторы со статьями
    from blog.models import Post
    authors_with_articles = User.objects.filter(
        author_posts__status='published',
        author_posts__created__gte=week_start,
        author_posts__created__lt=week_end
    ).distinct().count()
    active_authors.update(
        User.objects.filter(
            author_posts__status='published',
            author_posts__created__gte=week_start,
            author_posts__created__lt=week_end
        ).distinct()
    )
    
    # Авторы с заданиями
    from Asistent.models import TaskAssignment
    authors_with_tasks = User.objects.filter(
        task_assignments__status='approved',
        task_assignments__completed_at__gte=week_start,
        task_assignments__completed_at__lt=week_end
    ).distinct().count()
    active_authors.update(
        User.objects.filter(
            task_assignments__status='approved',
            task_assignments__completed_at__gte=week_start,
            task_assignments__completed_at__lt=week_end
        ).distinct()
    )
    
    return {
        'week_start': week_start,
        'week_end': week_end,
        'is_current': True,
        'total_donations': float(total_donations),
        'donations_count': donations_count,
        'active_authors_count': len(active_authors),
        'authors_with_articles': authors_with_articles,
        'authors_with_tasks': authors_with_tasks,
    }


def get_latest_finalized_report():
    """
    Получить последний зафиксированный отчет
    
    Returns:
        WeeklyReport объект или None
    """
    return WeeklyReport.objects.filter(
        is_finalized=True
    ).order_by('-week_start').first()


def get_pending_payments_summary():
    """
    Получить сводку по ожидающим выплатам
    
    Returns:
        dict: сводка
    """
    pending_payments = BonusPaymentRegistry.objects.filter(
        status__in=['pending', 'partial']
    ).select_related('author', 'week_report')
    
    total_pending = pending_payments.aggregate(
        total=Sum('amount_to_pay')
    )['total'] or Decimal('0.00')
    
    total_paid = pending_payments.aggregate(
        total=Sum('paid_amount')
    )['total'] or Decimal('0.00')
    
    return {
        'pending_count': pending_payments.count(),
        'total_pending': float(total_pending),
        'total_paid': float(total_paid),
        'total_remaining': float(total_pending - total_paid),
        'payments': [
            {
                'author': payment.author.username,
                'author_full_name': payment.author.get_full_name() or payment.author.username,
                'amount_to_pay': float(payment.amount_to_pay),
                'paid_amount': float(payment.paid_amount),
                'remaining': float(payment.amount_to_pay - payment.paid_amount),
                'week': f'{payment.week_report.week_start.date()} - {payment.week_report.week_end.date()}',
                'status': payment.get_status_display()
            }
            for payment in pending_payments.order_by('-week_report__week_start')
        ]
    }

