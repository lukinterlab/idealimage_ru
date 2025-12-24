"""
Валидация качества изображений для AI-генерируемых статей
"""
from PIL import Image
import os
import logging

logger = logging.getLogger(__name__)


class ImageQualityValidator:
    """Валидатор качества изображений"""
    
    # Минимальные требования к изображениям для статей
    MIN_WIDTH = 800
    MIN_HEIGHT = 600
    MIN_ASPECT_RATIO = 0.5  # 1:2 (вертикальное)
    MAX_ASPECT_RATIO = 2.5  # 2.5:1 (горизонтальное)
    MAX_FILE_SIZE_MB = 10
    
    # Допустимые форматы
    ALLOWED_FORMATS = {'JPEG', 'JPG', 'PNG', 'WEBP'}
    
    def __init__(self, min_width=None, min_height=None):
        """
        Args:
            min_width: Минимальная ширина (по умолчанию 800px)
            min_height: Минимальная высота (по умолчанию 600px)
        """
        self.min_width = min_width or self.MIN_WIDTH
        self.min_height = min_height or self.MIN_HEIGHT
    
    def validate(self, image_path):
        """
        Проверяет качество изображения
        
        Args:
            image_path: Путь к файлу изображения
        
        Returns:
            tuple: (is_valid, error_message, metadata)
        """
        try:
            # Проверка существования файла
            if not os.path.exists(image_path):
                return False, "Файл не найден", None
            
            # Проверка размера файла
            file_size_mb = os.path.getsize(image_path) / (1024 * 1024)
            if file_size_mb > self.MAX_FILE_SIZE_MB:
                return False, f"Файл слишком большой: {file_size_mb:.1f} MB (макс {self.MAX_FILE_SIZE_MB} MB)", None
            
            # Открываем изображение
            with Image.open(image_path) as img:
                width, height = img.size
                format_name = img.format
                
                metadata = {
                    'width': width,
                    'height': height,
                    'format': format_name,
                    'file_size_mb': round(file_size_mb, 2),
                    'aspect_ratio': round(width / height, 2)
                }
                
                # Проверка формата
                if format_name not in self.ALLOWED_FORMATS:
                    return False, f"Неподдерживаемый формат: {format_name}. Допустимые: {', '.join(self.ALLOWED_FORMATS)}", metadata
                
                # Проверка минимального разрешения
                if width < self.min_width:
                    return False, f"Ширина слишком мала: {width}px < {self.min_width}px", metadata
                
                if height < self.min_height:
                    return False, f"Высота слишком мала: {height}px < {self.min_height}px", metadata
                
                # Проверка соотношения сторон
                aspect_ratio = width / height
                if aspect_ratio < self.MIN_ASPECT_RATIO:
                    return False, f"Слишком вертикальное изображение: {aspect_ratio:.2f} < {self.MIN_ASPECT_RATIO}", metadata
                
                if aspect_ratio > self.MAX_ASPECT_RATIO:
                    return False, f"Слишком горизонтальное изображение: {aspect_ratio:.2f} > {self.MAX_ASPECT_RATIO}", metadata
                
                # Все проверки пройдены
                logger.info(f"✅ Изображение валидно: {width}x{height}, {format_name}, {file_size_mb:.2f} MB")
                return True, "OK", metadata
                
        except Exception as e:
            logger.error(f"❌ Ошибка при валидации изображения: {e}")
            return False, f"Ошибка обработки: {str(e)}", None
    
    def validate_from_url(self, image_url):
        """
        Валидация изображения по URL (без скачивания)
        Проверяет только расширение и доступность
        
        Args:
            image_url: URL изображения
        
        Returns:
            bool: True если URL выглядит валидным
        """
        if not image_url:
            return False
        
        # Проверка расширения в URL
        url_lower = image_url.lower()
        valid_extensions = ['.jpg', '.jpeg', '.png', '.webp']
        
        has_valid_ext = any(url_lower.endswith(ext) for ext in valid_extensions)
        
        # Дополнительные проверки
        if 'data:image' in url_lower:
            return False  # Base64 изображения пропускаем
        
        if len(image_url) < 10:
            return False  # Слишком короткий URL
        
        return has_valid_ext
    
    def get_best_image(self, image_paths):
        """
        Выбирает лучшее изображение из списка
        
        Args:
            image_paths: Список путей к изображениям
        
        Returns:
            str: Путь к лучшему изображению или None
        """
        best_image = None
        best_score = 0
        
        for path in image_paths:
            is_valid, error, metadata = self.validate(path)
            
            if not is_valid:
                logger.debug(f"Изображение {path} не прошло валидацию: {error}")
                continue
            
            # Рассчитываем score (больше = лучше)
            # Предпочитаем изображения ближе к 1200x800 (идеальный размер для статей)
            width = metadata['width']
            height = metadata['height']
            
            # Оптимальные размеры
            optimal_width = 1200
            optimal_height = 800
            
            # Чем ближе к оптимальным размерам, тем выше score
            width_diff = abs(width - optimal_width) / optimal_width
            height_diff = abs(height - optimal_height) / optimal_height
            
            score = 100 - (width_diff + height_diff) * 50
            
            # Бонус за хорошее соотношение сторон (1.5:1 идеал)
            aspect_ratio = metadata['aspect_ratio']
            if 1.3 <= aspect_ratio <= 1.7:
                score += 10
            
            logger.debug(f"Изображение {path}: score={score:.1f}")
            
            if score > best_score:
                best_score = score
                best_image = path
        
        if best_image:
            logger.info(f"🏆 Лучшее изображение выбрано с score={best_score:.1f}: {best_image}")
        
        return best_image


def validate_image(image_path, min_width=800, min_height=600):
    """
    Удобная функция для быстрой валидации
    
    Args:
        image_path: Путь к изображению
        min_width: Минимальная ширина
        min_height: Минимальная высота
    
    Returns:
        bool: True если изображение валидно
    """
    validator = ImageQualityValidator(min_width=min_width, min_height=min_height)
    is_valid, error, metadata = validator.validate(image_path)
    
    if not is_valid:
        logger.warning(f"Изображение не прошло валидацию: {error}")
    
    return is_valid

