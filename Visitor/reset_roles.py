"""
Скрипт для сброса ролей пользователей
Использование: python manage.py shell < Visitor/reset_roles.py
"""

from django.contrib.auth.models import User
from Visitor.models import Profile

def reset_user_roles(username):
    """Сбросить все роли конкретного пользователя"""
    try:
        user = User.objects.get(username=username)
        profile = user.profile
        
        print(f"\n=== Пользователь: {username} ===")
        print(f"Текущие роли:")
        print(f"  Автор: {profile.is_author}")
        print(f"  Модератор: {profile.is_moderator}")
        print(f"  Маркетолог: {profile.is_marketer}")
        print(f"  Администратор: {profile.is_admin}")
        
        # Сбрасываем роли
        profile.is_author = False
        profile.is_moderator = False
        profile.is_marketer = False
        profile.is_admin = False
        profile.save()
        
        print(f"\n✅ Все роли сброшены для пользователя {username}")
        print(f"Теперь пользователь может подать заявку на роль через личный кабинет")
        
    except User.DoesNotExist:
        print(f"❌ Пользователь {username} не найден")


def reset_all_roles():
    """Сбросить роли у ВСЕХ пользователей"""
    profiles = Profile.objects.all()
    count = 0
    
    for profile in profiles:
        if profile.is_author or profile.is_moderator or profile.is_marketer or profile.is_admin:
            profile.is_author = False
            profile.is_moderator = False
            profile.is_marketer = False
            profile.is_admin = False
            profile.save()
            count += 1
            print(f"Сброшены роли для: {profile.vizitor.username}")
    
    print(f"\n✅ Сброшено ролей у {count} пользователей")


def show_all_users_roles():
    """Показать роли всех пользователей"""
    profiles = Profile.objects.select_related('vizitor').all()
    
    print("\n=== Роли всех пользователей ===\n")
    print(f"{'Пользователь':<20} {'Автор':<8} {'Модератор':<12} {'Маркетолог':<13} {'Админ':<8}")
    print("-" * 70)
    
    for profile in profiles:
        print(f"{profile.vizitor.username:<20} "
              f"{'✓' if profile.is_author else '✗':<8} "
              f"{'✓' if profile.is_moderator else '✗':<12} "
              f"{'✓' if profile.is_marketer else '✗':<13} "
              f"{'✓' if profile.is_admin else '✗':<8}")


# Для использования в Django shell:
# from Visitor.reset_roles import *

# Показать роли всех пользователей
# show_all_users_roles()

# Сбросить роли конкретного пользователя
# reset_user_roles('username')

# Сбросить роли всех пользователей (ОСТОРОЖНО!)
# reset_all_roles()







