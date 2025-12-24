"""
Management команда для создания тестовых данных рекламы
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
import random

from advertising.models import (
    AdPlace, Advertiser, AdCampaign, AdBanner, ContextAd
)

User = get_user_model()


class Command(BaseCommand):
    help = 'Создать тестовые данные для системы рекламы'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Создание тестовых данных...'))
        
        # Получаем или создаем админа
        admin = User.objects.filter(is_staff=True).first()
        if not admin:
            admin = User.objects.first()
        
        # Создаем рекламные места
        places_data = [
            ('header_banner', 'Баннер в шапке', 'banner', '728x90'),
            ('sidebar_top', 'Сайдбар вверху', 'banner', '300x250'),
            ('in_post_middle', 'В середине статьи', 'banner', '468x60'),
            ('footer_banner', 'Баннер в футере', 'banner', '728x90'),
            ('popup_modal', 'Всплывающее окно', 'popup', '600x400'),
            ('ticker_line', 'Бегущая строка', 'ticker', '100%'),
        ]
        
        places = []
        for code, name, placement_type, size in places_data:
            place, created = AdPlace.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'placement_type': placement_type,
                    'recommended_size': size,
                    'is_active': True
                }
            )
            places.append(place)
            if created:
                self.stdout.write(f'  Создано место: {name}')
        
        # Создаем рекламодателей
        advertisers_data = [
            ('Модный магазин', 'fashion@example.com', '+7 (999) 123-45-67'),
            ('Салон красоты', 'beauty@example.com', '+7 (999) 765-43-21'),
            ('Фитнес-клуб', 'fitness@example.com', '+7 (999) 555-12-34'),
        ]
        
        advertisers = []
        for name, email, phone in advertisers_data:
            advertiser, created = Advertiser.objects.get_or_create(
                name=name,
                defaults={
                    'contact_email': email,
                    'contact_phone': phone,
                    'is_active': True
                }
            )
            advertisers.append(advertiser)
            if created:
                self.stdout.write(f'  Создан рекламодатель: {name}')
        
        # Создаем кампании
        campaigns = []
        for advertiser in advertisers:
            campaign, created = AdCampaign.objects.get_or_create(
                advertiser=advertiser,
                name=f'Кампания {advertiser.name} 2024',
                defaults={
                    'budget': Decimal('50000.00'),
                    'cost_per_click': Decimal('10.00'),
                    'cost_per_impression': Decimal('0.50'),
                    'start_date': timezone.now().date(),
                    'end_date': timezone.now().date() + timedelta(days=90),
                    'is_active': True,
                    'created_by': admin
                }
            )
            campaigns.append(campaign)
            if created:
                self.stdout.write(f'  Создана кампания: {campaign.name}')
        
        # Создаем баннеры
        banners_count = 0
        for campaign in campaigns:
            for place in places[:4]:  # Только для первых 4 мест
                banner, created = AdBanner.objects.get_or_create(
                    campaign=campaign,
                    place=place,
                    defaults={
                        'name': f'Баннер {campaign.advertiser.name} - {place.name}',
                        'banner_type': 'html',
                        'html_content': f'<div style="padding:20px; background:linear-gradient(135deg, #667eea 0%, #764ba2 100%); color:white; text-align:center;"><h3>{campaign.advertiser.name}</h3><p>Специальное предложение!</p></div>',
                        'target_url': 'https://example.com',
                        'is_active': True,
                        'priority': random.randint(5, 10),
                        'weight': 100
                    }
                )
                if created:
                    banners_count += 1
        
        self.stdout.write(f'  Создано баннеров: {banners_count}')
        
        # Создаем контекстную рекламу
        context_ads_data = [
            ('модная одежда', 'стильная одежда', 'https://example.com/fashion'),
            ('красивые волосы', 'уход за волосами', 'https://example.com/hair'),
            ('похудение', 'программы похудения', 'https://example.com/fitness'),
            ('макияж', 'профессиональный макияж', 'https://example.com/makeup'),
        ]
        
        context_ads_count = 0
        for campaign in campaigns:
            for keyword, anchor, url in context_ads_data[:2]:
                context_ad, created = ContextAd.objects.get_or_create(
                    campaign=campaign,
                    keyword_phrase=keyword,
                    defaults={
                        'anchor_text': anchor,
                        'target_url': url,
                        'cost_per_click': Decimal('15.00'),
                        'priority': random.randint(5, 10),
                        'is_active': True
                    }
                )
                if created:
                    context_ads_count += 1
        
        self.stdout.write(f'  Создано контекстных объявлений: {context_ads_count}')
        
        self.stdout.write(self.style.SUCCESS('[OK] Тестовые данные созданы!'))
        self.stdout.write(self.style.SUCCESS(f'  Мест: {len(places)}'))
        self.stdout.write(self.style.SUCCESS(f'  Рекламодателей: {len(advertisers)}'))
        self.stdout.write(self.style.SUCCESS(f'  Кампаний: {len(campaigns)}'))
        self.stdout.write(self.style.SUCCESS(f'  Баннеров: {banners_count}'))
        self.stdout.write(self.style.SUCCESS(f'  Контекстных объявлений: {context_ads_count}'))

