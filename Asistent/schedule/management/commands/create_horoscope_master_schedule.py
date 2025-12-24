"""
Management команда для создания управляемого расписания для автопостинга всех гороскопов.
"""
from django.core.management.base import BaseCommand
from Asistent.schedule.models import AISchedule
from Asistent.models import PromptTemplate
from blog.models import Category


class Command(BaseCommand):
    help = 'Создаёт управляемое расписание для автопостинга всех гороскопов'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--time',
            type=str,
            default='10:00',
            help='Время запуска в формате HH:MM (по умолчанию: 10:00)'
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='Обновить существующее расписание вместо создания нового'
        )
    
    def handle(self, *args, **options):
        time_str = options['time']
        hour, minute = map(int, time_str.split(':'))
        
        # Находим шаблон гороскопов
        template = PromptTemplate.objects.filter(
            name='DAILY_HOROSCOPE_PROMPT',
            is_active=True
        ).first()
        
        if not template:
            self.stdout.write(self.style.ERROR('❌ Шаблон DAILY_HOROSCOPE_PROMPT не найден!'))
            return
        
        # Находим категорию
        category = Category.objects.filter(title__icontains='гороскоп').first()
        if not category:
            # Пробуем найти категорию "Интеллектуальные Прогнозы"
            category = Category.objects.filter(title__icontains='прогноз').first()
        
        if not category:
            self.stdout.write(self.style.ERROR('❌ Категория гороскопов не найдена!'))
            return
        
        schedule_name = f'🔮 Автопостинг всех гороскопов ({time_str})'
        
        # Создаём или обновляем расписание
        if options['update']:
            schedule = AISchedule.objects.filter(name__startswith='🔮 Автопостинг всех гороскопов').first()
            if schedule:
                schedule.cron_expression = f'{minute} {hour} * * *'
                schedule.payload_template = {
                    'target_date_offset': 1,
                    'publish_mode': 'published',
                    'base_tags': ['гороскоп', 'прогноз на завтра'],
                }
                schedule.save()
                self.stdout.write(self.style.SUCCESS(f'✅ Обновлено расписание: {schedule.name}'))
                return
        
        schedule, created = AISchedule.objects.get_or_create(
            name=schedule_name,
            defaults={
                'strategy_type': 'prompt',
                'prompt_template': template,
                'category': category,
                'schedule_kind': 'cron',
                'cron_expression': f'{minute} {hour} * * *',
                'articles_per_run': 12,
                'is_active': True,
                'payload_template': {
                    'target_date_offset': 1,
                    'publish_mode': 'published',
                    'base_tags': ['гороскоп', 'прогноз на завтра'],
                }
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'✅ Создано расписание: {schedule.name}'))
            self.stdout.write(f'   CRON: {schedule.cron_expression}')
            self.stdout.write(f'   Статей за раз: {schedule.articles_per_run}')
        else:
            self.stdout.write(self.style.WARNING(f'⚠️ Расписание уже существует: {schedule.name}'))
            self.stdout.write(f'   Используйте --update для обновления')

