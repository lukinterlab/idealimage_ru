"""
Тесты для приложения advertising
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

from .models import (
    AdPlace, Advertiser, AdCampaign, AdBanner, AdSchedule,
    ContextAd, AdInsertion
)

User = get_user_model()


class AdPlaceModelTest(TestCase):
    """Тесты модели AdPlace"""
    
    def setUp(self):
        self.place = AdPlace.objects.create(
            name='Header Banner',
            code='header_banner',
            placement_type='banner',
            recommended_size='728x90'
        )
    
    def test_place_creation(self):
        """Тест создания рекламного места"""
        self.assertEqual(self.place.name, 'Header Banner')
        self.assertEqual(self.place.code, 'header_banner')
        self.assertTrue(self.place.is_active)
    
    def test_place_str(self):
        """Тест строкового представления"""
        expected = 'Header Banner (header_banner)'
        self.assertEqual(str(self.place), expected)


class AdvertiserModelTest(TestCase):
    """Тесты модели Advertiser"""
    
    def setUp(self):
        self.advertiser = Advertiser.objects.create(
            name='Test Company',
            contact_email='test@example.com'
        )
    
    def test_advertiser_creation(self):
        """Тест создания рекламодателя"""
        self.assertEqual(self.advertiser.name, 'Test Company')
        self.assertTrue(self.advertiser.is_active)
        self.assertEqual(self.advertiser.total_spent, Decimal('0.00'))


class AdCampaignModelTest(TestCase):
    """Тесты модели AdCampaign"""
    
    def setUp(self):
        self.advertiser = Advertiser.objects.create(
            name='Test Company',
            contact_email='test@example.com'
        )
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        self.campaign = AdCampaign.objects.create(
            advertiser=self.advertiser,
            name='Summer Campaign',
            budget=Decimal('10000.00'),
            cost_per_click=Decimal('5.00'),
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=30),
            created_by=self.user
        )
    
    def test_campaign_creation(self):
        """Тест создания кампании"""
        self.assertEqual(self.campaign.name, 'Summer Campaign')
        self.assertEqual(self.campaign.budget, Decimal('10000.00'))
        self.assertTrue(self.campaign.is_active)
    
    def test_is_active_now(self):
        """Тест проверки активности кампании"""
        self.assertTrue(self.campaign.is_active_now())
    
    def test_remaining_budget(self):
        """Тест остатка бюджета"""
        self.campaign.spent_amount = Decimal('3000.00')
        self.assertEqual(self.campaign.get_remaining_budget(), Decimal('7000.00'))
    
    def test_budget_usage_percent(self):
        """Тест процента использования бюджета"""
        self.campaign.spent_amount = Decimal('5000.00')
        self.assertEqual(self.campaign.get_budget_usage_percent(), 50.0)


class AdBannerModelTest(TestCase):
    """Тесты модели AdBanner"""
    
    def setUp(self):
        self.place = AdPlace.objects.create(
            name='Sidebar',
            code='sidebar_top',
            placement_type='banner'
        )
        self.advertiser = Advertiser.objects.create(
            name='Test Company',
            contact_email='test@example.com'
        )
        self.campaign = AdCampaign.objects.create(
            advertiser=self.advertiser,
            name='Test Campaign',
            budget=Decimal('5000.00'),
            cost_per_click=Decimal('10.00'),
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=30)
        )
        self.banner = AdBanner.objects.create(
            campaign=self.campaign,
            place=self.place,
            name='Test Banner',
            banner_type='image',
            target_url='https://example.com'
        )
    
    def test_banner_creation(self):
        """Тест создания баннера"""
        self.assertEqual(self.banner.name, 'Test Banner')
        self.assertTrue(self.banner.is_active)
        self.assertEqual(self.banner.priority, 5)
    
    def test_ctr_calculation(self):
        """Тест расчета CTR"""
        self.banner.impressions = 1000
        self.banner.clicks = 50
        self.assertEqual(self.banner.get_ctr(), 5.0)
    
    def test_ctr_zero_impressions(self):
        """Тест CTR при нулевых показах"""
        self.assertEqual(self.banner.get_ctr(), 0)
    
    def test_cost_calculation(self):
        """Тест расчета стоимости"""
        self.banner.clicks = 10
        cost = self.banner.get_cost()
        expected = Decimal('10') * Decimal('10.00')
        self.assertEqual(cost, expected)


class ContextAdModelTest(TestCase):
    """Тесты модели ContextAd"""
    
    def setUp(self):
        self.advertiser = Advertiser.objects.create(
            name='Test Company',
            contact_email='test@example.com'
        )
        self.campaign = AdCampaign.objects.create(
            advertiser=self.advertiser,
            name='Test Campaign',
            budget=Decimal('5000.00'),
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=30)
        )
        self.context_ad = ContextAd.objects.create(
            campaign=self.campaign,
            keyword_phrase='купить телефон',
            anchor_text='лучшие телефоны',
            target_url='https://example.com/phones',
            cost_per_click=Decimal('15.00')
        )
    
    def test_context_ad_creation(self):
        """Тест создания контекстной рекламы"""
        self.assertEqual(self.context_ad.keyword_phrase, 'купить телефон')
        self.assertTrue(self.context_ad.is_active)
    
    def test_is_active_permanent(self):
        """Тест активности постоянной рекламы"""
        self.context_ad.insertion_type = 'permanent'
        self.assertTrue(self.context_ad.is_active_now())
    
    def test_is_active_temporary_valid(self):
        """Тест активности временной рекламы (в сроке)"""
        self.context_ad.insertion_type = 'temporary'
        self.context_ad.expire_date = timezone.now().date() + timedelta(days=7)
        self.assertTrue(self.context_ad.is_active_now())
    
    def test_is_active_temporary_expired(self):
        """Тест активности временной рекламы (просрочена)"""
        self.context_ad.insertion_type = 'temporary'
        self.context_ad.expire_date = timezone.now().date() - timedelta(days=1)
        self.assertFalse(self.context_ad.is_active_now())


# Добавим тесты для других моделей по мере необходимости
