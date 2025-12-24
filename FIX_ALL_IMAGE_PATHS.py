#!/usr/bin/env python
"""
Исправление путей к изображениям в базе данных
Ищет WebP файлы и обновляет пути в Post.kartinka
"""
import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'IdealImage_PDJ.settings')
django.setup()

from blog.models import Post
from utilits.utils import generate_image_filename
import logging

logger = logging.getLogger(__name__)

def fix_image_paths():
    print("="*80)
    print("ИСПРАВЛЕНИЕ ПУТЕЙ К ИЗОБРАЖЕНИЯМ")
    print("="*80)
    print()

    # 1. Сканируем все WebP файлы в media/images/
    print("[1/4] Сканирую WebP файлы...")
    webp_files = {}
    images_dir = os.path.join(settings.MEDIA_ROOT, 'images')
    
    if os.path.exists(images_dir):
        for root, _, files in os.walk(images_dir):
            for file in files:
                if file.lower().endswith('.webp'):
                    # Сохраняем имя без расширения и относительный путь
                    base_name = os.path.splitext(file)[0]
                    rel_path = os.path.relpath(os.path.join(root, file), settings.MEDIA_ROOT)
                    webp_files[base_name] = rel_path
        print(f"   Найдено WebP файлов: {len(webp_files)}")
    else:
        print(f"   ❌ Папка {images_dir} не найдена!")
        return

    # 2. Обрабатываем посты
    print()
    print("[2/4] Обрабатываю посты...")
    posts_with_images = Post.objects.filter(kartinka__isnull=False).exclude(kartinka='')
    total = posts_with_images.count()
    print(f"   Постов с изображениями: {total}")

    fixed = 0
    already_ok = 0
    cleared = 0

    print()
    print("[3/4] Исправляю пути (это займёт 2-3 минуты)...")
    
    for i, post in enumerate(posts_with_images):
        if i % 100 == 0 and i > 0:
            print(f"   Обработано: {i}/{total}...")

        original_path = post.kartinka.name
        
        # Если путь уже WebP и файл существует - пропускаем
        if original_path.lower().endswith('.webp'):
            full_path = os.path.join(settings.MEDIA_ROOT, original_path)
            if os.path.exists(full_path):
                already_ok += 1
                continue

        # Генерируем ожидаемое имя WebP файла на основе заголовка
        expected_base = generate_image_filename(post.title, extension='').rsplit('-', 1)[0]
        
        found = False
        for base_name, rel_path in webp_files.items():
            if base_name.startswith(expected_base):
                post.kartinka.name = rel_path
                post.save(update_fields=['kartinka'])
                fixed += 1
                found = True
                break
        
        if not found:
            # Если не нашли - очищаем поле
            post.kartinka.name = ''
            post.save(update_fields=['kartinka'])
            cleared += 1

    print()
    print("[4/4] Проверка результатов...")
    # Проверяем случайные посты
    sample = Post.objects.filter(kartinka__isnull=False).exclude(kartinka='').order_by('?')[:50]
    existing = 0
    missing = 0
    
    for post in sample:
        full_path = os.path.join(settings.MEDIA_ROOT, post.kartinka.name)
        if os.path.exists(full_path):
            existing += 1
        else:
            missing += 1
    
    print(f"   Проверено 50 случайных постов:")
    print(f"   ✅ Файлы существуют: {existing}")
    print(f"   ❌ Файлы не найдены: {missing}")

    print()
    print("="*80)
    print("РЕЗУЛЬТАТ:")
    print(f"   Исправлено: {fixed}")
    print(f"   Уже правильные: {already_ok}")
    print(f"   Очищено: {cleared}")
    print("="*80)
    print()
    print("✅ ГОТОВО!")
    print("="*80)

if __name__ == '__main__':
    fix_image_paths()

