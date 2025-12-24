"""
Простая админка Django для системы модерации.

Регистрируются три модели:
- ArticleModerationSettings
- CommentModerationSettings
- ModerationLog (только для чтения)
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.http import HttpResponseRedirect
from django.contrib import messages
from .models import ArticleModerationSettings, CommentModerationSettings, ModerationLog, ArticleRegeneration


@admin.register(ArticleModerationSettings)
class ArticleModerationSettingsAdmin(admin.ModelAdmin):
    """Админка настроек модерации статей."""
    
    list_display = ['name_with_status', 'min_words', 'checks_summary', 'updated_at']
    list_filter = ['is_active', 'check_title', 'check_image', 'check_category']
    search_fields = ['name']
    
    fieldsets = (
        ('🔧 Основное', {
            'fields': ('name', 'is_active'),
            'description': 'Название профиля и его активность'
        }),
        ('✅ Какие проверки выполнять', {
            'fields': (
                'check_title',
                'check_image',
                'check_category',
                'check_length',
                'check_profanity',
            ),
            'description': 'Включите нужные проверки'
        }),
        ('⚙️ Настройки проверок', {
            'fields': ('min_words', 'min_title_length'),
            'description': 'Пороговые значения'
        }),
        ('📅 Информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def name_with_status(self, obj):
        """Название со статусом."""
        icon = "✅" if obj.is_active else "⏸️"
        return f"{icon} {obj.name}"
    name_with_status.short_description = "Профиль"
    
    def checks_summary(self, obj):
        """Краткое описание активных проверок."""
        checks = []
        if obj.check_title:
            checks.append("Заголовок")
        if obj.check_image:
            checks.append("Изображение")
        if obj.check_category:
            checks.append("Категория")
        if obj.check_length:
            checks.append(f"Длина ({obj.min_words} слов)")
        if obj.check_profanity:
            checks.append("Мат")
        
        if not checks:
            return "—"
        
        return ", ".join(checks)
    checks_summary.short_description = "Активные проверки"
    
    def save_model(self, request, obj, form, change):
        """При активации нового профиля - деактивировать остальные."""
        if obj.is_active:
            # Деактивируем все другие профили
            ArticleModerationSettings.objects.exclude(pk=obj.pk).update(is_active=False)
        super().save_model(request, obj, form, change)


@admin.register(CommentModerationSettings)
class CommentModerationSettingsAdmin(admin.ModelAdmin):
    """Админка настроек модерации комментариев."""
    
    list_display = ['name_with_status', 'min_length', 'checks_summary', 'updated_at']
    list_filter = ['is_active', 'block_urls', 'block_html', 'check_spam']
    search_fields = ['name', 'forbidden_words']
    
    fieldsets = (
        ('🔧 Основное', {
            'fields': ('name', 'is_active'),
            'description': 'Название профиля и его активность'
        }),
        ('✅ Какие проверки выполнять', {
            'fields': (
                'block_urls',
                'block_html',
                'block_short',
                'check_spam',
            ),
            'description': 'Включите нужные проверки'
        }),
        ('⚙️ Настройки проверок', {
            'fields': ('min_length', 'forbidden_words'),
            'description': 'Пороговые значения и стоп-слова'
        }),
        ('📅 Информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def name_with_status(self, obj):
        """Название со статусом."""
        icon = "✅" if obj.is_active else "⏸️"
        return f"{icon} {obj.name}"
    name_with_status.short_description = "Профиль"
    
    def checks_summary(self, obj):
        """Краткое описание активных проверок."""
        checks = []
        if obj.block_urls:
            checks.append("🔗 Ссылки")
        if obj.block_html:
            checks.append("📝 HTML")
        if obj.block_short:
            checks.append(f"📏 Длина ({obj.min_length})")
        if obj.check_spam:
            checks.append("🚫 Спам")
        
        if not checks:
            return "—"
        
        return " ".join(checks)
    checks_summary.short_description = "Активные проверки"
    
    def save_model(self, request, obj, form, change):
        """При активации нового профиля - деактивировать остальные."""
        if obj.is_active:
            # Деактивируем все другие профили
            CommentModerationSettings.objects.exclude(pk=obj.pk).update(is_active=False)
        super().save_model(request, obj, form, change)


@admin.register(ModerationLog)
class ModerationLogAdmin(admin.ModelAdmin):
    """Админка журнала модерации (только для чтения)."""
    
    list_display = [
        'status_icon',
        'content_type',
        'object_id',
        'problems_preview',
        'moderator',
        'created_at'
    ]
    list_filter = ['content_type', 'passed', 'created_at']
    search_fields = ['object_id', 'problems']
    date_hierarchy = 'created_at'
    
    readonly_fields = [
        'content_type',
        'object_id',
        'passed',
        'problems_formatted',
        'moderator',
        'created_at'
    ]
    
    fields = [
        'content_type',
        'object_id',
        'passed',
        'problems_formatted',
        'moderator',
        'created_at'
    ]
    
    def has_add_permission(self, request):
        """Запретить добавление записей вручную."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Запретить изменение записей."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Разрешить удаление старых логов."""
        return request.user.is_superuser
    
    def status_icon(self, obj):
        """Иконка статуса."""
        if obj.passed:
            return format_html('<span style="font-size: 20px;">✅</span>')
        else:
            return format_html('<span style="font-size: 20px;">❌</span>')
    status_icon.short_description = ""
    
    def problems_preview(self, obj):
        """Краткий превью проблем."""
        if not obj.problems:
            return format_html('<span style="color: green;">Проблем нет</span>')
        
        problems = obj.get_problems_list()
        count = len(problems)
        
        if count == 0:
            return format_html('<span style="color: green;">Проблем нет</span>')
        elif count == 1:
            return format_html('<span style="color: red;">{}</span>', problems[0][:50])
        else:
            return format_html(
                '<span style="color: red;">{} проблем</span>',
                count
            )
    problems_preview.short_description = "Проблемы"
    
    def problems_formatted(self, obj):
        """Форматированный список проблем."""
        if not obj.problems:
            return format_html('<p style="color: green;">✅ Проблем не обнаружено</p>')
        
        problems = obj.get_problems_list()
        html = '<ul style="margin: 0; padding-left: 20px;">'
        for problem in problems:
            html += f'<li>{problem}</li>'
        html += '</ul>'
        
        return format_html(html)
    problems_formatted.short_description = "Список проблем"


@admin.register(ArticleRegeneration)
class ArticleRegenerationAdmin(admin.ModelAdmin):
    """Админка регенерации статей."""
    
    list_display = [
        'status_icon',
        'original_article_link',
        'regenerated_article_link',
        'category',
        'regenerated_at'
    ]
    list_filter = ['status', 'regenerated_at']
    search_fields = ['original_article__title', 'regenerated_article__title']
    date_hierarchy = 'regenerated_at'
    readonly_fields = ['regenerated_at', 'regeneration_notes']
    
    change_list_template = 'admin/moderations/articleregeneration/change_list.html'
    
    fieldsets = (
        ('📄 Статьи', {
            'fields': ('original_article', 'regenerated_article'),
        }),
        ('📊 Статус', {
            'fields': ('status', 'regenerated_at'),
        }),
        ('📝 Заметки', {
            'fields': ('regeneration_notes',),
            'classes': ('collapse',),
        }),
    )
    
    def status_icon(self, obj):
        """Иконка статуса."""
        icons = {
            'pending': '⏳',
            'completed': '✅',
            'failed': '❌'
        }
        return format_html('<span style="font-size: 20px;">{}</span>', icons.get(obj.status, '❓'))
    status_icon.short_description = ""
    
    def original_article_link(self, obj):
        """Ссылка на оригинальную статью."""
        if obj.original_article:
            url = reverse('admin:blog_post_change', args=[obj.original_article.id])
            return format_html('<a href="{}">{}</a>', url, obj.original_article.title[:50])
        return "—"
    original_article_link.short_description = "Оригинальная статья"
    
    def regenerated_article_link(self, obj):
        """Ссылка на регенерированную статью."""
        if obj.regenerated_article:
            url = reverse('admin:blog_post_change', args=[obj.regenerated_article.id])
            return format_html('<a href="{}">{}</a>', url, obj.regenerated_article.title[:50])
        return "—"
    regenerated_article_link.short_description = "Регенерированная статья"
    
    def category(self, obj):
        """Категория статьи."""
        if obj.original_article and obj.original_article.category:
            return obj.original_article.category.title
        return "—"
    category.short_description = "Категория"
    
    def get_urls(self):
        """Добавляем кастомный URL для ручного запуска регенерации."""
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                'run-regeneration/',
                self.admin_site.admin_view(self.run_regeneration),
                name='Moderation_articleregeneration_run_regeneration',
            ),
        ]
        return custom_urls + urls
    
    def run_regeneration(self, request):
        """Ручной запуск регенерации статей."""
        from django_q.tasks import async_task
        from .tasks import daily_article_regeneration
        
        try:
            # Запускаем задачу асинхронно через Django-Q
            async_task(
                daily_article_regeneration,
                task_name=f"manual_regeneration_{timezone.now().timestamp()}",
                group='article_regeneration',
                timeout=3600  # 1 час на выполнение
            )
            messages.success(
                request,
                "✅ Задача регенерации статей запущена! Результаты будут доступны в логах Django-Q."
            )
        except Exception as e:
            messages.error(
                request,
                f"❌ Ошибка запуска регенерации: {str(e)}"
            )
        
        return HttpResponseRedirect(reverse('admin:Moderation_articleregeneration_changelist'))

