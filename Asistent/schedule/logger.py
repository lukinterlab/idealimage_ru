from typing import Any, Dict, Optional
from django.utils import timezone

from .models import AISchedule, AIScheduleRun


class RunLogger:
    """
    Отвечает за создание и обновление записей AIScheduleRun.
    Используется стратегиями для фиксации прогресса и результатов.
    """

    def __init__(self, schedule: AISchedule):
        self.schedule = schedule
        self.run: Optional[AIScheduleRun] = None

    def start(self, strategy_type: str) -> AIScheduleRun:
        self.run = AIScheduleRun.objects.create(
            schedule=self.schedule,
            strategy_type=strategy_type,
            status='running',
        )
        return self.run

    def finish(
        self,
        status: str,
        created_count: int = 0,
        errors: Optional[list] = None,
        context_snapshot: Optional[Dict[str, Any]] = None,
        result_payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not self.run:
            raise RuntimeError("RunLogger.finish() called before start()")

        self.run.status = status
        self.run.created_count = created_count
        self.run.errors = errors or []
        self.run.context_snapshot = context_snapshot or {}
        self.run.result_payload = result_payload or {}
        self.run.finished_at = timezone.now()
        self.run.save(update_fields=[
            'status',
            'created_count',
            'errors',
            'context_snapshot',
            'result_payload',
            'finished_at',
        ])

