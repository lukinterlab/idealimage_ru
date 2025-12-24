#!/bin/bash
# Полный запуск runserver + проверка qcluster

PROJECT_DIR="/home/users/j/j7642490/domains/idealimage.ru"
PYTHON="$PROJECT_DIR/.venv/python311/bin/python"
RUN_PID_FILE="$PROJECT_DIR/runserver.pid"
RUN_LOG="$PROJECT_DIR/logs/runserver.daemon.log"

cd "$PROJECT_DIR" || exit 1

echo "=== Остановка старых процессов ==="
if [ -x "$PROJECT_DIR/scripts/stop_runserver.sh" ]; then
    "$PROJECT_DIR/scripts/stop_runserver.sh" >/dev/null 2>&1
fi
if [ -x "$PROJECT_DIR/scripts/stop_qcluster.sh" ]; then
    "$PROJECT_DIR/scripts/stop_qcluster.sh" >/dev/null 2>&1
fi

mkdir -p "$PROJECT_DIR/logs"

echo "=== Запуск runserver (--noreload) ==="
nohup "$PYTHON" manage.py runserver --noreload 0.0.0.0:8000 >> "$RUN_LOG" 2>&1 &
RUN_PID=$!
echo $RUN_PID > "$RUN_PID_FILE"
echo "runserver запущен (PID: $RUN_PID), лог: $RUN_LOG"

sleep 5

echo "=== Проверка qcluster через health-check ==="
if "$PYTHON" manage.py monitor_djangoq --no-restart >/dev/null 2>&1; then
    echo "Django-Q уже активен (автозапуск runserver)"
else
    echo "Django-Q не запущен, пытаемся стартовать..."
    "$PROJECT_DIR/scripts/start_qcluster.sh"
fi

echo "Готово."

