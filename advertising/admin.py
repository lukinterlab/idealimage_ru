"""
Административная панель для управления рекламой
"""
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count
from django.urls import reverse
from django.utils import timezone
from .models import (
    AdPlace, Advertiser, AdCampaign, AdBanner, AdSchedule,
    ContextAd, AdInsertion, AdClick, AdImpression,
    AdPerformanceML, AdRecommendation, AdActionLog, ExternalScript, AdsTxtSettings
)


@admin.register(AdPlace)
class AdPlaceAdmin(admin.ModelAdmin):
    """Админка для рекламных мест"""
    list_display = ('name', 'code', 'placement_type', 'recommended_size', 
                    'is_active', 'position_order', 'banners_count')
    list_filter = ('placement_type', 'is_active')
    search_fields = ('name', 'code', 'description')
    prepopulated_fields = {'code': ('name',)}
    list_editable = ('is_active', 'position_order')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'code', 'description', 'placement_type')
        }),
        ('Параметры', {
            'fields': ('recommended_size', 'position_order', 'max_ads_per_rotation', 'is_active')
        }),
        ('⚙️ Настройки всплывающей рекламы (popup_modal)', {
            'fields': ('popup_test_mode', 'popup_test_interval_seconds', 'popup_delay_seconds', 'popup_cookie_hours'),
            'classes': ('collapse',),
            'description': 'Настройки работают только для рекламного места с кодом "popup_modal"'
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')
    
    def banners_count(self, obj):
        count = obj.banners.filter(is_active=True).count()
        return format_html('<b>{}</b> активных', count)
    banners_count.short_description = 'Баннеров'


@admin.register(Advertiser)
class AdvertiserAdmin(admin.ModelAdmin):
    """Админка для рекламодателей"""
    list_display = ('name', 'contact_email', 'contact_phone', 'is_active', 
                    'total_spent', 'campaigns_count', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'contact_email', 'company_info')
    list_editable = ('is_active',)
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'company_info', 'is_active')
        }),
        ('Контакты', {
            'fields': ('contact_email', 'contact_phone')
        }),
        ('Финансы', {
            'fields': ('total_spent',)
        }),
        ('Даты', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'total_spent')
    
    def campaigns_count(self, obj):
        count = obj.campaigns.count()
        active = obj.campaigns.filter(is_active=True).count()
        return format_html('{} <span style="color: green;">(активных: {})</span>', count, active)
    campaigns_count.short_description = 'Кампаний'
    
    actions = ['update_total_spent']
    
    def update_total_spent(self, request, queryset):
        for advertiser in queryset:
            advertiser.update_total_spent()
        self.message_user(request, f'Обновлено {queryset.count()} рекламодателей')
    update_total_spent.short_description = 'Обновить общую потраченную сумму'


class AdBannerInline(admin.TabularInline):
    """Inline для баннеров в кампании"""
    model = AdBanner
    extra = 0
    fields = ('name', 'place', 'banner_type', 'is_active', 'impressions', 'clicks', 'get_ctr_display')
    readonly_fields = ('impressions', 'clicks', 'get_ctr_display')
    
    def get_ctr_display(self, obj):
        if obj.pk:
            return f"{obj.get_ctr():.2f}%"
        return "-"
    get_ctr_display.short_description = 'CTR'


@admin.register(AdCampaign)
class AdCampaignAdmin(admin.ModelAdmin):
    """Админка для рекламных кампаний"""
    list_display = ('name', 'advertiser', 'budget', 'spent_amount', 'budget_usage',
                    'start_date', 'end_date', 'is_active_status', 'banners_count')
    list_filter = ('is_active', 'start_date', 'end_date', 'advertiser')
    search_fields = ('name', 'advertiser__name', 'notes')
    date_hierarchy = 'start_date'
    inlines = [AdBannerInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('advertiser', 'name', 'is_active', 'created_by')
        }),
        ('Период', {
            'fields': ('start_date', 'end_date')
        }),
        ('Бюджет и стоимость', {
            'fields': ('budget', 'spent_amount', 'cost_per_click', 'cost_per_impression')
        }),
        ('Таргетинг', {
            'fields': ('target_audience',),
            'classes': ('collapse',)
        }),
        ('Дополнительно', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at', 'spent_amount')
    
    def budget_usage(self, obj):
        try:
            percent = float(obj.get_budget_usage_percent() or 0)
            color = 'green' if percent < 70 else 'orange' if percent < 90 else 'red'
            return format_html(
                '<span style="color: {};">{:.1f}%</span>',
                color, percent
            )
        except (ValueError, TypeError):
            return format_html('<span style="color: gray;">0.0%</span>')
    budget_usage.short_description = 'Использование бюджета'
    
    def is_active_status(self, obj):
        if obj.is_active_now():
            return format_html('<span style="color: green;">✓ Активна</span>')
        return format_html('<span style="color: red;">✗ Неактивна</span>')
    is_active_status.short_description = 'Статус'
    
    def banners_count(self, obj):
        return obj.banners.count()
    banners_count.short_description = 'Баннеров'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


class AdScheduleInline(admin.TabularInline):
    """Inline для расписания баннера"""
    model = AdSchedule
    extra = 1
    fields = ('day_of_week', 'start_time', 'end_time', 'max_impressions_per_day', 
              'current_impressions', 'is_active')
    readonly_fields = ('current_impressions',)


@admin.register(AdBanner)
class AdBannerAdmin(admin.ModelAdmin):
    """Админка для баннеров"""
    list_display = ('preview_image', 'name', 'campaign', 'place', 'banner_type', 'is_active',
                    'priority', 'impressions', 'clicks', 'ctr_display', 'revenue_display')
    list_filter = ('banner_type', 'is_active', 'place', 'campaign__advertiser')
    search_fields = ('name', 'campaign__name', 'target_url')
    list_editable = ('is_active', 'priority')
    inlines = [AdScheduleInline]
    readonly_fields = ('created_at', 'updated_at', 'impressions', 'clicks', 'image_preview', 'video_preview')
    
    def get_fieldsets(self, request, obj=None):
        """Динамические fieldsets в зависимости от места баннера"""
        
        # Базовые секции для всех баннеров
        fieldsets = [
            ('Основная информация', {
                'fields': ('campaign', 'place', 'name', 'banner_type', 'is_active', 'unlimited_impressions', 'banner_height')
            }),
            ('Контент', {
                'fields': ('image', 'image_preview', 'video', 'video_preview', 'html_content', 'alt_text')
            }),
        ]
        
        # Определяем нужно ли показывать карточки
        show_cards = True
        place_code = None
        
        if obj and obj.place:
            place_code = obj.place.code
            # Для popup_modal и других мест БЕЗ карточек - НЕ показываем
            if place_code in ['popup_modal', 'ticker_line', 'sidebar_top', 'sidebar_after_author', 'sidebar_after_popular']:
                show_cards = False
        
        # Добавляем карточки только если нужно
        if show_cards:
            fieldsets.extend([
                ('Карточка 1 (для header/footer)', {
                    'fields': ('card1_type', 'card1_icon', 'card1_title', 'card1_text', 'card1_image', 'card1_video', 'card1_url'),
                    'classes': ('collapse',)
                }),
                ('Карточка 2 (для header/footer)', {
                    'fields': ('card2_type', 'card2_icon', 'card2_title', 'card2_text', 'card2_image', 'card2_video', 'card2_url'),
                    'classes': ('collapse',)
                }),
                ('Карточка 3 (для header/footer)', {
                    'fields': ('card3_type', 'card3_icon', 'card3_title', 'card3_text', 'card3_image', 'card3_video', 'card3_url'),
                    'classes': ('collapse',)
                }),
            ])
            
            # Добавляем "Карточка 4" только для 4-карточных баннеров (header и footer)
            # Для 3-карточных баннеров (in_post_middle*, before_article, after_comments) - НЕ показываем карточку 4
            if place_code in ['header_banner', 'footer_banner']:
                fieldsets.append(
                    ('Карточка 4 (для header/footer)', {
                        'fields': ('card4_type', 'card4_icon', 'card4_title', 'card4_text', 'card4_image', 'card4_video', 'card4_url'),
                        'classes': ('collapse',)
                    })
                )
        
        # Добавляем остальные секции
        fieldsets.extend([
            ('Настройки', {
                'fields': ('target_url', 'priority', 'weight')
            }),
            ('Статистика', {
                'fields': ('impressions', 'clicks'),
                'classes': ('collapse',)
            }),
            ('Даты', {
                'fields': ('created_at', 'updated_at'),
                'classes': ('collapse',)
            }),
        ])
        
        return fieldsets
    
    def preview_image(self, obj):
        """Превью для списка"""
        if obj.banner_type == 'image' and obj.image:
            return format_html(
                '<img src="{}" style="max-width: 80px; max-height: 80px; object-fit: cover; border-radius: 4px;" />',
                obj.image.url
            )
        elif obj.banner_type == 'video' and obj.video:
            return format_html(
                '<video style="max-width: 80px; max-height: 80px; object-fit: cover; border-radius: 4px;"><source src="{}" type="video/mp4"></video>',
                obj.video.url
            )
        elif obj.banner_type == 'html':
            return format_html('<div style="width: 80px; height: 80px; background: #f0f0f0; display: flex; align-items: center; justify-content: center; border-radius: 4px; color: #666;">HTML</div>')
        return format_html('<div style="width: 80px; height: 80px; background: #e0e0e0; display: flex; align-items: center; justify-content: center; border-radius: 4px; color: #999;">?</div>')
    preview_image.short_description = 'Превью'
    
    def image_preview(self, obj):
        """Превью изображения в форме редактирования"""
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width: 400px; max-height: 400px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.2);" />',
                obj.image.url
            )
        return format_html('<p style="color: #999; padding: 20px; background: #f5f5f5; border-radius: 8px; text-align: center;">Изображение не загружено. Выберите файл выше.</p>')
    image_preview.short_description = 'Текущее изображение'
    
    def video_preview(self, obj):
        """Превью видео в форме редактирования"""
        if obj.video:
            return format_html(
                '<video controls style="max-width: 500px; max-height: 400px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.2);"><source src="{}" type="video/mp4">Ваш браузер не поддерживает видео.</video>',
                obj.video.url
            )
        return format_html('<p style="color: #999; padding: 20px; background: #f5f5f5; border-radius: 8px; text-align: center;">Видео не загружено. Выберите файл выше.</p>')
    video_preview.short_description = 'Текущее видео'
    
    def ctr_display(self, obj):
        try:
            ctr = float(obj.get_ctr() or 0)
            color = 'green' if ctr > 3 else 'orange' if ctr > 1 else 'red'
            return format_html('<span style="color: {};">{:.2f}%</span>', color, ctr)
        except (ValueError, TypeError):
            return format_html('<span style="color: gray;">0.00%</span>')
    ctr_display.short_description = 'CTR'
    
    def revenue_display(self, obj):
        try:
            revenue = float(obj.get_revenue() or 0)
            return format_html('<b>{:.2f} ₽</b>', revenue)
        except (ValueError, TypeError):
            return format_html('<b>0.00 ₽</b>')
    revenue_display.short_description = 'Доход'
    
    actions = ['activate_banners', 'deactivate_banners']
    
    def activate_banners(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f'Активировано {count} баннеров')
    activate_banners.short_description = 'Активировать выбранные баннеры'
    
    def deactivate_banners(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f'Деактивировано {count} баннеров')
    deactivate_banners.short_description = 'Деактивировать выбранные баннеры'


@admin.register(AdSchedule)
class AdScheduleAdmin(admin.ModelAdmin):
    """Админка для расписаний"""
    list_display = ('banner', 'day_of_week_display', 'start_time', 'end_time',
                    'current_impressions', 'max_impressions_per_day', 'is_active')
    list_filter = ('is_active', 'day_of_week', 'banner__place')
    search_fields = ('banner__name',)
    list_editable = ('is_active',)
    
    def day_of_week_display(self, obj):
        if obj.day_of_week is None:
            return 'Каждый день'
        return obj.get_day_of_week_display()
    day_of_week_display.short_description = 'День недели'


class AdInsertionInline(admin.TabularInline):
    """Inline для вставок контекстной рекламы"""
    model = AdInsertion
    extra = 0
    fields = ('post', 'inserted_by', 'is_active', 'clicks', 'views')
    readonly_fields = ('inserted_by', 'clicks', 'views')


@admin.register(ContextAd)
class ContextAdAdmin(admin.ModelAdmin):
    """Админка для контекстной рекламы"""
    list_display = ('keyword_phrase', 'anchor_text', 'campaign', 'is_active',
                    'insertion_type', 'priority', 'impressions', 'clicks', 'ctr_display')
    list_filter = ('is_active', 'insertion_type', 'campaign__advertiser')
    search_fields = ('keyword_phrase', 'anchor_text', 'target_url')
    list_editable = ('is_active', 'priority')
    inlines = [AdInsertionInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('campaign', 'keyword_phrase', 'anchor_text', 'target_url', 'is_active')
        }),
        ('Настройки вставки', {
            'fields': ('insertion_type', 'expire_date', 'priority', 'max_insertions_per_article')
        }),
        ('Финансы', {
            'fields': ('cost_per_click',)
        }),
        ('Статистика', {
            'fields': ('impressions', 'clicks'),
            'classes': ('collapse',)
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at', 'impressions', 'clicks')
    
    def ctr_display(self, obj):
        try:
            ctr = float(obj.get_ctr() or 0)
            return format_html('{:.2f}%', ctr)
        except (ValueError, TypeError):
            return '0.00%'
    ctr_display.short_description = 'CTR'


@admin.register(AdInsertion)
class AdInsertionAdmin(admin.ModelAdmin):
    """Админка для вставок рекламы"""
    list_display = ('context_ad', 'post_link', 'inserted_by', 'inserted_at',
                    'is_active', 'clicks', 'views', 'ctr_display')
    list_filter = ('is_active', 'inserted_at', 'inserted_by')
    search_fields = ('context_ad__keyword_phrase', 'post__title', 'anchor_text_used')
    date_hierarchy = 'inserted_at'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('context_ad', 'post', 'is_active')
        }),
        ('Детали вставки', {
            'fields': ('inserted_by', 'insertion_position', 'anchor_text_used')
        }),
        ('Статистика', {
            'fields': ('clicks', 'views')
        }),
        ('Удаление', {
            'fields': ('removed_at', 'removal_reason'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('inserted_at', 'inserted_by', 'clicks', 'views')
    
    def post_link(self, obj):
        url = obj.get_article_link()
        return format_html('<a href="{}" target="_blank">{}</a>', url, obj.post.title[:50])
    post_link.short_description = 'Статья'
    
    def ctr_display(self, obj):
        try:
            ctr = float(obj.get_ctr() or 0)
            return f"{ctr:.2f}%"
        except (ValueError, TypeError):
            return "0.00%"
    ctr_display.short_description = 'CTR'


@admin.register(AdClick)
class AdClickAdmin(admin.ModelAdmin):
    """Админка для кликов"""
    list_display = ('ad_type', 'ad_name', 'user', 'ip_address', 'clicked_at')
    list_filter = ('clicked_at', 'ad_banner__campaign', 'context_ad__campaign')
    search_fields = ('ip_address', 'user__username', 'redirect_url')
    date_hierarchy = 'clicked_at'
    readonly_fields = ('ad_banner', 'context_ad', 'ad_insertion', 'user',
                       'session_key', 'ip_address', 'user_agent', 'clicked_at',
                       'referer', 'redirect_url')
    
    def has_add_permission(self, request):
        return False
    
    def ad_type(self, obj):
        if obj.ad_banner:
            return 'Баннер'
        elif obj.context_ad:
            return 'Контекст'
        return '-'
    ad_type.short_description = 'Тип'
    
    def ad_name(self, obj):
        if obj.ad_banner:
            return obj.ad_banner.name
        elif obj.context_ad:
            return obj.context_ad.anchor_text
        return '-'
    ad_name.short_description = 'Название'


@admin.register(AdImpression)
class AdImpressionAdmin(admin.ModelAdmin):
    """Админка для показов"""
    list_display = ('ad_type', 'ad_name', 'user', 'ip_address', 'shown_at', 'time_visible')
    list_filter = ('shown_at', 'viewport_position')
    search_fields = ('ip_address', 'user__username')
    date_hierarchy = 'shown_at'
    readonly_fields = ('ad_banner', 'context_ad', 'ad_insertion', 'user',
                       'session_key', 'ip_address', 'user_agent', 'shown_at',
                       'viewport_position', 'time_visible')
    
    def has_add_permission(self, request):
        return False
    
    def ad_type(self, obj):
        if obj.ad_banner:
            return 'Баннер'
        elif obj.context_ad:
            return 'Контекст'
        return '-'
    ad_type.short_description = 'Тип'
    
    def ad_name(self, obj):
        if obj.ad_banner:
            return obj.ad_banner.name
        elif obj.context_ad:
            return obj.context_ad.anchor_text
        return '-'
    ad_name.short_description = 'Название'


@admin.register(AdPerformanceML)
class AdPerformanceMLAdmin(admin.ModelAdmin):
    """Админка для данных ML"""
    list_display = ('ad_place', 'date', 'hour', 'impressions', 'clicks',
                    'ctr', 'revenue', 'effectiveness_score')
    list_filter = ('date', 'day_of_week', 'device_type', 'user_type', 'ad_place')
    search_fields = ('category',)
    date_hierarchy = 'date'
    readonly_fields = ('created_at',)


@admin.register(AdRecommendation)
class AdRecommendationAdmin(admin.ModelAdmin):
    """Админка для рекомендаций AI"""
    list_display = ('campaign', 'recommended_for', 'confidence_score',
                    'predicted_ctr', 'predicted_revenue', 'is_applied', 'created_at')
    list_filter = ('recommended_for', 'is_applied', 'created_at')
    search_fields = ('campaign__name', 'recommendation_reason')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Рекомендация', {
            'fields': ('recommended_for', 'campaign', 'place', 'post')
        }),
        ('Предсказания', {
            'fields': ('confidence_score', 'predicted_ctr', 'predicted_revenue', 'recommendation_reason')
        }),
        ('Результаты', {
            'fields': ('is_applied', 'actual_ctr', 'applied_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'applied_at')
    
    actions = ['apply_recommendations']
    
    def apply_recommendations(self, request, queryset):
        for recommendation in queryset:
            if not recommendation.is_applied:
                recommendation.apply_recommendation()
        self.message_user(request, f'Применено {queryset.count()} рекомендаций')
    apply_recommendations.short_description = 'Применить выбранные рекомендации'


@admin.register(AdActionLog)
class AdActionLogAdmin(admin.ModelAdmin):
    """Админка для журнала действий"""
    list_display = ('timestamp', 'action_type', 'target_display', 'performer_display',
                    'reverted_status', 'description_short')
    list_filter = ('action_type', 'performed_by_ai', 'reverted', 'timestamp', 'target_type')
    search_fields = ('description', 'target_name', 'performed_by__username')
    date_hierarchy = 'timestamp'
    readonly_fields = ('timestamp', 'performed_by', 'performed_by_ai', 'action_type',
                       'target_type', 'target_id', 'target_name', 'old_data', 'new_data',
                       'description', 'reverted', 'reverted_at', 'reverted_by')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('action_type', 'timestamp', 'description')
        }),
        ('Кто выполнил', {
            'fields': ('performed_by', 'performed_by_ai')
        }),
        ('Объект действия', {
            'fields': ('target_type', 'target_id', 'target_name')
        }),
        ('Данные', {
            'fields': ('old_data', 'new_data'),
            'classes': ('collapse',)
        }),
        ('Отмена', {
            'fields': ('can_revert', 'reverted', 'reverted_at', 'reverted_by'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        return False  # Нельзя создавать вручную
    
    def has_delete_permission(self, request, obj=None):
        return False  # Нельзя удалять (журнал должен храниться)
    
    def target_display(self, obj):
        return format_html(
            '<b>{}</b> #{}<br><small>{}</small>',
            obj.target_type,
            obj.target_id,
            obj.target_name or '-'
        )
    target_display.short_description = 'Объект'
    
    def performer_display(self, obj):
        if obj.performed_by_ai:
            return format_html('<span style="color: blue;">🤖 AI</span>')
        elif obj.performed_by:
            return format_html(
                '<span style="color: green;">👤 {}</span>',
                obj.performed_by.username
            )
        return format_html('<span style="color: gray;">⚙️ Система</span>')
    performer_display.short_description = 'Кто выполнил'
    
    def reverted_status(self, obj):
        if obj.reverted:
            return format_html(
                '<span style="color: red;">✗ Отменено</span><br><small>{}</small>',
                obj.reverted_at.strftime('%d.%m.%Y %H:%M') if obj.reverted_at else ''
            )
        elif obj.can_revert:
            return format_html('<span style="color: green;">✓ Активно</span>')
        return format_html('<span style="color: gray;">⊘ Нельзя отменить</span>')
    reverted_status.short_description = 'Статус'
    
    def description_short(self, obj):
        if len(obj.description) > 80:
            return obj.description[:77] + '...'
        return obj.description
    description_short.short_description = 'Описание'


@admin.register(ExternalScript)
class ExternalScriptAdmin(admin.ModelAdmin):
    """Админка для внешних скриптов"""
    list_display = ('name', 'script_type', 'provider', 'position', 
                    'is_active_display', 'priority', 'created_at')
    list_filter = ('script_type', 'position', 'is_active', 'provider')
    search_fields = ('name', 'provider', 'description')
    readonly_fields = ('created_at', 'updated_at', 'created_by')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'script_type', 'provider', 'description')
        }),
        ('Код скрипта', {
            'fields': ('code',),
            'description': 'Вставьте полный код скрипта (с тегами <script> если нужно)'
        }),
        ('Настройки размещения', {
            'fields': ('position', 'priority', 'is_active')
        }),
        ('Служебная информация', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # Если создаётся новый объект
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def is_active_display(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green; font-weight: bold;">✓ Активен</span>')
        return format_html('<span style="color: red;">✗ Выключен</span>')
    is_active_display.short_description = 'Статус'
    
    actions = ['activate_scripts', 'deactivate_scripts']
    
    def activate_scripts(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f'Активировано скриптов: {count}')
    activate_scripts.short_description = 'Активировать выбранные скрипты'
    
    def deactivate_scripts(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f'Деактивировано скриптов: {count}')
    deactivate_scripts.short_description = 'Деактивировать выбранные скрипты'


@admin.register(AdsTxtSettings)
class AdsTxtSettingsAdmin(admin.ModelAdmin):
    """Админка для настроек ads.txt"""
    list_display = ('domain', 'is_active', 'auto_update', 'last_successful_update', 
                    'update_count', 'status_display')
    readonly_fields = ('last_update_attempt', 'last_successful_update', 'last_error', 
                       'update_count', 'created_at', 'updated_at', 'content_preview')
    
    fieldsets = (
        ('Основные настройки', {
            'fields': ('domain', 'ezoic_manager_url', 'is_active', 'auto_update', 'update_interval_hours')
        }),
        ('Содержимое файла', {
            'fields': ('content', 'content_preview'),
            'classes': ('collapse',)
        }),
        ('Статус обновления', {
            'fields': ('last_successful_update', 'last_update_attempt', 'update_count', 'last_error'),
            'classes': ('collapse',)
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['update_ads_txt', 'activate_ads_txt', 'deactivate_ads_txt']
    
    def status_display(self, obj):
        if not obj.is_active:
            return format_html('<span style="color: red;">✗ Выключен</span>')
        if obj.last_error:
            return format_html('<span style="color: orange;">⚠ Ошибка</span>')
        if obj.needs_update():
            return format_html('<span style="color: blue;">🔄 Требует обновления</span>')
        return format_html('<span style="color: green;">✓ Активен</span>')
    status_display.short_description = 'Статус'
    
    def content_preview(self, obj):
        if obj.content:
            preview = obj.content[:500] + '...' if len(obj.content) > 500 else obj.content
            return format_html('<pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto;">{}</pre>', preview)
        return format_html('<p style="color: #999;">Содержимое отсутствует</p>')
    content_preview.short_description = 'Превью содержимого'
    
    def update_ads_txt(self, request, queryset):
        """Обновить ads.txt от Ezoic"""
        for settings in queryset:
            success, message = settings.update_from_ezoic()
            if success:
                self.message_user(request, f'✅ {settings.domain}: {message}')
            else:
                self.message_user(request, f'❌ {settings.domain}: {message}', level='ERROR')
    update_ads_txt.short_description = 'Обновить ads.txt от Ezoic'
    
    def activate_ads_txt(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f'Активировано: {count}')
    activate_ads_txt.short_description = 'Активировать ads.txt'
    
    def deactivate_ads_txt(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f'Деактивировано: {count}')
    deactivate_ads_txt.short_description = 'Деактивировать ads.txt'
