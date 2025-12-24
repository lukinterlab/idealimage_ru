"""
Команда для массовой конверсии изображений в WebP формат
Использование: python manage.py convert_images_to_webp [--dry-run] [--quality 85]
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from PIL import Image
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Конвертирует все изображения в WebP формат для оптимизации'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Только показать что будет сделано, без реальной конверсии',
        )
        parser.add_argument(
            '--quality',
            type=int,
            default=85,
            help='Качество WebP (1-100, по умолчанию 85)',
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Пропускать файлы, для которых уже есть WebP версия',
        )
        parser.add_argument(
            '--path',
            type=str,
            default='media/images',
            help='Путь к папке с изображениями (по умолчанию media/images)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        quality = options['quality']
        skip_existing = options['skip_existing']
        target_path = options['path']
        
        media_dir = Path(settings.BASE_DIR) / target_path
        
        if not media_dir.exists():
            self.stdout.write(self.style.ERROR(f'Папка {media_dir} не найдена!'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'\n🔍 Сканирование папки: {media_dir}'))
        
        # Поддерживаемые форматы
        supported_formats = ('.jpg', '.jpeg', '.png', '.gif')
        
        # Находим все изображения
        image_files = []
        for ext in supported_formats:
            image_files.extend(media_dir.rglob(f'*{ext}'))
            image_files.extend(media_dir.rglob(f'*{ext.upper()}'))
        
        total_files = len(image_files)
        self.stdout.write(self.style.WARNING(f'📊 Найдено изображений: {total_files}'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  РЕЖИМ ПРОСМОТРА (dry-run) - изменения не будут применены'))
        
        converted_count = 0
        skipped_count = 0
        error_count = 0
        total_saved_bytes = 0
        
        for i, image_path in enumerate(image_files, 1):
            webp_path = image_path.with_suffix('.webp')
            
            # Пропускаем если WebP уже существует
            if skip_existing and webp_path.exists():
                skipped_count += 1
                if i % 100 == 0:
                    self.stdout.write(f'⏩ Прогресс: {i}/{total_files} (пропущено: {skipped_count})')
                continue
            
            try:
                # Открываем изображение
                with Image.open(image_path) as img:
                    # Конвертируем в RGB если нужно
                    if img.mode in ('RGBA', 'LA', 'P'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        if img.mode in ('RGBA', 'LA'):
                            background.paste(img, mask=img.split()[-1])
                        img = background
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Получаем размер оригинала
                    original_size = image_path.stat().st_size
                    
                    if not dry_run:
                        # Сохраняем в WebP
                        img.save(
                            webp_path,
                            'WEBP',
                            quality=quality,
                            method=6  # Лучшее сжатие
                        )
                        
                        webp_size = webp_path.stat().st_size
                        saved_bytes = original_size - webp_size
                        total_saved_bytes += saved_bytes
                        
                        savings_percent = (saved_bytes / original_size) * 100 if original_size > 0 else 0
                        
                        converted_count += 1
                        
                        if converted_count % 10 == 0:
                            total_saved_mb = total_saved_bytes / (1024 * 1024)
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'✅ {converted_count}/{total_files} | '
                                    f'Сохранено: {total_saved_mb:.1f} MB | '
                                    f'Последний: {image_path.name} (-{savings_percent:.1f}%)'
                                )
                            )
                    else:
                        converted_count += 1
                        if converted_count % 50 == 0:
                            self.stdout.write(f'📝 Будет конвертировано: {converted_count}/{total_files}')
                
            except Exception as e:
                error_count += 1
                if error_count <= 10:  # Показываем первые 10 ошибок
                    self.stdout.write(
                        self.style.ERROR(f'❌ Ошибка обработки {image_path.name}: {e}')
                    )
        
        # Итоговая статистика
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('📊 ИТОГОВАЯ СТАТИСТИКА:'))
        self.stdout.write('='*70)
        self.stdout.write(f'📁 Всего файлов найдено: {total_files}')
        self.stdout.write(f'✅ Конвертировано: {converted_count}')
        self.stdout.write(f'⏩ Пропущено: {skipped_count}')
        self.stdout.write(f'❌ Ошибок: {error_count}')
        
        if not dry_run and total_saved_bytes > 0:
            total_saved_mb = total_saved_bytes / (1024 * 1024)
            avg_savings = (total_saved_bytes / converted_count / 1024) if converted_count > 0 else 0
            self.stdout.write(f'💾 Сэкономлено места: {total_saved_mb:.2f} MB')
            self.stdout.write(f'📉 В среднем на файл: {avg_savings:.1f} KB')
        
        self.stdout.write('='*70)
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    '\n💡 Чтобы запустить реальную конверсию, выполните команду без --dry-run:\n'
                    f'   python manage.py convert_images_to_webp --quality {quality}'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    '\n✨ Конверсия завершена! Теперь обновите шаблоны для использования WebP.'
                )
            )

