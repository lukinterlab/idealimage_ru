"""
Задачи Django-Q для системы парсинга статей.
"""
import logging
from typing import Dict
from .popular_parser import parse_popular_articles

logger = logging.getLogger(__name__)


def daily_article_parsing() -> Dict:
    """
    Ежедневная задача парсинга популярных статей.
    
    Запускается через Django-Q cron.
    Парсит по 5 статей на каждую активную категорию парсинга.
    
    Returns:
        Dict с результатами парсинга
    """
    logger.info("=" * 60)
    logger.info("📰 ЗАПУСК ЕЖЕДНЕВНОГО ПАРСИНГА СТАТЕЙ")
    logger.info("=" * 60)
    
    try:
        results = parse_popular_articles()
        
        logger.info("=" * 60)
        logger.info("📊 РЕЗУЛЬТАТЫ ПАРСИНГА:")
        logger.info(f"   Категорий обработано: {results['categories_processed']}")
        logger.info(f"   Статей найдено: {results['articles_found']}")
        logger.info(f"   Статей спаршено: {results['articles_parsed']}")
        logger.info(f"   Статей сохранено: {results['articles_saved']}")
        if results['errors']:
            logger.warning("   Ошибок: %d", len(results['errors']))
            for error in results['errors'][:5]:  # Показываем первые 5 ошибок
                logger.warning(f"      - {error}")
        logger.info("=" * 60)
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка в daily_article_parsing: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'articles_saved': 0,
            'errors': [str(e)]
        }

