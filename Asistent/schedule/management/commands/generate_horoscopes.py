"""
Management команда для запуска генерации всех гороскопов.
Использует функцию generate_all_horoscopes() из tasks.py
"""
from django.core.management.base import BaseCommand
from Asistent.schedule.tasks import generate_all_horoscopes
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Генерирует все 12 гороскопов для активных расписаний'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--schedule-id',
            type=int,
            help='ID конкретного расписания для генерации (если не указано - все активные)'
        )
        parser.add_argument(
            '--async',
            action='store_true',
            help='Запустить через Django-Q асинхронно'
        )
    
    def handle(self, *args, **options):
        schedule_id = options.get('schedule_id')
        use_async = options.get('async', False)
        
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('  🔮 ГЕНЕРАЦИЯ ГОРОСКОПОВ'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        
        if use_async:
            # Асинхронный запуск через Django-Q
            from django_q.tasks import async_task
            
            if schedule_id:
                task_id = async_task(
                    'Asistent.schedule.tasks.run_specific_schedule',
                    schedule_id,
                    task_name=f'horoscope:{schedule_id}'
                )
                self.stdout.write(self.style.SUCCESS(
                    f'✅ Задача запущена асинхронно! Task ID: {task_id}'
                ))
                self.stdout.write(f'   Расписание ID: {schedule_id}')
            else:
                task_id = async_task(
                    'Asistent.schedule.tasks.generate_all_horoscopes',
                    task_name='all_horoscopes_batch'
                )
                self.stdout.write(self.style.SUCCESS(
                    f'✅ Задача запущена асинхронно! Task ID: {task_id}'
                ))
                self.stdout.write('   Генерация всех 12 гороскопов')
            
            self.stdout.write('')
            self.stdout.write('   Проверьте статус в Django-Q: /admin/django_q/schedule/')
            return
        
        # Синхронный запуск
        if schedule_id:
            from Asistent.schedule.tasks import run_specific_schedule
            
            self.stdout.write(f'📅 Запуск расписания ID: {schedule_id}')
            self.stdout.write('')
            
            try:
                result = run_specific_schedule(schedule_id)
                
                if result.get('success'):
                    post_id = result.get('post_id')
                    self.stdout.write(self.style.SUCCESS(
                        f'✅ Успешно! Post ID: {post_id}'
                    ))
                else:
                    error = result.get('error') or result.get('reason', 'unknown_error')
                    self.stdout.write(self.style.ERROR(
                        f'❌ Ошибка: {error}'
                    ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f'❌ Исключение: {str(e)}'
                ))
                logger.exception("Ошибка генерации гороскопа")
        else:
            self.stdout.write('📋 Запуск генерации всех гороскопов...')
            self.stdout.write('')
            
            try:
                result = generate_all_horoscopes()
                
                self.stdout.write('')
                self.stdout.write(self.style.SUCCESS('=' * 70))
                
                if result.get('success'):
                    created_posts = result.get('created_posts', [])
                    errors = result.get('errors', [])
                    total = result.get('total', 0)
                    
                    self.stdout.write(self.style.SUCCESS(
                        f'✅ Генерация завершена успешно!'
                    ))
                    self.stdout.write(f'   Создано постов: {len(created_posts)}')
                    self.stdout.write(f'   Всего расписаний: {total}')
                    
                    if created_posts:
                        self.stdout.write('')
                        self.stdout.write('   Созданные посты:')
                        for post_id in created_posts:
                            self.stdout.write(f'      - Post ID: {post_id}')
                    
                    if errors:
                        self.stdout.write('')
                        self.stdout.write(self.style.WARNING(
                            f'⚠️ Ошибки ({len(errors)}):'
                        ))
                        for error in errors[:5]:  # Показываем первые 5
                            if isinstance(error, dict):
                                self.stdout.write(
                                    f'      - {error.get("schedule_name", "Unknown")}: '
                                    f'{error.get("error", "Unknown error")}'
                                )
                            else:
                                self.stdout.write(f'      - {error}')
                else:
                    error = result.get('error', 'unknown_error')
                    self.stdout.write(self.style.ERROR(
                        f'❌ Генерация завершена с ошибками: {error}'
                    ))
                    
                    errors = result.get('errors', [])
                    if errors:
                        self.stdout.write('')
                        self.stdout.write('   Ошибки:')
                        for error in errors[:5]:
                            if isinstance(error, dict):
                                self.stdout.write(
                                    f'      - {error.get("schedule_name", "Unknown")}: '
                                    f'{error.get("error", "Unknown error")}'
                                )
                            else:
                                self.stdout.write(f'      - {error}')
                
                self.stdout.write(self.style.SUCCESS('=' * 70))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f'❌ Критическая ошибка: {str(e)}'
                ))
                logger.exception("Критическая ошибка генерации гороскопов")

