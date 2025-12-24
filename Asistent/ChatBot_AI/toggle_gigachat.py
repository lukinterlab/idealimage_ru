#!/usr/bin/env python
"""
Скрипт для включения/выключения GigaChat для чат-бота
Использование: python Asistent/ChatBot_AI/toggle_gigachat.py [on|off]
"""

import os
import sys
import django

# Настройка Django окружения
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'IdealImage_PDJ.settings')
django.setup()

from Asistent.ChatBot_AI.models import ChatbotSettings


def toggle_gigachat(enable=None):
    """Включить/выключить GigaChat для чат-бота"""
    try:
        settings = ChatbotSettings.objects.first()
        
        if not settings:
            print("❌ Настройки чат-бота не найдены!")
            print("Создайте настройки через админку: /admin/ChatBot_AI/chatbotsettings/")
            return
        
        # Текущее состояние
        print("═" * 70)
        print("ТЕКУЩИЕ НАСТРОЙКИ:")
        print("═" * 70)
        print(f"use_ai (GigaChat): {settings.use_ai}")
        print(f"search_articles: {settings.search_articles}")
        print(f"max_search_results: {settings.max_search_results}")
        print()
        
        if enable is None:
            # Интерактивный режим
            current_status = "ВКЛЮЧЕН ✅" if settings.use_ai else "ВЫКЛЮЧЕН ❌"
            print(f"GigaChat сейчас: {current_status}")
            print()
            
            if settings.use_ai:
                answer = input("Выключить GigaChat? (yes/no): ").strip().lower()
                if answer in ['yes', 'y', 'да', 'д']:
                    settings.use_ai = False
                else:
                    print("❌ Отменено")
                    return
            else:
                answer = input("Включить GigaChat? (yes/no): ").strip().lower()
                if answer in ['yes', 'y', 'да', 'д']:
                    settings.use_ai = True
                else:
                    print("❌ Отменено")
                    return
        else:
            # Режим с параметром
            settings.use_ai = enable
        
        settings.save()
        
        print()
        print("═" * 70)
        print("✅ НАСТРОЙКИ ОБНОВЛЕНЫ!")
        print("═" * 70)
        print(f"use_ai (GigaChat): {settings.use_ai}")
        print()
        
        if settings.use_ai:
            print("🤖 GigaChat ВКЛЮЧЕН!")
            print()
            print("Алгоритм работы чат-бота:")
            print("1️⃣ FAQ (keyword + semantic)")
            print("2️⃣ Поиск по статьям")
            print("3️⃣ GigaChat-Max (качественные ответы) ✅")
            print("4️⃣ Fallback (форма связи)")
            print()
            print("⚠️ ВАЖНО: Потребляет токены GigaChat (~1-2₽ за ответ)")
        else:
            print("💤 GigaChat ВЫКЛЮЧЕН!")
            print()
            print("Алгоритм работы чат-бота:")
            print("1️⃣ FAQ (keyword + semantic)")
            print("2️⃣ Поиск по статьям")
            print("3️⃣ ❌ GigaChat отключен (экономия токенов)")
            print("4️⃣ Fallback (форма связи)")
            print()
            print("💰 ЭКОНОМИЯ: Токены GigaChat не расходуются")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ['on', 'enable', 'включить', '1', 'true']:
            toggle_gigachat(True)
        elif arg in ['off', 'disable', 'выключить', '0', 'false']:
            toggle_gigachat(False)
        else:
            print("❌ Неверный параметр!")
            print("Использование: python toggle_gigachat.py [on|off]")
    else:
        # Интерактивный режим
        toggle_gigachat()

