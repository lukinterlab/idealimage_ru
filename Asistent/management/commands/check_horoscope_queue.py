"""
Команда для диагностики очереди гороскопов и блокировок
Обновлена для работы с новой системой QueueManager
"""
from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.utils import timezone
from datetime import datetime, timedelta, date
from Asistent.models import AISchedule
import json


class Command(BaseCommand):
    help = 'Диагностика очереди гороскопов и блокировок (новая система QueueManager)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-lock',
            action='store_true',
            help='Принудительно освободить зависшую блокировку'
        )
        parser.add_argument(
            '--clear-queue',
            action='store_true',
            help='Очистить очередь гороскопов'
        )

    def handle(self, *args, **options):
        # Используем новую систему QueueManager
        from Asistent.generators.queue import QueueManager
        
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('  🔍 ДИАГНОСТИКА ОЧЕРЕДИ ГОРОСКОПОВ'))
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write('')
        
        # Создаём менеджер очереди для гороскопов (имя очереди как в UniversalContentGenerator)
        queue_manager = QueueManager(queue_name='horoscope_generation')
        
        # Получаем статус через новый API
        status = queue_manager.get_queue_status()
        
        queue_key = queue_manager.queue_key
        lock_key = queue_manager.lock_key
        
        # 1. Проверка очереди
        self.stdout.write(self.style.SUCCESS('[1/3] СОСТОЯНИЕ ОЧЕРЕДИ'))
        self.stdout.write('-' * 80)
        
        queue = status.get('tasks_in_queue', [])
        if queue:
            self.stdout.write(f'📋 В очереди: {len(queue)} расписаний')
            self.stdout.write('')
            for idx, schedule_id in enumerate(queue, 1):
                try:
                    schedule = AISchedule.objects.get(id=schedule_id)
                    self.stdout.write(f'   {idx}. ID={schedule_id} - {schedule.name}')
                except AISchedule.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f'   {idx}. ID={schedule_id} - ⚠️ Расписание не найдено'))
        else:
            self.stdout.write('📭 Очередь пуста')
        
        self.stdout.write('')
        self.stdout.write(f'   Ключ очереди: {queue_key}')
        self.stdout.write('')
        
        # 2. Проверка блокировки
        self.stdout.write(self.style.SUCCESS('[2/3] СОСТОЯНИЕ БЛОКИРОВКИ'))
        self.stdout.write('-' * 80)
        
        lock_value = status.get('lock_holder')
        heartbeat_key = f"{lock_key}:heartbeat"
        last_heartbeat = status.get('last_heartbeat')
        
        if lock_value:
            self.stdout.write(self.style.WARNING(f'🔒 Блокировка ЗАНЯТА'))
            self.stdout.write(f'   Держит задачу: ID={lock_value}')
            
            try:
                schedule = AISchedule.objects.get(id=lock_value)
                self.stdout.write(f'   Расписание: {schedule.name}')
            except AISchedule.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'   ⚠️ Расписание ID={lock_value} не найдено!'))
            
            # Проверяем heartbeat (в новой системе используется timestamp, а не datetime)
            if last_heartbeat is not None:
                current_time = timezone.now().timestamp()
                time_since_heartbeat = current_time - last_heartbeat
                
                heartbeat_time = datetime.fromtimestamp(last_heartbeat)
                self.stdout.write(f'   Последний heartbeat: {heartbeat_time.strftime("%H:%M:%S")}')
                self.stdout.write(f'   Прошло времени: {int(time_since_heartbeat)} сек')
                
                if time_since_heartbeat > 180:  # 3 минуты (как в QueueManager)
                    self.stdout.write(self.style.ERROR(f'   ⚠️ БЛОКИРОВКА ЗАВИСЛА! (heartbeat не обновлялся {int(time_since_heartbeat)} сек)'))
                    if options['clear_lock']:
                        cache.delete(lock_key)
                        cache.delete(heartbeat_key)
                        self.stdout.write(self.style.SUCCESS('   ✅ Блокировка принудительно освобождена'))
                    else:
                        self.stdout.write(self.style.WARNING('   💡 Запустите с --clear-lock для освобождения'))
                elif time_since_heartbeat > 120:
                    self.stdout.write(self.style.WARNING(f'   ⚠️ Подозрение на зависание (heartbeat не обновлялся {int(time_since_heartbeat)} сек)'))
                else:
                    self.stdout.write(self.style.SUCCESS('   ✅ Блокировка активна (heartbeat обновляется)'))
            else:
                self.stdout.write(self.style.WARNING('   ⚠️ Heartbeat не найден'))
                # Проверяем TTL блокировки
                ttl = cache.ttl(lock_key)
                if ttl and ttl > 0:
                    self.stdout.write(f'   TTL блокировки: {ttl} сек (истечёт через {ttl} сек)')
                    if options['clear_lock']:
                        cache.delete(lock_key)
                        cache.delete(heartbeat_key)
                        self.stdout.write(self.style.SUCCESS('   ✅ Блокировка принудительно освобождена'))
                    else:
                        self.stdout.write(self.style.WARNING('   💡 Запустите с --clear-lock для освобождения'))
                else:
                    self.stdout.write(self.style.WARNING('   ⚠️ TTL не определён'))
        else:
            self.stdout.write(self.style.SUCCESS('🔓 Блокировка СВОБОДНА'))
        
        self.stdout.write('')
        self.stdout.write(f'   Ключ блокировки: {lock_key}')
        
        self.stdout.write('')
        
        # 3. Проверка GigaChat блокировки
        self.stdout.write(self.style.SUCCESS('[3/3] СОСТОЯНИЕ GIGACHAT БЛОКИРОВКИ'))
        self.stdout.write('-' * 80)
        
        gigachat_lock_key = "gigachat_request_lock"
        gigachat_lock = cache.get(gigachat_lock_key)
        
        if gigachat_lock:
            ttl = cache.ttl(gigachat_lock_key)
            self.stdout.write(self.style.WARNING(f'🔒 GigaChat блокировка ЗАНЯТА'))
            if ttl and ttl > 0:
                self.stdout.write(f'   TTL: {ttl} сек (истечёт через {ttl} сек)')
            else:
                self.stdout.write('   TTL: не определён')
        else:
            self.stdout.write(self.style.SUCCESS('🔓 GigaChat блокировка СВОБОДНА'))
        
        self.stdout.write('')
        
        # Рекомендации
        self.stdout.write(self.style.SUCCESS('💡 РЕКОМЕНДАЦИИ'))
        self.stdout.write('-' * 80)
        
        if lock_value and last_heartbeat is not None:
            current_time = timezone.now().timestamp()
            time_since_heartbeat = current_time - last_heartbeat
            if time_since_heartbeat > 180:
                self.stdout.write(self.style.WARNING('1. Блокировка зависла - освободите её: python manage.py check_horoscope_queue --clear-lock'))
        
        if queue and not lock_value:
            self.stdout.write('2. Очередь не пуста, но блокировка свободна - задачи должны начать выполняться')
        
        if not queue and lock_value:
            self.stdout.write(self.style.WARNING('3. Очередь пуста, но блокировка занята - возможно зависание'))
        
        if options['clear_queue']:
            cache.delete(queue_key)
            self.stdout.write(self.style.SUCCESS('✅ Очередь очищена'))
        
        self.stdout.write('')
        self.stdout.write('=' * 80)

