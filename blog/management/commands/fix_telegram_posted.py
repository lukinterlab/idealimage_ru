"""
Команда для исправления поля telegram_posted_at у старых опубликованных статей
Проставляет текущую дату всем опубликованным статьям без telegram_posted_at
чтобы они не отправлялись повторно в Telegram
"""
from django.core.management.base import BaseCommand
from blog.models import Post
from django.utils import timezone


class Command(BaseCommand):
    help = 'Проставляет telegram_posted_at всем старым опубликованным статьям'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать что будет изменено, без реальных изменений',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write('=' * 70)
        self.stdout.write('  ИСПРАВЛЕНИЕ TELEGRAM_POSTED_AT ДЛЯ СТАРЫХ СТАТЕЙ')
        self.stdout.write('=' * 70)
        self.stdout.write()
        
        # Находим все опубликованные статьи без telegram_posted_at
        posts = Post.objects.filter(
            status='published',
            telegram_posted_at__isnull=True
        ).order_by('created')
        
        count = posts.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('[OK] Все статьи уже имеют telegram_posted_at'))
            return
        
        self.stdout.write(f'Найдено статей без telegram_posted_at: {count}')
        self.stdout.write()
        
        if dry_run:
            self.stdout.write(self.style.WARNING('РЕЖИМ ТЕСТИРОВАНИЯ (изменения не будут сохранены)'))
            self.stdout.write()
        
        # Показываем первые 10 статей
        self.stdout.write('Первые 10 статей для обновления:')
        for i, post in enumerate(posts[:10], 1):
            self.stdout.write(f'  {i}. [ID:{post.id}] {post.title[:60]} (создана: {post.created.strftime("%Y-%m-%d")})')
        
        if count > 10:
            self.stdout.write(f'  ... и еще {count - 10} статей')
        
        self.stdout.write()
        
        if not dry_run:
            # Обновляем все статьи
            updated = posts.update(telegram_posted_at=timezone.now())
            
            self.stdout.write(self.style.SUCCESS(f'[OK] Обновлено статей: {updated}'))
            self.stdout.write()
            self.stdout.write('Все старые опубликованные статьи помечены как отправленные в Telegram')
            self.stdout.write('Теперь они не будут отправляться повторно при редактировании')
        else:
            self.stdout.write(self.style.WARNING(f'Будет обновлено статей: {count}'))
            self.stdout.write()
            self.stdout.write('Для реального обновления запустите команду без --dry-run:')
            self.stdout.write('  python manage.py fix_telegram_posted')
        
        self.stdout.write()
        self.stdout.write('=' * 70)

