"""
Management команда для генерации рекомендаций AI
"""
from django.core.management.base import BaseCommand
from advertising.ml_optimizer import AdPlacementOptimizer


class Command(BaseCommand):
    help = 'Сгенерировать рекомендации AI по размещению рекламы'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--top',
            type=int,
            default=10,
            help='Количество рекомендаций (по умолчанию: 10)'
        )
    
    def handle(self, *args, **options):
        top_n = options['top']
        
        self.stdout.write(self.style.WARNING(f'Генерация {top_n} рекомендаций...'))
        
        optimizer = AdPlacementOptimizer()
        
        # Генерируем рекомендации
        count = optimizer.generate_recommendations(top_n=top_n)
        
        if count > 0:
            self.stdout.write(self.style.SUCCESS(f'[OK] Создано рекомендаций: {count}'))
        else:
            self.stdout.write(self.style.ERROR('Рекомендации не созданы'))

