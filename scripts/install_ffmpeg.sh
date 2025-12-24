#!/bin/bash
# Скрипт установки FFmpeg на сервере
# Использование: bash scripts/install_ffmpeg.sh

# Не прерываем выполнение при ошибках (set -e убран для общих хостингов)

echo "🚀 Установка FFmpeg для обработки видео..."

# Определяем директорию проекта
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN_DIR="$HOME/bin"
FFMPEG_DIR="$PROJECT_DIR/ffmpeg_bin"

# Создаем директорию для бинарников
mkdir -p "$BIN_DIR"
mkdir -p "$FFMPEG_DIR"

cd "$FFMPEG_DIR"

echo "📥 Скачивание FFmpeg..."

# Пробуем разные источники
if [ ! -f "ffmpeg" ]; then
    # Проверяем наличие xz
    HAS_XZ=$(command -v xz || command -v unxz || echo "")
    
    # Вариант 1: GitHub releases (BtbN builds) - tar.gz если нет xz
    echo "Попытка 1: GitHub releases..."
    if [ -n "$HAS_XZ" ]; then
        # Есть xz - используем tar.xz
        if wget -q --spider https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz 2>/dev/null; then
            wget -q https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz || true
            if [ -f "ffmpeg-master-latest-linux64-gpl.tar.xz" ]; then
                tar xf ffmpeg-master-latest-linux64-gpl.tar.xz 2>/dev/null || unxz -c ffmpeg-master-latest-linux64-gpl.tar.xz | tar xf - 2>/dev/null || true
                find . -name ffmpeg -type f -executable | head -1 | xargs -I {} cp {} "$BIN_DIR/ffmpeg" 2>/dev/null || true
                find . -name ffprobe -type f -executable | head -1 | xargs -I {} cp {} "$BIN_DIR/ffprobe" 2>/dev/null || true
            fi
        fi
    else
        # Нет xz - пробуем скачать готовый бинарник напрямую или использовать Python для распаковки
        echo "xz не найден, пробуем альтернативные методы..."
        
        # Вариант 1: Попробовать использовать Python для распаковки (если есть)
        if command -v python3 >/dev/null 2>&1; then
            echo "Попытка распаковки через Python..."
            if wget -q https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz 2>/dev/null; then
                if [ -f "ffmpeg-master-latest-linux64-gpl.tar.xz" ]; then
                    # Используем Python для распаковки
                    python3 << 'PYTHON_SCRIPT'
import tarfile
import lzma
import os

try:
    with lzma.open('ffmpeg-master-latest-linux64-gpl.tar.xz', 'rb') as xz_file:
        with tarfile.open(fileobj=xz_file, mode='r|') as tar:
            tar.extractall()
    print("Распаковка через Python успешна")
except Exception as e:
    print(f"Ошибка распаковки: {e}")
PYTHON_SCRIPT
                    if [ -d "ffmpeg-master-latest-linux64-gpl" ]; then
                        find . -name ffmpeg -type f -executable | head -1 | xargs -I {} cp {} "$BIN_DIR/ffmpeg" 2>/dev/null || true
                        find . -name ffprobe -type f -executable | head -1 | xargs -I {} cp {} "$BIN_DIR/ffprobe" 2>/dev/null || true
                    fi
                fi
            fi
        fi
        
        # Вариант 2: Если Python не помог, сообщаем что нужно обратиться к администратору
        if [ ! -f "$BIN_DIR/ffmpeg" ]; then
            echo "⚠️ Не удалось установить FFmpeg автоматически"
            echo "   На общем хостинге требуется помощь администратора"
            echo "   Или установите FFmpeg вручную в ~/bin"
        fi
    fi
    
    # Вариант 3: Статический бинарник (если есть в проекте)
    if [ ! -f "$BIN_DIR/ffmpeg" ] && [ -f "$PROJECT_DIR/ffmpeg_bin/ffmpeg" ]; then
        echo "Использование локального бинарника..."
        cp "$PROJECT_DIR/ffmpeg_bin/ffmpeg" "$BIN_DIR/ffmpeg"
        cp "$PROJECT_DIR/ffmpeg_bin/ffprobe" "$BIN_DIR/ffprobe" 2>/dev/null || true
    fi
fi

# Делаем исполняемыми
if [ -f "$BIN_DIR/ffmpeg" ]; then
    chmod +x "$BIN_DIR/ffmpeg" "$BIN_DIR/ffprobe" 2>/dev/null || true
    
    # Добавляем в PATH
    if ! echo "$PATH" | grep -q "$BIN_DIR"; then
        echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$HOME/.bashrc"
        export PATH="$BIN_DIR:$PATH"
    fi
    
    echo "✅ FFmpeg установлен в $BIN_DIR"
    "$BIN_DIR/ffmpeg" -version | head -1
else
    echo "❌ Не удалось установить FFmpeg автоматически"
    echo ""
    echo "📝 Ручная установка:"
    echo "   1. Установите xz: yum install xz || apt-get install xz-utils"
    echo "   2. Или скачайте готовый бинарник:"
    echo "      cd ~/bin"
    echo "      wget https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz"
    echo "      tar xf ffmpeg-master-latest-linux64-gpl.tar.xz"
    echo "      mv ffmpeg-*/bin/ffmpeg ~/bin/"
    echo "      mv ffmpeg-*/bin/ffprobe ~/bin/"
    echo "      chmod +x ~/bin/ffmpeg ~/bin/ffprobe"
    echo "      export PATH=\$HOME/bin:\$PATH"
    echo ""
    echo "⚠️ Видео будут работать без автоматической оптимизации"
    echo "   Можно обработать позже после установки FFmpeg"
    exit 0  # Не критичная ошибка, продолжаем работу
fi

echo "✅ Готово! FFmpeg установлен и готов к использованию"

