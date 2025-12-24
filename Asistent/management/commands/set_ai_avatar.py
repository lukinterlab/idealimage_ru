"""
Management command для установки логотипа сайта как аватарки AI
Запуск: python manage.py set_ai_avatar
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.core.files import File
from Visitor.models import Profile
import os
import shutil


class Command(BaseCommand):
    help = 'Устанавливает логотип сайта как аватарку для AI пользователя'

    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write("УСТАНОВКА АВАТАРКИ AI ПОЛЬЗОВАТЕЛЯ")
        self.stdout.write("=" * 60)
        
        try:
            # Находим AI пользователя
            ai_user = User.objects.get(username='ai_assistant')
            self.stdout.write(self.style.SUCCESS(f"[OK] AI пользователь найден (ID: {ai_user.id})"))
            
            # Проверяем профиль
            if not hasattr(ai_user, 'profile'):
                self.stdout.write(self.style.ERROR("[ERROR] У AI пользователя нет профиля!"))
                self.stdout.write("Запустите: python manage.py fix_ai_profile")
                return
            
            profile = ai_user.profile
            self.stdout.write(self.style.SUCCESS(f"[OK] Профиль найден (ID: {profile.id})"))
            
            # Путь к логотипу сайта
            logo_paths = [
                'static/new/img/logo.png',
                'static/new/img/favicon/favicon-192x192.png',
                'static/new/img/favicon/favicon.png',
                'media/images/avatar.png'
            ]
            
            logo_path = None
            for path in logo_paths:
                if os.path.exists(path):
                    logo_path = path
                    break
            
            if not logo_path:
                self.stdout.write(self.style.ERROR("[ERROR] Логотип не найден!"))
                self.stdout.write(f"Проверенные пути:")
                for path in logo_paths:
                    self.stdout.write(f"  - {path}")
                return
            
            self.stdout.write(f"\n[OK] Логотип найден: {logo_path}")
            
            # Копируем логотип в папку аватаров
            avatar_dir = 'media/images/avatars/'
            os.makedirs(avatar_dir, exist_ok=True)
            
            avatar_filename = 'ai_assistant_avatar.png'
            avatar_path = os.path.join(avatar_dir, avatar_filename)
            
            self.stdout.write(f"[...] Копирование логотипа...")
            shutil.copy2(logo_path, avatar_path)
            self.stdout.write(self.style.SUCCESS(f"[OK] Логотип скопирован: {avatar_path}"))
            
            # Устанавливаем аватарку в профиль
            with open(avatar_path, 'rb') as f:
                profile.avatar.save(avatar_filename, File(f), save=True)
            
            self.stdout.write(self.style.SUCCESS(f"[OK] Аватарка установлена!"))
            self.stdout.write(f"   URL: {profile.avatar.url}")
            
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write(self.style.SUCCESS("[SUCCESS] АВАТАРКА AI УСТАНОВЛЕНА!"))
            self.stdout.write("=" * 60)
            
            self.stdout.write(f"\nПроверить можно здесь:")
            self.stdout.write(f"  /admin/Visitor/profile/{profile.id}/change/")
            
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR("\n[ERROR] AI пользователь 'ai_assistant' не найден!"))
            self.stdout.write("Сначала запустите генерацию статей чтобы создать пользователя")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n[ERROR] Ошибка: {str(e)}"))
            import traceback
            self.stdout.write(traceback.format_exc())

