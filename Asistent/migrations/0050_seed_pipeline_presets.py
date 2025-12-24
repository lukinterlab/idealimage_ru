from __future__ import annotations

from django.db import migrations


def create_default_pipelines(apps, schema_editor):
    AutomationPipeline = apps.get_model("Asistent", "AutomationPipeline")
    AISchedule = apps.get_model("Asistent", "AISchedule")

    try:
        import importlib
        importlib.import_module("Asistent.pipeline")
        from Asistent.pipeline.models import validate_pipeline_payload
        from Asistent.pipeline.presets import get_preset
    except Exception:  # pragma: no cover - защитный импорт для миграций
        return

    preset_slugs = ["article-publication-flow", "article-draft-save"]

    for slug in preset_slugs:
        preset = get_preset(slug)
        if not preset:
            continue
        if AutomationPipeline.objects.filter(metadata__preset_slug=slug).exists():
            continue

        raw_payload = {
            "name": preset.get("name", slug.replace("-", " ").title()),
            "slug": "",
            "description": preset.get("description", ""),
            "kind": preset.get("kind", "article"),
            "is_active": True,
            "steps": preset.get("steps", []),
            "triggers": preset.get("triggers", []),
            "actions": preset.get("actions", []),
            "metadata": {
                **preset.get("metadata", {}),
                "preset_slug": slug,
                "auto_seeded": True,
            },
        }

        validated = validate_pipeline_payload(raw_payload)
        AutomationPipeline.objects.create(**validated)

    schedule_name = "Пример: ежедневная проверка публикаций"
    if not AISchedule.objects.filter(name=schedule_name).exists():
        AISchedule.objects.create(
            name=schedule_name,
            strategy_type="system",
            posting_frequency="daily",
            articles_per_run=1,
            is_active=False,
            strategy_options={
                "description": "Демонстрационное расписание для запуска пайплайна публикации статей.",
                "pipeline_slug": "article-publication-flow",
                "note": "Можно включить и связать с AutomationPipeline через триггер расписания.",
            },
        )


def remove_default_pipelines(apps, schema_editor):
    AutomationPipeline = apps.get_model("Asistent", "AutomationPipeline")
    AISchedule = apps.get_model("Asistent", "AISchedule")

    preset_slugs = ["article-publication-flow", "article-draft-save"]
    AutomationPipeline.objects.filter(metadata__preset_slug__in=preset_slugs).delete()
    AISchedule.objects.filter(name="Пример: ежедневная проверка публикаций").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("Asistent", "0049_automationpipeline_pipelinerunlog_and_more"),
    ]

    operations = [
        migrations.RunPython(create_default_pipelines, remove_default_pipelines),
    ]

