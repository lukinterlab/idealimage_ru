"""
Проверка импортов для диагностики проблемы "Incomplete response"
"""
import os
import sys
import django

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'IdealImage_PDJ.settings.production')

print("=" * 60)
print("ПРОВЕРКА ИМПОРТОВ")
print("=" * 60)

try:
    print("\n1. Инициализация Django...")
    django.setup()
    print("   ✅ Django инициализирован")
except Exception as e:
    print(f"   ❌ Ошибка Django: {e}")
    sys.exit(1)

try:
    print("\n2. Импорт gigachat_api...")
    from Asistent.gigachat_api import get_gigachat_client
    print("   ✅ gigachat_api импортирован")
except Exception as e:
    print(f"   ❌ Ошибка импорта gigachat_api: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    print("\n3. Импорт generators.universal...")
    from Asistent.generators.universal import UniversalContentGenerator
    print("   ✅ generators.universal импортирован")
except Exception as e:
    print(f"   ❌ Ошибка импорта generators.universal: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    print("\n4. Импорт schedule.tasks...")
    from Asistent.schedule.tasks import run_specific_schedule
    print("   ✅ schedule.tasks импортирован")
except Exception as e:
    print(f"   ❌ Ошибка импорта schedule.tasks: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    print("\n5. Импорт Test_Promot.services...")
    from Asistent.Test_Promot.services import ContentGenerationFactory
    print("   ✅ Test_Promot.services импортирован")
except Exception as e:
    print(f"   ❌ Ошибка импорта Test_Promot.services: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ ВСЕ ИМПОРТЫ УСПЕШНЫ")
print("=" * 60)

