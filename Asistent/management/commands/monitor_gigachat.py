from django.core.management.base import BaseCommand

from Asistent.services.gigachat_monitor import (
    check_gigachat_usage,
    reports_to_json,
)


class Command(BaseCommand):
    help = "Проверяет использование GigaChat и отправляет алерты при превышении лимитов или большом количестве ошибок."

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            action="store_true",
            help="Вывести отчёт в формате JSON",
        )
        parser.add_argument(
            "--no-alerts",
            action="store_true",
            help="Не отправлять уведомления (только отчёт)",
        )

    def handle(self, *args, **options):
        send_alerts = not options["no_alerts"]

        reports, alerts = check_gigachat_usage(send_alerts=send_alerts)

        if options["json"]:
            self.stdout.write(reports_to_json(reports))
        else:
            if not reports:
                self.stdout.write(self.style.WARNING("Нет данных о GigaChat."))
                return

            self.stdout.write(self.style.SUCCESS("📊 Статус GigaChat:"))
            for report in reports:
                percent = (
                    f"{report.percent_of_limit:.2f}%"
                    if report.percent_of_limit is not None
                    else "—"
                )
                self.stdout.write(
                    f" • {report.model}: {report.status.upper()} — {report.message} "
                    f"(ошибок {report.failed_requests}/{report.total_requests}, "
                    f"стоимость сегодня {report.cost_today}₽, лимит {report.daily_limit}, {percent})"
                )

            self.stdout.write("")
            if send_alerts:
                self.stdout.write(
                    self.style.SUCCESS(f"Отправлено уведомлений: {alerts}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING("Алерты не отправлялись (--no-alerts).")
                )

