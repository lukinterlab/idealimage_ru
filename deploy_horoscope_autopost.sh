#!/bin/bash
# Скрипт для деплоя автопостинга гороскопов на сервер
# Использование: ./deploy_horoscope_autopost.sh

cd /home/users/j/j7642490/domains/idealimage.ru

# Активация виртуального окружения
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
elif [ -f .venv/python311/bin/activate ]; then
    source .venv/python311/bin/activate
else
    echo "⚠️ Виртуальное окружение не найдено, продолжаю без активации..."
fi

echo "======================================================================"
echo "  🔮 НАСТРОЙКА АВТОПОСТИНГА ГОРОСКОПОВ"
echo "======================================================================"
echo ""

# 1. Проверка пайплайна
echo "1️⃣ Проверка пайплайна daily-horoscope-flow..."
python manage.py ensure_horoscope_pipeline
if [ $? -ne 0 ]; then
    echo "❌ Ошибка при проверке пайплайна!"
    exit 1
fi
echo ""

# 2. Создание расписаний
echo "2️⃣ Создание расписаний автопостинга..."
python manage.py setup_horoscope_interval
if [ $? -ne 0 ]; then
    echo "❌ Ошибка при создании расписаний!"
    exit 1
fi
echo ""

# 3. Синхронизация с Django-Q
echo "3️⃣ Синхронизация расписаний с Django-Q..."
python manage.py sync_schedules --force
if [ $? -ne 0 ]; then
    echo "❌ Ошибка при синхронизации!"
    exit 1
fi
echo ""

# 4. Проверка Django-Q
echo "4️⃣ Проверка статуса Django-Q..."
if pgrep -f "python.*qcluster" > /dev/null; then
    echo "✅ Django-Q уже запущен"
    QCLUSTER_PID=$(pgrep -f "python.*qcluster")
    echo "   PID: $QCLUSTER_PID"
else
    echo "⚠️ Django-Q не запущен, запускаю..."
    python manage.py qcluster >> logs/qcluster.log 2>&1 &
    sleep 3
    
    if pgrep -f "python.*qcluster" > /dev/null; then
        QCLUSTER_PID=$(pgrep -f "python.*qcluster")
        echo "✅ Django-Q успешно запущен (PID: $QCLUSTER_PID)"
    else
        echo "❌ Не удалось запустить Django-Q!"
        echo "   Попробуйте запустить вручную: python manage.py qcluster"
        exit 1
    fi
fi
echo ""

# 5. Финальная проверка
echo "5️⃣ Финальная проверка..."
echo "   Проверка расписаний в базе данных:"
python manage.py shell << EOF
from Asistent.models import AISchedule
from Asistent.pipeline.models import AutomationPipeline

schedules = AISchedule.objects.filter(name__contains='Автопостинг гороскопов')
print(f"   📋 Всего расписаний: {schedules.count()}")
print(f"   ✅ Активных: {schedules.filter(is_active=True).count()}")

pipeline = AutomationPipeline.objects.filter(slug='daily-horoscope-flow').first()
if pipeline:
    print(f"   🔧 Пайплайн: {pipeline.name} (активен: {pipeline.is_active})")
else:
    print("   ❌ Пайплайн не найден!")
EOF

echo ""
echo "======================================================================"
echo "  ✅ ДЕПЛОЙ ЗАВЕРШЁН!"
echo "======================================================================"
echo ""
echo "📋 Проверьте расписания:"
echo "   - Django-Q: /admin/django_q/schedule/"
echo "   - AISchedule: /admin/Asistent/aischedule/"
echo ""
echo "📊 Логи Django-Q:"
echo "   tail -f logs/qcluster.log"
echo ""
echo "⏰ Первый запуск будет завтра в 8:00"
echo ""

