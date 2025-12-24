"""
Management command для исправления профиля AI пользователя
Запуск: python manage.py fix_ai_profile
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from Visitor.models import Profile


class Command(BaseCommand):
    help = 'Исправляет профиль AI пользователя'

    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write("ИСПРАВЛЕНИЕ ПРОФИЛЯ AI ПОЛЬЗОВАТЕЛЯ")
        self.stdout.write("=" * 60)
        
        try:
            # Получаем или создаем пользователя ai_assistant
            ai_user, user_created = User.objects.get_or_create(
                username='ai_assistant',
                defaults={
                    'first_name': 'AI',
                    'last_name': 'Ассистент',
                    'email': 'ai@idealimage.ru',
                    'is_active': True
                }
            )
            
            if user_created:
                self.stdout.write(self.style.SUCCESS(f"[OK] Пользователь 'ai_assistant' создан (ID: {ai_user.id})"))
            else:
                self.stdout.write(self.style.SUCCESS(f"[OK] Пользователь 'ai_assistant' найден (ID: {ai_user.id})"))
            
            # Проверяем/создаем профиль
            profile, profile_created = Profile.objects.get_or_create(
                vizitor=ai_user,
                defaults={
                    'bio': 'AI-ассистент для автоматической генерации статей',
                    'completed_tasks_count': 0
                }
            )
            
            if profile_created:
                self.stdout.write(self.style.SUCCESS(f"[OK] Профиль создан (ID: {profile.id})"))
            else:
                self.stdout.write(self.style.SUCCESS(f"[OK] Профиль существует (ID: {profile.id})"))
            
            # Проверяем поле completed_tasks_count
            self.stdout.write(f"\nПроверка полей профиля:")
            self.stdout.write(f"  - completed_tasks_count: {profile.completed_tasks_count}")
            self.stdout.write(f"  - bio: {profile.bio[:50]}...")
            
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write(self.style.SUCCESS("[OK] ПРОФИЛЬ AI ПОЛЬЗОВАТЕЛЯ В ПОРЯДКЕ!"))
            self.stdout.write("=" * 60)
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n[ERROR] ОШИБКА: {str(e)}"))
            self.stdout.write("\n" + "=" * 60)
            return

