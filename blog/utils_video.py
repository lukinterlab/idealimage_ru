"""
Утилиты для работы с видео URL
Преобразует обычные ссылки в embed-формат для различных платформ
"""
import re
from urllib.parse import urlparse, parse_qs


def normalize_video_url(url):
    """
    Преобразует обычную ссылку на видео в embed-формат
    
    Поддерживаемые платформы:
    - YouTube (youtube.com, youtu.be)
    - VK Video (vk.com/video)
    - Rutube (rutube.ru)
    - Dzen Video (dzen.ru/video)
    - Яндекс.Видео (yandex.ru/video)
    
    Args:
        url: Ссылка на видео (обычная или уже embed)
    
    Returns:
        str: Embed-ссылка или None если не удалось преобразовать
    """
    if not url:
        return None
    
    url = url.strip()
    
    # Если уже embed-ссылка, возвращаем как есть
    if 'embed' in url or 'iframe' in url:
        # Извлекаем URL из embed-кода если нужно
        embed_match = re.search(r'src=["\']([^"\']+)["\']', url)
        if embed_match:
            url = embed_match.group(1)
        else:
            return url
    
    try:
        parsed = urlparse(url)
    except Exception:
        return None
    
    # YouTube
    if 'youtube.com' in parsed.netloc or 'youtu.be' in parsed.netloc:
        video_id = None
        
        if 'youtu.be' in parsed.netloc:
            # Короткая ссылка: https://youtu.be/VIDEO_ID
            video_id = parsed.path.lstrip('/')
        elif 'youtube.com' in parsed.netloc:
            if '/embed/' in parsed.path:
                # Уже embed
                return url
            elif '/watch' in parsed.path:
                # Обычная ссылка: https://www.youtube.com/watch?v=VIDEO_ID
                video_id = parse_qs(parsed.query).get('v', [None])[0]
            elif '/shorts/' in parsed.path:
                # YouTube Shorts: https://www.youtube.com/shorts/VIDEO_ID
                video_id = parsed.path.split('/shorts/')[-1].split('?')[0]
            elif '/v/' in parsed.path:
                # Альтернативный формат: https://www.youtube.com/v/VIDEO_ID
                video_id = parsed.path.split('/v/')[-1].split('?')[0]
        
        if video_id:
            # Очищаем video_id от лишних символов
            video_id = re.sub(r'[^a-zA-Z0-9_-]', '', video_id)
            return f'https://www.youtube.com/embed/{video_id}'
    
    # VK Video
    elif 'vk.com' in parsed.netloc or 'vk.ru' in parsed.netloc:
        if '/video' in parsed.path:
            # Формат: https://vk.com/video-123456_789 или https://vk.com/video123456_789
            video_match = re.search(r'/video-?(\d+_\d+)', parsed.path)
            if video_match:
                video_id = video_match.group(1)
                return f'https://vk.com/video_ext.php?oid={video_id.split("_")[0]}&id={video_id.split("_")[1]}&hash='
            # Или прямой embed
            video_match = re.search(r'/video(\d+_\d+)', parsed.path)
            if video_match:
                video_id = video_match.group(1)
                return f'https://vk.com/video_ext.php?oid={video_id.split("_")[0]}&id={video_id.split("_")[1]}&hash='
    
    # Rutube
    elif 'rutube.ru' in parsed.netloc:
        if '/video/' in parsed.path:
            video_id = parsed.path.split('/video/')[-1].split('/')[0]
            if video_id:
                return f'https://rutube.ru/play/embed/{video_id}'
        elif '/play/embed/' in parsed.path:
            # Уже embed
            return url
    
    # Dzen Video
    elif 'dzen.ru' in parsed.netloc:
        if '/video/' in parsed.path:
            # Формат: https://dzen.ru/video/watch/VIDEO_ID
            video_match = re.search(r'/video/watch/([a-zA-Z0-9_-]+)', parsed.path)
            if video_match:
                video_id = video_match.group(1)
                return f'https://dzen.ru/video/watch/{video_id}?embed=true'
    
    # Яндекс.Видео
    elif 'yandex.ru' in parsed.netloc or 'ya.ru' in parsed.netloc:
        if '/video' in parsed.path:
            # Пытаемся извлечь video_id из URL
            video_match = re.search(r'/video/([a-zA-Z0-9_-]+)', parsed.path)
            if video_match:
                video_id = video_match.group(1)
                return f'https://yandex.ru/video/embed/{video_id}'
    
    # Если не удалось определить платформу, но URL валидный, возвращаем как есть
    # (может быть прямой embed-URL или другой формат)
    if parsed.scheme in ('http', 'https'):
        return url
    
    return None


def is_video_url(url):
    """
    Проверяет, является ли URL ссылкой на видео
    
    Args:
        url: URL для проверки
    
    Returns:
        bool: True если это ссылка на видео
    """
    if not url:
        return False
    
    url_lower = url.lower()
    video_domains = [
        'youtube.com', 'youtu.be',
        'vk.com', 'vk.ru',
        'rutube.ru',
        'dzen.ru',
        'yandex.ru/video',
        'vimeo.com',
    ]
    
    return any(domain in url_lower for domain in video_domains)


def get_video_platform(url):
    """
    Определяет платформу видео по URL
    
    Args:
        url: URL видео
    
    Returns:
        str: Название платформы ('youtube', 'vk', 'rutube', 'dzen', 'yandex', 'unknown')
    """
    if not url:
        return 'unknown'
    
    url_lower = url.lower()
    
    if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return 'youtube'
    elif 'vk.com' in url_lower or 'vk.ru' in url_lower:
        return 'vk'
    elif 'rutube.ru' in url_lower:
        return 'rutube'
    elif 'dzen.ru' in url_lower:
        return 'dzen'
    elif 'yandex.ru' in url_lower or 'ya.ru' in url_lower:
        return 'yandex'
    elif 'vimeo.com' in url_lower:
        return 'vimeo'
    
    return 'unknown'

