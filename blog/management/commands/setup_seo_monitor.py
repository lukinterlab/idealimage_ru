"""
Команда для настройки автоматического SEO мониторинга через Django-Q
"""
from django.core.management.base import BaseCommand
from django_q.models import Schedule


class Command(BaseCommand):
    help = 'Настройка автоматического мониторинга 404 ошибок'
    
    def handle(self, *args, **options):
        # Создаём расписание для SEO мониторинга
        schedule, created = Schedule.objects.get_or_create(
            func='Asistent.seo_monitor.run_seo_404_monitor',
            defaults={
                'name': 'SEO 404 Monitor',
                'schedule_type': Schedule.HOURLY,
                'repeats': -1,  # Бесконечно
                'minutes': 360,  # Каждые 6 часов
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('[OK] SEO мониторинг настроен (каждые 6 часов)'))
        else:
            self.stdout.write(self.style.WARNING('[!] SEO мониторинг уже существует'))
            # Обновляем параметры
            schedule.schedule_type = Schedule.HOURLY
            schedule.minutes = 360
            schedule.repeats = -1
            schedule.save()
            self.stdout.write(self.style.SUCCESS('[OK] SEO мониторинг обновлён'))
        
        self.stdout.write(self.style.SUCCESS('\n[INFO] Следующие шаги:'))
        self.stdout.write('1. Запустите Django-Q кластер: python manage.py qcluster')
        self.stdout.write('2. Настройте переменные окружения в .env:')
        self.stdout.write('   - YANDEX_WEBMASTER_TOKEN')
        self.stdout.write('   - YANDEX_WEBMASTER_USER_ID')
        self.stdout.write('   - YANDEX_WEBMASTER_HOST_ID')
        self.stdout.write('\n3. Или запустите первую проверку вручную:')
        self.stdout.write('   python manage.py check_seo')

