"""
Административная панель для AI-Ассистента
"""
import json

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

# ПРИМЕЧАНИЕ: AISchedule и AIScheduleRun теперь регистрируются в schedule/admin.py
from .models import *

# ========================================================================
# Админки модерации перенесены в Asistent.moderations.admin
# ========================================================================

# ========================================================================
# Админ-панель для заданий
# ========================================================================
@admin.register(ContentTask)
class ContentTaskAdmin(admin.ModelAdmin):
    """Админ-панель для заданий"""
    
    list_display = [
        'title', 
        'status_badge', 
        'assigned_authors_count', 
        'deadline', 
        'reward',
        'created_by',
        'actions_column'
    ]
    list_filter = ['status', 'deadline', 'created_at', 'category']
    search_fields = ['title', 'description']
    
    fieldsets = [
        ('Основная информация', {
            'fields': ['title', 'description', 'category', 'tags']
        }),
        ('Требования', {
            'fields': [
                'required_word_count',
                'required_links',
                'required_keywords',
                'deadline',
                'reward'
            ]
        }),
        ('Статус', {
            'fields': ['status', 'max_completions']
        }),
        ('Служебная информация', {
            'fields': ['created_by', 'created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    
    readonly_fields = ['created_at', 'updated_at']
    
    def status_badge(self, obj):
        colors = {
            'available': '#28a745',
            'taken': '#ffc107',
            'submitted': '#17a2b8',
            'approved': '#007bff',
            'rejected': '#dc3545',
            'completed': '#6c757d',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Статус'
    
    def assigned_authors_count(self, obj):
        """Количество назначенных авторов"""
        count = obj.assignments.count()
        if count == 0:
            return format_html('<span style="color: #999;">—</span>')
        elif count < obj.max_completions:
            return format_html(
                '<span style="background-color: #007bff; color: white; padding: 3px 10px; border-radius: 3px;">{} авт.</span>',
                count
            )
        else:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px;">{} авт. ✅</span>',
                count
            )
    assigned_authors_count.short_description = 'Назначено'
    
    def actions_column(self, obj):
        buttons = []
        
        if obj.status == 'submitted':
            approve_url = f'/admin/approve-task/{obj.id}/'
            reject_url = f'/admin/reject-task/{obj.id}/'
            buttons.append(f'<a href="{approve_url}" style="color: green;">✓ Одобрить</a>')
            buttons.append(f'<a href="{reject_url}" style="color: red;">✗ Отклонить</a>')
        
        return format_html(' | '.join(buttons)) if buttons else '-'
    actions_column.short_description = 'Действия'
    
    def save_model(self, request, obj, form, change):
        if not change:  # Если создание нового объекта
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

# ========================================================================
# Админ-панель для расписаний AI
# ПРИМЕЧАНИЕ: Админка для AISchedule и AIScheduleRun перенесена в schedule/admin.py
# См. Asistent/schedule/admin.py
# ========================================================================

# ========================================================================
# Админ-панель для транзакций
# ========================================================================
@admin.register(AuthorBalance)
class AuthorBalanceAdmin(admin.ModelAdmin):
    """Админ-панель для транзакций"""
    
    list_display = [
        'author',
        'amount_display',
        'transaction_type',
        'task',
        'created_at'
    ]
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['author__username', 'description']
    readonly_fields = ['created_at']
    
    def amount_display(self, obj):
        color = 'green' if obj.amount > 0 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} руб.</span>',
            color,
            obj.amount
        )
    amount_display.short_description = 'Сумма'

# ========================================================================
# Админ-панель для истории заданий
# ========================================================================
@admin.register(TaskHistory)
class TaskHistoryAdmin(admin.ModelAdmin):
    """Админ-панель для истории заданий"""
    
    list_display = ['task', 'author', 'completed_at', 'reward']
    list_filter = ['completed_at']
    search_fields = ['task__title', 'author__username']
    readonly_fields = ['task', 'author', 'completed_at', 'reward']

# ========================================================================
# Админка ModerationLog перенесена в Asistent.moderations.admin
# ========================================================================

# ========================================================================
# Админ-панель для AI-статей
# ========================================================================
@admin.register(AIGeneratedArticle)
class AIGeneratedArticleAdmin(admin.ModelAdmin):
    """Админ-панель для AI-статей"""
    
    list_display = ['id', 'article_title', 'article_id_link', 'schedule', 'created_at']
    list_filter = ['created_at', 'schedule']
    search_fields = ['article__title', 'id']
    readonly_fields = ['id', 'schedule', 'article', 'source_urls', 'prompt', 'ai_response', 'created_at']
    
    def article_title(self, obj):
        """Заголовок статьи"""
        return obj.article.title[:60] + '...' if len(obj.article.title) > 60 else obj.article.title
    article_title.short_description = 'Заголовок статьи'
    
    def article_id_link(self, obj):
        """ID статьи со ссылкой"""
        from django.urls import reverse
        url = reverse('admin:blog_post_change', args=[obj.article.id])
        return format_html(
            '<a href="{}" target="_blank">ID: {} →</a>',
            url,
            obj.article.id
        )
    article_id_link.short_description = 'Статья (ID)'

# ========================================================================
# Админ-панель для уведомлений авторов
# ========================================================================
@admin.register(AuthorNotification)
class AuthorNotificationAdmin(admin.ModelAdmin):
    """Админ-панель для уведомлений"""
    
    list_display = [
        'recipient',
        'title',
        'notification_type',
        'is_read_badge',
        'created_at'
    ]
    list_filter = ['is_read', 'notification_type', 'created_at']
    search_fields = ['recipient__username', 'title', 'message']
    readonly_fields = ['created_at', 'read_at']
    
    def is_read_badge(self, obj):
        if obj.is_read:
            return format_html('<span style="color: green;">✓ Прочитано</span>')
        else:
            return format_html('<span style="color: red;">✗ Не прочитано</span>')
    is_read_badge.short_description = 'Статус'


# ============================================================================
# AI-ЧАТ И ЗАДАЧИ
# ============================================================================
@admin.register(AIConversation)
class AIConversationAdmin(admin.ModelAdmin):
    """Админ-панель для диалогов AI-чата"""
    
    list_display = ['id', 'title', 'admin', 'is_active', 'created_at', 'updated_at', 'messages_count']
    list_filter = ['is_active', 'created_at', 'admin']
    search_fields = ['title', 'admin__username']
    readonly_fields = ['created_at', 'updated_at']
    
    def messages_count(self, obj):
        return obj.messages.count()
    messages_count.short_description = 'Сообщений'

# ========================================================================
# Админ-панель для сообщений AI-чата
# ========================================================================
@admin.register(AIMessage)
class AIMessageAdmin(admin.ModelAdmin):
    """Админ-панель для сообщений AI-чата"""
    
    list_display = ['id', 'conversation', 'role', 'short_content', 'timestamp']
    list_filter = ['role', 'timestamp']
    search_fields = ['content', 'conversation__title']
    readonly_fields = ['timestamp']
    
    def short_content(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    short_content.short_description = 'Содержание'

# ========================================================================
# Админ-панель для задач AI-агента
# ========================================================================
@admin.register(AITask)
class AITaskAdmin(admin.ModelAdmin):
    """Админ-панель для задач AI-агента"""
    
    list_display = [
        'id',
        'task_type',
        'status_badge',
        'short_command',
        'created_at',
        'started_at',
        'completed_at',
        'view_result'
    ]
    list_filter = ['status', 'task_type', 'created_at']
    search_fields = ['command', 'task_type']
    readonly_fields = ['created_at', 'started_at', 'completed_at', 'result_display']
    
    fieldsets = [
        ('Основная информация', {
            'fields': ['conversation', 'command', 'task_type', 'status']
        }),
        ('Параметры', {
            'fields': ['parameters'],
            'classes': ['collapse']
        }),
        ('Выполнение', {
            'fields': ['progress_description', 'result_display', 'error_message']
        }),
        ('Даты', {
            'fields': ['created_at', 'started_at', 'completed_at'],
            'classes': ['collapse']
        })
    ]
    
    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'in_progress': '#17a2b8',
            'completed': '#28a745',
            'failed': '#dc3545',
            'cancelled': '#6c757d'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">● {}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Статус'
    
    def short_command(self, obj):
        return obj.command[:50] + '...' if len(obj.command) > 50 else obj.command
    short_command.short_description = 'Команда'
    
    def view_result(self, obj):
        if obj.result:
            return format_html('<a href="#" onclick="alert(\'{}\'); return false;">Показать</a>', str(obj.result)[:200])
        return '-'
    view_result.short_description = 'Результат'
    
    def result_display(self, obj):
        if obj.result:
            import json
            return format_html('<pre>{}</pre>', json.dumps(obj.result, indent=2, ensure_ascii=False))
        return 'Нет результата'
    result_display.short_description = 'Результат (полный)'

# ========================================================================
# Админ-панель для базы знаний AI
# ========================================================================
@admin.register(AIKnowledgeBase)
class AIKnowledgeBaseAdmin(admin.ModelAdmin):
    """Админ-панель для базы знаний AI"""
    
    list_display = [
        'id',
        'category',
        'title',
        'priority_badge',
        'usage_count',
        'is_active',
        'created_by',
        'created_at'
    ]
    list_filter = ['category', 'is_active', 'priority', 'created_at']
    search_fields = ['title', 'content', 'tags']
    readonly_fields = ['created_at', 'updated_at', 'usage_count']
    
    fieldsets = [
        ('Основная информация', {
            'fields': ['category', 'title', 'content']
        }),
        ('Метаданные', {
            'fields': ['tags', 'priority', 'is_active']
        }),
        ('Статистика', {
            'fields': ['usage_count', 'created_by', 'created_at', 'updated_at'],
            'classes': ['collapse']
        }),
        ('Векторное представление', {
            'fields': ['embedding'],
            'classes': ['collapse']
        })
    ]
    
    def priority_badge(self, obj):
        if obj.priority >= 90:
            color = '#dc3545'  # Красный - критически важное
            icon = '🔴'
        elif obj.priority >= 70:
            color = '#ffc107'  # Желтый - важное
            icon = '🟡'
        else:
            color = '#28a745'  # Зеленый - обычное
            icon = '🟢'
        
        return format_html(
            '{} <span style="color: {}; font-weight: bold;">{}</span>',
            icon, color, obj.priority
        )
    priority_badge.short_description = 'Приоритет'


# =====================================================
# ЧАТ-БОТ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ
# ПЕРЕНЕСЕНО В ChatBot_AI.admin
# =====================================================
# Админки чат-бота перенесены в модуль ChatBot_AI:
# - ChatbotSettingsAdmin -> ChatBot_AI.admin.ChatbotSettingsAdmin
# - ChatbotFAQAdmin -> ChatBot_AI.admin.ChatbotFAQAdmin
# - ChatMessageAdmin -> ChatBot_AI.admin.ChatMessageAdmin

# ПРИМЕЧАНИЕ: Админка для AIScheduleRun перенесена в schedule/admin.py
# См. Asistent/schedule/admin.py

# ========================================================================
# Админ-панель для системных логов
# ========================================================================
@admin.register(SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    """Админ-панель для системных логов"""
    
    list_display = ['timestamp', 'level', 'logger_name', 'module', 'message_short', 'process_id']
    list_filter = ['level', 'logger_name', 'timestamp', 'module']
    search_fields = ['message', 'module', 'function', 'logger_name']
    readonly_fields = ['timestamp', 'level', 'logger_name', 'message', 'module', 'function', 
                      'line', 'process_id', 'thread_id', 'extra_data']
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('timestamp', 'level', 'logger_name', 'message')
        }),
        ('Детали', {
            'fields': ('module', 'function', 'line', 'process_id', 'thread_id'),
            'classes': ('collapse',)
        }),
        ('Дополнительные данные', {
            'fields': ('extra_data',),
            'classes': ('collapse',)
        }),
    )
    
    def message_short(self, obj):
        """Короткая версия сообщения для списка"""
        if len(obj.message) > 100:
            return obj.message[:100] + '...'
        return obj.message
    message_short.short_description = 'Сообщение'
    
    def has_add_permission(self, request):
        """Запрещаем создание логов вручную"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Запрещаем редактирование логов"""
        return False
