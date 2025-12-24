"""
Management команда для инициализации настроек ads.txt
"""
from django.core.management.base import BaseCommand
from advertising.models import AdsTxtSettings


class Command(BaseCommand):
    help = 'Инициализировать настройки ads.txt для Ezoic'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Пересоздать настройки, даже если они уже существуют',
        )
    
    def handle(self, *args, **options):
        force = options.get('force', False)
        
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('Инициализация настроек ads.txt'))
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write('')
        
        # Проверяем существующие настройки
        existing = AdsTxtSettings.objects.first()
        
        if existing and not force:
            self.stdout.write(self.style.WARNING('  [SKIP] Настройки уже существуют'))
            self.stdout.write(f'  Домен: {existing.domain}')
            self.stdout.write(f'  URL: {existing.ezoic_manager_url}')
            self.stdout.write(f'  Активен: {"Да" if existing.is_active else "Нет"}')
            self.stdout.write('')
            self.stdout.write('  Используйте --force для пересоздания')
            return
        
        if existing and force:
            self.stdout.write('  Удаление существующих настроек...')
            existing.delete()
        
        # Создаём новые настройки
        self.stdout.write('  Создание настроек...')
        
        settings = AdsTxtSettings.objects.create(
            domain='idealimage.ru',
            ezoic_manager_url='https://srv.adstxtmanager.com/19390/idealimage.ru',
            auto_update=True,
            update_interval_hours=24,
            is_active=True
        )
        
        self.stdout.write(self.style.SUCCESS('  [OK] Настройки созданы!'))
        self.stdout.write(f'  Домен: {settings.domain}')
        self.stdout.write(f'  URL: {settings.ezoic_manager_url}')
        self.stdout.write(f'  Автообновление: {"Включено" if settings.auto_update else "Выключено"}')
        self.stdout.write(f'  Интервал: {settings.update_interval_hours} часов')
        self.stdout.write(f'  Активен: {"Да" if settings.is_active else "Нет"}')
        self.stdout.write('')
        self.stdout.write('  Теперь можно обновить файл:')
        self.stdout.write(self.style.SUCCESS('    python manage.py update_ads_txt'))
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('Инициализация завершена!'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')

