import logging
from typing import Any, Dict, Optional

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from Asistent.models import IntegrationEvent

logger = logging.getLogger(__name__)

DEFAULT_COOLDOWN_MINUTES = getattr(settings, "INTEGRATION_ALERT_COOLDOWN_MINUTES", 30)


def _cache_key(service: str, code: str) -> str:
    return f"integration-alert:{service}:{code}"


def record_integration_error(
    service: str,
    code: str,
    message: str,
    *,
    severity: str = "warning",
    context: Optional[Dict[str, Any]] = None,
    cooldown_minutes: Optional[int] = None,
) -> None:
    cooldown = (cooldown_minutes or DEFAULT_COOLDOWN_MINUTES) * 60
    key = _cache_key(service, code)

    if not cache.get(key):
        from Asistent.services.djangoq_monitor import notify_admin_alert  # локальный импорт

        details = context or {}
        details_text = "\n".join(f"{k}: {v}" for k, v in details.items()) if details else ""
        notify_admin_alert(
            f"[{service}] ошибка {code}: {message}\n{details_text}".strip(),
            severity=severity,
            prefix="Integration",
        )
        cache.set(key, {"ts": timezone.now().isoformat(), "message": message}, timeout=cooldown)
    else:
        logger.debug("🔁 Пропуск повторного алерта для %s (%s)", service, code)

    try:
        IntegrationEvent.objects.create(
            service=service[:32],
            code=code[:64],
            message=message,
            severity=severity,
            extra=context or {},
        )
    except Exception as exc:  # pragma: no cover
        logger.warning("⚠️ Не удалось записать IntegrationEvent: %s", exc)

    logger.warning("❌ Integration error [%s %s]: %s", service, code, message)


def record_integration_success(service: str, code: str = "ok") -> None:
    cache.delete(_cache_key(service, code))
    try:
        IntegrationEvent.objects.create(
            service=service[:32],
            code=code[:64],
            message="OK",
            severity="info",
        )
    except Exception:
        pass


def format_context(**kwargs) -> Dict[str, Any]:
    context: Dict[str, Any] = {}
    for key, value in kwargs.items():
        try:
            context[key] = value
        except Exception:
            context[key] = str(value)
    context["timestamp"] = timezone.now().isoformat()
    return context

