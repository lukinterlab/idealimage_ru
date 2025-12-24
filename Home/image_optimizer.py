"""
⚠️ УСТАРЕЛО: Используйте utilits.image_optimizer.ImageOptimizer
Этот файл оставлен для обратной совместимости
"""
from utilits.image_optimizer import ImageOptimizer as BaseImageOptimizer, optimize_landing_image

# Обратная совместимость
ImageOptimizer = BaseImageOptimizer
    """Оптимизация изображений для быстрой загрузки"""
    
    # Максимальные размеры для разных типов фонов
    MAX_SIZES = {
        'hero': (1920, 1080),      # Hero секция - Full HD
        'section': (1600, 900),     # Обычные секции
        'thumbnail': (800, 450),    # Превью
    }
    
    # Настройки качества
    QUALITY = {
        'webp': 85,    # WebP - отличное качество при малом размере
        'jpeg': 82,    # JPEG - хорошее качество
    }
    
    # Максимальный размер файла (в байтах)
    MAX_FILE_SIZE = 500 * 1024  # 500 KB
    
    @classmethod
    def optimize_image(cls, image_file, max_size='section', format='webp'):
        """
        Оптимизирует изображение для быстрой загрузки
        
        Args:
            image_file: File object или путь к файлу
            max_size: 'hero', 'section' или 'thumbnail'
            format: 'webp' или 'jpeg'
        
        Returns:
            ContentFile с оптимизированным изображением
        """
        try:
            # Открываем изображение
            if isinstance(image_file, str):
                img = Image.open(image_file)
            else:
                img = Image.open(image_file)
            
            # Конвертируем в RGB если нужно
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Получаем максимальный размер
            max_width, max_height = cls.MAX_SIZES.get(max_size, cls.MAX_SIZES['section'])
            
            # Изменяем размер если нужно (сохраняя пропорции)
            if img.width > max_width or img.height > max_height:
                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                logger.info(f"Resized image to {img.size}")
            
            # Сохраняем в нужном формате
            output = BytesIO()
            
            if format == 'webp':
                img.save(output, format='WEBP', quality=cls.QUALITY['webp'], method=6)
                extension = 'webp'
            else:
                img.save(output, format='JPEG', quality=cls.QUALITY['jpeg'], optimize=True)
                extension = 'jpg'
            
            output.seek(0)
            file_size = len(output.getvalue())
            
            # Если файл всё ещё слишком большой, уменьшаем качество
            if file_size > cls.MAX_FILE_SIZE:
                logger.warning(f"File too large ({file_size} bytes), reducing quality...")
                output = cls._reduce_quality(img, format, target_size=cls.MAX_FILE_SIZE)
                extension = 'webp' if format == 'webp' else 'jpg'
            
            # Создаём ContentFile
            output.seek(0)
            final_size = len(output.getvalue())
            logger.info(f"Optimized image: {final_size} bytes ({final_size/1024:.1f} KB)")
            
            return ContentFile(output.getvalue()), extension
            
        except Exception as e:
            logger.error(f"Error optimizing image: {e}")
            return None, None
    
    @classmethod
    def _reduce_quality(cls, img, format, target_size, min_quality=50):
        """Уменьшает качество изображения до достижения целевого размера"""
        quality = cls.QUALITY.get(format, 80)
        
        while quality >= min_quality:
            output = BytesIO()
            
            if format == 'webp':
                img.save(output, format='WEBP', quality=quality, method=6)
            else:
                img.save(output, format='JPEG', quality=quality, optimize=True)
            
            output.seek(0)
            size = len(output.getvalue())
            
            if size <= target_size:
                logger.info(f"Reduced to quality {quality}, size: {size} bytes")
                return output
            
            quality -= 5
        
        # Если не получилось, возвращаем с минимальным качеством
        output.seek(0)
        return output
    
    @classmethod
    def create_thumbnail(cls, image_file):
        """Создаёт миниатюру для предпросмотра"""
        return cls.optimize_image(image_file, max_size='thumbnail', format='webp')


def optimize_landing_image(image_path, section_type='section'):
    """
    Вспомогательная функция для оптимизации изображения лендинга
    
    Args:
        image_path: Путь к изображению
        section_type: Тип секции ('hero', 'section', 'thumbnail')
    
    Returns:
        (optimized_content, extension) или (None, None)
    """
    return ImageOptimizer.optimize_image(image_path, max_size=section_type, format='webp')


