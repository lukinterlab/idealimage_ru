"""
Команда для сброса статистики ошибок GigaChat
Использование: python manage.py reset_gigachat_errors [--model MODEL_NAME] [--all]
"""
from django.core.management.base import BaseCommand
from Asistent.models import GigaChatUsageStats
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Сбрасывает статистику ошибок (failed_requests) для GigaChat моделей"

    def add_arguments(self, parser):
        parser.add_argument(
            '--model',
            type=str,
            help='Название модели для сброса (GigaChat, GigaChat-Pro, GigaChat-Max)',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Сбросить ошибки для всех моделей',
        )

    def handle(self, *args, **options):
        model_name = options.get('model')
        reset_all = options.get('all', False)

        if not model_name and not reset_all:
            self.stdout.write(
                self.style.ERROR('❌ Укажите --model MODEL_NAME или --all для сброса всех моделей')
            )
            return

        if reset_all:
            stats = GigaChatUsageStats.objects.all()
            self.stdout.write(self.style.WARNING('⚠️ Сброс ошибок для ВСЕХ моделей...'))
        else:
            try:
                stats = [GigaChatUsageStats.objects.get(model_name=model_name)]
                self.stdout.write(self.style.WARNING(f'⚠️ Сброс ошибок для модели: {model_name}'))
            except GigaChatUsageStats.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'❌ Модель {model_name} не найдена в статистике')
                )
                return

        reset_count = 0
        for stat in stats:
            old_failed = stat.failed_requests
            stat.failed_requests = 0
            stat.save(update_fields=['failed_requests'])
            reset_count += 1
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ {stat.model_name}: сброшено {old_failed} ошибок '
                    f'(было: {stat.total_requests} запросов, {old_failed} ошибок)'
                )
            )
            logger.info(f"Сброшена статистика ошибок для {stat.model_name}: {old_failed} → 0")

        self.stdout.write(
            self.style.SUCCESS(f'\n🎉 Успешно сброшено ошибок для {reset_count} моделей!')
        )
        self.stdout.write(
            self.style.WARNING(
                '\n💡 Теперь новые ошибки будут считаться правильно:\n'
                '   - 402 с автопереключением = НЕ ошибка\n'
                '   - 429 с retry = НЕ ошибка\n'
                '   - Только реальные неустранимые ошибки = ошибка'
            )
        )

