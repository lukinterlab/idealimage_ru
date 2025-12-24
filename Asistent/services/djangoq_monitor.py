import logging
import subprocess
import sys
from datetime import timedelta
from pathlib import Path
from typing import Dict, Optional

from django.apps import apps
from django.conf import settings
from django.utils import timezone

from Asistent.services.telegram_client import get_telegram_client

logger = logging.getLogger(__name__)


def check_djangoq_status() -> Dict:
    """
    Возвращает расширенный статус Django-Q кластера.
    Используется и в веб-интерфейсе, и в health-check командe.
    """
    try:
        OrmQ = apps.get_model("django_q", "OrmQ")
        Success = apps.get_model("django_q", "Success")
    except (LookupError, ImportError) as import_error:
        logger.error("Не удалось получить модели Django-Q: %s", import_error)
        return {
            "is_running": False,
            "active_tasks": 0,
            "queued_tasks": 0,
            "recent_tasks": 0,
            "last_task": None,
            "status_message": f"❌ Ошибка импорта Django-Q: {import_error}",
            "error": str(import_error),
        }

    stat_info = None
    stat_status = None

    try:
        from django_q.monitor import Stat

        stats = list(Stat.get_all())
        if stats:
            stat = stats[0]
            stat_info = {
                "cluster_id": stat.cluster_id,
                "status": stat.status,
                "uptime": stat.uptime() if callable(getattr(stat, "uptime", None)) else None,
                "task_q_size": getattr(stat, "task_q_size", None),
                "done_q_size": getattr(stat, "done_q_size", None),
                "reincarnations": getattr(stat, "reincarnations", None),
                "workers": getattr(stat, "workers", None),
            }
            stat_status = stat.status
    except ImportError:
        stat_info = None
    except Exception as monitor_error:
        logger.warning("Не удалось получить статистику Django-Q: %s", monitor_error)

    try:
        now = timezone.now()

        active_count = OrmQ.objects.filter(lock__isnull=False).count()
        queued_count = OrmQ.objects.filter(lock__isnull=True).count()

        hour_ago = now - timedelta(hours=1)
        recent_tasks_qs = Success.objects.filter(stopped__gte=hour_ago)
        recent_count = recent_tasks_qs.count()

        last_task = Success.objects.order_by("-stopped").first()

        cluster_name = getattr(settings, "Q_CLUSTER", {}).get("name")

        is_running = False
        status_message = ""

        if active_count > 0:
            is_running = True
            status_message = f"✅ Активно: {active_count} задач выполняется"
        elif stat_status in {"working", "idle", "WORKING", "IDLE"}:
            is_running = True
            normalized = str(stat_status).upper()
            readable = "в работе" if normalized == "WORKING" else "ожидает задания"
            status_message = f"✅ Кластер {readable}"
        elif recent_count > 0:
            is_running = True
            minutes_ago = int((now - last_task.stopped).total_seconds() / 60) if last_task else 0
            status_message = f"✅ Работает: последняя задача {minutes_ago} мин назад"
        elif queued_count > 0:
            status_message = f"⚠️ Очередь: {queued_count} задач ждут выполнения"
        else:
            status_message = "❌ Остановлен: нет активности"

        return {
            "is_running": is_running,
            "active_tasks": active_count,
            "queued_tasks": queued_count,
            "recent_tasks": recent_count,
            "last_task": last_task,
            "cluster_name": cluster_name,
            "cluster_stat": stat_info,
            "heartbeat": None,
            "heartbeat_age_seconds": None,
            "status_message": status_message,
            "checked_at": now,
        }
    except Exception as exc:
        logger.error("Ошибка проверки Django-Q: %s", exc)
        return {
            "is_running": False,
            "active_tasks": 0,
            "queued_tasks": 0,
            "recent_tasks": 0,
            "last_task": None,
            "status_message": f"❌ Ошибка: {exc}",
            "error": str(exc),
        }


def start_djangoq_cluster() -> Dict[str, Optional[int]]:
    """
    Запускает `python manage.py qcluster` в фоне и возвращает PID процесса.
    Используется health-check командой и админкой.
    """
    manage_py = Path(settings.BASE_DIR) / "manage.py"
    python_bin = sys.executable
    cwd = Path(settings.BASE_DIR)

    try:
        if sys.platform == "win32":
            # Windows: отдельная консоль, чтобы процесс не блокировал health-check
            creation_flags = subprocess.CREATE_NEW_CONSOLE  # type: ignore[attr-defined]
            process = subprocess.Popen(
                [python_bin, str(manage_py), "qcluster"],
                cwd=cwd,
                creationflags=creation_flags,
            )
        else:
            stdout_path = cwd / "logs" / "qcluster.daemon.log"
            stdout_path.parent.mkdir(exist_ok=True)
            with open(stdout_path, "ab", buffering=0) as log_file:
                process = subprocess.Popen(
                    [python_bin, str(manage_py), "qcluster"],
                    cwd=cwd,
                    stdout=log_file,
                    stderr=log_file,
                    start_new_session=True,
                )
        logger.info("🚀 Запущен qcluster (PID=%s)", process.pid)
        return {"success": True, "pid": process.pid}
    except Exception as exc:
        logger.error("❌ Не удалось запустить qcluster: %s", exc, exc_info=True)
        return {"success": False, "error": str(exc)}


def notify_admin_alert(message: str, severity: str = "info", prefix: str = "System") -> None:
    chat_id = getattr(settings, "ADMIN_ALERT_CHAT_ID", "") or getattr(settings, "CHAT_ID8", "")
    if not chat_id:
        logger.warning("ADMIN_ALERT_CHAT_ID не настроен, сообщение: %s", message)
        return

    prefix_icon = {
        "info": "ℹ️",
        "warning": "⚠️",
        "error": "❌",
    }.get(severity, "ℹ️")

    title = prefix or "System"
    text = f"{prefix_icon} {title}: {message}\n⏱ {timezone.localtime().strftime('%d.%m %H:%M:%S')}"
    client = get_telegram_client()
    if not client.send_message(chat_id, text):
        logger.error("Не удалось отправить Telegram-уведомление: %s", text)


def notify_qcluster_alert(message: str, severity: str = "info") -> None:
    """Совместимость: уведомления для Django-Q."""
    notify_admin_alert(message, severity=severity, prefix="Django-Q")

