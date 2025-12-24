"""
Команда для оптимизации всех существующих видео на сайте
Использование: python manage.py optimize_existing_videos [--force] [--limit N]
"""
from django.core.management.base import BaseCommand
from blog.models import Post
from blog.utils_video_processing import (
    optimize_video, 
    create_video_poster, 
    get_video_info,
    check_ffmpeg_available
)
from django.core.files import File
import os
from pathlib import Path


class Command(BaseCommand):
    help = 'Оптимизирует все существующие видео на сайте: создает poster, оптимизирует размер'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Принудительно переобработать уже оптимизированные видео',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Ограничить количество обрабатываемых видео',
        )
        parser.add_argument(
            '--skip-optimization',
            action='store_true',
            help='Пропустить оптимизацию, только создать poster',
        )
        parser.add_argument(
            '--skip-poster',
            action='store_true',
            help='Пропустить создание poster, только оптимизировать',
        )

    def handle(self, *args, **options):
        force = options['force']
        limit = options.get('limit')
        skip_optimization = options.get('skip_optimization', False)
        skip_poster = options.get('skip_poster', False)
        
        # Проверяем FFmpeg
        if not check_ffmpeg_available():
            self.stdout.write(
                self.style.WARNING('⚠️ FFmpeg не установлен. Установите FFmpeg для работы команды.')
            )
            self.stdout.write('   Ubuntu/Debian: sudo apt-get install ffmpeg')
            self.stdout.write('   CentOS/RHEL: sudo yum install ffmpeg')
            self.stdout.write('   Windows: https://ffmpeg.org/download.html')
            return
        
        self.stdout.write(self.style.SUCCESS('🚀 Начало оптимизации видео'))
        
        # Получаем все посты с видео
        video_extensions = ['.mp4', '.webm', '.mov', '.avi']
        posts_query = Post.objects.filter(
            kartinka__isnull=False
        ).exclude(kartinka='')
        
        if not force:
            # Пропускаем уже оптимизированные
            posts_query = posts_query.filter(video_optimized=False)
        
        # Фильтруем только видео файлы
        posts_with_video = []
        for post in posts_query:
            if post.kartinka and post.kartinka.name:
                if any(post.kartinka.name.lower().endswith(ext) for ext in video_extensions):
                    posts_with_video.append(post)
        
        if limit:
            posts_with_video = posts_with_video[:limit]
        
        total = len(posts_with_video)
        self.stdout.write(f'📊 Найдено видео для обработки: {total}')
        
        if total == 0:
            self.stdout.write(self.style.WARNING('Нет видео для обработки'))
            return
        
        # Статистика
        stats = {
            'processed': 0,
            'posters_created': 0,
            'videos_optimized': 0,
            'errors': 0,
            'skipped': 0,
        }
        
        for i, post in enumerate(posts_with_video, 1):
            self.stdout.write(f'\n[{i}/{total}] Обработка: {post.title}')
            
            try:
                # Получаем путь к видео
                if not hasattr(post.kartinka, 'path') or not os.path.exists(post.kartinka.path):
                    self.stdout.write(self.style.WARNING(f'  ⚠️ Файл не найден: {post.kartinka.name}'))
                    stats['skipped'] += 1
                    continue
                
                video_path = post.kartinka.path
                
                # Получаем информацию о видео
                video_info = get_video_info(video_path)
                if video_info:
                    post.video_duration = video_info['duration']
                    self.stdout.write(f'  📹 Длительность: {video_info["duration"]:.1f} сек, Размер: {video_info["size_mb"]:.1f} MB')
                
                # Создаем poster
                if not skip_poster:
                    if not post.video_poster or force:
                        self.stdout.write('  🖼️ Создание poster...')
                        poster_path = create_video_poster(video_path)
                        if poster_path and os.path.exists(poster_path):
                            with open(poster_path, 'rb') as f:
                                post.video_poster.save(
                                    f'poster_{post.slug or post.pk}.webp',
                                    File(f),
                                    save=False
                                )
                            stats['posters_created'] += 1
                            self.stdout.write(self.style.SUCCESS('  ✅ Poster создан'))
                        else:
                            self.stdout.write(self.style.WARNING('  ⚠️ Не удалось создать poster'))
                    else:
                        self.stdout.write('  ⏭️ Poster уже существует')
                
                # Оптимизируем видео
                if not skip_optimization:
                    if video_info and video_info.get('size_mb', 0) > 10:
                        if not post.video_optimized or force:
                            self.stdout.write('  ⚙️ Оптимизация видео...')
                            optimized_path = optimize_video(video_path)
                            if optimized_path and os.path.exists(optimized_path):
                                # Заменяем оригинальное видео
                                original_size = os.path.getsize(video_path)
                                optimized_size = os.path.getsize(optimized_path)
                                
                                if optimized_size < original_size:
                                    with open(optimized_path, 'rb') as f:
                                        post.kartinka.save(
                                            post.kartinka.name,
                                            File(f),
                                            save=False
                                        )
                                    os.remove(optimized_path)
                                    stats['videos_optimized'] += 1
                                    saved_mb = (original_size - optimized_size) / (1024 * 1024)
                                    self.stdout.write(
                                        self.style.SUCCESS(
                                            f'  ✅ Видео оптимизировано (сэкономлено {saved_mb:.1f} MB)'
                                        )
                                    )
                                else:
                                    os.remove(optimized_path)
                                    self.stdout.write(self.style.WARNING('  ⚠️ Оптимизированное видео больше оригинала'))
                            else:
                                self.stdout.write(self.style.WARNING('  ⚠️ Не удалось оптимизировать видео'))
                        else:
                            self.stdout.write('  ⏭️ Видео уже оптимизировано')
                    else:
                        self.stdout.write('  ⏭️ Видео меньше 10MB, оптимизация не требуется')
                
                        # Обновляем статус (с переподключением к БД)
                        from django.db import connection
                        connection.close()  # Закрываем старое соединение
                        post = Post.objects.get(pk=post.pk)  # Переподключаемся
                        post.video_optimized = True
                        post.video_processing_status = 'completed'
                        post.save(update_fields=[
                            'video_optimized', 
                            'video_processing_status', 
                            'video_duration',
                            'video_poster',
                            'kartinka'
                        ])
                
                stats['processed'] += 1
                
            except Exception as e:
                stats['errors'] += 1
                self.stdout.write(
                    self.style.ERROR(f'  ❌ Ошибка обработки: {e}')
                )
                # Обновляем статус на ошибку
                try:
                    post.video_processing_status = 'failed'
                    post.save(update_fields=['video_processing_status'])
                except:
                    pass
        
        # Итоговая статистика
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('✅ Обработка завершена'))
        self.stdout.write(f'📊 Обработано: {stats["processed"]}')
        self.stdout.write(f'🖼️ Poster создано: {stats["posters_created"]}')
        self.stdout.write(f'⚙️ Видео оптимизировано: {stats["videos_optimized"]}')
        self.stdout.write(f'⏭️ Пропущено: {stats["skipped"]}')
        if stats['errors'] > 0:
            self.stdout.write(self.style.ERROR(f'❌ Ошибок: {stats["errors"]}'))

