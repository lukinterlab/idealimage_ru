from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.shortcuts import redirect
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
import json

from .models import (
    Donation, DonationNotification, PaymentWebhookLog, DonationSettings,
    AuthorRole, BonusFormula, AuthorStats, AuthorBonus,
    AuthorPenaltyReward, WeeklyReport, BonusPaymentRegistry, AIBonusCommand
)


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'get_donor_name_display', 'amount_display', 'article_display',
        'article_author_display', 'payment_method',
        'status_display', 'created_at', 'completed_at', 'actions_column'
    ]
    list_filter = ['status', 'payment_method', 'is_anonymous', 'created_at', 'article_author']
    search_fields = ['id', 'user_email', 'user_name', 'payment_id', 'message', 'article__title', 'article_author__username']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'completed_at',
        'payment_id', 'payment_url', 'qr_code_display', 'payment_data_display'
    ]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('id', 'user', 'user_email', 'user_name', 'is_anonymous')
        }),
        ('Связь со статьей (для бонусов)', {
            'fields': ('article', 'article_author')
        }),
        ('Платеж', {
            'fields': ('amount', 'currency', 'payment_method', 'status')
        }),
        ('Данные платежной системы', {
            'fields': ('payment_id', 'payment_url', 'payment_data_display'),
            'classes': ('collapse',)
        }),
        ('QR-код', {
            'fields': ('qr_code_display',),
            'classes': ('collapse',)
        }),
        ('Сообщение', {
            'fields': ('message',)
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at', 'completed_at')
        }),
    )
    
    def get_donor_name_display(self, obj):
        return obj.get_donor_name()
    get_donor_name_display.short_description = 'Донатер'
    
    def amount_display(self, obj):
        return f'{obj.amount} ₽'
    amount_display.short_description = 'Сумма'
    amount_display.admin_order_field = 'amount'
    
    def article_display(self, obj):
        if obj.article:
            return format_html(
                '<a href="/blog/{}/" target="_blank">{}</a>',
                obj.article.slug, obj.article.title[:50]
            )
        return '-'
    article_display.short_description = 'Статья'
    
    def article_author_display(self, obj):
        if obj.article_author:
            return format_html(
                '<a href="/admin/auth/user/{}/change/">{}</a>',
                obj.article_author.id,
                obj.article_author.get_full_name() or obj.article_author.username
            )
        return '-'
    article_author_display.short_description = 'Автор статьи'
    
    def status_display(self, obj):
        colors = {
            'pending': 'gray',
            'processing': 'blue',
            'succeeded': 'green',
            'canceled': 'red',
            'refunded': 'orange',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = 'Статус'
    
    def qr_code_display(self, obj):
        if obj.qr_code:
            return format_html('<img src="{}" style="max-width: 300px;" />', obj.qr_code)
        return 'QR-код не создан'
    qr_code_display.short_description = 'QR-код'
    
    def payment_data_display(self, obj):
        if obj.payment_data:
            formatted_json = json.dumps(obj.payment_data, indent=2, ensure_ascii=False)
            return format_html('<pre>{}</pre>', formatted_json)
        return 'Нет данных'
    payment_data_display.short_description = 'Данные от платежной системы'
    
    def actions_column(self, obj):
        if obj.status == 'succeeded':
            return format_html(
                '<a class="button" href="{}">Просмотр</a>',
                reverse('donations:donation_status', args=[obj.id])
            )
        return '-'
    actions_column.short_description = 'Действия'
    
    def changelist_view(self, request, extra_context=None):
        # Добавляем статистику на страницу списка
        extra_context = extra_context or {}
        
        # Статистика за все время
        total_stats = Donation.objects.filter(status='succeeded').aggregate(
            total_amount=Sum('amount'),
            total_count=Count('id')
        )
        
        # Статистика за последние 30 дней
        month_ago = timezone.now() - timedelta(days=30)
        month_stats = Donation.objects.filter(
            status='succeeded',
            completed_at__gte=month_ago
        ).aggregate(
            total_amount=Sum('amount'),
            total_count=Count('id')
        )
        
        # Статистика по методам оплаты
        payment_methods = Donation.objects.filter(status='succeeded').values(
            'payment_method'
        ).annotate(
            count=Count('id'),
            total=Sum('amount')
        )
        
        extra_context['total_amount'] = total_stats['total_amount'] or 0
        extra_context['total_count'] = total_stats['total_count'] or 0
        extra_context['month_amount'] = month_stats['total_amount'] or 0
        extra_context['month_count'] = month_stats['total_count'] or 0
        extra_context['payment_methods_stats'] = payment_methods
        
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(DonationNotification)
class DonationNotificationAdmin(admin.ModelAdmin):
    list_display = ['donation', 'notification_type', 'recipient', 'sent_at', 'is_successful']
    list_filter = ['notification_type', 'is_successful', 'sent_at']
    search_fields = ['donation__id', 'recipient']
    readonly_fields = ['donation', 'notification_type', 'recipient', 'sent_at', 'error_message']
    
    def has_add_permission(self, request):
        return False


@admin.register(PaymentWebhookLog)
class PaymentWebhookLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'payment_system', 'donation', 'processed', 'created_at']
    list_filter = ['payment_system', 'processed', 'created_at']
    search_fields = ['donation__id', 'error']
    readonly_fields = ['payment_system', 'webhook_data_display', 'donation', 'processed', 'error', 'created_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('payment_system', 'donation', 'processed', 'created_at')
        }),
        ('Данные webhook', {
            'fields': ('webhook_data_display',)
        }),
        ('Ошибки', {
            'fields': ('error',)
        }),
    )
    
    def webhook_data_display(self, obj):
        if obj.webhook_data:
            formatted_json = json.dumps(obj.webhook_data, indent=2, ensure_ascii=False)
            return format_html('<pre>{}</pre>', formatted_json)
        return 'Нет данных'
    webhook_data_display.short_description = 'Данные webhook'
    
    def has_add_permission(self, request):
        return False


@admin.register(DonationSettings)
class DonationSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Ограничения суммы', {
            'fields': ('min_amount', 'max_amount', 'preset_amounts')
        }),
        ('Включить платежные методы', {
            'fields': ('enable_yandex', 'enable_sberpay', 'enable_sbp', 'enable_qr')
        }),
        ('Настройки уведомлений', {
            'fields': ('send_email_to_donor', 'send_email_to_admin', 'admin_emails')
        }),
        ('Тексты писем', {
            'fields': ('thank_you_subject', 'thank_you_message')
        }),
        ('Настройки отображения', {
            'fields': ('donation_page_title', 'donation_page_description')
        }),
    )
    
    def has_add_permission(self, request):
        # Разрешаем создание только если еще нет настроек
        return not DonationSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Запрещаем удаление настроек
        return False


# ============================================
# Админ-панель для системы бонусов
# ============================================

class BonusFormulaInline(admin.StackedInline):
    """Inline для редактирования формулы прямо в роли"""
    model = BonusFormula
    extra = 0
    fields = [
        'articles_weight', 'likes_weight', 'comments_weight', 
        'views_weight', 'tasks_weight',
        'min_points_required', 'min_articles_required', 'is_active'
    ]


@admin.register(AuthorRole)
class AuthorRoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'level', 'bonus_percentage', 'point_value', 'color_display']
    list_editable = ['bonus_percentage', 'point_value']
    ordering = ['level']
    inlines = [BonusFormulaInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'level', 'description')
        }),
        ('Настройки бонусов', {
            'fields': ('bonus_percentage', 'point_value', 'color')
        }),
    )
    
    def color_display(self, obj):
        return format_html(
            '<div style="width: 50px; height: 20px; background-color: {}; border: 1px solid #ccc;"></div>',
            obj.color
        )
    color_display.short_description = 'Цвет'


@admin.register(BonusFormula)
class BonusFormulaAdmin(admin.ModelAdmin):
    list_display = [
        'role', 'articles_weight', 'likes_weight', 'comments_weight',
        'views_weight', 'tasks_weight', 'min_points_required', 'is_active'
    ]
    list_filter = ['is_active', 'role']
    list_editable = [
        'articles_weight', 'likes_weight', 'comments_weight',
        'views_weight', 'tasks_weight', 'min_points_required', 'is_active'
    ]
    
    fieldsets = (
        ('Роль', {
            'fields': ('role',)
        }),
        ('Веса для расчета баллов', {
            'fields': (
                'articles_weight', 'likes_weight', 'comments_weight',
                'views_weight', 'tasks_weight'
            )
        }),
        ('Требования для роли', {
            'fields': ('min_points_required', 'min_articles_required')
        }),
        ('Настройки', {
            'fields': ('is_active',)
        }),
    )


@admin.register(AuthorStats)
class AuthorStatsAdmin(admin.ModelAdmin):
    list_display = [
        'author', 'period_type', 'period_start', 'articles_count',
        'total_likes', 'total_comments', 'total_views',
        'completed_tasks_count', 'calculated_points', 'current_role'
    ]
    list_filter = ['period_type', 'current_role', 'period_start']
    search_fields = ['author__username', 'author__first_name', 'author__last_name']
    readonly_fields = [
        'author', 'period_type', 'period_start', 'period_end',
        'articles_count', 'total_likes', 'total_comments', 'total_views',
        'completed_tasks_count', 'tasks_reward_total',
        'calculated_points', 'current_role', 'calculated_at',
        'articles_detail_display', 'tasks_detail_display'
    ]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('author', 'period_type', 'period_start', 'period_end')
        }),
        ('Статистика по статьям', {
            'fields': (
                'articles_count', 'total_likes', 'total_comments', 'total_views',
                'articles_detail_display'
            )
        }),
        ('Статистика по заданиям', {
            'fields': ('completed_tasks_count', 'tasks_reward_total', 'tasks_detail_display')
        }),
        ('Расчетные данные', {
            'fields': ('calculated_points', 'current_role', 'calculated_at')
        }),
    )
    
    def articles_detail_display(self, obj):
        if not obj.articles_detail:
            return 'Нет данных'
        html = '<table style="width: 100%; border-collapse: collapse;">'
        html += '<tr style="background-color: #f0f0f0;"><th>Статья</th><th>Лайки</th><th>Комментарии</th><th>Просмотры</th></tr>'
        for article in obj.articles_detail[:10]:  # Показываем первые 10
            html += f'''
            <tr style="border-bottom: 1px solid #ddd;">
                <td><a href="/blog/{article['slug']}/" target="_blank">{article['title']}</a></td>
                <td>{article['likes']}</td>
                <td>{article['comments']}</td>
                <td>{article['views']}</td>
            </tr>
            '''
        html += '</table>'
        if len(obj.articles_detail) > 10:
            html += f'<p><i>...и еще {len(obj.articles_detail) - 10} статей</i></p>'
        return format_html(html)
    articles_detail_display.short_description = 'Детали по статьям'
    
    def tasks_detail_display(self, obj):
        if not obj.tasks_detail:
            return 'Нет данных'
        html = '<table style="width: 100%; border-collapse: collapse;">'
        html += '<tr style="background-color: #f0f0f0;"><th>Задание</th><th>Выполнено</th><th>Вознаграждение</th></tr>'
        for task in obj.tasks_detail[:10]:  # Показываем первые 10
            html += f'''
            <tr style="border-bottom: 1px solid #ddd;">
                <td>{task['task_title']}</td>
                <td>{task['completed_at'][:10] if task['completed_at'] else '-'}</td>
                <td>{task['reward']}₽</td>
            </tr>
            '''
        html += '</table>'
        if len(obj.tasks_detail) > 10:
            html += f'<p><i>...и еще {len(obj.tasks_detail) - 10} заданий</i></p>'
        return format_html(html)
    tasks_detail_display.short_description = 'Детали по заданиям'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return True
    
    actions = ['recalculate_stats']
    
    def recalculate_stats(self, request, queryset):
        from .bonus_calculator import calculate_author_stats
        count = 0
        for stats in queryset:
            calculate_author_stats(
                stats.author,
                stats.period_start,
                stats.period_end,
                stats.period_type
            )
            count += 1
        self.message_user(request, f'Пересчитана статистика для {count} записей')
    recalculate_stats.short_description = 'Пересчитать статистику'


@admin.register(AuthorBonus)
class AuthorBonusAdmin(admin.ModelAdmin):
    list_display = [
        'author', 'period_start', 'total_bonus', 'status_display',
        'role_at_calculation', 'created_at', 'paid_at'
    ]
    list_filter = ['status', 'role_at_calculation', 'period_start']
    search_fields = ['author__username', 'author__first_name', 'author__last_name']
    readonly_fields = [
        'author', 'period_start', 'period_end',
        'donations_amount', 'bonus_percentage', 'calculated_bonus',
        'tasks_reward', 'points_earned', 'point_value', 'bonus_from_points',
        'total_bonus', 'role_at_calculation', 'created_at'
    ]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('author', 'period_start', 'period_end', 'role_at_calculation')
        }),
        ('Бонус от донатов', {
            'fields': ('donations_amount', 'bonus_percentage', 'calculated_bonus')
        }),
        ('Вознаграждение за задания', {
            'fields': ('tasks_reward',)
        }),
        ('Бонус от баллов', {
            'fields': ('points_earned', 'point_value', 'bonus_from_points')
        }),
        ('Итого', {
            'fields': ('total_bonus', 'status', 'notes')
        }),
        ('Метаданные', {
            'fields': ('created_at', 'approved_at', 'paid_at')
        }),
    )
    
    def status_display(self, obj):
        colors = {
            'pending': 'orange',
            'approved': 'blue',
            'paid': 'green',
            'cancelled': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = 'Статус'
    
    actions = ['approve_bonuses', 'recalculate_bonuses']
    
    def approve_bonuses(self, request, queryset):
        count = queryset.filter(status='pending').update(
            status='approved',
            approved_at=timezone.now()
        )
        self.message_user(request, f'Утверждено {count} бонусов')
    approve_bonuses.short_description = 'Утвердить выбранные бонусы'
    
    def recalculate_bonuses(self, request, queryset):
        from .bonus_calculator import calculate_bonus
        count = 0
        for bonus in queryset:
            calculate_bonus(bonus.author, bonus.period_start, bonus.period_end)
            count += 1
        self.message_user(request, f'Пересчитано {count} бонусов')
    recalculate_bonuses.short_description = 'Пересчитать выбранные бонусы'


@admin.register(AuthorPenaltyReward)
class AuthorPenaltyRewardAdmin(admin.ModelAdmin):
    list_display = [
        'author', 'type_display', 'amount', 'amount_type',
        'applied_to', 'applied_from', 'is_active'
    ]
    list_filter = ['type', 'amount_type', 'applied_to', 'is_active']
    search_fields = ['author__username', 'reason']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('author', 'type', 'reason')
        }),
        ('Сумма', {
            'fields': ('amount', 'amount_type')
        }),
        ('Применение', {
            'fields': ('applied_to', 'applied_from', 'applied_until', 'is_active')
        }),
        ('Метаданные', {
            'fields': ('created_by', 'created_at')
        }),
    )
    
    readonly_fields = ['created_by', 'created_at']
    
    def type_display(self, obj):
        color = 'red' if obj.type == 'penalty' else 'green'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_type_display()
        )
    type_display.short_description = 'Тип'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(WeeklyReport)
class WeeklyReportAdmin(admin.ModelAdmin):
    list_display = [
        'week_period', 'authors_count', 'total_donations',
        'total_bonuses', 'is_finalized', 'is_paid', 'generated_at'
    ]
    list_filter = ['is_finalized', 'is_paid', 'week_start']
    readonly_fields = [
        'week_start', 'week_end', 'generated_at', 'report_data_display',
        'total_donations', 'total_bonuses', 'total_tasks_rewards', 'authors_count',
        'finalized_at', 'finalized_by'
    ]
    
    fieldsets = (
        ('Период', {
            'fields': ('week_start', 'week_end', 'generated_at')
        }),
        ('Статистика', {
            'fields': (
                'authors_count', 'total_donations',
                'total_bonuses', 'total_tasks_rewards'
            )
        }),
        ('Данные отчета', {
            'fields': ('report_data_display',),
            'classes': ('collapse',)
        }),
        ('Статус', {
            'fields': ('is_finalized', 'finalized_at', 'finalized_by', 'is_paid', 'notes')
        }),
    )
    
    def week_period(self, obj):
        return f'{obj.week_start.date()} - {obj.week_end.date()}'
    week_period.short_description = 'Период'
    
    def report_data_display(self, obj):
        if not obj.report_data:
            return 'Нет данных'
        formatted_json = json.dumps(obj.report_data, indent=2, ensure_ascii=False)
        return format_html('<pre style="max-height: 500px; overflow: auto;">{}</pre>', formatted_json)
    report_data_display.short_description = 'Данные отчета (JSON)'
    
    actions = ['finalize_reports', 'generate_new_report']
    
    def finalize_reports(self, request, queryset):
        from .weekly_processor import finalize_weekly_report
        count = 0
        for report in queryset.filter(is_finalized=False):
            finalize_weekly_report(report, request.user)
            count += 1
        self.message_user(request, f'Зафиксировано {count} отчетов')
    finalize_reports.short_description = 'Зафиксировать выбранные отчеты'
    
    def generate_new_report(self, request, queryset):
        from .weekly_processor import get_previous_week_boundaries, generate_weekly_report
        week_start, week_end = get_previous_week_boundaries()
        report = generate_weekly_report(week_start, week_end, force=True)
        self.message_user(request, f'Сгенерирован отчет за {week_start.date()} - {week_end.date()}')
        return redirect(f'/admin/donations/weeklyreport/{report.id}/change/')
    generate_new_report.short_description = 'Сгенерировать новый отчет за прошлую неделю'


@admin.register(BonusPaymentRegistry)
class BonusPaymentRegistryAdmin(admin.ModelAdmin):
    list_display = [
        'author', 'week_period', 'amount_to_pay', 'paid_amount',
        'status_display', 'payment_date', 'marked_by'
    ]
    list_filter = ['status', 'week_report__week_start', 'payment_date']
    search_fields = ['author__username', 'payment_note']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('week_report', 'author', 'bonus')
        }),
        ('Суммы', {
            'fields': ('amount_to_pay', 'paid_amount')
        }),
        ('Оплата', {
            'fields': ('status', 'payment_date', 'payment_method', 'payment_note', 'marked_by')
        }),
        ('Метаданные', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    readonly_fields = ['week_report', 'author', 'bonus', 'created_at', 'updated_at']
    
    def week_period(self, obj):
        return f'{obj.week_report.week_start.date()} - {obj.week_report.week_end.date()}'
    week_period.short_description = 'Период'
    
    def status_display(self, obj):
        colors = {
            'pending': 'orange',
            'paid': 'green',
            'partial': 'blue',
            'cancelled': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = 'Статус'
    
    actions = ['mark_as_paid']
    
    def mark_as_paid(self, request, queryset):
        count = 0
        for payment in queryset.filter(status='pending'):
            from .weekly_processor import mark_payment_as_paid
            mark_payment_as_paid(
                payment,
                payment.amount_to_pay,
                'Отмечено из админки',
                'Массовая отметка',
                request.user
            )
            count += 1
        self.message_user(request, f'Отмечено как оплачено: {count} записей')
    mark_as_paid.short_description = 'Отметить как оплачено'
    
    def save_model(self, request, obj, form, change):
        if obj.status == 'paid' and not obj.marked_by:
            obj.marked_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(AIBonusCommand)
class AIBonusCommandAdmin(admin.ModelAdmin):
    list_display = [
        'command_type', 'target_author', 'executed',
        'executed_at', 'created_at'
    ]
    list_filter = ['command_type', 'executed', 'created_at']
    search_fields = ['target_author__username', 'parameters']
    readonly_fields = [
        'conversation', 'message', 'command_type', 'target_author',
        'parameters_display', 'executed', 'executed_at', 'result_display', 'created_at'
    ]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('conversation', 'message', 'command_type', 'target_author')
        }),
        ('Параметры команды', {
            'fields': ('parameters_display',)
        }),
        ('Результат', {
            'fields': ('executed', 'executed_at', 'result_display')
        }),
    )
    
    def parameters_display(self, obj):
        formatted_json = json.dumps(obj.parameters, indent=2, ensure_ascii=False)
        return format_html('<pre>{}</pre>', formatted_json)
    parameters_display.short_description = 'Параметры'
    
    def result_display(self, obj):
        if not obj.result:
            return 'Команда не выполнена'
        formatted_json = json.dumps(obj.result, indent=2, ensure_ascii=False)
        return format_html('<pre>{}</pre>', formatted_json)
    result_display.short_description = 'Результат'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return True