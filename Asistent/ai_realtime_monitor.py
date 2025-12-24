"""
AI Agent - Мониторинг в РЕАЛЬНОМ ВРЕМЕНИ
Реагирует МГНОВЕННО на все события на сайте
"""
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# МОНИТОРИНГ СТАТЕЙ В РЕАЛЬНОМ ВРЕМЕНИ
# =============================================================================
@receiver(post_save, sender='blog.Post')
def monitor_new_post(sender, instance, created, **kwargs):
    """
    AI Agent моментально реагирует на новые статьи
    ПОЛНОСТЬЮ БЕЗОПАСНАЯ ВЕРСИЯ: не прерывает сохранение поста при любых ошибках
    
    ВРЕМЕННО ОТКЛЮЧЕНО: требуется применить миграции для поля conversation_id
    """
    return  # ВРЕМЕННО ОТКЛЮЧЕНО до применения миграций
    
    # Мониторинг работает только для новых статей
    if not created:
        return
    
    try:
        from .models import AIConversation, AIMessage
        
        # Получаем admin для логирования
        try:
            admin = User.objects.filter(is_superuser=True).first()
            if not admin:
                logger.debug("Нет суперпользователя для мониторинга")
                return
        except Exception as e:
            logger.error(f"Ошибка получения admin для мониторинга: {e}")
            return
        
        # Создаём/получаем диалог
        try:
            conversation, _ = AIConversation.objects.get_or_create(
                admin=admin,
                title='🔴 Мониторинг в реальном времени',
                defaults={'is_active': True}
            )
        except Exception as e:
            logger.error(f"❌ Не удалось создать conversation для мониторинга: {e}")
            return
        
        # Формируем отчёт
        try:
            message = f"📝 НОВАЯ СТАТЬЯ!\n\n"
            message += f"Заголовок: {instance.title}\n"
            message += f"Автор: {instance.author.username}\n"
            message += f"Категория: {instance.category.title if instance.category else 'Не указана'}\n"
            message += f"Статус: {instance.status}\n"
            
            # ПРОВЕРКА #1: Есть ли изображение?
            if not instance.kartinka:
                message += f"\n❌ КРИТИЧНО: Статья БЕЗ изображения!\n"
                message += f"📋 Действие: Оставлена в статусе {instance.status}\n"
                message += f"💡 Рекомендация: Добавьте изображение вручную\n"
            else:
                message += f"\n✅ Изображение: Есть\n"
            
            # ПРОВЕРКА #2: Длина текста
            text_length = len(instance.content) if instance.content else 0
            if text_length < 1500:
                message += f"\n⚠️ ВНИМАНИЕ: Текст короткий ({text_length} символов)\n"
                message += f"📋 Минимум: 1500 символов\n"
        except Exception as e:
            logger.error(f"Ошибка формирования отчёта мониторинга: {e}")
            message = f"📝 Новая статья создана: {getattr(instance, 'title', 'без названия')}"
        
        # Сохраняем отчёт в БД
        try:
            AIMessage.objects.create(
                conversation=conversation,
                role='assistant',
                content=message
            )
            logger.info(f"✅ AI Agent отреагировал на новую статью: {instance.title}")
        except Exception as e:
            logger.error(f"❌ Не удалось создать AIMessage для мониторинга: {e}")
            # Не прерываем процесс!
    
    except Exception as e:
        logger.error(f"❌ Критическая ошибка AI мониторинга статьи: {e}", exc_info=True)
        # НЕ ПРЕРЫВАЕМ СОХРАНЕНИЕ ПОСТА!


# ========================================================================
# МОНИТОРИНГ КОММЕНТАРИЕВ В РЕАЛЬНОМ ВРЕМЕНИ
# ========================================================================
@receiver(post_save, sender='blog.Comment')
def monitor_new_comment(sender, instance, created, **kwargs):
    """
    AI Agent моментально реагирует на новые комментарии
    """
    from .models import AIConversation, AIMessage
    
    if not created:
        return
    
    try:
        admin = User.objects.filter(is_superuser=True).first()
        if not admin:
            return
        
        conversation, _ = AIConversation.objects.get_or_create(
            admin=admin,
            title='🔴 Мониторинг в реальном времени',
            defaults={'is_active': True}
        )
        
        # Проверка на спам/мат
        raw_comment = getattr(instance, 'content', None)
        if raw_comment is None:
            raw_comment = getattr(instance, 'text', '')
        comment_text = (raw_comment or "").lower()
        
        # Простая проверка на запрещённые слова
        forbidden_words = ['спам', 'реклама', 'купить', 'дёшево', 'скидка']
        has_spam = any(word in comment_text for word in forbidden_words)
        
        if has_spam or len(comment_text) < 10:
            message = f"💬 ПОДОЗРИТЕЛЬНЫЙ КОММЕНТАРИЙ!\n\n"
            message += f"Автор: {instance.author_comment}\n"
            message += f"Статья: {instance.post.title}\n"
            message += f"Текст: {comment_text[:100]}...\n\n"
            
            if has_spam:
                message += f"⚠️ Обнаружены подозрительные слова\n"
            if len(comment_text) < 10:
                message += f"⚠️ Слишком короткий комментарий ({len(comment_text)} символов)\n"
            
            message += f"\n📋 Рекомендация: Проверьте и одобрите/удалите вручную"
            
            AIMessage.objects.create(
                conversation=conversation,
                role='assistant',
                content=message
            )
            
            logger.info(f"⚠️ AI Agent обнаружил подозрительный комментарий")
    
    except Exception as e:
        logger.error(f"Ошибка AI мониторинга комментария: {e}")


# =============================================================================
# МОНИТОРИНГ РЕКЛАМЫ В РЕАЛЬНОМ ВРЕМЕНИ
# =============================================================================
@receiver(post_save, sender='advertising.AdClick')
def monitor_ad_click(sender, instance, created, **kwargs):
    """
    AI Agent анализирует клики по рекламе в реальном времени
    """
    if not created:
        return
    
    try:
        from advertising.models import AdImpression
        
        # Получаем статистику баннера
        banner = instance.banner
        clicks = banner.clicks.count()
        impressions = AdImpression.objects.filter(banner=banner).count()
        
        # Если достаточно данных - проверяем CTR
        if impressions >= 100:
            ctr = (clicks / impressions) * 100
            
            # Если CTR очень низкий - уведомляем
            if ctr < 0.5:
                admin = User.objects.filter(is_superuser=True).first()
                if not admin:
                    return
                
                from Asistent.models import AIConversation, AIMessage
                
                conversation, _ = AIConversation.objects.get_or_create(
                    admin=admin,
                    title='🔴 Мониторинг в реальном времени',
                    defaults={'is_active': True}
                )
                
                message = f"📢 ПРОБЛЕМА С РЕКЛАМОЙ!\n\n"
                message += f"Баннер: {banner.name}\n"
                message += f"Место: {banner.place.name}\n"
                message += f"CTR: {ctr:.2f}% (ОЧЕНЬ НИЗКИЙ!)\n"
                message += f"Показов: {impressions}\n"
                message += f"Кликов: {clicks}\n\n"
                message += f"💡 Рекомендация:\n"
                message += f"  - Измените дизайн баннера\n"
                message += f"  - Проверьте релевантность контента\n"
                message += f"  - Попробуйте другое изображение/текст"
                
                AIMessage.objects.create(
                    conversation=conversation,
                    role='assistant',
                    content=message
                )
                
                logger.warning(f"⚠️ AI Agent обнаружил низкий CTR: {banner.name} ({ctr:.2f}%)")
    
    except Exception as e:
        logger.error(f"Ошибка AI мониторинга рекламы: {e}")


# =============================================================================
# МОНИТОРИНГ ДОНАТОВ В РЕАЛЬНОМ ВРЕМЕНИ
# =============================================================================
@receiver(post_save, sender='donations.Donation')
def monitor_new_donation(sender, instance, created, **kwargs):
    """
    AI Agent моментально реагирует на новые донаты
    """
    if not created:
        return
    
    try:
        admin = User.objects.filter(is_superuser=True).first()
        if not admin:
            return
        
        from Asistent.models import AIConversation, AIMessage
        
        conversation, _ = AIConversation.objects.get_or_create(
            admin=admin,
            title='🔴 Мониторинг в реальном времени',
            defaults={'is_active': True}
        )
        
        message = f"💰 НОВЫЙ ДОНАТ!\n\n"
        message += f"Сумма: {instance.amount}₽\n"
        message += f"От: {instance.donor.username if instance.donor else 'Анонимно'}\n"
        message += f"Статус: {instance.status}\n"
        
        if instance.amount >= 1000:
            message += f"\n🎉 КРУПНЫЙ ДОНАТ! Спасибо донору!"
        
        message += f"\n📋 Действие: Ожидает обработки через систему распределения"
        
        AIMessage.objects.create(
            conversation=conversation,
            role='assistant',
            content=message
        )
        
        logger.info(f"💰 AI Agent зарегистрировал новый донат: {instance.amount}₽")
    
    except Exception as e:
        logger.error(f"Ошибка AI мониторинга доната: {e}")


# =============================================================================
# МОНИТОРИНГ ЗАДАЧ В РЕАЛЬНОМ ВРЕМЕНИ
# =============================================================================
@receiver(post_save, sender='Asistent.AITask')
def monitor_task_status(sender, instance, created, **kwargs):
    """
    AI Agent отслеживает статус задач в реальном времени
    """
    try:
        # Если задача провалилась - уведомляем
        if instance.status == 'failed' and instance.error_message:
            admin = User.objects.filter(is_superuser=True).first()
            if not admin:
                return
            
            from Asistent.models import AIConversation, AIMessage
            
            conversation, _ = AIConversation.objects.get_or_create(
                admin=admin,
                title='🔴 Мониторинг в реальном времени',
                defaults={'is_active': True}
            )
            
            message = f"❌ ЗАДАЧА ПРОВАЛИЛАСЬ!\n\n"
            message += f"Тип: {instance.task_type}\n"
            message += f"Ошибка: {instance.error_message}\n"
            message += f"Время: {instance.started_at.strftime('%H:%M:%S') if instance.started_at else 'N/A'}\n\n"
            
            # Анализ ошибки
            error_lower = instance.error_message.lower()
            
            if 'изображение' in error_lower or 'image' in error_lower:
                message += f"💡 ПРИЧИНА: Проблема с изображением\n"
                message += f"📋 Решение:\n"
                message += f"  - Проверьте API ключи (Unsplash, Pixabay)\n"
                message += f"  - Добавьте изображения в media/stock_images/\n"
            elif 'время' in error_lower or 'working_hours' in error_lower:
                message += f"💡 ПРИЧИНА: Вне рабочего времени (8:00-21:00)\n"
                message += f"📋 Решение: Задача будет повторена автоматически в 09:00\n"
            elif 'уникальн' in error_lower or 'duplicate' in error_lower:
                message += f"💡 ПРИЧИНА: Изображение уже использовано\n"
                message += f"📋 Решение: Система попытается найти другое изображение\n"
            else:
                message += f"💡 Рекомендация: Проверьте логи для подробностей\n"
            
            AIMessage.objects.create(
                conversation=conversation,
                role='assistant',
                content=message
            )
            
            logger.warning(f"❌ AI Agent зарегистрировал провал задачи: {instance.task_type}")
    
    except Exception as e:
        logger.error(f"Ошибка AI мониторинга задачи: {e}")


# =============================================================================
# МЕТРИКИ УДАЛЕНЫ - не использовались
# =============================================================================

