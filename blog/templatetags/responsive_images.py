"""
Template tags для responsive images (srcset)
"""
from django import template
from django.conf import settings
import os

register = template.Library()


@register.simple_tag
def responsive_image_srcset(image_field, sizes=None):
    """
    Генерирует srcset для responsive images
    
    Args:
        image_field: FileField изображения
        sizes: Атрибут sizes (опционально)
    
    Returns:
        Строка srcset или пустая строка
    """
    if not image_field:
        return ''
    
    try:
        from utilits.image_optimizer import ImageOptimizer
        
        # Получаем путь к изображению
        image_path = image_field.path if hasattr(image_field, 'path') else None
        if not image_path or not os.path.exists(image_path):
            # Fallback: используем URL
            image_url = image_field.url if hasattr(image_field, 'url') else ''
            if image_url:
                return f'{settings.SITE_URL}{image_url} 1920w'
            return ''
        
        # Генерируем responsive images
        responsive = ImageOptimizer.generate_responsive_images(image_path)
        
        if responsive and responsive.get('srcset'):
            return responsive['srcset']
        
        # Fallback
        image_url = image_field.url if hasattr(image_field, 'url') else ''
        if image_url:
            return f'{settings.SITE_URL}{image_url} 1920w'
        
        return ''
        
    except Exception as e:
        import logging
        logging.error(f"Ошибка генерации srcset: {e}")
        return ''


@register.simple_tag
def responsive_image_sizes():
    """
    Возвращает стандартный sizes атрибут для responsive images
    """
    return '(max-width: 320px) 320px, (max-width: 640px) 640px, (max-width: 1024px) 1024px, 1920px'


@register.inclusion_tag('blog/partials/responsive_image.html')
def responsive_image(image_field, alt_text='', class_name='', lazy=True):
    """
    Рендерит responsive image с srcset
    
    Args:
        image_field: FileField изображения
        alt_text: Alt текст
        class_name: CSS класс
        lazy: Использовать lazy loading
    
    Returns:
        Context для шаблона
    """
    image_url = image_field.url if image_field and hasattr(image_field, 'url') else ''
    
    if not image_url:
        return {
            'image_url': '',
            'srcset': '',
            'sizes': '',
            'alt_text': alt_text,
            'class_name': class_name,
            'lazy': lazy
        }
    
    # Генерируем srcset
    srcset = responsive_image_srcset(image_field)
    sizes = responsive_image_sizes()
    
    # Если srcset не сгенерирован, используем обычный URL
    if not srcset:
        srcset = f'{settings.SITE_URL}{image_url} 1920w'
    
    return {
        'image_url': f'{settings.SITE_URL}{image_url}',
        'srcset': srcset,
        'sizes': sizes,
        'alt_text': alt_text,
        'class_name': class_name,
        'lazy': lazy
    }

