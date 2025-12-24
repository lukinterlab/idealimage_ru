"""
Management command для очистки истории использованных статей
Запуск: python manage.py clear_ai_history <schedule_id>
"""
from django.core.management.base import BaseCommand
from Asistent.models import AISchedule, AIGeneratedArticle  # AISchedule через __getattr__


class Command(BaseCommand):
    help = 'Очищает историю использованных статей для расписания'

    def add_arguments(self, parser):
        parser.add_argument(
            'schedule_id',
            type=int,
            nargs='?',
            help='ID расписания (опционально, без него очистит для всех)'
        )
        
        parser.add_argument(
            '--all',
            action='store_true',
            help='Очистить историю для всех расписаний'
        )

    def handle(self, *args, **options):
        schedule_id = options.get('schedule_id')
        clear_all = options.get('all')
        
        self.stdout.write("=" * 60)
        self.stdout.write("ОЧИСТКА ИСТОРИИ ИСПОЛЬЗОВАННЫХ СТАТЕЙ")
        self.stdout.write("=" * 60)
        
        try:
            if clear_all or schedule_id is None:
                # Очистка для всех расписаний
                self.stdout.write("\n[!] Очистка истории для ВСЕХ расписаний")
                
                total_deleted = 0
                schedules = AISchedule.objects.all()
                
                for schedule in schedules:
                    count = AIGeneratedArticle.objects.filter(schedule=schedule).count()
                    if count > 0:
                        AIGeneratedArticle.objects.filter(schedule=schedule).delete()
                        self.stdout.write(f"[OK] Расписание '{schedule.name}': удалено {count} записей")
                        total_deleted += count
                
                self.stdout.write(self.style.SUCCESS(f"\n[SUCCESS] Всего удалено: {total_deleted} записей"))
                
            else:
                # Очистка для конкретного расписания
                schedule = AISchedule.objects.get(id=schedule_id)
                self.stdout.write(f"\n[OK] Расписание найдено: '{schedule.name}'")
                
                count = AIGeneratedArticle.objects.filter(schedule=schedule).count()
                self.stdout.write(f"[...] Найдено записей в истории: {count}")
                
                if count > 0:
                    AIGeneratedArticle.objects.filter(schedule=schedule).delete()
                    self.stdout.write(self.style.SUCCESS(f"[OK] Удалено записей: {count}"))
                else:
                    self.stdout.write(self.style.WARNING("[INFO] История уже пуста"))
            
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write(self.style.SUCCESS("[SUCCESS] ИСТОРИЯ ОЧИЩЕНА!"))
            self.stdout.write("=" * 60)
            
            self.stdout.write(f"\nТеперь AI будет использовать статьи заново.")
            self.stdout.write(f"Повторы не будут происходить до следующей очистки.")
            
        except AISchedule.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"\n[ERROR] Расписание с ID {schedule_id} не найдено!"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n[ERROR] Ошибка: {str(e)}"))
            import traceback
            self.stdout.write(traceback.format_exc())

