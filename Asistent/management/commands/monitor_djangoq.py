from django.conf import settings
import json

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from Asistent.services import djangoq_monitor


class Command(BaseCommand):
    """
    Health-check для Django-Q.
    Рекомендуется запускать через планировщик (Task Scheduler / cron) каждые 5-10 минут.
    """

    help = "Проверяет состояние Django-Q кластера, при необходимости перезапускает и отправляет уведомления."

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-restart",
            action="store_true",
            help="Не перезапускать кластер, только сообщать о проблеме.",
        )
        parser.add_argument(
            "--queue-threshold",
            type=int,
            default=getattr(settings, "DJANGOQ_QUEUE_ALERT_THRESHOLD", 200),
            help="Порог длины очереди для предупреждений (по умолчанию DJANGOQ_QUEUE_ALERT_THRESHOLD).",
        )
        parser.add_argument(
            "--stale-minutes",
            type=int,
            default=getattr(settings, "DJANGOQ_STALE_TASK_MINUTES", 30),
            help="Через сколько минут без задач считать кластер зависшим.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Вывести результат в формате JSON (для интеграции с внешними мониторингами).",
        )

    def handle(self, *args, **options):
        status = djangoq_monitor.check_djangoq_status()
        queue_threshold = options["queue_threshold"]
        stale_minutes = options["stale_minutes"]
        no_restart = options["no_restart"]
        as_json = options["json"]

        issues = []

        # 1. Кластер упал
        if not status.get("is_running"):
            message = status.get("status_message") or "Кластер не активен."
            djangoq_monitor.notify_qcluster_alert(message, severity="error")
            self.stderr.write(self.style.ERROR(message))

            if not no_restart:
                restart_result = djangoq_monitor.start_djangoq_cluster()
                if restart_result.get("success"):
                    pid = restart_result.get("pid")
                    msg = f"Попытка перезапуска Django-Q (PID {pid}) выполнена."
                    djangoq_monitor.notify_qcluster_alert(msg, severity="warning")
                    self.stdout.write(self.style.SUCCESS(msg))
                    if as_json:
                        self.stdout.write(json.dumps({"status": "restarted", "pid": pid}, ensure_ascii=False))
                    return
                err = restart_result.get("error", "unknown")
                djangoq_monitor.notify_qcluster_alert(f"Перезапуск не удался: {err}", severity="error")
                raise CommandError(f"Перезапуск не удался: {err}")
            raise CommandError(message)

        # 2. Очередь растёт
        queued = status.get("queued_tasks", 0)
        if queued > queue_threshold:
            msg = f"Очередь Django-Q {queued} задач превышает порог {queue_threshold}."
            djangoq_monitor.notify_qcluster_alert(msg, severity="warning")
            issues.append(msg)
        else:
            self.stdout.write(self.style.SUCCESS(f"Очередь: {queued} (порог {queue_threshold})."))

        # 3. Проверка последней задачи
        last_task = status.get("last_task")
        if last_task and last_task.stopped:
            delta = timezone.now() - last_task.stopped
            if delta.total_seconds() > stale_minutes * 60:
                msg = (
                    f"Нет завершённых задач уже {int(delta.total_seconds() // 60)} минут. "
                    "Возможна блокировка очереди."
                )
                djangoq_monitor.notify_qcluster_alert(msg, severity="warning")
                issues.append(msg)
        elif not last_task:
            msg = "Django-Q ещё ни разу не выполнял задач — проверьте расписания."
            djangoq_monitor.notify_qcluster_alert(msg, severity="warning")
            issues.append(msg)

        # 4. Общий статус
        if as_json:
            payload = {
                "status": status.get("status_message", "Статус получен."),
                "queued_tasks": queued,
                "active_tasks": status.get("active_tasks", 0),
                "recent_tasks": status.get("recent_tasks", 0),
                "issues": issues,
            }
            self.stdout.write(json.dumps(payload, ensure_ascii=False, default=str))
        else:
            self.stdout.write(self.style.SUCCESS(status.get("status_message", "Статус получен.")))

        if issues:
            raise CommandError("; ".join(issues))

