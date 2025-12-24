"""
Формы для управления рекламой
"""
from django import forms
from .models import AdBanner, AdCampaign, AdPlace, ContextAd, Advertiser, AdSchedule


class AdBannerForm(forms.ModelForm):
    """Форма создания/редактирования баннера"""
    
    class Meta:
        model = AdBanner
        fields = [
            'campaign', 'place', 'name', 'banner_type',
            'image', 'video', 'html_content', 'target_url',
            'alt_text', 'is_active', 'unlimited_impressions', 'banner_height', 'priority', 'weight',
            # Поля для карточек
            'card1_type', 'card1_icon', 'card1_title', 'card1_text', 'card1_image', 'card1_video', 'card1_url',
            'card2_type', 'card2_icon', 'card2_title', 'card2_text', 'card2_image', 'card2_video', 'card2_url',
            'card3_type', 'card3_icon', 'card3_title', 'card3_text', 'card3_image', 'card3_video', 'card3_url',
            'card4_type', 'card4_icon', 'card4_title', 'card4_text', 'card4_image', 'card4_video', 'card4_url',
        ]
        widgets = {
            'campaign': forms.Select(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500'
            }),
            'place': forms.Select(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500'
            }),
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500',
                'placeholder': 'Например: Баннер "Летняя распродажа"'
            }),
            'banner_type': forms.Select(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500'
            }),
            'image': forms.FileInput(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500',
                'accept': 'image/*'
            }),
            'video': forms.FileInput(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500',
                'accept': 'video/*'
            }),
            'html_content': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500',
                'rows': 6,
                'placeholder': '<div style="padding:20px;">Ваш HTML код</div>'
            }),
            'target_url': forms.URLInput(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500',
                'placeholder': 'https://example.com'
            }),
            'alt_text': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500',
                'placeholder': 'Альтернативный текст для изображения'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-orange-600 bg-gray-50 dark:bg-gray-700 border-gray-300 dark:border-gray-600 rounded focus:ring-2 focus:ring-orange-500'
            }),
            'unlimited_impressions': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-orange-600 bg-gray-50 dark:bg-gray-700 border-gray-300 dark:border-gray-600 rounded focus:ring-2 focus:ring-orange-500'
            }),
            'banner_height': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500',
                'min': 50,
                'max': 300,
                'placeholder': '100'
            }),
            'priority': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500',
                'min': 1,
                'max': 10
            }),
            'weight': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500',
                'min': 1
            }),
            # Виджеты для карточек
            'card1_type': forms.Select(attrs={'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg'}),
            'card1_icon': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg', 'placeholder': '📸'}),
            'card1_title': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg', 'placeholder': 'Заголовок'}),
            'card1_text': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg', 'placeholder': 'Текст описания'}),
            'card1_image': forms.FileInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg', 'accept': 'image/*'}),
            'card1_video': forms.FileInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg', 'accept': 'video/*'}),
            'card2_type': forms.Select(attrs={'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg'}),
            'card2_icon': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg', 'placeholder': '🎥'}),
            'card2_title': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg', 'placeholder': 'Заголовок'}),
            'card2_text': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg', 'placeholder': 'Текст описания'}),
            'card2_image': forms.FileInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg', 'accept': 'image/*'}),
            'card2_video': forms.FileInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg', 'accept': 'video/*'}),
            'card3_type': forms.Select(attrs={'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg'}),
            'card3_icon': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg', 'placeholder': '🎨'}),
            'card3_title': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg', 'placeholder': 'Заголовок'}),
            'card3_text': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg', 'placeholder': 'Текст описания'}),
            'card3_image': forms.FileInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg', 'accept': 'image/*'}),
            'card3_video': forms.FileInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg', 'accept': 'video/*'}),
            'card4_type': forms.Select(attrs={'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg'}),
            'card4_icon': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg', 'placeholder': '✨'}),
            'card4_title': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg', 'placeholder': 'Заголовок'}),
            'card4_text': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg', 'placeholder': 'Текст описания'}),
            'card4_image': forms.FileInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg', 'accept': 'image/*'}),
            'card4_video': forms.FileInput(attrs={'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg', 'accept': 'video/*'}),
            # URL для карточек
            'card1_url': forms.URLInput(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg',
                'placeholder': 'https://example.com'
            }),
            'card2_url': forms.URLInput(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg',
                'placeholder': 'https://example.com'
            }),
            'card3_url': forms.URLInput(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg',
                'placeholder': 'https://example.com'
            }),
            'card4_url': forms.URLInput(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg',
                'placeholder': 'https://example.com'
            }),
        }


class ContextAdForm(forms.ModelForm):
    """Форма создания/редактирования контекстной рекламы"""
    
    class Meta:
        model = ContextAd
        fields = [
            'campaign', 'keyword_phrase', 'anchor_text', 'target_url',
            'is_active', 'insertion_type', 'expire_date',
            'cost_per_click', 'priority', 'max_insertions_per_article'
        ]
        widgets = {
            'campaign': forms.Select(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500'
            }),
            'keyword_phrase': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500',
                'placeholder': 'Например: модная одежда'
            }),
            'anchor_text': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500',
                'placeholder': 'Например: стильная одежда 2024'
            }),
            'target_url': forms.URLInput(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500',
                'placeholder': 'https://example.com'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-purple-600 bg-gray-50 dark:bg-gray-700 border-gray-300 dark:border-gray-600 rounded focus:ring-2 focus:ring-purple-500'
            }),
            'insertion_type': forms.Select(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500'
            }),
            'expire_date': forms.DateInput(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500',
                'type': 'date'
            }),
            'cost_per_click': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500',
                'step': '0.01',
                'min': '0'
            }),
            'priority': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500',
                'min': 1,
                'max': 10
            }),
            'max_insertions_per_article': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500',
                'min': 1
            }),
        }


class AdCampaignForm(forms.ModelForm):
    """Форма создания/редактирования кампании"""
    
    class Meta:
        model = AdCampaign
        fields = [
            'advertiser', 'name', 'budget', 'cost_per_click',
            'cost_per_impression', 'start_date', 'end_date',
            'is_active', 'target_audience', 'notes'
        ]
        widgets = {
            'advertiser': forms.Select(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
            }),
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Например: Летняя кампания 2024'
            }),
            'budget': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'step': '0.01',
                'min': '0'
            }),
            'cost_per_click': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'step': '0.01',
                'min': '0'
            }),
            'cost_per_impression': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'step': '0.01',
                'min': '0'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'type': 'date'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-blue-600 bg-gray-50 dark:bg-gray-700 border-gray-300 dark:border-gray-600 rounded focus:ring-2 focus:ring-blue-500'
            }),
            'target_audience': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'rows': 3,
                'placeholder': '{"age": "18-35", "interests": ["мода", "красота"]}'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'rows': 3,
                'placeholder': 'Дополнительные заметки'
            }),
        }


class AdvertiserForm(forms.ModelForm):
    """Форма создания/редактирования рекламодателя"""
    
    class Meta:
        model = Advertiser
        fields = ['name', 'contact_email', 'contact_phone', 'company_info', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500',
                'placeholder': 'Название компании'
            }),
            'contact_email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500',
                'placeholder': 'email@example.com'
            }),
            'contact_phone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500',
                'placeholder': '+7 (999) 123-45-67'
            }),
            'company_info': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500',
                'rows': 4,
                'placeholder': 'Информация о компании'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-green-600 bg-gray-50 dark:bg-gray-700 border-gray-300 dark:border-gray-600 rounded focus:ring-2 focus:ring-green-500'
            }),
        }

