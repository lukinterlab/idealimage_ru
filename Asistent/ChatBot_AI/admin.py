"""
Django admin для чат-бота
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import ChatbotSettings, ChatbotFAQ, ChatMessage


@admin.register(ChatbotSettings)
class ChatbotSettingsAdmin(admin.ModelAdmin):
    """Админ-панель для настроек чат-бота"""
    
    list_display = ['id', 'status_badge', 'use_ai', 'search_articles', 'updated_at']
    readonly_fields = ['updated_at']
    
    fieldsets = [
        ('🤖 Основные настройки', {
            'fields': ['is_active', 'welcome_message', 'system_prompt'],
            'description': 'Основные параметры работы чат-бота'
        }),
        ('⚙️ Режимы работы', {
            'fields': ['use_ai', 'search_articles', 'max_search_results'],
            'description': '''
                <ul>
                    <li><strong>GigaChat AI</strong>: Ответы генерируются нейросетью (потребляет токены)</li>
                    <li><strong>Поиск по статьям</strong>: Поиск релевантных статей блога</li>
                    <li>Если AI выключен, будут использоваться FAQ + поиск статей</li>
                </ul>
            '''
        }),
        ('📧 Контакт с администратором', {
            'fields': ['admin_contact_enabled', 'admin_email'],
            'description': 'Настройки формы обращения к администратору'
        }),
        ('🛡️ Ограничения и защита', {
            'fields': ['rate_limit_messages'],
            'description': 'Лимит сообщений в час на одну сессию (защита от спама)'
        }),
        ('📅 Метаданные', {
            'fields': ['updated_at'],
            'classes': ['collapse']
        })
    ]
    
    def status_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color: #10b981; font-weight: bold;">✅ Активен</span>'
            )
        return format_html(
            '<span style="color: #ef4444; font-weight: bold;">❌ Выключен</span>'
        )
    status_badge.short_description = 'Статус'
    
    def has_add_permission(self, request):
        # Разрешаем добавление только если записи нет
        return not ChatbotSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Запрещаем удаление (Singleton)
        return False


@admin.register(ChatbotFAQ)
class ChatbotFAQAdmin(admin.ModelAdmin):
    """Админ-панель для FAQ чат-бота"""
    
    list_display = [
        'id',
        'question_short',
        'priority_badge',
        'usage_count',
        'is_active',
        'created_at'
    ]
    list_filter = ['is_active', 'priority', 'created_at']
    search_fields = ['question', 'answer', 'keywords']
    readonly_fields = ['usage_count', 'created_at', 'updated_at']
    ordering = ['-priority', '-usage_count']
    
    fieldsets = [
        ('❓ Вопрос', {
            'fields': ['question', 'keywords'],
            'description': '''
                <p><strong>Ключевые слова</strong> помогают найти нужный FAQ.</p>
                <p>Формат: ["слово1", "слово2", "слово3"]</p>
                <p>Пример: ["автор", "заявка", "стать автором"]</p>
            '''
        }),
        ('💬 Ответ', {
            'fields': ['answer', 'related_url'],
            'description': '''
                <p>Ответ может содержать HTML теги для форматирования.</p>
                <p>Ссылка (related_url) добавляется автоматически в конец ответа.</p>
            '''
        }),
        ('⚙️ Настройки', {
            'fields': ['priority', 'is_active']
        }),
        ('📊 Статистика', {
            'fields': ['usage_count', 'created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    
    def question_short(self, obj):
        if len(obj.question) > 60:
            return obj.question[:60] + '...'
        return obj.question
    question_short.short_description = 'Вопрос'
    
    def priority_badge(self, obj):
        if obj.priority >= 90:
            color = '#dc3545'
            icon = '🔴'
            text = 'Критичный'
        elif obj.priority >= 70:
            color = '#ffc107'
            icon = '🟡'
            text = 'Важный'
        elif obj.priority >= 50:
            color = '#17a2b8'
            icon = '🔵'
            text = 'Средний'
        else:
            color = '#6c757d'
            icon = '⚪'
            text = 'Низкий'
        
        return format_html(
            '{} <span style="color: {}; font-weight: bold;">{} ({})</span>',
            icon, color, obj.priority, text
        )
    priority_badge.short_description = 'Приоритет'


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    """Админ-панель для истории сообщений чат-бота"""
    
    list_display = [
        'id',
        'user_display',
        'message_short',
        'source_badge',
        'processing_time',
        'created_at'
    ]
    list_filter = ['source', 'created_at']
    search_fields = ['message', 'response', 'session_key', 'user__username']
    readonly_fields = [
        'session_key',
        'user',
        'message',
        'response',
        'source',
        'found_articles',
        'processing_time',
        'ip_address',
        'user_agent',
        'created_at'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = [
        ('👤 Пользователь', {
            'fields': ['session_key', 'user', 'ip_address', 'user_agent']
        }),
        ('💬 Сообщение', {
            'fields': ['message', 'response']
        }),
        ('🔍 Метаданные', {
            'fields': ['source', 'found_articles', 'processing_time']
        }),
        ('📅 Время', {
            'fields': ['created_at']
        })
    ]
    
    def has_add_permission(self, request):
        # Запрещаем ручное добавление (создаются автоматически)
        return False
    
    def user_display(self, obj):
        if obj.user:
            return format_html(
                '<a href="/admin/auth/user/{}/change/">{}</a>',
                obj.user.id,
                obj.user.username
            )
        return format_html(
            '<span style="color: #9ca3af;">Гость ({}...)</span>',
            obj.session_key[:8]
        )
    user_display.short_description = 'Пользователь'
    
    def message_short(self, obj):
        if len(obj.message) > 50:
            return obj.message[:50] + '...'
        return obj.message
    message_short.short_description = 'Сообщение'
    
    def source_badge(self, obj):
        source_config = {
            'faq': ('🤖 FAQ', '#10b981'),
            'article_search': ('📄 Статьи', '#3b82f6'),
            'ai': ('🧠 AI', '#8b5cf6'),
            'error': ('❌ Ошибка', '#ef4444')
        }
        
        text, color = source_config.get(obj.source, ('❓ Неизвестно', '#6c757d'))
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, text
        )
    source_badge.short_description = 'Источник'

