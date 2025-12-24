"""
Формы для AI-Ассистента
"""
import json
import re
from datetime import datetime

from django import forms
from django.conf import settings

try:
    from croniter import croniter
except ImportError:  # pragma: no cover - croniter устанавливается вместе с django-q
    croniter = None


from .models import ContentTask
from blog.models import Category

"""Форма создания/редактирования задания"""
class ContentTaskForm(forms.ModelForm):
    """Форма создания/редактирования задания"""
    
    # Упрощённые поля для критериев задания
    task_min_length = forms.IntegerField(
        required=False,
        label='Минимальная длина статьи (символов)',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '1000'
        })
    )
    
    task_max_length = forms.IntegerField(
        required=False,
        label='Максимальная длина статьи (символов)',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '5000'
        })
    )
    
    task_required_keywords_text = forms.CharField(
        required=False,
        label='Обязательные ключевые слова для статьи (через запятую)',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'красота, стиль, мода'
        })
    )
    
    task_forbidden_words_text = forms.CharField(
        required=False,
        label='Запрещённые слова в статье (через запятую)',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'спам, реклама'
        })
    )
    
    task_tone_text = forms.CharField(
        required=False,
        label='Требуемый тон статьи',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'дружелюбный и профессиональный'
        })
    )
    
    task_structure_text = forms.CharField(
        required=False,
        label='Требования к структуре статьи',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Введение, основная часть, заключение'
        })
    )
    
    task_additional_rules_text = forms.CharField(
        required=False,
        label='Дополнительные правила для статьи',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Особые требования к оформлению'
        })
    )
    
    class Meta:
        model = ContentTask
        fields = [
            'title',
            'description',
            'category',
            'tags',
            'deadline',
            'required_word_count',
            'required_links',
            'required_keywords',
            'reward',
            'max_completions'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Название задания'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Подробное описание задания'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control'
            }),
            'tags': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'красота, мода, стиль'
            }),
            'deadline': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'required_word_count': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 100
            }),
            'required_links': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'https://example.com/article1\nhttps://example.com/article2'
            }),
            'required_keywords': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'ключевая фраза 1\nключевая фраза 2'
            }),
            'reward': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'max_completions': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'value': 1
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Если редактируем существующее задание, заполняем критерии
        if self.instance and self.instance.pk and self.instance.task_criteria:
            criteria = self.instance.task_criteria
            self.fields['task_min_length'].initial = criteria.get('min_length', '')
            self.fields['task_max_length'].initial = criteria.get('max_length', '')
            self.fields['task_required_keywords_text'].initial = ', '.join(criteria.get('required_keywords', []))
            self.fields['task_forbidden_words_text'].initial = ', '.join(criteria.get('forbidden_words', []))
            self.fields['task_tone_text'].initial = criteria.get('tone', '')
            self.fields['task_structure_text'].initial = criteria.get('structure', '')
            self.fields['task_additional_rules_text'].initial = criteria.get('additional_rules', '')
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Собираем task_criteria из упрощённых полей в JSON
        task_criteria = {}
        
        if self.cleaned_data.get('task_min_length'):
            task_criteria['min_length'] = self.cleaned_data['task_min_length']
        
        if self.cleaned_data.get('task_max_length'):
            task_criteria['max_length'] = self.cleaned_data['task_max_length']
        
        if self.cleaned_data.get('task_required_keywords_text'):
            keywords = [kw.strip() for kw in self.cleaned_data['task_required_keywords_text'].split(',') if kw.strip()]
            if keywords:
                task_criteria['required_keywords'] = keywords
        
        if self.cleaned_data.get('task_forbidden_words_text'):
            words = [w.strip() for w in self.cleaned_data['task_forbidden_words_text'].split(',') if w.strip()]
            if words:
                task_criteria['forbidden_words'] = words
        
        if self.cleaned_data.get('task_tone_text'):
            task_criteria['tone'] = self.cleaned_data['task_tone_text']
        
        if self.cleaned_data.get('task_structure_text'):
            task_criteria['structure'] = self.cleaned_data['task_structure_text']
        
        if self.cleaned_data.get('task_additional_rules_text'):
            task_criteria['additional_rules'] = self.cleaned_data['task_additional_rules_text']
        
        instance.task_criteria = task_criteria
        
        if commit:
            instance.save()
        
        return instance

"""Форма сдачи задания"""
class SubmitTaskForm(forms.Form):
    """Форма сдачи задания"""
    
    article_url = forms.URLField(
        label='Ссылка на статью',
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://idealimage.ru/article/...'
        })
    )
    
    comments = forms.CharField(
        required=False,
        label='Комментарии (необязательно)',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Дополнительные комментарии к работе'
        })
    )


# PromptTemplateForm и DjangoQScheduleForm перенесены (см. выше)

