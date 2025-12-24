"""
Переопределенная команда runserver - автоматически запускает Django-Q
"""
from django.core.management.commands.runserver import Command as RunserverCommand
from django.conf import settings
import subprocess
import sys
import atexit
import signal


class Command(RunserverCommand):
    help = 'Запускает Django сервер с автоматическим запуском Django-Q worker'
    
    qcluster_process = None
    
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--no-qcluster',
            action='store_true',
            help='Запустить БЕЗ Django-Q (только Django сервер)'
        )
    
    def handle(self, *args, **options):
        """Запуск с автоматическим Django-Q"""
        
        # Проверяем флаг --no-qcluster
        if options.get('no_qcluster'):
            self.stdout.write(self.style.WARNING('⚠ Django-Q отключен (--no-qcluster)'))
            return super().handle(*args, **options)
        
        # Запускаем Django-Q worker
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('  🚀 АВТОЗАПУСК Django + Django-Q'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')
        
        self.start_qcluster()
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('  ✅ Django-Q запущен автоматически!'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('📍 Мониторинг: http://127.0.0.1:8000/admin/django_q/'))
        self.stdout.write(self.style.SUCCESS('💡 Для запуска БЕЗ Django-Q: --no-qcluster'))
        self.stdout.write('')
        
        # Регистрируем очистку при выходе
        atexit.register(self.cleanup_qcluster)
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Запускаем Django сервер (стандартная команда)
        try:
            super().handle(*args, **options)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\n\n⚠ Остановка сервера...'))
            self.cleanup_qcluster()
            raise
    
    def start_qcluster(self):
        """Запуск Django-Q worker в фоновом процессе"""
        self.stdout.write('[1/2] Запуск Django-Q worker...')
        
        try:
            if sys.platform == 'win32':
                # Windows - запускаем в отдельном окне
                self.qcluster_process = subprocess.Popen(
                    [sys.executable, 'manage.py', 'qcluster'],
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
                self.stdout.write(self.style.SUCCESS('   ✓ Django-Q запущен (в отдельном окне)'))
            else:
                # Linux/Mac - запускаем в фоне
                import os
                devnull = open(os.devnull, 'w')
                self.qcluster_process = subprocess.Popen(
                    [sys.executable, 'manage.py', 'qcluster'],
                    stdout=devnull,
                    stderr=devnull,
                    preexec_fn=os.setpgrp  # Отделяем от родительского процесса
                )
                self.stdout.write(self.style.SUCCESS(f'   ✓ Django-Q запущен (PID: {self.qcluster_process.pid})'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ✗ Ошибка запуска Django-Q: {e}'))
            self.stdout.write(self.style.WARNING('   ⚠ Django продолжит работу без Django-Q'))
            self.qcluster_process = None
        
        self.stdout.write('[2/2] Запуск Django сервера...')
    
    def cleanup_qcluster(self):
        """Остановка Django-Q при завершении"""
        if self.qcluster_process and self.qcluster_process.poll() is None:
            self.stdout.write(self.style.WARNING('\n🛑 Остановка Django-Q...'))
            try:
                self.qcluster_process.terminate()
                self.qcluster_process.wait(timeout=5)
                self.stdout.write(self.style.SUCCESS('✓ Django-Q остановлен'))
            except subprocess.TimeoutExpired:
                self.stdout.write(self.style.WARNING('⚠ Принудительная остановка Django-Q...'))
                self.qcluster_process.kill()
                self.stdout.write(self.style.SUCCESS('✓ Django-Q остановлен (force)'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Ошибка остановки Django-Q: {e}'))
    
    def signal_handler(self, signum, frame):
        """Обработчик сигналов для корректной остановки"""
        self.cleanup_qcluster()
        sys.exit(0)

