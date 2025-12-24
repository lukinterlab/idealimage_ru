"""
Management команда для переноса статей из категории "БЕЗУПРЕЧНЫЙ МЕЙК" (ID=20)
в категорию "ИДЕАЛЬНЫЙ ОБРАЗ" (ID=2) и добавления тега "Безупречный Мейк"
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from blog.models import Post, Category
from taggit.models import Tag


class Command(BaseCommand):
    help = 'Переносит статьи из категории "БЕЗУПРЕЧНЫЙ МЕЙК" (ID=20) в "ИДЕАЛЬНЫЙ ОБРАЗ" (ID=2) и добавляет тег'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать изменения без применения',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # ID категорий
        OLD_CATEGORY_ID = 20  # БЕЗУПРЕЧНЫЙ МЕЙК
        NEW_CATEGORY_ID = 2   # ИДЕАЛЬНЫЙ ОБРАЗ
        TAG_NAME = "Безупречный Мейк"
        
        self.stdout.write(self.style.WARNING('=' * 80))
        self.stdout.write(self.style.WARNING('МИГРАЦИЯ СТАТЕЙ ИЗ КАТЕГОРИИ'))
        self.stdout.write(self.style.WARNING('=' * 80))
        
        # Проверяем существование категорий
        try:
            old_category = Category.objects.get(id=OLD_CATEGORY_ID)
            self.stdout.write(f'[OK] Старая категория найдена: "{old_category.title}" (ID={old_category.id})')
        except Category.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'[ОШИБКА] Категория с ID={OLD_CATEGORY_ID} не найдена!'))
            return
        
        try:
            new_category = Category.objects.get(id=NEW_CATEGORY_ID)
            self.stdout.write(f'[OK] Новая категория найдена: "{new_category.title}" (ID={new_category.id})')
        except Category.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'[ОШИБКА] Категория с ID={NEW_CATEGORY_ID} не найдена!'))
            return
        
        # Получаем статьи из старой категории
        posts = Post.objects.filter(category_id=OLD_CATEGORY_ID)
        posts_count = posts.count()
        
        if posts_count == 0:
            self.stdout.write(self.style.WARNING(f'В категории "{old_category.title}" нет статей'))
            return
        
        self.stdout.write(f'\nНайдено статей для переноса: {posts_count}')
        self.stdout.write('-' * 80)
        
        # Выводим список статей
        for i, post in enumerate(posts, 1):
            self.stdout.write(f'{i}. "{post.title}" (ID={post.id}, slug={post.slug})')
        
        self.stdout.write('-' * 80)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n[ТЕСТ] Режим тестирования (--dry-run)'))
            self.stdout.write(self.style.WARNING('Изменения НЕ будут применены'))
            self.stdout.write(f'\nБудет выполнено:')
            self.stdout.write(f'  - Перенос {posts_count} статей')
            self.stdout.write(f'  - Из категории: "{old_category.title}" (ID={OLD_CATEGORY_ID})')
            self.stdout.write(f'  - В категорию: "{new_category.title}" (ID={NEW_CATEGORY_ID})')
            self.stdout.write(f'  - Добавление тега: "{TAG_NAME}"')
            return
        
        # Подтверждение перед выполнением
        self.stdout.write(self.style.WARNING(f'\n[ВНИМАНИЕ] Будет выполнено:'))
        self.stdout.write(f'  - Перенос {posts_count} статей')
        self.stdout.write(f'  - Из категории: "{old_category.title}" (ID={OLD_CATEGORY_ID})')
        self.stdout.write(f'  - В категорию: "{new_category.title}" (ID={NEW_CATEGORY_ID})')
        self.stdout.write(f'  - Добавление тега: "{TAG_NAME}"')
        
        # Выполняем миграцию в транзакции
        try:
            with transaction.atomic():
                # Получаем или создаём тег
                tag, tag_created = Tag.objects.get_or_create(name=TAG_NAME)
                if tag_created:
                    self.stdout.write(self.style.SUCCESS(f'\n[OK] Создан новый тег: "{TAG_NAME}"'))
                else:
                    self.stdout.write(f'\n[OK] Используется существующий тег: "{TAG_NAME}"')
                
                updated_count = 0
                tagged_count = 0
                
                for post in posts:
                    # Меняем категорию
                    post.category = new_category
                    post.save(update_fields=['category'])
                    updated_count += 1
                    
                    # Добавляем тег, если его еще нет
                    if not post.tags.filter(name=TAG_NAME).exists():
                        post.tags.add(tag)
                        tagged_count += 1
                
                self.stdout.write('-' * 80)
                self.stdout.write(self.style.SUCCESS(f'\n[УСПЕХ] УСПЕШНО ВЫПОЛНЕНО:'))
                self.stdout.write(self.style.SUCCESS(f'  - Перенесено статей: {updated_count}'))
                self.stdout.write(self.style.SUCCESS(f'  - Добавлен тег к статьям: {tagged_count}'))
                self.stdout.write(self.style.SUCCESS(f'  - Из категории: "{old_category.title}"'))
                self.stdout.write(self.style.SUCCESS(f'  - В категорию: "{new_category.title}"'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n[ОШИБКА] При выполнении миграции:'))
            self.stdout.write(self.style.ERROR(f'  {str(e)}'))
            raise
        
        self.stdout.write(self.style.WARNING('\n' + '=' * 80))

