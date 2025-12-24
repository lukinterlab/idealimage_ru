"""
Команда для реорганизации категорий блога
Объединяет старые категории в новые логические группы
Сохраняет старые названия в виде тегов
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from blog.models import Category, Post
from django.utils.text import slugify
from unidecode import unidecode


class Command(BaseCommand):
    help = 'Реорганизация категорий блога: объединение категорий и добавление тегов'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Режим проверки без внесения изменений в БД',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('=' * 70))
            self.stdout.write(self.style.WARNING('РЕЖИМ ПРОВЕРКИ (DRY-RUN) - изменения НЕ будут сохранены'))
            self.stdout.write(self.style.WARNING('=' * 70))
        else:
            self.stdout.write(self.style.SUCCESS('=' * 70))
            self.stdout.write(self.style.SUCCESS('РЕЖИМ ВЫПОЛНЕНИЯ - изменения будут сохранены в БД'))
            self.stdout.write(self.style.SUCCESS('=' * 70))
        
        self.stdout.write('')
        
        # Определяем схему реорганизации
        # Формат: 'Новая категория': (['старая1', 'старая2'], добавлять_теги_для_всех)
        reorganization_plan = {
            'Предсказания': (
                ['Матрица СУДЬБЫ', 'СТУДЕНЧЕСКАЯ МАГИЯ', 'ТАРО КАРТЫ В ЖИЗНИ', 'Гороскопы'],
                True  # Добавлять теги для всех (название изменилось)
            ),
            'Малыши и Мамы': (
                ['Я - МАМОЧКА', 'ЛАПОЧКИ-МАЛЫШКИ'],
                True  # Добавлять теги для всех (название изменилось)
            ),
            'ПСИХОЛОГИЯ': (
                ['NLP', 'ПСИХОЛОГИЯ'],
                False  # Добавлять теги только для изменившихся (NLP)
            ),
            'ЕШЬ ЛЮБИ МОЛИСЬ': (
                ['ЕШЬ ЛЮБИ МОЛИСЬ', 'ЛАКОМКА'],
                False  # Добавлять теги только для изменившихся (ЛАКОМКА)
            ),
        }
        
        # Статистика
        stats = {
            'categories_created': 0,
            'posts_moved': 0,
            'tags_added': 0,
            'categories_deleted': 0,
            'errors': 0,
        }
        
        try:
            if not dry_run:
                transaction.set_autocommit(False)
            
            # Обрабатываем каждую группу
            for new_category_name, (old_category_names, tag_all) in reorganization_plan.items():
                self.stdout.write(self.style.HTTP_INFO(f'\n📁 Группа: {new_category_name}'))
                self.stdout.write('-' * 70)
                
                # Находим или создаем новую категорию
                new_category = self._get_or_create_category(new_category_name, dry_run)
                if new_category == 'CREATED':
                    stats['categories_created'] += 1
                    self.stdout.write(self.style.SUCCESS(f'   ✅ Создана новая категория: {new_category_name}'))
                elif new_category == 'EXISTS':
                    self.stdout.write(f'   ℹ️  Категория уже существует: {new_category_name}')
                else:
                    if not dry_run:
                        new_category_obj = new_category
                    else:
                        new_category_obj = None
                
                # Обрабатываем старые категории
                for old_category_name in old_category_names:
                    result = self._process_old_category(
                        old_category_name,
                        new_category_name,
                        new_category_obj if not dry_run else None,
                        tag_all,
                        dry_run
                    )
                    
                    stats['posts_moved'] += result['posts_moved']
                    stats['tags_added'] += result['tags_added']
                    if result['category_deleted']:
                        stats['categories_deleted'] += 1
                    stats['errors'] += result['errors']
            
            # Выводим итоговую статистику
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('=' * 70))
            self.stdout.write(self.style.SUCCESS('СТАТИСТИКА ОПЕРАЦИЙ'))
            self.stdout.write(self.style.SUCCESS('=' * 70))
            self.stdout.write(f'📊 Создано новых категорий: {stats["categories_created"]}')
            self.stdout.write(f'📝 Перемещено статей: {stats["posts_moved"]}')
            self.stdout.write(f'🏷️  Добавлено тегов: {stats["tags_added"]}')
            self.stdout.write(f'🗑️  Удалено пустых категорий: {stats["categories_deleted"]}')
            if stats['errors'] > 0:
                self.stdout.write(self.style.ERROR(f'❌ Ошибок: {stats["errors"]}'))
            
            if dry_run:
                self.stdout.write('')
                self.stdout.write(self.style.WARNING('⚠️  Это был режим проверки. Для реального выполнения запустите:'))
                self.stdout.write(self.style.WARNING('   python manage.py reorganize_categories'))
            else:
                transaction.commit()
                self.stdout.write('')
                self.stdout.write(self.style.SUCCESS('✅ Миграция категорий успешно завершена!'))
                self.stdout.write('')
                self.stdout.write('💡 Рекомендуется проверить:')
                self.stdout.write('   1. Админ-панель категорий')
                self.stdout.write('   2. Отображение статей на сайте')
                self.stdout.write('   3. Работу фильтров по категориям')
                self.stdout.write('   4. Теги в статьях')
        
        except Exception as e:
            if not dry_run:
                transaction.rollback()
            self.stdout.write(self.style.ERROR(f'\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}'))
            self.stdout.write(self.style.ERROR('Все изменения отменены'))
            raise
        finally:
            if not dry_run:
                transaction.set_autocommit(True)
    
    def _get_or_create_category(self, category_name, dry_run):
        """Находит или создает категорию (case-insensitive поиск)"""
        # Ищем категорию без учета регистра
        category = Category.objects.filter(title__iexact=category_name).first()
        
        if category:
            return 'EXISTS' if dry_run else category
        else:
            if dry_run:
                return 'CREATED'
            else:
                # Создаем новую категорию
                category = Category.objects.create(
                    title=category_name,
                    slug=self._generate_slug(category_name)
                )
                return category
    
    def _generate_slug(self, title):
        """Генерирует уникальный slug для категории"""
        base_slug = slugify(unidecode(title))
        slug = base_slug
        counter = 1
        
        while Category.objects.filter(slug=slug).exists():
            slug = f'{base_slug}-{counter}'
            counter += 1
        
        return slug
    
    def _process_old_category(self, old_name, new_name, new_category_obj, tag_all, dry_run):
        """Обрабатывает одну старую категорию"""
        result = {
            'posts_moved': 0,
            'tags_added': 0,
            'category_deleted': False,
            'errors': 0,
        }
        
        # Ищем старую категорию без учета регистра
        old_category = Category.objects.filter(title__iexact=old_name).first()
        
        if not old_category:
            self.stdout.write(self.style.WARNING(f'   ⚠️  Категория "{old_name}" не найдена - пропускаем'))
            return result
        
        # Получаем статьи из старой категории
        posts = Post.objects.filter(category=old_category)
        posts_count = posts.count()
        
        self.stdout.write(f'\n   📂 Обработка категории: {old_category.title}')
        self.stdout.write(f'      Найдено статей: {posts_count}')
        
        if posts_count == 0:
            self.stdout.write(f'      ℹ️  Категория пуста')
            if not dry_run:
                old_category.delete()
                result['category_deleted'] = True
                self.stdout.write(self.style.SUCCESS(f'      ✅ Пустая категория удалена'))
            return result
        
        # Определяем, нужно ли добавлять тег
        # Добавляем тег если:
        # 1. tag_all=True (название категории изменилось для всех статей в группе)
        # 2. tag_all=False И старое название != новое название
        should_add_tag = tag_all or (old_category.title != new_name)
        
        # Обрабатываем каждую статью
        for post in posts:
            try:
                # Перемещаем в новую категорию
                if not dry_run:
                    post.category = new_category_obj
                
                # Добавляем тег со старым названием категории (если нужно)
                if should_add_tag:
                    if not dry_run:
                        post.tags.add(old_category.title)
                    result['tags_added'] += 1
                
                if not dry_run:
                    post.save()
                
                result['posts_moved'] += 1
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'      ❌ Ошибка при обработке статьи #{post.id}: {e}'))
                result['errors'] += 1
        
        self.stdout.write(self.style.SUCCESS(f'      ✅ Перемещено статей: {result["posts_moved"]}'))
        if should_add_tag:
            self.stdout.write(f'      🏷️  Добавлено тегов: {result["tags_added"]}')
        else:
            self.stdout.write(f'      ℹ️  Теги не добавлялись (название категории не изменилось)')
        
        # Удаляем старую категорию (если она теперь пуста и отличается от новой)
        if not dry_run and old_category.title != new_name:
            # Проверяем что категория действительно пуста
            if Post.objects.filter(category=old_category).count() == 0:
                old_category.delete()
                result['category_deleted'] = True
                self.stdout.write(self.style.SUCCESS(f'      ✅ Старая категория удалена'))
        
        return result

