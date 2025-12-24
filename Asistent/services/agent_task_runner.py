import logging
from typing import Any, Callable, Dict, Optional

from django.utils import timezone


logger = logging.getLogger(__name__)


def execute_agent_task(
    task_id: int,
    *,
    agent_method: Callable[[Any], Dict[str, Any]],
    success_message: Optional[str] = None,
    message_extractor: Optional[Callable[[Dict[str, Any]], str]] = None,
    metadata_builder: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
    persist_message: bool = True,
) -> Dict[str, Any]:
    """
    Унифицированный запуск задач AI-агента.

    Args:
        task_id: идентификатор задачи AITask
        agent_method: вызываемый метод AIAgent (должен принимать AITask)
        success_message: текст сообщения по умолчанию, если message_extractor не задан
        message_extractor: функция, возвращающая текст из результата
        metadata_builder: функция, возвращающая метаданные для AIMessage
        persist_message: создавать ли AIMessage при успехе
    """
    from Asistent.models import AITask, AIMessage

    task = AITask.objects.get(id=task_id)
    task.status = "in_progress"
    task.save(update_fields=["status"])

    agent_result: Dict[str, Any]
    try:
        agent_result = agent_method(task)
    except Exception as exc:
        logger.exception("❌ Ошибка выполнения метода агента")
        task.error_message = str(exc)
        task.status = "failed"
        task.completed_at = timezone.now()
        task.save(update_fields=["error_message", "status", "completed_at"])
        return {"success": False, "error": str(exc)}

    is_success = agent_result.get("success", False)

    if is_success:
        task.status = "completed"
        task.completed_at = timezone.now()
        task.result = agent_result
        task.save(update_fields=["status", "completed_at", "result"])

        if persist_message:
            message_text = (
                message_extractor(agent_result)
                if message_extractor
                else agent_result.get("message") or success_message or "✅ Выполнено"
            )

            metadata = metadata_builder(agent_result) if metadata_builder else {"task_id": task_id}

            if message_text:
                AIMessage.objects.create(
                    conversation=task.conversation,
                    role="assistant",
                    content=message_text,
                    metadata=metadata,
                )
    else:
        error_message = agent_result.get("error", "Неизвестная ошибка")
        task.error_message = error_message
        task.status = "failed"
        task.completed_at = timezone.now()
        task.result = agent_result
        task.save(update_fields=["error_message", "status", "completed_at", "result"])

        if persist_message:
            AIMessage.objects.create(
                conversation=task.conversation,
                role="assistant",
                content=f"❌ Ошибка: {error_message}",
                metadata={"task_id": task_id, "error": error_message},
            )

    return agent_result

