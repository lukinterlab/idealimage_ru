#!/bin/bash
# Полная настройка оптимизации видео на сервере
# Использование: bash scripts/setup_video_optimization.sh

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "🚀 Настройка оптимизации видео для IdealImage.ru"
echo "================================================"

# 1. Установка FFmpeg
echo ""
echo "📦 Шаг 1: Установка FFmpeg..."
if bash scripts/install_ffmpeg.sh; then
    FFMPEG_INSTALLED=$?
    if [ $FFMPEG_INSTALLED -eq 0 ]; then
        # Проверяем что FFmpeg действительно установлен
        if command -v ffmpeg >/dev/null 2>&1; then
            echo "✅ FFmpeg установлен"
        else
            echo "⚠️ FFmpeg не установлен, но работа продолжится без оптимизации"
        fi
    else
        echo "⚠️ FFmpeg не установлен, но работа продолжится без оптимизации"
    fi
else
    echo "⚠️ FFmpeg не установлен, но работа продолжится без оптимизации"
fi

# 2. Применение миграций
echo ""
echo "📦 Шаг 2: Применение миграций..."
python manage.py migrate blog

# 3. Проверка установки
echo ""
echo "📦 Шаг 3: Проверка установки..."
python manage.py check

# 4. Проверка FFmpeg через Python
echo ""
echo "📦 Шаг 4: Проверка FFmpeg..."
python << EOF
import subprocess
import sys

try:
    result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        print("✅ FFmpeg доступен:")
        print(result.stdout.split('\n')[0])
    else:
        print("⚠️ FFmpeg не найден в PATH")
        sys.exit(1)
except FileNotFoundError:
    print("❌ FFmpeg не установлен")
    print("   Видео будут загружаться без автоматической оптимизации")
    sys.exit(1)
except Exception as e:
    print(f"⚠️ Ошибка проверки FFmpeg: {e}")
    sys.exit(1)
EOF

FFMPEG_STATUS=$?

# 5. Оптимизация существующих видео (опционально)
if [ $FFMPEG_STATUS -eq 0 ]; then
    echo ""
    echo "📦 Шаг 5: Оптимизация существующих видео..."
    read -p "Обработать все существующие видео? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Запуск оптимизации в фоне..."
        nohup python manage.py optimize_existing_videos > logs/video_optimization.log 2>&1 &
        echo "✅ Оптимизация запущена в фоне"
        echo "   Логи: tail -f logs/video_optimization.log"
    else
        echo "⏭️ Пропущено. Запустите позже: python manage.py optimize_existing_videos"
    fi
else
    echo ""
    echo "⏭️ Шаг 5 пропущен (FFmpeg не установлен)"
fi

echo ""
echo "================================================"
echo "✅ Настройка завершена!"
echo ""
echo "📝 Следующие шаги:"
echo "   1. Проверьте работу: загрузите видео в админке"
echo "   2. Проверьте логи: tail -f logs/django.log"
echo "   3. Оптимизируйте существующие видео:"
echo "      python manage.py optimize_existing_videos"
echo ""

