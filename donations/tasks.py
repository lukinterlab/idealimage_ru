"""
Django-Q задачи для системы бонусов
"""
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
import logging

from .weekly_processor import (
    generate_weekly_report,
    get_previous_week_boundaries,
    get_current_week_boundaries
)
from .bonus_calculator import recalculate_all_authors_stats
from .models import WeeklyReport, DonationSettings

logger = logging.getLogger(__name__)


def weekly_report_task():
    """
    Еженедельная задача генерации отчета
    Запускается каждый понедельник в 12:00 МСК
    """
    logger.info('Запуск еженедельной задачи генерации отчета')
    
    try:
        # Получаем границы прошлой недели
        week_start, week_end = get_previous_week_boundaries()
        
        logger.info(f'Генерация отчета за {week_start} - {week_end}')
        
        # Проверяем, нет ли уже отчета за этот период
        existing_report = WeeklyReport.objects.filter(
            week_start=week_start,
            week_end=week_end
        ).first()
        
        if existing_report and existing_report.is_finalized:
            logger.info(f'Отчет за этот период уже зафиксирован')
            return {
                'success': True,
                'message': 'Отчет уже существует и зафиксирован',
                'report_id': existing_report.id
            }
        
        # Генерируем отчет
        report = generate_weekly_report(week_start, week_end, force=False)
        
        logger.info(f'Отчет сгенерирован: ID={report.id}, авторов={report.authors_count}, '
                   f'бонусов={report.total_bonuses}₽')
        
        # Отправляем уведомления админам
        send_weekly_report_notification(report)
        
        return {
            'success': True,
            'message': f'Отчет успешно сгенерирован',
            'report_id': report.id,
            'authors_count': report.authors_count,
            'total_bonuses': float(report.total_bonuses)
        }
    
    except Exception as e:
        logger.error(f'Ошибка при генерации еженедельного отчета: {str(e)}')
        return {
            'success': False,
            'error': str(e)
        }


def daily_stats_update():
    """
    Ежедневная задача обновления текущей статистики
    Запускается каждый день в 00:00 МСК
    """
    logger.info('Запуск ежедневной задачи обновления статистики')
    
    try:
        # Получаем границы текущей недели
        week_start, week_end = get_current_week_boundaries()
        
        logger.info(f'Обновление статистики за текущую неделю {week_start} - {week_end}')
        
        # Пересчитываем статистику для всех активных авторов
        stats_list = recalculate_all_authors_stats(week_start, week_end, period_type='week')
        
        logger.info(f'Обновлена статистика для {len(stats_list)} авторов')
        
        return {
            'success': True,
            'message': f'Статистика обновлена для {len(stats_list)} авторов',
            'authors_count': len(stats_list)
        }
    
    except Exception as e:
        logger.error(f'Ошибка при ежедневном обновлении статистики: {str(e)}')
        return {
            'success': False,
            'error': str(e)
        }


def monthly_stats_update():
    """
    Ежемесячная задача обновления статистики за месяц
    Запускается 1 числа каждого месяца в 01:00 МСК
    """
    logger.info('Запуск ежемесячной задачи обновления статистики')
    
    try:
        # Получаем границы прошлого месяца
        from datetime import datetime, timedelta
        import pytz
        
        moscow_tz = pytz.timezone('Europe/Moscow')
        now = timezone.now().astimezone(moscow_tz)
        
        # Первый день текущего месяца
        first_day_this_month = datetime(now.year, now.month, 1, 0, 0, 0)
        first_day_this_month = moscow_tz.localize(first_day_this_month)
        
        # Последний день прошлого месяца
        last_day_prev_month = first_day_this_month - timedelta(days=1)
        
        # Первый день прошлого месяца
        first_day_prev_month = datetime(last_day_prev_month.year, last_day_prev_month.month, 1, 0, 0, 0)
        first_day_prev_month = moscow_tz.localize(first_day_prev_month)
        
        # Последний момент прошлого месяца
        month_end = first_day_this_month
        
        logger.info(f'Обновление статистики за месяц {first_day_prev_month} - {month_end}')
        
        # Пересчитываем статистику
        stats_list = recalculate_all_authors_stats(
            first_day_prev_month,
            month_end,
            period_type='month'
        )
        
        logger.info(f'Обновлена месячная статистика для {len(stats_list)} авторов')
        
        return {
            'success': True,
            'message': f'Месячная статистика обновлена для {len(stats_list)} авторов',
            'authors_count': len(stats_list),
            'period': f'{first_day_prev_month.date()} - {month_end.date()}'
        }
    
    except Exception as e:
        logger.error(f'Ошибка при ежемесячном обновлении статистики: {str(e)}')
        return {
            'success': False,
            'error': str(e)
        }


def send_weekly_report_notification(report):
    """
    Отправить уведомление админам о новом недельном отчете
    
    Args:
        report: WeeklyReport объект
    """
    logger.info(f'Отправка уведомлений о отчете {report.id}')
    
    try:
        # Получаем email администраторов из настроек донатов
        donation_settings = DonationSettings.get_settings()
        
        if not donation_settings.admin_emails:
            logger.warning('Не указаны email администраторов для уведомлений')
            return
        
        admin_emails = [
            email.strip()
            for email in donation_settings.admin_emails.split('\n')
            if email.strip()
        ]
        
        if not admin_emails:
            logger.warning('Список email администраторов пуст')
            return
        
        # Формируем сообщение
        subject = f'Недельный отчет по бонусам: {report.week_start.date()} - {report.week_end.date()}'
        
        message = f"""
Сгенерирован недельный отчет по бонусам авторов.

Период: {report.week_start.date()} - {report.week_end.date()}

Статистика:
- Количество авторов: {report.authors_count}
- Общая сумма донатов: {report.total_donations}₽
- Общая сумма бонусов: {report.total_bonuses}₽
- Вознаграждение за задания: {report.total_tasks_rewards}₽

Дата генерации: {report.generated_at}

Перейдите в админ-панель для просмотра детального отчета и утверждения выплат:
{settings.SITE_URL}/admin/donations/weeklyreport/{report.id}/change/

---
Это автоматическое уведомление от системы IdealImage.ru
        """
        
        # Отправляем email
        send_mail(
            subject=subject,
            message=message.strip(),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=admin_emails,
            fail_silently=False,
        )
        
        logger.info(f'Уведомления отправлены на {len(admin_emails)} адресов')
    
    except Exception as e:
        logger.error(f'Ошибка при отправке уведомлений: {str(e)}')


def send_payment_reminder():
    """
    Задача отправки напоминаний о неоплаченных бонусах
    Запускается каждый четверг в 10:00 МСК
    """
    logger.info('Запуск задачи отправки напоминаний о платежах')
    
    try:
        from .models import BonusPaymentRegistry
        
        # Получаем неоплаченные записи старше 3 дней
        from datetime import timedelta
        three_days_ago = timezone.now() - timedelta(days=3)
        
        pending_payments = BonusPaymentRegistry.objects.filter(
            status__in=['pending', 'partial'],
            created_at__lte=three_days_ago
        ).select_related('week_report', 'author')
        
        if not pending_payments.exists():
            logger.info('Нет неоплаченных платежей старше 3 дней')
            return {
                'success': True,
                'message': 'Нет неоплаченных платежей'
            }
        
        # Получаем email администраторов
        donation_settings = DonationSettings.get_settings()
        
        if not donation_settings.admin_emails:
            logger.warning('Не указаны email администраторов')
            return {
                'success': False,
                'error': 'Не указаны email администраторов'
            }
        
        admin_emails = [
            email.strip()
            for email in donation_settings.admin_emails.split('\n')
            if email.strip()
        ]
        
        # Формируем сообщение
        subject = f'Напоминание: {pending_payments.count()} неоплаченных бонусов'
        
        payment_list = []
        total_amount = 0
        
        for payment in pending_payments[:20]:  # Показываем первые 20
            payment_list.append(
                f"- {payment.author.get_full_name() or payment.author.username}: "
                f"{payment.amount_to_pay}₽ (неделя {payment.week_report.week_start.date()})"
            )
            total_amount += payment.amount_to_pay
        
        message = f"""
Напоминание о неоплаченных бонусах авторам.

Всего неоплаченных записей: {pending_payments.count()}
Общая сумма к выплате: {total_amount}₽

Список (первые 20):
{chr(10).join(payment_list)}

{'...' if pending_payments.count() > 20 else ''}

Перейдите в админ-панель для обработки платежей:
{settings.SITE_URL}/admin/donations/bonuspaymentregistry/

---
Это автоматическое напоминание от системы IdealImage.ru
        """
        
        send_mail(
            subject=subject,
            message=message.strip(),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=admin_emails,
            fail_silently=False,
        )
        
        logger.info(f'Напоминание о {pending_payments.count()} платежах отправлено')
        
        return {
            'success': True,
            'message': f'Отправлено напоминание о {pending_payments.count()} платежах',
            'pending_count': pending_payments.count(),
            'total_amount': float(total_amount)
        }
    
    except Exception as e:
        logger.error(f'Ошибка при отправке напоминаний о платежах: {str(e)}')
        return {
            'success': False,
            'error': str(e)
        }


def cleanup_old_stats():
    """
    Задача очистки старой статистики (старше 1 года)
    Запускается раз в месяц (1 числа в 03:00 МСК)
    """
    logger.info('Запуск задачи очистки старой статистики')
    
    try:
        from datetime import timedelta
        from .models import AuthorStats
        
        # Удаляем статистику старше 1 года
        one_year_ago = timezone.now() - timedelta(days=365)
        
        old_stats = AuthorStats.objects.filter(
            period_type='week',
            period_start__lt=one_year_ago
        )
        
        count = old_stats.count()
        old_stats.delete()
        
        logger.info(f'Удалено {count} записей старой статистики')
        
        return {
            'success': True,
            'message': f'Удалено {count} записей старой статистики',
            'deleted_count': count
        }
    
    except Exception as e:
        logger.error(f'Ошибка при очистке старой статистики: {str(e)}')
        return {
            'success': False,
            'error': str(e)
        }

