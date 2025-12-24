#!/bin/bash
# Скрипт проверки и перезапуска qcluster (для cron)

PROJECT_DIR="/home/users/j/j7642490/domains/idealimage.ru"
PID_FILE="$PROJECT_DIR/qcluster.pid"
PYTHON="$PROJECT_DIR/.venv/python311/bin/python"
LOG_FILE="$PROJECT_DIR/logs/qcluster.log"

cd $PROJECT_DIR

# Проверяем запущен ли qcluster
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        # Процесс работает
        exit 0
    else
        # PID файл есть, но процесс умер - перезапускаем
        rm -f "$PID_FILE"
    fi
fi

# Запускаем qcluster
mkdir -p "$PROJECT_DIR/logs"
nohup $PYTHON manage.py qcluster >> "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"

echo "[$(date)] qcluster перезапущен (PID: $!)" >> "$LOG_FILE"
