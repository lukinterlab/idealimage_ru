"""
Management команда для конвертации существующих изображений в WebP формат
С автоматическим переименованием по контексту (статья/категория)
"""
import os
import logging
from pathlib import Path
from PIL import Image
from django.core.management.base import BaseCommand
from django.conf import settings
from blog.models import Post, Category
from Visitor.models import Profile
from utilits.utils import generate_image_filename

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Конвертирует все изображения (JPG, PNG, JPEG) в WebP формат с переименованием'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--delete-originals',
            action='store_true',
            help='Удалить оригинальные файлы после конвертации',
        )
        parser.add_argument(
            '--quality',
            type=int,
            default=85,
            help='Качество WebP (0-100, по умолчанию 85)',
        )
        parser.add_argument(
            '--max-width',
            type=int,
            default=1920,
            help='Максимальная ширина изображения (по умолчанию 1920px)',
        )
        parser.add_argument(
            '--max-height',
            type=int,
            default=1080,
            help='Максимальная высота изображения (по умолчанию 1080px)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Пробный запуск без реального изменения файлов',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Начало конвертации изображений в WebP'))
        
        delete_originals = options['delete_originals']
        quality = options['quality']
        max_width = options['max_width']
        max_height = options['max_height']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️ ПРОБНЫЙ ЗАПУСК - файлы не будут изменены'))
        
        if delete_originals and not dry_run:
            self.stdout.write(self.style.WARNING('⚠️ Оригинальные файлы будут УДАЛЕНЫ!'))
        
        # Статистика
        stats = {
            'total_found': 0,
            'converted': 0,
            'skipped': 0,
            'errors': 0,
            'space_saved': 0
        }
        
        # 1. Конвертация изображений постов
        self.stdout.write('\n📝 Обработка изображений статей...')
        self._convert_post_images(stats, delete_originals, quality, max_width, max_height, dry_run)
        
        # 2. Конвертация изображений категорий
        self.stdout.write('\n📂 Обработка изображений категорий...')
        self._convert_category_images(stats, delete_originals, quality, max_width, max_height, dry_run)
        
        # 3. Конвертация изображений профилей
        self.stdout.write('\n👤 Обработка изображений профилей...')
        self._convert_profile_images(stats, delete_originals, quality, max_width, max_height, dry_run)
        
        # Итоговая статистика
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('✅ Конвертация завершена!'))
        self.stdout.write(f"📊 Найдено изображений: {stats['total_found']}")
        self.stdout.write(f"✓ Конвертировано: {stats['converted']}")
        self.stdout.write(f"⊘ Пропущено: {stats['skipped']}")
        self.stdout.write(f"❌ Ошибок: {stats['errors']}")
        if stats['space_saved'] > 0:
            space_mb = stats['space_saved'] / (1024 * 1024)
            self.stdout.write(f"💾 Экономия места: {space_mb:.2f} MB")
        self.stdout.write('='*60)
    
    def _convert_post_images(self, stats, delete_originals, quality, max_width, max_height, dry_run):
        """Конвертирует изображения статей"""
        posts = Post.objects.exclude(kartinka='')
        self.stdout.write(f"   Найдено статей с изображениями: {posts.count()}")
        
        for post in posts:
            if not post.kartinka:
                continue
            
            stats['total_found'] += 1
            
            try:
                # Путь к оригинальному файлу
                original_path = post.kartinka.path
                
                # Пропускаем если файл не существует
                if not os.path.exists(original_path):
                    self.stdout.write(f"   ⚠️ Файл не найден: {original_path}")
                    stats['skipped'] += 1
                    continue
                
                # Пропускаем если уже WebP
                if original_path.lower().endswith('.webp'):
                    stats['skipped'] += 1
                    continue
                
                # Генерируем новое имя файла на основе заголовка статьи
                new_filename = generate_image_filename(post.title, extension='webp')
                
                # Определяем путь для нового файла (в той же папке)
                original_dir = os.path.dirname(original_path)
                new_path = os.path.join(original_dir, new_filename)
                
                if not dry_run:
                    # Конвертируем в WebP
                    original_size = os.path.getsize(original_path)
                    self._convert_image_to_webp(
                        original_path, 
                        new_path, 
                        quality, 
                        max_width, 
                        max_height
                    )
                    new_size = os.path.getsize(new_path)
                    stats['space_saved'] += (original_size - new_size)
                    
                    # Обновляем путь в БД
                    relative_path = os.path.relpath(new_path, settings.MEDIA_ROOT)
                    post.kartinka = relative_path
                    post.save(update_fields=['kartinka'])
                    
                    # Удаляем оригинал если нужно
                    if delete_originals:
                        os.remove(original_path)
                
                stats['converted'] += 1
                self.stdout.write(f"   ✓ {post.title[:50]} → {new_filename}")
                
            except Exception as e:
                stats['errors'] += 1
                self.stdout.write(self.style.ERROR(f"   ❌ Ошибка: {post.title[:50]} - {str(e)}"))
                logger.error(f"Ошибка конвертации изображения поста {post.id}: {e}")
    
    def _convert_category_images(self, stats, delete_originals, quality, max_width, max_height, dry_run):
        """Конвертирует изображения категорий"""
        categories = Category.objects.exclude(kartinka='')
        self.stdout.write(f"   Найдено категорий с изображениями: {categories.count()}")
        
        for category in categories:
            if not category.kartinka:
                continue
            
            stats['total_found'] += 1
            
            try:
                original_path = category.kartinka.path
                
                if not os.path.exists(original_path):
                    stats['skipped'] += 1
                    continue
                
                if original_path.lower().endswith('.webp'):
                    stats['skipped'] += 1
                    continue
                
                # Генерируем имя на основе названия категории
                new_filename = generate_image_filename(category.title, extension='webp')
                original_dir = os.path.dirname(original_path)
                new_path = os.path.join(original_dir, new_filename)
                
                if not dry_run:
                    original_size = os.path.getsize(original_path)
                    self._convert_image_to_webp(
                        original_path, 
                        new_path, 
                        quality, 
                        max_width, 
                        max_height
                    )
                    new_size = os.path.getsize(new_path)
                    stats['space_saved'] += (original_size - new_size)
                    
                    relative_path = os.path.relpath(new_path, settings.MEDIA_ROOT)
                    category.kartinka = relative_path
                    category.save(update_fields=['kartinka'])
                    
                    if delete_originals:
                        os.remove(original_path)
                
                stats['converted'] += 1
                self.stdout.write(f"   ✓ {category.title} → {new_filename}")
                
            except Exception as e:
                stats['errors'] += 1
                self.stdout.write(self.style.ERROR(f"   ❌ Ошибка: {category.title} - {str(e)}"))
    
    def _convert_profile_images(self, stats, delete_originals, quality, max_width, max_height, dry_run):
        """Конвертирует аватары профилей"""
        profiles = Profile.objects.exclude(avatar='')
        self.stdout.write(f"   Найдено профилей с аватарами: {profiles.count()}")
        
        for profile in profiles:
            if not profile.avatar:
                continue
            
            stats['total_found'] += 1
            
            try:
                original_path = profile.avatar.path
                
                if not os.path.exists(original_path):
                    stats['skipped'] += 1
                    continue
                
                if original_path.lower().endswith('.webp'):
                    stats['skipped'] += 1
                    continue
                
                # Генерируем имя на основе username
                username = profile.user.username if profile.user else 'user'
                new_filename = generate_image_filename(username, extension='webp')
                original_dir = os.path.dirname(original_path)
                new_path = os.path.join(original_dir, new_filename)
                
                if not dry_run:
                    original_size = os.path.getsize(original_path)
                    # Для аватаров используем меньший размер
                    self._convert_image_to_webp(
                        original_path, 
                        new_path, 
                        quality, 
                        500,  # max width для аватара
                        500   # max height для аватара
                    )
                    new_size = os.path.getsize(new_path)
                    stats['space_saved'] += (original_size - new_size)
                    
                    relative_path = os.path.relpath(new_path, settings.MEDIA_ROOT)
                    profile.avatar = relative_path
                    profile.save(update_fields=['avatar'])
                    
                    if delete_originals:
                        os.remove(original_path)
                
                stats['converted'] += 1
                self.stdout.write(f"   ✓ {username} → {new_filename}")
                
            except Exception as e:
                stats['errors'] += 1
                self.stdout.write(self.style.ERROR(f"   ❌ Ошибка: {profile.user.username if profile.user else 'N/A'} - {str(e)}"))
    
    def _convert_image_to_webp(self, input_path, output_path, quality, max_width, max_height):
        """
        Конвертирует изображение в WebP с оптимизацией размера
        
        Args:
            input_path: Путь к исходному файлу
            output_path: Путь для сохранения WebP
            quality: Качество (0-100)
            max_width: Максимальная ширина
            max_height: Максимальная высота
        """
        with Image.open(input_path) as img:
            # Конвертируем в RGB если нужно (WebP не поддерживает некоторые режимы)
            if img.mode in ('RGBA', 'LA', 'P'):
                # Создаем белый фон для прозрачных изображений
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Изменяем размер если нужно
            if img.width > max_width or img.height > max_height:
                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            # Сохраняем как WebP
            img.save(output_path, 'WEBP', quality=quality, method=6)

