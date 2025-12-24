"""
Management команда для добавления новых рекламных мест для детальной страницы статьи
"""
from django.core.management.base import BaseCommand
from advertising.models import AdPlace


class Command(BaseCommand):
    help = 'Добавить новые рекламные места для детальной страницы статьи'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Добавление новых рекламных мест...'))
        
        # Данные для новых рекламных мест
        new_places = [
            {
                'code': 'before_article_content',
                'name': 'Перед текстом статьи',
                'description': 'Рекламный блок перед основным текстом статьи',
                'placement_type': 'banner',
                'recommended_size': '728x90',
                'position_order': 15,
            },
            {
                'code': 'after_comments',
                'name': 'После комментариев',
                'description': 'Рекламный блок после секции комментариев',
                'placement_type': 'banner',
                'recommended_size': '728x90',
                'position_order': 20,
            },
            {
                'code': 'sidebar_after_author',
                'name': 'Сайдбар после автора',
                'description': 'Рекламный блок в сайдбаре после карточки автора',
                'placement_type': 'banner',
                'recommended_size': '300x250',
                'position_order': 25,
            },
            {
                'code': 'sidebar_after_popular',
                'name': 'Сайдбар после популярных статей',
                'description': 'Рекламный блок в сайдбаре после популярных статей',
                'placement_type': 'banner',
                'recommended_size': '300x250',
                'position_order': 30,
            },
        ]
        
        created_count = 0
        existing_count = 0
        
        for place_data in new_places:
            place, created = AdPlace.objects.get_or_create(
                code=place_data['code'],
                defaults={
                    'name': place_data['name'],
                    'description': place_data['description'],
                    'placement_type': place_data['placement_type'],
                    'recommended_size': place_data['recommended_size'],
                    'position_order': place_data['position_order'],
                    'is_active': True,
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'  [+] Создано: {place.name} ({place.code})'))
                created_count += 1
            else:
                self.stdout.write(f'  [i] Уже существует: {place.name} ({place.code})')
                existing_count += 1
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS(f'[OK] Готово!'))
        self.stdout.write(f'  Создано новых мест: {created_count}')
        self.stdout.write(f'  Уже существовало: {existing_count}')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        self.stdout.write('[INFO] Следующие шаги:')
        self.stdout.write('  1. Создайте баннеры для новых мест в админ-панели')
        self.stdout.write('  2. Или используйте команду: python manage.py populate_ad_test_data')

