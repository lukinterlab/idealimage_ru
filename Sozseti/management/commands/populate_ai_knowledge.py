"""
Management команда для добавления знаний о соцсетях в AIKnowledgeBase
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from Asistent.models import AIKnowledgeBase


class Command(BaseCommand):
    help = 'Добавляет базовые знания о социальных сетях в AIKnowledgeBase'
    
    def handle(self, *args, **options):
        self.stdout.write('[*] Добавление знаний о соцсетях в AIKnowledgeBase...')
        
        # Получаем админа
        admin = User.objects.filter(is_superuser=True).first()
        
        if not admin:
            self.stdout.write(
                self.style.ERROR('[ERROR] Не найден суперпользователь')
            )
            return
        
        knowledge_entries = [
            {
                'category': 'инструкции',
                'title': 'Публикация в Telegram каналы',
                'content': '''
Для публикации статьи в Telegram каналы:

1. Через команду:
   python manage.py test_social_publish <POST_ID> --platforms telegram

2. Через админку:
   /admin/Sozseti/postpublication/ → Добавить публикацию

3. Автоматически:
   - Включите "Автопубликация в соцсетях" в статье
   - Статус = "Опубликовано"
   - Django-Q автоматически опубликует

AI умно выбирает каналы на основе категории статьи.

У нас 18 Telegram каналов:
- @ideal_image_ru (главный)
- @fizkult_hello_beauty (красота)
- @the_best_hairstyles (прически)
- @Fashion_Couture_ru (мода)
- ... и другие
''',
                'tags': ['telegram', 'публикация', 'каналы'],
                'priority': 90,
            },
            {
                'category': 'правила',
                'title': 'Правила постинга в соцсетях',
                'content': '''
Telegram:
- Максимум 4096 символов
- HTML форматирование
- Эмодзи приветствуются
- Хештеги в конце

VK:
- Максимум 16384 символа
- Хештеги обязательны
- Изображения повышают охват

Pinterest:
- Обязательно изображение
- Описание 100-500 символов
- Ключевые слова важны для поиска

Rutube:
- Ориентация на видео
- Краткое описание
- Ссылка на полную статью

Яндекс.Дзен:
- Полноценная статья или анонс
- Изображения минимум 1200×675px
- Качественный контент для дочитываний
''',
                'tags': ['правила', 'соцсети', 'форматирование'],
                'priority': 85,
            },
            {
                'category': 'команды',
                'title': 'Команды для управления соцсетями',
                'content': '''
Доступные команды:

1. Инициализация:
   python manage.py init_social_platforms

2. Синхронизация Telegram:
   python manage.py sync_telegram_channels

3. Тестовая публикация:
   python manage.py test_social_publish <POST_ID>

4. Полная настройка:
   python manage.py setup_sozseti --with-demo

5. Демо-расписания:
   python manage.py create_demo_schedules

6. Добавление знаний:
   python manage.py populate_ai_knowledge
''',
                'tags': ['команды', 'управление'],
                'priority': 80,
            },
            {
                'category': 'примеры',
                'title': 'Примеры использования AI для соцсетей',
                'content': '''
Python API:

from Sozseti.ai_agent.social_agent import SocialMediaAgent

agent = SocialMediaAgent()

# Умное распределение
distribution = agent.distribute_post(post, strategy='auto')

# Оптимизация времени
optimal_time = agent.optimize_posting_time(channel, post)

# Адаптация контента
telegram_text = agent.generate_post_content(post, 'telegram')
vk_text = agent.generate_post_content(post, 'vk')

# Анализ канала
suggestions = agent.suggest_improvements(channel)

# Планирование рекламы
campaign = agent.plan_ad_campaign(budget=10000, goal='subscribers')
''',
                'tags': ['примеры', 'ai', 'api'],
                'priority': 75,
            },
        ]
        
        created = 0
        
        for entry_data in knowledge_entries:
            entry, is_created = AIKnowledgeBase.objects.get_or_create(
                category=entry_data['category'],
                title=entry_data['title'],
                defaults={
                    'content': entry_data['content'],
                    'tags': entry_data['tags'],
                    'priority': entry_data['priority'],
                    'is_active': True,
                    'created_by': admin,
                }
            )
            
            if is_created:
                created += 1
                self.stdout.write(f'  [+] Добавлено: {entry.title}')
        
        self.stdout.write(
            self.style.SUCCESS(f'\n[OK] Добавлено {created} записей в базу знаний')
        )
        
        if created > 0:
            self.stdout.write('\nТеперь AI-агент может использовать эти знания')
            self.stdout.write('Проверить: /admin/Asistent/aiknowledgebase/')

