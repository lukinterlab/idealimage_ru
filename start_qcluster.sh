#!/bin/bash
# Скрипт автозапуска qcluster для shared hosting

# Путь к проекту
PROJECT_DIR="/home/users/j/j7642490/domains/idealimage.ru"
cd $PROJECT_DIR

# Путь к Python виртуального окружения
PYTHON="$PROJECT_DIR/.venv/python311/bin/python"

# Проверяем запущен ли qcluster
PID_FILE="$PROJECT_DIR/qcluster.pid"
LOG_FILE="$PROJECT_DIR/logs/qcluster.log"

# Функция очистки зомби-процессов
cleanup_zombie_processes() {
    # Находим ВСЕ процессы qcluster текущего пользователя
    ALL_PIDS=$(ps aux | grep "[p]ython manage.py qcluster" | awk '{print $2}')
    
    if [ -z "$ALL_PIDS" ]; then
        return 0  # Нет процессов - всё ок
    fi
    
    # Читаем легитимный PID из файла
    VALID_PID=""
    if [ -f "$PID_FILE" ]; then
        VALID_PID=$(cat "$PID_FILE")
    fi
    
    # Убиваем все процессы КРОМЕ легитимного
    ZOMBIE_COUNT=0
    for pid in $ALL_PIDS; do
        if [ "$pid" != "$VALID_PID" ]; then
            echo "Убиваем зомби-процесс: $pid"
            kill $pid 2>/dev/null
            ZOMBIE_COUNT=$((ZOMBIE_COUNT + 1))
        fi
    done
    
    if [ $ZOMBIE_COUNT -gt 0 ]; then
        echo "Найдено и убито зомби-процессов: $ZOMBIE_COUNT"
        # Даём время на завершение
        sleep 2
        
        # Жёсткое убийство если не помогло
        for pid in $ALL_PIDS; do
            if [ "$pid" != "$VALID_PID" ] && ps -p $pid > /dev/null 2>&1; then
                echo "Жёсткое убийство зомби: $pid"
                kill -9 $pid 2>/dev/null
            fi
        done
    fi
}

# СНАЧАЛА очищаем зомби-процессы
echo "Проверка зомби-процессов..."
cleanup_zombie_processes

# Проверяем существует ли ЛЕГИТИМНЫЙ процесс
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo "qcluster уже запущен (PID: $PID)"
        exit 0
    else
        echo "Старый PID файл найден, но процесс не запущен. Удаляем..."
        rm -f "$PID_FILE"
    fi
fi

# Создаем папку для логов если её нет
mkdir -p "$PROJECT_DIR/logs"

# Запускаем qcluster в фоновом режиме
# Логи пишутся через Django logging (автоматическая ротация в settings.py)
echo "Запуск qcluster..."
nohup $PYTHON manage.py qcluster > /dev/null 2>&1 &

# Сохраняем PID
echo $! > "$PID_FILE"

echo "qcluster запущен (PID: $!)"
echo "Логи: $LOG_FILE"

