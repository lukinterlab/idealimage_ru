"""
Простой запуск автопостинга гороскопов через Django shell
"""
import os
import sys

# Команда для выполнения
command = """
from Asistent.schedule.tasks import run_specific_schedule
from Asistent.schedule.models import AISchedule
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ищем расписание гороскопов
schedule = AISchedule.objects.filter(
    name__icontains='гороскоп',
    strategy='horoscope'
).first()

if not schedule:
    schedule = AISchedule.objects.get(id=1)

if not schedule.is_active:
    schedule.is_active = True
    schedule.save()

print(f"🚀 Запуск расписания: {schedule.name} (ID={schedule.id})")
print(f"   Статей за запуск: {schedule.articles_per_run}")
print(f"   Это займет ~4-5 минут...\\n")

result = run_specific_schedule(schedule.id)

print(f"\\n✅ Результат:")
print(f"   Успешно: {result.get('success', False)}")
print(f"   Создано: {len(result.get('created_posts', []))}")

if result.get('created_posts'):
    print(f"\\n   Созданные гороскопы:")
    for post in result.get('created_posts', [])[:12]:
        print(f"      - {post.title}")

if result.get('errors'):
    print(f"\\n   Ошибки ({len(result.get('errors', []))}):")
    for error in result.get('errors', [])[:5]:
        print(f"      - {error}")
"""

# Запуск через manage.py shell
os.system(f'python manage.py shell -c "{command}"')

