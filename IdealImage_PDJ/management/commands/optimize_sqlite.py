"""
Команда для оптимизации SQLite базы данных
Включает WAL режим и другие оптимизации
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Оптимизирует SQLite базу данных для лучшей производительности и предотвращения блокировок'

    def handle(self, *args, **options):
        self.stdout.write('Оптимизация SQLite базы данных...')
        
        with connection.cursor() as cursor:
            # Включить WAL режим (Write-Ahead Logging) - позволяет читать во время записи
            cursor.execute('PRAGMA journal_mode=WAL;')
            result = cursor.fetchone()
            self.stdout.write(f'  ✓ Journal mode: {result[0]}')
            
            # Установить синхронизацию в NORMAL (быстрее, но все еще безопасно)
            cursor.execute('PRAGMA synchronous=NORMAL;')
            self.stdout.write('  ✓ Synchronous mode: NORMAL')
            
            # Увеличить размер кэша (10000 страниц = ~40MB)
            cursor.execute('PRAGMA cache_size=10000;')
            self.stdout.write('  ✓ Cache size: 10000 страниц')
            
            # Увеличить таймаут занятости
            cursor.execute('PRAGMA busy_timeout=60000;')  # 60 секунд
            self.stdout.write('  ✓ Busy timeout: 60 секунд')
            
            # Оптимизировать временные файлы в памяти
            cursor.execute('PRAGMA temp_store=MEMORY;')
            self.stdout.write('  ✓ Temp store: MEMORY')
            
            # Автоматическая очистка (автоочистка WAL файлов)
            cursor.execute('PRAGMA wal_autocheckpoint=1000;')
            self.stdout.write('  ✓ WAL autocheckpoint: 1000')
            
            # Оптимизировать базу (defragmentation)
            cursor.execute('VACUUM;')
            self.stdout.write('  ✓ Выполнена дефрагментация (VACUUM)')
            
            # Анализ для обновления статистики запросов
            cursor.execute('ANALYZE;')
            self.stdout.write('  ✓ Обновлена статистика (ANALYZE)')
        
        self.stdout.write(self.style.SUCCESS('\n✅ SQLite база данных оптимизирована!'))
        self.stdout.write(self.style.WARNING('\n⚠️  Рекомендация: Для высоконагруженных сайтов лучше использовать PostgreSQL'))

