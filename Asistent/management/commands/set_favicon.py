"""
Management command для установки favicon сайта
Запуск: python manage.py set_favicon <путь_к_файлу>
"""
from django.core.management.base import BaseCommand
from PIL import Image
import os
import shutil


class Command(BaseCommand):
    help = 'Устанавливает указанный файл как favicon сайта'

    def add_arguments(self, parser):
        parser.add_argument(
            'image_path',
            type=str,
            help='Путь к файлу изображения'
        )

    def handle(self, *args, **options):
        image_path = options['image_path']
        
        self.stdout.write("=" * 60)
        self.stdout.write("УСТАНОВКА FAVICON САЙТА")
        self.stdout.write("=" * 60)
        
        try:
            # Проверяем существование файла
            if not os.path.exists(image_path):
                self.stdout.write(self.style.ERROR(f"[ERROR] Файл не найден: {image_path}"))
                return
            
            self.stdout.write(f"[OK] Файл найден: {image_path}")
            file_size = os.path.getsize(image_path) / 1024  # KB
            self.stdout.write(f"   Размер: {file_size:.2f} KB")
            
            # Открываем изображение
            img = Image.open(image_path)
            self.stdout.write(f"[OK] Изображение открыто: {img.size[0]}x{img.size[1]} px")
            
            # Создаем нужные директории
            favicon_dirs = [
                'static/new/img/favicon/',
                'staticfiles/new/img/favicon/',
                ''  # Корень проекта
            ]
            
            for directory in favicon_dirs:
                if directory:
                    os.makedirs(directory, exist_ok=True)
            
            # Размеры favicon для разных устройств
            sizes = [
                (16, 16, 'favicon-16x16.png'),
                (32, 32, 'favicon-32x32.png'),
                (48, 48, 'favicon-48x48.png'),
                (64, 64, 'favicon-64x64.png'),
                (96, 96, 'favicon-96x96.png'),
                (128, 128, 'favicon-128x128.png'),
                (192, 192, 'favicon-192x192.png'),
                (512, 512, 'favicon-512x512.png'),
            ]
            
            self.stdout.write(f"\n[...] Создание favicon разных размеров...")
            
            created_count = 0
            for width, height, filename in sizes:
                try:
                    # Создаем изображение нужного размера
                    resized = img.resize((width, height), Image.Resampling.LANCZOS)
                    
                    # Сохраняем в static и staticfiles
                    for base_dir in ['static/new/img/favicon/', 'staticfiles/new/img/favicon/']:
                        output_path = os.path.join(base_dir, filename)
                        resized.save(output_path, 'PNG')
                    
                    self.stdout.write(f"   [OK] {filename} ({width}x{height})")
                    created_count += 1
                    
                except Exception as e:
                    self.stdout.write(f"   [WARN] {filename}: {e}")
            
            self.stdout.write(self.style.SUCCESS(f"\n[OK] Создано {created_count} файлов favicon"))
            
            # Создаем favicon.ico (для старых браузеров)
            self.stdout.write(f"\n[...] Создание favicon.ico...")
            
            # ICO файл содержит несколько размеров
            ico_img = img.resize((32, 32), Image.Resampling.LANCZOS)
            
            # Сохраняем в корень и static
            ico_paths = [
                'favicon.ico',
                'static/favicon.ico',
                'staticfiles/favicon.ico'
            ]
            
            for ico_path in ico_paths:
                try:
                    ico_img.save(ico_path, format='ICO')
                    self.stdout.write(f"   [OK] {ico_path}")
                except Exception as e:
                    self.stdout.write(f"   [WARN] {ico_path}: {e}")
            
            # Также сохраняем основной favicon.png
            main_favicon_paths = [
                'static/new/img/favicon/favicon.png',
                'staticfiles/new/img/favicon/favicon.png'
            ]
            
            for fav_path in main_favicon_paths:
                try:
                    resized_main = img.resize((192, 192), Image.Resampling.LANCZOS)
                    resized_main.save(fav_path, 'PNG')
                except:
                    pass
            
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write(self.style.SUCCESS("[SUCCESS] FAVICON САЙТА УСТАНОВЛЕН!"))
            self.stdout.write("=" * 60)
            
            self.stdout.write(f"\nФайлы созданы:")
            self.stdout.write(f"  - favicon.ico (корень)")
            self.stdout.write(f"  - favicon-16x16.png до favicon-512x512.png")
            self.stdout.write(f"  - В директориях: static/ и staticfiles/")
            
            self.stdout.write(f"\nОбновите страницу сайта и очистите кэш браузера (Ctrl+F5)")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n[ERROR] Ошибка: {str(e)}"))
            import traceback
            self.stdout.write(traceback.format_exc())

