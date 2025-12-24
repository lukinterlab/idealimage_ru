"""
Тестовая команда для проверки работы Django-Q
"""
from django.core.management.base import BaseCommand
from django_q.tasks import async_task, result
from django_q.models import Task
import time


class Command(BaseCommand):
    help = 'Тестирование Django-Q'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('  ТЕСТИРОВАНИЕ Django-Q'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')
        
        # Тест 1: Проверка подключения к БД
        self.stdout.write('[1/4] Проверка подключения к БД Django-Q...')
        try:
            task_count = Task.objects.count()
            self.stdout.write(self.style.SUCCESS(f'   OK. Задач в БД: {task_count}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   Ошибка: {e}'))
            return
        
        # Тест 2: Создание простой задачи
        self.stdout.write('[2/4] Создание тестовой задачи...')
        try:
            task_id = async_task(
                'Asistent.management.commands.test_djangoq.test_function',
                'Hello Django-Q!'
            )
            self.stdout.write(self.style.SUCCESS(f'   Задача создана. ID: {task_id}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   Ошибка: {e}'))
            return
        
        # Тест 3: Проверка статуса задачи
        self.stdout.write('[3/4] Проверка статуса задачи...')
        self.stdout.write('   Ожидание выполнения (до 10 секунд)...')
        
        for i in range(10):
            time.sleep(1)
            try:
                task = Task.objects.get(id=task_id)
                if task.success:
                    self.stdout.write(self.style.SUCCESS(f'   Задача выполнена успешно за {i+1} секунд'))
                    self.stdout.write(f'   Результат: {task.result}')
                    break
                elif task.success is False:
                    self.stdout.write(self.style.ERROR(f'   Задача завершилась с ошибкой'))
                    self.stdout.write(f'   Ошибка: {task.result}')
                    break
            except Task.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'   Задача еще не появилась в БД (попытка {i+1}/10)'))
        else:
            self.stdout.write(self.style.WARNING('   ВНИМАНИЕ: Задача не выполнена за 10 секунд'))
            self.stdout.write('   ВАЖНО: Убедитесь что запущен qcluster: python manage.py qcluster')
        
        # Тест 4: Статистика
        self.stdout.write('[4/4] Общая статистика Django-Q...')
        total = Task.objects.count()
        success = Task.objects.filter(success=True).count()
        failed = Task.objects.filter(success=False).count()
        pending = Task.objects.filter(success__isnull=True).count()
        
        self.stdout.write(f'   Всего задач: {total}')
        self.stdout.write(f'   Успешных: {success}')
        self.stdout.write(f'   С ошибками: {failed}')
        self.stdout.write(f'   В ожидании: {pending}')
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('  ТЕСТИРОВАНИЕ ЗАВЕРШЕНО'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')
        
        if pending > 0:
            self.stdout.write(self.style.WARNING('ВНИМАНИЕ: Есть задачи в ожидании!'))
            self.stdout.write('  Запустите Django-Q worker:')
            self.stdout.write('  python manage.py qcluster')
            self.stdout.write('  или')
            self.stdout.write('  START_ALL_NEW.bat')


def test_function(message):
    """Тестовая функция для Django-Q"""
    return f"Получено сообщение: {message}"

