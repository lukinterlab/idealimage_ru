#!/bin/bash
# Скрипт остановки qcluster

PROJECT_DIR="/home/users/j/j7642490/domains/idealimage.ru"
PID_FILE="$PROJECT_DIR/qcluster.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo "Останавливаем qcluster (PID: $PID)..."
        kill $PID
        rm -f "$PID_FILE"
        echo "qcluster остановлен"
    else
        echo "Процесс с PID $PID не найден"
        rm -f "$PID_FILE"
    fi
else
    echo "PID файл не найден. qcluster не запущен?"
fi
