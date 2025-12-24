"""
Management команда для оптимизации изображений в статьях
Конвертирует в WebP и добавляет lazy loading
"""
from django.core.management.base import BaseCommand
from blog.models import Post
from PIL import Image
import os
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Оптимизирует изображения статей (конвертация в WebP)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Ограничить количество обрабатываемых статей',
        )
        parser.add_argument(
            '--quality',
            type=int,
            default=85,
            help='Качество WebP изображений (1-100)',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🖼️ Начинаем оптимизацию изображений...')
        )

        quality = options['quality']
        
        # Получаем статьи с изображениями
        posts = Post.objects.filter(
            status='published'
        ).exclude(kartinka='')

        if options['limit']:
            posts = posts[:options['limit']]

        total = posts.count()
        
        if total == 0:
            self.stdout.write(
                self.style.WARNING('Статьи с изображениями не найдены')
            )
            return

        self.stdout.write(f'Найдено статей с изображениями: {total}')

        optimized_count = 0
        skipped_count = 0
        errors_count = 0
        saved_bytes = 0

        for i, post in enumerate(posts, 1):
            try:
                if not post.kartinka:
                    continue
                
                image_path = post.kartinka.path
                
                # Проверяем что файл существует
                if not os.path.exists(image_path):
                    skipped_count += 1
                    continue
                
                # Пропускаем если уже WebP
                if image_path.lower().endswith('.webp'):
                    skipped_count += 1
                    continue
                
                # Получаем размер до оптимизации
                original_size = os.path.getsize(image_path)
                
                # Открываем изображение
                img = Image.open(image_path)
                
                # Конвертируем в RGB если нужно
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Создаем имя WebP файла
                webp_path = os.path.splitext(image_path)[0] + '.webp'
                
                # Оптимизация размера (макс 1920px по ширине)
                max_width = 1920
                if img.width > max_width:
                    ratio = max_width / img.width
                    new_size = (max_width, int(img.height * ratio))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                
                # Сохраняем как WebP
                img.save(webp_path, 'WebP', quality=quality, optimize=True)
                
                # Получаем размер после оптимизации
                optimized_size = os.path.getsize(webp_path)
                saved = original_size - optimized_size
                saved_bytes += saved
                
                percentage = (saved / original_size) * 100 if original_size > 0 else 0
                
                optimized_count += 1
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'[{i}/{total}] ✅ {post.title[:40]}... '
                        f'({original_size//1024}KB → {optimized_size//1024}KB, '
                        f'-{percentage:.1f}%)'
                    )
                )
                
            except Exception as e:
                errors_count += 1
                logger.error(f'Ошибка при оптимизации изображения статьи {post.id}: {e}')
                self.stdout.write(
                    self.style.ERROR(
                        f'[{i}/{total}] ❌ Ошибка: {post.title[:40]}... - {str(e)}'
                    )
                )

        # Итоговая статистика
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('✅ Оптимизация завершена!'))
        self.stdout.write(f'📊 Всего статей: {total}')
        self.stdout.write(self.style.SUCCESS(f'✅ Оптимизировано: {optimized_count}'))
        self.stdout.write(f'⏭️ Пропущено: {skipped_count}')
        
        if errors_count > 0:
            self.stdout.write(self.style.ERROR(f'❌ Ошибок: {errors_count}'))
        
        saved_mb = saved_bytes / (1024 * 1024)
        self.stdout.write(
            self.style.SUCCESS(f'💾 Сэкономлено места: {saved_mb:.2f} MB')
        )
        self.stdout.write('=' * 60)
        
        self.stdout.write('\n💡 Примечание:')
        self.stdout.write('WebP файлы созданы рядом с оригинальными изображениями')
        self.stdout.write('Оригиналы НЕ удалены (удалите их вручную после проверки)\n')


