from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Исправляет абсолютные пути в FileField, заменяя их относительными (для картинок постов)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--prefix",
            help="Некорректный префикс, который нужно удалить (по умолчанию MEDIA_ROOT).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Только показать, что будет изменено, без сохранения.",
        )

    def handle(self, *args, **options):
        from blog.models import Post

        prefix = options["prefix"] or str(Path(settings.MEDIA_ROOT).resolve())
        prefix = prefix.replace("\\", "/").rstrip("/") + "/"

        dry_run = options["dry_run"]
        updated = 0

        qs = Post.objects.exclude(kartinka="").exclude(kartinka__isnull=True)
        for post in qs.iterator():
            current = (post.kartinka.name or "").replace("\\", "/")
            if current.startswith(prefix):
                new_path = current[len(prefix):]
                self.stdout.write(f"Post #{post.id}: {current} → {new_path}")
                if not dry_run:
                    Post.objects.filter(pk=post.pk).update(kartinka=new_path)
                updated += 1

        if dry_run:
            self.stdout.write(self.style.WARNING(f"DRY-RUN: изменений не внесено. Исправлений потребуется: {updated}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"✅ Обновлено записей: {updated}"))


