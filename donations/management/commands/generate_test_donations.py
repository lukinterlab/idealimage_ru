"""
Management команда для генерации тестовых донатов
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
import random
import uuid

from donations.models import Donation
from blog.models import Post


class Command(BaseCommand):
    help = 'Генерация тестовых донатов для проверки системы бонусов'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=50,
            help='Количество донатов для генерации'
        )
        parser.add_argument(
            '--weeks',
            type=int,
            default=4,
            help='За сколько недель назад генерировать'
        )

    def handle(self, *args, **options):
        count = options['count']
        weeks = options['weeks']
        
        self.stdout.write(self.style.SUCCESS(f'Генерация {count} тестовых донатов за {weeks} недель...'))
        
        # Получаем опубликованные статьи с авторами
        articles = list(Post.objects.filter(status='published').select_related('author'))
        
        if not articles:
            self.stdout.write(self.style.ERROR('Нет опубликованных статей для генерации донатов'))
            return
        
        # Генерируем донаты
        donations_created = 0
        
        for i in range(count):
            # Случайная статья
            article = random.choice(articles)
            
            # Случайная дата в пределах указанных недель
            days_ago = random.randint(0, weeks * 7)
            completed_at = timezone.now() - timedelta(days=days_ago, hours=random.randint(0, 23))
            
            # Случайная сумма
            amounts = [100, 200, 500, 1000, 2000, 5000]
            amount = Decimal(str(random.choice(amounts)))
            
            # Случайный метод оплаты
            payment_methods = ['yandex', 'sberpay', 'sbp']
            payment_method = random.choice(payment_methods)
            
            # Случайное имя донатера
            donor_names = [
                'Анна Иванова', 'Мария Петрова', 'Елена Сидорова',
                'Ольга Смирнова', 'Татьяна Кузнецова', 'Наталья Попова',
                'Анонимный донатер'
            ]
            donor_name = random.choice(donor_names)
            is_anonymous = donor_name == 'Анонимный донатер'
            
            # Создаем донат
            donation = Donation.objects.create(
                id=uuid.uuid4(),
                user_email=f'test{i}@example.com',
                user_name=donor_name if not is_anonymous else '',
                amount=amount,
                currency='RUB',
                payment_method=payment_method,
                status='succeeded',
                payment_id=f'test_{uuid.uuid4().hex[:16]}',
                is_anonymous=is_anonymous,
                created_at=completed_at - timedelta(minutes=5),
                completed_at=completed_at,
                article=article,
                article_author=article.author,
                message='Тестовый донат для проверки системы' if random.random() > 0.7 else ''
            )
            
            donations_created += 1
            
            if (i + 1) % 10 == 0:
                self.stdout.write(f'  Создано {i + 1} донатов...')
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'[OK] Создано {donations_created} тестовых донатов'))
        
        # Статистика по авторам
        from django.db.models import Sum, Count
        
        author_stats = Donation.objects.filter(
            status='succeeded',
            article_author__isnull=False
        ).values(
            'article_author__username'
        ).annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')[:10]
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Топ-10 авторов по донатам:'))
        for stat in author_stats:
            self.stdout.write(f"  • {stat['article_author__username']}: {stat['total']}₽ ({stat['count']} донатов)")
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Теперь можно протестировать систему бонусов:'))
        self.stdout.write('  1. Зайдите в /donations/admin/bonuses/')
        self.stdout.write('  2. Нажмите кнопку "Создать отчет"')
        self.stdout.write('  3. Проверьте начисление бонусов авторам')

