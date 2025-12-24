import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from Asistent.models import AIMessage, AITask

logger = logging.getLogger(__name__)


@dataclass
class TaskExecutionContext:
    """
    Утилита для унифицированной работы с AITask:
    - переключение статусов (start/complete/fail)
    - создание ответных сообщений AI
    """

    task: AITask
    persist_message: bool = True

    @classmethod
    def start(cls, task_id: int, *, persist_message: bool = True) -> "TaskExecutionContext":
        task = (
            AITask.objects.select_related("conversation")
            .filter(id=task_id)
            .first()
        )
        if not task:
            raise AITask.DoesNotExist(f"AITask #{task_id} не найдена")

        task.start()
        logger.info("🚀 Старт задачи #%s (%s)", task_id, task.task_type)
        return cls(task=task, persist_message=persist_message)

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _build_metadata(self, metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        default_metadata = {"task_id": self.task.id, "task_type": self.task.task_type}
        if metadata:
            default_metadata.update(metadata)
        return default_metadata

    def _create_message(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        if not self.persist_message:
            return

        AIMessage.objects.create(
            conversation=self.task.conversation,
            role="assistant",
            content=content,
            metadata=self._build_metadata(metadata),
        )

    # ------------------------------------------------------------------ #
    # публичные методы
    # ------------------------------------------------------------------ #
    def complete(
        self,
        *,
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self.task.complete(result)
        if message:
            self._create_message(message, metadata)

        logger.info("✅ Задача #%s завершена успешно", self.task.id)
        return {"success": True, "task_id": self.task.id, "result": result or {}}

    def fail(
        self,
        error_message: str,
        *,
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self.task.fail(error_message)

        if message:
            metadata = metadata or {}
            metadata.setdefault("status", "failed")
            metadata.setdefault("error", error_message)
            self._create_message(message, metadata)

        logger.error("❌ Задача #%s завершилась ошибкой: %s", self.task.id, error_message)
        return {"success": False, "error": error_message}

    def update_result(self, result: Dict[str, Any]) -> None:
        """
        Позволяет обновить поле result без завершения задачи (редкий случай).
        """
        self.task.result = result
        self.task.save(update_fields=["result"])


