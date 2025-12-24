"""
URL маршруты для AI-Ассистента
"""
from django.urls import path, include
from django.views.generic import RedirectView
from . import views
# Модерация теперь работает только через Django Admin (/admin/)

app_name = 'asistent'

urlpatterns = [
    # Корневой URL - редирект на админ-панель
    path('', RedirectView.as_view(pattern_name='asistent:admin_dashboard', permanent=False), name='index'),
    
    # Админ-панель - задания
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/calendar/', views.task_calendar, name='task_calendar'),
    path('admin-panel/tasks/management/', views.tasks_management, name='tasks_management'),
    path('admin-panel/tasks/create/', views.create_task, name='create_task'),
    path('admin-panel/tasks/<int:task_id>/edit/', views.edit_task, name='edit_task'),
    path('admin-panel/tasks/<int:task_id>/cancel/', views.cancel_task, name='cancel_task'),
    
    # URL для пайплайнов удалены - система пайплайнов больше не используется
    
    # AI расписания (старые маршруты для обратной совместимости)
    path('admin-panel/ai-schedules/', views.ai_schedules, name='ai_schedules'),
    path('admin-panel/integration-events/', views.integration_events, name='integration_events'),
    path('admin-panel/ai-schedules/create/', views.create_ai_schedule, name='create_ai_schedule'),
    path('admin-panel/ai-schedules/<int:schedule_id>/edit/', views.edit_ai_schedule, name='edit_ai_schedule'),
    path('admin-panel/ai-schedules/<int:schedule_id>/delete/', views.delete_ai_schedule, name='delete_ai_schedule'),
    path('admin-panel/ai-schedules/<int:schedule_id>/run/', views.run_ai_schedule, name='run_ai_schedule'),
    path('admin-panel/ai-schedules/<int:schedule_id>/toggle/', views.toggle_ai_schedule, name='toggle_ai_schedule'),
    path('admin-panel/ai-schedules/bulk-action/', views.bulk_ai_schedules_action, name='bulk_ai_schedules_action'),
    
    # Новые маршруты для управления расписаниями (schedule app)
    path('schedules/', include('Asistent.schedule.urls', namespace='schedule')),
    
    # Системные задачи Django-Q Schedule (CRUD)
    path('admin-panel/system-schedules/create/', views.create_system_schedule, name='create_system_schedule'),
    path('admin-panel/system-schedules/<int:schedule_id>/edit/', views.edit_system_schedule, name='edit_system_schedule'),
    path('admin-panel/system-schedules/<int:schedule_id>/delete/', views.delete_system_schedule, name='delete_system_schedule'),
    
    # Шаблоны промптов
    path('admin-panel/prompts/', views.prompt_templates_list, name='prompt_templates_list'),
    path('admin-panel/prompts/create/', views.prompt_template_create, name='prompt_template_create'),
    path('admin-panel/prompts/<int:template_id>/edit/', views.prompt_template_edit, name='prompt_template_edit'),
    path('admin-panel/prompts/<int:template_id>/delete/', views.prompt_template_delete, name='prompt_template_delete'),
    path('admin-panel/prompts/<int:template_id>/test/', views.prompt_template_test, name='prompt_template_test'),
    path('api/prompt/<int:prompt_id>/variables/', views.get_prompt_variables, name='get_prompt_variables'),
    
    # Журнал AI-агента
    path('admin-panel/ai-message-log/', views.ai_message_log, name='ai_message_log'),
    path('admin-panel/ai-message-log/clear/', views.clear_ai_messages, name='clear_ai_messages'),
    
    # Django-Q управление
    path('api/start-djangoq/', views.api_start_djangoq, name='api_start_djangoq'),
    path('api/djangoq-status/', views.api_djangoq_status, name='api_djangoq_status'),
    path('admin-panel/sync-schedules/', views.sync_schedules_ajax, name='sync_schedules_ajax'),
    
    # Оптимизация токенов
    path('admin-panel/token-optimization/', views.token_optimization, name='token_optimization'),
    path('api/token-analysis/', views.api_token_analysis, name='api_token_analysis'),
    
    # Django-Q управление задачами
    path('admin-panel/djangoq/tasks/active/', views.djangoq_tasks_active, name='djangoq_tasks_active'),
    path('admin-panel/djangoq/tasks/queued/', views.djangoq_tasks_queued, name='djangoq_tasks_queued'),
    path('admin-panel/djangoq/tasks/recent/', views.djangoq_tasks_recent, name='djangoq_tasks_recent'),
    path('admin-panel/djangoq/tasks/all/', views.djangoq_tasks_all, name='djangoq_tasks_all'),
    path('admin-panel/djangoq/task/create/', views.djangoq_task_create, name='djangoq_task_create'),
    path('admin-panel/djangoq/task/<str:task_id>/<str:task_type>/', views.djangoq_task_detail, name='djangoq_task_detail'),
    path('admin-panel/djangoq/task/<str:task_id>/run/', views.djangoq_task_run_now, name='djangoq_task_run_now'),
    path('admin-panel/djangoq/task/<str:task_id>/delete/', views.djangoq_task_delete, name='djangoq_task_delete'),
    
    # ContentTask управление
    path('admin-panel/content-tasks/available/', views.content_tasks_available, name='content_tasks_available'),
    path('admin-panel/content-tasks/active/', views.content_tasks_active, name='content_tasks_active'),
    path('admin-panel/content-tasks/completed/', views.content_tasks_completed, name='content_tasks_completed'),
    path('admin-panel/content-task/<int:task_id>/', views.content_task_detail, name='content_task_detail'),
    
    # AISchedule управление
    path('admin-panel/ai-schedules/active/', views.ai_schedules_active, name='ai_schedules_active'),
    path('admin-panel/ai-schedules/inactive/', views.ai_schedules_inactive, name='ai_schedules_inactive'),
    path('admin-panel/ai-schedules/stats-today/', views.ai_schedules_stats_today, name='ai_schedules_stats_today'),
    
    # API endpoints
    path('api/tasks/available/', views.api_available_tasks, name='api_available_tasks'),
    path('api/tasks/my/', views.api_my_tasks, name='api_my_tasks'),
    path('api/notifications/', views.api_notifications, name='api_notifications'),
    path('api/task-status/<str:task_id>/', views.api_task_status, name='api_task_status'),
    path('api/schedule/preview/', views.api_schedule_preview, name='schedule_preview'),
    
    # Dashboard аналитики
    path('analytics/', views.ai_analytics_dashboard, name='ai_analytics_dashboard'),
    
    # AI-Чат
    path('chat/', views.ai_chat_view, name='ai_chat'),
    path('api/chat/create-conversation/', views.api_create_conversation, name='api_create_conversation'),
    path('api/chat/send/', views.api_chat_send, name='api_chat_send'),
    path('api/conversation/<int:conversation_id>/delete/', views.api_delete_conversation, name='api_delete_conversation'),
    
    # AI Knowledge Base API
    path('api/knowledge/search/', views.api_knowledge_search, name='api_knowledge_search'),
    path('api/knowledge/counts/', views.api_knowledge_counts, name='api_knowledge_counts'),
    path('api/knowledge/list/<str:category>/', views.api_knowledge_list, name='api_knowledge_list'),
    path('api/knowledge/get/<int:knowledge_id>/', views.api_knowledge_get, name='api_knowledge_get'),
    path('api/knowledge/create/', views.api_knowledge_create, name='api_knowledge_create'),
    path('api/knowledge/<int:knowledge_id>/update/', views.api_knowledge_update, name='api_knowledge_update'),
    path('api/knowledge/<int:knowledge_id>/delete/', views.api_knowledge_delete, name='api_knowledge_delete'),
    
    # ЧАТ-БОТ для пользователей (перенесено в ChatBot_AI)
    path('', include('Asistent.ChatBot_AI.urls')),
    
    # GigaChat мониторинг
    path('api/gigachat-balance/', views.api_gigachat_balance, name='api_gigachat_balance'),
    path('api/gigachat-settings-update/', views.api_gigachat_settings_update, name='api_gigachat_settings_update'),
    path('admin-panel/ai-schedules/runs/', views.schedule_runs, name='schedule_runs'),
    path('admin-panel/ai-schedules/runs/<int:run_id>/detail/', views.schedule_run_detail, name='schedule_run_detail'),
    # URL для retry_pipeline_run удален - система пайплайнов больше не используется
    
    # Парсинг популярных статей
    path('parsed-articles/', views.parsed_articles_dashboard, name='parsed_articles_dashboard'),
    path('api/parsed-articles/<int:article_id>/toggle-selection/', views.api_parsed_articles_toggle_selection, name='api_parsed_articles_toggle_selection'),
    path('api/parsed-articles/autopost/', views.api_parsed_articles_autopost, name='api_parsed_articles_autopost'),
]

# Модерация работает через Django Admin, кастомные URL больше не нужны

