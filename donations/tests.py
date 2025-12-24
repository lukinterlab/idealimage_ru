"""
Тесты для приложения donations

Здесь можно добавить unit-тесты для проверки функционала
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from decimal import Decimal

from .models import Donation, DonationSettings


class DonationModelTest(TestCase):
    """Тесты модели Donation"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_donation(self):
        """Тест создания доната"""
        donation = Donation.objects.create(
            user=self.user,
            user_email='test@example.com',
            amount=Decimal('1000.00'),
            payment_method='yandex',
            status='pending'
        )
        
        self.assertEqual(donation.amount, Decimal('1000.00'))
        self.assertEqual(donation.status, 'pending')
        self.assertEqual(donation.payment_method, 'yandex')
    
    def test_get_donor_name(self):
        """Тест получения имени донатера"""
        donation = Donation.objects.create(
            user_email='test@example.com',
            user_name='Тест Тестов',
            amount=Decimal('500.00'),
            payment_method='yandex'
        )
        
        self.assertEqual(donation.get_donor_name(), 'Тест Тестов')
    
    def test_anonymous_donation(self):
        """Тест анонимного доната"""
        donation = Donation.objects.create(
            user_email='test@example.com',
            amount=Decimal('500.00'),
            payment_method='yandex',
            is_anonymous=True
        )
        
        self.assertEqual(donation.get_donor_name(), 'Анонимный донатер')


class DonationSettingsTest(TestCase):
    """Тесты модели DonationSettings"""
    
    def test_get_settings(self):
        """Тест получения настроек (синглтон)"""
        settings1 = DonationSettings.get_settings()
        settings2 = DonationSettings.get_settings()
        
        self.assertEqual(settings1.id, settings2.id)
        self.assertEqual(settings1.id, 1)
    
    def test_default_values(self):
        """Тест значений по умолчанию"""
        settings = DonationSettings.get_settings()
        
        self.assertEqual(settings.min_amount, Decimal('100.00'))
        self.assertTrue(settings.enable_yandex)
        self.assertTrue(settings.send_email_to_donor)


class DonationViewsTest(TestCase):
    """Тесты представлений"""
    
    def setUp(self):
        self.client = Client()
        DonationSettings.get_settings()
    
    def test_donation_page_get(self):
        """Тест GET запроса к странице донатов"""
        response = self.client.get('/donations/')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Поддержать проект')
    
    def test_donation_list(self):
        """Тест страницы списка донатов"""
        response = self.client.get('/donations/list/')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Наши спонсоры')
    
    def test_quick_donation_page(self):
        """Тест быстрой формы"""
        response = self.client.get('/donations/quick/')
        
        self.assertEqual(response.status_code, 200)


class DonationFormsTest(TestCase):
    """Тесты форм"""
    
    def setUp(self):
        DonationSettings.get_settings()
    
    def test_donation_form_valid(self):
        """Тест валидной формы"""
        from .forms import DonationForm
        
        form_data = {
            'amount': '1000',
            'payment_method': 'yandex',
            'user_email': 'test@example.com',
            'user_name': 'Тест',
            'is_anonymous': False,
        }
        
        form = DonationForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_donation_form_invalid_amount(self):
        """Тест невалидной суммы"""
        from .forms import DonationForm
        
        form_data = {
            'amount': '50',  # Меньше минимальной
            'payment_method': 'yandex',
            'user_email': 'test@example.com',
        }
        
        form = DonationForm(data=form_data)
        self.assertFalse(form.is_valid())


# Добавьте свои тесты здесь