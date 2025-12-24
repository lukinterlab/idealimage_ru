"""
Команда для проверки и автозапуска Django-Q Cluster
"""
import os
import sys
import subprocess
import time
from django.core.management.base import BaseCommand
from django_q.models import Task
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = 'Проверяет работу Django-Q Cluster и запускает его если необходимо'

    def add_arguments(self, parser):
        parser.add_argument(
            '--monitor',
            action='store_true',
            help='Режим мониторинга (проверка каждые 60 секунд)',
        )

    def handle(self, *args, **options):
        monitor_mode = options.get('monitor', False)
        
        if monitor_mode:
            self.stdout.write(self.style.WARNING('🔄 Режим мониторинга Django-Q'))
            self.stdout.write('Проверка каждые 60 секунд. Ctrl+C для выхода.\n')
            
            try:
                while True:
                    self._check_and_start()
                    time.sleep(60)
            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING('\n⚠️ Мониторинг остановлен'))
        else:
            self._check_and_start()

    def _check_and_start(self):
        """Проверяет и запускает Django-Q если необходимо"""
        is_running = self._is_qcluster_running()
        
        if is_running:
            self.stdout.write(self.style.SUCCESS('✅ Django-Q Cluster работает'))
            self._show_stats()
        else:
            self.stdout.write(self.style.ERROR('❌ Django-Q Cluster не запущен'))
            
            # Пытаемся запустить
            if self._start_qcluster():
                self.stdout.write(self.style.SUCCESS('✅ Django-Q Cluster запущен'))
                time.sleep(3)  # Даём время на старт
                
                if self._is_qcluster_running():
                    self.stdout.write(self.style.SUCCESS('✅ Подтверждено: Cluster работает'))
                else:
                    self.stdout.write(self.style.ERROR('❌ Не удалось запустить Cluster'))
                    self.stdout.write('Запустите вручную: python manage.py qcluster')
            else:
                self.stdout.write(self.style.ERROR('❌ Ошибка запуска Cluster'))

    def _is_qcluster_running(self):
        """Проверяет, запущен ли Django-Q Cluster"""
        try:
            # Проверяем наличие недавних задач (последние 5 минут)
            recent_time = timezone.now() - timedelta(minutes=5)
            recent_tasks = Task.objects.filter(
                stopped__gte=recent_time
            ).exists()
            
            # Или активные задачи (выполняются сейчас)
            active_tasks = Task.objects.filter(
                started__isnull=False,
                stopped__isnull=True
            ).exists()
            
            return recent_tasks or active_tasks
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка проверки: {e}'))
            return False

    def _start_qcluster(self):
        """Запускает Django-Q Cluster в фоне"""
        try:
            if sys.platform == 'win32':
                # Windows - в новом окне консоли
                subprocess.Popen(
                    ['python', 'manage.py', 'qcluster'],
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            else:
                # Linux/Mac - в фоне с перенаправлением вывода
                subprocess.Popen(
                    ['python', 'manage.py', 'qcluster'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
            return True
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка запуска: {e}'))
            return False

    def _show_stats(self):
        """Показывает статистику задач"""
        try:
            active = Task.objects.filter(
                started__isnull=False,
                stopped__isnull=True
            ).count()
            
            queued = Task.objects.filter(
                started__isnull=True
            ).count()
            
            today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            completed_today = Task.objects.filter(
                stopped__gte=today_start,
                success=True
            ).count()
            
            self.stdout.write(f'   Выполняется: {active}')
            self.stdout.write(f'   В очереди: {queued}')
            self.stdout.write(f'   Выполнено сегодня: {completed_today}')
        except Exception:
            pass

