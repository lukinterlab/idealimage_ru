"""
API endpoints для Asistent
Все AJAX-эндпоинты собраны здесь для единообразия
"""

from .tasks_api import (
    api_available_tasks,
    api_my_tasks,
    api_task_status,
)

from .notifications_api import (
    api_notifications,
)

from .chat_api import (
    api_create_conversation,
    api_chat_send,
    api_delete_conversation,
)

from .knowledge_api import (
    api_knowledge_search,
    api_knowledge_counts,
    api_knowledge_list,
    api_knowledge_get,
    api_knowledge_create,
    api_knowledge_update,
    api_knowledge_delete,
)

from .gigachat_api import (
    api_gigachat_balance,
    api_gigachat_settings_update,
)

from .djangoq_api import (
    api_djangoq_status,
    api_start_djangoq,
)

from .schedules_api import (
    api_schedule_preview,
)

from .parsed_articles_api import (
    api_parsed_articles_toggle_selection,
    api_parsed_articles_autopost,
)

from .token_api import (
    api_token_analysis,
)

__all__ = [
    # Tasks API
    'api_available_tasks',
    'api_my_tasks',
    'api_task_status',
    # Notifications API
    'api_notifications',
    # Chat API
    'api_create_conversation',
    'api_chat_send',
    'api_delete_conversation',
    # Knowledge API
    'api_knowledge_search',
    'api_knowledge_counts',
    'api_knowledge_list',
    'api_knowledge_get',
    'api_knowledge_create',
    'api_knowledge_update',
    'api_knowledge_delete',
    # GigaChat API
    'api_gigachat_balance',
    'api_gigachat_settings_update',
    # Django-Q API
    'api_djangoq_status',
    'api_start_djangoq',
    # Schedules API
    'api_schedule_preview',
    # Parsed Articles API
    'api_parsed_articles_toggle_selection',
    'api_parsed_articles_autopost',
    # Token API
    'api_token_analysis',
]

