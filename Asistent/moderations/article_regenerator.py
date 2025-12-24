"""
Система регенерации старых статей.

Выбирает самые старые статьи с минимальными просмотрами (по 1 из каждой категории),
генерирует новый контент через GigaChat и обновляет старые статьи.
"""
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from django.utils import timezone
from django.utils.html import strip_tags
from django.contrib.auth.models import User
from django.db import transaction

from blog.models import Post, Category
from .models import ArticleRegeneration
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


def update_dates_in_text(text: str, old_date: datetime, new_date: datetime) -> str:
    """
    Обновляет даты в тексте на современные.
    
    Args:
        text: Исходный текст
        old_date: Старая дата
        new_date: Новая дата
    
    Returns:
        Текст с обновленными датами
    """
    # Паттерны для поиска дат
    date_patterns = [
        # "5 ноября 2023" -> "5 ноября 2025"
        (r'(\d{1,2})\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+(\d{4})', 
         lambda m: f"{m.group(1)} {m.group(2)} {new_date.year}"),
        # "2023 год" -> "2025 год"
        (r'(\d{4})\s+год', lambda m: f"{new_date.year} год"),
        # "в 2023 году" -> "в 2025 году"
        (r'в\s+(\d{4})\s+году', lambda m: f"в {new_date.year} году"),
        # "01.01.2023" -> "01.01.2025"
        (r'(\d{1,2})\.(\d{1,2})\.(\d{4})', lambda m: f"{m.group(1)}.{m.group(2)}.{new_date.year}"),
    ]
    
    updated_text = text
    for pattern, replacement in date_patterns:
        updated_text = re.sub(pattern, replacement, updated_text, flags=re.IGNORECASE)
    
    return updated_text


def regenerate_old_articles(limit_per_category: int = 1) -> Dict:
    """
    Регенерирует старые статьи с минимальными просмотрами.
    
    Выбирает по 1 статье из каждой категории (всего 9 категорий),
    генерирует новый контент и обновляет старые статьи.
    
    Args:
        limit_per_category: Количество статей на категорию (по умолчанию 1)
    
    Returns:
        Dict с результатами регенерации
    """
    logger.info("🔄 Начало регенерации старых статей")
    
    results = {
        'total_categories': 0,
        'articles_found': 0,
        'regenerated': 0,
        'failed': 0,
        'errors': []
    }
    
    try:
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
        
        # Получаем все категории (только корневые, без вложенных)
        categories = Category.objects.filter(parent=None, posts__isnull=False).distinct()
        results['total_categories'] = categories.count()
        
        logger.info(f"📋 Найдено категорий: {results['total_categories']}")
        
        # Для каждой категории выбираем самую старую статью с минимальными просмотрами
        for category in categories:
            try:
                # Ищем статьи, которые еще не регенерировались сегодня
                today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
                already_regenerated_today = ArticleRegeneration.objects.filter(
                    regenerated_at__gte=today_start,
                    original_article__category=category
                ).values_list('original_article_id', flat=True)
                
                # Выбираем самую старую статью с минимальными просмотрами
                old_article = Post.objects.filter(
                    category=category,
                    status='published',
                    created__lt=timezone.now() - timedelta(days=30)  # Старше 30 дней
                ).exclude(
                    id__in=already_regenerated_today
                ).order_by('views', 'created').first()
                
                if not old_article:
                    logger.warning(f"⚠️ Не найдено старых статей для категории: {category.title}")
                    continue
                
                results['articles_found'] += 1
                logger.info(f"📄 Обработка статьи: {old_article.title} (ID: {old_article.id}, просмотров: {old_article.views})")
                
                # Создаем запись о регенерации
                regeneration = ArticleRegeneration.objects.create(
                    original_article=old_article,
                    status='pending'
                )
                
                try:
                    # ШАГ 1: Генерируем новый текст через GigaChat
                    logger.info(f"   🤖 Генерация нового текста...")
                    old_content = strip_tags(old_article.content or "")
                    
                    # Обновляем даты в старом контенте для промпта
                    old_date = old_article.created
                    new_date = timezone.now()
                    updated_content = update_dates_in_text(old_content, old_date, new_date)
                    
                    # Формируем промпт для регенерации
                    regeneration_prompt = f"""Перепиши следующую статью, сделав её актуальной и современной:

Оригинальная статья:
Заголовок: {old_article.title}
Категория: {category.title}
Текст: {updated_content[:2000]}

Требования:
1. Сохрани основную тему и смысл статьи
2. Обнови все даты на {new_date.strftime('%d %B %Y')}
3. Сделай текст более современным и актуальным
4. Улучши структуру и читаемость
5. Добавь актуальную информацию, если это уместно
6. Минимум 500 слов

Верни только текст статьи без заголовка."""

                    new_content = gigachat.chat(
                        regeneration_prompt,
                        system_prompt="Ты опытный копирайтер, специализирующийся на создании актуального контента."
                    )
                    
                    if not new_content or len(new_content) < 200:
                        raise Exception("Сгенерированный текст слишком короткий или пустой")
                    
                    # Обновляем даты в новом тексте
                    new_content = update_dates_in_text(new_content, old_date, new_date)
                    
                    logger.info(f"   ✅ Текст сгенерирован ({len(new_content)} символов)")
                    
                    # ШАГ 2: Генерируем новое изображение
                    logger.info(f"   🖼️ Генерация изображения...")
                    image_prompt = f"Иллюстрация для статьи: {old_article.title}"
                    image_data = gigachat.generate_image(image_prompt, width=1024, height=1024)
                    
                    image_saved = False
                    if image_data:
                        logger.info(f"   ✅ Изображение сгенерировано")
                    
                    # ШАГ 3: Обновляем заголовок (обновляем даты)
                    new_title = update_dates_in_text(old_article.title, old_date, new_date)
                    # Ограничиваем длину заголовка
                    if len(new_title) > 200:
                        new_title = new_title[:197] + "..."
                    
                    # ШАГ 4: Создаем новую статью
                    logger.info(f"   💾 Создание новой статьи...")
                    new_article = Post.objects.create(
                        title=new_title,
                        content=new_content,
                        category=category,
                        author=ai_user,
                        status='published',
                        description=old_article.description or "",
                        # Копируем SEO поля
                        meta_title=old_article.meta_title or "",
                        meta_description=old_article.meta_description or "",
                        focus_keyword=old_article.focus_keyword or "",
                        og_title=old_article.og_title or "",
                        og_description=old_article.og_description or "",
                    )
                    
                    # Загружаем изображение, если сгенерировано
                    if image_data:
                        try:
                            import base64
                            from django.core.files.base import ContentFile
                            from django.core.files.storage import default_storage
                            
                            # Декодируем base64
                            if isinstance(image_data, str):
                                # Убираем префикс data:image если есть
                                if 'base64,' in image_data:
                                    image_data = image_data.split('base64,')[1]
                                image_bytes = base64.b64decode(image_data)
                            else:
                                image_bytes = image_data
                            
                            # Сохраняем изображение
                            img_name = f"regenerated_{new_article.id}_{int(timezone.now().timestamp())}.jpg"
                            img_path = default_storage.save(f"images/{img_name}", ContentFile(image_bytes))
                            new_article.kartinka = img_path
                            new_article.save()
                            image_saved = True
                            logger.info(f"   ✅ Изображение загружено")
                        except Exception as e:
                            logger.warning(f"   ⚠️ Ошибка загрузки изображения: {e}")
                    else:
                        logger.warning(f"   ⚠️ Не удалось сгенерировать изображение")
                    
                    # Обновляем запись о регенерации
                    regeneration.regenerated_article = new_article
                    regeneration.status = 'completed'
                    regeneration.regeneration_notes = f"Успешно регенерировано. Старая статья: {old_article.views} просмотров"
                    regeneration.save()
                    
                    logger.info(f"   ✅ Новая статья создана (ID: {new_article.id})")
                    
                    # ШАГ 5: Обновляем старую статью
                    logger.info(f"   🔧 Обновление старой статьи...")
                    
                    # Проверяем, есть ли FAQ в старой статье
                    old_content_lower = (old_article.content or "").lower()
                    has_faq = 'faq-section' in old_content_lower or 'часто задаваемые вопросы' in old_content_lower
                    
                    if not has_faq:
                        # Генерируем FAQ блок
                        logger.info(f"   📝 Генерация FAQ блока...")
                        faq_result = seo_optimizer.generate_faq_block(old_article)
                        if faq_result.get('success') and faq_result.get('html'):
                            old_article.content += '\n\n' + faq_result['html']
                            logger.info(f"   ✅ FAQ блок добавлен")
                    
                    # Оптимизируем мета-теги
                    logger.info(f"   🔍 Оптимизация мета-тегов...")
                    if not old_article.meta_title or not old_article.meta_description:
                        try:
                            seo_data = gigachat.generate_seo_metadata(
                                title=old_article.title,
                                content=strip_tags(old_article.content or "")[:500],
                                keywords=[category.title] if category.title else [],
                                category=category.title or ""
                            )
                            if seo_data:
                                old_article.meta_title = seo_data.get('meta_title', '')[:60]
                                old_article.meta_description = seo_data.get('meta_description', '')[:160]
                                old_article.og_title = seo_data.get('og_title', '')[:60]
                                old_article.og_description = seo_data.get('og_description', '')[:160]
                                logger.info(f"   ✅ Мета-теги оптимизированы")
                        except Exception as e:
                            logger.warning(f"   ⚠️ Ошибка оптимизации мета-тегов: {e}")
                    
                    # Сохраняем обновленную старую статью
                    old_article._skip_auto_moderation = True  # Пропускаем модерацию
                    old_article.save()
                    
                    # Отправляем на индексацию
                    logger.info(f"   📤 Отправка на индексацию...")
                    try:
                        submit_post_for_indexing(old_article.id)
                        logger.info(f"   ✅ Отправлено на индексацию")
                    except Exception as e:
                        logger.warning(f"   ⚠️ Ошибка индексации: {e}")
                    
                    results['regenerated'] += 1
                    logger.info(f"✅ Статья регенерирована: {old_article.title} → {new_article.title}")
                    
                except Exception as e:
                    error_msg = f"Ошибка регенерации статьи {old_article.id}: {str(e)}"
                    logger.error(f"❌ {error_msg}", exc_info=True)
                    results['errors'].append(error_msg)
                    results['failed'] += 1
                    
                    regeneration.status = 'failed'
                    regeneration.regeneration_notes = f"Ошибка: {str(e)}"
                    regeneration.save()
                    
            except Exception as e:
                error_msg = f"Ошибка обработки категории {category.title}: {str(e)}"
                logger.error(f"❌ {error_msg}", exc_info=True)
                results['errors'].append(error_msg)
        
        logger.info(f"✅ Регенерация завершена: найдено {results['articles_found']}, регенерировано {results['regenerated']}, ошибок {results['failed']}")
        
    except Exception as e:
        error_msg = f"Критическая ошибка регенерации: {str(e)}"
        logger.error(f"❌ {error_msg}", exc_info=True)
        results['errors'].append(error_msg)
    
    return results

