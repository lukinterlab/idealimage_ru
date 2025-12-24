"""
Management команда для переименования тегов в статьях
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from blog.models import Post
from taggit.models import Tag


class Command(BaseCommand):
    help = 'Переименовывает теги в статьях'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать изменения без применения',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Список замен: (старый_тег, новый_тег)
        tag_replacements = [
            ('ТАРО КАРТЫ В ЖИЗНИ', 'ТАРО КАРТЫ'),
            ('младшие.арканы', 'младшие арканы'),
            ('старшие.арканы', 'старшие арканы'),
        ]
        
        self.stdout.write(self.style.WARNING('=' * 80))
        self.stdout.write(self.style.WARNING('ПЕРЕИМЕНОВАНИЕ ТЕГОВ В СТАТЬЯХ'))
        self.stdout.write(self.style.WARNING('=' * 80))
        
        total_updated = 0
        
        try:
            with transaction.atomic():
                for old_tag_name, new_tag_name in tag_replacements:
                    self.stdout.write(f'\n📋 Обработка тега: "{old_tag_name}" → "{new_tag_name}"')
                    
                    # Ищем старый тег
                    try:
                        old_tag = Tag.objects.get(name=old_tag_name)
                    except Tag.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f'  ⚠️ Тег "{old_tag_name}" не найден, пропускаем'))
                        continue
                    
                    # Получаем или создаем новый тег
                    new_tag, created = Tag.objects.get_or_create(name=new_tag_name)
                    if created:
                        self.stdout.write(self.style.SUCCESS(f'  ✅ Создан новый тег: "{new_tag_name}"'))
                    else:
                        self.stdout.write(f'  ℹ️ Используется существующий тег: "{new_tag_name}"')
                    
                    # Находим все статьи со старым тегом
                    posts = Post.objects.filter(tags=old_tag).distinct()
                    posts_count = posts.count()
                    
                    if posts_count == 0:
                        self.stdout.write(f'  ℹ️ Статей с тегом "{old_tag_name}" не найдено')
                        continue
                    
                    self.stdout.write(f'  📝 Найдено статей: {posts_count}')
                    
                    if dry_run:
                        self.stdout.write(self.style.WARNING(f'  🔍 [DRY RUN] Будет обновлено статей: {posts_count}'))
                        for post in posts[:5]:  # Показываем первые 5
                            self.stdout.write(f'    - {post.title}')
                        if posts_count > 5:
                            self.stdout.write(f'    ... и еще {posts_count - 5} статей')
                    else:
                        updated_count = 0
                        for post in posts:
                            # Удаляем старый тег
                            post.tags.remove(old_tag)
                            # Добавляем новый тег (если его еще нет)
                            if not post.tags.filter(name=new_tag_name).exists():
                                post.tags.add(new_tag)
                            updated_count += 1
                        
                        self.stdout.write(self.style.SUCCESS(f'  ✅ Обновлено статей: {updated_count}'))
                        total_updated += updated_count
                        
                        # Удаляем старый тег, если он больше не используется
                        remaining_posts = Post.objects.filter(tags=old_tag).count()
                        if remaining_posts == 0:
                            old_tag.delete()
                            self.stdout.write(self.style.SUCCESS(f'  🗑️ Удален неиспользуемый тег: "{old_tag_name}"'))
                
                if dry_run:
                    self.stdout.write(self.style.WARNING('\n' + '=' * 80))
                    self.stdout.write(self.style.WARNING('[DRY RUN] Изменения не применены'))
                    self.stdout.write(self.style.WARNING('Запустите без --dry-run для применения изменений'))
                else:
                    self.stdout.write('\n' + '=' * 80)
                    self.stdout.write(self.style.SUCCESS(f'[УСПЕХ] Всего обновлено статей: {total_updated}'))
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n[ОШИБКА] При выполнении операции:'))
            self.stdout.write(self.style.ERROR(f'  {str(e)}'))
            if not dry_run:
                raise
        
        self.stdout.write(self.style.WARNING('\n' + '=' * 80))

