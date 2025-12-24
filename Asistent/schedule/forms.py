"""
Формы для управления расписаниями и задачами.
Перенесено из Asistent/forms.py для модульности.
"""
import json
from datetime import datetime

from django import forms
from django.conf import settings

try:
    from croniter import croniter
except ImportError:
    croniter = None

from .models import AISchedule
from blog.models import Category


class AIScheduleForm(forms.ModelForm):
    """
    Улучшенная форма создания/редактирования расписания AI.
    Объединена из Asistent/forms.py с улучшениями для payload_template.
    """
    
    # Параметры генерации гороскопов (для horoscope стратегии)
    generation_delay = forms.IntegerField(
        label='Задержка между генерациями (секунды)',
        initial=2,
        required=False,
        help_text='Задержка между генерацией каждого гороскопа (по умолчанию 2 сек)',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 0,
            'max': 60,
            'placeholder': '2'
        })
    )
    
    retry_count = forms.IntegerField(
        label='Количество повторных попыток',
        initial=2,
        required=False,
        help_text='Сколько раз повторять генерацию для неудачных знаков (по умолчанию 2)',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 0,
            'max': 5,
            'placeholder': '2'
        })
    )
    
    retry_delay = forms.IntegerField(
        label='Задержка перед повтором (секунды)',
        initial=5,
        required=False,
        help_text='Задержка перед повторной попыткой генерации (по умолчанию 5 сек)',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 0,
            'max': 120,
            'placeholder': '5'
        })
    )
    
    class Meta:
        model = AISchedule
        fields = [
            'name',
            'strategy_type',
            'payload_template',
            'prompt_template',
            'scheduled_time',
            'task_type',
            'schedule_kind',
            'cron_expression',
            'interval_minutes',
            'weekday',
            'source_urls',
            'category',
            'tags',
            'posting_frequency',
            'articles_per_run',
            'min_word_count',
            'max_word_count',
            'keywords',
            'tone',
            'strategy_options',
            'static_params',
            'dynamic_params',
            'max_runs',
            'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Название расписания'
            }),
            'strategy_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'pipeline': forms.Select(attrs={
                'class': 'form-control',
            }),
            'pipeline_slug': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'daily-horoscope-flow'
            }),
            'payload_template': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': '{"post_id": 1}'
            }),
            'prompt_template': forms.Select(attrs={
                'class': 'form-control'
            }),
            'scheduled_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time',
                'placeholder': '08:30'
            }),
            'task_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'schedule_kind': forms.Select(attrs={
                'class': 'form-control'
            }),
            'cron_expression': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '0 8 * * *'
            }),
            'interval_minutes': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'placeholder': '60'
            }),
            'weekday': forms.Select(attrs={
                'class': 'form-control'
            }),
            'source_urls': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'https://news-site1.com\nhttps://news-site2.com/beauty\nhttps://fashion-blog.com/rss'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control'
            }),
            'tags': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ai, новости, актуальное'
            }),
            'posting_frequency': forms.Select(attrs={
                'class': 'form-control'
            }),
            'articles_per_run': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
            'min_word_count': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 100
            }),
            'max_word_count': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 100
            }),
            'keywords': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'красота\nмода\nстиль'
            }),
            'tone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'дружелюбный и экспертный'
            }),
            'strategy_options': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '{"task": "optimization"}'
            }),
            'static_params': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '{"topic": "гороскоп", "style": "по-фрейду"}'
            }),
            'dynamic_params': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': '{"name": {"type": "cycle_list", "values": ["Анна", "Иван", "Мария"]}}'
            }),
            'max_runs': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'placeholder': 'Пусто = бесконечно'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Если редактируем существующее расписание, заполняем поля из payload_template
        if self.instance and self.instance.pk:
            payload = self.instance.payload_template or {}
            # Заполняем поля параметров генерации гороскопов
            if 'generation_delay' in self.fields:
                self.fields['generation_delay'].initial = payload.get('generation_delay', 2)
            if 'retry_count' in self.fields:
                self.fields['retry_count'].initial = payload.get('retry_count', 2)
            if 'retry_delay' in self.fields:
                self.fields['retry_delay'].initial = payload.get('retry_delay', 5)
        
        self.fields['payload_template'].help_text = 'JSON-объект, который будет передан в пайплайн. Используйте конструктор ниже, чтобы не редактировать JSON вручную.'
        for field_name in ('strategy_options', 'static_params', 'dynamic_params', 'payload_template'):
            value = self.initial.get(field_name)
            if isinstance(value, dict):
                self.initial[field_name] = json.dumps(value, ensure_ascii=False, indent=2)
    
    def clean(self):
        """Валидация и базовая нормализация настроек расписания"""
        cleaned_data = super().clean()
        prompt_template = cleaned_data.get('prompt_template')
        source_urls = cleaned_data.get('source_urls', '').strip()
        strategy_type = cleaned_data.get('strategy_type') or 'prompt'
        strategy_options = cleaned_data.get('strategy_options')

        if isinstance(strategy_options, str) and strategy_options.strip():
            try:
                cleaned_data['strategy_options'] = json.loads(strategy_options)
            except json.JSONDecodeError as exc:
                raise forms.ValidationError(f'Опции стратегии должны быть валидным JSON: {exc}')
        elif not strategy_options:
            cleaned_data['strategy_options'] = {}

        pipeline = cleaned_data.get('pipeline')
        pipeline_slug = cleaned_data.get('pipeline_slug', '').strip()
        cleaned_data['pipeline_slug'] = pipeline_slug

        payload_template = cleaned_data.get('payload_template')
        if isinstance(payload_template, str) and payload_template.strip():
            try:
                cleaned_data['payload_template'] = json.loads(payload_template)
            except json.JSONDecodeError as exc:
                raise forms.ValidationError(f'Payload пайплайна должен быть валидным JSON: {exc}')
        elif not payload_template:
            # Если payload_template пустой, создаём из существующего или новый
            if self.instance and self.instance.pk:
                cleaned_data['payload_template'] = self.instance.payload_template or {}
            else:
                cleaned_data['payload_template'] = {}
        
        # Добавляем параметры генерации гороскопов в payload_template
        payload = cleaned_data['payload_template']
        if not isinstance(payload, dict):
            payload = {}
        
        # Сохраняем параметры генерации гороскопов (только если указаны)
        generation_delay = cleaned_data.get('generation_delay')
        if generation_delay is not None:
            payload['generation_delay'] = max(0, min(60, generation_delay))  # Ограничение 0-60 сек
        
        retry_count = cleaned_data.get('retry_count')
        if retry_count is not None:
            payload['retry_count'] = max(0, min(5, retry_count))  # Ограничение 0-5 попыток
        
        retry_delay = cleaned_data.get('retry_delay')
        if retry_delay is not None:
            payload['retry_delay'] = max(0, min(120, retry_delay))  # Ограничение 0-120 сек
        
        cleaned_data['payload_template'] = payload

        if strategy_type == 'pipeline':
            if not pipeline and not pipeline_slug:
                raise forms.ValidationError('Для стратегии "Пайплайн" выберите автоматизацию или укажите slug.')
        else:
            cleaned_data['pipeline'] = None
            cleaned_data['pipeline_slug'] = pipeline_slug

        # Требование к промптовой стратегии — наличие шаблона или источников
        if strategy_type == 'prompt':
            if not prompt_template and not source_urls:
                raise forms.ValidationError(
                    'Для стратегии "Промпт" необходимо выбрать шаблон промпта или указать URL источников'
                )

        # Для системной стратегии обязательно указать задачу
        if strategy_type == 'system':
            options = cleaned_data.get('strategy_options') or {}
            if not isinstance(options, dict):
                options = {}
            static_params = cleaned_data.get('static_params') or {}
            if not isinstance(static_params, dict):
                static_params = {}
            task_name = options.get('task') or static_params.get('task')
            if not task_name:
                raise forms.ValidationError(
                    'Для системной стратегии укажите ключ "task" в опциях стратегии или в статических параметрах.'
                )

        schedule_kind = cleaned_data.get('schedule_kind') or 'daily'
        scheduled_time = cleaned_data.get('scheduled_time')
        interval_minutes = cleaned_data.get('interval_minutes')
        weekday = cleaned_data.get('weekday')
        cron_expression = (cleaned_data.get('cron_expression') or '').strip()
        articles_per_run = cleaned_data.get('articles_per_run') or 1
        load_limit = getattr(settings, 'AISCHEDULE_MAX_ITEMS_PER_HOUR', 30)

        if schedule_kind in ('daily', 'weekly') and not scheduled_time:
            raise forms.ValidationError('Для выбранного режима задайте точное время запуска.')

        if schedule_kind == 'weekly' and weekday is None:
            raise forms.ValidationError('Выберите день недели для еженедельного запуска.')

        if schedule_kind == 'interval':
            if not interval_minutes:
                raise forms.ValidationError('Укажите интервал в минутах.')
            if interval_minutes < 5:
                raise forms.ValidationError('Интервальный запуск не может быть чаще, чем раз в 5 минут.')
            if interval_minutes > 1440:
                raise forms.ValidationError('Интервал не может превышать 1440 минут (сутки).')

            per_hour = (60 / interval_minutes) * max(articles_per_run, 1)
            if per_hour > load_limit:
                raise forms.ValidationError(
                    f'Нагрузка {per_hour:.1f} публикаций/час превышает допустимый лимит {load_limit}. '
                    'Увеличьте интервал или уменьшите количество статей за запуск.'
                )
            cleaned_data['cron_expression'] = ''
        elif schedule_kind == 'cron':
            if not cron_expression:
                raise forms.ValidationError('Укажите cron-выражение для данного типа расписания.')
            if not croniter:
                raise forms.ValidationError('Библиотека croniter недоступна, cron-расписание временно не поддерживается.')
            try:
                croniter(cron_expression, datetime.now())
            except Exception as exc:
                raise forms.ValidationError(f'Некорректное cron-выражение: {exc}')
            cleaned_data['cron_expression'] = cron_expression
            cleaned_data['interval_minutes'] = None
        else:
            cleaned_data['cron_expression'] = ''
            if schedule_kind != 'interval':
                cleaned_data['interval_minutes'] = None

        if schedule_kind != 'weekly':
            cleaned_data['weekday'] = None

        return cleaned_data


class DjangoQScheduleForm(forms.Form):
    """Форма для создания/редактирования системных задач Django-Q"""
    
    SCHEDULE_TYPE_CHOICES = [
        ('I', 'Интервал (минуты)'),
        ('H', 'Ежечасно'),
        ('D', 'Ежедневно'),
        ('W', 'Еженедельно'),
        ('M', 'Ежемесячно'),
        ('C', 'Cron выражение'),
        ('O', 'Однократно'),
    ]
    
    name = forms.CharField(
        label='Название задачи',
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white',
            'placeholder': 'Очистка старых данных'
        })
    )
    
    func = forms.CharField(
        label='Функция для выполнения',
        max_length=500,
        widget=forms.TextInput(attrs={
            'class': 'form-control w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-mono',
            'placeholder': 'myapp.tasks.my_function'
        }),
        help_text='Полный путь к функции: app.module.function'
    )
    
    schedule_type = forms.ChoiceField(
        label='Тип расписания',
        choices=SCHEDULE_TYPE_CHOICES,
        initial='D',
        widget=forms.Select(attrs={
            'class': 'form-control w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white'
        })
    )
    
    minutes = forms.IntegerField(
        label='Интервал (минуты)',
        required=False,
        initial=60,
        widget=forms.NumberInput(attrs={
            'class': 'form-control w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white',
            'placeholder': '60'
        }),
        help_text='Используется только для типа "Интервал"'
    )
    
    cron = forms.CharField(
        label='Cron выражение',
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-mono',
            'placeholder': '0 3 * * *'
        }),
        help_text='Используется только для типа "Cron". Формат: минута час день месяц день_недели'
    )
    
    args = forms.CharField(
        label='Аргументы (через запятую)',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-mono',
            'placeholder': 'arg1, arg2, arg3'
        }),
        help_text='Позиционные аргументы через запятую'
    )
    
    kwargs = forms.CharField(
        label='Именованные аргументы (JSON)',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-mono',
            'rows': 3,
            'placeholder': '{"key": "value", "timeout": 300}'
        }),
        help_text='JSON объект с именованными аргументами'
    )
    
    repeats = forms.IntegerField(
        label='Количество повторений',
        initial=-1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white',
            'placeholder': '-1'
        }),
        help_text='-1 = бесконечно, 0 = выполнено, >0 = количество раз'
    )
    
    next_run = forms.DateTimeField(
        label='Следующий запуск',
        required=False,
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white',
            'type': 'datetime-local'
        }),
        help_text='Оставьте пустым для автоматического расчета'
    )

