"""
Сервис для обработки изображений постов и категорий
Безопасно конвертирует изображения в WebP без прерывания основного процесса
"""
import logging
from utilits.utils import optimize_and_convert_to_webp

logger = logging.getLogger(__name__)


def process_post_image(post):
    """
    Конвертирует изображение поста в WebP (если нужно)
    БЕЗОПАСНО: не прерывает процесс при ошибке
    
    Args:
        post: Экземпляр модели Post
    
    Returns:
        bool: True если конвертация успешна, False при ошибке
    """
    if not post.kartinka or not hasattr(post.kartinka, 'path'):
        logger.debug(f"   ⏭️ Пост '{post.title}' без изображения")
        return False
    
    try:
        # Пропускаем если уже WebP
        if post.kartinka.name.lower().endswith('.webp'):
            logger.info(f"   ⏭️ Изображение уже в формате WebP: {post.kartinka.name}")
            return True
        
        logger.info(f"   🔄 Конвертирую изображение поста '{post.title}' в WebP...")
        
        # Конвертируем в WebP
        new_path = optimize_and_convert_to_webp(
            post.kartinka.path,
            context_name=post.title,
            max_width=1920,
            max_height=1080,
            quality=85
        )
        
        if new_path:
            post.kartinka.name = new_path
            post.save(update_fields=['kartinka'])
            logger.info(f"   ✅ Изображение конвертировано в WebP: {new_path}")
            return True
        else:
            logger.warning(f"   ⚠️ Не удалось конвертировать изображение поста '{post.title}'")
            return False
            
    except Exception as e:
        logger.error(f"   ❌ Ошибка конвертации изображения поста '{post.title}': {e}", exc_info=True)
        # НЕ прерываем процесс - продолжаем с оригинальным изображением
        return False


def process_category_image(category):
    """
    Конвертирует изображение категории в WebP (если нужно)
    БЕЗОПАСНО: не прерывает процесс при ошибке
    
    Args:
        category: Экземпляр модели Category
    
    Returns:
        bool: True если конвертация успешна, False при ошибке
    """
    if not category.kartinka or not hasattr(category.kartinka, 'path'):
        return False
    
    try:
        # Пропускаем если уже WebP
        if category.kartinka.name.lower().endswith('.webp'):
            logger.info(f"✅ Изображение категории '{category.title}' уже в WebP")
            return True
        
        logger.info(f"🔄 Конвертирую изображение категории '{category.title}' в WebP...")
        
        new_path = optimize_and_convert_to_webp(
            category.kartinka.path,
            context_name=category.title,
            max_width=1200,
            max_height=800,
            quality=85
        )
        
        if new_path:
            category.kartinka.name = new_path
            category.save(update_fields=['kartinka'])
            logger.info(f"✅ Изображение категории '{category.title}' конвертировано в WebP: {new_path}")
            return True
        else:
            logger.warning(f"⚠️ Не удалось конвертировать изображение категории '{category.title}'")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка конвертации изображения категории '{category.title}': {e}", exc_info=True)
        # НЕ прерываем процесс
        return False

