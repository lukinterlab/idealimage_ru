from __future__ import annotations

import logging
from datetime import timedelta
from typing import Dict, Optional

from django.conf import settings
from django.utils import timezone

from .models import AISchedule, AIScheduleRun
from .context import ScheduleContext
from .logger import RunLogger
from .services import PromptGenerationWorkflow, SystemTaskRunner, ManualWorkflow
from .horoscope import generate_horoscope_from_prompt_template


""" Базовый класс для стратегий расписания  """
class ScheduleStrategy:
    strategy_type: str = 'base'

    def __init__(self, schedule: AISchedule):
        self.schedule = schedule
        self.logger = RunLogger(schedule)
        self.run = None
        self.context: Optional[ScheduleContext] = None
        self._logger = logging.getLogger(__name__)

    """ Метод для выполнения стратегии  """
    def execute(self) -> Dict:
        skip_result = self._ensure_single_run()
        if skip_result is not None:
            return skip_result

        self.run = self.logger.start(self.strategy_type)
        self.context = ScheduleContext(schedule=self.schedule, run=self.run)
        try:
            result = self._execute(self.context)
            status = result.get('status', 'success')
            created_count = result.get('created_count', 0)
            errors = result.get('errors', [])
            self.logger.finish(
                status=status,
                created_count=created_count,
                errors=errors,
                context_snapshot=self.context.to_dict(),
                result_payload=result,
            )
            return result
        except Exception as exc:
            if self.context:
                self.context.add_log('error', 'Unhandled exception', {'error': str(exc)})
            self.logger.finish(
                status='failed',
                errors=[str(exc)],
                context_snapshot=self.context.to_dict() if self.context else {},
            )
            raise

    
    """ Метод для выполнения стратегии  """
    def _execute(self, context: ScheduleContext) -> Dict:
        raise NotImplementedError

    """ Метод для проверки наличия активного запуска расписания  """
    def _ensure_single_run(self) -> Optional[Dict]:
        existing_run = AIScheduleRun.objects.filter(
            schedule=self.schedule,
            status='running',
        ).order_by('-started_at').first()

        if not existing_run:
            return None

        stale_minutes = getattr(settings, 'AISCHEDULE_STALE_RUN_MINUTES', 45)
        stale_delta = timedelta(minutes=stale_minutes)
        now = timezone.now()

        if existing_run.started_at and now - existing_run.started_at > stale_delta:
            errors = list(existing_run.errors or [])
            errors.append(f'Stale run auto-closed at {now.isoformat()}')
            existing_run.errors = errors
            existing_run.status = 'failed'
            existing_run.finished_at = now
            existing_run.save(update_fields=['errors', 'status', 'finished_at'])
            self._logger.warning(
                "Стратегия %s: предыдущий запуск #%s закрыт как устаревший",
                self.strategy_type,
                existing_run.id,
            )
            return None

        self._logger.info(
            "Стратегия %s: пропуск запуска, уже выполняется run #%s",
            self.strategy_type,
            existing_run.id,
        )
        return {
            'status': 'skipped',
            'success': False,
            'created_count': 0,
            'reason': 'already_running',
            'active_run_id': existing_run.id,
            'started_at': existing_run.started_at.isoformat() if existing_run.started_at else None,
        }

""" Стратегия для генерации промпта  """
class PromptScheduleStrategy(ScheduleStrategy):
    strategy_type = 'prompt'

    """ Метод для выполнения стратегии  """
    def _execute(self, context: ScheduleContext) -> Dict:
        workflow = PromptGenerationWorkflow(schedule=self.schedule, context=context)
        return workflow.run(current_time=timezone.now())


""" Стратегия для системного запуска расписания  """
class SystemScheduleStrategy(ScheduleStrategy):
    strategy_type = 'system'

    def _execute(self, context: ScheduleContext) -> Dict:
        runner = SystemTaskRunner(schedule=self.schedule, context=context)
        return runner.run(current_time=timezone.now())


""" Стратегия для ручного запуска расписания  """
class ManualScheduleStrategy(ScheduleStrategy):
    strategy_type = 'manual'

    def _execute(self, context: ScheduleContext) -> Dict:
        workflow = ManualWorkflow(schedule=self.schedule, context=context)
        return workflow.run(current_time=timezone.now())


""" Стратегия для генерации гороскопов  """
class HoroscopeScheduleStrategy(ScheduleStrategy):
    strategy_type = 'horoscope'

    def _execute(self, context: ScheduleContext) -> Dict:
        """
        Генерация гороскопов через специализированный модуль.
        Поддерживает генерацию всех 12 знаков за один запуск.
        """
        result = generate_horoscope_from_prompt_template(self.schedule.id)
        
        # Преобразуем результат в формат стратегии
        return {
            'status': result.get('status', 'success' if result.get('success') else 'failed'),
            'created_count': result.get('created_count', len(result.get('created_posts', []))),
            'errors': result.get('errors', []),
            'result': result
        }

