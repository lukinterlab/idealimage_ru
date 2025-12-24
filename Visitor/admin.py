from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils import timezone
from .models import Profile, Feedback, Pisaka, RoleApplication, Subscription, Like, Donation, ActivityLog, CookieConsent

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """ Админ-панель модели профиля """
    list_display = ('vizitor', 'post_photo', 'spez', 'birth_date', 'slug', 'is_author', 'is_moderator', 'telegram_id', 'total_bonus')
    list_display_links = ('vizitor', 'slug')
    list_filter = ['spez', 'is_author', 'is_moderator', 'is_marketer', 'is_admin', 'agreed_to_terms']
    prepopulated_fields = {'slug': ('vizitor',)}
    search_fields = ('vizitor__username', 'vizitor__email', 'spez')
    readonly_fields = ('registration', 'agreed_at', 'last_bonus_calculated')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('vizitor', 'slug', 'avatar', 'bio', 'birth_date', 'spez')
        }),
        ('Роли и права', {
            'fields': ('is_author', 'is_moderator', 'is_marketer', 'is_admin')
        }),
        ('Telegram и согласия', {
            'fields': ('telegram_id', 'agreed_to_terms', 'agreed_at')
        }),
        ('Статистика и премии', {
            'fields': ('total_bonus', 'last_bonus_calculated', 'registration')
        }),
    )

    @admin.display(description="АВАТАР", ordering='vizitor')
    def post_photo(self, Visitor: Profile):
        if Visitor.avatar:
            return mark_safe(f"<img src='{Visitor.avatar.url}' width=30>")
        return "Без фото"


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    """
    Админ-панель модели обратной связи
    """
    list_display = ('email', 'subject', 'ip_address', 'user', 'time_create')
    list_display_links = ('email', 'subject')
    search_fields = ('email', 'subject', 'content')
    list_filter = ('time_create',)
    readonly_fields = ('time_create', 'ip_address')


@admin.register(Pisaka)
class PisakaAdmin(admin.ModelAdmin):
    """    Админ-панель модели категорий    """
    list_display = ('psevdonim', 'active', 'prais')
    list_display_links = ('psevdonim', 'prais')
    prepopulated_fields = {'slug': ('psevdonim',)}


@admin.register(RoleApplication)
class RoleApplicationAdmin(admin.ModelAdmin):
    """Админ-панель заявок на роли"""
    list_display = ('user', 'role', 'status', 'applied_at', 'processed_by', 'processed_at')
    list_display_links = ('user', 'role')
    list_filter = ('role', 'status', 'applied_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('applied_at', 'processed_at')
    actions = ['approve_applications', 'reject_applications']
    
    fieldsets = (
        ('Информация о заявке', {
            'fields': ('user', 'role', 'status', 'applied_at')
        }),
        ('Обработка заявки', {
            'fields': ('admin_response', 'processed_by', 'processed_at')
        }),
    )
    
    @admin.action(description='Одобрить выбранные заявки')
    def approve_applications(self, request, queryset):
        """Одобрение заявок на роли"""
        approved_count = 0
        
        for application in queryset.filter(status='pending'):
            application.status = 'approved'
            application.processed_at = timezone.now()
            application.processed_by = request.user
            application.save()
            
            # Присваиваем роль пользователю
            profile = application.user.profile
            if application.role == 'author':
                profile.is_author = True
            elif application.role == 'moderator':
                profile.is_moderator = True
            elif application.role == 'marketer':
                profile.is_marketer = True
            elif application.role == 'admin':
                profile.is_admin = True
                application.user.is_staff = True
                application.user.save()
            profile.save()
            
            # Создаем лог активности
            ActivityLog.objects.create(
                user=application.user,
                action_type='role_granted',
                target_user=request.user,
                target_object_id=application.id,
                description=f'Пользователю {application.user.username} присвоена роль {application.get_role_display()}'
            )
            
            approved_count += 1
        
        self.message_user(request, f'Одобрено заявок: {approved_count}')
    
    @admin.action(description='Отклонить выбранные заявки')
    def reject_applications(self, request, queryset):
        """Отклонение заявок на роли"""
        rejected_count = 0
        
        for application in queryset.filter(status='pending'):
            application.status = 'rejected'
            application.processed_at = timezone.now()
            application.processed_by = request.user
            application.save()
            rejected_count += 1
        
        self.message_user(request, f'Отклонено заявок: {rejected_count}')


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """Админ-панель подписок"""
    list_display = ('subscriber', 'author', 'created_at')
    list_display_links = ('subscriber', 'author')
    list_filter = ('created_at',)
    search_fields = ('subscriber__username', 'author__username')
    readonly_fields = ('created_at',)


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    """Админ-панель лайков"""
    list_display = ('user', 'post', 'created_at')
    list_display_links = ('user', 'post')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'post__title')
    readonly_fields = ('created_at',)


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    """Админ-панель донатов"""
    list_display = ('user', 'author', 'amount', 'created_at', 'is_anonymous')
    list_display_links = ('user', 'author')
    list_filter = ('created_at', 'is_anonymous')
    search_fields = ('user__username', 'author__username', 'message')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Информация о донате', {
            'fields': ('user', 'author', 'post', 'amount', 'is_anonymous')
        }),
        ('Сообщение', {
            'fields': ('message',)
        }),
        ('Время', {
            'fields': ('created_at',)
        }),
    )


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    """Админ-панель логов активности"""
    list_display = ('user', 'action_type', 'target_user', 'created_at', 'short_description')
    list_display_links = ('user', 'action_type')
    list_filter = ('action_type', 'created_at')
    search_fields = ('user__username', 'target_user__username', 'description')
    readonly_fields = ('created_at',)
    
    @admin.display(description='Описание')
    def short_description(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description


@admin.register(CookieConsent)
class CookieConsentAdmin(admin.ModelAdmin):
    """Админ-панель согласий на cookies (GDPR/Закон РФ)"""
    list_display = (
        'id',
        'user_display',
        'consent_categories',
        'ip_address',
        'consent_date_display'
    )
    list_filter = ('necessary', 'functional', 'analytics', 'advertising')
    search_fields = ('session_key', 'user__username', 'ip_address')
    readonly_fields = (
        'session_key',
        'user',
        'necessary',
        'functional',
        'analytics',
        'advertising',
        'ip_address',
        'user_agent',
        'consent_date'
    )
    # date_hierarchy = 'consent_date'  # ОТКЛЮЧЕНО: MySQL не настроен для часовых поясов
    ordering = ['-id']  # Используем id вместо consent_date для избежания проблем с TZ
    
    fieldsets = (
        ('👤 Пользователь', {
            'fields': ('session_key', 'user')
        }),
        ('✅ Категории согласия', {
            'fields': ('necessary', 'functional', 'analytics', 'advertising'),
            'description': '''
                <ul>
                    <li><strong>Обязательные</strong>: Всегда включены (необходимы для работы сайта)</li>
                    <li><strong>Функциональные</strong>: Улучшают функциональность</li>
                    <li><strong>Аналитика</strong>: Google Analytics, Яндекс.Метрика</li>
                    <li><strong>Реклама</strong>: Персонализированная реклама</li>
                </ul>
            '''
        }),
        ('🔍 Метаданные', {
            'fields': ('ip_address', 'user_agent', 'consent_date')
        }),
    )
    
    def has_add_permission(self, request):
        # Запрещаем ручное добавление
        return False
    
    def user_display(self, obj):
        if obj.user:
            return mark_safe(f'<a href="/admin/auth/user/{obj.user.id}/change/">{obj.user.username}</a>')
        return mark_safe(f'<span style="color: #9ca3af;">Гость ({obj.session_key[:8]}...)</span>')
    user_display.short_description = 'Пользователь'
    
    def consent_categories(self, obj):
        categories = []
        if obj.necessary:
            categories.append('<span style="color: #10b981;">✓ Обязательные</span>')
        if obj.functional:
            categories.append('<span style="color: #3b82f6;">✓ Функциональные</span>')
        if obj.analytics:
            categories.append('<span style="color: #8b5cf6;">✓ Аналитика</span>')
        if obj.advertising:
            categories.append('<span style="color: #f59e0b;">✓ Реклама</span>')
        
        return mark_safe('<br>'.join(categories) if categories else '<span style="color: #9ca3af;">Нет согласий</span>')
    consent_categories.short_description = 'Согласие'
    
    def consent_date_display(self, obj):
        """Отображение даты согласия без проблем с часовыми поясами"""
        if obj.consent_date:
            try:
                from django.utils import timezone
                # Конвертируем в локальное время если нужно
                local_time = timezone.localtime(obj.consent_date)
                return local_time.strftime('%d.%m.%Y %H:%M')
            except:
                # Если возникла ошибка, возвращаем ID записи
                return f'ID: {obj.id}'
        return '-'
    consent_date_display.short_description = 'Дата согласия'