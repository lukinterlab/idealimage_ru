import json
from dataclasses import dataclass, asdict
from decimal import Decimal
from typing import List, Tuple

from django.utils import timezone

from Asistent.models import GigaChatSettings, GigaChatUsageStats
from Asistent.services.integration_monitor import (
    record_integration_error,
    record_integration_success,
)


@dataclass
class UsageReport:
    model: str
    tokens_today: int
    daily_limit: int
    percent_of_limit: float | None
    failed_requests: int
    total_requests: int
    cost_today: Decimal
    status: str
    message: str


def _limit_for_model(model_name: str, settings: GigaChatSettings) -> int:
    if model_name == "GigaChat":
        return settings.lite_daily_limit or 0
    if "Pro" in model_name:
        return settings.pro_daily_limit or 0
    if "Max" in model_name:
        return settings.max_daily_limit or 0
    return 0


def _status_for_report(
    tokens_today: int,
    daily_limit: int,
    alert_threshold: int,
) -> Tuple[str, str, float | None]:
    if not daily_limit:
        return "ok", "Лимит не задан", None

    percent = round((tokens_today / daily_limit) * 100, 2)
    if percent >= alert_threshold:
        return (
            "warning",
            f"Использовано {percent:.2f}% дневного лимита ({tokens_today}/{daily_limit})",
            percent,
        )
    return (
        "ok",
        f"{percent:.2f}% от дневного лимита ({tokens_today}/{daily_limit})",
        percent,
    )


def check_gigachat_usage(send_alerts: bool = True) -> Tuple[List[UsageReport], int]:
    """
    Анализирует статистику GigaChat и при необходимости отправляет алерты.

    Returns:
        (reports, alerts_count)
    """

    settings = GigaChatSettings.objects.first()
    if not settings:
        return [], 0

    reports: List[UsageReport] = []
    alerts_sent = 0

    stats_qs = GigaChatUsageStats.objects.order_by("model_name")
    alert_threshold = settings.alert_threshold_percent or 20

    for stat in stats_qs:
        stat.reset_daily_counters_if_needed(save=True)
        daily_limit = _limit_for_model(stat.model_name, settings)
        status, message, percent = _status_for_report(
            stat.tokens_used_today,
            daily_limit,
            alert_threshold,
        )

        failure_ratio = (
            (stat.failed_requests / stat.total_requests) * 100
            if stat.total_requests
            else 0
        )

        if failure_ratio >= 50 and stat.failed_requests >= settings.task_failure_limit:
            status = "error"
            message = (
                f"{stat.failed_requests}/{stat.total_requests} запросов завершились ошибкой "
                f"(~{failure_ratio:.0f}%)"
            )

        if send_alerts:
            ctx = {
                "model": stat.model_name,
                "tokens_today": stat.tokens_used_today,
                "limit": daily_limit,
                "percent": percent,
                "failed_requests": stat.failed_requests,
                "total_requests": stat.total_requests,
                "cost_today": float(stat.cost_today),
                "checked_at": timezone.now().isoformat(),
            }

            if status == "ok":
                record_integration_success("gigachat", f"{stat.model_name}_usage")
            elif status == "warning":
                record_integration_error(
                    "gigachat",
                    f"{stat.model_name}_usage",
                    message,
                    severity="warning",
                    context=ctx,
                    cooldown_minutes=15,
                )
                alerts_sent += 1
            else:
                # Увеличиваем cooldown для ошибок до 2 часов, чтобы не спамить каждые 30 минут
                # Если ошибки продолжаются - это системная проблема, не нужно уведомлять так часто
                record_integration_error(
                    "gigachat",
                    f"{stat.model_name}_failures",
                    message,
                    severity="error",
                    context=ctx,
                    cooldown_minutes=120,  # 2 часа вместо 30 минут
                )
                alerts_sent += 1

        reports.append(
            UsageReport(
                model=stat.model_name,
                tokens_today=stat.tokens_used_today,
                daily_limit=daily_limit,
                percent_of_limit=percent,
                failed_requests=stat.failed_requests,
                total_requests=stat.total_requests,
                cost_today=stat.cost_today,
                status=status,
                message=message,
            )
        )

    return reports, alerts_sent


def reports_to_json(reports: List[UsageReport]) -> str:
    return json.dumps([asdict(r) for r in reports], ensure_ascii=False, default=str, indent=2)

