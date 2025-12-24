"""
Утилиты для оптимизации видео
"""
import os
from django.conf import settings
from pathlib import Path


def get_video_poster_url(video_path):
    """
    Получает URL для poster изображения видео
    
    Логика:
    1. Проверяет наличие .jpg/.webp файла с тем же именем
    2. Если нет - возвращает None (будет использован первый кадр)
    
    Args:
        video_path: Путь к видео файлу (относительно MEDIA_ROOT)
    
    Returns:
        str: URL poster изображения или None
    """
    if not video_path:
        return None
    
    # Убираем расширение видео
    base_path = Path(video_path).stem
    video_dir = Path(video_path).parent
    
    # Проверяем наличие poster изображений
    poster_extensions = ['.jpg', '.jpeg', '.webp', '.png']
    for ext in poster_extensions:
        poster_path = video_dir / f"{base_path}{ext}"
        full_poster_path = Path(settings.MEDIA_ROOT) / poster_path
        
        if full_poster_path.exists():
            return f"{settings.MEDIA_URL}{poster_path}"
    
    return None


def should_use_lazy_loading(video_size_mb=None):
    """
    Определяет, нужно ли использовать lazy loading для видео
    
    Args:
        video_size_mb: Размер видео в MB (опционально)
    
    Returns:
        bool: True если нужно lazy loading
    """
    # Если видео больше 5MB - используем lazy loading
    if video_size_mb and video_size_mb > 5:
        return True
    
    # По умолчанию - lazy loading для всех видео
    return True


def get_optimal_preload_strategy(video_size_mb=None, is_autoplay=False):
    """
    Определяет оптимальную стратегию preload для видео
    
    Args:
        video_size_mb: Размер видео в MB
        is_autoplay: Автопроигрывание включено
    
    Returns:
        str: 'none', 'metadata', 'auto'
    """
    if is_autoplay:
        # Для autoplay - минимум preload
        return 'none'
    
    if video_size_mb and video_size_mb > 10:
        # Большие видео - только metadata
        return 'metadata'
    
    # По умолчанию - metadata (баланс между скоростью и функциональностью)
    return 'metadata'


def get_video_file_size_mb(video_path):
    """
    Получает размер видео файла в MB
    
    Args:
        video_path: Путь к видео (относительно MEDIA_ROOT)
    
    Returns:
        float: Размер в MB или None
    """
    if not video_path:
        return None
    
    full_path = Path(settings.MEDIA_ROOT) / video_path
    if full_path.exists():
        size_bytes = full_path.stat().st_size
        return size_bytes / (1024 * 1024)  # Конвертация в MB
    
    return None

