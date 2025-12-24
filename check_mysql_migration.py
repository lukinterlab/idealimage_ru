#!/usr/bin/env python
"""
Проверка успешности миграции на MySQL
"""
import os
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'IdealImage_PDJ.settings')
django.setup()

from django.db import connection
from django.contrib.auth.models import User
from blog.models import Post, Category
from Visitor.models import Profile
from django_q.models import Task, Schedule

print("="*80)
print("ПРОВЕРКА МИГРАЦИИ НА MySQL")
print("="*80)
print()

# 1. Проверка подключения
print("[1/8] Проверка подключения к базе данных...")
try:
    db_vendor = connection.vendor
    db_name = connection.settings_dict['NAME']
    db_user = connection.settings_dict['USER']
    db_host = connection.settings_dict.get('HOST', 'localhost')
    
    print(f"   ✅ Движок: {db_vendor}")
    print(f"   ✅ База: {db_name}")
    print(f"   ✅ Пользователь: {db_user}")
    print(f"   ✅ Хост: {db_host}")
    
    if db_vendor != 'mysql':
        print(f"   ⚠️  ВНИМАНИЕ: Используется {db_vendor}, а не MySQL!")
    
except Exception as e:
    print(f"   ❌ Ошибка подключения: {e}")
    exit(1)

# 2. Проверка пользователей
print()
print("[2/8] Проверка пользователей...")
try:
    users_count = User.objects.count()
    superusers = User.objects.filter(is_superuser=True)
    staff = User.objects.filter(is_staff=True)
    
    print(f"   ✅ Всего пользователей: {users_count}")
    print(f"   ✅ Суперпользователей: {superusers.count()}")
    print(f"   ✅ Персонал: {staff.count()}")
    
    if superusers.exists():
        print(f"   ✅ Суперпользователи: {', '.join([u.username for u in superusers[:5]])}")
    
    if users_count < 5:
        print("   ⚠️  ВНИМАНИЕ: Мало пользователей, возможно данные не полностью импортированы")
        
except Exception as e:
    print(f"   ❌ Ошибка: {e}")

# 3. Проверка постов
print()
print("[3/8] Проверка постов...")
try:
    posts_count = Post.objects.count()
    published = Post.objects.filter(status='published').count()
    drafts = Post.objects.filter(status='draft').count()
    
    print(f"   ✅ Всего постов: {posts_count}")
    print(f"   ✅ Опубликованных: {published}")
    print(f"   ✅ Черновиков: {drafts}")
    
    # Последние посты
    recent_posts = Post.objects.order_by('-created')[:3]
    if recent_posts:
        print(f"   ✅ Последние посты:")
        for post in recent_posts:
            print(f"      - {post.title[:50]}... (автор: {post.author.username})")
    
    if posts_count < 100:
        print("   ⚠️  ВНИМАНИЕ: Мало постов, проверьте импорт данных")
        
except Exception as e:
    print(f"   ❌ Ошибка: {e}")

# 4. Проверка категорий
print()
print("[4/8] Проверка категорий...")
try:
    categories = Category.objects.all()
    print(f"   ✅ Категорий: {categories.count()}")
    
    if categories.exists():
        print(f"   ✅ Список категорий:")
        for cat in categories[:10]:
            posts_in_cat = cat.posts.count()
            print(f"      - {cat.title} ({posts_in_cat} постов)")
    
    if categories.count() == 0:
        print("   ⚠️  ВНИМАНИЕ: Нет категорий!")
        
except Exception as e:
    print(f"   ❌ Ошибка: {e}")

# 5. Проверка профилей
print()
print("[5/8] Проверка профилей...")
try:
    profiles = Profile.objects.all()
    authors = Profile.objects.filter(is_author=True)
    
    print(f"   ✅ Профилей: {profiles.count()}")
    print(f"   ✅ Авторов: {authors.count()}")
    
    # Проверка профилей с постами
    profiles_with_posts = Profile.objects.filter(vizitor__author_posts__isnull=False).distinct()
    print(f"   ✅ Профилей с постами: {profiles_with_posts.count()}")
    
    if profiles.count() != User.objects.count():
        print(f"   ⚠️  ВНИМАНИЕ: Профилей ({profiles.count()}) != Пользователей ({User.objects.count()})")
        
except Exception as e:
    print(f"   ❌ Ошибка: {e}")

# 6. Проверка Django-Q
print()
print("[6/8] Проверка Django-Q...")
try:
    schedules = Schedule.objects.all()
    tasks = Task.objects.all()
    
    print(f"   ✅ Расписаний: {schedules.count()}")
    print(f"   ✅ Задач в истории: {tasks.count()}")
    
    if schedules.exists():
        print(f"   ✅ Активные расписания:")
        for schedule in schedules[:5]:
            print(f"      - {schedule.name}: {schedule.func}")
    
    if schedules.count() == 0:
        print("   ⚠️  ВНИМАНИЕ: Нет расписаний Django-Q!")
        
except Exception as e:
    print(f"   ❌ Ошибка: {e}")

# 7. Проверка таблиц
print()
print("[7/8] Проверка структуры БД...")
try:
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        tables_count = len(tables)
        
        print(f"   ✅ Таблиц в БД: {tables_count}")
        
        # Проверяем критичные таблицы
        critical_tables = [
            'auth_user',
            'blog_post',
            'blog_category',
            'app_profiles',
            'django_q_schedule',
            'django_q_task',
            'advertising_adbanner',
        ]
        
        table_names = [t[0] for t in tables]
        missing = []
        
        for table in critical_tables:
            if table in table_names:
                print(f"   ✅ {table}")
            else:
                print(f"   ❌ {table} - ОТСУТСТВУЕТ!")
                missing.append(table)
        
        if missing:
            print(f"   ⚠️  ВНИМАНИЕ: Отсутствуют таблицы: {', '.join(missing)}")
            print(f"   ⚠️  Запустите: python manage.py migrate --run-syncdb")
            
except Exception as e:
    print(f"   ❌ Ошибка: {e}")

# 8. Проверка изображений
print()
print("[8/8] Проверка медиа-файлов...")
try:
    # Проверяем посты с изображениями
    posts_with_images = Post.objects.filter(kartinka__isnull=False).exclude(kartinka='')
    print(f"   ✅ Постов с изображениями: {posts_with_images.count()}")
    
    # Проверяем несколько путей
    import os
    from django.conf import settings
    
    media_root = settings.MEDIA_ROOT
    if os.path.exists(media_root):
        # Подсчитываем файлы в media/images
        images_dir = os.path.join(media_root, 'images')
        if os.path.exists(images_dir):
            image_files = []
            for root, dirs, files in os.walk(images_dir):
                image_files.extend([f for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif'))])
            print(f"   ✅ Файлов изображений в media/images/: {len(image_files)}")
        else:
            print(f"   ⚠️  Папка {images_dir} не найдена")
    else:
        print(f"   ⚠️  MEDIA_ROOT ({media_root}) не найден")
    
    # Проверяем профили с аватарами
    profiles_with_avatars = Profile.objects.exclude(avatar='images/avatar.png')
    print(f"   ✅ Профилей с аватарами: {profiles_with_avatars.count()}")
    
except Exception as e:
    print(f"   ❌ Ошибка: {e}")

# Итоговый отчет
print()
print("="*80)
print("ИТОГОВЫЙ ОТЧЕТ:")
print("="*80)

try:
    summary = {
        'Движок БД': db_vendor.upper(),
        'База данных': db_name,
        'Пользователей': User.objects.count(),
        'Постов': Post.objects.count(),
        'Категорий': Category.objects.count(),
        'Профилей': Profile.objects.count(),
        'Django-Q расписаний': Schedule.objects.count(),
        'Таблиц в БД': tables_count,
    }
    
    for key, value in summary.items():
        print(f"   {key}: {value}")
    
    print()
    
    # Проверка что всё ОК
    if (db_vendor == 'mysql' and 
        User.objects.count() >= 10 and 
        Post.objects.count() >= 100 and
        Category.objects.count() >= 3 and
        Profile.objects.count() >= 10 and
        Schedule.objects.count() >= 3):
        
        print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!")
        print("✅ МИГРАЦИЯ ВЫПОЛНЕНА УСПЕШНО!")
    else:
        print("⚠️  ЕСТЬ ЗАМЕЧАНИЯ:")
        if db_vendor != 'mysql':
            print("   - Используется не MySQL")
        if User.objects.count() < 10:
            print("   - Мало пользователей")
        if Post.objects.count() < 100:
            print("   - Мало постов")
        if Category.objects.count() < 3:
            print("   - Мало категорий")
        if Profile.objects.count() < 10:
            print("   - Мало профилей")
        if Schedule.objects.count() < 3:
            print("   - Мало расписаний Django-Q")
        
        print()
        print("РЕКОМЕНДАЦИЯ: Проверьте импорт данных")
    
except Exception as e:
    print(f"❌ Ошибка итогового отчета: {e}")

print("="*80)

