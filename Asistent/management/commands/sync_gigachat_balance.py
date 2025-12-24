"""
Management команда для синхронизации балансов GigaChat моделей
Использование: python manage.py sync_gigachat_balance
"""
from django.core.management.base import BaseCommand
from Asistent.gigachat_api import get_gigachat_client
from Asistent.models import GigaChatUsageStats
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Синхронизирует балансы всех моделей GigaChat с API'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('🔄 Синхронизация балансов GigaChat...'))
        
        try:
            # Получаем клиент
            client = get_gigachat_client()
            
            # Получаем балансы через API
            balances = client.get_balance()
            
            if not balances:
                self.stdout.write(self.style.ERROR('❌ Не удалось получить балансы от API'))
                return
            
            # Обновляем статистику для каждой модели
            updated_count = 0
            
            for model_name, tokens_remaining in balances.items():
                stats, created = GigaChatUsageStats.objects.get_or_create(
                    model_name=model_name,
                    defaults={
                        'tokens_remaining': tokens_remaining,
                        'total_requests': 0,
                        'successful_requests': 0,
                        'failed_requests': 0,
                    }
                )
                
                if not created:
                    # Обновляем баланс
                    stats.tokens_remaining = tokens_remaining
                    stats.save()
                
                updated_count += 1
                
                # Форматированный вывод
                tokens_formatted = f"{tokens_remaining:,}".replace(',', ' ')
                self.stdout.write(
                    self.style.SUCCESS(f'✅ {model_name}: {tokens_formatted} токенов')
                )
            
            self.stdout.write(
                self.style.SUCCESS(f'\n🎉 Успешно обновлено {updated_count} моделей!')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Ошибка синхронизации: {e}')
            )
            logger.error(f"Ошибка sync_gigachat_balance: {e}", exc_info=True)

