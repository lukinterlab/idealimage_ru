#!/usr/bin/env python
"""
Восстановление путей к изображениям на сервере из JSON
"""
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'IdealImage_PDJ.settings')
django.setup()

from blog.models import Post

print("="*80)
print("ВОССТАНОВЛЕНИЕ ПУТЕЙ К ИЗОБРАЖЕНИЯМ")
print("="*80)
print()

# Проверяем наличие файла
json_file = 'image_paths_backup.json'
if not os.path.exists(json_file):
    print(f"❌ ОШИБКА: Файл {json_file} не найден!")
    print("   Загрузите его с локалки через FTP")
    exit(1)

print(f"[1/3] Загружаю данные из {json_file}...")
with open(json_file, 'r', encoding='utf-8') as f:
    image_data = json.load(f)

print(f"   ✅ Загружено записей: {len(image_data)}")

print()
print("[2/3] Восстанавливаю пути к изображениям...")

restored = 0
not_found = 0
errors = []

for post_id_str, data in image_data.items():
    post_id = int(post_id_str)
    kartinka = data['kartinka']
    
    try:
        post = Post.objects.get(id=post_id)
        post.kartinka = kartinka
        post.save(update_fields=['kartinka'])
        restored += 1
        
        if restored % 100 == 0:
            print(f"   Восстановлено: {restored}/{len(image_data)}...")
            
    except Post.DoesNotExist:
        not_found += 1
        errors.append(f"Пост ID {post_id} не найден")
    except Exception as e:
        errors.append(f"Ошибка для поста ID {post_id}: {e}")

print()
print("[3/3] Проверка результатов...")

# Проверяем сколько постов с изображениями
posts_with_images = Post.objects.filter(kartinka__isnull=False).exclude(kartinka='')
print(f"   ✅ Постов с изображениями в БД: {posts_with_images.count()}")

print()
print("="*80)
print("РЕЗУЛЬТАТ:")
print(f"   Восстановлено: {restored}")
print(f"   Не найдено: {not_found}")
print(f"   Ошибок: {len(errors)}")

if errors and len(errors) <= 10:
    print()
    print("Первые ошибки:")
    for err in errors[:10]:
        print(f"   - {err}")

print("="*80)
print()
print("✅ ВОССТАНОВЛЕНИЕ ЗАВЕРШЕНО!")
print()
print("СЛЕДУЮЩИЙ ШАГ:")
print("   touch tmp/restart.txt")
print("   Проверьте: https://idealimage.ru/blog/")
print("="*80)

