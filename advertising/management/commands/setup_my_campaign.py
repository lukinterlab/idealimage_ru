"""
Management команда для очистки рекламных данных и создания компании МОЯ
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

from advertising.models import (
    AdPlace, Advertiser, AdCampaign, AdBanner, AdSchedule,
    ContextAd, AdInsertion, AdClick, AdImpression, AdPerformanceML,
    AdRecommendation, AdActionLog
)

User = get_user_model()


class Command(BaseCommand):
    help = 'Очистить все рекламные данные и создать компанию МОЯ с баннерами'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('Начинаем очистку рекламных данных и создание компании МОЯ'))
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write('')
        
        # Шаг 1: Удаление AdClick (клики)
        self.stdout.write('Шаг 1: Удаление кликов...')
        clicks_count = AdClick.objects.count()
        AdClick.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'  [OK] Удалено кликов: {clicks_count}'))
        
        # Шаг 2: Удаление AdImpression (показы)
        self.stdout.write('Шаг 2: Удаление показов...')
        impressions_count = AdImpression.objects.count()
        AdImpression.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'  [OK] Удалено показов: {impressions_count}'))
        
        # Шаг 3: Удаление AdPerformanceML (данные ML)
        self.stdout.write('Шаг 3: Удаление данных ML...')
        ml_count = AdPerformanceML.objects.count()
        AdPerformanceML.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'  [OK] Удалено записей ML: {ml_count}'))
        
        # Шаг 4: Удаление AdRecommendation (рекомендации)
        self.stdout.write('Шаг 4: Удаление рекомендаций AI...')
        recommendations_count = AdRecommendation.objects.count()
        AdRecommendation.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'  [OK] Удалено рекомендаций: {recommendations_count}'))
        
        # Шаг 5: Удаление AdInsertion (вставки контекстной рекламы)
        self.stdout.write('Шаг 5: Удаление вставок контекстной рекламы...')
        insertions_count = AdInsertion.objects.count()
        AdInsertion.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'  [OK] Удалено вставок: {insertions_count}'))
        
        # Шаг 6: Удаление AdSchedule (расписания)
        self.stdout.write('Шаг 6: Удаление расписаний...')
        schedules_count = AdSchedule.objects.count()
        AdSchedule.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'  [OK] Удалено расписаний: {schedules_count}'))
        
        # Шаг 7: Удаление AdBanner (баннеры)
        self.stdout.write('Шаг 7: Удаление баннеров...')
        banners_count = AdBanner.objects.count()
        AdBanner.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'  [OK] Удалено баннеров: {banners_count}'))
        
        # Шаг 8: Удаление ContextAd (контекстная реклама)
        self.stdout.write('Шаг 8: Удаление контекстных объявлений...')
        context_ads_count = ContextAd.objects.count()
        ContextAd.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'  [OK] Удалено контекстных объявлений: {context_ads_count}'))
        
        # Шаг 9: Удаление AdCampaign (кампании)
        self.stdout.write('Шаг 9: Удаление кампаний...')
        campaigns_count = AdCampaign.objects.count()
        AdCampaign.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'  [OK] Удалено кампаний: {campaigns_count}'))
        
        # Шаг 10: Удаление Advertiser (рекламодатели)
        self.stdout.write('Шаг 10: Удаление рекламодателей...')
        advertisers_count = Advertiser.objects.count()
        Advertiser.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'  [OK] Удалено рекламодателей: {advertisers_count}'))
        
        # Шаг 11: Удаление AdActionLog (журнал действий)
        self.stdout.write('Шаг 11: Удаление журнала действий...')
        logs_count = AdActionLog.objects.count()
        AdActionLog.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'  [OK] Удалено записей журнала: {logs_count}'))
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('[OK] Очистка завершена!'))
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('Начинаем создание компании МОЯ...'))
        self.stdout.write('')
        
        # Получаем или создаем админа
        admin = User.objects.filter(is_staff=True).first()
        if not admin:
            admin = User.objects.first()
        
        # Шаг 12: Создание рекламодателя "МОЯ КОМПАНИЯ"
        self.stdout.write('Шаг 12: Создание рекламодателя...')
        advertiser = Advertiser.objects.create(
            name='МОЯ КОМПАНИЯ',
            contact_email='info@idealimage.ru',
            contact_phone='+7 (999) 000-00-00',
            company_info='Основная рекламная компания сайта IdealImage.ru',
            is_active=True
        )
        self.stdout.write(self.style.SUCCESS(f'  [OK] Создан рекламодатель: {advertiser.name}'))
        
        # Шаг 13: Создание кампании "МОЯ"
        self.stdout.write('Шаг 13: Создание кампании...')
        today = timezone.now().date()
        campaign = AdCampaign.objects.create(
            advertiser=advertiser,
            name='МОЯ',
            budget=Decimal('1000000.00'),
            cost_per_click=Decimal('0.00'),
            cost_per_impression=Decimal('0.00'),
            start_date=today,
            end_date=today + timedelta(days=365),
            is_active=True,
            created_by=admin
        )
        self.stdout.write(self.style.SUCCESS(f'  [OK] Создана кампания: {campaign.name}'))
        
        # Шаг 14: Получение всех рекламных мест
        self.stdout.write('Шаг 14: Получение рекламных мест...')
        places = AdPlace.objects.all()
        places_count = places.count()
        self.stdout.write(self.style.SUCCESS(f'  [OK] Найдено мест: {places_count}'))
        
        # Шаг 15: Создание баннеров для каждого места
        self.stdout.write('Шаг 15: Создание баннеров...')
        banners_created = 0
        
        for place in places:
            # HTML контент для баннера
            # Для баннеров с карточками НЕ создаем HTML (карточки рендерятся динамически через поля card1_*, card2_*, и т.д.)
            if place.code in ['header_banner', 'footer_banner', 'in_post_middle', 'in_post_middle_1', 'in_post_middle_2', 'before_article_content', 'after_comments']:
                html_content = ''  # Пустой HTML, карточки рендерятся через render_card_content()
                default_height = 120
            else:
                # Для остальных мест - обычный блок
                html_content = f'''<div style="padding:20px; background:linear-gradient(135deg, #667eea 0%, #764ba2 100%); color:white; text-align:center; border-radius:8px;">
    <h3 style="font-size:20px; font-weight:bold; margin-bottom:8px;">{place.name}</h3>
    <p style="font-size:14px; opacity:0.9;">Рекламное место: {place.code}</p>
</div>'''
                default_height = 100
            
            banner = AdBanner.objects.create(
                campaign=campaign,
                place=place,
                name=place.name,
                banner_type='html',
                html_content=html_content,
                target_url='https://idealimage.ru',
                is_active=True,
                unlimited_impressions=True,
                banner_height=default_height,
                priority=10,
                weight=100
            )
            
            self.stdout.write(self.style.SUCCESS(f'  [OK] Создан баннер: {banner.name}'))
            banners_created += 1
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('[УСПЕШНО] Все операции завершены!'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        self.stdout.write(f'Создано:')
        self.stdout.write(f'  - Рекламодателей: 1')
        self.stdout.write(f'  - Кампаний: 1')
        self.stdout.write(f'  - Баннеров: {banners_created}')
        self.stdout.write('')
        self.stdout.write('Все баннеры настроены с безлимитным отображением!')
        self.stdout.write('')

