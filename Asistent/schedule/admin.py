"""
Админ-панель для моделей расписаний.
Перенесено из Asistent/admin.py для модульности.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import AISchedule, AIScheduleRun


@admin.register(AISchedule)
class AIScheduleAdmin(admin.ModelAdmin):
    """Админ-панель для расписаний AI"""
    
    list_display = [
        'name',
        'strategy_type',
        'schedule_kind',
        'category',
        'articles_per_run',
        'is_active',
        'last_run',
        'next_run',
    ]
    list_filter = ['is_active', 'posting_frequency', 'strategy_type', 'category', 'schedule_kind']
    search_fields = ['name', 'source_urls', 'tags']
    
    fieldsets = [
        ('Основная информация', {
            'fields': ['name', 'is_active', 'strategy_type']
        }),
        ('Настройки стратегии', {
            'fields': [
                'prompt_template',
                'task_type',
                'strategy_options',
                'payload_template',
                'schedule_kind',
                'scheduled_time',
                'cron_expression',
                'interval_minutes',
                'weekday',
                'static_params',
                'dynamic_params',
                'max_runs',
                'current_run_count',
            ]
        }),
        ('Источники', {
            'fields': ['source_urls']
        }),
        ('Настройки публикации', {
            'fields': [
                'category',
                'tags',
                'posting_frequency',
                'articles_per_run'
            ]
        }),
        ('Требования к контенту', {
            'fields': [
                'min_word_count',
                'max_word_count',
                'keywords',
                'tone'
            ]
        }),
        ('Расписание', {
            'fields': ['last_run', 'next_run']
        }),
        ('Даты', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    
    readonly_fields = ['last_run', 'current_run_count', 'created_at', 'updated_at']
    
    def save_model(self, request, obj, form, change):
        """Сохранение с автоматическим обновлением next_run"""
        super().save_model(request, obj, form, change)
        if obj.is_active and not obj.next_run:
            obj.update_next_run()


@admin.register(AIScheduleRun)
class AIScheduleRunAdmin(admin.ModelAdmin):
    """Админ-панель для журнала запусков"""
    
    list_display = [
        'id',
        'schedule_link',
        'strategy_type',
        'status',
        'created_count',
        'started_at',
        'duration_display',
    ]
    list_filter = ['status', 'strategy_type', 'started_at']
    search_fields = ['schedule__name']
    readonly_fields = [
        'schedule',
        'strategy_type',
        'started_at',
        'finished_at',
        'status',
        'created_count',
        'errors',
        'context_snapshot',
        'result_payload',
    ]
    
    fieldsets = [
        ('Информация о запуске', {
            'fields': ['schedule', 'strategy_type', 'status']
        }),
        ('Время', {
            'fields': ['started_at', 'finished_at']
        }),
        ('Результаты', {
            'fields': ['created_count', 'errors']
        }),
        ('Детали', {
            'fields': ['context_snapshot', 'result_payload'],
            'classes': ['collapse']
        }),
    ]
    
    def schedule_link(self, obj):
        """Ссылка на расписание"""
        url = reverse('admin:schedule_aischedule_change', args=[obj.schedule.id])
        return format_html('<a href="{}">{}</a>', url, obj.schedule.name)
    schedule_link.short_description = 'Расписание'
    
    def duration_display(self, obj):
        """Длительность выполнения"""
        if obj.duration:
            seconds = obj.duration.total_seconds()
            if seconds < 60:
                return f"{seconds:.1f}с"
            else:
                minutes = seconds / 60
                return f"{minutes:.1f}мин"
        return '-'
    duration_display.short_description = 'Длительность'
    
    def has_add_permission(self, request):
        """Запрет создания записей вручную"""
        return False

