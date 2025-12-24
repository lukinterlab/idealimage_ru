"""
Утилиты для обработки видео: конвертация, создание poster, оптимизация
Требует FFmpeg на сервере (опционально - работает без него, но без конвертации)
"""
import os
import subprocess
import logging
from pathlib import Path
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image
import io

logger = logging.getLogger(__name__)


def check_ffmpeg_available():
    """
    Проверяет доступность FFmpeg
    
    Returns:
        bool: True если FFmpeg доступен
    """
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_video_info(video_path):
    """
    Получает информацию о видео через FFprobe
    
    Args:
        video_path: Полный путь к видео файлу
    
    Returns:
        dict: Информация о видео (duration, width, height, bitrate) или None
    """
    if not check_ffmpeg_available():
        return None
    
    try:
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            video_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            return None
        
        import json
        info = json.loads(result.stdout)
        
        # Ищем видео поток
        video_stream = None
        for stream in info.get('streams', []):
            if stream.get('codec_type') == 'video':
                video_stream = stream
                break
        
        if not video_stream:
            return None
        
        # Извлекаем информацию
        duration = float(info.get('format', {}).get('duration', 0))
        width = int(video_stream.get('width', 0))
        height = int(video_stream.get('height', 0))
        bitrate = int(info.get('format', {}).get('bit_rate', 0))
        
        return {
            'duration': duration,
            'width': width,
            'height': height,
            'bitrate': bitrate,
            'size_mb': os.path.getsize(video_path) / (1024 * 1024)
        }
    
    except Exception as e:
        logger.warning(f'Ошибка получения информации о видео: {e}')
        return None


def create_video_poster(video_path, output_path=None, time_offset=1.0):
    """
    Создает poster изображение из видео (первый кадр)
    
    Args:
        video_path: Полный путь к видео файлу
        output_path: Путь для сохранения poster (опционально)
        time_offset: Время в секундах для извлечения кадра (по умолчанию 1 сек)
    
    Returns:
        str: Путь к созданному poster изображению или None
    """
    if not check_ffmpeg_available():
        logger.warning('FFmpeg не доступен, poster не будет создан')
        return None
    
    try:
        # Определяем путь для poster
        if not output_path:
            video_dir = os.path.dirname(video_path)
            video_name = Path(video_path).stem
            output_path = os.path.join(video_dir, f'{video_name}_poster.jpg')
        
        # Извлекаем кадр через FFmpeg с правильным масштабированием
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-ss', str(time_offset),  # Время извлечения
            '-vframes', '1',  # Только один кадр
            '-vf', 'scale=1920:1080:force_original_aspect_ratio=decrease:force_divisible_by=2',  # Масштабирование с четными размерами
            '-q:v', '2',  # Качество JPEG (2 = высокое)
            '-y',  # Перезаписать если существует
            output_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 and os.path.exists(output_path):
            # Конвертируем в WebP для лучшего сжатия
            try:
                img = Image.open(output_path)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Сохраняем в WebP
                webp_path = output_path.replace('.jpg', '.webp')
                img.save(webp_path, 'WEBP', quality=80, method=6)
                
                # Удаляем JPEG, оставляем WebP
                if os.path.exists(webp_path):
                    os.remove(output_path)
                    return webp_path
            except Exception as e:
                logger.warning(f'Ошибка конвертации poster в WebP: {e}')
            
            return output_path
        
        return None
    
    except subprocess.TimeoutExpired:
        logger.error(f'Таймаут при создании poster для {video_path}')
        return None
    except Exception as e:
        logger.error(f'Ошибка создания poster: {e}', exc_info=True)
        return None


def optimize_video(input_path, output_path=None, max_bitrate='3M', max_resolution='1920x1080'):
    """
    Оптимизирует видео: сжимает, уменьшает битрейт, разрешение
    
    Args:
        input_path: Полный путь к исходному видео
        output_path: Путь для сохранения оптимизированного видео
        max_bitrate: Максимальный битрейт (например '3M' для 3 Mbps)
        max_resolution: Максимальное разрешение (например '1920x1080')
    
    Returns:
        str: Путь к оптимизированному видео или None
    """
    if not check_ffmpeg_available():
        logger.warning('FFmpeg не доступен, видео не будет оптимизировано')
        return None
    
    try:
        # Определяем путь для оптимизированного видео
        if not output_path:
            video_dir = os.path.dirname(input_path)
            video_name = Path(input_path).stem
            output_path = os.path.join(video_dir, f'{video_name}_optimized.mp4')
        
        # Получаем информацию о видео для правильного масштабирования
        video_info = get_video_info(input_path)
        if video_info:
            width = video_info['width']
            height = video_info['height']
            
            # Вычисляем новые размеры с сохранением пропорций
            max_w, max_h = map(int, max_resolution.split('x'))
            ratio = min(max_w / width, max_h / height, 1.0)
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            
            # Округляем до четных чисел (требование H.264)
            new_width = new_width - (new_width % 2)
            new_height = new_height - (new_height % 2)
            
            # Минимальный размер 2x2
            if new_width < 2:
                new_width = 2
            if new_height < 2:
                new_height = 2
            
            scale_filter = f'scale={new_width}:{new_height}'
        else:
            # Если не удалось получить информацию, используем безопасный фильтр
            scale_filter = f'scale={max_resolution}:force_original_aspect_ratio=decrease:force_divisible_by=2'
        
        # Команда FFmpeg для оптимизации
        # Используем H.264 кодек с оптимальными настройками
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-c:v', 'libx264',  # H.264 кодек
            '-preset', 'medium',  # Баланс скорость/качество
            '-crf', '23',  # Качество (18-28, меньше = лучше качество)
            '-maxrate', max_bitrate,  # Максимальный битрейт
            '-bufsize', f'{int(max_bitrate[:-1]) * 2}M',  # Буфер
            '-vf', scale_filter,  # Масштабирование с четными размерами
            '-c:a', 'aac',  # Аудио кодек
            '-b:a', '128k',  # Аудио битрейт
            '-movflags', '+faststart',  # Быстрый старт (moov atom в начале)
            '-y',  # Перезаписать если существует
            output_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 минут максимум
        )
        
        if result.returncode == 0 and os.path.exists(output_path):
            # Проверяем размер - если оптимизированное больше оригинала, возвращаем None
            original_size = os.path.getsize(input_path)
            optimized_size = os.path.getsize(output_path)
            
            if optimized_size >= original_size:
                logger.info(f'Оптимизированное видео больше оригинала, используем оригинал')
                os.remove(output_path)
                return None
            
            logger.info(f'Видео оптимизировано: {original_size / (1024*1024):.1f}MB -> {optimized_size / (1024*1024):.1f}MB')
            return output_path
        
        logger.error(f'Ошибка оптимизации видео: {result.stderr}')
        return None
    
    except subprocess.TimeoutExpired:
        logger.error(f'Таймаут при оптимизации видео {input_path}')
        return None
    except Exception as e:
        logger.error(f'Ошибка оптимизации видео: {e}', exc_info=True)
        return None


def validate_video_file(video_file):
    """
    Валидирует видео файл: размер, формат, длительность
    
    Args:
        video_file: Django FileField объект
    
    Returns:
        tuple: (is_valid: bool, error_message: str)
    """
    if not video_file:
        return True, None
    
    # Проверка расширения
    allowed_extensions = ['.mp4', '.webm', '.mov', '.avi']
    file_ext = Path(video_file.name).suffix.lower()
    
    if file_ext not in allowed_extensions:
        return False, f'Неподдерживаемый формат видео. Разрешены: {", ".join(allowed_extensions)}'
    
    # Проверка размера (максимум 100MB)
    max_size_mb = 100
    max_size_bytes = max_size_mb * 1024 * 1024
    
    if hasattr(video_file, 'size'):
        file_size = video_file.size
    else:
        # Если файл уже сохранен
        try:
            file_size = os.path.getsize(video_file.path)
        except:
            return True, None  # Не можем проверить, пропускаем
    
    if file_size > max_size_bytes:
        return False, f'Размер видео превышает {max_size_mb}MB. Текущий размер: {file_size / (1024*1024):.1f}MB'
    
    # Проверка длительности (требует FFmpeg)
    if check_ffmpeg_available():
        try:
            # Временно сохраняем файл для проверки
            temp_path = None
            if hasattr(video_file, 'temporary_file_path'):
                temp_path = video_file.temporary_file_path()
            elif hasattr(video_file, 'path'):
                temp_path = video_file.path
            
            if temp_path and os.path.exists(temp_path):
                video_info = get_video_info(temp_path)
                if video_info:
                    max_duration = 600  # 10 минут
                    if video_info['duration'] > max_duration:
                        return False, f'Длительность видео превышает {max_duration // 60} минут. Текущая: {video_info["duration"] / 60:.1f} минут'
        except Exception as e:
            logger.warning(f'Не удалось проверить длительность видео: {e}')
    
    return True, None

