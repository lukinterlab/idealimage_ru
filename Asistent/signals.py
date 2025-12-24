"""
Сигналы для автоматической синхронизации расписаний
"""
from datetime import time as dtime

from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django_q.models import Schedule
from django.utils import timezone
import logging

from Asistent.services.embedding import (
    cache_previous_state,
    should_regenerate_embedding,
    store_embedding,
)
from .models import AISchedule

logger = logging.getLogger(__name__)

"""Сигналы для автоматической синхронизации расписаний"""
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


"""Автоматически удаляет Schedule из Django-Q"""
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



"""Преобразует частоту в минуты"""
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
    return dtime(hour=8, minute=0)


def _build_django_q_schedule(instance):
    """Формирует конфигурацию для Django-Q с учётом schedule_kind."""
    base = {
        'name': f'ai_schedule_{instance.id}',
        'func': 'Asistent.tasks.run_specific_schedule',
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


# ============================================
# Сигналы для системы бонусов
# ============================================
"""Автоматически обрабатывает команды по бонусам из сообщений AI"""
@receiver(post_save, sender='Asistent.AIMessage')
def process_ai_bonus_commands(sender, instance, created, **kwargs):
    """
    Автоматически обрабатывает команды по бонусам из сообщений AI
    """
    # Обрабатываем только новые сообщения от ассистента
    if not created or instance.role != 'assistant':
        return
    
    try:
        from donations.ai_integration import process_ai_message_for_commands
        
        # Обрабатываем сообщение на наличие команд
        results = process_ai_message_for_commands(instance)
        
        if results:
            logger.info(f"Обработано {len(results)} команд по бонусам из сообщения AI")
            for result in results:
                if result.get('success'):
                    logger.info(f"Команда выполнена успешно: {result.get('message')}")
                else:
                    logger.error(f"Ошибка выполнения команды: {result.get('error')}")
    except Exception as e:
        logger.error(f"Ошибка обработки AI команд по бонусам: {str(e)}")


# ============================================
# Векторный поиск: Автогенерация embeddings
# ============================================

# Кэш для отслеживания изменений контента
_knowledge_old_content = {}

"""Отслеживаем изменение контента перед сохранением"""
@receiver(pre_save, sender='Asistent.AIKnowledgeBase')
def track_knowledge_content_change(sender, instance, **kwargs):
    """
    Отслеживаем изменение контента перед сохранением
    чтобы понять нужно ли перегенерировать embeddings
    """
    if not instance.pk:
        return

    try:
        from .models import AIKnowledgeBase

        cache_previous_state(
            _knowledge_old_content,
            instance,
            model_cls=AIKnowledgeBase,
            fields=('title', 'content'),
            extra_fields=('embedding',),
        )
    except Exception as exc:
        logger.warning("⚠️ Не удалось сохранить предыдущее состояние AIKnowledgeBase: %s", exc)


"""Автоматически генерирует embeddings для записи в базе знаний"""
@receiver(post_save, sender='Asistent.AIKnowledgeBase')
def generate_knowledge_embedding(sender, instance, created, **kwargs):
    """
    Автоматически генерирует embeddings для записи в базе знаний
    при создании или изменении title/content
    """
    # Предотвращаем рекурсивный вызов сигнала
    if getattr(instance, '_skip_embedding_generation', False):
        return
    
    should_generate = should_regenerate_embedding(
        _knowledge_old_content,
        instance,
        created=created,
        fields=('title', 'content'),
        embedding_field='embedding',
    )

    if not should_generate:
        return
    
    if created:
        logger.info("📊 Новая запись в базе знаний: %s", instance.title)
    else:
        logger.info("📊 Обновление записи базы знаний: %s", instance.title)
    
    try:
        # Импортируем функцию для получения embeddings
        from .gigachat_api import get_embeddings
        from .models import AIKnowledgeBase
        
        # Формируем текст для векторизации (title + content)
        text_for_embedding = f"{instance.title}\n\n{instance.content}"
        
        logger.info(f"   🔄 Генерация embeddings для '{instance.title[:50]}...'")
        
        # Получаем вектор
        embedding = get_embeddings(text_for_embedding)
        
        if store_embedding(
            instance,
            embedding,
            model_cls=AIKnowledgeBase,
            skip_flag='_skip_embedding_generation',
        ):
            logger.info("   ✅ Embeddings сохранён: %s измерений", len(embedding))

            try:
                from .knowledge_cache import clear_knowledge_cache
                clear_knowledge_cache()
            except ImportError:
                pass
        else:
            logger.warning("   ⚠️ Не удалось получить embeddings для '%s'", instance.title)
            
    except Exception as e:
        logger.error("   ❌ Ошибка генерации embeddings: %s", e)
        # Не пробрасываем исключение - не блокируем сохранение записи


# ============================================
# Embeddings для ChatbotFAQ
# ПЕРЕНЕСЕНО В ChatBot_AI.signals
# ============================================
# Сигналы для чат-бота перенесены в модуль ChatBot_AI:
# - track_faq_content_change() -> ChatBot_AI.signals.track_faq_content_change()
# - generate_faq_embedding() -> ChatBot_AI.signals.generate_faq_embedding()

# ============================================
# Embeddings для AIMessage (только для admin)
# ============================================

"""Автоматически генерирует embeddings для сообщений администратора"""
@receiver(post_save, sender='Asistent.AIMessage')
def generate_message_embedding(sender, instance, created, **kwargs):
    """
    Автоматически генерирует embeddings для сообщений администратора
    Используется для поиска похожих запросов и автоответов
    """
    
    # Генерируем только для новых сообщений от админа
    if not created or instance.role != 'admin':
        return
    
    # Пропускаем если уже есть embedding или установлен флаг
    if instance.embedding or getattr(instance, '_skip_embedding', False):
        return
    
    try:
        from .gigachat_api import get_embeddings
        from .models import AIMessage
        
        logger.info(f"📊 Генерация embedding для сообщения админа: {instance.content[:50]}...")
        
        embedding = get_embeddings(instance.content)
        
        if store_embedding(
            instance,
            embedding,
            model_cls=AIMessage,
            skip_flag='_skip_embedding',
        ):
            logger.info("   ✅ Embedding для сообщения сохранён: %s измерений", len(embedding))
        else:
            logger.warning("   ⚠️ Не удалось получить embedding для сообщения")
            
    except Exception as e:
        logger.error("   ❌ Ошибка генерации embedding для сообщения: %s", e)