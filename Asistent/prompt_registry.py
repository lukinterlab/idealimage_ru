"""
Реестр промптов GigaChat, предоставляющий кэшированный доступ к шаблонам.
Позволяет централизовать управление шаблонами и уменьшить дублирование строк.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from .models import PromptTemplate

logger = logging.getLogger(__name__)


# ПРОМПТЫ ДЛЯ SEO-ОПТИМИЗАЦИИ
# =============================================================================
class PromptRegistry:
    """
    Централизованный доступ к шаблонам промптов.
    Использует name в качестве ключа (уникальность лежит на администраторе).
    """

    # =============================================================================
    # ПОЛУЧЕНИЕ ШАБЛОНА ПРОМПТА
    # =============================================================================
    @classmethod
    def get_template(cls, name: str) -> Optional[PromptTemplate]:
        template = (
            PromptTemplate.objects.filter(name=name, is_active=True)
            .order_by('-updated_at')
            .first()
        )
        if not template:
            logger.debug("PromptTemplate '%s' не найден или деактивирован", name)
        return template

    # =============================================================================
    # РЕНДЕРИНГ ШАБЛОНА ПРОМПТА
    # =============================================================================
    @classmethod
    def render(cls, name: str, params: Optional[Dict[str, Any]] = None, default: Optional[str] = None) -> Optional[str]:
        """
        Получает шаблон по имени и подставляет параметры. Если шаблон не найден,
        возвращает default (или None).
        """
        template = cls.get_template(name)
        mapping = params or {}
        if template:
            try:
                return template.template.format(**mapping)
            except KeyError as exc:
                logger.warning("Отсутствует переменная %s при рендеринге промпта '%s'", exc, name)
                return template.template
        if default:
            try:
                return default.format(**mapping)
            except KeyError:
                return default
        return None

    # =============================================================================
    # ПОЛУЧЕНИЕ МЕТАДАННЫХ ШАБЛОНА ПРОМПТА
    # =============================================================================
    @classmethod
    def get_metadata(cls, name: str) -> Dict[str, Any]:
        template = cls.get_template(name)
        if not template:
            return {}
        return {
            'id': template.id,
            'name': template.name,
            'category': template.category,
            'updated_at': template.updated_at.isoformat(),
            'variables': template.variables,
        }

    # =============================================================================
    # УВЕЛИЧЕНИЕ СЧЁТЧИКА ИСПОЛЬЗОВАНИЙ ШАБЛОНА ПРОМПТА
    # =============================================================================
    @classmethod
    def increment_usage(cls, name: str) -> None:
        template = cls.get_template(name)
        if not template:
            return
        PromptTemplate.objects.filter(pk=template.pk).update(
            usage_count=template.usage_count + 1
        )
    
    # =============================================================================
    # ОЧИСТКА КЭША ШАБЛОНОВ ПРОМПТОВ (удалено - кэширование отключено)
    # =============================================================================
    @classmethod
    def invalidate(cls, name: Optional[str] = None) -> None:
        """Заглушка для совместимости. Кэширование отключено."""
        pass

