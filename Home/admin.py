from django.contrib import admin
from django.utils.html import format_html
from .models import LandingSection, LandingTheme, LandingConfig, Portal


@admin.register(LandingSection)
class LandingSectionAdmin(admin.ModelAdmin):
    list_display = ['section_icon', 'section', 'media_type', 'preview_thumb', 'ai_generated', 'is_active', 'updated_at']
    list_filter = ['media_type', 'is_active', 'ai_generated', 'section']
    search_fields = ['section', 'ai_search_query']
    readonly_fields = ['created_at', 'updated_at', 'preview_image', 'preview_video']
    
    fieldsets = (
        ('🎯 Основные настройки', {
            'fields': ('section', 'media_type', 'is_active')
        }),
        ('🖼️ Медиафайлы', {
            'fields': (
                'background_image',
                'preview_image',
                'background_video',
                'preview_video',
                'video_url',
            ),
            'description': 'Загрузите изображение или видео для фона секции'
        }),
        ('🎨 Стилизация', {
            'fields': ('gradient_colors', 'opacity', 'overlay_color', 'overlay_opacity'),
            'classes': ('collapse',),
        }),
        ('🤖 AI Информация', {
            'fields': ('ai_generated', 'ai_search_query'),
            'classes': ('collapse',),
        }),
        ('📅 Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def section_icon(self, obj):
        """Отображение иконки секции"""
        icons = dict(obj.SECTION_CHOICES)
        return icons.get(obj.section, obj.section)
    section_icon.short_description = 'Секция'
    
    def preview_thumb(self, obj):
        """Миниатюра превью в списке"""
        if obj.media_type == 'image' and obj.background_image:
            return format_html(
                '<img src="{}" style="width: 80px; height: 45px; object-fit: cover; border-radius: 4px;" />',
                obj.background_image.url
            )
        elif obj.media_type == 'video' and obj.background_video:
            return format_html(
                '<span style="display:inline-block; width:80px; height:45px; background:#333; border-radius:4px; text-align:center; line-height:45px; color:white;">▶️ Video</span>'
            )
        elif obj.media_type == 'gradient':
            return format_html(
                '<div style="width:80px; height:45px; border-radius:4px;" class="{}"></div>',
                obj.gradient_colors
            )
        return '—'
    preview_thumb.short_description = 'Превью'
    
    def preview_image(self, obj):
        """Полное превью изображения"""
        if obj.background_image:
            return format_html(
                '<img src="{}" style="max-width: 100%; max-height: 400px; border-radius: 8px;" />',
                obj.background_image.url
            )
        return 'Изображение не загружено'
    preview_image.short_description = 'Превью изображения'
    
    def preview_video(self, obj):
        """Превью видео"""
        if obj.background_video:
            return format_html(
                '<video controls style="max-width: 100%; max-height: 400px; border-radius: 8px;"><source src="{}" type="video/mp4"></video>',
                obj.background_video.url
            )
        elif obj.video_url:
            return format_html('<a href="{}" target="_blank">🔗 Открыть видео</a>', obj.video_url)
        return 'Видео не загружено'
    preview_video.short_description = 'Превью видео'
    
    actions = ['activate_sections', 'deactivate_sections', 'reset_to_gradient']
    
    def activate_sections(self, request, queryset):
        """Активировать выбранные секции"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'Активировано секций: {updated}')
    activate_sections.short_description = '✅ Активировать выбранные секции'
    
    def deactivate_sections(self, request, queryset):
        """Деактивировать выбранные секции"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Деактивировано секций: {updated}')
    deactivate_sections.short_description = '❌ Деактивировать выбранные секции'
    
    def reset_to_gradient(self, request, queryset):
        """Сбросить на градиент по умолчанию"""
        updated = queryset.update(
            media_type='gradient',
            gradient_colors='from-pink-500 via-purple-500 to-indigo-600',
            background_image=None,
            background_video=None,
            video_url=''
        )
        self.message_user(request, f'Сброшено на градиент: {updated} секций')
    reset_to_gradient.short_description = '🎨 Сбросить на градиент по умолчанию'


@admin.register(LandingTheme)
class LandingThemeAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_by', 'created_at', 'actions_buttons']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'style_prompt']
    readonly_fields = ['created_at', 'created_by', 'preview_theme', 'sections_preview']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'style_prompt', 'is_active')
        }),
        ('Превью', {
            'fields': ('preview_image', 'preview_theme'),
        }),
        ('Конфигурация', {
            'fields': ('sections_preview',),
            'classes': ('collapse',),
        }),
        ('Метаданные', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',),
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def actions_buttons(self, obj):
        """Кнопки действий"""
        return format_html(
            '<a class="button" href="/admin/Home/landingtheme/{}/apply/">Применить</a>',
            obj.pk
        )
    actions_buttons.short_description = 'Действия'
    
    def preview_theme(self, obj):
        """Превью темы"""
        if obj.preview_image:
            return format_html(
                '<img src="{}" style="max-width: 600px; max-height: 400px; border-radius: 8px;" />',
                obj.preview_image.url
            )
        return 'Превью не загружено'
    preview_theme.short_description = 'Превью темы'
    
    def sections_preview(self, obj):
        """Предпросмотр конфигурации секций"""
        if not obj.sections_config:
            return 'Конфигурация пуста'
        
        import json
        formatted_json = json.dumps(obj.sections_config, indent=2, ensure_ascii=False)
        return format_html('<pre style="background: #f5f5f5; padding: 10px; border-radius: 4px;">{}</pre>', formatted_json)
    sections_preview.short_description = 'Конфигурация секций'
    
    actions = ['apply_selected_theme']
    
    def apply_selected_theme(self, request, queryset):
        """Применить выбранную тему"""
        if queryset.count() > 1:
            self.message_user(request, 'Выберите только одну тему для применения', level='error')
            return
        
        theme = queryset.first()
        if theme.apply_theme():
            self.message_user(request, f'Тема "{theme.name}" успешно применена!')
        else:
            self.message_user(request, 'Ошибка применения темы', level='error')
    apply_selected_theme.short_description = '✨ Применить выбранную тему'


@admin.register(LandingConfig)
class LandingConfigAdmin(admin.ModelAdmin):
    """Админка для управления активным лендингом"""
    
    list_display = ['id', 'active_landing_display', 'updated_at', 'updated_by']
    
    fieldsets = (
        ('🎨 Управление главной страницей', {
            'fields': ('active_landing',),
            'description': '''
                <div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                    <h3 style="margin-top: 0;">💡 Переключение между лендингами</h3>
                    <ul style="margin-bottom: 0;">
                        <li><strong>Лендинг №1 (Оригинальный IdealImage):</strong> Основной дизайн сайта с категориями, статьями и AI-функционалом</li>
                        <li><strong>Лендинг №2 (Салон красоты):</strong> Дизайн в стиле салона красоты с услугами, портфолио и формой записи</li>
                    </ul>
                    <p style="margin-bottom: 0; margin-top: 10px;"><em>Изменения применяются мгновенно после сохранения.</em></p>
                </div>
            '''
        }),
        ('📊 Информация', {
            'fields': ('updated_at', 'updated_by'),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ['updated_at', 'updated_by']
    
    def active_landing_display(self, obj):
        """Отображение активного лендинга с иконкой"""
        if obj.active_landing == 'landing1':
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">🎨 Лендинг №1 (IdealImage)</span>'
            )
        else:
            return format_html(
                '<span style="color: #ff6b9d; font-weight: bold;">💅 Лендинг №2 (Салон красоты)</span>'
            )
    active_landing_display.short_description = 'Активный лендинг'
    
    def save_model(self, request, obj, form, change):
        """Сохранение с указанием пользователя"""
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
        
        # Сброс кэша при изменении
        from django.core.cache import cache
        cache.clear()
        
        self.message_user(
            request,
            f'✅ Главная страница переключена на: {obj.get_active_landing_display()}',
            level='success'
        )
    
    def has_delete_permission(self, request, obj=None):
        """Запрещаем удаление (singleton модель)"""
        return False
    
    def has_add_permission(self, request):
        """Запрещаем создание новых записей если уже есть одна"""
        return not LandingConfig.objects.exists()


@admin.register(Portal)
class PortalAdmin(admin.ModelAdmin):
    """Админка для управления порталами в секции 'Сеть порталов'"""
    
    list_display = ['status_icon', 'name', 'description_short', 'portal_preview', 'is_main', 'is_active', 'order', 'updated_at']
    list_filter = ['is_active', 'is_main', 'created_at']
    search_fields = ['name', 'description', 'url']
    list_editable = ['order', 'is_active', 'is_main']
    readonly_fields = ['created_at', 'updated_at', 'image_preview']
    
    fieldsets = (
        ('🌐 Основная информация', {
            'fields': ('name', 'description', 'url')
        }),
        ('🖼️ Изображение', {
            'fields': ('image', 'image_preview'),
            'description': 'Загрузите изображение портала (рекомендуемый размер: 400x300px)'
        }),
        ('⚙️ Настройки', {
            'fields': ('is_main', 'is_active', 'order'),
            'description': 'Главный портал выделяется специальной рамкой'
        }),
        ('📅 Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def status_icon(self, obj):
        """Иконка статуса"""
        if obj.is_main:
            return '👑'
        return '✅' if obj.is_active else '❌'
    status_icon.short_description = ''
    
    def description_short(self, obj):
        """Краткое описание"""
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_short.short_description = 'Описание'
    
    def portal_preview(self, obj):
        """Миниатюра в списке"""
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 100px; height: 75px; object-fit: cover; border-radius: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);" />',
                obj.image.url
            )
        return '—'
    portal_preview.short_description = 'Превью'
    
    def image_preview(self, obj):
        """Полное превью изображения"""
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width: 400px; max-height: 300px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);" />',
                obj.image.url
            )
        return 'Изображение не загружено'
    image_preview.short_description = 'Превью изображения'
    
    actions = ['mark_as_main', 'mark_as_regular', 'activate_portals', 'deactivate_portals']
    
    def mark_as_main(self, request, queryset):
        """Отметить как главный портал"""
        if queryset.count() > 1:
            self.message_user(request, 'Можно выбрать только один главный портал', level='warning')
            return
        
        # Снимаем флаг "главный" со всех
        Portal.objects.update(is_main=False)
        # Ставим выбранному
        updated = queryset.update(is_main=True, is_active=True)
        self.message_user(request, f'Установлен главный портал: {queryset.first().name}')
    mark_as_main.short_description = '👑 Отметить как главный портал'
    
    def mark_as_regular(self, request, queryset):
        """Снять отметку главного портала"""
        updated = queryset.update(is_main=False)
        self.message_user(request, f'Снята отметка "главный" с {updated} порталов')
    mark_as_regular.short_description = '📌 Снять отметку главного'
    
    def activate_portals(self, request, queryset):
        """Активировать порталы"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'Активировано порталов: {updated}')
    activate_portals.short_description = '✅ Активировать выбранные'
    
    def deactivate_portals(self, request, queryset):
        """Деактивировать порталы"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Деактивировано порталов: {updated}')
    deactivate_portals.short_description = '❌ Деактивировать выбранные'
