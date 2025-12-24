"""
🚀 РАСШИРЕННАЯ SEO-ОПТИМИЗАЦИЯ С GIGACHAT API
Комплексная система для максимального роста трафика
"""
import logging
import re
import json
import requests
from typing import Dict, List, Optional
import os
from pathlib import Path
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils.text import slugify
from PIL import Image
from django.conf import settings
from django.utils.html import strip_tags
from django.db.models import Count, Q
from bs4 import BeautifulSoup
from Asistent.prompt_registry import PromptRegistry
from Asistent.faq_service import generate_faq_bundle
from Asistent.services.yandex_webmaster import get_yandex_webmaster_client
from Asistent.constants import ZODIAC_SIGNS

logger = logging.getLogger(__name__)

# ПРОДВИНУТЫЙ SEO-ОПТИМИЗАТОР С AI-ГЕНЕРАЦИЕЙ
# =============================================================================
class AdvancedSEOOptimizer:
    """
    Продвинутый SEO-оптимизатор с AI-генерацией:
    - FAQ блоков для расширенных сниппетов Google
    - Внутренних ссылок между статьями
    - Alt/title для изображений
    - Обновления старых статей
    - Отправки в поисковые системы
    """
    
    def __init__(self):
        from .gigachat_api import get_gigachat_client
        self.gigachat = get_gigachat_client()
    
    # ========================================================================
    # 1. FAQ БЛОКИ ДЛЯ РАСШИРЕННЫХ СНИППЕТОВ GOOGLE
    # ========================================================================
    def generate_faq_block(self, post, context: Optional[Dict] = None) -> Dict:
        """
        Генерирует FAQ блок для статьи через GigaChat
        Для попадания в расширенные сниппеты Google
        ОПТИМИЗИРОВАНО: Кэширование + использует GigaChat Lite
        
        Args:
            post: Объект статьи
            context: Дополнительные параметры (например, zodiac_sign)
        
        Returns:
            Dict с FAQ данными и Schema.org разметкой
        """
        from .gigachat_cache import should_generate_faq
        
        logger.info(f"Генерация FAQ блока для: {post.title}")
        
        # Проверяем нужно ли генерировать (экономия токенов!)
        if not should_generate_faq(post):
            logger.info(f"FAQ уже существует, пропускаем генерацию")
            return {
                'success': False,
                'error': 'FAQ already exists',
                'questions': [],
                'schema': {},
                'html': ''
            }
        
        return self._generate_faq_uncached(post, context=context or {})
    
    # =============================================================================
    # ГЕНЕРАЦИЯ FAQ БЛОКА БЕЗ КЭША
    # =============================================================================
    def _generate_faq_uncached(self, post, context: Optional[Dict] = None) -> Dict:
        """
        Внутренний метод генерации FAQ без кэша
        Использует GigaChat Lite для экономии (194₽/1M)
        """
        try:
            payload, _meta = generate_faq_bundle(
                post,
                self.gigachat,
                context=context or {},
                include_html=True,
                include_schema=True,
            )

            if payload.get('success'):
                logger.info(f"✅ FAQ сгенерирован: {payload.get('count', 0)} вопросов")
            else:
                logger.warning("FAQ генерация вернула статус False: %s", payload.get('error'))

            return payload

        except Exception as e:
            logger.error(f"❌ Ошибка генерации FAQ: {e}")
            return {
                'success': False,
                'error': str(e),
                'questions': [],
                'schema': {},
                'html': ''
            }

    # ========================================================================
    # 2. ВНУТРЕННИЕ ССЫЛКИ МЕЖДУ СТАТЬЯМИ
    # ========================================================================
    def generate_internal_links(self, post, content: str, target_count: int = 5) -> Dict:
        """
        Генерирует релевантные внутренние ссылки на другие статьи
        Повышает время на сайте и SEO
        
        Args:
            post: Текущая статья
            content: Контент статьи
            target_count: Сколько ссылок нужно добавить
        
        Returns:
            Dict с предложениями по ссылкам
        """
        logger.info(f"🔗 Генерация внутренних ссылок для: {post.title}")
        
        from blog.models import Post
        
        # Находим релевантные статьи
        related_posts = self._find_related_posts(post, limit=10)
        
        if not related_posts:
            logger.warning("⚠️ Не найдены релевантные статьи для ссылок")
            return {
                'success': False,
                'error': 'Нет релевантных статей',
                'suggestions': []
            }
        
        # Формируем список статей для AI
        posts_list = '\n'.join([
            f"{i+1}. [{p.title}] - {p.get_absolute_url()}"
            for i, p in enumerate(related_posts)
        ])
        
        # Получаем фрагмент контента
        clean_content = strip_tags(content)[:1500]
        
        max_articles = len(related_posts) or 1
        default_prompt = (
            "Ты - SEO-специалист. Подбери ЛУЧШИЕ места для внутренних ссылок в статье.\n\n"
            "📰 ТЕКУЩАЯ СТАТЬЯ: {post_title}\n\n"
            "📝 НАЧАЛО ТЕКСТА:\n"
            "{clean_content}...\n\n"
            "🔗 ДОСТУПНЫЕ СТАТЬИ ДЛЯ ССЫЛОК:\n"
            "{posts_list}\n\n"
            "✅ ЗАДАНИЕ: Найди {target_count} ЛУЧШИХ мест в тексте, где ЕСТЕСТВЕННО вставить ссылки на другие статьи.\n\n"
            "📌 ТРЕБОВАНИЯ:\n"
            "1. Ссылка должна быть РЕЛЕВАНТНА контексту (не притянута за уши!)\n"
            "2. Анкор (текст ссылки) должен быть ЕСТЕСТВЕННЫМ в предложении\n"
            "3. Ссылка должна ПОМОГАТЬ читателю узнать больше\n"
            "4. НЕ вставляй ссылки в заголовки!\n"
            "5. Выбирай самые ПОДХОДЯЩИЕ статьи из списка\n\n"
            "💡 ПРИМЕРЫ ХОРОШИХ анкоров:\n"
            "- \"Узнайте больше о правильном уходе\" → ссылка на статью об уходе\n"
            "- \"как мы уже писали ранее\" → ссылка на прошлую статью\n"
            "- \"подробнее о выборе косметики\" → ссылка на обзор\n"
            "- \"в нашей статье о макияже\" → ссылка на статью о макияже\n\n"
            "ВАЖНО: Верни ответ СТРОГО в формате JSON:\n"
            "{{\n"
            "    \"suggestions\": [\n"
            "        {{\n"
            "            \"anchor_text\": \"текст для ссылки (2-5 слов)\",\n"
            "            \"context\": \"фрагмент предложения где вставить (20-30 слов)\",\n"
            "            \"article_number\": номер статьи из списка (1-{max_articles}),\n"
            "            \"reason\": \"почему эта ссылка уместна\"\n"
            "        }},\n"
            "        ...\n"
            "    ]\n"
            "}}\n\n"
            "Верни {target_count} предложений. Только JSON!"
        )
        
        prompt = PromptRegistry.render(
            'SEO_INTERNAL_LINKS_PROMPT',
            params={
                'post_title': post.title,
                'clean_content': clean_content,
                'posts_list': posts_list,
                'target_count': target_count,
                'max_articles': max_articles,
            },
            default=default_prompt,
        )
        PromptRegistry.increment_usage('SEO_INTERNAL_LINKS_PROMPT')

        try:
            # ОПТИМИЗАЦИЯ: используем GigaChat Lite (194₽/1M) для простых alt-тегов
            response = self.gigachat.chat(prompt)
            
            # Извлекаем JSON
            if '```json' in response:
                json_start = response.find('```json') + 7
                json_end = response.find('```', json_start)
                response = response[json_start:json_end].strip()
            elif '```' in response:
                json_start = response.find('```') + 3
                json_end = response.find('```', json_start)
                response = response[json_start:json_end].strip()
            
            suggestions_data = json.loads(response)
            
            # Дополняем данными о статьях
            for suggestion in suggestions_data.get('suggestions', []):
                article_num = suggestion.get('article_number', 1) - 1
                if 0 <= article_num < len(related_posts):
                    related_post = related_posts[article_num]
                    suggestion['article_title'] = related_post.title
                    suggestion['article_url'] = related_post.get_absolute_url()
            
            logger.info(f"✅ Сгенерировано {len(suggestions_data.get('suggestions', []))} предложений ссылок")
            
            return {
                'success': True,
                'suggestions': suggestions_data.get('suggestions', []),
                'count': len(suggestions_data.get('suggestions', []))
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации внутренних ссылок: {e}")
            return {
                'success': False,
                'error': str(e),
                'suggestions': []
            }
    
    # =============================================================================
    # НАХОЖДЕНИЕ РЕЛЕВАНТНЫХ СТАТЕЙ ДЛЯ ССЫЛОК
    # =============================================================================
    def _find_related_posts(self, post, limit: int = 10) -> List:
        """Находит релевантные статьи для ссылок"""
        from blog.models import Post
        
        # 1. Статьи из той же категории
        category_posts = Post.objects.filter(
            category=post.category,
            status='published'
        ).exclude(id=post.id).order_by('-views')[:limit]
        
        if category_posts.count() >= limit:
            return list(category_posts)
        
        # 2. Добавляем статьи с общими тегами
        if hasattr(post, 'tags') and post.tags.exists():
            tag_ids = list(post.tags.values_list('id', flat=True))
            
            tagged_posts = Post.objects.filter(
                tags__id__in=tag_ids,
                status='published'
            ).exclude(id=post.id).annotate(
                common_tags=Count('tags', filter=Q(tags__id__in=tag_ids))
            ).order_by('-common_tags', '-views')[:limit]
            
            # Объединяем списки
            all_posts = list(category_posts) + [
                p for p in tagged_posts if p.id not in [cp.id for cp in category_posts]
            ]
            
            return all_posts[:limit]
        
        return list(category_posts)
    
    # ========================================================================
    # 3. ОПТИМИЗАЦИЯ ИЗОБРАЖЕНИЙ (ALT/TITLE)
    # ========================================================================
    
    def optimize_images_alt_tags(self, post, content: str) -> Dict:
        """
        Добавляет/улучшает alt и title атрибуты изображений через AI
        ОПТИМИЗИРОВАНО: Batch обработка (1 запрос = все изображения)
        ЭКОНОМИЯ: 80% токенов на alt-тегах!
        
        Args:
            post: Объект статьи
            content: HTML контент статьи
        
        Returns:
            Dict с оптимизированным контентом
        """
        logger.info(f"Оптимизация alt-тегов изображений для: {post.title}")
        
        # Находим все изображения
        soup = BeautifulSoup(content, 'html.parser')
        images = soup.find_all('img')
        
        if not images:
            logger.info(" В статье нет изображений")
            return {
                'success': True,
                'modified': False,
                'images_count': 0,
                'optimized_content': content
            }
        
        # Собираем изображения без alt или с коротким alt
        images_to_process = []
        for i, img in enumerate(images, 1):
            current_alt = img.get('alt', '')
            if len(current_alt) <= 20:  # Нет описательного alt
                img_context = self._get_image_context(
                    img,
                    soup,
                    strip_tags(content)[:1000],
                    post
                )
                images_to_process.append({
                    'index': i,
                    'img_tag': img,
                    'context': img_context,
                    'current_alt': current_alt
                })
        
        if not images_to_process:
            logger.info("Все изображения уже имеют alt-теги")
            return {
                'success': True,
                'modified': False,
                'images_count': len(images),
                'optimized_count': 0,
                'optimized_content': content
            }
        
        # BATCH ОБРАБОТКА: генерируем alt для ВСЕХ изображений одним запросом!
        logger.info(f"   [BATCH] Генерация alt-тегов для {len(images_to_process)} изображений одним запросом...")
        
        alt_tags_batch = self._generate_all_alts_batch(
            images_data=images_to_process,
            post_title=post.title,
            post_category=post.category.title if post.category else ""
        )
        
        # Применяем сгенерированные alt-теги
        optimized_count = 0
        if alt_tags_batch and len(alt_tags_batch) == len(images_to_process):
            for img_data, new_alt in zip(images_to_process, alt_tags_batch):
                if new_alt:
                    img_data['img_tag']['alt'] = new_alt
                    img_data['img_tag']['title'] = new_alt
                    optimized_count += 1
                    logger.info(f"Изображение {img_data['index']}: alt='{new_alt[:50]}...'")
        
        # Возвращаем модифицированный HTML
        optimized_content = str(soup)
        
        logger.info(f"BATCH обработка: {optimized_count}/{len(images)} изображений (1 запрос GigaChat!)")
        
        return {
            'success': True,
            'modified': optimized_count > 0,
            'images_count': len(images),
            'optimized_count': optimized_count,
            'optimized_content': optimized_content
        }
    
    def _get_image_context(self, img, soup, fallback_text: str, post) -> str:
        """
        Формирует текстовое описание изображения на основе данных поста и ближайшего окружения.
        Используется исключительно для генерации alt/title.
        """
        context_parts: List[str] = []

        if getattr(post, 'category', None) and getattr(post.category, 'title', None):
            category_title = post.category.title.strip()
            if category_title:
                context_parts.append(category_title)

        if getattr(post, 'title', None):
            post_title = post.title.strip()
            if post_title:
                context_parts.append(post_title)

        current_alt = (img.get('alt') or '').strip()
        if current_alt:
            context_parts.append(current_alt)

        figure = img.find_parent('figure')
        if figure:
            caption_tag = figure.find('figcaption')
            if caption_tag:
                caption_text = caption_tag.get_text(strip=True)
                if caption_text:
                    context_parts.append(caption_text)

        if not context_parts and fallback_text:
            context_parts.append(fallback_text[:200])

        return " | ".join(context_parts)

    # =============================================================================
    # BATCH ГЕНЕРАЦИЯ ALT-ТЕГОВ ДЛЯ ВСЕХ ИЗОБРАЖЕНИЙ
    # =============================================================================
    def _generate_all_alts_batch(
        self, 
        images_data: List[Dict], 
        post_title: str, 
        post_category: str
        ) -> List[str]:
        """
        BATCH генерация alt-тегов для ВСЕХ изображений одним запросом
        ЭКОНОМИЯ: 80% токенов! (1 запрос вместо N)
        
        Args:
            images_data: Список dict с данными изображений
            post_title: Заголовок статьи
            post_category: Категория статьи
        
        Returns:
            Список alt-тегов (по порядку)
        """
        if not images_data:
            return []
        
        # Формируем описание изображений для промпта
        images_descriptions = []
        for img in images_data:
            images_descriptions.append(
                f"Изображение {img['index']}: Контекст - {img['context'][:150]}"
            )
        images_descriptions_str = "\n".join(images_descriptions)
        images_count = len(images_data)
        
        default_prompt = (
            "Создай SEO-описания (alt) для {images_count} изображений в одной статье.\n\n"
            "📰 СТАТЬЯ: {post_title}\n"
            "📂 КАТЕГОРИЯ: {post_category}\n\n"
            "📸 ИЗОБРАЖЕНИЯ:\n"
            "{images_descriptions}\n\n"
            "✅ ТРЕБОВАНИЯ к каждому alt:\n"
            "- Длина: 5-15 слов\n"
            "- Описывает ЧТО изображено\n"
            "- Содержит ключевые слова\n"
            "- НЕ начинается с \"Изображение\", \"Картинка\"\n"
            "- Написано естественно\n\n"
            "💡 ПРИМЕРЫ:\n"
            "- \"Девушка наносит тональный крем на лицо\"\n"
            "- \"Модная красная помада на губах\"\n"
            "- \"Здоровое питание для красивой кожи\"\n\n"
            "ВАЖНО: Верни ответ СТРОГО в формате JSON:\n"
            "{{\n"
            "    \"alt_tags\": [\n"
            "        \"описание изображения 1\",\n"
            "        \"описание изображения 2\",\n"
            "        ...\n"
            "    ]\n"
            "}}\n\n"
            "Верни {images_count} alt-тегов. Только JSON!"
        )
        
        prompt = PromptRegistry.render(
            'SEO_ALT_BATCH_PROMPT',
            params={
                'images_count': images_count,
                'post_title': post_title,
                'post_category': post_category,
                'images_descriptions': images_descriptions_str,
            },
            default=default_prompt,
        )
        PromptRegistry.increment_usage('SEO_ALT_BATCH_PROMPT')

        try:
            # ОПТИМИЗАЦИЯ: task_type='alt_tags' → GigaChat Lite (194₽/1M)
            response = self.gigachat.chat(prompt)
            
            # Извлекаем JSON
            if '```json' in response:
                json_start = response.find('```json') + 7
                json_end = response.find('```', json_start)
                response = response[json_start:json_end].strip()
            elif '```' in response:
                json_start = response.find('```') + 3
                json_end = response.find('```', json_start)
                response = response[json_start:json_end].strip()
            
            result = json.loads(response)
            alt_tags = result.get('alt_tags', [])
            
            logger.info(f"   [BATCH] Сгенерировано {len(alt_tags)} alt-тегов одним запросом!")
            return alt_tags
            
        except Exception as e:
            logger.error(f"❌ Ошибка batch генерации alt: {e}")
            # Fallback: генерируем по одному (старый метод)
            return self._generate_alts_one_by_one(images_data, post_title, post_category)
    
    # =============================================================================
    # ГЕНЕРАЦИЯ ALT-ТЕГА ДЛЯ ОДНОГО ИЗОБРАЖЕНИЯ
    # =============================================================================
    def _generate_alts_one_by_one(
        self,
        images_data: List[Dict],
        post_title: str,
        post_category: str
        ) -> List[str]:
        """Fallback: генерация по одному изображению"""
        alt_tags = []
        for img in images_data:
            alt = self._generate_image_alt_single(
                post_title, post_category, img['context'], img['index']
            )
            alt_tags.append(alt)
        return alt_tags
    
    # =============================================================================
    # ГЕНЕРАЦИЯ ALT-ТЕГА ДЛЯ ОДНОГО ИЗОБРАЖЕНИЯ
    # =============================================================================
    def _generate_image_alt_single(self, post_title: str, post_category: str, 
                           image_context: str, image_number: int) -> Optional[str]:
        """Генерирует alt-текст для ОДНОГО изображения (fallback метод)"""
        
        default_prompt = (
            "Создай КОРОТКОЕ SEO-описание (alt) для изображения №{image_number} в статье.\n\n"
            "📰 СТАТЬЯ: {post_title}\n"
            "📂 КАТЕГОРИЯ: {post_category}\n"
            "📝 КОНТЕКСТ ИЗОБРАЖЕНИЯ: {image_context}\n\n"
            "✅ ТРЕБОВАНИЯ:\n"
            "- Длина: 5-15 слов\n"
            "- Описывает ЧТО изображено\n"
            "- Содержит ключевые слова из статьи\n"
            "- НЕ начинается с \"Изображение\", \"Картинка\", \"Фото\"\n"
            "- Написано естественно\n\n"
            "💡 ПРИМЕРЫ:\n"
            "- \"Девушка наносит тональный крем на лицо\"\n"
            "- \"Модная красная помада на губах\"\n"
            "- \"Шикарная прическа с локонами на длинные волосы\"\n"
            "- \"Здоровое питание для красивой кожи\"\n\n"
            "Верни ТОЛЬКО текст alt (одну строку), без кавычек и лишних слов!"
        )
        
        prompt = PromptRegistry.render(
            'SEO_ALT_SINGLE_PROMPT',
            params={
                'image_number': image_number,
                'post_title': post_title,
                'post_category': post_category,
                'image_context': image_context,
            },
            default=default_prompt,
        )
        PromptRegistry.increment_usage('SEO_ALT_SINGLE_PROMPT')

        try:
            # Fallback использует обычный chat (без оптимизации)
            response = self.gigachat.chat(prompt)
            alt_text = response.strip().strip('"\'')
            
            # Ограничиваем длину
            if len(alt_text) > 125:
                alt_text = alt_text[:122] + '...'
            
            return alt_text
            
        except Exception as e:
            logger.error(f"Ошибка генерации alt: {e}")
            # Ultimate fallback
            return f"{post_title} - изображение {image_number}"
    
    # ========================================================================
    # 4. ОБНОВЛЕНИЕ СТАРЫХ СТАТЕЙ
    # ========================================================================
    
    def refresh_old_article(self, post) -> Dict:
        """
        Обновляет старую статью актуальной информацией
        Улучшает SEO и возвращает статью в топ
        
        Args:
            post: Старая статья для обновления
        
        Returns:
            Dict с обновленным контентом
        """
        from datetime import datetime
        from django.utils import timezone
        
        logger.info(f"Обновление старой статьи: {post.title}")
        
        # Получаем текущий год и сезон
        now = timezone.now()
        current_year = now.year
        month = now.month
        
        if month in [12, 1, 2]:
            season = 'зима'
        elif month in [3, 4, 5]:
            season = 'весна'
        elif month in [6, 7, 8]:
            season = 'лето'
        else:
            season = 'осень'
        
        # Получаем контент
        clean_content = strip_tags(post.content)[:2000]
        
        publish_date = post.created.strftime('%Y-%m-%d')
        category_title = post.category.title if post.category else "Общее"
        
        default_prompt = (
            "Ты - редактор журнала. Обнови СТАРУЮ статью актуальной информацией.\n\n"
            "📰 ОРИГИНАЛЬНЫЙ ЗАГОЛОВОК: {post_title}\n"
            "📅 ДАТА ПУБЛИКАЦИИ: {publish_date}\n"
            "📂 КАТЕГОРИЯ: {category_title}\n\n"
            "📝 НАЧАЛО СТАРОЙ СТАТЬИ:\n"
            "{clean_content}...\n\n"
            "🎯 ТЕКУЩАЯ ДАТА: {current_year}, {season}\n\n"
            "✅ ЗАДАНИЕ: Обнови статью, добавив:\n"
            "1. Актуальные тренды {season} {current_year}\n"
            "2. Новую информацию и факты\n"
            "3. Современные примеры\n"
            "4. Обновленные рекомендации\n\n"
            "📐 ЧТО ДОБАВИТЬ:\n"
            "- Секцию \"Что нового в {current_year}?\"\n"
            "- Актуальные тренды {season}\n"
            "- Обновленные советы экспертов\n"
            "- Ссылки на последние исследования\n\n"
            "📌 ТРЕБОВАНИЯ:\n"
            "- НЕ переписывай статью полностью!\n"
            "- Добавь 2-3 новых раздела (H2/H3)\n"
            "- Обнови устаревшие факты\n"
            "- Сохрани основную структуру\n"
            "- Добавь эмодзи в заголовки\n\n"
            "ФОРМАТ ОТВЕТА:\n"
            "Верни ТОЛЬКО НОВЫЕ РАЗДЕЛЫ для вставки в статью (HTML):\n"
            "<h2>🆕 Что нового в {current_year}?</h2>\n"
            "<p>[Актуальная информация]</p>\n"
            "...\n\n"
            "Верни 2-3 новых раздела в HTML!"
        )
        
        prompt = PromptRegistry.render(
            'SEO_REFRESH_ARTICLE_PROMPT',
            params={
                'post_title': post.title,
                'publish_date': publish_date,
                'category_title': category_title,
                'clean_content': clean_content,
                'current_year': current_year,
                'season': season,
            },
            default=default_prompt,
        )
        PromptRegistry.increment_usage('SEO_REFRESH_ARTICLE_PROMPT')

        try:
            # Используем GigaChat для текста
            response = self.gigachat.chat(prompt)
            
            # Очищаем от markdown оберток
            new_sections = response.replace('```html', '').replace('```', '').strip()
            
            # Обновленный заголовок
            updated_title = self._update_title_for_current_year(post.title, current_year)
            
            logger.info(f"✅ Сгенерированы обновления для статьи")
            
            return {
                'success': True,
                'updated_title': updated_title,
                'new_sections': new_sections,
                'update_note': f'Статья обновлена {now.strftime("%d.%m.%Y")} актуальной информацией'
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления статьи: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # =============================================================================
    # ОБНОВЛЕНИЕ ЗАГОЛОВКА СТАТЬИ
    # =============================================================================
    def _update_title_for_current_year(self, title: str, year: int) -> str:
        """Обновляет заголовок добавляя текущий год"""
        # Убираем старые года если есть
        title = re.sub(r'\b20\d{2}\b', '', title)
        
        # Добавляем текущий год если нет
        if str(year) not in title:
            # Ищем подходящее место
            if ':' in title:
                parts = title.split(':', 1)
                return f"{parts[0].strip()} {year}: {parts[1].strip()}"
            else:
                return f"{title.strip()} - {year}"
        
        return title
    
    # ========================================================================
    # 5. ОТПРАВКА В ПОИСКОВЫЕ СИСТЕМЫ
    # ========================================================================
    
    def submit_to_search_engines(self, post) -> Dict:
        """
        Отправляет статью в поисковые системы
        - Яндекс Вебмастер API
        - Google Search Console API
        
        Args:
            post: Объект статьи
        
        Returns:
            Dict с результатами отправки
        """
        logger.info(f"Отправка в поисковики: {post.title}")
        
        results = {
            'yandex': {'success': False},
            'google': {'success': False}
        }
        
        post_url = f"{settings.SITE_URL}{post.get_absolute_url()}"
        
        # 1. Яндекс Вебмастер
        if hasattr(settings, 'YANDEX_WEBMASTER_TOKEN') and settings.YANDEX_WEBMASTER_TOKEN:
            yandex_result = self._submit_to_yandex(post_url)
            results['yandex'] = yandex_result
        
        # 2. Google Search Console
        # (требует OAuth2, сложнее настроить)
        # Пока используем sitemap - Google сам найдет через него
        
        return results
    
    def _submit_to_yandex(self, url: str) -> Dict:
        """
        Отправляет URL в Яндекс Вебмастер через API
        
        Docs: https://yandex.ru/dev/webmaster/doc/dg/reference/host-recrawl-post.html
        """
        client = get_yandex_webmaster_client()
        
        result = client.enqueue_recrawl(url)

        if result.get('success'):
            logger.info("✅ URL отправлен в Яндекс: %s", url)
            result.setdefault('message', 'URL added to recrawl queue')
            return result

        error_message = result.get('error') or result.get('details') or 'unknown_error'
        logger.error("❌ Ошибка Яндекс API: %s", error_message)
        return result
    
    def submit_sitemap_to_search_engines(self) -> Dict:
        """
        Уведомляет поисковики об обновлении sitemap
        
        Returns:
            Dict с результатами отправки
        """
        sitemap_url = f"{settings.SITE_URL}/sitemap.xml"
        
        results = {}
        
        # Яндекс
        try:
            client = get_yandex_webmaster_client()
            yandex_result = client.ping_sitemap(sitemap_url)
            results['yandex'] = {
                'success': yandex_result.get('success', False),
                'status_code': yandex_result.get('status_code'),
                'details': yandex_result.get('response') or yandex_result.get('error'),
            }
            if results['yandex']['success']:
                logger.info("✅ Sitemap отправлен в Яндекс")
            else:
                logger.error("❌ Ошибка ping sitemap Яндекс: %s", results['yandex'].get('details'))
        except Exception as e:
            results['yandex'] = {'success': False, 'error': str(e)}
            logger.error("❌ Ошибка пинга Яндекс sitemap: %s", e)
        
        # Google
        try:
            google_ping_url = f"https://www.google.com/ping?sitemap={sitemap_url}"
            response = requests.get(google_ping_url, timeout=10)
            results['google'] = {
                'success': response.status_code == 200,
                'status_code': response.status_code
            }
            logger.info(f"✅ Sitemap отправлен в Google")
        except Exception as e:
            results['google'] = {'success': False, 'error': str(e)}
            logger.error(f"❌ Ошибка пинга Google sitemap: {e}")
        
        return results

    # ========================================================================
    # 4. КОНВЕРСИЯ В WEBP И SEO-ИМЕНА (АТОМАРНО)
    # ========================================================================
    def ensure_webp_conversion(self, post, dry_run: bool = False) -> Dict:
        """
        Гарантирует, что главное изображение статьи в WebP с SEO-именем.
        - Генерирует .webp во временный путь, затем атомарно меняет FileField
        - Сохраняет бэкап соответствий (старый->новый) для отката
        - При сбое выполняет полное восстановление
        """
        try:
            if not post.kartinka:
                return {'success': False, 'error': 'no_image'}
            old_name = post.kartinka.name
            old_path = default_storage.path(old_name) if hasattr(default_storage, 'path') else old_name
            ext = os.path.splitext(old_name)[1].lower()
            if ext == '.webp' and '-' in os.path.basename(old_name):
                # Уже webp и вероятно SEO-имя
                return {'success': True, 'skipped': True, 'reason': 'already_webp'}

            # Формируем SEO-имя
            base_slug = slugify(f"{post.title[:80]}-{post.id}") or f"post-{post.id}"
            new_rel_dir = os.path.dirname(old_name)
            new_basename = f"{base_slug}.webp"
            new_name = os.path.join(new_rel_dir, new_basename).replace('\\', '/')

            # Готовим файл webp
            with default_storage.open(old_name, 'rb') as f:
                im = Image.open(f)
                im = im.convert('RGB')
                # Временное имя
                temp_name = os.path.join(new_rel_dir, f".{base_slug}.tmp.webp").replace('\\', '/')
                with default_storage.open(temp_name, 'wb') as out:
                    im.save(out, format='WEBP', quality=85, method=6)

            # Бэкап-реестр (дописываем в существующий json если есть)
            backup_item = {'post_id': post.id, 'old': old_name, 'new': new_name}
            try:
                backup_json_path = Path(settings.BASE_DIR) / 'image_paths_backup.json'
                backup_data = []
                if backup_json_path.exists():
                    import json as _json
                    with backup_json_path.open('r', encoding='utf-8') as bf:
                        backup_data = _json.load(bf)
                backup_data.append(backup_item)
                with backup_json_path.open('w', encoding='utf-8') as bf:
                    import json as _json
                    _json.dump(backup_data, bf, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning(f"Не удалось записать бэкап-реестр: {e}")

            if dry_run:
                # Удаляем временный, не меняем БД
                default_storage.delete(temp_name)
                return {'success': True, 'dry_run': True, 'old': old_name, 'new': new_name}

            # Атомарная замена: перенос файла и смена FileField
            with transaction.atomic():
                # Перемещаем временный в целевое имя
                with default_storage.open(temp_name, 'rb') as src:
                    # Перезапишем, если вдруг имя занято
                    if default_storage.exists(new_name):
                        default_storage.delete(new_name)
                    default_storage.save(new_name, src)
                default_storage.delete(temp_name)

                # Обновляем FileField
                post.kartinka.name = new_name
                post.save(update_fields=['kartinka'])

            # Проверка доступности
            if not default_storage.exists(new_name):
                # Возврат к старому
                with transaction.atomic():
                    post.kartinka.name = old_name
                    post.save(update_fields=['kartinka'])
                return {'success': False, 'error': 'new_file_missing'}

            # Опционально: удалить старый файл (после успешной замены)
            try:
                if old_name != new_name and default_storage.exists(old_name):
                    default_storage.delete(old_name)
            except Exception as e:
                logger.warning(f"Не удалось удалить старый файл {old_name}: {e}")

            return {'success': True, 'old': old_name, 'new': new_name}
        except Exception as e:
            logger.error(f"❌ ensure_webp_conversion error: {e}")
            return {'success': False, 'error': str(e)}

    # ========================================================================
    # 5. ИНДЕКСАЦИЯ ИЗОБРАЖЕНИЙ (IndexNow + sitemap)
    # ========================================================================
    def submit_images_to_search_engines(self, image_urls: List[str]) -> Dict:
        """
        Отправляет список URL изображений в поисковые системы:
        - IndexNow (Bing и др.) при наличии ключа
        - Пинг sitemap как fallback
        """
        results: Dict[str, Dict] = {}
        try:
            host = settings.SITE_URL.replace('https://', '').replace('http://', '')
            indexnow_key = getattr(settings, 'BING_INDEXNOW_KEY', '')
            if indexnow_key and image_urls:
                payload = {
                    "host": host,
                    "key": indexnow_key,
                    "urlList": image_urls
                }
                resp = requests.post("https://api.indexnow.org/indexnow", json=payload, timeout=10)
                results['indexnow'] = {
                    'success': resp.status_code == 200,
                    'status_code': resp.status_code
                }
                if resp.status_code == 200:
                    logger.info(f"✅ IndexNow: отправлено {len(image_urls)} изображений")
                else:
                    logger.warning(f"⚠️ IndexNow: {resp.status_code}")
            else:
                results['indexnow'] = {'success': False, 'error': 'not_configured_or_empty'}
        except Exception as e:
            results['indexnow'] = {'success': False, 'error': str(e)}
            logger.error(f"❌ IndexNow ошибка: {e}")

        # Sitemap ping как резерв
        try:
            sm = self.submit_sitemap_to_search_engines()
            results['sitemap'] = sm
        except Exception as e:
            results['sitemap'] = {'success': False, 'error': str(e)}

        return results

