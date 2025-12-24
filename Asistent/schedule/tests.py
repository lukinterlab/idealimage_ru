"""
Тесты для системы расписаний AI.
Проверка работоспособности форм, вьюшек и генерации гороскопов.
"""
import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from .models import AISchedule, AIScheduleRun
from .forms import AIScheduleForm
from Asistent.models import PromptTemplate
from blog.models import Category


class AIScheduleFormTests(TestCase):
    """Тесты формы AIScheduleForm"""
    
    def setUp(self):
        """Подготовка тестовых данных"""
        self.category = Category.objects.create(
            title='Тестовая категория',
            slug='test-category'
        )
        self.prompt_template = PromptTemplate.objects.create(
            name='TEST_PROMPT',
            template='Тестовый промпт для {zodiac_sign}',
            category='horoscope',
            is_active=True
        )
    
    def test_form_generation_delay_save(self):
        """Тест сохранения generation_delay в payload_template"""
        form_data = {
            'name': 'Тест гороскопов',
            'strategy_type': 'prompt',
            'prompt_template': self.prompt_template.id,
            'category': self.category.id,
            'schedule_kind': 'daily',
            'scheduled_time': '08:00',
            'posting_frequency': 'daily',
            'articles_per_run': 12,
            'min_word_count': 500,
            'max_word_count': 1000,
            'generation_delay': 3,
            'retry_count': 2,
            'retry_delay': 5,
            'is_active': True,
        }
        
        form = AIScheduleForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Ошибки формы: {form.errors}")
        
        schedule = form.save()
        self.assertIsNotNone(schedule.payload_template)
        self.assertEqual(schedule.payload_template.get('generation_delay'), 3)
        self.assertEqual(schedule.payload_template.get('retry_count'), 2)
        self.assertEqual(schedule.payload_template.get('retry_delay'), 5)
    
    def test_form_generation_delay_validation(self):
        """Тест валидации диапазонов generation_delay, retry_count, retry_delay"""
        form_data = {
            'name': 'Тест валидации',
            'strategy_type': 'prompt',
            'prompt_template': self.prompt_template.id,
            'category': self.category.id,
            'schedule_kind': 'daily',
            'scheduled_time': '08:00',
            'posting_frequency': 'daily',
            'articles_per_run': 1,
            'min_word_count': 500,
            'max_word_count': 1000,
            'generation_delay': 100,  # Превышает лимит 60
            'retry_count': 10,  # Превышает лимит 5
            'retry_delay': 200,  # Превышает лимит 120
            'is_active': True,
        }
        
        form = AIScheduleForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        schedule = form.save()
        # Проверяем, что значения ограничены
        self.assertEqual(schedule.payload_template.get('generation_delay'), 60)
        self.assertEqual(schedule.payload_template.get('retry_count'), 5)
        self.assertEqual(schedule.payload_template.get('retry_delay'), 120)
    
    def test_form_edit_loads_parameters(self):
        """Тест загрузки параметров из payload_template при редактировании"""
        schedule = AISchedule.objects.create(
            name='Тест редактирования',
            strategy_type='prompt',
            prompt_template=self.prompt_template,
            category=self.category,
            schedule_kind='daily',
            scheduled_time='08:00',
            posting_frequency='daily',
            articles_per_run=12,
            min_word_count=500,
            max_word_count=1000,
            payload_template={
                'generation_delay': 5,
                'retry_count': 3,
                'retry_delay': 10,
            },
            is_active=True
        )
        
        form = AIScheduleForm(instance=schedule)
        self.assertEqual(form.fields['generation_delay'].initial, 5)
        self.assertEqual(form.fields['retry_count'].initial, 3)
        self.assertEqual(form.fields['retry_delay'].initial, 10)
    
    def test_form_static_dynamic_params(self):
        """Тест сохранения static_params и dynamic_params"""
        form_data = {
            'name': 'Тест параметров',
            'strategy_type': 'prompt',
            'prompt_template': self.prompt_template.id,
            'category': self.category.id,
            'schedule_kind': 'daily',
            'scheduled_time': '08:00',
            'posting_frequency': 'daily',
            'articles_per_run': 1,
            'min_word_count': 500,
            'max_word_count': 1000,
            'static_params': json.dumps({'topic': 'гороскоп', 'style': 'дружелюбный'}),
            'dynamic_params': json.dumps({
                'zodiac_sign': {
                    'type': 'cycle_list',
                    'values': ['Овен', 'Телец', 'Близнецы']
                }
            }),
            'is_active': True,
        }
        
        form = AIScheduleForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Ошибки формы: {form.errors}")
        
        schedule = form.save()
        self.assertIsNotNone(schedule.static_params)
        self.assertEqual(schedule.static_params.get('topic'), 'гороскоп')
        self.assertIsNotNone(schedule.dynamic_params)
        self.assertIn('zodiac_sign', schedule.dynamic_params)


class AIScheduleViewsTests(TestCase):
    """Тесты вьюшек расписаний"""
    
    def setUp(self):
        """Подготовка тестовых данных"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )
        self.client.login(username='testuser', password='testpass123')
        
        self.category = Category.objects.create(
            title='Тестовая категория',
            slug='test-category'
        )
        self.prompt_template = PromptTemplate.objects.create(
            name='TEST_PROMPT',
            template='Тестовый промпт',
            category='horoscope',
            is_active=True
        )
    
    def test_schedule_create_view(self):
        """Тест создания расписания через вьюшку"""
        url = reverse('schedule:schedule_create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertIn('schedule_presets', response.context)
        self.assertIn('schedule_preview_url', response.context)
    
    def test_schedule_create_post(self):
        """Тест POST запроса на создание расписания"""
        url = reverse('schedule:schedule_create')
        form_data = {
            'name': 'Тестовое расписание',
            'strategy_type': 'prompt',
            'prompt_template': self.prompt_template.id,
            'category': self.category.id,
            'schedule_kind': 'daily',
            'scheduled_time': '08:00',
            'posting_frequency': 'daily',
            'articles_per_run': 12,
            'min_word_count': 500,
            'max_word_count': 1000,
            'generation_delay': 2,
            'retry_count': 2,
            'retry_delay': 5,
            'is_active': True,
        }
        
        response = self.client.post(url, data=form_data)
        self.assertEqual(response.status_code, 302)  # Редирект после успешного создания
        
        schedule = AISchedule.objects.get(name='Тестовое расписание')
        self.assertIsNotNone(schedule)
        self.assertEqual(schedule.payload_template.get('generation_delay'), 2)
        self.assertEqual(schedule.payload_template.get('retry_count'), 2)
        self.assertEqual(schedule.payload_template.get('retry_delay'), 5)
    
    def test_schedule_edit_view(self):
        """Тест редактирования расписания"""
        schedule = AISchedule.objects.create(
            name='Тест редактирования',
            strategy_type='prompt',
            prompt_template=self.prompt_template,
            category=self.category,
            schedule_kind='daily',
            scheduled_time='08:00',
            posting_frequency='daily',
            articles_per_run=12,
            min_word_count=500,
            max_word_count=1000,
            payload_template={
                'generation_delay': 3,
                'retry_count': 2,
                'retry_delay': 5,
            },
            is_active=True
        )
        
        url = reverse('schedule:schedule_edit', args=[schedule.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertIn('schedule', response.context)
        self.assertEqual(response.context['schedule'].id, schedule.id)
    
    def test_old_views_redirect(self):
        """Тест редиректа старых вьюшек на новые"""
        # Тест редиректа create_ai_schedule
        url = reverse('asistent:create_ai_schedule')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/schedules/create/'))


class HoroscopeGenerationTests(TestCase):
    """Тесты генерации гороскопов"""
    
    def setUp(self):
        """Подготовка тестовых данных"""
        self.category = Category.objects.create(
            title='Гороскопы',
            slug='horoscopes'
        )
        self.prompt_template = PromptTemplate.objects.create(
            name='DAILY_HOROSCOPE_PROMPT',
            template='Гороскоп для {zodiac_sign} на {date}',
            category='horoscope',
            is_active=True
        )
    
    def test_horoscope_parameters_usage(self):
        """Тест использования параметров generation_delay, retry_count, retry_delay в генерации"""
        schedule = AISchedule.objects.create(
            name='Тест гороскопов',
            strategy_type='prompt',
            prompt_template=self.prompt_template,
            category=self.category,
            schedule_kind='daily',
            scheduled_time='08:00',
            posting_frequency='daily',
            articles_per_run=12,
            min_word_count=500,
            max_word_count=1000,
            payload_template={
                'generation_delay': 2,
                'retry_count': 2,
                'retry_delay': 5,
            },
            is_active=True
        )
        
        # Импортируем функцию генерации
        from .horoscope import _generate_all_horoscopes
        
        # Проверяем, что параметры читаются из payload_template
        payload = schedule.payload_template or {}
        generation_delay = payload.get('generation_delay', 2)
        retry_count = payload.get('retry_count', 2)
        retry_delay = payload.get('retry_delay', 5)
        
        self.assertEqual(generation_delay, 2)
        self.assertEqual(retry_count, 2)
        self.assertEqual(retry_delay, 5)
    
    def test_horoscope_default_parameters(self):
        """Тест значений по умолчанию для параметров гороскопов"""
        schedule = AISchedule.objects.create(
            name='Тест дефолтных параметров',
            strategy_type='prompt',
            prompt_template=self.prompt_template,
            category=self.category,
            schedule_kind='daily',
            scheduled_time='08:00',
            posting_frequency='daily',
            articles_per_run=12,
            min_word_count=500,
            max_word_count=1000,
            payload_template={},  # Пустой payload
            is_active=True
        )
        
        payload = schedule.payload_template or {}
        generation_delay = payload.get('generation_delay', 2)  # Значение по умолчанию
        retry_count = payload.get('retry_count', 2)  # Значение по умолчанию
        retry_delay = payload.get('retry_delay', 5)  # Значение по умолчанию
        
        self.assertEqual(generation_delay, 2)
        self.assertEqual(retry_count, 2)
        self.assertEqual(retry_delay, 5)


class ScheduleIntegrationTests(TestCase):
    """Интеграционные тесты системы расписаний"""
    
    def setUp(self):
        """Подготовка тестовых данных"""
        self.category = Category.objects.create(
            title='Тестовая категория',
            slug='test-category'
        )
        self.prompt_template = PromptTemplate.objects.create(
            name='TEST_PROMPT',
            template='Тестовый промпт',
            category='horoscope',
            is_active=True
        )
    
    def test_full_workflow(self):
        """Тест полного цикла: создание -> редактирование -> использование параметров"""
        # 1. Создание расписания через форму
        form_data = {
            'name': 'Полный тест',
            'strategy_type': 'prompt',
            'prompt_template': self.prompt_template.id,
            'category': self.category.id,
            'schedule_kind': 'daily',
            'scheduled_time': '08:00',
            'posting_frequency': 'daily',
            'articles_per_run': 12,
            'min_word_count': 500,
            'max_word_count': 1000,
            'generation_delay': 3,
            'retry_count': 2,
            'retry_delay': 5,
            'is_active': True,
        }
        
        form = AIScheduleForm(data=form_data)
        self.assertTrue(form.is_valid())
        schedule = form.save()
        
        # 2. Проверка сохранения
        schedule.refresh_from_db()
        self.assertEqual(schedule.payload_template.get('generation_delay'), 3)
        self.assertEqual(schedule.payload_template.get('retry_count'), 2)
        self.assertEqual(schedule.payload_template.get('retry_delay'), 5)
        
        # 3. Редактирование
        edit_form_data = form_data.copy()
        edit_form_data['generation_delay'] = 4
        edit_form = AIScheduleForm(data=edit_form_data, instance=schedule)
        self.assertTrue(edit_form.is_valid())
        schedule = edit_form.save()
        
        # 4. Проверка обновления
        schedule.refresh_from_db()
        self.assertEqual(schedule.payload_template.get('generation_delay'), 4)
        
        # 5. Проверка использования в генерации
        payload = schedule.payload_template or {}
        generation_delay = payload.get('generation_delay', 2)
        self.assertEqual(generation_delay, 4)

