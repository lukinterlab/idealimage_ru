"""
Management команда для создания демо-расписаний публикаций
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from Sozseti.models import PublicationSchedule, SocialChannel, SocialPlatform
from blog.models import Category


class Command(BaseCommand):
    help = 'Создаёт демо-расписания для автопубликации'
    
    def handle(self, *args, **options):
        self.stdout.write('[*] Создание демо-расписаний...')
        
        # Получаем Telegram платформу
        try:
            telegram_platform = SocialPlatform.objects.get(name='telegram')
        except SocialPlatform.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('[ERROR] Telegram платформа не найдена. Запустите: python manage.py init_social_platforms')
            )
            return
        
        # Получаем активные Telegram каналы
        telegram_channels = SocialChannel.objects.filter(
            platform=telegram_platform,
            is_active=True
        )
        
        if not telegram_channels.exists():
            self.stdout.write(
                self.style.ERROR('[ERROR] Нет активных Telegram каналов. Запустите: python manage.py sync_telegram_channels')
            )
            return
        
        # Получаем категории
        categories = Category.objects.all()[:3]
        
        if not categories.exists():
            self.stdout.write(
                self.style.ERROR('[ERROR] Нет категорий в блоге')
            )
            return
        
        # Создаём расписания
        schedules_data = [
            {
                'name': 'Ежедневная публикация в главный канал',
                'posting_frequency': 'daily',
                'optimal_times': [10, 14, 19],
                'content_template': '{title}\n\n{description}\n\nЧитать: {url}',
                'hashtags': '#IdealImage #красота #мода',
                'is_active': False,  # Активируем вручную
                'ai_optimization': True,
            },
            {
                'name': 'Красота - 3 раза в день',
                'posting_frequency': '3times_day',
                'optimal_times': [9, 14, 20],
                'content_template': '📝 {title}\n\n{description}...\n\n👉 {url}',
                'hashtags': '#красота #макияж #уход',
                'is_active': False,
                'ai_optimization': True,
            },
            {
                'name': 'Еженедельный дайджест',
                'posting_frequency': 'weekly',
                'optimal_times': [10],
                'content_template': '📰 {title}\n\n{description}\n\nПодробнее: {url}',
                'hashtags': '#дайджест #IdealImage',
                'is_active': False,
                'ai_optimization': False,
            },
        ]
        
        created = 0
        
        for data in schedules_data:
            schedule, is_created = PublicationSchedule.objects.get_or_create(
                name=data['name'],
                defaults={
                    **data,
                    'next_run': timezone.now() + timedelta(hours=1)
                }
            )
            
            if is_created:
                # Добавляем каналы
                if data['name'] == 'Ежедневная публикация в главный канал':
                    main_channel = telegram_channels.filter(channel_id='@ideal_image_ru').first()
                    if main_channel:
                        schedule.channels.add(main_channel)
                elif data['name'] == 'Красота - 3 раза в день':
                    beauty_channels = telegram_channels.filter(channel_type='beauty')
                    schedule.channels.add(*beauty_channels)
                else:
                    # Все каналы
                    schedule.channels.add(*telegram_channels[:5])
                
                # Добавляем категории
                schedule.categories.add(*categories)
                
                created += 1
                self.stdout.write(f'  [+] Создано расписание: {schedule.name}')
        
        self.stdout.write(
            self.style.SUCCESS(f'\n[OK] Создано {created} расписаний')
        )
        
        if created > 0:
            self.stdout.write('\nДля активации:')
            self.stdout.write('1. Откройте /admin/Sozseti/publicationschedule/')
            self.stdout.write('2. Отредактируйте расписания')
            self.stdout.write('3. Установите is_active = True')
            self.stdout.write('4. Django-Q автоматически начнёт публиковать статьи')

