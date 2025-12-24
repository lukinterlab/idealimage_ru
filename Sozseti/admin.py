"""
Админ-панель для управления публикациями в соцсетях
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    SocialPlatform,
    SocialChannel,
    TelegramChannelGroup,
    PostPublication,
    PublicationSchedule,
    SocialConversation,
    SocialComment,
    AdCampaign,
    ChannelAnalytics,
    CrossPostingRule,
)


@admin.register(SocialPlatform)
class SocialPlatformAdmin(admin.ModelAdmin):
    list_display = ['name_with_status', 'is_active', 'requires_vpn', 'last_sync', 'channels_count']
    list_filter = ['is_active', 'requires_vpn', 'name']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'is_active', 'requires_vpn', 'icon_class')
        }),
        ('API настройки', {
            'fields': ('api_credentials', 'rate_limits'),
            'classes': ('collapse',),
        }),
        ('Синхронизация', {
            'fields': ('last_sync',),
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def name_with_status(self, obj):
        status_icon = '✅' if obj.is_active else '❌'
        vpn_icon = ' 🔒' if obj.requires_vpn else ''
        return format_html(
            '<span style="font-size: 16px;">{} {}{}</span>',
            status_icon,
            obj.get_name_display(),
            vpn_icon
        )
    name_with_status.short_description = 'Платформа'
    
    def channels_count(self, obj):
        count = obj.channels.count()
        if count > 0:
            url = reverse('admin:Sozseti_socialchannel_changelist') + f'?platform__id__exact={obj.id}'
            return format_html('<a href="{}">{} каналов</a>', url, count)
        return '0 каналов'
    channels_count.short_description = 'Каналов'


@admin.register(SocialChannel)
class SocialChannelAdmin(admin.ModelAdmin):
    list_display = ['channel_name_with_status', 'platform', 'channel_type', 'subscribers_count', 'engagement_rate', 'publications_count']
    list_filter = ['platform', 'is_active', 'channel_type']
    search_fields = ['channel_name', 'channel_id']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('platform', 'channel_id', 'channel_name', 'channel_type', 'channel_url')
        }),
        ('Статистика', {
            'fields': ('subscribers_count', 'engagement_rate', 'is_active'),
        }),
        ('Настройки постинга', {
            'fields': ('posting_rules',),
            'classes': ('collapse',),
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def channel_name_with_status(self, obj):
        status_icon = '✅' if obj.is_active else '❌'
        return format_html(
            '{} <strong>{}</strong>',
            status_icon,
            obj.channel_name
        )
    channel_name_with_status.short_description = 'Канал'
    
    def publications_count(self, obj):
        count = obj.publications.count()
        if count > 0:
            url = reverse('admin:Sozseti_postpublication_changelist') + f'?channel__id__exact={obj.id}'
            return format_html('<a href="{}">{}</a>', url, count)
        return '0'
    publications_count.short_description = 'Публикаций'


@admin.register(TelegramChannelGroup)
class TelegramChannelGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'posting_strategy', 'channels_count', 'is_active']
    list_filter = ['is_active', 'posting_strategy']
    search_fields = ['name']
    filter_horizontal = ['channels']
    
    def channels_count(self, obj):
        return obj.channels.count()
    channels_count.short_description = 'Каналов'


@admin.register(PostPublication)
class PostPublicationAdmin(admin.ModelAdmin):
    list_display = ['post_title', 'channel', 'status', 'published_at', 'metrics_display']
    list_filter = ['status', 'channel__platform', 'channel']
    search_fields = ['post__title', 'platform_post_id']
    readonly_fields = ['created_at', 'updated_at', 'engagement_score']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Публикация', {
            'fields': ('post', 'channel', 'status')
        }),
        ('Планирование', {
            'fields': ('scheduled_at', 'published_at'),
        }),
        ('Платформа', {
            'fields': ('platform_post_id', 'platform_url'),
        }),
        ('Контент', {
            'fields': ('post_content',),
            'classes': ('collapse',),
        }),
        ('Метрики', {
            'fields': ('views_count', 'likes_count', 'comments_count', 'shares_count', 'engagement_score'),
        }),
        ('Ошибки', {
            'fields': ('error_log',),
            'classes': ('collapse',),
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    actions = ['republish_selected']
    
    def post_title(self, obj):
        return obj.post.title[:50]
    post_title.short_description = 'Статья'
    
    def metrics_display(self, obj):
        return format_html(
            '👁️ {} | ❤️ {} | 💬 {} | 🔄 {}',
            obj.views_count,
            obj.likes_count,
            obj.comments_count,
            obj.shares_count
        )
    metrics_display.short_description = 'Метрики'
    
    def republish_selected(self, request, queryset):
        # Будет реализовано позже
        self.message_user(request, 'Функция в разработке')
    republish_selected.short_description = 'Переопубликовать выбранные'


@admin.register(PublicationSchedule)
class PublicationScheduleAdmin(admin.ModelAdmin):
    list_display = ['name_with_status', 'posting_frequency', 'channels_count', 'categories_count', 'ai_optimization', 'next_run']
    list_filter = ['is_active', 'posting_frequency', 'ai_optimization']
    search_fields = ['name']
    filter_horizontal = ['channels', 'categories']
    readonly_fields = ['last_run', 'next_run', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'is_active')
        }),
        ('Настройки', {
            'fields': ('posting_frequency', 'optimal_times', 'ai_optimization'),
        }),
        ('Каналы и категории', {
            'fields': ('channels', 'categories'),
        }),
        ('Контент', {
            'fields': ('content_template', 'hashtags'),
        }),
        ('Расписание', {
            'fields': ('last_run', 'next_run'),
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def name_with_status(self, obj):
        status_icon = '✅' if obj.is_active else '❌'
        return format_html('{} {}', status_icon, obj.name)
    name_with_status.short_description = 'Расписание'
    
    def channels_count(self, obj):
        return obj.channels.count()
    channels_count.short_description = 'Каналов'
    
    def categories_count(self, obj):
        return obj.categories.count()
    categories_count.short_description = 'Категорий'


@admin.register(SocialConversation)
class SocialConversationAdmin(admin.ModelAdmin):
    list_display = ['user_name', 'channel', 'status', 'ai_responded', 'needs_admin', 'last_message_at']
    list_filter = ['status', 'ai_responded', 'needs_admin', 'channel__platform']
    search_fields = ['user_name', 'user_id']
    readonly_fields = ['created_at', 'last_message_at']
    
    def has_add_permission(self, request):
        return False  # Создаются автоматически


@admin.register(SocialComment)
class SocialCommentAdmin(admin.ModelAdmin):
    list_display = ['author_name', 'publication', 'sentiment', 'is_moderated', 'created_at']
    list_filter = ['sentiment', 'is_moderated', 'publication__channel__platform']
    search_fields = ['author_name', 'text']
    readonly_fields = ['created_at']
    
    def has_add_permission(self, request):
        return False  # Создаются автоматически


@admin.register(AdCampaign)
class AdCampaignAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'budget', 'spent', 'roi_display', 'start_date', 'end_date']
    list_filter = ['status', 'start_date']
    search_fields = ['name']
    filter_horizontal = ['platforms']
    readonly_fields = ['created_at', 'updated_at', 'created_by']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'platforms', 'status')
        }),
        ('Бюджет', {
            'fields': ('budget', 'spent'),
        }),
        ('Даты', {
            'fields': ('start_date', 'end_date'),
        }),
        ('Таргетинг', {
            'fields': ('target_audience',),
        }),
        ('Контент', {
            'fields': ('ad_content',),
        }),
        ('Метрики', {
            'fields': ('metrics',),
        }),
        ('Служебное', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def roi_display(self, obj):
        roi = obj.get_roi()
        color = 'green' if roi > 0 else 'red'
        return format_html('<span style="color: {};">{} %</span>', color, roi)
    roi_display.short_description = 'ROI'


@admin.register(ChannelAnalytics)
class ChannelAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['channel', 'date', 'subscribers_gained', 'posts_published', 'total_views', 'total_engagement']
    list_filter = ['date', 'channel__platform', 'channel']
    search_fields = ['channel__channel_name']
    readonly_fields = ['created_at']
    date_hierarchy = 'date'
    
    def has_add_permission(self, request):
        return False  # Создаются автоматически


@admin.register(CrossPostingRule)
class CrossPostingRuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'source_channel', 'target_count', 'transform_content', 'is_active']
    list_filter = ['is_active', 'transform_content']
    search_fields = ['name']
    filter_horizontal = ['target_channels']
    
    def target_count(self, obj):
        return obj.target_channels.count()
    target_count.short_description = 'Целевых каналов'
