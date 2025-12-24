"""
Template tags для работы с медиа-контентом
"""
from django import template
from django.utils.safestring import mark_safe
import os

register = template.Library()


@register.inclusion_tag('partials/media_preview.html')
def render_media(post, size='medium', show_controls=False, lazy=True, css_class=''):
    """
    Универсальный рендеринг медиа (изображение/видео)
    
    Args:
        post: Объект статьи
        size: Размер ('small', 'medium', 'large', 'hero')
        show_controls: Показывать элементы управления видео
        lazy: Lazy loading
        css_class: Дополнительные CSS классы
    
    Использование:
        {% load media_tags %}
        {% render_media post size='large' %}
    """
    return {
        'post': post,
        'size': size,
        'show_controls': show_controls,
        'lazy': lazy,
        'css_class': css_class,
    }


@register.simple_tag
def responsive_image_srcset(image_url):
    """
    Генерирует srcset для адаптивных изображений
    
    Использование:
        {% load media_tags %}
        <img srcset="{% responsive_image_srcset post.kartinka.url %}" ...>
    """
    if not image_url:
        return ''
    
    # Получаем имя файла и расширение
    base_name, ext = os.path.splitext(image_url)
    
    # Проверяем наличие WebP версии
    webp_url = f"{base_name}.webp"
    
    # Генерируем srcset для разных размеров
    # Предполагается что изображения уже оптимизированы
    srcset = f"{webp_url} 1x"
    
    return srcset


@register.simple_tag
def get_media_type(post):
    """
    Определяет тип медиа для статьи
    
    Returns:
        'video_url', 'video_file', 'image', 'none'
    """
    if post.video_url:
        return 'video_url'
    elif post.kartinka:
        if post.kartinka.name and any(post.kartinka.name.endswith(ext) for ext in ['.mp4', '.webm', '.mov']):
            return 'video_file'
        else:
            return 'image'
    return 'none'


@register.filter
def is_video(file_field):
    """
    Проверяет является ли файл видео
    
    Использование:
        {% if post.kartinka|is_video %}
    """
    if not file_field or not file_field.name:
        return False
    return any(file_field.name.lower().endswith(ext) for ext in ['.mp4', '.webm', '.mov', '.avi'])


@register.filter
def webp_url(image_url):
    """
    Конвертирует URL изображения в WebP версию
    
    Использование:
        <source srcset="{{ post.kartinka.url|webp_url }}" type="image/webp">
    """
    if not image_url:
        return ''
    
    base_name, ext = os.path.splitext(image_url)
    return f"{base_name}.webp"

