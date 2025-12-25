#!/usr/bin/env python
"""
Обновление профилей авторов
Устанавливает is_author=True и заполняет bio, spez
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'IdealImage_PDJ.settings')
django.setup()

from django.contrib.auth.models import User
from Visitor.models import Profile

def update_profiles():
    print("="*80)
    print("ОБНОВЛЕНИЕ ПРОФИЛЕЙ АВТОРОВ")
    print("="*80)
    print()

    # Находим всех пользователей с постами
    print("[1/3] Поиск авторов...")
    users_with_posts = User.objects.filter(author_posts__isnull=False).distinct()
    print(f"   Найдено авторов: {users_with_posts.count()}")

    print()
    print("[2/3] Обновление профилей...")
    updated = 0
    
    for user in users_with_posts:
        try:
            profile = user.profile
            post_count = user.author_posts.count()
            
            # Устанавливаем is_author
            if not profile.is_author:
                profile.is_author = True
                updated += 1
            
            # Генерируем bio если пустое
            if not profile.bio:
                if post_count >= 100:
                    profile.bio = f"Профессиональный автор. Опубликовано статей: {post_count}"
                elif post_count >= 50:
                    profile.bio = f"Опытный автор. Опубликовано статей: {post_count}"
                elif post_count >= 10:
                    profile.bio = f"Активный автор. Опубликовано статей: {post_count}"
                else:
                    profile.bio = f"Автор. Опубликовано статей: {post_count}"
            
            # Генерируем spez если пустое
            if not profile.spez:
                if post_count >= 100:
                    profile.spez = "Профессиональный копирайтер"
                elif post_count >= 50:
                    profile.spez = "Опытный автор"
                elif post_count >= 10:
                    profile.spez = "Контент-мейкер"
                else:
                    profile.spez = "Автор"
            
            profile.save()
            print(f"   ✅ {user.username}: {post_count} постов")
            
        except Profile.DoesNotExist:
            print(f"   ⚠️  {user.username}: профиль не найден")
        except Exception as e:
            print(f"   ❌ {user.username}: ошибка - {e}")

    print()
    print("[3/3] Проверка результатов...")
    authors = Profile.objects.filter(is_author=True)
    print(f"   Всего авторов: {authors.count()}")
    
    # Показываем топ авторов
    top_authors = User.objects.filter(
        author_posts__isnull=False
    ).distinct().order_by('-author_posts__created')[:5]
    
    print()
    print("   Топ авторов:")
    for user in top_authors:
        post_count = user.author_posts.count()
        print(f"      - {user.username}: {post_count} постов")

    print()
    print("="*80)
    print("РЕЗУЛЬТАТ:")
    print(f"   Обновлено профилей: {updated}")
    print(f"   Всего авторов: {authors.count()}")
    print("="*80)
    print()
    print("✅ ГОТОВО!")
    print("="*80)

if __name__ == '__main__':
    update_profiles()

