"""
Команда для настройки ежедневной генерации всех 12 гороскопов в 10:00
Создает одно расписание AISchedule, которое генерирует все 12 гороскопов сразу
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from Asistent.models import AISchedule, PromptTemplate
from blog.models import Category
from django.utils import timezone
from datetime import time
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Настройка ежедневной генерации всех 12 гороскопов в 10:00 через Django-Q'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Пересоздать расписание даже если оно уже существует'
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('  🔮 НАСТРОЙКА ЕЖЕДНЕВНОЙ ГЕНЕРАЦИИ ГОРОСКОПОВ В 10:00'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        
        # Проверяем шаблон промпта
        self.stdout.write('🔍 Проверка шаблона промпта...')
        prompt_template = PromptTemplate.objects.filter(
            name="DAILY_HOROSCOPE_PROMPT",
            is_active=True
        ).first()
        
        if not prompt_template:
            self.stdout.write(self.style.ERROR(
                '❌ Шаблон промпта "DAILY_HOROSCOPE_PROMPT" не найден или неактивен!'
            ))
            self.stdout.write('   Создайте шаблон промпта в админке: /admin/Asistent/prompttemplate/')
            return
        
        self.stdout.write(self.style.SUCCESS(
            f'✅ Шаблон промпта найден: {prompt_template.name} (ID: {prompt_template.id})'
        ))
        self.stdout.write('')
        
        # Получаем категорию
        try:
            category = Category.objects.get(slug="intellektualnye-prognozy")
        except Category.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                '❌ Категория "intellektualnye-prognozy" не найдена!'
            ))
            return
        
        # Проверяем существующее расписание
        schedule_name = "Генерация всех гороскопов в 10:00"
        existing_schedule = AISchedule.objects.filter(
            name=schedule_name,
            prompt_template=prompt_template
        ).first()
        
        if existing_schedule and not force:
            self.stdout.write(self.style.WARNING(
                f'⚠️ Расписание уже существует: {schedule_name} (ID: {existing_schedule.id})'
            ))
            self.stdout.write('   Используйте --force для пересоздания')
            self.stdout.write('')
            self.stdout.write(f'   Текущий статус: {"✅ Активно" if existing_schedule.is_active else "⏸️ Неактивно"}')
            self.stdout.write(f'   Следующий запуск: {existing_schedule.next_run}')
            return
        
        # Удаляем старое расписание если force
        if force and existing_schedule:
            existing_schedule.delete()
            self.stdout.write(self.style.WARNING(
                f'🗑️ Удалено старое расписание: {schedule_name}'
            ))
            self.stdout.write('')
        
        # Создаем новое расписание
        self.stdout.write('📅 Создание расписания...')
        schedule = AISchedule.objects.create(
            name=schedule_name,
            strategy_type="prompt",
            prompt_template=prompt_template,
            category=category,
            schedule_kind="cron",
            cron_expression="0 10 * * *",  # Каждый день в 10:00
            scheduled_time=time(10, 0),
            articles_per_run=12,  # Все 12 гороскопов за один запуск
            is_active=True,
            payload_template={
                "target_date_offset": 1,  # Прогноз на завтра
                "publish_mode": "published",  # Сразу публикуем
                "title_template": "{zodiac_sign} — гороскоп на {horoscope_target_date_display}",
                "description_template": "Ежедневный гороскоп для {zodiac_sign} на {horoscope_target_date_display}.",
                "base_tags": ["гороскоп", "прогноз на завтра"],
                "prompt_name": "DAILY_HOROSCOPE_PROMPT",
                "image_prompt_name": "HOROSCOPE_IMAGE_PROMPT",
                "generation_delay": 5,  # Задержка 5 секунд между генерациями
                "retry_count": 2,
                "retry_delay": 60,
            }
        )
        
        # Вычисляем следующий запуск
        schedule.update_next_run()
        
        self.stdout.write(self.style.SUCCESS(
            f'✅ Расписание создано: {schedule.name} (ID: {schedule.id})'
        ))
        self.stdout.write(f'   📊 Статей за запуск: {schedule.articles_per_run}')
        self.stdout.write(f'   ⏰ Время запуска: {schedule.scheduled_time}')
        self.stdout.write(f'   📅 Следующий запуск: {schedule.next_run}')
        self.stdout.write('')
        
        # Синхронизируем с Django-Q
        self.stdout.write('🔄 Синхронизация с Django-Q...')
        try:
            call_command('sync_schedules', '--force')
            self.stdout.write(self.style.SUCCESS(
                '✅ Расписание синхронизировано с Django-Q'
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f'❌ Ошибка синхронизации: {e}'
            ))
            logger.error(f"Ошибка синхронизации расписаний: {e}", exc_info=True)
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('  ✅ НАСТРОЙКА ЗАВЕРШЕНА'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        self.stdout.write('📋 Проверьте расписание:')
        self.stdout.write('   - Админка: /admin/Asistent/aischedule/')
        self.stdout.write('   - Django-Q: /admin/django_q/schedule/')
        self.stdout.write('')
        self.stdout.write('⚠️ ВАЖНО: Убедитесь, что Django-Q запущен:')
        self.stdout.write('   python manage.py qcluster')
        self.stdout.write('')
        self.stdout.write('📝 Для ручного запуска:')
        self.stdout.write(f'   python manage.py generate_all_horoscopes_now')

