"""
Команда для очистки старых анонимных лайков
Использование: python manage.py cleanup_anonymous_likes --days 30
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from blog.models_likes import Like


class Command(BaseCommand):
    help = 'Удаляет старые анонимные лайки для очистки базы данных'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Количество дней, после которых анонимные лайки будут удалены (по умолчанию: 30)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать количество лайков для удаления без фактического удаления'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        
        # Вычисляем дату отсечки
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Находим старые анонимные лайки
        old_anonymous_likes = Like.objects.filter(
            user__isnull=True,
            session_key__isnull=False,
            created__lt=cutoff_date
        )
        
        count = old_anonymous_likes.count()
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'Режим проверки: найдено {count} анонимных лайков старше {days} дней'
                )
            )
            if count > 0:
                self.stdout.write(
                    self.style.WARNING(
                        'Запустите команду без --dry-run для удаления этих лайков'
                    )
                )
        else:
            if count == 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Не найдено анонимных лайков старше {days} дней'
                    )
                )
            else:
                old_anonymous_likes.delete()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Успешно удалено {count} анонимных лайков старше {days} дней'
                    )
                )

