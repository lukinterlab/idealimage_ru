"""
Система автопостинга спаршенных статей.

Генерирует полные статьи через GigaChat на основе спаршенного контента
и публикует их на сайте.
"""
import logging
import base64
from typing import Dict, List
from django.utils import timezone
from django.utils.html import strip_tags
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from blog.models import Post
from .models import ParsedArticle
from ..gigachat_api import get_gigachat_client
from ..seo_advanced import AdvancedSEOOptimizer
from ..daily_article_generator import submit_post_for_indexing

logger = logging.getLogger(__name__)


def get_ai_user() -> User:
    """Получает или создает пользователя AI."""
    ai_user, _ = User.objects.get_or_create(
        username='ai_assistant',
        defaults={
            'first_name': 'AI',
            'last_name': 'Ассистент',
            'email': 'ai@idealimage.ru',
            'is_active': True
        }
    )
    return ai_user


def autopost_selected_articles() -> Dict:
    """
    Автопостинг выбранных спаршенных статей.
    
    Берет статьи с selected_for_posting=True и:
    1. Генерирует полный текст через GigaChat
    2. Генерирует изображение через GigaChat
    3. Генерирует FAQ блок
    4. Создает и публикует статью
    5. Обновляет статус ParsedArticle
    
    Returns:
        Dict с результатами автопостинга
    """
    logger.info("=" * 60)
    logger.info("📤 НАЧАЛО АВТОПОСТИНГА ВЫБРАННЫХ СТАТЕЙ")
    logger.info("=" * 60)
    
    results = {
        'total_selected': 0,
        'published': 0,
        'failed': 0,
        'errors': []
    }
    
    try:
        # Получаем выбранные статьи
        selected_articles = ParsedArticle.objects.filter(
            selected_for_posting=True,
            status__in=['pending', 'approved']
        ).exclude(
            status='published'  # Уже опубликованные пропускаем
        )
        
        results['total_selected'] = selected_articles.count()
        logger.info(f"📋 Найдено выбранных статей: {results['total_selected']}")
        
        if results['total_selected'] == 0:
            logger.info("⏭️ Нет выбранных статей для публикации")
            return results
        
        # Получаем AI пользователя
        ai_user = get_ai_user()
        
        # Получаем GigaChat клиент
        gigachat = get_gigachat_client()
        if not gigachat or not gigachat.client:
            error_msg = "GigaChat клиент недоступен"
            logger.error(f"❌ {error_msg}")
            results['errors'].append(error_msg)
            return results
        
        # Получаем SEO оптимизатор
        seo_optimizer = AdvancedSEOOptimizer()
        
        # Обрабатываем каждую выбранную статью
        for parsed_article in selected_articles:
            try:
                logger.info(f"📄 Обработка статьи: {parsed_article.title[:50]}...")
                
                # ШАГ 1: Генерируем полный текст через GigaChat
                logger.info(f"   🤖 Генерация полного текста...")
                
                generation_prompt = f"""Напиши полную статью на основе следующего спаршенного контента:

Заголовок: {parsed_article.title}
Категория: {parsed_article.category.title if parsed_article.category else 'Общее'}
Спаршенный контент: {parsed_article.content}

Требования:
1. Сохрани основную тему и смысл
2. Расширь контент до полноценной статьи (минимум 500 слов)
3. Сделай текст уникальным и интересным
4. Добавь структуру с подзаголовками
5. Используй современный стиль написания
6. Адаптируй под женскую аудиторию

Верни только текст статьи без заголовка."""

                full_content = gigachat.chat(
                    generation_prompt,
                    system_prompt="Ты опытный копирайтер женского журнала, специализирующийся на создании интересного и полезного контента."
                )
                
                if not full_content or len(full_content) < 300:
                    raise Exception("Сгенерированный текст слишком короткий или пустой")
                
                logger.info(f"   ✅ Текст сгенерирован ({len(full_content)} символов)")
                
                # ШАГ 2: Генерируем изображение
                logger.info(f"   🖼️ Генерация изображения...")
                image_prompt = f"Иллюстрация для статьи: {parsed_article.title}"
                image_data = gigachat.generate_image(image_prompt, width=1024, height=1024)
                
                image_saved = False
                if image_data:
                    logger.info(f"   ✅ Изображение сгенерировано")
                else:
                    logger.warning(f"   ⚠️ Не удалось сгенерировать изображение")
                
                # ШАГ 3: Генерируем SEO метаданные
                logger.info(f"   🔍 Генерация SEO метаданных...")
                try:
                    seo_data = gigachat.generate_seo_metadata(
                        title=parsed_article.title,
                        content=strip_tags(full_content)[:500],
                        keywords=[parsed_article.category.title] if parsed_article.category else [],
                        category=parsed_article.category.title if parsed_article.category else ""
                    )
                except Exception as e:
                    logger.warning(f"   ⚠️ Ошибка генерации SEO: {e}")
                    seo_data = {}
                
                # ШАГ 4: Создаем статью
                logger.info(f"   💾 Создание статьи...")
                new_article = Post.objects.create(
                    title=parsed_article.title[:200],
                    content=full_content,
                    category=parsed_article.category,
                    author=ai_user,
                    status='published',
                    description=parsed_article.content[:300] or "",
                    meta_title=seo_data.get('meta_title', '')[:60] if seo_data else '',
                    meta_description=seo_data.get('meta_description', '')[:160] if seo_data else '',
                    focus_keyword=seo_data.get('focus_keyword', '')[:100] if seo_data else '',
                    og_title=seo_data.get('og_title', '')[:60] if seo_data else '',
                    og_description=seo_data.get('og_description', '')[:160] if seo_data else '',
                )
                
                # Загружаем изображение, если сгенерировано
                if image_data:
                    try:
                        # Декодируем base64
                        if isinstance(image_data, str):
                            if 'base64,' in image_data:
                                image_data = image_data.split('base64,')[1]
                            image_bytes = base64.b64decode(image_data)
                        else:
                            image_bytes = image_data
                        
                        # Сохраняем изображение
                        img_name = f"autopost_{new_article.id}_{int(timezone.now().timestamp())}.jpg"
                        img_path = default_storage.save(f"images/{img_name}", ContentFile(image_bytes))
                        new_article.kartinka = img_path
                        new_article.save()
                        image_saved = True
                        logger.info(f"   ✅ Изображение загружено")
                    except Exception as e:
                        logger.warning(f"   ⚠️ Ошибка загрузки изображения: {e}")
                
                # ШАГ 5: Генерируем FAQ блок
                logger.info(f"   📝 Генерация FAQ блока...")
                try:
                    faq_result = seo_optimizer.generate_faq_block(new_article)
                    if faq_result.get('success') and faq_result.get('html'):
                        new_article.content += '\n\n' + faq_result['html']
                        new_article.save()
                        logger.info(f"   ✅ FAQ блок добавлен")
                except Exception as e:
                    logger.warning(f"   ⚠️ Ошибка генерации FAQ: {e}")
                
                # ШАГ 6: Обновляем статус ParsedArticle
                parsed_article.status = 'published'
                parsed_article.published_article = new_article
                parsed_article.selected_for_posting = False  # Снимаем флаг выбора
                parsed_article.save()
                
                # ШАГ 7: Отправляем на индексацию
                logger.info(f"   📤 Отправка на индексацию...")
                try:
                    submit_post_for_indexing(new_article.id)
                    logger.info(f"   ✅ Отправлено на индексацию")
                except Exception as e:
                    logger.warning(f"   ⚠️ Ошибка индексации: {e}")
                
                results['published'] += 1
                logger.info(f"✅ Статья опубликована: {new_article.title} (ID: {new_article.id})")
                
            except Exception as e:
                error_msg = f"Ошибка публикации статьи {parsed_article.id}: {str(e)}"
                logger.error(f"❌ {error_msg}", exc_info=True)
                results['errors'].append(error_msg)
                results['failed'] += 1
                
                # Обновляем статус на failed
                parsed_article.status = 'pending'  # Возвращаем в pending для повторной попытки
                parsed_article.notes = f"Ошибка автопостинга: {str(e)}"
                parsed_article.save()
        
        logger.info("=" * 60)
        logger.info("📊 РЕЗУЛЬТАТЫ АВТОПОСТИНГА:")
        logger.info(f"   Выбрано статей: {results['total_selected']}")
        logger.info(f"   Успешно опубликовано: {results['published']}")
        logger.info(f"   Ошибок: {results['failed']}")
        if results['errors']:
            logger.warning("   Список ошибок:")
            for error in results['errors']:
                logger.warning(f"      - {error}")
        logger.info("=" * 60)
        
    except Exception as e:
        error_msg = f"Критическая ошибка автопостинга: {str(e)}"
        logger.error(f"❌ {error_msg}", exc_info=True)
        results['errors'].append(error_msg)
    
    return results

