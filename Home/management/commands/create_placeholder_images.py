"""
Команда для создания placeholder изображений для лендинга №2
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import random


class Command(BaseCommand):
    help = 'Создание placeholder изображений для лендинга №2'

    def __init__(self):
        super().__init__()
        self.media_dir = Path(settings.MEDIA_ROOT) / 'landing2'
        self.colors = [
            '#ff6b9d', '#c44569', '#ffa500', '#ff8c00',  # Розово-оранжевые
            '#9b59b6', '#8e44ad', '#3498db', '#2980b9',  # Фиолетово-синие
            '#e74c3c', '#c0392b', '#f39c12', '#d35400',  # Красно-оранжевые
        ]

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🎨 Создаем placeholder изображения...'))
        
        # Определяем нужные изображения
        placeholders = {
            'images': [
                ('service-1.jpg', 800, 600, '✂️\nПарикмахерские\nуслуги'),
                ('service-2.jpg', 800, 600, '💅\nМаникюр\nи педикюр'),
                ('service-3.jpg', 800, 600, '✨\nКосметология'),
                ('service-4.jpg', 800, 600, '🌸\nSPA\nи массаж'),
                ('service-5.jpg', 800, 600, '👁️\nБрови\nи ресницы'),
                ('service-6.jpg', 800, 600, '⚡\nЛазерная\nэпиляция'),
                ('about.jpg', 800, 600, '💖\nIdealImage\nBeauty Studio'),
                ('client-1.jpg', 300, 300, '👤'),
                ('client-2.jpg', 300, 300, '👤'),
                ('client-3.jpg', 300, 300, '👤'),
            ],
            'portfolio': [
                (f'work-{i}.jpg', 600, 600, f'Работа\n#{i}') 
                for i in range(1, 7)
            ],
            'team': [
                (f'master-{i}.jpg', 400, 500, f'Мастер\n#{i}') 
                for i in range(1, 4)
            ],
            'brands': [
                (f'logo-{i}.png', 200, 100, f'Бренд\n{i}') 
                for i in range(1, 7)
            ],
            'backgrounds': [
                ('hero-bg.jpg', 1920, 1080, ''),
                ('cta-bg.jpg', 1920, 1080, ''),
            ],
        }
        
        created_count = 0
        
        for category, images in placeholders.items():
            category_dir = self.media_dir / category
            category_dir.mkdir(parents=True, exist_ok=True)
            
            for filename, width, height, text in images:
                filepath = category_dir / filename
                
                # Пропускаем если файл уже существует
                if filepath.exists():
                    self.stdout.write(f'   ⏭️  Пропускаем {filepath.name} (уже существует)')
                    continue
                
                # Создаем изображение
                self.create_placeholder(filepath, width, height, text)
                created_count += 1
                self.stdout.write(f'   ✅ Создан {category}/{filepath.name}')
        
        self.stdout.write(self.style.SUCCESS(f'\n✨ Создано {created_count} placeholder изображений!'))
        self.stdout.write(f'   Папка: {self.media_dir}')
        self.stdout.write('\n💡 Совет: Замените эти изображения на свои для лучшего вида!')
    
    def create_placeholder(self, filepath, width, height, text):
        """Создает красивое placeholder изображение"""
        # Создаем градиент
        image = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(image)
        
        # Выбираем случайный цвет из палитры
        color1 = self.hex_to_rgb(random.choice(self.colors))
        color2 = self.hex_to_rgb(random.choice(self.colors))
        
        # Рисуем градиент
        for y in range(height):
            ratio = y / height
            r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
            g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
            b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        
        # Добавляем узор
        for i in range(0, width, 50):
            for j in range(0, height, 50):
                draw.ellipse([i, j, i+3, j+3], fill=(255, 255, 255, 30))
        
        # Добавляем текст
        if text:
            try:
                # Пытаемся использовать системный шрифт
                font_size = min(width, height) // 8
                try:
                    font = ImageFont.truetype("arial.ttf", font_size)
                except:
                    font = ImageFont.load_default()
            except:
                font = ImageFont.load_default()
            
            # Центрируем текст
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (width - text_width) // 2
            y = (height - text_height) // 2
            
            # Рисуем тень
            draw.text((x+2, y+2), text, fill=(0, 0, 0, 128), font=font)
            # Рисуем текст
            draw.text((x, y), text, fill='white', font=font)
        
        # Добавляем watermark
        watermark = "IdealImage.ru"
        try:
            wm_font = ImageFont.truetype("arial.ttf", 14)
        except:
            wm_font = ImageFont.load_default()
        
        bbox = draw.textbbox((0, 0), watermark, font=wm_font)
        wm_width = bbox[2] - bbox[0]
        
        draw.text(
            (width - wm_width - 10, height - 25),
            watermark,
            fill=(255, 255, 255, 128),
            font=wm_font
        )
        
        # Сохраняем
        image.save(filepath, quality=85, optimize=True)
    
    def hex_to_rgb(self, hex_color):
        """Конвертирует HEX в RGB"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

