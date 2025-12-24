"""
Сигналы для автоматической синхронизации расписаний с Django-Q.
Создаёт, обновляет и удаляет задачи в Django-Q при изменении AISchedule.
"""
from datetime import time as dtime

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django_q.models import Schedule
from django.utils import timezone
import logging

from .models import AISchedule

logger = logging.getLogger(__name__)


@receiver(post_save, sender=AISchedule)
def sync_ai_schedule_on_save(sender, instance, created, **kwargs):
    """
    Автоматически создает/обновляет Schedule в Django-Q
    при сохранении AISchedule
    """
    if not instance.is_active:
        # Если расписание неактивно - удаляем из Django-Q
        schedule_name = f'ai_schedule_{instance.id}'
        try:
            dq_schedule = Schedule.objects.get(name=schedule_name)
            dq_schedule.delete()
            logger.info(f"🗑️ Удалено неактивное расписание {schedule_name}")
        except Schedule.DoesNotExist:
            pass
        return
    
    # Создаем или обновляем расписание в Django-Q
    schedule_name = f'ai_schedule_{instance.id}'
    
    config = _build_django_q_schedule(instance)
    if not config:
        logger.warning("⚠️ Не удалось построить расписание для %s", instance)
        return

    try:
        dq_schedule = Schedule.objects.get(name=schedule_name)
        _apply_schedule_config(dq_schedule, config)
        logger.info("♻️ Обновлено расписание %s [%s]", instance.name, config.get('description', ''))
    except Schedule.DoesNotExist:
        Schedule.objects.create(**_cleanup_schedule_kwargs(config))
        logger.info("✨ Создано расписание %s [%s]", instance.name, config.get('description', ''))


@receiver(post_delete, sender=AISchedule)
def delete_schedule_on_ai_schedule_delete(sender, instance, **kwargs):
    """
    Автоматически удаляет Schedule из Django-Q
    при удалении AISchedule
    """
    schedule_name = f'ai_schedule_{instance.id}'
    try:
        dq_schedule = Schedule.objects.get(name=schedule_name)
        dq_schedule.delete()
        logger.info(f"🗑️ Удалено расписание {schedule_name} после удаления AISchedule")
    except Schedule.DoesNotExist:
        pass


# ============================================================================
# Вспомогательные функции для построения Django-Q Schedule
# ============================================================================

def get_interval_minutes(frequency):
    """Преобразует частоту в минуты"""
    frequency_map = {
        'hourly': 60,
        'every_2_hours': 120,
        'every_3_hours': 180,
        'every_4_hours': 240,
        'every_6_hours': 360,
        'every_8_hours': 480,
        'every_12_hours': 720,
        'daily': 1440,
        'twice_daily': 720,
        'weekly': 10080,
    }
    
    return frequency_map.get(frequency)


def _default_time():
    """Возвращает время по умолчанию для запуска расписания"""
    return dtime(hour=8, minute=0)


def _build_django_q_schedule(instance):
    """Формирует конфигурацию для Django-Q с учётом schedule_kind."""
    base = {
        'name': f'ai_schedule_{instance.id}',
        'func': 'Asistent.schedule.tasks.run_specific_schedule',  # Обновлённый путь
        'args': f'{instance.id}',
        'task': f'schedule:{instance.id}',
        'repeats': -1,
        'next_run': instance.next_run or timezone.now(),
    }

    kind = (instance.schedule_kind or 'daily').lower()
    description = kind

    if kind == 'interval':
        minutes = instance.interval_minutes or get_interval_minutes(instance.posting_frequency) or 60
        base.update({
            'schedule_type': Schedule.MINUTES,
            'minutes': minutes,
            'cron': '',
        })
        description = f'каждые {minutes} мин'
    else:
        cron_expr = _resolve_cron_expression(instance, kind)
        if not cron_expr:
            return None
        base.update({
            'schedule_type': Schedule.CRON,
            'cron': cron_expr,
            'minutes': None,
        })
        description = f'cron {cron_expr}'

    base['description'] = description
    return base


def _resolve_cron_expression(instance, kind):
    """Формирует CRON-выражение в зависимости от типа расписания"""
    time_point = instance.scheduled_time or _default_time()
    minute, hour = time_point.minute, time_point.hour

    if kind == 'cron':
        cron_expr = (instance.cron_expression or '').strip()
        if cron_expr:
            return cron_expr
        return f"{minute} {hour} * * *"
    if kind == 'weekly':
        weekday = instance.weekday if instance.weekday is not None else 0
        return f"{minute} {hour} * * {weekday}"
    # daily и остальные по умолчанию
    return f"{minute} {hour} * * *"


def _apply_schedule_config(dq_schedule, config):
    """Применяет конфигурацию к существующему Django-Q Schedule"""
    dq_schedule.schedule_type = config['schedule_type']
    dq_schedule.func = config['func']
    dq_schedule.args = config['args']
    dq_schedule.task = config['task']
    dq_schedule.repeats = config['repeats']
    dq_schedule.next_run = config['next_run']

    if config['schedule_type'] == Schedule.CRON:
        dq_schedule.cron = config['cron']
        dq_schedule.minutes = None
    else:
        dq_schedule.minutes = config['minutes']
        dq_schedule.cron = ''

    dq_schedule.save()


def _cleanup_schedule_kwargs(config):
    """Удаляет вспомогательные ключи перед созданием Schedule."""
    payload = config.copy()
    payload.pop('description', None)
    if payload.get('schedule_type') == Schedule.CRON:
        payload.pop('minutes', None)
    else:
        payload.pop('cron', None)
    return payload

