"""
Статистика SEO-оптимизации
"""
from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from blog.models import Post
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = 'Показывает статистику SEO-оптимизации статей'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('>>> СТАТИСТИКА SEO-ОПТИМИЗАЦИИ <<<'))
        self.stdout.write(self.style.SUCCESS('='*80 + '\n'))
        
        # Общая статистика
        total_posts = Post.objects.filter(status='published').count()
        
        # Статьи с FAQ блоками
        with_faq = Post.objects.filter(
            status='published',
            content__icontains='faq-section'
        ).count()
        
        # Статьи с SEO метаданными
        with_meta = Post.objects.filter(
            status='published'
        ).exclude(meta_title='').exclude(meta_title__isnull=True).count()
        
        # Статьи с focus_keyword
        with_keywords = Post.objects.filter(
            status='published'
        ).exclude(focus_keyword='').exclude(focus_keyword__isnull=True).count()
        
        # Новые статьи (за последние 7 дней)
        recent_posts = Post.objects.filter(
            status='published',
            created__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        # Старые статьи (старше 6 месяцев)
        old_posts = Post.objects.filter(
            status='published',
            created__lt=timezone.now() - timedelta(days=180)
        ).count()
        
        # Популярные старые статьи (кандидаты на обновление)
        popular_old = Post.objects.filter(
            status='published',
            created__lt=timezone.now() - timedelta(days=180),
            views__gt=500
        ).count()
        
        # Вывод статистики
        self.stdout.write('ОБЩАЯ СТАТИСТИКА:')
        self.stdout.write(f'   * Всего опубликованных статей: {total_posts}')
        self.stdout.write(f'   * Новые статьи (7 дней): {recent_posts}')
        self.stdout.write(f'   * Старые статьи (>6 мес): {old_posts}\n')
        
        self.stdout.write('SEO-ОПТИМИЗАЦИЯ:')
        self.stdout.write(f'   * С FAQ блоками: {with_faq} ({with_faq/total_posts*100:.1f}%)')
        self.stdout.write(f'   * С meta_title: {with_meta} ({with_meta/total_posts*100:.1f}%)')
        self.stdout.write(f'   * С focus_keyword: {with_keywords} ({with_keywords/total_posts*100:.1f}%)\n')
        
        self.stdout.write('ПОТЕНЦИАЛ:')
        self.stdout.write(f'   * Без FAQ блоков: {total_posts - with_faq} статей')
        self.stdout.write(f'   * Популярных старых для обновления: {popular_old} статей\n')
        
        # Рекомендации
        self.stdout.write('='*80)
        self.stdout.write('РЕКОМЕНДАЦИИ:\n')
        
        if total_posts - with_faq > 0:
            self.stdout.write(self.style.WARNING(
                f'   [!] Добавьте FAQ к оставшимся {total_posts - with_faq} статьям:'
            ))
            self.stdout.write('       python manage.py seo_boost --mode=faq\n')
        
        if popular_old > 0:
            self.stdout.write(self.style.WARNING(
                f'   [!] Обновите {popular_old} популярных старых статей:'
            ))
            self.stdout.write('       python manage.py seo_boost --mode=refresh\n')
        
        if total_posts - with_meta > 0:
            self.stdout.write(self.style.WARNING(
                f'   [!] {total_posts - with_meta} статей без SEO метаданных'
            ))
            self.stdout.write('       (добавятся автоматически при следующей публикации)\n')
        
        self.stdout.write('='*80 + '\n')

