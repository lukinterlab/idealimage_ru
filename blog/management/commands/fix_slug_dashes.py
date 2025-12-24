"""
Команда для исправления slug начинающихся с дефиса
Исправляет проблему: -zagolovok-a51dddbb -> zagolovok-a51dddbb
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from blog.models import Post, Category
from Visitor.models import Profile


class Command(BaseCommand):
    help = 'Исправляет slug начинающиеся с дефиса'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать что будет исправлено без сохранения',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 РЕЖИМ ПРОВЕРКИ (dry-run) - изменения не будут сохранены'))
        else:
            self.stdout.write(self.style.SUCCESS('🔧 РЕЖИМ ИСПРАВЛЕНИЯ - изменения будут сохранены'))
        
        self.stdout.write('')
        
        # Исправляем Post
        self.fix_model_slugs(Post, 'Статьи', dry_run)
        
        # Исправляем Category
        self.fix_model_slugs(Category, 'Категории', dry_run)
        
        # Исправляем Profile
        self.fix_model_slugs(Profile, 'Профили', dry_run)
        
        if dry_run:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('Для применения изменений запустите без --dry-run'))
        else:
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('✅ Все slug исправлены!'))

    def fix_model_slugs(self, model, model_name, dry_run):
        """Исправляет slug для модели"""
        self.stdout.write(f'📝 Проверка {model_name}...')
        
        # Находим все записи с slug начинающимся с дефиса
        bad_slugs = model.objects.filter(slug__startswith='-')
        
        count = bad_slugs.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS(f'  ✅ {model_name}: проблемных slug не найдено'))
            return
        
        self.stdout.write(self.style.WARNING(f'  ⚠️  Найдено проблемных slug: {count}'))
        
        fixed = 0
        errors = 0
        
        with transaction.atomic():
            for obj in bad_slugs:
                old_slug = obj.slug
                new_slug = old_slug.strip('-')
                
                # Если после обработки slug пустой, генерируем новый
                if not new_slug:
                    from utilits.utils import unique_slugify
                    if hasattr(obj, 'title'):
                        new_slug = unique_slugify(obj, obj.title)
                    elif hasattr(obj, 'psevdonim'):
                        new_slug = unique_slugify(obj, str(obj.psevdonim))
                    else:
                        from uuid import uuid4
                        new_slug = f'{model.__name__.lower()}-{uuid4().hex[:8]}'
                
                # Проверяем что новый slug уникален
                if model.objects.filter(slug=new_slug).exclude(pk=obj.pk).exists():
                    # Если не уникален, добавляем суффикс
                    from uuid import uuid4
                    new_slug = f'{new_slug}-{uuid4().hex[:8]}'
                
                if dry_run:
                    self.stdout.write(f'    📌 {old_slug} -> {new_slug}')
                else:
                    try:
                        obj.slug = new_slug
                        obj.save(update_fields=['slug'])
                        self.stdout.write(self.style.SUCCESS(f'    ✅ {old_slug} -> {new_slug}'))
                        fixed += 1
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'    ❌ Ошибка для {old_slug}: {e}'))
                        errors += 1
        
        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f'  ✅ Исправлено: {fixed}, Ошибок: {errors}'))

