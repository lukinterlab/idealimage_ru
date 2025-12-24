from django import forms
from django.contrib.auth import get_user_model
from .models import Donation, DonationSettings, AuthorPenaltyReward

User = get_user_model()


class DonationForm(forms.ModelForm):
    """Форма для создания доната"""
    
    class Meta:
        model = Donation
        fields = ['amount', 'payment_method', 'user_email', 'user_name', 'message', 'is_anonymous']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-input mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'placeholder': 'Введите сумму',
                'min': '100',
                'step': '1',
            }),
            'payment_method': forms.RadioSelect(attrs={
                'class': 'payment-method-radio',
            }),
            'user_email': forms.EmailInput(attrs={
                'class': 'form-input mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'placeholder': 'your@email.com',
            }),
            'user_name': forms.TextInput(attrs={
                'class': 'form-input mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'placeholder': 'Ваше имя (необязательно)',
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-textarea mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'placeholder': 'Ваше сообщение или пожелание (необязательно)',
                'rows': 3,
            }),
            'is_anonymous': forms.CheckboxInput(attrs={
                'class': 'form-checkbox h-5 w-5 text-indigo-600 rounded',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Получаем настройки
        settings = DonationSettings.get_settings()
        
        # Обновляем ограничения по сумме
        self.fields['amount'].widget.attrs.update({
            'min': str(settings.min_amount),
            'max': str(settings.max_amount),
        })
        
        # Динамически формируем выбор способов оплаты на основе настроек
        payment_choices = []
        if settings.enable_yandex:
            payment_choices.append(('yandex', 'Яндекс.Касса'))
        if settings.enable_sberpay:
            payment_choices.append(('sberpay', 'СберПей'))
        if settings.enable_sbp:
            payment_choices.append(('sbp', 'Система Быстрых Платежей'))
        if settings.enable_qr:
            payment_choices.append(('qr', 'QR-код'))
        
        self.fields['payment_method'].choices = payment_choices
        
        # Устанавливаем обязательные поля
        self.fields['user_email'].required = True
        self.fields['user_name'].required = False
        self.fields['message'].required = False
        self.fields['is_anonymous'].required = False
        
        # Добавляем подсказки
        self.fields['amount'].help_text = f'От {settings.min_amount} до {settings.max_amount} ₽'
        self.fields['is_anonymous'].help_text = 'Ваше имя не будет показано публично'
    
    def clean_amount(self):
        """Валидация суммы доната"""
        amount = self.cleaned_data.get('amount')
        settings = DonationSettings.get_settings()
        
        if amount < settings.min_amount:
            raise forms.ValidationError(f'Минимальная сумма доната: {settings.min_amount} ₽')
        
        if amount > settings.max_amount:
            raise forms.ValidationError(f'Максимальная сумма доната: {settings.max_amount} ₽')
        
        return amount


class QuickDonationForm(forms.Form):
    """Быстрая форма доната с предустановленными суммами"""
    
    preset_amount = forms.ChoiceField(
        label='Выберите сумму',
        widget=forms.RadioSelect(attrs={
            'class': 'preset-amount-radio',
        }),
        required=False
    )
    
    custom_amount = forms.DecimalField(
        label='Или введите свою сумму',
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-input mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
            'placeholder': 'Своя сумма',
        })
    )
    
    payment_method = forms.ChoiceField(
        label='Способ оплаты',
        widget=forms.RadioSelect(attrs={
            'class': 'payment-method-radio',
        })
    )
    
    user_email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-input mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
            'placeholder': 'your@email.com',
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        settings = DonationSettings.get_settings()
        
        # Формируем выбор предустановленных сумм
        preset_choices = [(str(amount), f'{amount} ₽') for amount in settings.preset_amounts]
        self.fields['preset_amount'].choices = preset_choices
        
        # Формируем выбор способов оплаты
        payment_choices = []
        if settings.enable_yandex:
            payment_choices.append(('yandex', 'Яндекс.Касса'))
        if settings.enable_sberpay:
            payment_choices.append(('sberpay', 'СберПей'))
        if settings.enable_sbp:
            payment_choices.append(('sbp', 'Система Быстрых Платежей'))
        if settings.enable_qr:
            payment_choices.append(('qr', 'QR-код'))
        
        self.fields['payment_method'].choices = payment_choices
    
    def clean(self):
        cleaned_data = super().clean()
        preset_amount = cleaned_data.get('preset_amount')
        custom_amount = cleaned_data.get('custom_amount')
        
        if not preset_amount and not custom_amount:
            raise forms.ValidationError('Выберите сумму из списка или введите свою')
        
        # Определяем финальную сумму
        if custom_amount:
            final_amount = custom_amount
        else:
            final_amount = float(preset_amount)
        
        settings = DonationSettings.get_settings()
        
        if final_amount < settings.min_amount:
            raise forms.ValidationError(f'Минимальная сумма доната: {settings.min_amount} ₽')
        
        if final_amount > settings.max_amount:
            raise forms.ValidationError(f'Максимальная сумма доната: {settings.max_amount} ₽')
        
        cleaned_data['final_amount'] = final_amount
        return cleaned_data


class AuthorPenaltyRewardForm(forms.ModelForm):
    """Форма для создания штрафа/премии автору"""
    
    class Meta:
        model = AuthorPenaltyReward
        fields = ['author', 'type', 'amount', 'amount_type', 'reason', 
                  'applied_to', 'applied_from', 'applied_until', 'is_active']
        widgets = {
            'author': forms.Select(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500'
            }),
            'type': forms.RadioSelect(attrs={
                'class': 'flex gap-4'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'amount_type': forms.RadioSelect(attrs={
                'class': 'flex gap-4'
            }),
            'reason': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500',
                'rows': 4,
                'placeholder': 'Опишите причину назначения штрафа или премии'
            }),
            'applied_to': forms.Select(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500'
            }),
            'applied_from': forms.DateTimeInput(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500',
                'type': 'datetime-local'
            }),
            'applied_until': forms.DateTimeInput(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500',
                'type': 'datetime-local'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-green-600 bg-gray-50 dark:bg-gray-700 border-gray-300 dark:border-gray-600 rounded focus:ring-2 focus:ring-green-500'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Только авторы в списке
        self.fields['author'].queryset = User.objects.filter(
            profile__is_author=True
        ).order_by('username')
