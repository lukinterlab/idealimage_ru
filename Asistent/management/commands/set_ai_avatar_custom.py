"""
Management command для установки кастомной аватарки AI
Запуск: python manage.py set_ai_avatar_custom <путь_к_файлу>
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.core.files import File
from Visitor.models import Profile
import os


class Command(BaseCommand):
    help = 'Устанавливает указанный файл как аватарку для AI пользователя'

    def add_arguments(self, parser):
        parser.add_argument(
            'image_path',
            type=str,
            help='Путь к файлу изображения'
        )

    def handle(self, *args, **options):
        image_path = options['image_path']
        
        self.stdout.write("=" * 60)
        self.stdout.write("УСТАНОВКА КАСТОМНОЙ АВАТАРКИ AI")
        self.stdout.write("=" * 60)
        
        try:
            # Проверяем существование файла
            if not os.path.exists(image_path):
                self.stdout.write(self.style.ERROR(f"[ERROR] Файл не найден: {image_path}"))
                return
            
            self.stdout.write(f"[OK] Файл найден: {image_path}")
            file_size = os.path.getsize(image_path) / 1024  # KB
            self.stdout.write(f"   Размер: {file_size:.2f} KB")
            
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
            
            # Получаем имя файла
            filename = os.path.basename(image_path)
            self.stdout.write(f"\n[...] Установка аватарки: {filename}")
            
            # Открываем файл и устанавливаем как аватар
            with open(image_path, 'rb') as f:
                profile.avatar.save(filename, File(f), save=True)
            
            self.stdout.write(self.style.SUCCESS(f"[OK] Аватарка установлена!"))
            self.stdout.write(f"   URL: {profile.avatar.url}")
            
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write(self.style.SUCCESS("[SUCCESS] АВАТАРКА AI ОБНОВЛЕНА!"))
            self.stdout.write("=" * 60)
            
            self.stdout.write(f"\nПроверить можно здесь:")
            self.stdout.write(f"  /admin/Visitor/profile/{profile.id}/change/")
            self.stdout.write(f"  /admin/auth/user/{ai_user.id}/change/")
            
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR("\n[ERROR] AI пользователь 'ai_assistant' не найден!"))
            self.stdout.write("Сначала запустите генерацию статей чтобы создать пользователя")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n[ERROR] Ошибка: {str(e)}"))
            import traceback
            self.stdout.write(traceback.format_exc())

