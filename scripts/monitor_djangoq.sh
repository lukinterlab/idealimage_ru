#!/bin/bash
# Health-check wrapper for Django-Q. Запланируйте через cron каждые 5 минут.

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python}"
QUEUE_THRESHOLD="${QUEUE_THRESHOLD:-200}"
LOG_DIR="$PROJECT_DIR/logs"

mkdir -p "$LOG_DIR"
cd "$PROJECT_DIR" || exit 1

# Тихая проверка (без перезапуска). Если всё хорошо — просто выходим.
$PYTHON_BIN manage.py monitor_djangoq --no-restart --queue-threshold "$QUEUE_THRESHOLD" >> "$LOG_DIR/djangoq_health.log" 2>&1
STATUS=$?
if [ $STATUS -eq 0 ]; then
  exit 0
fi

# Повторный запуск уже с попыткой перезапуска воркера.
$PYTHON_BIN manage.py monitor_djangoq --queue-threshold "$QUEUE_THRESHOLD" >> "$LOG_DIR/djangoq_health.log" 2>&1
exit $?

