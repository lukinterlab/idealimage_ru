"""
Система парсинга популярных статей из интернета.

Ищет популярные статьи через Google/Yandex/RSS/соцсети,
парсит их и сохраняет для модерации.
"""
import logging
import re
from typing import Dict, List, Optional
from django.utils import timezone
from django.utils.html import strip_tags
from django.db import transaction

from blog.models import Category
from .models import ParsedArticle, ParsingCategory
from .universal_parser import UniversalParser

logger = logging.getLogger(__name__)


def extract_first_words(text: str, word_count: int = 200) -> str:
    """
    Извлекает первые N слов из текста.
    
    Args:
        text: Исходный текст
        word_count: Количество слов
    
    Returns:
        Текст с первыми N словами
    """
    words = text.split()
    return ' '.join(words[:word_count])


def parse_popular_articles() -> Dict:
    """
    Парсит популярные статьи из интернета.
    
    Для каждой активной категории парсинга:
    1. Формирует поисковые запросы
    2. Ищет статьи через Google/Yandex/RSS/соцсети
    3. Парсит найденные статьи (~200 слов)
    4. Сохраняет в ParsedArticle со статусом pending
    5. Распределяет по категориям сайта
    
    Returns:
        Dict с результатами парсинга
    """
    logger.info("=" * 60)
    logger.info("📰 НАЧАЛО ПАРСИНГА ПОПУЛЯРНЫХ СТАТЕЙ")
    logger.info("=" * 60)
    
    results = {
        'categories_processed': 0,
        'articles_found': 0,
        'articles_parsed': 0,
        'articles_saved': 0,
        'errors': []
    }
    
    try:
        # Получаем активные категории парсинга
        parsing_categories = ParsingCategory.objects.filter(is_active=True)
        results['categories_processed'] = parsing_categories.count()
        
        logger.info(f"📋 Найдено активных категорий парсинга: {results['categories_processed']}")
        
        # Инициализируем парсер
        parser = UniversalParser()
        
        # Для каждой категории парсинга
        for parsing_category in parsing_categories:
            try:
                logger.info(f"🔍 Обработка категории: {parsing_category.name}")
                
                # Получаем поисковые запросы
                search_queries = parsing_category.search_queries or []
                if not search_queries:
                    logger.warning(f"   ⚠️ Нет поисковых запросов для категории {parsing_category.name}")
                    continue
                
                # Получаем источники
                sources = parsing_category.sources or []
                if not sources:
                    logger.warning(f"   ⚠️ Нет источников для категории {parsing_category.name}")
                    continue
                
                # Ограничение на количество статей в день
                articles_per_day = parsing_category.articles_per_day or 5
                
                # Проверяем, сколько уже спаршено сегодня
                today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
                already_parsed_today = ParsedArticle.objects.filter(
                    parsing_category=parsing_category,
                    parsed_at__gte=today_start
                ).count()
                
                if already_parsed_today >= articles_per_day:
                    logger.info(f"   ⏭️ Уже спаршено {already_parsed_today} статей сегодня (лимит: {articles_per_day})")
                    continue
                
                remaining = articles_per_day - already_parsed_today
                logger.info(f"   📊 Нужно спарсить еще {remaining} статей")
                
                articles_found = 0
                articles_parsed = 0
                
                # Для каждого поискового запроса
                for query in search_queries[:3]:  # Максимум 3 запроса на категорию
                    if articles_parsed >= remaining:
                        break
                    
                    try:
                        logger.info(f"   🔎 Поиск по запросу: '{query}'")
                        
                        # Ищем источники через UniversalParser
                        if 'google' in sources or 'yandex' in sources:
                            sources_list = parser.search_sources(query, limit=10)
                            results['articles_found'] += len(sources_list)
                            articles_found += len(sources_list)
                            
                            # Парсим найденные статьи
                            for source in sources_list[:remaining]:
                                if articles_parsed >= remaining:
                                    break
                                
                                try:
                                    url = source.get('url', '')
                                    if not url:
                                        continue
                                    
                                    # Парсим статью
                                    logger.info(f"      📥 Парсинг: {url[:80]}...")
                                    parsed_data = parser.parse_article(url, retries=2)
                                    
                                    if not parsed_data.get('success'):
                                        logger.warning(f"      ⚠️ Не удалось спарсить: {url}")
                                        continue
                                    
                                    title = parsed_data.get('title', 'Без заголовка')
                                    text = parsed_data.get('text', '')
                                    
                                    if len(text) < 100:
                                        logger.warning(f"      ⚠️ Текст слишком короткий: {len(text)} символов")
                                        continue
                                    
                                    # Извлекаем первые ~200 слов
                                    content = extract_first_words(text, 200)
                                    
                                    # Определяем категорию сайта
                                    site_category = parsing_category.site_category
                                    if not site_category:
                                        # Пытаемся найти категорию по названию
                                        try:
                                            site_category = Category.objects.filter(
                                                title__icontains=parsing_category.name
                                            ).first()
                                        except:
                                            pass
                                    
                                    # Проверяем, не спаршена ли уже эта статья
                                    existing = ParsedArticle.objects.filter(
                                        source_url=url
                                    ).first()
                                    
                                    if existing:
                                        logger.info(f"      ⏭️ Статья уже спаршена ранее: {title[:50]}")
                                        continue
                                    
                                    # Сохраняем спаршенную статью
                                    parsed_article = ParsedArticle.objects.create(
                                        title=title[:500],
                                        content=content,
                                        source_url=url,
                                        source_name=source.get('title', 'Неизвестный источник')[:200],
                                        category=site_category,
                                        parsing_category=parsing_category,
                                        status='pending',
                                        popularity_score=source.get('popularity_score', 0)
                                    )
                                    
                                    articles_parsed += 1
                                    results['articles_parsed'] += 1
                                    results['articles_saved'] += 1
                                    
                                    logger.info(f"      ✅ Сохранено: {title[:50]}...")
                                    
                                except Exception as e:
                                    error_msg = f"Ошибка парсинга статьи {url}: {str(e)}"
                                    logger.error(f"      ❌ {error_msg}", exc_info=True)
                                    results['errors'].append(error_msg)
                        
                        # RSS ленты (если указаны)
                        if 'rss' in sources and articles_parsed < remaining:
                            # TODO: Реализовать парсинг RSS лент
                            logger.info(f"   📡 RSS парсинг пока не реализован")
                        
                        # Соцсети (если указаны)
                        if 'social' in sources and articles_parsed < remaining:
                            # TODO: Реализовать парсинг соцсетей
                            logger.info(f"   📱 Парсинг соцсетей пока не реализован")
                    
                    except Exception as e:
                        error_msg = f"Ошибка обработки запроса '{query}': {str(e)}"
                        logger.error(f"   ❌ {error_msg}", exc_info=True)
                        results['errors'].append(error_msg)
                
                logger.info(f"   ✅ Категория '{parsing_category.name}': найдено {articles_found}, спаршено {articles_parsed}")
                
            except Exception as e:
                error_msg = f"Ошибка обработки категории парсинга {parsing_category.name}: {str(e)}"
                logger.error(f"❌ {error_msg}", exc_info=True)
                results['errors'].append(error_msg)
        
        logger.info("=" * 60)
        logger.info("📊 РЕЗУЛЬТАТЫ ПАРСИНГА:")
        logger.info(f"   Категорий обработано: {results['categories_processed']}")
        logger.info(f"   Статей найдено: {results['articles_found']}")
        logger.info(f"   Статей спаршено: {results['articles_parsed']}")
        logger.info(f"   Статей сохранено: {results['articles_saved']}")
        if results['errors']:
            logger.warning("   Ошибок: %d", len(results['errors']))
        logger.info("=" * 60)
        
    except Exception as e:
        error_msg = f"Критическая ошибка парсинга: {str(e)}"
        logger.error(f"❌ {error_msg}", exc_info=True)
        results['errors'].append(error_msg)
    
    return results

