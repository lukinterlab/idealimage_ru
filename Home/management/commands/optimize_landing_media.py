"""
Management команда для оптимизации всех медиафайлов лендинга
"""
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from Home.models import LandingSection
from Home.image_optimizer import ImageOptimizer
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Optimizacija vseh mediafajlov lendinga dlja bystroj zagruzki'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Perezapisat uzhe optimizirovannye fajly'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('[OPTIMIZER] Optimizacija mediafajlov lendinga'))
        self.stdout.write('=' * 70)
        
        force = options.get('force')
        optimized_count = 0
        skipped_count = 0
        error_count = 0
        
        # Оптимизируем все секции с изображениями
        sections = LandingSection.objects.filter(
            media_type='image',
            background_image__isnull=False
        ).exclude(background_image='')
        
        total = sections.count()
        self.stdout.write(f'\n[INFO] Najdeno sekcij s izobrazhenijami: {total}')
        
        for idx, section in enumerate(sections, 1):
            self.stdout.write(f'\n[{idx}/{total}] Sekcija: {section.get_section_display()}')
            
            try:
                # Путь к файлу
                image_path = section.background_image.path
                
                # Проверяем размер файла
                file_size = os.path.getsize(image_path)
                file_size_mb = file_size / (1024 * 1024)
                
                self.stdout.write(f'    Tekushhij razmer: {file_size_mb:.2f} MB')
                
                # Если файл уже маленький и не force, пропускаем
                if file_size < 300 * 1024 and not force:  # < 300 KB
                    self.stdout.write(self.style.WARNING('    [SKIP] Uzhe optimizirovan'))
                    skipped_count += 1
                    continue
                
                # Оптимизируем
                section_type = 'hero' if section.section == 'hero' else 'section'
                optimized, extension = ImageOptimizer.optimize_image(
                    image_path,
                    max_size=section_type,
                    format='webp'
                )
                
                if optimized:
                    # Генерируем имя
                    original_name = os.path.splitext(os.path.basename(image_path))[0]
                    new_name = f"{original_name}_opt.{extension}"
                    
                    # Сохраняем оптимизированный файл
                    section.background_image.save(new_name, optimized, save=True)
                    
                    # Проверяем новый размер
                    new_size = os.path.getsize(section.background_image.path)
                    new_size_mb = new_size / (1024 * 1024)
                    savings = ((file_size - new_size) / file_size) * 100
                    
                    self.stdout.write(self.style.SUCCESS(
                        f'    [OK] Optimizirovano: {new_size_mb:.2f} MB (jekonomija: {savings:.1f}%)'
                    ))
                    optimized_count += 1
                else:
                    self.stdout.write(self.style.ERROR('    [ERROR] Ne udalos optimizirovat'))
                    error_count += 1
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'    [ERROR] {e}'))
                error_count += 1
                logger.error(f'Error optimizing section {section.section}: {e}')
        
        # Итоги
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS(f'[GOTOVO]'))
        self.stdout.write(f'  Optimizirovano: {optimized_count}')
        self.stdout.write(f'  Propushheno:    {skipped_count}')
        self.stdout.write(f'  Oshibok:        {error_count}')
        
        if optimized_count > 0:
            self.stdout.write(self.style.SUCCESS('\n[TIP] Ochistite kesh: cache.clear()'))


