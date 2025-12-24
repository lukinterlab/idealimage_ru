"""
Django management команда для запуска всех сервисов разработки
Использование: python manage.py rundev
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
import subprocess
import sys
import signal
import os
from pathlib import Path


class Command(BaseCommand):
    help = 'Запускает Django сервер + Celery Worker + Celery Beat автоматически'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-celery',
            action='store_true',
            help='Запустить только Django без Celery',
        )
        parser.add_argument(
            '--no-beat',
            action='store_true',
            help='Не запускать Celery Beat',
        )

    def handle(self, *args, **options):
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('  IdealImage.ru - Development Server'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')
        
        processes = []
        
        try:
            # Создаем папку для логов
            log_dir = Path('logs')
            log_dir.mkdir(exist_ok=True)
            
            if not options['no_celery']:
                # Запуск Celery Worker
                self.stdout.write(self.style.WARNING('  [1/3] Starting Celery Worker...'))
                
                worker_log = log_dir / 'celery_worker.log'
                worker_process = subprocess.Popen(
                    [sys.executable, '-m', 'celery', '-A', 'IdealImage_PDJ', 
                     'worker', '-l', 'info', '--pool=solo'],
                    stdout=open(worker_log, 'w'),
                    stderr=subprocess.STDOUT
                )
                processes.append(('Celery Worker', worker_process))
                self.stdout.write(self.style.SUCCESS(f'        OK - PID: {worker_process.pid}'))
                self.stdout.write(self.style.WARNING(f'        Log: {worker_log}'))
                self.stdout.write('')
                
                import time
                time.sleep(2)
                
                # Запуск Celery Beat
                if not options['no_beat']:
                    self.stdout.write(self.style.WARNING('  [2/3] Starting Celery Beat...'))
                    
                    beat_log = log_dir / 'celery_beat.log'
                    beat_process = subprocess.Popen(
                        [sys.executable, '-m', 'celery', '-A', 'IdealImage_PDJ', 
                         'beat', '-l', 'info'],
                        stdout=open(beat_log, 'w'),
                        stderr=subprocess.STDOUT
                    )
                    processes.append(('Celery Beat', beat_process))
                    self.stdout.write(self.style.SUCCESS(f'        OK - PID: {beat_process.pid}'))
                    self.stdout.write(self.style.WARNING(f'        Log: {beat_log}'))
                    self.stdout.write('')
                    
                    time.sleep(2)
            
            # Запуск Django
            self.stdout.write(self.style.WARNING('  [3/3] Starting Django Server...'))
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('=' * 60))
            self.stdout.write(self.style.SUCCESS('  ALL SERVICES RUNNING!'))
            self.stdout.write(self.style.SUCCESS('=' * 60))
            self.stdout.write('')
            self.stdout.write(self.style.HTTP_INFO('  Web:      http://127.0.0.1:8000'))
            self.stdout.write(self.style.HTTP_INFO('  Admin:    http://127.0.0.1:8000/admin/'))
            self.stdout.write(self.style.HTTP_INFO('  AI Panel: http://127.0.0.1:8000/asistent/admin-panel/'))
            self.stdout.write('')
            
            if processes:
                self.stdout.write(self.style.WARNING('  Logs:'))
                for name, proc in processes:
                    if name == 'Celery Worker':
                        self.stdout.write(self.style.WARNING('    - logs/celery_worker.log'))
                    elif name == 'Celery Beat':
                        self.stdout.write(self.style.WARNING('    - logs/celery_beat.log'))
                self.stdout.write('')
            
            self.stdout.write(self.style.SUCCESS('=' * 60))
            self.stdout.write(self.style.WARNING('  Press Ctrl+C to stop all services'))
            self.stdout.write(self.style.SUCCESS('=' * 60))
            self.stdout.write('')
            
            # Регистрируем обработчик сигналов
            def signal_handler(sig, frame):
                self.stdout.write('')
                self.stdout.write(self.style.WARNING('\nStopping all services...'))
                for name, proc in processes:
                    if proc.poll() is None:
                        self.stdout.write(f'  Stopping {name}...')
                        proc.terminate()
                        try:
                            proc.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                self.stdout.write(self.style.SUCCESS('\nAll services stopped!'))
                sys.exit(0)
            
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            # Запускаем Django сервер (блокирующий вызов)
            call_command('runserver')
            
        except KeyboardInterrupt:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('\nStopping all services...'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\nError: {e}'))
        finally:
            # Останавливаем все процессы
            for name, proc in processes:
                if proc.poll() is None:
                    self.stdout.write(f'  Stopping {name}...')
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
            
            if processes:
                self.stdout.write(self.style.SUCCESS('\nAll services stopped!'))

