"""
Команда для установки qcluster как системного сервиса
Поддерживает: Linux (systemd), Windows (NSSM)
"""
from django.core.management.base import BaseCommand
from django.conf import settings
import os
import sys
import platform


class Command(BaseCommand):
    help = 'Установка qcluster как системного сервиса (автозапуск)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            default='www-data',
            help='Пользователь для запуска сервиса (только Linux)'
        )
        parser.add_argument(
            '--uninstall',
            action='store_true',
            help='Удалить сервис'
        )

    def handle(self, *args, **options):
        system = platform.system()
        uninstall = options.get('uninstall', False)
        
        self.stdout.write(self.style.SUCCESS('=' * 70))
        if uninstall:
            self.stdout.write(self.style.SUCCESS('  🗑️ УДАЛЕНИЕ СЕРВИСА QCLUSTER'))
        else:
            self.stdout.write(self.style.SUCCESS('  ⚙️ УСТАНОВКА СЕРВИСА QCLUSTER'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        self.stdout.write(f'🖥️ Операционная система: {system}')
        self.stdout.write('')

        if system == 'Linux':
            if uninstall:
                self._uninstall_linux()
            else:
                self._install_linux(options['user'])
        elif system == 'Windows':
            if uninstall:
                self._uninstall_windows()
            else:
                self._install_windows()
        else:
            self.stdout.write(self.style.ERROR(f'❌ Неподдерживаемая ОС: {system}'))
            self.stdout.write('Поддерживаются только Linux и Windows')

    def _install_linux(self, user):
        """Установка systemd service для Linux"""
        self.stdout.write('🐧 Установка для Linux (systemd)...')
        self.stdout.write('')

        # Определяем пути
        project_dir = settings.BASE_DIR
        venv_path = os.path.join(project_dir, 'venv')
        python_path = os.path.join(venv_path, 'bin', 'python')
        manage_py = os.path.join(project_dir, 'manage.py')

        # Проверяем наличие venv
        if not os.path.exists(python_path):
            python_path = sys.executable
            self.stdout.write(self.style.WARNING(
                f'⚠️ Virtualenv не найден, используется системный Python: {python_path}'
            ))

        # Создаем содержимое service файла
        service_content = f"""[Unit]
Description=IdealImage Django-Q Cluster
After=network.target

[Service]
Type=simple
User={user}
WorkingDirectory={project_dir}
Environment="PATH={os.path.dirname(python_path)}:/usr/local/bin:/usr/bin:/bin"
ExecStart={python_path} {manage_py} qcluster
Restart=always
RestartSec=10
StandardOutput=append:/var/log/idealimage-qcluster.log
StandardError=append:/var/log/idealimage-qcluster-error.log

[Install]
WantedBy=multi-user.target
"""

        service_path = '/etc/systemd/system/idealimage-qcluster.service'

        self.stdout.write('📝 Содержимое service файла:')
        self.stdout.write('─' * 70)
        self.stdout.write(service_content)
        self.stdout.write('─' * 70)
        self.stdout.write('')

        # Записываем файл
        self.stdout.write(f'💾 Создание файла: {service_path}')
        
        try:
            with open(service_path, 'w') as f:
                f.write(service_content)
            self.stdout.write(self.style.SUCCESS('  ✓ Файл создан'))
        except PermissionError:
            self.stdout.write(self.style.ERROR('  ✗ Нет прав для создания файла'))
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('📋 РУЧНАЯ УСТАНОВКА:'))
            self.stdout.write('')
            self.stdout.write('1. Создайте файл как root:')
            self.stdout.write(f'   sudo nano {service_path}')
            self.stdout.write('')
            self.stdout.write('2. Вставьте содержимое (показано выше)')
            self.stdout.write('')
            self.stdout.write('3. Выполните команды:')
            self.stdout.write('   sudo systemctl daemon-reload')
            self.stdout.write('   sudo systemctl enable idealimage-qcluster')
            self.stdout.write('   sudo systemctl start idealimage-qcluster')
            self.stdout.write('   sudo systemctl status idealimage-qcluster')
            return

        # Выполняем команды systemctl
        self.stdout.write('')
        self.stdout.write('⚙️ Настройка сервиса...')
        
        commands = [
            ('Перезагрузка systemd', 'sudo systemctl daemon-reload'),
            ('Включение автозапуска', 'sudo systemctl enable idealimage-qcluster'),
            ('Запуск сервиса', 'sudo systemctl start idealimage-qcluster'),
        ]

        for desc, cmd in commands:
            self.stdout.write(f'  • {desc}...')
            exit_code = os.system(cmd)
            if exit_code == 0:
                self.stdout.write(self.style.SUCCESS('    ✓ Выполнено'))
            else:
                self.stdout.write(self.style.ERROR(f'    ✗ Ошибка (код: {exit_code})'))
                self.stdout.write(f'    Выполните вручную: {cmd}')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('  ✅ УСТАНОВКА ЗАВЕРШЕНА'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        self.stdout.write('📊 Проверка статуса:')
        self.stdout.write('   sudo systemctl status idealimage-qcluster')
        self.stdout.write('')
        self.stdout.write('📋 Управление сервисом:')
        self.stdout.write('   sudo systemctl start idealimage-qcluster   # Запустить')
        self.stdout.write('   sudo systemctl stop idealimage-qcluster    # Остановить')
        self.stdout.write('   sudo systemctl restart idealimage-qcluster # Перезапустить')
        self.stdout.write('')
        self.stdout.write('📝 Логи:')
        self.stdout.write('   sudo journalctl -u idealimage-qcluster -f')
        self.stdout.write('   tail -f /var/log/idealimage-qcluster.log')
        self.stdout.write('')

    def _uninstall_linux(self):
        """Удаление systemd service"""
        self.stdout.write('🗑️ Удаление сервиса...')
        
        commands = [
            ('Остановка сервиса', 'sudo systemctl stop idealimage-qcluster'),
            ('Отключение автозапуска', 'sudo systemctl disable idealimage-qcluster'),
            ('Удаление файла', 'sudo rm /etc/systemd/system/idealimage-qcluster.service'),
            ('Перезагрузка systemd', 'sudo systemctl daemon-reload'),
        ]

        for desc, cmd in commands:
            self.stdout.write(f'  • {desc}...')
            os.system(cmd)

        self.stdout.write(self.style.SUCCESS('✅ Сервис удален'))

    def _install_windows(self):
        """Установка Windows Service используя NSSM"""
        self.stdout.write('🪟 Установка для Windows...')
        self.stdout.write('')

        project_dir = settings.BASE_DIR
        venv_path = os.path.join(project_dir, '.venv')
        python_path = os.path.join(venv_path, 'Scripts', 'python.exe')
        manage_py = os.path.join(project_dir, 'manage.py')

        if not os.path.exists(python_path):
            python_path = sys.executable
            self.stdout.write(self.style.WARNING(
                f'⚠️ Virtualenv не найден, используется системный Python: {python_path}'
            ))

        self.stdout.write(self.style.WARNING('⚠️ Для Windows требуется NSSM (Non-Sucking Service Manager)'))
        self.stdout.write('')
        self.stdout.write('📦 Установка NSSM:')
        self.stdout.write('   1. Скачайте: https://nssm.cc/download')
        self.stdout.write('   2. Распакуйте и добавьте nssm.exe в PATH')
        self.stdout.write('   3. Или используйте: choco install nssm')
        self.stdout.write('')
        self.stdout.write('📋 КОМАНДЫ ДЛЯ УСТАНОВКИ СЕРВИСА:')
        self.stdout.write('─' * 70)
        self.stdout.write('')
        self.stdout.write('1. Откройте PowerShell/CMD как Администратор')
        self.stdout.write('')
        self.stdout.write('2. Установите сервис:')
        self.stdout.write(f'   nssm install IdealImageQCluster "{python_path}" "{manage_py}" qcluster')
        self.stdout.write('')
        self.stdout.write('3. Настройте параметры:')
        self.stdout.write(f'   nssm set IdealImageQCluster AppDirectory "{project_dir}"')
        self.stdout.write(f'   nssm set IdealImageQCluster DisplayName "IdealImage Django-Q Worker"')
        self.stdout.write(f'   nssm set IdealImageQCluster Description "Обработчик фоновых задач AI-агента"')
        self.stdout.write(f'   nssm set IdealImageQCluster Start SERVICE_AUTO_START')
        self.stdout.write('')
        self.stdout.write('4. Запустите сервис:')
        self.stdout.write('   nssm start IdealImageQCluster')
        self.stdout.write('')
        self.stdout.write('5. Проверьте статус:')
        self.stdout.write('   nssm status IdealImageQCluster')
        self.stdout.write('')
        self.stdout.write('─' * 70)
        self.stdout.write('')
        self.stdout.write('📊 Управление сервисом:')
        self.stdout.write('   nssm start IdealImageQCluster    # Запустить')
        self.stdout.write('   nssm stop IdealImageQCluster     # Остановить')
        self.stdout.write('   nssm restart IdealImageQCluster  # Перезапустить')
        self.stdout.write('   nssm status IdealImageQCluster   # Статус')
        self.stdout.write('')
        self.stdout.write('🗑️ Удаление сервиса:')
        self.stdout.write('   nssm stop IdealImageQCluster')
        self.stdout.write('   nssm remove IdealImageQCluster confirm')
        self.stdout.write('')

        # Альтернативный способ - Task Scheduler
        self.stdout.write('📋 АЛЬТЕРНАТИВА: Task Scheduler')
        self.stdout.write('─' * 70)
        self.stdout.write('')
        self.stdout.write('Создайте .bat файл START_QCLUSTER_BACKGROUND.bat:')
        self.stdout.write('')
        bat_content = f'''@echo off
cd /d "{project_dir}"
"{python_path}" manage.py qcluster
'''
        self.stdout.write(bat_content)
        self.stdout.write('')
        self.stdout.write('Затем добавьте в Task Scheduler:')
        self.stdout.write('   Trigger: At system startup')
        self.stdout.write('   Action: Run START_QCLUSTER_BACKGROUND.bat')
        self.stdout.write('   Settings: Run with highest privileges')
        self.stdout.write('')

    def _uninstall_windows(self):
        """Удаление Windows Service"""
        self.stdout.write('🗑️ Удаление сервиса Windows...')
        self.stdout.write('')
        self.stdout.write('Выполните команды:')
        self.stdout.write('   nssm stop IdealImageQCluster')
        self.stdout.write('   nssm remove IdealImageQCluster confirm')
        self.stdout.write('')

