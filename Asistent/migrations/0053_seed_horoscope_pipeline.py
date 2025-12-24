from __future__ import annotations

from django.db import migrations


def ensure_horoscope_pipeline(apps, validate_payload, get_preset):
    AutomationPipeline = apps.get_model("Asistent", "AutomationPipeline")

    if AutomationPipeline.objects.filter(metadata__preset_slug="daily-horoscope-flow").exists():
        return

    preset = get_preset("daily-horoscope-flow")
    if not preset:
        return

    raw_payload = {
        "name": preset.get("name", "Ежедневные гороскопы"),
        "slug": preset.get("slug", "daily-horoscope-flow"),
        "description": preset.get("description", ""),
        "kind": preset.get("kind", "horoscope"),
        "is_active": False,  # включим после тестов
        "steps": preset.get("steps", []),
        "triggers": preset.get("triggers", []),
        "actions": preset.get("actions", []),
        "metadata": {
            **preset.get("metadata", {}),
            "preset_slug": preset["slug"],
            "auto_seeded": True,
        },
    }
    validated = validate_payload(raw_payload)
    AutomationPipeline.objects.create(**validated)


def forwards(apps, schema_editor):
    try:
        import importlib

        importlib.import_module("Asistent.pipeline")
        from Asistent.pipeline.models import validate_pipeline_payload
        from Asistent.pipeline.presets import get_preset
    except Exception:
        return

    ensure_horoscope_pipeline(apps, validate_pipeline_payload, get_preset)


def backwards(apps, schema_editor):
    AutomationPipeline = apps.get_model("Asistent", "AutomationPipeline")
    AutomationPipeline.objects.filter(metadata__preset_slug="daily-horoscope-flow").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("Asistent", "0052_update_horoscope_prompts"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]

