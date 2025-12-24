"""
Команда для оптимизации всех изображений в папке media/images/
- Конвертирует в WebP
- Изменяет размеры
- Удаляет оригиналы
- Обновляет Post.kartinka
- Отправляет в IndexNow для индексации
"""
import os
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files import File
from django.db import connection
from blog.models import Post
from utilits.image_optimizer import ImageOptimizer
from Asistent.seo_advanced import AdvancedSEOOptimizer

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Оптимизирует все изображения в media/images/: конвертация в WebP, изменение размеров, удаление оригиналов, отправка в IndexNow'

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
            help='Ограничить количество обрабатываемых файлов',
        )
        parser.add_argument(
            '--skip-delete',
            action='store_true',
            help='Не удалять оригинальные файлы',
        )
        parser.add_argument(
            '--skip-indexnow',
            action='store_true',
            help='Не отправлять в IndexNow',
        )
        parser.add_argument(
            '--min-size',
            type=int,
            default=100,
            help='Минимальный размер файла для обработки (KB, по умолчанию 100KB)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']
        skip_delete = options['skip_delete']
        skip_indexnow = options['skip_indexnow']
        min_size_kb = options['min_size']

        self.stdout.write(self.style.SUCCESS('🖼️ Начинаем оптимизацию всех изображений в media/images/'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️ РЕЖИМ ПРОСМОТРА: изменения не будут сохранены'))
        
        # Путь к папке с изображениями
        media_images_path = os.path.join(settings.MEDIA_ROOT, 'images')
        
        if not os.path.exists(media_images_path):
            self.stdout.write(self.style.ERROR(f'❌ Папка не найдена: {media_images_path}'))
            return
        
        # Расширения изображений
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
        video_extensions = ['.mp4', '.webm', '.mov', '.avi']
        
        # Собираем все файлы изображений
        image_files = []
        stats_scan = {
            'total_files': 0,
            'skipped_video': 0,
            'skipped_webp': 0,
            'skipped_not_image': 0,
            'skipped_too_small': 0,
            'found': 0
        }
        
        for root, dirs, files in os.walk(media_images_path):
            for file in files:
                stats_scan['total_files'] += 1
                file_path = os.path.join(root, file)
                file_ext = os.path.splitext(file.lower())[1]
                
                # Пропускаем видео
                if file_ext in video_extensions:
                    stats_scan['skipped_video'] += 1
                    continue
                
                # Пропускаем уже WebP (если не переоптимизируем)
                if file_ext == '.webp':
                    stats_scan['skipped_webp'] += 1
                    continue
                
                # Пропускаем если не изображение
                if file_ext not in image_extensions:
                    stats_scan['skipped_not_image'] += 1
                    continue
                
                # Проверяем минимальный размер
                try:
                    file_size_kb = os.path.getsize(file_path) / 1024
                    if file_size_kb < min_size_kb:
                        stats_scan['skipped_too_small'] += 1
                        continue
                except OSError:
                    # Файл не доступен или удален
                    continue
                
                image_files.append(file_path)
                stats_scan['found'] += 1
        
        # Показываем статистику сканирования
        self.stdout.write('\n📊 Статистика сканирования:')
        self.stdout.write(f'  📁 Всего файлов в папке: {stats_scan["total_files"]}')
        self.stdout.write(f'  🎥 Пропущено видео: {stats_scan["skipped_video"]}')
        self.stdout.write(f'  🖼️ Пропущено WebP (уже оптимизированы): {stats_scan["skipped_webp"]}')
        self.stdout.write(f'  ❌ Пропущено не-изображений: {stats_scan["skipped_not_image"]}')
        self.stdout.write(f'  📏 Пропущено слишком маленьких (<{min_size_kb}KB): {stats_scan["skipped_too_small"]}')
        self.stdout.write(f'  ✅ Найдено изображений для обработки: {stats_scan["found"]}')
        
        if limit:
            image_files = image_files[:limit]
            if limit < stats_scan['found']:
                self.stdout.write(f'  ⚠️ Ограничено до {limit} файлов (--limit)')
        
        total = len(image_files)
        
        if total == 0:
            self.stdout.write(self.style.WARNING('\n📭 Изображения для оптимизации не найдены'))
            self.stdout.write(f'\n💡 Попробуйте:')
            self.stdout.write(f'   - Уменьшить --min-size (текущее: {min_size_kb}KB)')
            self.stdout.write(f'   - Проверить путь: {media_images_path}')
            return
        
        self.stdout.write(f'\n📊 Будет обработано: {total}')
        
        # Статистика
        stats = {
            'processed': 0,
            'optimized': 0,
            'updated_posts': 0,
            'deleted': 0,
            'skipped': 0,
            'errors': 0,
            'saved_bytes': 0,
        }
        
        # Список URL для отправки в IndexNow
        indexnow_urls = []
        
        # Обрабатываем каждый файл
        for i, image_path in enumerate(image_files, 1):
            try:
                # Переподключение к БД для избежания timeout
                connection.close()
                connection.connect()
                
                self.stdout.write(f'\n[{i}/{total}] Обработка: {os.path.basename(image_path)}')
                
                # Получаем размер оригинала
                original_size = os.path.getsize(image_path)
                original_size_kb = original_size / 1024
                
                self.stdout.write(f'  📏 Размер оригинала: {original_size_kb:.1f} KB')
                
                if dry_run:
                    self.stdout.write(self.style.WARNING('  ⚠️ [DRY-RUN] Пропущено'))
                    stats['skipped'] += 1
                    continue
                
                # Оптимизируем изображение
                # Определяем тип размера на основе размера файла
                if original_size_kb > 500:
                    size_type = 'article'  # Большие изображения - размер статьи
                else:
                    size_type = 'thumbnail'  # Маленькие - thumbnail
                
                optimized_file, extension = ImageOptimizer.optimize_image(
                    image_path,
                    max_size=size_type,
                    format='webp'
                )
                
                if not optimized_file:
                    self.stdout.write(self.style.ERROR('  ❌ Не удалось оптимизировать'))
                    stats['errors'] += 1
                    continue
                
                # Создаем путь для оптимизированного файла
                base_name = os.path.splitext(image_path)[0]
                optimized_path = f"{base_name}.webp"
                
                # Сохраняем оптимизированное изображение
                with open(optimized_path, 'wb') as f:
                    f.write(optimized_file.read())
                
                # Получаем размер оптимизированного файла
                optimized_size = os.path.getsize(optimized_path)
                optimized_size_kb = optimized_size / 1024
                saved = original_size - optimized_size
                saved_percent = (saved / original_size * 100) if original_size > 0 else 0
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✅ Оптимизировано: {original_size_kb:.1f}KB → {optimized_size_kb:.1f}KB '
                        f'(-{saved_percent:.1f}%, сэкономлено {saved/1024:.1f}KB)'
                    )
                )
                
                stats['optimized'] += 1
                stats['saved_bytes'] += saved
                
                # Ищем посты, связанные с этим файлом
                relative_path = os.path.relpath(image_path, settings.MEDIA_ROOT)
                posts = Post.objects.filter(kartinka=relative_path)
                
                if posts.exists():
                    self.stdout.write(f'  🔗 Найдено связанных постов: {posts.count()}')
                    
                    # Обновляем kartinka на оптимизированный файл
                    optimized_relative_path = os.path.relpath(optimized_path, settings.MEDIA_ROOT)
                    
                    for post in posts:
                        try:
                            # Обновляем поле kartinka
                            post.kartinka = optimized_relative_path
                            post.save(update_fields=['kartinka'])
                            
                            # Формируем URL для IndexNow
                            image_url = f"{settings.SITE_URL}{post.kartinka.url}"
                            indexnow_urls.append(image_url)
                            
                            stats['updated_posts'] += 1
                            
                            self.stdout.write(
                                self.style.SUCCESS(f'  ✅ Обновлен пост: {post.title[:50]}...')
                            )
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f'  ❌ Ошибка обновления поста {post.id}: {e}')
                            )
                            stats['errors'] += 1
                else:
                    # Если нет связанных постов, все равно добавляем URL для IndexNow
                    # (на случай если изображение используется где-то еще)
                    optimized_relative_path = os.path.relpath(optimized_path, settings.MEDIA_ROOT)
                    image_url = f"{settings.SITE_URL}/media/{optimized_relative_path}"
                    indexnow_urls.append(image_url)
                
                # Удаляем оригинальный файл
                if not skip_delete:
                    try:
                        os.remove(image_path)
                        stats['deleted'] += 1
                        self.stdout.write(self.style.SUCCESS('  🗑️ Оригинал удален'))
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'  ❌ Ошибка удаления оригинала: {e}')
                        )
                        stats['errors'] += 1
                else:
                    self.stdout.write(self.style.WARNING('  ⏭️ Оригинал сохранен (--skip-delete)'))
                
                stats['processed'] += 1
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ❌ Ошибка обработки: {e}'))
                logger.error(f'Ошибка оптимизации изображения {image_path}: {e}', exc_info=True)
                stats['errors'] += 1
        
        # Отправляем в IndexNow
        if not skip_indexnow and indexnow_urls and not dry_run:
            self.stdout.write('\n' + '=' * 60)
            self.stdout.write('📤 Отправка в IndexNow для индексации...')
            
            try:
                seo_optimizer = AdvancedSEOOptimizer()
                # Отправляем батчами по 100 URL (лимит IndexNow)
                batch_size = 100
                for i in range(0, len(indexnow_urls), batch_size):
                    batch = indexnow_urls[i:i + batch_size]
                    result = seo_optimizer.submit_images_to_search_engines(batch)
                    
                    if result.get('indexnow', {}).get('success'):
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  ✅ IndexNow: отправлено {len(batch)} URL '
                                f'({i+1}-{min(i+batch_size, len(indexnow_urls))} из {len(indexnow_urls)})'
                            )
                        )
                    else:
                        error = result.get('indexnow', {}).get('error', 'unknown')
                        self.stdout.write(
                            self.style.WARNING(
                                f'  ⚠️ IndexNow: не удалось отправить батч '
                                f'({i+1}-{min(i+batch_size, len(indexnow_urls))}): {error}'
                            )
                        )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ❌ Ошибка отправки в IndexNow: {e}')
                )
                logger.error(f'Ошибка отправки в IndexNow: {e}', exc_info=True)
        
        # Итоговая статистика
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('✅ Оптимизация завершена!'))
        self.stdout.write(f'📊 Всего файлов: {total}')
        self.stdout.write(self.style.SUCCESS(f'✅ Обработано: {stats["processed"]}'))
        self.stdout.write(self.style.SUCCESS(f'🖼️ Оптимизировано: {stats["optimized"]}'))
        self.stdout.write(self.style.SUCCESS(f'🔗 Обновлено постов: {stats["updated_posts"]}'))
        
        if not skip_delete:
            self.stdout.write(self.style.SUCCESS(f'🗑️ Удалено оригиналов: {stats["deleted"]}'))
        
        if not skip_indexnow:
            self.stdout.write(self.style.SUCCESS(f'📤 Отправлено в IndexNow: {len(indexnow_urls)} URL'))
        
        self.stdout.write(f'⏭️ Пропущено: {stats["skipped"]}')
        
        if stats['errors'] > 0:
            self.stdout.write(self.style.ERROR(f'❌ Ошибок: {stats["errors"]}'))
        
        saved_mb = stats['saved_bytes'] / (1024 * 1024)
        self.stdout.write(
            self.style.SUCCESS(f'💾 Сэкономлено места: {saved_mb:.2f} MB')
        )
        self.stdout.write('=' * 60)
        
        if dry_run:
            self.stdout.write('\n💡 Для реальной оптимизации запустите без --dry-run')

