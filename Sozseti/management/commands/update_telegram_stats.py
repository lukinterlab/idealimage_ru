"""
Management команда для обновления статистики Telegram каналов
"""
from django.core.management.base import BaseCommand
from Sozseti.api_integrations.telegram_manager import TelegramChannelManager


class Command(BaseCommand):
    help = 'Обновляет статистику подписчиков для всех Telegram каналов'
    
    def handle(self, *args, **options):
        self.stdout.write('[*] Обновление статистики Telegram каналов...\n')
        
        telegram = TelegramChannelManager()
        
        try:
            updated = telegram.update_all_channels_statistics()
            
            if updated > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\n[OK] Статистика обновлена для {updated} каналов'
                    )
                )
                
                # Показываем топ-5 каналов
                from Sozseti.models import SocialChannel
                
                top_channels = SocialChannel.objects.filter(
                    platform__name='telegram',
                    is_active=True
                ).order_by('-subscribers_count')[:5]
                
                self.stdout.write('\nТОП-5 каналов по подписчикам:')
                for i, channel in enumerate(top_channels, 1):
                    self.stdout.write(
                        f'  {i}. {channel.channel_name}: {channel.subscribers_count} подписчиков'
                    )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        '\n[WARN] Не удалось обновить статистику каналов'
                    )
                )
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f'\n[ERROR] Ошибка обновления статистики: {e}'
                )
            )
        
        self.stdout.write('\n' + '='*50)
        self.stdout.write('[COMPLETE] Обновление завершено!')

