"""
Утилиты для работы с изображениями
"""
import requests
import os
import hashlib
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import logging

logger = logging.getLogger(__name__)


"""Скачивает изображение по URL и сохраняет в media"""
def download_image(image_url, save_to='images/ai_generated/'):
    """
    Скачивает изображение по URL и сохраняет в media
    
    Args:
        image_url: URL изображения
        save_to: Директория для сохранения
    
    Returns:
        Путь к сохраненному файлу или None
    """
    if not image_url:
        return None
    
    try:
        logger.info(f"📷 Скачивание изображения: {image_url[:60]}...")
        
        # Скачиваем изображение
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(image_url, headers=headers, timeout=10, stream=True)
        response.raise_for_status()
        
        # Проверяем что это действительно изображение
        content_type = response.headers.get('Content-Type', '')
        if 'image' not in content_type:
            logger.warning(f"   ⚠️ URL не содержит изображение: {content_type}")
            return None
        
        # Генерируем уникальное имя файла
        url_hash = hashlib.md5(image_url.encode()).hexdigest()[:8]
        ext = get_image_extension(content_type)
        filename = f"{url_hash}_{os.path.basename(image_url).split('?')[0][:20]}.{ext}"
        
        # Путь для сохранения
        filepath = os.path.join(save_to, filename)
        
        # Сохраняем файл
        file_content = ContentFile(response.content)
        saved_path = default_storage.save(filepath, file_content)
        
        logger.info(f"   ✅ Изображение сохранено: {saved_path}")
        return saved_path
        
    except Exception as e:
        logger.error(f"   ❌ Ошибка скачивания изображения: {e}")
        return None


"""Определяет расширение файла по Content-Type"""
def get_image_extension(content_type):
    """
    Определяет расширение файла по Content-Type
    
    Args:
        content_type: MIME тип
    
    Returns:
        Расширение файла
    """
    extensions = {
        'image/jpeg': 'jpg',
        'image/jpg': 'jpg',
        'image/png': 'png',
        'image/gif': 'gif',
        'image/webp': 'webp',
        'image/svg+xml': 'svg',
    }
    return extensions.get(content_type, 'jpg')


"""Выбирает лучшее изображение из списка источников"""
def get_best_image_from_sources(sources_data, fallback_search=True, keywords=None):
    """
    Выбирает лучшее изображение из списка источников
    
    Args:
        sources_data: List словарей со статьями
        fallback_search: Искать в интернете если не найдено в источниках
        keywords: Ключевые слова для поиска (если fallback_search=True)
    
    Returns:
        URL лучшего изображения или None
    """
    # ШАГ 1: Ищем в спаршенных источниках
    for source in sources_data:
        image_url = source.get('image_url')
        if image_url and is_valid_image_url(image_url):
            logger.info(f"   ✅ Изображение найдено в источнике: {image_url[:60]}...")
            return image_url
    
    # ШАГ 2: Если не нашли - пробуем искать в HTML источников
    for source in sources_data:
        html_content = source.get('content', '')
        if html_content:
            # Ищем теги img в HTML
            import re
            img_matches = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html_content)
            for img_url in img_matches:
                if is_valid_image_url(img_url) and not img_url.startswith('data:'):
                    # Преобразуем относительные URL в абсолютные
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    elif img_url.startswith('/') and source.get('url'):
                        from urllib.parse import urljoin
                        img_url = urljoin(source.get('url'), img_url)
                    
                    if img_url.startswith('http'):
                        logger.info(f"   ✅ Изображение найдено в HTML: {img_url[:60]}...")
                        return img_url
    
    # ШАГ 3: Fallback - поиск через бесплатные API
    if fallback_search and keywords:
        logger.info(f"   🔍 Fallback: ищем изображение по ключевым словам...")
        fallback_image = search_free_image(keywords)
        if fallback_image:
            logger.info(f"   ✅ Найдено fallback изображение: {fallback_image[:60]}...")
            return fallback_image
    
    logger.warning(f"   ⚠️ Изображение не найдено (проверено источников: {len(sources_data)})")
    return None


"""Ищет бесплатное изображение по ключевым словам через Unsplash API"""
def search_free_image(keywords):
    """
    Ищет бесплатное изображение по ключевым словам через Unsplash API
    
    Args:
        keywords: Список ключевых слов или строка
    
    Returns:
        URL найденного изображения или None
    """
    # Преобразуем keywords в строку для поиска
    if isinstance(keywords, list):
        search_query = ' '.join(keywords[:3])  # Берем первые 3 ключевых слова
    else:
        search_query = str(keywords)
    
    try:
        logger.info(f"   🔍 Поиск изображения по запросу: {search_query}")

        unsplash_key = getattr(settings, "UNSPLASH_ACCESS_KEY", None)
        if unsplash_key:
            try:
                response = requests.get(
                    "https://api.unsplash.com/search/photos",
                    params={
                        "query": search_query,
                        "orientation": "landscape",
                        "per_page": 5,
                    },
                    headers={"Authorization": f"Client-ID {unsplash_key}"},
                    timeout=10,
                )
                response.raise_for_status()
                results = response.json().get("results", [])
                for item in results:
                    urls = item.get("urls", {})
                    candidate = urls.get("regular") or urls.get("full")
                    if candidate:
                        logger.info("   ✅ Unsplash вернул изображение")
                        return candidate
                logger.info("   ℹ️ Unsplash не нашел подходящее изображение")
            except Exception as exc:
                logger.warning("   ⚠️ Ошибка Unsplash API: %s", exc)

        # Fallback: веб-поиск через агрегатор
        try:
            from .parsers.web_image_parser import get_best_web_image

            fallback = get_best_web_image(search_query)
            if fallback:
                logger.info("   ✅ Найдено изображение через веб-поиск")
                return fallback
        except Exception as exc:
            logger.warning("   ⚠️ Ошибка веб-поиска изображения: %s", exc)

        logger.info("   ℹ️ Удалось найти ни одно fallback изображение")
        return None

    except Exception as e:
        logger.warning(f"   ⚠️ Ошибка поиска изображения: {e}")
        return None


"""Сохраняет base64 изображение в media"""
def save_base64_image(base64_data, filename_prefix='gigachat_generated', save_to='images/ai_generated/'):
    """
    Сохраняет base64 изображение в media
    
    Args:
        base64_data: Данные изображения в base64
        filename_prefix: Префикс имени файла
        save_to: Директория для сохранения
    
    Returns:
        Путь к сохраненному файлу или None
    """
    import base64
    from datetime import datetime
    
    try:
        logger.info(f"💾 Сохранение base64 изображения...")
        
        # Декодируем base64
        if isinstance(base64_data, str):
            # Убираем префикс data:image/png;base64, если есть
            if 'base64,' in base64_data:
                base64_data = base64_data.split('base64,')[1]
            
            image_bytes = base64.b64decode(base64_data)
        else:
            image_bytes = base64_data
        
        # Генерируем уникальное имя файла
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{filename_prefix}_{timestamp}.png"
        filepath = os.path.join(save_to, filename)
        
        # Сохраняем файл
        file_content = ContentFile(image_bytes)
        saved_path = default_storage.save(filepath, file_content)
        
        logger.info(f"   ✅ Изображение сохранено: {saved_path}")
        return saved_path
        
    except Exception as e:
        logger.error(f"   ❌ Ошибка сохранения base64 изображения: {e}")
        return None

"""Проверяет что URL ведет на изображение"""
def is_valid_image_url(url):
    """
    Проверяет что URL ведет на изображение
    
    Args:
        url: URL для проверки
    
    Returns:
        True если валидный URL изображения
    """
    if not url:
        return False
    
    # Проверяем расширение
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    url_lower = url.lower().split('?')[0]  # Убираем query параметры
    
    return any(url_lower.endswith(ext) for ext in valid_extensions)

