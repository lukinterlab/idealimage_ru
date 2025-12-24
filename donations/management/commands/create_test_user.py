from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Создать тестового пользователя для ЮКассы'

    def handle(self, *args, **options):
        email = 'test@idealimage.ru'
        password = 'Test2025Ideal'
        
        # Проверяем, есть ли уже такой пользователь
        if User.objects.filter(email=email).exists():
            user = User.objects.get(email=email)
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.WARNING(
                f'Пользователь {email} уже существует. Пароль обновлён.'
            ))
        else:
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password
            )
            self.stdout.write(self.style.SUCCESS(
                f'✅ Тестовый пользователь создан!'
            ))
        
        self.stdout.write(self.style.SUCCESS(
            f'\n📧 Email: {email}\n🔑 Пароль: {password}\n'
        ))
        self.stdout.write(self.style.SUCCESS(
            'Используйте эти данные для передачи в ЮКассу'
        ))

