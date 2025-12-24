"""
Management команда для переноса статей из категории "ТАРО КАРТЫ В ЖИЗНИ." (ID=18)
в категорию "Интеллектуальные Прогнозы" (ID=37) с добавлением тега "ТАРО КАРТЫ В ЖИЗНИ"
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from blog.models import Post, Category
from taggit.models import Tag


class Command(BaseCommand):
    help = 'Переносит статьи из "ТАРО КАРТЫ В ЖИЗНИ" в "Интеллектуальные Прогнозы" с тегом'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать изменения без применения',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Жестко закодированные параметры
        FROM_ID = 18  # ТАРО КАРТЫ В ЖИЗНИ.
        TO_ID = 37    # Интеллектуальные Прогнозы
        TAG_NAME = "ТАРО КАРТЫ В ЖИЗНИ"
        
        self.stdout.write(self.style.WARNING('=' * 80))
        self.stdout.write(self.style.WARNING('МИГРАЦИЯ КАТЕГОРИИ "ТАРО КАРТЫ В ЖИЗНИ"'))
        self.stdout.write(self.style.WARNING('=' * 80))
        
        # Проверяем существование категорий
        try:
            old_category = Category.objects.get(id=FROM_ID)
            self.stdout.write(f'[OK] Старая категория найдена: "{old_category.title}" (ID={old_category.id})')
        except Category.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'[ОШИБКА] Категория с ID={FROM_ID} не найдена!'))
            return
        
        try:
            new_category = Category.objects.get(id=TO_ID)
            self.stdout.write(f'[OK] Новая категория найдена: "{new_category.title}" (ID={new_category.id})')
        except Category.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'[ОШИБКА] Категория с ID={TO_ID} не найдена!'))
            return
        
        # Получаем статьи из старой категории
        posts = Post.objects.filter(category_id=FROM_ID)
        posts_count = posts.count()
        
        if posts_count == 0:
            self.stdout.write(self.style.WARNING(f'В категории "{old_category.title}" нет статей'))
            return
        
        self.stdout.write(f'\nНайдено статей для переноса: {posts_count}')
        self.stdout.write('-' * 80)
        
        # Выводим список ID статей
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
            self.stdout.write(f'  - Из категории: "{old_category.title}" (ID={FROM_ID})')
            self.stdout.write(f'  - В категорию: "{new_category.title}" (ID={TO_ID})')
            self.stdout.write(f'  - Добавление тега: [имя тега]')
            return
        
        # Подтверждение перед выполнением
        self.stdout.write(self.style.WARNING(f'\n[ВНИМАНИЕ] Будет выполнено:'))
        self.stdout.write(f'  - Перенос {posts_count} статей')
        self.stdout.write(f'  - Из категории: "{old_category.title}" (ID={FROM_ID})')
        self.stdout.write(f'  - В категорию: "{new_category.title}" (ID={TO_ID})')
        self.stdout.write(f'  - Добавление тега: [имя тега]')
        
        # Выполняем миграцию в транзакции
        try:
            with transaction.atomic():
                # Получаем или создаём тег
                tag, tag_created = Tag.objects.get_or_create(name=TAG_NAME)
                if tag_created:
                    self.stdout.write(self.style.SUCCESS(f'\n[OK] Создан новый тег'))
                else:
                    self.stdout.write(f'\n[OK] Используется существующий тег')
                
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

