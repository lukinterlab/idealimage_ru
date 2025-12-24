#!/bin/bash
# Cron helper: резервная копия БД

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python}"
LOG_DIR="$PROJECT_DIR/logs"
RETENTION_DAYS="${DB_BACKUP_RETENTION:-14}"

mkdir -p "$LOG_DIR"
cd "$PROJECT_DIR" || exit 1

$PYTHON_BIN manage.py backup_database --retention-days "$RETENTION_DAYS" >> "$LOG_DIR/backup_database.log" 2>&1

