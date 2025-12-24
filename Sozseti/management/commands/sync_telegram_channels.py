"""
Management команда для синхронизации Telegram каналов с БД
"""
from django.core.management.base import BaseCommand
from Sozseti.api_integrations.telegram_manager import TelegramChannelManager


class Command(BaseCommand):
    help = 'Синхронизирует все 18 Telegram каналов с базой данных'
    
    def handle(self, *args, **options):
        self.stdout.write('[*] Начинаем синхронизацию Telegram каналов...')
        
        telegram = TelegramChannelManager()
        synced_count = telegram.sync_channels_to_db()
        
        self.stdout.write(
            self.style.SUCCESS(f'[OK] Успешно синхронизировано {synced_count} каналов')
        )
        
        # Обновляем статистику
        self.stdout.write('[*] Обновляем статистику каналов...')
        updated = telegram.update_all_channels_statistics()
        
        self.stdout.write(
            self.style.SUCCESS(f'[OK] Статистика обновлена для {updated} каналов')
        )

