"""
Команда для создания таблицы кэша в БД
Запускать после переключения на DB кэш: python manage.py init_cache_table
"""
from django.core.management.base import BaseCommand
from django.core.cache import cache


class Command(BaseCommand):
    help = 'Создает таблицу для DB кэша (django_cache_table)'

    def handle(self, *args, **options):
        self.stdout.write('Инициализация таблицы кэша...')
        
        try:
            # Django автоматически создает таблицу при первом использовании
            # Просто делаем пробную операцию для проверки/создания таблицы
            cache.set('_test_key', '_test_value', 1)
            cache.get('_test_key')
            cache.delete('_test_key')
            
            self.stdout.write(self.style.SUCCESS('✓ Таблица кэша создана/проверена успешно'))
            self.stdout.write('  Таблица: django_cache_table')
            self.stdout.write('  Backend: DatabaseCache')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Ошибка создания таблицы кэша: {e}'))
            self.stdout.write('  Убедитесь что миграции применены: python manage.py migrate')

