"""
Management команда для отображения статистики GigaChat
Использование: python manage.py gigachat_stats
"""
from django.core.management.base import BaseCommand
from Asistent.models import GigaChatUsageStats, GigaChatSettings
from Asistent.gigachat_api import MODEL_TOKEN_LIMITS
from decimal import Decimal


class Command(BaseCommand):
    help = 'Отображает детальную статистику использования GigaChat'

    def add_arguments(self, parser):
        parser.add_argument(
            '--model',
            type=str,
            help='Фильтр по конкретной модели (GigaChat, GigaChat-Pro, GigaChat-Max, GigaChat-Embeddings)'
        )
        parser.add_argument(
            '--cost',
            action='store_true',
            help='Показать расчет стоимости'
        )

    def handle(self, *args, **options):
        model_filter = options.get('model')
        show_cost = options.get('cost')
        
        self.stdout.write(self.style.WARNING('📊 СТАТИСТИКА GIGACHAT'))
        self.stdout.write(self.style.WARNING('=' * 80))
        self.stdout.write('')
        
        # Получаем настройки для цен
        settings = GigaChatSettings.objects.first()
        prices = {
            'GigaChat-Embeddings': settings.price_embeddings if settings else Decimal('40.00'),
            'GigaChat': settings.price_lite if settings else Decimal('194.00'),
            'GigaChat-Pro': settings.price_pro if settings else Decimal('1500.00'),
            'GigaChat-Max': settings.price_max if settings else Decimal('1950.00'),
        }
        
        # Получаем статистику
        stats_qs = GigaChatUsageStats.objects.all()
        
        if model_filter:
            stats_qs = stats_qs.filter(model_name=model_filter)
        
        if not stats_qs.exists():
            self.stdout.write(self.style.ERROR('Статистика не найдена'))
            return
        
        # Показываем статистику по каждой модели
        total_requests = 0
        total_success = 0
        total_failures = 0
        total_cost = Decimal('0.00')
        
        for stats in stats_qs:
            limit = MODEL_TOKEN_LIMITS.get(stats.model_name, 1000000)
            percent = (stats.tokens_remaining / limit * 100) if stats.tokens_remaining else 0
            
            # Определяем статус
            if percent >= 50:
                status_color = self.style.SUCCESS
                status = '✅ ХОРОШО'
            elif percent >= 20:
                status_color = self.style.WARNING
                status = '⚠️ НИЗКИЙ'
            else:
                status_color = self.style.ERROR
                status = '🔴 КРИТИЧЕСКИЙ'
            
            self.stdout.write(self.style.HTTP_INFO(f'🤖 {stats.model_name}'))
            self.stdout.write('-' * 80)
            
            self.stdout.write(f'  Баланс: {stats.tokens_remaining:,} / {limit:,} токенов ({percent:.1f}%)')
            self.stdout.write(status_color(f'  Статус: {status}'))
            self.stdout.write(f'  Всего запросов: {stats.total_requests}')
            self.stdout.write(f'  Успешных: {stats.successful_requests} ({stats.success_rate:.1f}%)')
            self.stdout.write(f'  Ошибок: {stats.failed_requests}')
            
            # Расчет стоимости если запрошено
            if show_cost:
                tokens_used = limit - stats.tokens_remaining if stats.tokens_remaining else 0
                price_per_million = prices.get(stats.model_name, Decimal('1000.00'))
                cost = (Decimal(str(tokens_used)) / Decimal('1000000')) * price_per_million
                
                self.stdout.write(self.style.WARNING(f'  Использовано токенов: {tokens_used:,}'))
                self.stdout.write(self.style.WARNING(f'  Стоимость: {float(cost):.2f} ₽'))
                
                total_cost += cost
            
            # Дополнительная статистика
            if stats.tokens_used_today > 0:
                self.stdout.write(f'  Использовано сегодня: {stats.tokens_used_today:,} токенов')
            
            if stats.cost_today > 0:
                self.stdout.write(f'  Расходы сегодня: {float(stats.cost_today):.2f} ₽')
            
            self.stdout.write('')
            
            # Агрегируем
            total_requests += stats.total_requests
            total_success += stats.successful_requests
            total_failures += stats.failed_requests
        
        # Итоговая статистика
        self.stdout.write(self.style.WARNING('ИТОГО:'))
        self.stdout.write('-' * 80)
        self.stdout.write(f'  Всего запросов: {total_requests}')
        self.stdout.write(f'  Успешных: {total_success}')
        self.stdout.write(f'  Ошибок: {total_failures}')
        
        if show_cost and total_cost > 0:
            self.stdout.write(self.style.WARNING(f'  Общая стоимость: {float(total_cost):.2f} ₽'))
        
        self.stdout.write('')
        
        # Текущая активная модель
        if settings:
            self.stdout.write(self.style.HTTP_INFO(f'🎯 Активная модель: {settings.current_model}'))
            self.stdout.write(f'   Автопереключение: {"включено" if settings.auto_switch_enabled else "выключено"}')
            self.stdout.write('')

