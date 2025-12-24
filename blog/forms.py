from django import forms
from ckeditor_uploader.widgets import CKEditorUploadingWidget

from .models import *


class PostAdminForm(forms.ModelForm):
    content = forms.CharField(
        label='Полное описание',
        widget=CKEditorUploadingWidget(),
        required=False
    )
    
    class Meta:
        model = Post
        fields = '__all__'
    
    def clean_kartinka(self):
        """
        Валидация видео файла при загрузке
        """
        kartinka = self.cleaned_data.get('kartinka')
        
        if not kartinka:
            return kartinka
        
        # Проверяем, является ли файл видео
        video_extensions = ['.mp4', '.webm', '.mov', '.avi']
        file_ext = kartinka.name.lower() if hasattr(kartinka, 'name') else ''
        is_video = any(file_ext.endswith(ext) for ext in video_extensions)
        
        if is_video:
            # Валидируем видео файл
            from blog.utils_video_processing import validate_video_file
            is_valid, error_message = validate_video_file(kartinka)
            
            if not is_valid:
                raise forms.ValidationError(error_message or 'Ошибка валидации видео файла')
        
        return kartinka


class PostCreateForm(forms.ModelForm):
    """
    Форма добавления статей на сайте
    """
    
    # Явно указываем виджет CKEditor для поля content
    content = forms.CharField(
        label='Полное описание',
        widget=CKEditorUploadingWidget(),
        required=False
    )
    
    # Поля для AI-помощника
    use_ai_assistant = forms.BooleanField(
        required=False,
        label='🤖 Попросить AI улучшить черновик',
        help_text='AI-помощник улучшит ваш текст, сохраняя авторский стиль',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    ai_improvement_style = forms.ChoiceField(
        required=False,
        label='Стиль улучшения',
        choices=[
            ('balanced', '⚖️ Сбалансированный (рекомендуется)'),
            ('literary', '✍️ Литературный и художественный'),
            ('seo', '🔍 SEO-оптимизированный'),
            ('emotional', '💖 Эмоциональный и вдохновляющий'),
        ],
        initial='balanced',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    ai_custom_prompt = forms.CharField(
        required=False,
        label='Дополнительные критерии для AI',
        help_text='Опишите дополнительные требования к тексту (например: "добавь больше примеров", "сделай короче")',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Например: добавь больше эмоций, используй метафоры, сократи до 500 слов...'
        })
    )
    
    generate_image = forms.BooleanField(
        required=False,
        label='🎨 Сгенерировать новое главное изображение',
        help_text='AI создаст новое изображение для статьи',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    image_generation_prompt = forms.CharField(
        required=False,
        label='Сюжет для изображения',
        help_text='Опишите что должно быть на изображении (оставьте пустым для автоматического создания на основе текста)',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Например: красивая девушка с длинными волосами в солнечный день...'
        })
    )
    
    class Meta:
        model = Post
        fields = ('title', 'category', 'description', 'content', 'kartinka', 'tags', 'status')

    def __init__(self, *args, **kwargs):
        """
        Обновление стилей формы под Bootstrap
        """
        super().__init__(*args, **kwargs)
        
        # Убеждаемся, что для поля content установлен виджет CKEditor
        if 'content' in self.fields:
            if not isinstance(self.fields['content'].widget, CKEditorUploadingWidget):
                self.fields['content'].widget = CKEditorUploadingWidget()
        
        ai_fields = ['use_ai_assistant', 'ai_improvement_style', 'ai_custom_prompt', 
                     'generate_image', 'image_generation_prompt']
        for field in self.fields:
            if field not in ai_fields and field != 'content':
                self.fields[field].widget.attrs.update({
                    'class': 'form-control',
                    'autocomplete': 'off'
                })
            
        



class PostUpdateForm(PostCreateForm):
    """
    Форма обновления статьи на сайте
    """
    class Meta:
        model = Post
        fields = PostCreateForm.Meta.fields + ('updater', 'fixed')

    def __init__(self, *args, **kwargs):
        """
        Обновление стилей формы под Bootstrap
        """
        super().__init__(*args, **kwargs)
        self.fields['fixed'].widget.attrs.update({
                'class': 'form-check-input'
        })            
            
    
    
        
        
        
class CommentForm(forms.ModelForm):
    """
    Форма добавления комментариев к статьям
    """
    author_comment = forms.CharField(label='', widget=forms.TextInput(
        attrs={'cols': 5, 'rows': 5, 'placeholder': 'Ваше Ф.И.О.', 'class': 'form-control'}))
    email = forms.CharField(label='', widget=forms.TextInput(
        attrs={'cols': 5, 'rows': 5, 'placeholder': 'Ваш email:', 'class': 'form-control'}))
    content = forms.CharField(label='', widget=forms.Textarea(
        attrs={'cols': 30, 'rows': 5, 'placeholder': 'Напишите комментарий', 'class': 'form-control'}))

    class Meta:
        model = Comment
        fields = ('author_comment', 'email', 'content')
     
     
       
class SearchForm(forms.Form):  
    query = forms.CharField(max_length=100,  
                            widget=forms.TextInput(  
                                attrs={  
                                    'class': 'form-control me-2 mx-1',  
                                    'placeholder': 'Что ищем?',  
                                }  
                            ))  

    def clean_query(self):  
        query = self.cleaned_data['query']  
        cleaned_query = " ".join(query.split())  
        return cleaned_query
        
    
        
        
        