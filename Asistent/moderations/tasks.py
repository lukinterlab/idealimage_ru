"""
Задачи Django-Q для системы регенерации статей.
"""
import logging
from typing import Dict
from .article_regenerator import regenerate_old_articles

logger = logging.getLogger(__name__)


def daily_article_regeneration() -> Dict:
    """
    Ежедневная задача регенерации старых статей.
    
    Запускается через Django-Q cron.
    Обрабатывает по 1 статье из каждой категории (всего 9 статей).
    
    Returns:
        Dict с результатами регенерации
    """
    logger.info("=" * 60)
    logger.info("🔄 ЗАПУСК ЕЖЕДНЕВНОЙ РЕГЕНЕРАЦИИ СТАТЕЙ")
    logger.info("=" * 60)
    
    try:
        results = regenerate_old_articles(limit_per_category=1)
        
        logger.info("=" * 60)
        logger.info("📊 РЕЗУЛЬТАТЫ РЕГЕНЕРАЦИИ:")
        logger.info(f"   Категорий обработано: {results['total_categories']}")
        logger.info(f"   Статей найдено: {results['articles_found']}")
        logger.info(f"   Успешно регенерировано: {results['regenerated']}")
        logger.info(f"   Ошибок: {results['failed']}")
        if results['errors']:
            logger.warning("   Список ошибок:")
            for error in results['errors']:
                logger.warning(f"      - {error}")
        logger.info("=" * 60)
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка в daily_article_regeneration: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'regenerated': 0,
            'failed': 0
        }

