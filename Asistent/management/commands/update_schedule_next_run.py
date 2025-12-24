"""
Команда для обновления next_run всех активных расписаний
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from Asistent.models import AISchedule


class Command(BaseCommand):
    help = 'Обновляет next_run для всех активных расписаний используя правильный расчёт'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать, какие изменения будут внесены, без фактического сохранения.'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('  🔄 ОБНОВЛЕНИЕ NEXT_RUN ДЛЯ РАСПИСАНИЙ'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        
        active_schedules = AISchedule.objects.filter(is_active=True)
        count = active_schedules.count()
        
        self.stdout.write(f'📋 Найдено активных расписаний: {count}')
        self.stdout.write('')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 РЕЖИМ ПРОСМОТРА (dry-run):'))
            for schedule in active_schedules:
                old_next_run = schedule.next_run
                new_next_run = schedule.calculate_next_run()
                
                self.stdout.write(f'\n  - {schedule.name} (ID: {schedule.id})')
                self.stdout.write(f'    Старый next_run: {old_next_run.strftime("%d.%m.%Y %H:%M") if old_next_run else "Не установлен"}')
                self.stdout.write(f'    Новый next_run: {new_next_run.strftime("%d.%m.%Y %H:%M") if new_next_run else "Не установлен"}')
                if schedule.schedule_kind == 'cron' and schedule.cron_expression:
                    self.stdout.write(f'    CRON: {schedule.cron_expression}')
            self.stdout.write(f'\nБудет обновлено: {count} расписаний')
        else:
            updated_count = 0
            for schedule in active_schedules:
                old_next_run = schedule.next_run
                schedule.update_next_run(commit=False)
                new_next_run = schedule.next_run
                
                if old_next_run != new_next_run:
                    schedule.save(update_fields=['next_run'])
                    updated_count += 1
                    self.stdout.write(self.style.SUCCESS(
                        f'  ✓ {schedule.name} (ID: {schedule.id}): '
                        f'{old_next_run.strftime("%d.%m.%Y %H:%M") if old_next_run else "Не установлен"} → '
                        f'{new_next_run.strftime("%d.%m.%Y %H:%M") if new_next_run else "Не установлен"}'
                    ))
                else:
                    self.stdout.write(
                        f'  - {schedule.name} (ID: {schedule.id}): без изменений'
                    )
            
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS(f'✅ Обновлено расписаний: {updated_count}'))
            self.stdout.write(self.style.SUCCESS('\n🎉 Обновление завершено!'))
            self.stdout.write(self.style.WARNING('\n💡 Рекомендация: Запустите sync_schedules для синхронизации с Django-Q'))
        
        self.stdout.write('')

