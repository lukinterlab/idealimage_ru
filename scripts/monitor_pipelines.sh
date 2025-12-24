#!/bin/bash
# Cron helper: мониторинг пайплайнов и AI-расписаний

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python}"
LOG_DIR="$PROJECT_DIR/logs"
QUEUE_THRESHOLD="${PIPELINE_QUEUE_THRESHOLD:-180}"

mkdir -p "$LOG_DIR"
cd "$PROJECT_DIR" || exit 1

$PYTHON_BIN manage.py monitor_pipelines --lookback-minutes 180 >> "$LOG_DIR/pipelines_health.log" 2>&1

