"""
Формы для работы с шаблонами промптов.
Перенесено из Asistent/forms.py для модульности.
"""
from django import forms
from Asistent.models import PromptTemplate


class PromptTemplateForm(forms.ModelForm):
    """Форма для создания/редактирования шаблона промпта"""
    
    change_summary = forms.CharField(
        required=False,
        label='Описание изменений',
        widget=forms.Textarea(attrs={
            'class': 'form-control w-full',
            'rows': 3,
            'placeholder': 'Коротко опишите внесённые изменения'
        })
    )
    
    class Meta:
        model = PromptTemplate
        fields = [
            'category', 'name', 'template', 'variables',
            'blog_category', 'default_author', 'title_criteria',
            'image_source_type', 'image_search_criteria', 'image_generation_criteria', 'auto_process_image',
            'tags_criteria',
            'content_source_type', 'content_source_urls', 'parse_first_paragraph',
            'uploaded_media',
            'is_active'
        ]
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control w-full'}),
            'name': forms.TextInput(attrs={'class': 'form-control w-full', 'placeholder': 'Название промпта'}),
            'template': forms.Textarea(attrs={'class': 'form-control w-full', 'rows': 15, 'placeholder': 'Текст промпта с {переменными}'}),
            'variables': forms.Textarea(attrs={'class': 'form-control w-full', 'rows': 4, 'placeholder': '["переменная1", "переменная2"]'}),
            'blog_category': forms.Select(attrs={'class': 'form-control w-full'}),
            'default_author': forms.Select(attrs={'class': 'form-control w-full'}),
            'title_criteria': forms.Textarea(attrs={'class': 'form-control w-full', 'rows': 4}),
            'image_source_type': forms.Select(attrs={'class': 'form-control w-full'}),
            'image_search_criteria': forms.Textarea(attrs={'class': 'form-control w-full', 'rows': 4}),
            'image_generation_criteria': forms.Textarea(attrs={'class': 'form-control w-full', 'rows': 4}),
            'auto_process_image': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tags_criteria': forms.TextInput(attrs={'class': 'form-control w-full', 'placeholder': '"тег1", переменная, "тег2"'}),
            'content_source_type': forms.Select(attrs={'class': 'form-control w-full'}),
            'content_source_urls': forms.Textarea(attrs={'class': 'form-control w-full', 'rows': 5, 'placeholder': 'https://example.com/article1\nhttps://example.com/article2'}),
            'parse_first_paragraph': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'uploaded_media': forms.FileInput(attrs={'class': 'form-control w-full'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['change_summary'].help_text = 'Это описание попадёт в историю версий.'
        else:
            self.fields['change_summary'].initial = 'Создание шаблона'
            self.fields['change_summary'].help_text = 'Опишите цель и контекст нового шаблона.'

        content_field = self.fields.get('content_source_type')
        if content_field:
            filtered_choices = [
                choice for choice in content_field.choices
                if choice[0] != 'hybrid'
            ]
            content_field.choices = filtered_choices
            initial_value = self.initial.get('content_source_type') or self.instance.content_source_type
            if initial_value == 'hybrid':
                self.initial['content_source_type'] = 'parse'

