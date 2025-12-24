from PIL import Image, ImageOps
from uuid import uuid4
from pytils.translit import slugify

def unique_slugify(instance, slug):
    """
    Генератор уникальных SLUG для моделей, в случае существования такого SLUG.
    ИСПРАВЛЕНО: Убирает дефисы в начале и конце slug.
    """
    model = instance.__class__
    unique_slug = slugify(slug)
    
    # Убираем дефисы в начале и конце (проблема: -zagolovok-a51dddbb)
    unique_slug = unique_slug.strip('-')
    
    # Если после обработки slug пустой, используем fallback
    if not unique_slug:
        unique_slug = f'post-{uuid4().hex[:8]}'
    
    while model.objects.filter(slug=unique_slug).exists():
        unique_slug = f'{unique_slug}-{uuid4().hex[:8]}'
    
    return unique_slug


def image_compress(image_path, height, width):
    """
    Оптимизация изображений
    """
    img = Image.open(image_path)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    if img.height > height or img.width > width:
        output_size = (height, width)
        img.thumbnail(output_size)
    img = ImageOps.exif_transpose(img)
    img.save(image_path, format='JPEG', quality=99, optimize=True)


def get_client_ip(request):
    """
    Get user's IP
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    ip = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
    return ip


def generate_image_filename(context_name, extension='webp'):
    """
    Генерирует имя файла на основе контекста (статья/категория/тег)
    с транслитерацией и ограничением до 2 слов
    
    Args:
        context_name: Название статьи/категории/тега
        extension: Расширение файла (по умолчанию webp)
    
    Returns:
        Имя файла вида "fashion-style-1234567890.webp"
    
    Примеры:
        "Модные тренды 2025" → "modnye-trendy-1234567890.webp"
        "Красота и здоровье" → "krasota-zdorove-1234567890.webp"
    """
    from unidecode import unidecode
    import re
    from datetime import datetime
    
    # Транслитерация в латиницу
    transliterated = unidecode(context_name.lower())
    
    # Оставляем только буквы, цифры и пробелы
    cleaned = re.sub(r'[^a-z0-9\s-]', '', transliterated)
    
    # Разбиваем на слова и берем первые 2
    words = [w for w in cleaned.split() if len(w) > 1][:2]  # Только слова длиннее 1 символа
    
    # Соединяем дефисом
    base_name = '-'.join(words) if words else 'image'
    
    # Добавляем уникальный timestamp
    timestamp = int(datetime.now().timestamp())
    
    return f"{base_name}-{timestamp}.{extension}"


# Импортируем из нового унифицированного модуля
from utilits.image_optimizer import optimize_and_convert_to_webp as _optimize_and_convert_to_webp

def optimize_and_convert_to_webp(image_path, context_name=None, max_width=1920, max_height=1080, quality=85):
    """
    Оптимизирует изображение, конвертирует в WebP и переименовывает
    Записывает EXIF метаданные: Author: IdealImage.ru, Copyright
    
    Args:
        image_path: Путь к оригинальному изображению
        context_name: Название для переименования (опционально)
        max_width: Максимальная ширина
        max_height: Максимальная высота
        quality: Качество WebP (0-100)
    
    Returns:
        Путь к новому WebP файлу или None при ошибке
    """
    # Используем унифицированную функцию
    return _optimize_and_convert_to_webp(image_path, context_name, max_width, max_height, quality)