"""
⚠️ УСТАРЕЛО: Используйте utilits.image_optimizer.ImageOptimizer
Этот файл оставлен для обратной совместимости
"""
from utilits.image_optimizer import ImageOptimizer as BaseImageOptimizer

# Обратная совместимость
ImageOptimizer = BaseImageOptimizer
    """Оптимизация и обработка изображений для статей"""
    
    # Максимальные размеры
    MAX_SIZES = {
        'article': (1200, 800),     # Основное изображение статьи
        'thumbnail': (600, 400),     # Миниатюра
        'gallery': (800, 600),       # Галерея
    }
    
    # Качество
    QUALITY = {
        'webp': 85,
        'jpeg': 82,
    }
    
    # Таймаут для скачивания
    DOWNLOAD_TIMEOUT = 15
    
    # Максимальный размер файла
    MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB
    
    
    """Инициализация сессии для скачивания изображений"""
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    
    """Скачивает изображение из URL и оптимизирует его"""
    def download_and_optimize(self, url: str, size_type: str = 'article') -> dict:
        """
        Скачивает изображение из URL и оптимизирует его
        
        Args:
            url: URL изображения
            size_type: Тип размера ('article', 'thumbnail', 'gallery')
        
        Returns:
            Dict с ключами: file, filename, format, size
        """
        logger.info(f"🖼️ Скачивание изображения: {url}")
        
        try:
            # Скачиваем
            response = self.session.get(url, timeout=self.DOWNLOAD_TIMEOUT, stream=True)
            response.raise_for_status()
            
            # Проверяем размер
            content_length = response.headers.get('Content-Length')
            if content_length and int(content_length) > self.MAX_FILE_SIZE:
                logger.warning(f"Изображение слишком большое: {content_length} bytes")
                return None
            
            # Читаем контент
            image_data = BytesIO(response.content)
            
            # Открываем изображение
            img = Image.open(image_data)
            
            # Генерируем имя файла
            parsed_url = urlparse(url)
            original_filename = os.path.basename(parsed_url.path) or 'image.jpg'
            filename_base = os.path.splitext(original_filename)[0][:50]  # Ограничиваем длину
            
            # Оптимизируем
            optimized_file, extension = self._optimize_image(img, size_type, format='webp')
            
            if not optimized_file:
                return None
            
            filename = f"{filename_base}.{extension}"
            
            logger.info(f"✅ Изображение оптимизировано: {filename}")
            
            return {
                'file': optimized_file,
                'filename': filename,
                'format': extension,
                'original_url': url,
                'success': True
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Ошибка скачивания изображения {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка обработки изображения {url}: {e}")
            return None
    
    """Оптимизирует изображение"""
    def _optimize_image(self, img: Image.Image, size_type: str, format: str = 'webp'):
        """
        Оптимизирует изображение
        
        Args:
            img: PIL Image объект
            size_type: Тип размера
            format: Формат ('webp' или 'jpeg')
        
        Returns:
            (ContentFile, extension) или (None, None)
        """
        try:
            # Конвертируем в RGB
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                if img.mode in ('RGBA', 'LA'):
                    background.paste(img, mask=img.split()[-1])
                else:
                    background.paste(img)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Изменяем размер
            max_width, max_height = self.MAX_SIZES.get(size_type, self.MAX_SIZES['article'])
            
            if img.width > max_width or img.height > max_height:
                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                logger.info(f"Изображение изменено до {img.size}")
            
            # Сохраняем
            output = BytesIO()
            
            if format == 'webp':
                img.save(output, format='WEBP', quality=self.QUALITY['webp'], method=6)
                extension = 'webp'
            else:
                img.save(output, format='JPEG', quality=self.QUALITY['jpeg'], optimize=True)
                extension = 'jpg'
            
            output.seek(0)
            file_size = len(output.getvalue())
            
            # Если слишком большой - уменьшаем качество
            if file_size > 500 * 1024:  # 500 KB
                logger.info("Уменьшаю качество для оптимизации размера...")
                output = self._reduce_quality(img, format)
            
            output.seek(0)
            final_size = len(output.getvalue())
            logger.info(f"Финальный размер: {final_size / 1024:.1f} KB")
            
            return ContentFile(output.getvalue()), extension
            
        except Exception as e:
            logger.error(f"Ошибка оптимизации: {e}")
            return None, None
    
    """Уменьшает качество изображения"""
    def _reduce_quality(self, img: Image.Image, format: str, min_quality: int = 60):
        """Уменьшает качество изображения"""
        quality = self.QUALITY.get(format, 80)
        
        while quality >= min_quality:
            output = BytesIO()
            
            if format == 'webp':
                img.save(output, format='WEBP', quality=quality, method=6)
            else:
                img.save(output, format='JPEG', quality=quality, optimize=True)
            
            output.seek(0)
            size = len(output.getvalue())
            
            if size <= 500 * 1024:  # 500 KB
                logger.info(f"Качество снижено до {quality}, размер: {size / 1024:.1f} KB")
                return output
            
            quality -= 5
        
        output.seek(0)
        return output
    
    """Создаёт миниатюру изображения"""
    def create_thumbnail(self, image_url: str) -> dict:
        """Создаёт миниатюру изображения"""
        return self.download_and_optimize(image_url, size_type='thumbnail')

