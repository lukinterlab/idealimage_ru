"""
Management команда для инициализации всех социальных платформ
"""
from django.core.management.base import BaseCommand
from Sozseti.models import SocialPlatform


class Command(BaseCommand):
    help = 'Инициализирует все социальные платформы в базе данных'
    
    def handle(self, *args, **options):
        self.stdout.write('[*] Инициализация социальных платформ...')
        
        platforms_data = [
            {
                'name': 'telegram',
                'is_active': True,
                'requires_vpn': False,
                'icon_class': 'fab fa-telegram',
            },
            {
                'name': 'vk',
                'is_active': False,  # Активируем после настройки токена
                'requires_vpn': False,
                'icon_class': 'fab fa-vk',
            },
            {
                'name': 'pinterest',
                'is_active': False,
                'requires_vpn': False,
                'icon_class': 'fab fa-pinterest',
            },
            {
                'name': 'rutube',
                'is_active': False,
                'requires_vpn': False,
                'icon_class': 'fas fa-video',
            },
            {
                'name': 'dzen',
                'is_active': False,
                'requires_vpn': False,
                'icon_class': 'fas fa-newspaper',
            },
            {
                'name': 'whatsapp',
                'is_active': True,  # Share button работает всегда
                'requires_vpn': False,
                'icon_class': 'fab fa-whatsapp',
            },
            {
                'name': 'max',
                'is_active': False,  # API в разработке
                'requires_vpn': False,
                'icon_class': 'fas fa-comment',
            },
            {
                'name': 'instagram',
                'is_active': False,
                'requires_vpn': True,
                'icon_class': 'fab fa-instagram',
            },
            {
                'name': 'facebook',
                'is_active': False,
                'requires_vpn': True,
                'icon_class': 'fab fa-facebook',
            },
            {
                'name': 'youtube',
                'is_active': False,
                'requires_vpn': True,
                'icon_class': 'fab fa-youtube',
            },
        ]
        
        created = 0
        updated = 0
        
        for data in platforms_data:
            platform, is_created = SocialPlatform.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            
            if is_created:
                created += 1
                self.stdout.write(f'  [+] Создана платформа: {platform.get_name_display()}')
            else:
                # Обновляем иконку если изменилась
                if platform.icon_class != data['icon_class']:
                    platform.icon_class = data['icon_class']
                    platform.save()
                    updated += 1
                    self.stdout.write(f'  [~] Обновлена платформа: {platform.get_name_display()}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n[OK] Создано: {created}, Обновлено: {updated}'
            )
        )
        
        # Синхронизируем Telegram каналы
        self.stdout.write('\n[*] Синхронизация Telegram каналов...')
        
        from Sozseti.api_integrations.telegram_manager import TelegramChannelManager
        
        telegram = TelegramChannelManager()
        synced = telegram.sync_channels_to_db()
        
        self.stdout.write(
            self.style.SUCCESS(f'[OK] Синхронизировано {synced} Telegram каналов')
        )
        
        # VK исключен (глючит, не используется)
        # self.stdout.write('\n[*] Синхронизация VK группы...')
        # from Sozseti.api_integrations.vk_manager import VKManager
        # vk = VKManager()
        # vk_synced = vk.sync_groups_to_db()
        self.stdout.write('\n[SKIP] VK платформа исключена из использования')
        
        # Синхронизируем Rutube
        self.stdout.write('\n[*] Синхронизация Rutube канала...')
        
        from Sozseti.api_integrations.rutube_manager import RutubeManager
        
        rutube = RutubeManager()
        rutube_synced = rutube.sync_channel_to_db()
        
        if rutube_synced > 0:
            self.stdout.write(
                self.style.SUCCESS(f'[OK] Синхронизирован Rutube канал')
            )
        else:
            self.stdout.write(
                self.style.WARNING('[WARN] Rutube не настроен - добавьте RUTUBE_API_KEY в .env')
            )
        
        # Синхронизируем Dzen
        self.stdout.write('\n[*] Синхронизация Dzen канала...')
        
        from Sozseti.api_integrations.dzen_manager import DzenManager
        
        dzen = DzenManager()
        dzen_synced = dzen.sync_channel_to_db()
        
        if dzen_synced > 0:
            self.stdout.write(
                self.style.SUCCESS(f'[OK] Синхронизирован Dzen канал')
            )
        else:
            self.stdout.write(
                self.style.WARNING('[WARN] Dzen не настроен - добавьте DZEN_TOKEN в .env')
            )
        
        self.stdout.write('\n' + '='*50)
        self.stdout.write(
            self.style.SUCCESS('[COMPLETE] Инициализация завершена!')
        )
        self.stdout.write('\nСледующие шаги:')
        self.stdout.write('1. Настройте API токены в .env файле')
        self.stdout.write('2. Запустите: python manage.py sync_telegram_channels')
        self.stdout.write('3. Откройте админку: /admin/Sozseti/')
        self.stdout.write('4. Проверьте каналы и активируйте нужные платформы')

