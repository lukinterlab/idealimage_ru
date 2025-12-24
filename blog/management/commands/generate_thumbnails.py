"""
Команда для генерации thumbnail изображений для всех постов
Создает thumbnail (600x400 WebP) для постов, у которых их еще нет
"""
import os
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files import File
from django.db import connection
from blog.models import Post
from utilits.image_optimizer import ImageOptimizer

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Создает thumbnail изображения (600x400 WebP) для всех постов, у которых их еще нет'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Только показать что будет сделано, без реальных изменений',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Ограничить количество обрабатываемых постов',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Пересоздать thumbnail даже если они уже существуют',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']
        force = options['force']

        self.stdout.write(self.style.SUCCESS('🖼️ Начинаем генерацию thumbnail для постов...'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️ РЕЖИМ ПРОСМОТРА: изменения не будут сохранены'))
        
        # Находим посты с изображениями, но без thumbnail
        posts_query = Post.objects.filter(
            kartinka__isnull=False
        ).exclude(
            kartinka=''
        )
        
        if not force:
            posts_query = posts_query.filter(thumbnail__isnull=True)
        
        # Пропускаем видео файлы
        video_extensions = ['.mp4', '.webm', '.mov', '.avi']
        posts = []
        for post in posts_query:
            if post.kartinka.name:
                file_ext = os.path.splitext(post.kartinka.name.lower())[1]
                if file_ext not in video_extensions:
                    posts.append(post)
        
        if limit:
            posts = posts[:limit]
        
        total = len(posts)
        
        if total == 0:
            self.stdout.write(self.style.WARNING('📭 Посты для обработки не найдены'))
            if not force:
                self.stdout.write('💡 Все посты уже имеют thumbnail. Используйте --force для пересоздания')
            return
        
        self.stdout.write(f'📊 Найдено постов для обработки: {total}')
        
        # Статистика
        stats = {
            'processed': 0,
            'created': 0,
            'skipped': 0,
            'errors': 0,
        }
        
        # Обрабатываем каждый пост
        for i, post in enumerate(posts, 1):
            try:
                # Переподключение к БД для избежания timeout
                connection.close()
                connection.connect()
                
                self.stdout.write(f'\n[{i}/{total}] Обработка: {post.title[:50]}...')
                
                if not post.kartinka:
                    self.stdout.write(self.style.WARNING('  ⏭️ Нет изображения'))
                    stats['skipped'] += 1
                    continue
                
                # Проверяем что это изображение, а не видео
                video_extensions = ['.mp4', '.webm', '.mov', '.avi']
                if any(post.kartinka.name.lower().endswith(ext) for ext in video_extensions):
                    self.stdout.write(self.style.WARNING('  ⏭️ Это видео, пропускаем'))
                    stats['skipped'] += 1
                    continue
                
                # Проверяем наличие файла
                image_path = post.kartinka.path if hasattr(post.kartinka, 'path') else None
                if not image_path or not os.path.exists(image_path):
                    self.stdout.write(self.style.WARNING(f'  ⚠️ Файл не найден: {post.kartinka.name}'))
                    stats['skipped'] += 1
                    continue
                
                # Проверяем, есть ли уже thumbnail
                if post.thumbnail and not force:
                    self.stdout.write(self.style.WARNING('  ⏭️ Thumbnail уже существует'))
                    stats['skipped'] += 1
                    continue
                
                if dry_run:
                    self.stdout.write(self.style.WARNING('  ⚠️ [DRY-RUN] Пропущено'))
                    stats['skipped'] += 1
                    continue
                
                # Создаем thumbnail (600x400 WebP)
                self.stdout.write('  🖼️ Создание thumbnail...')
                thumbnail_file, extension = ImageOptimizer.optimize_image(
                    image_path,
                    max_size='thumbnail',
                    format='webp'
                )
                
                if thumbnail_file:
                    # Сохраняем thumbnail
                    thumbnail_filename = f'thumb_{post.slug or post.pk}.webp'
                    post.thumbnail.save(
                        thumbnail_filename,
                        File(thumbnail_file),
                        save=False
                    )
                    post.save(update_fields=['thumbnail'])
                    
                    stats['created'] += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✅ Thumbnail создан: {thumbnail_filename}')
                    )
                else:
                    self.stdout.write(self.style.ERROR('  ❌ Не удалось создать thumbnail'))
                    stats['errors'] += 1
                
                stats['processed'] += 1
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ❌ Ошибка обработки: {e}'))
                logger.error(f'Ошибка создания thumbnail для поста {post.id}: {e}', exc_info=True)
                stats['errors'] += 1
        
        # Итоговая статистика
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('✅ Генерация thumbnail завершена!'))
        self.stdout.write(f'📊 Всего постов: {total}')
        self.stdout.write(self.style.SUCCESS(f'✅ Обработано: {stats["processed"]}'))
        self.stdout.write(self.style.SUCCESS(f'🖼️ Thumbnail создано: {stats["created"]}'))
        self.stdout.write(f'⏭️ Пропущено: {stats["skipped"]}')
        
        if stats['errors'] > 0:
            self.stdout.write(self.style.ERROR(f'❌ Ошибок: {stats["errors"]}'))
        
        self.stdout.write('=' * 60)
        
        if dry_run:
            self.stdout.write('\n💡 Для реальной генерации запустите без --dry-run')

