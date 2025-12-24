"""
Template tags для работы с видео
"""
from django import template
from blog.utils_video import normalize_video_url, is_video_url, get_video_platform
from blog.utils_video_optimization import get_video_poster_url

register = template.Library()


@register.filter
def video_embed(url):
    """
    Преобразует обычную ссылку на видео в embed-формат
    
    Использование в шаблоне:
    {{ post.video_url|video_embed }}
    
    Args:
        url: Ссылка на видео
    
    Returns:
        str: Embed-ссылка или пустая строка
    """
    if not url:
        return ''
    
    normalized = normalize_video_url(url)
    return normalized if normalized else ''


@register.filter
def is_video(url):
    """
    Проверяет, является ли URL ссылкой на видео
    
    Использование:
    {% if post.video_url|is_video %}
        <iframe src="{{ post.video_url|video_embed }}"></iframe>
    {% endif %}
    """
    return is_video_url(url) if url else False


@register.filter
def video_platform(url):
    """
    Определяет платформу видео
    
    Использование:
    {{ post.video_url|video_platform }}  # вернет 'youtube', 'vk', и т.д.
    """
    return get_video_platform(url) if url else 'unknown'


@register.filter
def video_poster(video_path):
    """
    Получает URL для poster изображения видео
    
    Использование:
    {{ post.kartinka.name|video_poster }}
    
    Args:
        video_path: Путь к видео файлу
    
    Returns:
        str: URL poster изображения или пустая строка
    """
    if not video_path:
        return ''
    
    poster_url = get_video_poster_url(video_path)
    return poster_url if poster_url else ''

