"""
Команда для установки флага is_author всем пользователям, которые писали статьи
Использование: python manage.py set_authors
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from blog.models import Post
from Visitor.models import Profile

User = get_user_model()


class Command(BaseCommand):
    help = 'Устанавливает флаг is_author всем пользователям, которые писали статьи'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать пользователей без фактического изменения базы данных'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Находим всех пользователей, у которых есть статьи
        authors_with_posts = User.objects.filter(
            author_posts__isnull=False
        ).distinct()
        
        count = authors_with_posts.count()
        
        if count == 0:
            self.stdout.write(
                self.style.WARNING('Не найдено пользователей со статьями')
            )
            return
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'РЕЖИМ ПРОВЕРКИ: Найдено {count} пользователей со статьями:'
                )
            )
            for user in authors_with_posts:
                posts_count = Post.objects.filter(author=user).count()
                profile = user.profile
                status = "[+] УЖЕ АВТОР" if profile.is_author else "[-] НЕ АВТОР"
                self.stdout.write(
                    f'  - {user.username} ({posts_count} статей) - {status}'
                )
            self.stdout.write(
                self.style.WARNING(
                    '\nЗапустите команду без --dry-run для применения изменений'
                )
            )
        else:
            updated = 0
            already_authors = 0
            
            for user in authors_with_posts:
                profile = user.profile
                posts_count = Post.objects.filter(author=user).count()
                
                if not profile.is_author:
                    profile.is_author = True
                    profile.save()
                    updated += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'[+] {user.username} теперь автор ({posts_count} статей)'
                        )
                    )
                else:
                    already_authors += 1
                    self.stdout.write(
                        f'  {user.username} уже был автором ({posts_count} статей)'
                    )
            
            self.stdout.write('')
            self.stdout.write(
                self.style.SUCCESS(
                    f'ИТОГО: Обновлено {updated} пользователей, '
                    f'{already_authors} уже были авторами'
                )
            )
            
            if updated > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        'Все пользователи со статьями теперь имеют статус "Автор"!'
                    )
                )

