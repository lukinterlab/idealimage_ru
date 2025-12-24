"""
Команда для проверки и создания пайплайна daily-horoscope-flow
"""
from django.core.management.base import BaseCommand
from Asistent.pipeline.models import AutomationPipeline, validate_pipeline_payload
from Asistent.pipeline.presets import get_preset
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Проверка и создание пайплайна daily-horoscope-flow если его нет'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Пересоздать пайплайн даже если он уже существует'
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('  🔮 ПРОВЕРКА ПАЙПЛАЙНА ГОРОСКОПОВ'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        
        # Проверяем существование пайплайна
        pipeline = AutomationPipeline.objects.filter(
            slug="daily-horoscope-flow"
        ).first()
        
        if pipeline and not force:
            self.stdout.write(self.style.SUCCESS(
                f'✅ Пайплайн уже существует: {pipeline.name}'
            ))
            self.stdout.write(f'   Slug: {pipeline.slug}')
            self.stdout.write(f'   Активен: {pipeline.is_active}')
            self.stdout.write(f'   Шагов: {len(pipeline.steps)}')
            return
        
        # Получаем preset
        preset = get_preset("daily-horoscope-flow")
        if not preset:
            self.stdout.write(self.style.ERROR(
                '❌ Preset "daily-horoscope-flow" не найден!'
            ))
            return
        
        # Удаляем старый пайплайн если force
        if pipeline and force:
            pipeline.delete()
            self.stdout.write(self.style.WARNING(
                '🗑️ Старый пайплайн удалён'
            ))
        
        # Создаём новый пайплайн
        raw_payload = {
            "name": preset.get("name", "Ежедневные гороскопы"),
            "slug": preset.get("slug", "daily-horoscope-flow"),
            "description": preset.get("description", ""),
            "kind": preset.get("kind", "automation"),
            "is_active": True,  # Активируем сразу
            "steps": preset.get("steps", []),
            "triggers": preset.get("triggers", []),
            "actions": preset.get("actions", []),
            "metadata": {
                **preset.get("metadata", {}),
                "preset_slug": preset["slug"],
                "auto_seeded": True,
            },
        }
        
        try:
            validated = validate_pipeline_payload(raw_payload)
            pipeline = AutomationPipeline.objects.create(**validated)
            
            self.stdout.write(self.style.SUCCESS(
                f'✅ Пайплайн создан: {pipeline.name}'
            ))
            self.stdout.write(f'   Slug: {pipeline.slug}')
            self.stdout.write(f'   Активен: {pipeline.is_active}')
            self.stdout.write(f'   Шагов: {len(pipeline.steps)}')
            self.stdout.write(f'   Шаги: {", ".join([s.get("code") for s in pipeline.steps])}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f'❌ Ошибка создания пайплайна: {e}'
            ))
            logger.error(f"Ошибка создания пайплайна: {e}", exc_info=True)
            return
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('  ✅ ПРОВЕРКА ЗАВЕРШЕНА'))
        self.stdout.write(self.style.SUCCESS('=' * 70))

