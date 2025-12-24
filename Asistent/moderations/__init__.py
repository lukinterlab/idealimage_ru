"""
Упрощённая система модерации контента.

Основные компоненты:
- ArticleModerationSettings - настройки модерации статей
- CommentModerationSettings - настройки модерации комментариев
- ModerationLog - журнал проверок

Основные функции:
- check_article(post) - проверить статью
- check_comment(comment) - проверить комментарий
- moderate_article(post) - выполнить проверку без изменения статуса
- moderate_comment(comment) - выполнить проверку без изменения статуса

Использование:
    from Asistent.moderations import check_article, check_comment
    
    # Проверить статью
    passed = check_article(post)
    
    # Проверить комментарий
    passed = check_comment(comment)
"""

__version__ = '2.0.0'

# Ленивые импорты для избежания циклических зависимостей
def __getattr__(name):
    """Ленивая загрузка модулей."""
    if name in ('check_article', 'check_comment', 'moderate_article', 
                'moderate_comment', 'get_article_statistics', 
                'get_comment_statistics', 'get_moderation_statistics'):
        from .moderator import (
            check_article, check_comment, moderate_article, moderate_comment,
            get_article_statistics, get_comment_statistics, get_moderation_statistics
        )
        return locals()[name]
    
    if name in ('ArticleModerationSettings', 'CommentModerationSettings', 'ModerationLog'):
        from .models import ArticleModerationSettings, CommentModerationSettings, ModerationLog
        return locals()[name]
    
    # Для обратной совместимости (legacy)
    if name == 'ai_agent_cleanup_database':
        from .signals import ai_agent_cleanup_database
        return ai_agent_cleanup_database
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
