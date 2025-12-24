"""
🚀 УНИФИЦИРОВАННЫЙ ImageOptimizer для всего проекта
Объединяет функциональность из Asistent, Home и utilits
Поддерживает: оптимизацию, WebP конвертацию, скачивание из URL, responsive images
"""
import os
import logging
import requests
from io import BytesIO
from PIL import Image, ImageOps
from PIL.ExifTags import TAGS
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.conf import settings
from urllib.parse import urlparse
from datetime import datetime
from unidecode import unidecode
import re

logger = logging.getLogger(__name__)


class ImageOptimizer:
    """
    Унифицированный оптимизатор изображений для всего проекта
    
    Поддерживает:
    - Оптимизацию размеров и качества
    - Конвертацию в WebP/AVIF
    - Скачивание из URL
    - Генерацию responsive images (srcset)
    - EXIF метаданные для SEO
    - SEO-имена файлов
    """
    
    # Максимальные размеры для разных типов
    MAX_SIZES = {
        'hero': (1920, 1080),        # Hero секция - Full HD
        'article': (1200, 800),      # Основное изображение статьи
        'section': (1600, 900),      # Обычные секции
        'thumbnail': (600, 400),     # Миниатюра
        'gallery': (800, 600),       # Галерея
        'og': (1200, 630),           # Open Graph изображение
    }
    
    # Responsive breakpoints для srcset
    RESPONSIVE_SIZES = {
        'mobile': 320,
        'tablet': 640,
        'desktop': 1024,
        'large': 1920,
    }
    
    # Настройки качества
    QUALITY = {
        'webp': 85,
        'jpeg': 82,
        'avif': 80,  # AVIF - самый современный формат
    }
    
    # Таймаут для скачивания
    DOWNLOAD_TIMEOUT = 15
    
    # Максимальный размер файла
    MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB
    
    def __init__(self):
        """Инициализация сессии для скачивания изображений"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    @classmethod
    def optimize_image(cls, image_file, max_size='section', format='webp', context_name=None):
        """
        Оптимизирует изображение для быстрой загрузки
        
        Args:
            image_file: File object, путь к файлу или BytesIO
            max_size: 'hero', 'article', 'section', 'thumbnail', 'gallery', 'og'
            format: 'webp', 'jpeg' или 'avif'
            context_name: Название для SEO-имени файла (опционально)
        
        Returns:
            (ContentFile, extension) или (None, None)
        """
        try:
            # Открываем изображение
            if isinstance(image_file, str):
                img = Image.open(image_file)
            elif isinstance(image_file, BytesIO):
                img = Image.open(image_file)
            else:
                img = Image.open(image_file)
            
            # Конвертируем в RGB если нужно
            img = cls._convert_to_rgb(img)
            
            # Получаем максимальный размер
            max_width, max_height = cls.MAX_SIZES.get(max_size, cls.MAX_SIZES['section'])
            
            # Изменяем размер если нужно (сохраняя пропорции)
            if img.width > max_width or img.height > max_height:
                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                logger.info(f"Изображение изменено до {img.size}")
            
            # Поворачиваем по EXIF если нужно
            img = ImageOps.exif_transpose(img)
            
            # Сохраняем в нужном формате
            output = BytesIO()
            
            if format == 'webp':
                img.save(output, format='WEBP', quality=cls.QUALITY['webp'], method=6)
                extension = 'webp'
            elif format == 'avif':
                # AVIF требует pillow-avif-plugin, fallback на webp
                try:
                    img.save(output, format='AVIF', quality=cls.QUALITY['avif'])
                    extension = 'avif'
                except Exception:
                    logger.warning("AVIF не поддерживается, используем WebP")
                    img.save(output, format='WEBP', quality=cls.QUALITY['webp'], method=6)
                    extension = 'webp'
            else:
                img.save(output, format='JPEG', quality=cls.QUALITY['jpeg'], optimize=True)
                extension = 'jpg'
            
            output.seek(0)
            file_size = len(output.getvalue())
            
            # Если файл всё ещё слишком большой, уменьшаем качество
            max_file_size = 500 * 1024  # 500 KB
            if file_size > max_file_size:
                logger.warning(f"Файл слишком большой ({file_size} bytes), уменьшаю качество...")
                output = cls._reduce_quality(img, format, target_size=max_file_size)
                output.seek(0)
            
            final_size = len(output.getvalue())
            logger.info(f"✅ Изображение оптимизировано: {final_size} bytes ({final_size/1024:.1f} KB)")
            
            return ContentFile(output.getvalue()), extension
            
        except Exception as e:
            logger.error(f"❌ Ошибка оптимизации изображения: {e}")
            return None, None
    
    @classmethod
    def _convert_to_rgb(cls, img):
        """Конвертирует изображение в RGB"""
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
        return img
    
    @classmethod
    def _reduce_quality(cls, img, format, target_size, min_quality=50):
        """Уменьшает качество изображения до достижения целевого размера"""
        quality = cls.QUALITY.get(format, 80)
        
        while quality >= min_quality:
            output = BytesIO()
            
            if format == 'webp':
                img.save(output, format='WEBP', quality=quality, method=6)
            elif format == 'avif':
                try:
                    img.save(output, format='AVIF', quality=quality)
                except:
                    img.save(output, format='WEBP', quality=quality, method=6)
            else:
                img.save(output, format='JPEG', quality=quality, optimize=True)
            
            output.seek(0)
            size = len(output.getvalue())
            
            if size <= target_size:
                logger.info(f"Качество снижено до {quality}, размер: {size} bytes")
                return output
            
            quality -= 5
        
        output.seek(0)
        return output
    
    def download_and_optimize(self, url: str, size_type: str = 'article', format: str = 'webp') -> dict:
        """
        Скачивает изображение из URL и оптимизирует его
        
        Args:
            url: URL изображения
            size_type: Тип размера
            format: Формат ('webp', 'jpeg', 'avif')
        
        Returns:
            Dict с ключами: file, filename, format, size, success
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
            filename_base = os.path.splitext(original_filename)[0][:50]
            
            # Оптимизируем
            optimized_file, extension = self.optimize_image(img, size_type, format)
            
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
    
    @classmethod
    def create_thumbnail(cls, image_file):
        """Создаёт миниатюру для предпросмотра"""
        return cls.optimize_image(image_file, max_size='thumbnail', format='webp')
    
    @classmethod
    def generate_responsive_images(cls, image_path, context_name=None):
        """
        Генерирует responsive images (несколько размеров) для srcset
        
        Args:
            image_path: Путь к оригинальному изображению
            context_name: Название для SEO-имени (опционально)
        
        Returns:
            Dict с путями к разным размерам и srcset строкой
        """
        try:
            if not os.path.exists(image_path):
                return None
            
            img = Image.open(image_path)
            original_width = img.width
            
            responsive_images = {}
            srcset_parts = []
            
            # Генерируем разные размеры
            for size_name, target_width in cls.RESPONSIVE_SIZES.items():
                if target_width > original_width:
                    continue  # Пропускаем размеры больше оригинала
                
                # Изменяем размер
                ratio = target_width / original_width
                new_height = int(img.height * ratio)
                resized_img = img.resize((target_width, new_height), Image.Resampling.LANCZOS)
                
                # Сохраняем
                base_name = cls._generate_seo_filename(context_name or 'image', 'webp')
                filename = f"{base_name}-{target_width}w.webp"
                output_path = os.path.join(os.path.dirname(image_path), filename)
                
                resized_img.save(output_path, 'WEBP', quality=cls.QUALITY['webp'], method=6)
                
                responsive_images[size_name] = {
                    'path': output_path,
                    'width': target_width,
                    'url': f"/media/{os.path.relpath(output_path, settings.MEDIA_ROOT)}"
                }
                
                srcset_parts.append(f"{responsive_images[size_name]['url']} {target_width}w")
            
            return {
                'images': responsive_images,
                'srcset': ', '.join(srcset_parts),
                'sizes': '(max-width: 320px) 320px, (max-width: 640px) 640px, (max-width: 1024px) 1024px, 1920px'
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации responsive images: {e}")
            return None
    
    @classmethod
    def _generate_seo_filename(cls, context_name, extension='webp'):
        """Генерирует SEO-имя файла"""
        # Транслитерация в латиницу
        transliterated = unidecode(context_name.lower())
        
        # Оставляем только буквы, цифры и пробелы
        cleaned = re.sub(r'[^a-z0-9\s-]', '', transliterated)
        
        # Разбиваем на слова и берем первые 2
        words = [w for w in cleaned.split() if len(w) > 1][:2]
        
        # Соединяем дефисом
        base_name = '-'.join(words) if words else 'image'
        
        # Добавляем уникальный timestamp
        timestamp = int(datetime.now().timestamp())
        
        return f"{base_name}-{timestamp}.{extension}"
    
    @classmethod
    def optimize_and_convert_to_webp(cls, image_path, context_name=None, max_width=1920, max_height=1080, quality=85):
        """
        Оптимизирует изображение, конвертирует в WebP и переименовывает
        Записывает EXIF метаданные для SEO
        
        Args:
            image_path: Путь к оригинальному изображению
            context_name: Название для переименования (опционально)
            max_width: Максимальная ширина
            max_height: Максимальная высота
            quality: Качество WebP (0-100)
        
        Returns:
            Путь к новому WebP файлу или None при ошибке
        """
        try:
            # Пропускаем конвертацию если уже WebP
            if image_path.lower().endswith('.webp'):
                full_path = image_path if os.path.isabs(image_path) else os.path.join(settings.MEDIA_ROOT, image_path)
                if not os.path.exists(full_path):
                    return None
                return os.path.relpath(full_path, settings.MEDIA_ROOT)
            
            # Полный путь к файлу
            full_path = image_path if os.path.isabs(image_path) else os.path.join(settings.MEDIA_ROOT, image_path)
            
            # Проверяем существование файла
            if not os.path.exists(full_path):
                return None
            
            # Генерируем новое имя файла
            if context_name:
                new_filename = cls._generate_seo_filename(context_name, extension='webp')
            else:
                base_name = os.path.splitext(os.path.basename(full_path))[0]
                timestamp = int(datetime.now().timestamp())
                new_filename = f"{base_name}-{timestamp}.webp"
            
            # Путь для нового файла
            original_dir = os.path.dirname(full_path)
            new_path = os.path.join(original_dir, new_filename)
            
            # Открываем и конвертируем изображение
            img = Image.open(full_path)
            
            # Конвертируем в RGB
            img = cls._convert_to_rgb(img)
            
            # Изменяем размер если нужно
            if img.width > max_width or img.height > max_height:
                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            # Поворачиваем по EXIF
            img = ImageOps.exif_transpose(img)
            
            # Записываем EXIF метаданные для SEO
            try:
                from PIL.Image import Exif
                exif = Exif()
                
                tag_to_code = {v: k for k, v in TAGS.items()}
                
                exif_dict = {
                    'Artist': 'IdealImage.ru',
                    'Copyright': f'© {datetime.now().year} IdealImage.ru. All rights reserved.',
                    'ImageDescription': context_name if context_name else 'Fashion and Style Image',
                    'Software': 'IdealImage.ru Image Optimizer',
                    'DateTime': datetime.now().strftime('%Y:%m:%d %H:%M:%S'),
                }
                
                for tag_name, value in exif_dict.items():
                    if tag_name in tag_to_code:
                        exif[tag_to_code[tag_name]] = value
                
                img.save(new_path, 'WEBP', quality=quality, method=6, exif=exif.tobytes())
                
            except Exception as exif_error:
                logger.warning(f"Не удалось записать EXIF для {new_filename}: {exif_error}")
                img.save(new_path, 'WEBP', quality=quality, method=6)
            
            # Удаляем оригинал
            if os.path.exists(full_path) and full_path != new_path:
                os.remove(full_path)
            
            # Возвращаем относительный путь
            relative_path = os.path.relpath(new_path, settings.MEDIA_ROOT)
            return relative_path
            
        except Exception as e:
            logger.error(f"Ошибка конвертации изображения {image_path}: {e}")
            return None


# Функции-обертки для обратной совместимости
def optimize_landing_image(image_path, section_type='section'):
    """Вспомогательная функция для оптимизации изображения лендинга"""
    return ImageOptimizer.optimize_image(image_path, max_size=section_type, format='webp')


def optimize_and_convert_to_webp(image_path, context_name=None, max_width=1920, max_height=1080, quality=85):
    """Вспомогательная функция для обратной совместимости"""
    return ImageOptimizer.optimize_and_convert_to_webp(image_path, context_name, max_width, max_height, quality)

