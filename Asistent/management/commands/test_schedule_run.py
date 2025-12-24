"""
Команда для тестового запуска расписания с выводом логов
"""
from django.core.management.base import BaseCommand
from Asistent.models import AISchedule
from Asistent.schedule.tasks import run_specific_schedule
import logging
import sys

# Настраиваем логирование для вывода в консоль
logger = logging.getLogger('Asistent.schedule.tasks')
logger.setLevel(logging.INFO)

# Создаём handler для вывода в консоль
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


class Command(BaseCommand):
    help = 'Тестовый запуск расписания с выводом логов'

    def add_arguments(self, parser):
        parser.add_argument(
            'schedule_id',
            type=int,
            help='ID расписания для запуска'
        )

    def handle(self, *args, **options):
        schedule_id = options['schedule_id']
        
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS(f'  🚀 ТЕСТОВЫЙ ЗАПУСК РАСПИСАНИЯ ID={schedule_id}'))
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write('')
        
        # Проверяем существование расписания
        try:
            schedule = AISchedule.objects.get(id=schedule_id)
            self.stdout.write(f'📋 Расписание: {schedule.name}')
            self.stdout.write(f'   Тип: {schedule.get_strategy_type_display()}')
            self.stdout.write(f'   Частота: {schedule.get_posting_frequency_display()}')
            if schedule.cron_expression:
                self.stdout.write(f'   CRON: {schedule.cron_expression}')
            self.stdout.write('')
        except AISchedule.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ Расписание с ID={schedule_id} не найдено!'))
            return
        
        self.stdout.write(self.style.WARNING('⏳ Запуск расписания...'))
        self.stdout.write(self.style.WARNING('   (Это может занять несколько минут)'))
        self.stdout.write('')
        self.stdout.write('-' * 80)
        self.stdout.write('')
        
        try:
            # Запускаем расписание
            result = run_specific_schedule(schedule_id)
            
            self.stdout.write('')
            self.stdout.write('-' * 80)
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('✅ ЗАПУСК ЗАВЕРШЁН'))
            self.stdout.write('')
            self.stdout.write('📊 РЕЗУЛЬТАТ:')
            
            if result.get('success'):
                self.stdout.write(self.style.SUCCESS('   ✅ Успешно'))
                if 'post_id' in result:
                    self.stdout.write(f'   📝 Создана статья ID: {result["post_id"]}')
                if 'message' in result:
                    self.stdout.write(f'   💬 {result["message"]}')
            else:
                self.stdout.write(self.style.ERROR('   ❌ Ошибка'))
                if 'error' in result:
                    self.stdout.write(self.style.ERROR(f'   ⚠️ {result["error"]}'))
            
            self.stdout.write('')
            self.stdout.write('=' * 80)
            
        except Exception as e:
            self.stdout.write('')
            self.stdout.write('-' * 80)
            self.stdout.write('')
            self.stdout.write(self.style.ERROR('❌ КРИТИЧЕСКАЯ ОШИБКА'))
            self.stdout.write(self.style.ERROR(f'   {str(e)}'))
            self.stdout.write('')
            import traceback
            self.stdout.write(self.style.ERROR(traceback.format_exc()))
            self.stdout.write('')
            self.stdout.write('=' * 80)
