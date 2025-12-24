"""
Management команда для полной настройки Sozseti за один раз
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Полная настройка приложения Sozseti'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--with-demo',
            action='store_true',
            help='Создать демо-расписания'
        )
    
    def handle(self, *args, **options):
        self.stdout.write('='*60)
        self.stdout.write(self.style.SUCCESS('[SOZSETI SETUP] Начинаем настройку...'))
        self.stdout.write('='*60)
        
        # Шаг 1: Миграции
        self.stdout.write('\n[1/5] Применение миграций...')
        try:
            call_command('migrate', '--noinput', verbosity=0)
            self.stdout.write(self.style.SUCCESS('  [OK] Миграции применены'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  [ERROR] {e}'))
        
        # Шаг 2: Инициализация платформ
        self.stdout.write('\n[2/5] Инициализация платформ...')
        try:
            call_command('init_social_platforms')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  [ERROR] {e}'))
        
        # Шаг 3: Синхронизация Telegram
        self.stdout.write('\n[3/5] Синхронизация Telegram каналов...')
        try:
            call_command('sync_telegram_channels')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  [ERROR] {e}'))
        
        # Шаг 4: Демо-данные (опционально)
        if options['with_demo']:
            self.stdout.write('\n[4/5] Создание демо-расписаний...')
            try:
                call_command('create_demo_schedules')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  [ERROR] {e}'))
        else:
            self.stdout.write('\n[4/5] Демо-данные пропущены (используйте --with-demo)')
        
        # Шаг 5: Проверка
        self.stdout.write('\n[5/5] Финальная проверка...')
        try:
            call_command('check', verbosity=0)
            self.stdout.write(self.style.SUCCESS('  [OK] Проверка пройдена'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  [ERROR] {e}'))
        
        # Итоги
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('[COMPLETE] Настройка завершена!'))
        self.stdout.write('='*60)
        
        self.stdout.write('\nСтатус:')
        
        from Sozseti.models import SocialPlatform, SocialChannel
        
        platforms = SocialPlatform.objects.all()
        for platform in platforms:
            status = '[OK]' if platform.is_active else '[  ]'
            vpn = ' (VPN)' if platform.requires_vpn else ''
            channels_count = platform.channels.count()
            
            self.stdout.write(
                f'  {status} {platform.get_name_display()}{vpn}: {channels_count} каналов'
            )
        
        self.stdout.write('\nСледующие шаги:')
        self.stdout.write('1. Настройте API токены в .env файле')
        self.stdout.write('2. Активируйте платформы: /admin/Sozseti/socialplatform/')
        self.stdout.write('3. Проверьте каналы: /admin/Sozseti/socialchannel/')
        self.stdout.write('4. Откройте дашборд: /sozseti/dashboard/')
        self.stdout.write('5. Создайте расписания: /admin/Sozseti/publicationschedule/')
        self.stdout.write('\nДокументация: ИНСТРУКЦИИ/ИНСТРУКЦИЯ_СОЦСЕТИ.md')

