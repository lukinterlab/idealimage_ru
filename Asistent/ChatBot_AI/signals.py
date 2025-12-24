"""
Сигналы для чат-бота

Автоматическая генерация embeddings для FAQ
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
import logging

logger = logging.getLogger(__name__)

# Кеш для отслеживания изменений
_faq_old_content = {}


@receiver(pre_save, sender='ChatBot_AI.ChatbotFAQ')
def track_faq_content_change(sender, instance, **kwargs):
    """Отслеживаем изменение FAQ перед сохранением"""
    if not instance.pk:
        return

    try:
        from .models import ChatbotFAQ
        from Asistent.services.embedding import cache_previous_state
        
        cache_previous_state(
            _faq_old_content,
            instance,
            model_cls=ChatbotFAQ,
            fields=('question', 'answer'),
            extra_fields=('embedding',),
        )
    except Exception as exc:
        logger.warning("⚠️ Не удалось сохранить предыдущее состояние ChatbotFAQ: %s", exc)


@receiver(post_save, sender='ChatBot_AI.ChatbotFAQ')
def generate_faq_embedding(sender, instance, created, **kwargs):
    """Автоматически генерирует embeddings для FAQ"""
    
    if getattr(instance, '_skip_embedding_generation', False):
        return
    
    try:
        from .models import ChatbotFAQ
        from Asistent.services.embedding import should_regenerate_embedding, store_embedding
        
        should_generate = should_regenerate_embedding(
            _faq_old_content,
            instance,
            created=created,
            fields=('question', 'answer'),
            embedding_field='embedding',
        )

        if not should_generate:
            return
        
        if created:
            logger.info("📊 Новый FAQ: %s...", instance.question[:50])
        else:
            logger.info("📊 Обновление FAQ: %s...", instance.question[:50])
        
        try:
            from Asistent.gigachat_api import get_embeddings
            
            # Формируем текст: вопрос + ответ
            text_for_embedding = f"{instance.question}\n\n{instance.answer}"
            
            logger.info(f"   🔄 Генерация embeddings для FAQ...")
            embedding = get_embeddings(text_for_embedding)
            
            if store_embedding(
                instance,
                embedding,
                model_cls=ChatbotFAQ,
                skip_flag='_skip_embedding_generation',
            ):
                logger.info("   ✅ Embeddings для FAQ сохранён: %s измерений", len(embedding))
            else:
                logger.warning("   ⚠️ Не удалось получить embeddings для FAQ")
                
        except Exception as e:
            logger.error("   ❌ Ошибка генерации embeddings для FAQ: %s", e)
            
    except Exception as e:
        logger.error("Ошибка в сигнале generate_faq_embedding: %s", e)

