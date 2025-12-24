"""
Команда для просмотра логов GigaChat из базы данных
Использование: python manage.py view_gigachat_logs
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from Asistent.models import SystemLog


class Command(BaseCommand):
    help = 'Просмотр логов GigaChat из базы данных'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Сколько часов назад искать логи (по умолчанию: 24)'
        )
        parser.add_argument(
            '--level',
            type=str,
            default='',
            help='Фильтр по уровню: DEBUG, INFO, WARNING, ERROR, CRITICAL'
        )
        parser.add_argument(
            '--search',
            type=str,
            default='',
            help='Поиск по тексту в сообщении'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Максимум записей (по умолчанию: 50)'
        )

    def handle(self, *args, **options):
        hours = options['hours']
        level = options['level'].upper()
        search = options['search']
        limit = options['limit']
        
        # Временной интервал
        time_threshold = timezone.now() - timedelta(hours=hours)
        
        # Базовый запрос
        logs = SystemLog.objects.filter(
            timestamp__gte=time_threshold
        ).filter(
            message__icontains='gigachat'
        ) | SystemLog.objects.filter(
            timestamp__gte=time_threshold,
            message__icontains='изображение'
        ) | SystemLog.objects.filter(
            timestamp__gte=time_threshold,
            message__icontains='generate_and_save_image'
        )
        
        # Фильтр по уровню
        if level:
            logs = logs.filter(level=level)
        
        # Фильтр по поиску
        if search:
            logs = logs.filter(message__icontains=search)
        
        # Сортировка и лимит
        logs = logs.order_by('-timestamp')[:limit]
        
        # Подсчёт
        total_count = logs.count()
        
        if total_count == 0:
            self.stdout.write(self.style.WARNING(
                f'📭 Логов не найдено за последние {hours} часов'
            ))
            return
        
        self.stdout.write(self.style.SUCCESS(
            f'\n📊 Найдено логов: {total_count} (показаны последние {limit})\n'
        ))
        self.stdout.write(self.style.SUCCESS(f'⏰ Период: последние {hours} часов\n'))
        self.stdout.write('=' * 100 + '\n')
        
        # Вывод логов
        for log in logs:
            # Цвет в зависимости от уровня
            if log.level == 'ERROR' or log.level == 'CRITICAL':
                style = self.style.ERROR
                icon = '❌'
            elif log.level == 'WARNING':
                style = self.style.WARNING
                icon = '⚠️'
            elif log.level == 'INFO':
                style = self.style.SUCCESS
                icon = '✅'
            else:
                style = self.style.MIGRATE_LABEL
                icon = '🔍'
            
            # Время
            time_str = log.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            
            # Заголовок
            self.stdout.write(
                style(f'{icon} [{log.level}] {time_str} | {log.logger_name}')
            )
            
            # Модуль и функция
            if log.module or log.function:
                location = f'   📍 {log.module}'
                if log.function:
                    location += f' → {log.function}()'
                if log.line:
                    location += f' [строка {log.line}]'
                self.stdout.write(self.style.MIGRATE_HEADING(location))
            
            # Сообщение
            self.stdout.write(f'   💬 {log.message}')
            
            # Дополнительные данные (если есть)
            if hasattr(log, 'extra_data') and log.extra_data:
                self.stdout.write(f'   📦 Данные: {log.extra_data}')
            
            self.stdout.write('-' * 100)
        
        # Статистика по уровням
        self.stdout.write('\n📈 СТАТИСТИКА ПО УРОВНЯМ:\n')
        
        levels_stats = SystemLog.objects.filter(
            timestamp__gte=time_threshold,
            message__icontains='gigachat'
        ).values('level').annotate(
            count=models.Count('id')
        ).order_by('-count')
        
        for stat in levels_stats:
            level_name = stat['level']
            count = stat['count']
            
            if level_name in ['ERROR', 'CRITICAL']:
                icon = '❌'
            elif level_name == 'WARNING':
                icon = '⚠️'
            else:
                icon = '✅'
            
            self.stdout.write(f'   {icon} {level_name}: {count}')
        
        self.stdout.write('\n' + '=' * 100)
        
        # Подсказки
        self.stdout.write(self.style.MIGRATE_HEADING('\n💡 ПОЛЕЗНЫЕ КОМАНДЫ:'))
        self.stdout.write('   python manage.py view_gigachat_logs --level ERROR')
        self.stdout.write('   python manage.py view_gigachat_logs --search "пустой путь"')
        self.stdout.write('   python manage.py view_gigachat_logs --hours 1 --limit 20')
        self.stdout.write('')


# Импорт для аннотаций
from django.db import models
























