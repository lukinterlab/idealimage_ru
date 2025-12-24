"""
Management команда для генерации SEO мета-тегов для существующих статей
"""
from django.core.management.base import BaseCommand
from django.db.models import Q
from blog.models import Post, Category
from utilits.seo_utils import generate_meta_description
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Генерирует SEO мета-теги для статей которые их не имеют'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Обновить ВСЕ статьи (даже те у которых уже есть мета-теги)',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Ограничить количество обрабатываемых статей',
        )
        parser.add_argument(
            '--category',
            type=str,
            help='Обработать только статьи из указанной категории (slug)',
        )

    @staticmethod
    def _smart_trim(text: str, length: int) -> str:
        if len(text) <= length:
            return text
        trimmed = text[:length].rstrip(' ,.-—:')
        return trimmed if trimmed else text[:length]

    @staticmethod
    def _safe_console_text(value: str) -> str:
        if not value:
            return ''
        return value.encode('cp1251', errors='ignore').decode('cp1251', errors='ignore')

    def _build_meta_title(self, post) -> str:
        title = (post.title or '').strip()
        if not title:
            return ''

        category_title = (post.category.title if getattr(post, 'category', None) else '').strip()
        category_key = category_title.upper()
        lower_title = title.lower()

        brand_suffix = ' | IdealImage.ru'
        max_length = 60

        base = title

        if category_key == 'ПСИХОЛОГИЯ':
            if any(token in lower_title for token in ['таро', 'кубк', 'жезл', 'меч']):
                base = f'{title} — значение и сочетания Таро'
            elif 'нлп' in lower_title or 'nlp' in lower_title:
                base = f'{title}: техники и упражнения'
            else:
                base = f'{title} — психология и практики'
        elif category_key == 'МАЛЫШИ И МАМЫ':
            if any(token in lower_title for token in ['кос', 'пуч', 'прич']):
                base = f'{title}: как сделать прическу'
            elif 'плач' in lower_title:
                base = f'{title}: советы для родителей'
            else:
                base = f'{title}: идеи для мам и малышей'
        elif category_key == 'ИДЕАЛЬНЫЙ ОБРАЗ':
            base = f'{title}: стиль и вдохновение'
        elif category_key == 'FASHION COUTURE':
            base = f'{title}: тренды сезона'
        elif category_key == 'ЕШЬ ЛЮБИ МОЛИСЬ':
            base = f'{title}: рецепт и лайфхаки'
        elif category_key == 'LUKINTERLAB':
            base = f'{title} — проекты и обновления'
        else:
            base = f'{title} — блог IdealImage'

        if len(base) + len(brand_suffix) <= max_length:
            return base + brand_suffix

        return self._smart_trim(base, max_length)

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Начинаем генерацию SEO мета-тегов...')
        )

        posts = Post.objects.filter(status='published')

        if options['category']:
            try:
                category = Category.objects.get(slug=options['category'])
                posts = posts.filter(category=category)
                self.stdout.write(
                    self.style.WARNING(f'Обрабатываем категорию: {category.title}')
                )
            except Category.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Категория {options["category"]} не найдена!')
                )
                return

        if not options['all']:
            posts = posts.filter(
                Q(meta_title='') | Q(meta_description='')
            )

        if options['limit']:
            posts = posts[:options['limit']]

        total = posts.count()

        if total == 0:
            self.stdout.write(
                self.style.SUCCESS('Все статьи уже имеют SEO мета-теги.')
            )
            return

        self.stdout.write(
            self.style.WARNING(f'Найдено статей для обработки: {total}')
        )

        updated_count = 0
        errors_count = 0

        for i, post in enumerate(posts, 1):
            try:
                updated = False

                if not post.meta_title or options['all']:
                    new_meta_title = self._build_meta_title(post)
                    if new_meta_title:
                        post.meta_title = new_meta_title
                        updated = True

                if not post.meta_description or options['all']:
                    post.meta_description = generate_meta_description(
                        post.description or post.content,
                        max_length=160,
                        post=post
                    )
                    updated = True

                if not post.focus_keyword or options['all']:
                    if post.tags.exists():
                        post.focus_keyword = post.tags.first().name
                    elif getattr(post, 'category', None):
                        post.focus_keyword = post.category.title
                    updated = True

                if not post.og_title or options['all']:
                    post.og_title = post.meta_title
                    updated = True

                if not post.og_description or options['all']:
                    post.og_description = post.meta_description
                    updated = True

                if updated:
                    post.save()
                    updated_count += 1

                    self.stdout.write(
                        self.style.SUCCESS(
                            f'[{i}/{total}] Обновлена: {self._safe_console_text(post.title)[:50]}...'
                        )
                    )

            except Exception as e:
                errors_count += 1
                logger.error(f'Ошибка при обработке статьи {post.id}: {e}')
                self.stdout.write(
                    self.style.ERROR(
                        f'[{i}/{total}] Ошибка: {self._safe_console_text(post.title)[:50]}... - {self._safe_console_text(str(e))}'
                    )
                )

        cache.clear()

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('Обработка завершена.'))
        self.stdout.write(f'Обработано статей: {total}')
        self.stdout.write(self.style.SUCCESS(f'Успешно обновлено: {updated_count}'))

        if errors_count > 0:
            self.stdout.write(self.style.ERROR(f'Ошибок: {errors_count}'))

        self.stdout.write('=' * 60)

        self.stdout.write('\nРекомендации:')
        self.stdout.write('1. Проверьте сгенерированные мета-теги в админке')
        self.stdout.write('2. Отредактируйте их вручную для важных статей')
        self.stdout.write('3. Запустите python manage.py generate_sitemap для обновления sitemap.xml')
        self.stdout.write('4. Проверьте статьи в Google Search Console\n')


        # Очищаем кэш после обновления
        cache.clear()
        
        # Итоговая статистика
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('Обработка завершена.'))
        self.stdout.write(f'Обработано статей: {total}')
        self.stdout.write(self.style.SUCCESS(f'Успешно обновлено: {updated_count}'))
        
        if errors_count > 0:
            self.stdout.write(self.style.ERROR(f'Ошибок: {errors_count}'))
        
        self.stdout.write('=' * 60)
        
        # Рекомендации
        self.stdout.write('\nРекомендации:')
        self.stdout.write('1. Проверьте сгенерированные мета-теги в админке')
        self.stdout.write('2. Отредактируйте их вручную для важных статей')
        self.stdout.write('3. Запустите python manage.py generate_sitemap для обновления sitemap.xml')
        self.stdout.write('4. Проверьте статьи в Google Search Console\n')


