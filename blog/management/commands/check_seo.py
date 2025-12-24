"""
Команда для ручной проверки SEO здоровья сайта
"""
from django.core.management.base import BaseCommand
from Asistent.seo_monitor import SEO404Monitor
import json


class Command(BaseCommand):
    help = 'Ручная проверка SEO здоровья сайта (404 ошибки, битые ссылки, дубли URL)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Автоматически исправить найденные проблемы'
        )
        parser.add_argument(
            '--json',
            action='store_true',
            help='Вывести результат в формате JSON'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('[SEO] Запуск мониторинга...'))
        self.stdout.write('')
        
        monitor = SEO404Monitor()
        results = monitor.run_full_check()
        
        if options['json']:
            # Конвертируем datetime в строку для JSON
            results['timestamp'] = results['timestamp'].isoformat()
            self.stdout.write(json.dumps(results, indent=2, ensure_ascii=False))
            return
        
        # Красивый вывод результатов
        self.stdout.write(self.style.SUCCESS(f"[OK] Время проверки: {results['timestamp'].strftime('%d.%m.%Y %H:%M')}"))
        self.stdout.write('')
        
        # Битые ссылки
        broken_count = len(results['broken_links'])
        if broken_count > 0:
            self.stdout.write(self.style.ERROR(f'[ERROR] Битые внутренние ссылки: {broken_count}'))
            for link in results['broken_links'][:5]:
                self.stdout.write(f"  • {link['post_title']}")
                self.stdout.write(f"    {link['broken_url']}")
            if broken_count > 5:
                self.stdout.write(f"  ...и ещё {broken_count - 5}")
        else:
            self.stdout.write(self.style.SUCCESS('[OK] Битых ссылок не найдено'))
        
        self.stdout.write('')
        
        # 404 из Яндекса
        yandex_count = len(results['yandex_404s'])
        if yandex_count > 0:
            self.stdout.write(self.style.ERROR(f'[ERROR] 404 ошибки в Яндексе: {yandex_count}'))
            for url in results['yandex_404s'][:5]:
                self.stdout.write(f"  • {url}")
            if yandex_count > 5:
                self.stdout.write(f"  ...и ещё {yandex_count - 5}")
        else:
            self.stdout.write(self.style.SUCCESS('[OK] 404 ошибок в Яндексе не найдено'))
        
        self.stdout.write('')
        
        # Дубли URL
        duplicate_count = results['duplicate_urls']['total_issues']
        if duplicate_count > 0:
            self.stdout.write(self.style.ERROR(f'[ERROR] Дубли URL: {duplicate_count}'))
            
            if results['duplicate_urls']['database_duplicates']:
                self.stdout.write('  Дубли в базе данных:')
                for dup in results['duplicate_urls']['database_duplicates'][:3]:
                    self.stdout.write(f"    • slug: {dup['slug']} ({dup['count']} постов)")
            
            if results['duplicate_urls']['url_duplicates']:
                self.stdout.write('  URL с GET-параметрами:')
                for dup in results['duplicate_urls']['url_duplicates'][:3]:
                    self.stdout.write(f"    • {dup['duplicate_url']}")
        else:
            self.stdout.write(self.style.SUCCESS('[OK] Дублей URL не найдено'))
        
        self.stdout.write('')
        
        # Автоисправления
        auto_fixed_count = len(results['auto_fixed'])
        if auto_fixed_count > 0:
            self.stdout.write(self.style.SUCCESS(f'[OK] Автоматически исправлено: {auto_fixed_count}'))
            for fix in results['auto_fixed'][:5]:
                if 'post' in fix:
                    self.stdout.write(f"  • {fix['post']}")
                elif 'description' in fix:
                    self.stdout.write(f"  • {fix['description']}")
            if auto_fixed_count > 5:
                self.stdout.write(f"  ...и ещё {auto_fixed_count - 5}")
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('[OK] Проверка завершена!'))
        
        # Советы
        if broken_count > 0 or yandex_count > 0 or duplicate_count > 0:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('[INFO] Рекомендации:'))
            if broken_count > 0:
                self.stdout.write('  • Проверьте битые ссылки в админ-панели')
            if yandex_count > 0:
                self.stdout.write('  • Настройте Яндекс Вебмастер API для автоматического удаления')
            if duplicate_count > 0:
                self.stdout.write('  • Убедитесь что robots.txt содержит Clean-param правила')
                self.stdout.write('    python manage.py regenerate_robots')

