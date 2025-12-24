"""
Запуск расписания #1 - 🔮 Автопостинг всех гороскопов (8:00)
Для запуска на сервере: python scripts/run_horoscopes_server.py
"""
import os
import sys
import django

# Настройка Django
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'IdealImage_PDJ.settings.production')
django.setup()

from Asistent.schedule.tasks import run_specific_schedule
from Asistent.schedule.models import AISchedule

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 ЗАПУСК РАСПИСАНИЯ #1 - 🔮 Автопостинг всех гороскопов")
    print("=" * 60)
    
    # Ищем расписание #1
    try:
        schedule = AISchedule.objects.get(id=1)
    except AISchedule.DoesNotExist:
        print("❌ Расписание #1 не найдено!")
        sys.exit(1)
    
    # Активируем если неактивно
    if not schedule.is_active:
        schedule.is_active = True
        schedule.save(update_fields=['is_active'])
        print("✅ Расписание активировано")
    
    print(f"\n📋 Расписание: {schedule.name}")
    print(f"   ID: {schedule.id}")
    print(f"   Статей за запуск: {schedule.articles_per_run}")
    print(f"\n🚀 Запуск генерации...")
    print(f"   Это может занять ~4-5 минут (12 гороскопов × ~20с)\n")
    
    # Запускаем
    result = run_specific_schedule(schedule.id)
    
    # Результаты
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ")
    print("=" * 60)
    print(f"   Успешно: {result.get('success', False)}")
    print(f"   Создано постов: {len(result.get('created_posts', []))}")
    
    if result.get('created_posts'):
        print(f"\n   ✅ Созданные гороскопы:")
        for post in result.get('created_posts', [])[:12]:
            print(f"      - {post.title}")
    
    if result.get('errors'):
        print(f"\n   ⚠️ Ошибки ({len(result.get('errors', []))}):")
        for error in result.get('errors', [])[:5]:
            print(f"      - {error}")
    
    if result.get('success'):
        print("\n✅ Автопостинг завершен успешно!")
    else:
        print(f"\n❌ Завершилось с ошибками: {result.get('error', 'Неизвестная ошибка')}")

