"""
🚀 КОМАНДА МАССОВОГО SEO-УСИЛЕНИЯ
Применяет все SEO-оптимизации ко всем статьям
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from blog.models import Post
from Asistent.seo_advanced import AdvancedSEOOptimizer, ZODIAC_SIGNS
import logging
import re

logger = logging.getLogger(__name__)


def remove_emojis(text):
    """Удаляет эмодзи из текста для совместимости с Windows console"""
    # Паттерн для поиска эмодзи
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # смайлики
        "\U0001F300-\U0001F5FF"  # символы и пиктограммы
        "\U0001F680-\U0001F6FF"  # транспорт и символы карт
        "\U0001F1E0-\U0001F1FF"  # флаги
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+", 
        flags=re.UNICODE
    )
    return emoji_pattern.sub(r'', text)


# =============================================================================
# КЛАСС КОМАНДЫ
# =============================================================================
class Command(BaseCommand):
    help = 'Массовая SEO-оптимизация всех статей: FAQ, внутренние ссылки, alt-теги, обновление старых'
    
    # =============================================================================
    # ДОБАВЛЕНИЕ АРГУМЕНТОВ
    # =============================================================================
    def add_arguments(self, parser):
        parser.add_argument(
            '--mode',
            type=str,
            default='all',
            choices=['all', 'faq', 'links', 'images', 'refresh', 'submit'],
            help='Режим оптимизации: all (всё), faq (только FAQ), links (внутренние ссылки), images (alt-теги), refresh (обновление старых), submit (отправка в поисковики)'
        )
        
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Ограничить количество обрабатываемых статей (для тестирования)'
        )
        
        parser.add_argument(
            '--old-days',
            type=int,
            default=180,
            help='Статьи старше N дней считаются "старыми" для обновления (по умолчанию 180 дней)'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Тестовый запуск без сохранения изменений'
        )
    
    def handle(self, *args, **options):
        mode = options['mode']
        limit = options['limit']
        old_days = options['old_days']
        dry_run = options['dry_run']
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('>>> МАССОВАЯ SEO-ОПТИМИЗАЦИЯ ЗАПУЩЕНА <<<'))
        self.stdout.write(self.style.SUCCESS('='*80 + '\n'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('!!! ТЕСТОВЫЙ РЕЖИМ (изменения не сохраняются)\n'))
        
        optimizer = AdvancedSEOOptimizer()
        
        # Получаем статьи
        posts = Post.objects.filter(status='published').order_by('-created')
        
        if limit:
            posts = posts[:limit]
            self.stdout.write(f'Обрабатываем {limit} последних статей\n')
        else:
            self.stdout.write(f'Обрабатываем ВСЕ статьи ({posts.count()} шт.)\n')
        
        stats = {
            'total': posts.count(),
            'faq_added': 0,
            'links_added': 0,
            'images_optimized': 0,
            'articles_refreshed': 0,
            'submitted': 0,
            'errors': 0
        }
        
        # Выполняем оптимизацию
        for i, post in enumerate(posts, 1):
            # Убираем эмодзи из названия для Windows консоли
            clean_title = remove_emojis(post.title)
            self.stdout.write(f'\n[{i}/{stats["total"]}] {clean_title}')
            self.stdout.write(f'   URL: {post.get_absolute_url()}')
            
            try:
                # 1. FAQ блоки
                if mode in ['all', 'faq']:
                    if not self._has_faq_block(post.content):
                        self.stdout.write('   [FAQ] Генерация FAQ блока...')
                        sign_guess = next((z for z in ZODIAC_SIGNS if z.lower() in post.title.lower()), None)
                        faq_context = {'zodiac_sign': sign_guess} if sign_guess else None
                        faq_result = optimizer.generate_faq_block(post, context=faq_context)
                        
                        if faq_result['success'] and faq_result['questions']:
                            if not dry_run:
                                # Добавляем FAQ в конец статьи
                                post.content += '\n\n' + faq_result['html']
                                post.save()
                            
                            stats['faq_added'] += 1
                            self.stdout.write(self.style.SUCCESS(f'   [OK] FAQ: {faq_result["count"]} вопросов'))
                        else:
                            self.stdout.write(self.style.WARNING(f'   [WARN] FAQ не сгенерирован'))
                    else:
                        self.stdout.write('   [INFO] FAQ уже есть')
                
                # 2. Внутренние ссылки
                if mode in ['all', 'links']:
                    current_links_count = post.content.count('<a ')
                    if current_links_count < 3:
                        self.stdout.write(f'   [LINKS] Генерация внутренних ссылок (текущих: {current_links_count})...')
                        links_result = optimizer.generate_internal_links(post, post.content, target_count=5)
                        
                        if links_result['success'] and links_result['suggestions']:
                            self.stdout.write(self.style.SUCCESS(f'   [OK] Ссылки: {links_result["count"]} предложений'))
                            
                            for suggestion in links_result['suggestions']:
                                self.stdout.write(f'      -> "{suggestion["anchor_text"]}" -> {suggestion["article_title"]}')
                            
                            stats['links_added'] += links_result['count']
                        else:
                            self.stdout.write(self.style.WARNING(f'   [WARN] Ссылки не сгенерированы'))
                    else:
                        self.stdout.write(f'   [INFO] Уже есть {current_links_count} ссылок')
                
                # 3. Оптимизация изображений (alt/title)
                if mode in ['all', 'images']:
                    self.stdout.write('   [IMG] Оптимизация alt-тегов изображений...')
                    images_result = optimizer.optimize_images_alt_tags(post, post.content)
                    
                    if images_result['modified']:
                        if not dry_run:
                            post.content = images_result['optimized_content']
                            post.save()
                        
                        self.stdout.write(self.style.SUCCESS(
                            f'   [OK] Изображения: {images_result["optimized_count"]}/{images_result["images_count"]} оптимизировано'
                        ))
                        stats['images_optimized'] += images_result['optimized_count']
                    else:
                        self.stdout.write('   [INFO] Alt-теги в порядке')
                
                # 4. Обновление старых статей
                if mode in ['all', 'refresh']:
                    article_age = (timezone.now() - post.created).days
                    if article_age > old_days:
                        self.stdout.write(f'   [REFRESH] Статья старая ({article_age} дней), обновляем...')
                        refresh_result = optimizer.refresh_old_article(post)
                        
                        if refresh_result['success']:
                            if not dry_run:
                                # Добавляем новые разделы в конец
                                post.content += '\n\n' + refresh_result['new_sections']
                                post.title = refresh_result['updated_title']
                                post.updated = timezone.now()
                                post.save()
                            
                            self.stdout.write(self.style.SUCCESS('   [OK] Статья обновлена актуальной информацией'))
                            stats['articles_refreshed'] += 1
                        else:
                            self.stdout.write(self.style.WARNING('   [WARN] Обновление не удалось'))
                    else:
                        self.stdout.write(f'   [INFO] Статья свежая ({article_age} дней)')
                
                # 5. Отправка в поисковые системы
                if mode in ['all', 'submit']:
                    self.stdout.write('   [SUBMIT] Отправка в поисковики...')
                    submit_result = optimizer.submit_to_search_engines(post)
                    
                    if submit_result['yandex']['success']:
                        self.stdout.write(self.style.SUCCESS('   [OK] Яндекс: отправлено'))
                        stats['submitted'] += 1
                    else:
                        self.stdout.write('   [WARN] Яндекс: ошибка')
                
            except Exception as e:
                stats['errors'] += 1
                self.stdout.write(self.style.ERROR(f'   [ERROR] Ошибка: {e}'))
                logger.error(f"Ошибка обработки {post.id}: {e}")
        
        # Финальная статистика
        self.stdout.write('\n' + '='*80)
        self.stdout.write(self.style.SUCCESS('>>> ОПТИМИЗАЦИЯ ЗАВЕРШЕНА <<<'))
        self.stdout.write('='*80)
        self.stdout.write(f'\nСТАТИСТИКА:')
        self.stdout.write(f'   * Всего обработано: {stats["total"]} статей')
        self.stdout.write(f'   * FAQ блоков добавлено: {stats["faq_added"]}')
        self.stdout.write(f'   * Внутренних ссылок предложено: {stats["links_added"]}')
        self.stdout.write(f'   * Изображений оптимизировано: {stats["images_optimized"]}')
        self.stdout.write(f'   * Старых статей обновлено: {stats["articles_refreshed"]}')
        self.stdout.write(f'   * Отправлено в поисковики: {stats["submitted"]}')
        self.stdout.write(f'   * Ошибок: {stats["errors"]}\n')
        
        # Отправляем sitemap в поисковики
        if mode in ['all', 'submit']:
            self.stdout.write('\n[SITEMAP] Отправка sitemap в поисковые системы...')
            sitemap_result = optimizer.submit_sitemap_to_search_engines()
            
            if sitemap_result.get('yandex', {}).get('success'):
                self.stdout.write(self.style.SUCCESS('   [OK] Яндекс: sitemap отправлен'))
            
            if sitemap_result.get('google', {}).get('success'):
                self.stdout.write(self.style.SUCCESS('   [OK] Google: sitemap отправлен'))
        
        self.stdout.write('\n' + '='*80 + '\n')
    
    def _has_faq_block(self, content: str) -> bool:
        """Проверяет есть ли уже FAQ блок в статье"""
        return 'faq-section' in content.lower() or 'часто задаваемые вопросы' in content.lower()

