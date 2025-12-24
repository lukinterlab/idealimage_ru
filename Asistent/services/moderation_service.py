"""
Совместимость для legacy-кода.

Новый конвейер модерации вынесен в ``Asistent.moderations.services.article_pipeline``.
Этот модуль сохраняет прежний публичный интерфейс, чтобы существующие импорты
продолжили работать без изменений.
"""

from Asistent.moderations.services.article_pipeline import run_article_moderation
from Asistent.moderations.services.helpers import embedding_spam_score as _embedding_spam_score

__all__ = [
    "run_article_moderation",
    "_embedding_spam_score",
]


