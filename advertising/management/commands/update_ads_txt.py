"""
Management команда для обновления файла ads.txt от Ezoic
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from advertising.models import AdsTxtSettings


class Command(BaseCommand):
    help = 'Обновить файл ads.txt от Ezoic'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Принудительно обновить, даже если не требуется',
        )
    
    def handle(self, *args, **options):
        force = options.get('force', False)
        
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('Обновление файла ads.txt'))
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write('')
        
        # Получаем настройки
        settings_obj = AdsTxtSettings.objects.first()
        
        if not settings_obj:
            self.stdout.write(self.style.ERROR('  [ERROR] Настройки ads.txt не найдены'))
            self.stdout.write('  Создайте настройки через админку или дашборд')
            return
        
        # Проверяем, нужно ли обновление
        if not force and not settings_obj.needs_update():
            self.stdout.write(self.style.WARNING('  [SKIP] Обновление не требуется'))
            if settings_obj.last_successful_update:
                self.stdout.write(f'  Последнее обновление: {settings_obj.last_successful_update.strftime("%Y-%m-%d %H:%M:%S")}')
            return
        
        # Обновляем
        self.stdout.write(f'  Домен: {settings_obj.domain}')
        self.stdout.write(f'  URL: {settings_obj.ezoic_manager_url}')
        self.stdout.write('  Обновление...')
        
        success, message = settings_obj.update_from_ezoic()
        
        if success:
            self.stdout.write(self.style.SUCCESS(f'  [OK] {message}'))
            self.stdout.write(f'  Обновлений всего: {settings_obj.update_count}')
            if settings_obj.content:
                lines_count = len(settings_obj.content.split('\n'))
                self.stdout.write(f'  Строк в файле: {lines_count}')
        else:
            self.stdout.write(self.style.ERROR(f'  [ERROR] {message}'))
            if settings_obj.last_error:
                self.stdout.write(f'  Ошибка: {settings_obj.last_error[:200]}')
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('Обновление завершено!'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')

