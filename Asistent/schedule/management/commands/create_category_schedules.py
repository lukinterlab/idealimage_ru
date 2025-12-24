"""
Management команда для создания расписаний автопостинга по категориям.
"""
from django.core.management.base import BaseCommand
from Asistent.schedule.models import AISchedule
from Asistent.models import PromptTemplate
from blog.models import Category


class Command(BaseCommand):
    help = 'Создаёт расписания для автопостинга по категориям'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--mode',
            choices=['batch', 'separate'],
            default='separate',
            help='Режим: batch (все сразу) или separate (с интервалом 15 мин)'
        )
        parser.add_argument(
            '--time',
            default='10:00',
            help='Время запуска (HH:MM)'
        )
        parser.add_argument(
            '--template',
            type=str,
            help='Имя промпт-шаблона (по умолчанию ищет CATEGORY_ARTICLE_PROMPT)'
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='Обновить существующие расписания'
        )
    
    def handle(self, *args, **options):
        mode = options['mode']
        time_str = options['time']
        hour, minute = map(int, time_str.split(':'))
        template_name = options.get('template') or 'CATEGORY_ARTICLE_PROMPT'
        
        # Находим промпт-шаблон
        template = PromptTemplate.objects.filter(
            name=template_name,
            is_active=True
        ).first()
        
        if not template:
            self.stdout.write(self.style.WARNING(f'⚠️ Шаблон {template_name} не найден!'))
            self.stdout.write('   Попытка создать шаблон автоматически...')
            
            # Пытаемся создать шаблон автоматически
            try:
                from django.core.management import call_command
                call_command('create_category_article_prompt', verbosity=0)
                
                # Повторно ищем шаблон
                template = PromptTemplate.objects.filter(
                    name=template_name,
                    is_active=True
                ).first()
                
                if template:
                    self.stdout.write(self.style.SUCCESS(f'✅ Шаблон {template_name} создан автоматически!'))
                else:
                    self.stdout.write(self.style.ERROR(f'❌ Не удалось создать шаблон {template_name}'))
                    self.stdout.write('   Запустите вручную: python manage.py create_category_article_prompt')
                    return
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Ошибка при создании шаблона: {e}'))
                self.stdout.write('   Запустите вручную: python manage.py create_category_article_prompt')
                return
        
        # Получаем все категории (поле is_active отсутствует в модели Category)
        categories = Category.objects.all()
        
        if not categories.exists():
            self.stdout.write(self.style.ERROR('❌ Нет активных категорий!'))
            return
        
        if mode == 'batch':
            # Одно расписание для всех категорий
            schedule_name = f'📰 Автопостинг по всем категориям ({time_str})'
            
            if options['update']:
                schedule = AISchedule.objects.filter(name=schedule_name).first()
                if schedule:
                    schedule.cron_expression = f'{minute} {hour} * * *'
                    schedule.articles_per_run = categories.count()
                    schedule.save()
                    self.stdout.write(self.style.SUCCESS(f'✅ Обновлено расписание: {schedule.name}'))
                    return
            
            schedule, created = AISchedule.objects.get_or_create(
                name=schedule_name,
                defaults={
                    'strategy_type': 'prompt',
                    'prompt_template': template,
                    'schedule_kind': 'cron',
                    'cron_expression': f'{minute} {hour} * * *',
                    'articles_per_run': categories.count(),
                    'is_active': True,
                    'payload_template': {
                        'target_date_offset': 0,
                        'publish_mode': 'published',
                        'mode': 'all_categories',
                    }
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'✅ Создано расписание: {schedule.name}'))
                self.stdout.write(f'   CRON: {schedule.cron_expression}')
                self.stdout.write(f'   Статей за раз: {schedule.articles_per_run}')
            else:
                self.stdout.write(self.style.WARNING(f'⚠️ Расписание уже существует: {schedule.name}'))
        
        else:
            # Отдельные расписания с интервалом 15 минут
            created_count = 0
            updated_count = 0
            
            for i, category in enumerate(categories):
                schedule_minute = (minute + i * 15) % 60
                schedule_hour = hour + ((minute + i * 15) // 60)
                
                schedule_name = f'📰 {category.title} ({schedule_hour:02d}:{schedule_minute:02d})'
                
                if options['update']:
                    schedule = AISchedule.objects.filter(
                        name__startswith=f'📰 {category.title}'
                    ).first()
                    if schedule:
                        schedule.cron_expression = f'{schedule_minute} {schedule_hour} * * *'
                        schedule.save()
                        updated_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'✅ Обновлено: {schedule.name} (CRON: {schedule.cron_expression})'
                            )
                        )
                        continue
                
                schedule, created = AISchedule.objects.get_or_create(
                    name=schedule_name,
                    defaults={
                        'strategy_type': 'prompt',
                        'prompt_template': template,
                        'category': category,
                        'schedule_kind': 'cron',
                        'cron_expression': f'{schedule_minute} {schedule_hour} * * *',
                        'articles_per_run': 1,
                        'is_active': True,
                        'payload_template': {
                            'target_date_offset': 0,
                            'publish_mode': 'published',
                            'category_id': category.id,
                        }
                    }
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✅ Создано: {schedule.name} (CRON: {schedule.cron_expression})'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'⚠️ Уже существует: {schedule.name}')
                    )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✅ Итого: создано {created_count}, обновлено {updated_count} расписаний'
                )
            )

