"""
Management команда для обучения ML модели
"""
from django.core.management.base import BaseCommand
from advertising.ml_optimizer import AdPlacementOptimizer


class Command(BaseCommand):
    help = 'Обучить ML модель для оптимизации размещения рекламы'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Количество дней данных для обучения (по умолчанию: 90)'
        )
    
    def handle(self, *args, **options):
        days = options['days']
        
        self.stdout.write(self.style.WARNING(f'Начинаем обучение ML модели на данных за {days} дней...'))
        
        optimizer = AdPlacementOptimizer()
        
        # Собираем данные
        data = optimizer.collect_training_data(days=days)
        
        if data is None or len(data) < 100:
            self.stdout.write(self.style.ERROR('Недостаточно данных для обучения'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Собрано {len(data)} записей'))
        
        # Обучаем модель CTR
        self.stdout.write('Обучение модели предсказания CTR...')
        ctr_metrics = optimizer.train_ctr_model()
        
        if 'error' in ctr_metrics:
            self.stdout.write(self.style.ERROR(f'Ошибка: {ctr_metrics["error"]}'))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'Модель CTR обучена: MAE={ctr_metrics["mae"]:.4f}, R²={ctr_metrics["r2"]:.4f}'
            ))
        
        # Обучаем модель revenue
        self.stdout.write('Обучение модели предсказания дохода...')
        revenue_metrics = optimizer.train_revenue_model()
        
        if 'error' in revenue_metrics:
            self.stdout.write(self.style.ERROR(f'Ошибка: {revenue_metrics["error"]}'))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'Модель revenue обучена: MAE={revenue_metrics["mae"]:.4f}, R²={revenue_metrics["r2"]:.4f}'
            ))
        
        self.stdout.write(self.style.SUCCESS('[OK] Обучение завершено!'))

