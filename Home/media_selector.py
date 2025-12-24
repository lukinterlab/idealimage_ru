"""
Умный выбор медиафайлов для лендинга из локальных источников
"""
import os
import random
from django.conf import settings
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class LocalMediaSelector:
    """Выбирает подходящие медиафайлы из локальной коллекции"""
    
    def __init__(self):
        self.media_root = settings.MEDIA_ROOT
        self.images_dir = os.path.join(self.media_root, 'images')
    
    def select_images_for_style(self, style, section_key, count=5):
        """
        Подбирает изображения из локальной коллекции по стилю
        
        Args:
            style: Описание стиля
            section_key: Ключ секции
            count: Количество изображений
        
        Returns:
            List путей к изображениям
        """
        # Собираем все изображения
        image_extensions = ('.jpg', '.jpeg', '.png', '.webp')
        all_images = []
        
        # Ищем в media/images/
        if os.path.exists(self.images_dir):
            for root, dirs, files in os.walk(self.images_dir):
                for file in files:
                    if file.lower().endswith(image_extensions):
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, self.media_root)
                        all_images.append(rel_path.replace('\\', '/'))
        
        logger.info(f"Found {len(all_images)} local images")
        
        # Фильтруем по размеру (берём только не слишком большие)
        suitable_images = []
        for img_path in all_images:
            try:
                full_path = os.path.join(self.media_root, img_path.replace('/', os.sep))
                size = os.path.getsize(full_path)
                # Берём файлы от 50KB до 2MB
                if 50 * 1024 < size < 2 * 1024 * 1024:
                    suitable_images.append(img_path)
            except:
                continue
        
        logger.info(f"Found {len(suitable_images)} suitable images (50KB - 2MB)")
        
        # Случайно выбираем N изображений
        if len(suitable_images) >= count:
            selected = random.sample(suitable_images, count)
        else:
            selected = suitable_images[:count]
        
        return selected
    
    def get_best_image_for_section(self, section_key, style=''):
        """
        Получает лучшее изображение для секции
        
        Args:
            section_key: Ключ секции (hero, features, etc)
            style: Описание стиля
        
        Returns:
            Путь к изображению или None
        """
        images = self.select_images_for_style(style, section_key, count=10)
        
        if not images:
            return None
        
        # Приоритет по типу секции
        preferences = {
            'hero': ['fashion', 'beauty', 'model', 'style'],
            'features': ['tech', 'quality', 'innovation'],
            'technology': ['ai', 'digital', 'tech', 'futuristic'],
            'categories': ['lifestyle', 'food', 'sport'],
            'blogger': ['creator', 'social', 'content'],
            'advertising': ['business', 'marketing'],
            'top_posts': ['popular', 'trending'],
            'network': ['network', 'connection'],
            'cta': ['success', 'action', 'motivation'],
        }
        
        keywords = preferences.get(section_key, [])
        
        # Пробуем найти изображение с подходящим именем
        for keyword in keywords:
            for img in images:
                if keyword.lower() in img.lower():
                    return img
        
        # Если не нашли по ключевым словам, возвращаем случайное
        return random.choice(images) if images else None


class RussianMediaParser:
    """Парсер изображений и видео из российских источников"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def parse_images_from_sources(self, query, limit=10):
        """
        Парсит изображения из доступных российских источников
        
        Args:
            query: Поисковый запрос
            limit: Количество изображений
        
        Returns:
            List[str] URL изображений
        """
        images = []
        
        # Источник 1: Пикабу
        try:
            images.extend(self._parse_pikabu(query, limit=limit//2))
        except Exception as e:
            logger.warning(f"Pikabu parsing error: {e}")
        
        # Источник 2: Яндекс.Картинки (публичное API недоступно, используем другой подход)
        # Можно добавить другие источники
        
        return images[:limit]
    
    def _parse_pikabu(self, query, limit=5):
        """Парсинг популярных изображений с Пикабу"""
        # Базовая реализация - можно расширить
        return []
    
    def get_rutube_videos(self, query, limit=5):
        """Получает видео с Rutube по запросу"""
        from Asistent.parsers.video_parsers import RutubeParser
        
        try:
            rutube = RutubeParser()
            videos = rutube.search_videos(query, limit=limit)
            return [v.get('embed_url') for v in videos if v.get('embed_url')]
        except Exception as e:
            logger.error(f"Rutube parsing error: {e}")
            return []


def get_media_for_landing_section(section_key, style='', prefer_local=True):
    """
    Универсальная функция для получения медиа для секции лендинга
    
    Args:
        section_key: Ключ секции
        style: Описание стиля
        prefer_local: Предпочитать локальные файлы
    
    Returns:
        dict с медиа-данными
    """
    result = {
        'type': 'gradient',
        'url': None,
        'path': None,
    }
    
    # Сначала пробуем локальные файлы
    if prefer_local:
        selector = LocalMediaSelector()
        local_image = selector.get_best_image_for_section(section_key, style)
        
        if local_image:
            result['type'] = 'image'
            result['path'] = local_image
            result['url'] = f"/media/{local_image}"
            logger.info(f"Selected local image for {section_key}: {local_image}")
            return result
    
    # Если локальных нет, пробуем парсить
    parser = RussianMediaParser()
    images = parser.parse_images_from_sources(style or section_key, limit=5)
    
    if images:
        result['type'] = 'image'
        result['url'] = images[0]
        logger.info(f"Parsed image for {section_key}: {images[0][:60]}")
        return result
    
    # Fallback - возвращаем градиент
    logger.warning(f"No media found for {section_key}, using gradient")
    return result


