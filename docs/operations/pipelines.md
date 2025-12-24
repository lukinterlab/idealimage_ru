# Мониторинг пайплайнов и расписаний

## 1. Планировщик (cron/Task Scheduler)
Запускайте команду раз в 1015 минут:
`
python manage.py monitor_pipelines --lookback-minutes 180
`
Команда делает следующее:
- смотрит PipelineRunLog и AIScheduleRun за последние N минут;
- если у пайплайна/расписания подряд несколько ailed, шлёт уведомление в Telegram (prefix Pipeline или AI Schedule);
- ищет зависшие unning старше PIPELINE_STALE_RUN_MINUTES и сигналит отдельно;
- повторные алерты блокируются на PIPELINE_ALERT_COOLDOWN_MINUTES.

### Cron-пример
`
*/10 * * * * /home/user/idealimage.ru/.venv/bin/python manage.py monitor_pipelines >> logs/pipeline_health.log 2>&1
`

## 2. Повторный запуск пайплайна
- В карточке расписания и в строке таблицы появилась кнопка Повторить пайплайн (активна, если есть последний PipelineRunLog).
- Кнопка делает POST на sistent:retry_pipeline_run, который дергает un_pipeline_by_slug_task с прежним payload и пишет событие в Telegram.
- Для ручного вызова: POST /asistent/admin-panel/pipeline-runs/<run_id>/retry/ c CSRF токеном.

## 3. Алгоритм реагирования
1. **Уведомление** приходит в админский Telegram (чат CHAT_ID8).
2. Откройте /admin/Asistent/pipelinerunlog/<run_id>/change/ (ссылка в карточке).
3. Нажмите Повторить пайплайн прямо в интерфейсе или вызовите команду python manage.py run_pipeline_by_slug_task ....
4. Если проблема системная (нет токенов, внешний API), временно поставьте расписание на паузу (Остановить).

## 4. Настройки
Все лимиты задаются в .env / settings:
- PIPELINE_FAILURE_ALERT_THRESHOLD (по умолчанию 3);
- PIPELINE_STALE_RUN_MINUTES (45 минут);
- PIPELINE_ALERT_COOLDOWN_MINUTES (60 минут между алертами);
- AISCHEDULE_MAX_ITEMS_PER_HOUR (для предупреждений по нагрузке в интерфейсе).

Измените значения и перезапустите Django/Q кластер. Команда автоматически прочитает новые пороги.
