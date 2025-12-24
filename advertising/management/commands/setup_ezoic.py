"""
Management команда для инициализации интеграции Ezoic
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

from advertising.models import (
    Advertiser, AdCampaign, ExternalScript
)

User = get_user_model()


class Command(BaseCommand):
    help = 'Инициализировать интеграцию Ezoic: создать рекламодателя и скрипты'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Пересоздать записи даже если они уже существуют',
        )
    
    def handle(self, *args, **options):
        force = options.get('force', False)
        
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('Инициализация интеграции Ezoic'))
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write('')
        
        # Получаем или создаем админа
        admin = User.objects.filter(is_staff=True).first()
        if not admin:
            admin = User.objects.first()
        
        # Шаг 1: Создание/получение рекламодателя "Ezoic"
        self.stdout.write('Шаг 1: Создание рекламодателя Ezoic...')
        advertiser, created = Advertiser.objects.get_or_create(
            name='Ezoic',
            defaults={
                'contact_email': 'support@ezoic.com',
                'contact_phone': '',
                'company_info': 'Ezoic - платформа монетизации сайтов через программатическую рекламу. Панель управления: https://pubdash.ezoic.com/',
                'is_active': True
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'  [OK] Создан рекламодатель: {advertiser.name}'))
        else:
            if force:
                advertiser.contact_email = 'support@ezoic.com'
                advertiser.company_info = 'Ezoic - платформа монетизации сайтов через программатическую рекламу. Панель управления: https://pubdash.ezoic.com/'
                advertiser.is_active = True
                advertiser.save()
                self.stdout.write(self.style.SUCCESS(f'  [OK] Обновлен рекламодатель: {advertiser.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'  [SKIP] Рекламодатель уже существует: {advertiser.name}'))
        
        # Шаг 2: Создание скриптов Ezoic
        self.stdout.write('')
        self.stdout.write('Шаг 2: Создание скриптов Ezoic...')
        
        # Скрипт 1: Gatekeeper CMP (приоритет 1)
        script1_data = {
            'name': 'Ezoic - Скрипт конфиденциальности (Gatekeeper CMP)',
            'script_type': 'advertising',
            'provider': 'Ezoic',
            'code': '<script src="https://cmp.gatekeeperconsent.com/min.js" data-cfasync="false"></script>',
            'position': 'head_start',
            'priority': 1,
            'is_active': True,
            'description': 'Скрипт конфиденциальности Ezoic для обработки согласий пользователей (CMP). Должен загружаться первым.',
            'created_by': admin
        }
        
        script1, created1 = ExternalScript.objects.get_or_create(
            name=script1_data['name'],
            defaults=script1_data
        )
        
        if created1:
            self.stdout.write(self.style.SUCCESS(f'  [OK] Создан скрипт 1: {script1.name} (priority={script1.priority})'))
        else:
            if force:
                for key, value in script1_data.items():
                    if key != 'name':
                        setattr(script1, key, value)
                script1.save()
                self.stdout.write(self.style.SUCCESS(f'  [OK] Обновлен скрипт 1: {script1.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'  [SKIP] Скрипт уже существует: {script1.name}'))
        
        # Скрипт 2: Gatekeeper (приоритет 2)
        script2_data = {
            'name': 'Ezoic - Скрипт конфиденциальности (Gatekeeper)',
            'script_type': 'advertising',
            'provider': 'Ezoic',
            'code': '<script src="https://the.gatekeeperconsent.com/cmp.min.js" data-cfasync="false"></script>',
            'position': 'head_start',
            'priority': 2,
            'is_active': True,
            'description': 'Второй скрипт конфиденциальности Ezoic (Gatekeeper). Загружается после первого скрипта.',
            'created_by': admin
        }
        
        script2, created2 = ExternalScript.objects.get_or_create(
            name=script2_data['name'],
            defaults=script2_data
        )
        
        if created2:
            self.stdout.write(self.style.SUCCESS(f'  [OK] Создан скрипт 2: {script2.name} (priority={script2.priority})'))
        else:
            if force:
                for key, value in script2_data.items():
                    if key != 'name':
                        setattr(script2, key, value)
                script2.save()
                self.stdout.write(self.style.SUCCESS(f'  [OK] Обновлен скрипт 2: {script2.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'  [SKIP] Скрипт уже существует: {script2.name}'))
        
        # Скрипт 3: Основной скрипт Ezoic (приоритет 3)
        script3_data = {
            'name': 'Ezoic - Основной скрипт рекламы',
            'script_type': 'advertising',
            'provider': 'Ezoic',
            'code': '''<script async src="//www.ezojs.com/ezoic/sa.min.js"></script>
<script>
    window.ezstandalone = window.ezstandalone || {};
    ezstandalone.cmd = ezstandalone.cmd || [];
</script>''',
            'position': 'head_start',
            'priority': 3,
            'is_active': True,
            'description': 'Основной скрипт Ezoic для показа рекламы. Инициализирует рекламную систему на сайте.',
            'created_by': admin
        }
        
        script3, created3 = ExternalScript.objects.get_or_create(
            name=script3_data['name'],
            defaults=script3_data
        )
        
        if created3:
            self.stdout.write(self.style.SUCCESS(f'  [OK] Создан скрипт 3: {script3.name} (priority={script3.priority})'))
        else:
            if force:
                for key, value in script3_data.items():
                    if key != 'name':
                        setattr(script3, key, value)
                script3.save()
                self.stdout.write(self.style.SUCCESS(f'  [OK] Обновлен скрипт 3: {script3.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'  [SKIP] Скрипт уже существует: {script3.name}'))
        
        # Шаг 3: Проверка интеграции
        self.stdout.write('')
        self.stdout.write('Шаг 3: Проверка интеграции...')
        
        scripts_count = ExternalScript.objects.filter(provider='Ezoic', is_active=True).count()
        scripts_total = ExternalScript.objects.filter(provider='Ezoic').count()
        
        self.stdout.write(self.style.SUCCESS(f'  [OK] Найдено скриптов Ezoic: {scripts_total} (активных: {scripts_count})'))
        
        # Проверка порядка загрузки
        scripts = ExternalScript.objects.filter(
            provider='Ezoic',
            position='head_start',
            is_active=True
        ).order_by('priority')
        
        if scripts.count() == 3:
            priorities = [s.priority for s in scripts]
            if priorities == [1, 2, 3]:
                self.stdout.write(self.style.SUCCESS(f'  [OK] Порядок загрузки правильный: {priorities}'))
            else:
                self.stdout.write(self.style.WARNING(f'  [WARNING] Порядок загрузки: {priorities} (ожидалось [1, 2, 3])'))
        else:
            self.stdout.write(self.style.WARNING(f'  [WARNING] Найдено {scripts.count()} активных скриптов (ожидалось 3)'))
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('[УСПЕШНО] Инициализация Ezoic завершена!'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        self.stdout.write('Создано/обновлено:')
        self.stdout.write(f'  - Рекламодатель: {advertiser.name}')
        self.stdout.write(f'  - Скриптов Ezoic: {scripts_total} (активных: {scripts_count})')
        self.stdout.write('')
        self.stdout.write('Скрипты будут автоматически загружаться в шаблоне через:')
        self.stdout.write('  {% load_external_scripts "head_start" %}')
        self.stdout.write('')
        self.stdout.write('Порядок загрузки:')
        for script in scripts:
            self.stdout.write(f'  {script.priority}. {script.name}')
        self.stdout.write('')
        self.stdout.write('Панель управления Ezoic: https://pubdash.ezoic.com/')
        self.stdout.write('')

