"""
Management команда для переноса статей из одной категории в другую БЕЗ добавления тега
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from blog.models import Post, Category


class Command(BaseCommand):
    help = 'Переносит статьи из одной категории в другую без добавления тега'

    def add_arguments(self, parser):
        parser.add_argument(
            '--from-id',
            type=int,
            required=True,
            help='ID исходной категории',
        )
        parser.add_argument(
            '--to-id',
            type=int,
            required=True,
            help='ID целевой категории',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать изменения без применения',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        from_id = options['from_id']
        to_id = options['to_id']
        
        self.stdout.write(self.style.WARNING('=' * 80))
        self.stdout.write(self.style.WARNING('МИГРАЦИЯ СТАТЕЙ ИЗ КАТЕГОРИИ (БЕЗ ТЕГА)'))
        self.stdout.write(self.style.WARNING('=' * 80))
        
        # Проверяем существование категорий
        try:
            old_category = Category.objects.get(id=from_id)
            self.stdout.write(f'[OK] Старая категория найдена: "{old_category.title}" (ID={old_category.id})')
        except Category.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'[ОШИБКА] Категория с ID={from_id} не найдена!'))
            return
        
        try:
            new_category = Category.objects.get(id=to_id)
            self.stdout.write(f'[OK] Новая категория найдена: "{new_category.title}" (ID={new_category.id})')
        except Category.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'[ОШИБКА] Категория с ID={to_id} не найдена!'))
            return
        
        # Получаем статьи из старой категории
        posts = Post.objects.filter(category_id=from_id)
        posts_count = posts.count()
        
        if posts_count == 0:
            self.stdout.write(self.style.WARNING(f'В категории "{old_category.title}" нет статей'))
            return
        
        self.stdout.write(f'\nНайдено статей для переноса: {posts_count}')
        self.stdout.write('-' * 80)
        
        # Выводим список статей (только ID, чтобы избежать проблем с кодировкой)
        self.stdout.write('Список ID статей:')
        ids = [str(post.id) for post in posts]
        self.stdout.write(', '.join(ids[:20]))
        if posts_count > 20:
            self.stdout.write(f'... и еще {posts_count - 20} статей')
        
        self.stdout.write('-' * 80)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n[ТЕСТ] Режим тестирования (--dry-run)'))
            self.stdout.write(self.style.WARNING('Изменения НЕ будут применены'))
            self.stdout.write(f'\nБудет выполнено:')
            self.stdout.write(f'  - Перенос {posts_count} статей')
            self.stdout.write(f'  - Из категории: "{old_category.title}" (ID={from_id})')
            self.stdout.write(f'  - В категорию: "{new_category.title}" (ID={to_id})')
            return
        
        # Подтверждение перед выполнением
        self.stdout.write(self.style.WARNING(f'\n[ВНИМАНИЕ] Будет выполнено:'))
        self.stdout.write(f'  - Перенос {posts_count} статей')
        self.stdout.write(f'  - Из категории: "{old_category.title}" (ID={from_id})')
        self.stdout.write(f'  - В категорию: "{new_category.title}" (ID={to_id})')
        
        # Выполняем миграцию в транзакции
        try:
            with transaction.atomic():
                updated_count = 0
                
                for post in posts:
                    # Меняем категорию
                    post.category = new_category
                    post.save(update_fields=['category'])
                    updated_count += 1
                
                self.stdout.write('-' * 80)
                self.stdout.write(self.style.SUCCESS(f'\n[УСПЕХ] УСПЕШНО ВЫПОЛНЕНО:'))
                self.stdout.write(self.style.SUCCESS(f'  - Перенесено статей: {updated_count}'))
                self.stdout.write(self.style.SUCCESS(f'  - Из категории: "{old_category.title}"'))
                self.stdout.write(self.style.SUCCESS(f'  - В категорию: "{new_category.title}"'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n[ОШИБКА] При выполнении миграции:'))
            self.stdout.write(self.style.ERROR(f'  {str(e)}'))
            raise
        
        self.stdout.write(self.style.WARNING('\n' + '=' * 80))

