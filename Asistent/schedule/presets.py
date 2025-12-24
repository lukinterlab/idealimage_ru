from __future__ import annotations

from typing import Any, Dict, List


AI_SCHEDULE_PRESETS: List[Dict[str, Any]] = [
    {
        "id": "daily_horoscope",
        "title": "Ежедневные гороскопы",
        "description": "Генерация 12 гороскопов с изображениями каждое утро.",
        "pipeline_slug": "daily-horoscope-flow",
        "schedule_kind": "daily",
        "scheduled_time": "08:00",
        "cron_expression": "0 8 * * *",
        "posting_frequency": "daily",
        "articles_per_run": 12,
        "interval_minutes": None,
        "weekday": None,
        "max_runs": None,
        "tags": "гороскопы, прогнозы",
        "payload_template": {
            "publish_mode": "draft",
            "generate_image": True,
            "include_push": False,
        },
    },
    {
        "id": "nightly_seo_refresh",
        "title": "Ночная SEO‑переиндексация",
        "description": "Запуск SEO‑пайплайна для опубликованных статей каждую ночь.",
        "pipeline_slug": "article-seo-flow",
        "schedule_kind": "cron",
        "scheduled_time": None,
        "cron_expression": "0 3 * * *",
        "posting_frequency": "daily",
        "articles_per_run": 4,
        "interval_minutes": None,
        "weekday": None,
        "max_runs": None,
        "tags": "seo, оптимизация",
        "payload_template": {
            "mode": "nightly-refresh",
            "max_posts": 4,
        },
    },
    {
        "id": "distribution_followup",
        "title": "Дистрибуция статей по соцсетям",
        "description": "Каждый час запускает пайплайн рассылки свежих постов.",
        "pipeline_slug": "distribution-flow",
        "schedule_kind": "interval",
        "scheduled_time": None,
        "cron_expression": "",
        "posting_frequency": "daily",
        "articles_per_run": 3,
        "interval_minutes": 60,
        "weekday": None,
        "max_runs": None,
        "tags": "smm, рассылка",
        "payload_template": {
            "channels": ["telegram", "vk", "dzen"],
            "min_post_age_minutes": 30,
        },
    },
]

