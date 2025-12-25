"""
Модели для приложения AI-Ассистент
Разделены на логические модули для лучшей организации кода
"""

# Импорт всех моделей для обратной совместимости
from .tasks import (
    ContentTask,
    TaskAssignment,
    AuthorTaskRejection,
    TaskHistory,
)

from .ai_interactions import (
    AIConversation,
    AIMessage,
    AITask,
)

from .finances import (
    AuthorBalance,
    BonusFormula,
    BonusCalculation,
    DonationDistribution,
    AuthorDonationShare,
)

from .ai_settings import (
    GigaChatSettings,
)

from .prompts import (
    PromptTemplate,
    PromptTemplateVersion,
)

from .knowledge import (
    AIKnowledgeBase,
)

from .notifications import (
    AuthorNotification,
)

from .profiles import (
    AuthorStyleProfile,
    BotProfile,
    BotActivity,
)

from .metrics import (
    ArticleGenerationMetric,
    GigaChatUsageStats,
)

from .logs import (
    IntegrationEvent,
    SystemLog,
)

from .generated_content import (
    AIGeneratedArticle,
)

# Импорт моделей модерации из moderations
from Asistent.moderations.models import (
    ArticleModerationSettings,
    CommentModerationSettings,
    ModerationLog,
)

# Алиасы для обратной совместимости
ModerationCriteria = ArticleModerationSettings
CommentModerationCriteria = CommentModerationSettings
CommentModerationLog = ModerationLog

# =============================================================================
# ОБРАТНАЯ СОВМЕСТИМОСТЬ: Ленивый импорт моделей из schedule
# =============================================================================
def __getattr__(name):
    """
    Ленивый импорт моделей из schedule для обратной совместимости.
    Позволяет использовать: from Asistent.models import AISchedule
    Без циклического импорта при загрузке модуля.
    """
    if name == 'AISchedule':
        from ..schedule.models import AISchedule
        return AISchedule
    elif name == 'AIScheduleRun':
        from ..schedule.models import AIScheduleRun
        return AIScheduleRun
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    # Tasks
    'ContentTask',
    'TaskAssignment',
    'AuthorTaskRejection',
    'TaskHistory',
    # AI Interactions
    'AIConversation',
    'AIMessage',
    'AITask',
    # Finances
    'AuthorBalance',
    'BonusFormula',
    'BonusCalculation',
    'DonationDistribution',
    'AuthorDonationShare',
    # AI Settings
    'GigaChatSettings',
    # Prompts
    'PromptTemplate',
    'PromptTemplateVersion',
    # Knowledge
    'AIKnowledgeBase',
    # Notifications
    'AuthorNotification',
    # Profiles
    'AuthorStyleProfile',
    'BotProfile',
    'BotActivity',
    # Metrics
    'ArticleGenerationMetric',
    'GigaChatUsageStats',
    # Logs
    'IntegrationEvent',
    'SystemLog',
    # Generated Content
    'AIGeneratedArticle',
    # Moderation (aliases)
    'ModerationCriteria',
    'CommentModerationCriteria',
    'CommentModerationLog',
]

