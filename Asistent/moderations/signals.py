"""
Сигналы для автоматической модерации контента.

Содержит:
- Автоматическую модерацию комментариев при сохранении
- Заглушку для обратной совместимости (ai_agent_cleanup_database)
"""

from __future__ import annotations

import logging

from django.contrib.auth.models import User
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


def ai_agent_cleanup_database() -> dict:
    """
    Заглушка для обратной совместимости.
    
    Исторически функция удаляла битые статьи из старой системы модерации.
    Сейчас просто возвращает пустой результат для совместимости с legacy-кодом.
    """
    logger.info("ai_agent_cleanup_database: вызвана (заглушка, нет действий)")
    return {
        "deleted_no_image": 0,
        "deleted_broken_image": 0,
        "changed_to_draft": 0,
    }


@receiver(pre_save, sender="blog.Comment")
def moderate_comment_on_save(sender, instance, **_kwargs):
    """
    Автоматическая модерация комментария при сохранении.
    
    Использует упрощённую систему модерации из moderator.py
    Блокирует спам, ссылки, HTML, короткие комментарии и т.п.
    """
    # Проверяем что модерация ещё не выполнялась (защита от повторных вызовов)
    if getattr(instance, "_ai_moderation_processed", False):
        return
    
    # Используем новую упрощённую систему модерации
    from .moderator import check_comment
    
    try:
        # Проверяем комментарий (без автосохранения, чтобы не было рекурсии)
        passed = check_comment(instance, save=False)
        
        # Если комментарий заблокирован - логируем в AI Agent
        if not passed:
            admin = User.objects.filter(is_superuser=True).first()
            if admin:
                # Получаем или создаём диалог с AI Agent
                from Asistent.models import AIConversation, AIMessage
                
                conversation, _ = AIConversation.objects.get_or_create(
                    admin=admin,
                    title="AI Agent - Модерация",
                    defaults={"is_active": True},
                )
                
                # Получаем текст комментария
                content = getattr(instance, "content", None) or getattr(instance, "text", "")
                clean_text = strip_tags(content or "")
                
                # Получаем причины блокировки из последнего лога
                from .models import ModerationLog
                last_log = ModerationLog.objects.filter(
                    content_type='comment',
                    object_id=instance.id if instance.id else 0
                ).order_by('-created_at').first()
                
                problems = last_log.get_problems_list() if last_log else ["Причина не указана"]
                
                # Формируем отчёт для AI Agent
                report_lines = [
                    "🚫 КОММЕНТАРИЙ ЗАБЛОКИРОВАН МОДЕРАЦИЕЙ",
                    "",
                    f"👤 Автор: {getattr(instance, 'author_comment', 'не указан')}",
                    f"📄 Статья: {instance.post.title if getattr(instance, 'post', None) else 'не указана'}",
                    f"💬 Текст: {clean_text[:200]}{'...' if len(clean_text) > 200 else ''}",
                    "",
                    "🔍 Причины блокировки:",
                ] + [f"  • {item}" for item in problems]
                
                # Записываем в диалог с AI Agent
                AIMessage.objects.create(
                    conversation=conversation,
                    role="assistant",
                    content="\n".join(report_lines),
                )
                
                logger.warning(
                    "Комментарий заблокирован автоматической модерацией: автор=%s, проблем=%d",
                    getattr(instance, "author_comment", "—"),
                    len(problems)
                )
    
    except Exception as e:
        logger.error(f"Ошибка автоматической модерации комментария: {e}", exc_info=True)
        # В случае ошибки - разрешаем комментарий (безопасный fallback)
        instance.active = True
        instance._ai_moderation_processed = True

