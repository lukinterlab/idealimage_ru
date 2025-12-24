"""
Команда для парсинга медиа файлов из оригинального сайта салона красоты
Скачивает все изображения и сохраняет в media/landing2/
"""
import os
import re
import requests
from urllib.parse import urljoin, urlparse
from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path


class Command(BaseCommand):
    help = 'Парсинг медиа файлов с оригинального сайта салона красоты'

    def __init__(self):
        super().__init__()
        self.base_url = 'https://mos-263463.oml.ru/'
        self.media_dir = Path(settings.MEDIA_ROOT) / 'landing2'
        self.downloaded_files = {}
        
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Перезаписать существующие файлы',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        
        self.stdout.write(self.style.SUCCESS('🚀 Начинаем парсинг медиа файлов...'))
        
        # Создаем директории
        self.create_directories()
        
        # Скачиваем HTML страницы
        self.stdout.write('📄 Загружаем HTML...')
        html_content = self.download_html()
        
        if not html_content:
            self.stdout.write(self.style.ERROR('❌ Не удалось загрузить HTML'))
            return
        
        # Извлекаем все URL изображений
        self.stdout.write('🔍 Ищем изображения...')
        image_urls = self.extract_image_urls(html_content)
        
        self.stdout.write(f'✅ Найдено {len(image_urls)} изображений')
        
        # Скачиваем изображения
        self.stdout.write('⬇️  Скачиваем изображения...')
        downloaded = 0
        skipped = 0
        
        for url in image_urls:
            if self.download_image(url, force):
                downloaded += 1
            else:
                skipped += 1
            
            # Прогресс
            total = downloaded + skipped
            if total % 5 == 0:
                self.stdout.write(f'   Обработано: {total}/{len(image_urls)}')
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Парсинг завершен!'))
        self.stdout.write(f'   Скачано: {downloaded}')
        self.stdout.write(f'   Пропущено: {skipped}')
        self.stdout.write(f'   Папка: {self.media_dir}')
        
        # Создаем mapping файл
        self.create_mapping_file()
        
    def create_directories(self):
        """Создает необходимые директории"""
        dirs = ['images', 'portfolio', 'team', 'brands', 'icons', 'backgrounds']
        for dir_name in dirs:
            dir_path = self.media_dir / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
        self.stdout.write(self.style.SUCCESS('✅ Директории созданы'))
    
    def download_html(self):
        """Скачивает HTML страницу"""
        try:
            response = requests.get(self.base_url, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка загрузки HTML: {e}'))
            return None
    
    def extract_image_urls(self, html):
        """Извлекает все URL изображений из HTML"""
        image_urls = set()
        
        # Ищем img src
        img_pattern = r'<img[^>]+src=["\'](https?://[^"\']+)["\']'
        for match in re.finditer(img_pattern, html):
            image_urls.add(match.group(1))
        
        # Ищем background-image в style
        bg_pattern = r'background-image:\s*url\(["\']?(https?://[^"\')\s]+)["\']?\)'
        for match in re.finditer(bg_pattern, html):
            image_urls.add(match.group(1))
        
        # Ищем в inline styles
        inline_pattern = r'style=["\']([^"\']*background-image:[^"\']*)["\']'
        for match in re.finditer(inline_pattern, html):
            style_content = match.group(1)
            bg_urls = re.findall(r'url\(["\']?(https?://[^"\')\s]+)["\']?\)', style_content)
            image_urls.update(bg_urls)
        
        # Конвертируем относительные пути в абсолютные
        absolute_urls = []
        for url in image_urls:
            if url.startswith('http'):
                absolute_urls.append(url)
            else:
                absolute_urls.append(urljoin(self.base_url, url))
        
        return list(set(absolute_urls))
    
    def download_image(self, url, force=False):
        """Скачивает одно изображение"""
        try:
            # Определяем имя файла
            parsed = urlparse(url)
            filename = os.path.basename(parsed.path)
            
            if not filename or '.' not in filename:
                # Генерируем имя из хэша URL
                import hashlib
                filename = hashlib.md5(url.encode()).hexdigest()[:10] + '.jpg'
            
            # Определяем категорию по URL
            category = self.categorize_image(url, filename)
            filepath = self.media_dir / category / filename
            
            # Проверяем существование
            if filepath.exists() and not force:
                self.downloaded_files[url] = str(filepath.relative_to(settings.MEDIA_ROOT))
                return False
            
            # Скачиваем
            response = requests.get(url, timeout=15, stream=True)
            response.raise_for_status()
            
            # Сохраняем
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Сохраняем маппинг
            self.downloaded_files[url] = str(filepath.relative_to(settings.MEDIA_ROOT))
            
            return True
            
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'⚠️  Ошибка загрузки {url}: {e}'))
            return False
    
    def categorize_image(self, url, filename):
        """Определяет категорию изображения по URL или имени"""
        url_lower = url.lower()
        filename_lower = filename.lower()
        
        if any(x in url_lower or x in filename_lower for x in ['portfolio', 'work', 'result']):
            return 'portfolio'
        elif any(x in url_lower or x in filename_lower for x in ['team', 'master', 'specialist']):
            return 'team'
        elif any(x in url_lower or x in filename_lower for x in ['brand', 'logo', 'partner']):
            return 'brands'
        elif any(x in url_lower or x in filename_lower for x in ['icon', 'ico']):
            return 'icons'
        elif any(x in url_lower or x in filename_lower for x in ['background', 'bg', 'hero']):
            return 'backgrounds'
        else:
            return 'images'
    
    def create_mapping_file(self):
        """Создает файл маппинга старых URL на новые пути"""
        mapping_file = self.media_dir / 'url_mapping.txt'
        
        with open(mapping_file, 'w', encoding='utf-8') as f:
            f.write('# Маппинг URL изображений\n')
            f.write('# Формат: СТАРЫЙ_URL -> НОВЫЙ_ПУТЬ\n\n')
            
            for old_url, new_path in sorted(self.downloaded_files.items()):
                f.write(f'{old_url} -> {new_path}\n')
        
        self.stdout.write(self.style.SUCCESS(f'✅ Создан файл маппинга: {mapping_file}'))

