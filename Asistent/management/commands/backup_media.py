import shutil
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Архивирует каталог media в backups/media и удаляет старые архивы."

    def add_arguments(self, parser):
        parser.add_argument(
            "--retention-days",
            type=int,
            default=14,
            help="Сколько дней хранить архивы медиа (по умолчанию 14).",
        )

    def handle(self, *args, **options):
        media_root = Path(settings.MEDIA_ROOT)
        if not media_root.exists():
            self.stdout.write(self.style.WARNING(f"Каталог media отсутствует: {media_root}"))
            return

        backup_dir = Path(settings.BASE_DIR) / "backups" / "media"
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        archive_base = backup_dir / f"media_backup_{timestamp}"
        archive_path = shutil.make_archive(str(archive_base), "gztar", root_dir=media_root.parent, base_dir=media_root.name)

        self.stdout.write(self.style.SUCCESS(f"✅ Архив создан: {archive_path}"))

        self._cleanup_old_archives(backup_dir, options["retention_days"])

    def _cleanup_old_archives(self, backup_dir: Path, retention_days: int) -> None:
        cutoff = timezone.now() - timedelta(days=retention_days)
        removed = 0
        for archive in backup_dir.glob("media_backup_*.tar.gz"):
            mtime = timezone.datetime.fromtimestamp(archive.stat().st_mtime, tz=timezone.utc)
            if mtime < cutoff:
                archive.unlink(missing_ok=True)
                removed += 1
        if removed:
            self.stdout.write(f"🧹 Удалено старых архивов: {removed}")


