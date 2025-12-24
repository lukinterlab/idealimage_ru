from __future__ import annotations

from django.db import migrations


def update_publication_pipeline(apps, validate_payload, get_preset):
    AutomationPipeline = apps.get_model("Asistent", "AutomationPipeline")

    preset = get_preset("article-publication-flow")
    if not preset:
        return

    try:
        pipeline = AutomationPipeline.objects.get(metadata__preset_slug="article-publication-flow")
    except AutomationPipeline.DoesNotExist:
        return

    raw_payload = {
        "name": pipeline.name,
        "slug": pipeline.slug,
        "description": pipeline.description,
        "kind": pipeline.kind,
        "is_active": pipeline.is_active,
        "steps": pipeline.steps,
        "triggers": pipeline.triggers,
        "actions": preset["actions"],
        "metadata": pipeline.metadata,
    }
    validated = validate_payload(raw_payload)
    for field, value in validated.items():
        setattr(pipeline, field, value)
    pipeline.save()


def ensure_ai_assist_pipeline(apps, validate_payload, get_preset):
    AutomationPipeline = apps.get_model("Asistent", "AutomationPipeline")

    if AutomationPipeline.objects.filter(metadata__preset_slug="article-ai-assist-flow").exists():
        return

    preset = get_preset("article-ai-assist-flow")
    if not preset:
        return

    raw_payload = {
        "name": preset.get("name", "AI Assist Flow"),
        "slug": preset.get("slug", ""),
        "description": preset.get("description", ""),
        "kind": preset.get("kind", "article"),
        "is_active": True,
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


def ensure_seo_pipeline(apps, validate_payload, get_preset):
    AutomationPipeline = apps.get_model("Asistent", "AutomationPipeline")

    if AutomationPipeline.objects.filter(metadata__preset_slug="seo-recrawl-flow").exists():
        return

    preset = get_preset("seo-recrawl-flow")
    if not preset:
        return

    raw_payload = {
        "name": preset.get("name", "SEO Recrawl Flow"),
        "slug": preset.get("slug", ""),
        "description": preset.get("description", ""),
        "kind": preset.get("kind", "seo"),
        "is_active": True,
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


def ensure_donations_pipeline(apps, validate_payload, get_preset):
    AutomationPipeline = apps.get_model("Asistent", "AutomationPipeline")
def ensure_distribution_pipeline(apps, validate_payload, get_preset):
    AutomationPipeline = apps.get_model("Asistent", "AutomationPipeline")

    if AutomationPipeline.objects.filter(metadata__preset_slug="distribution-flow").exists():
        return

    preset = get_preset("distribution-flow")
    if not preset:
        return

    raw_payload = {
        "name": preset.get("name", "Distribution Flow"),
        "slug": preset.get("slug", ""),
        "description": preset.get("description", ""),
        "kind": preset.get("kind", "distribution"),
        "is_active": True,
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


    if AutomationPipeline.objects.filter(metadata__preset_slug="donations-report-flow").exists():
        return

    preset = get_preset("donations-report-flow")
    if not preset:
        return

    raw_payload = {
        "name": preset.get("name", "Donations Report Flow"),
        "slug": preset.get("slug", ""),
        "description": preset.get("description", ""),
        "kind": preset.get("kind", "donations"),
        "is_active": True,
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

    update_publication_pipeline(apps, validate_pipeline_payload, get_preset)
    ensure_ai_assist_pipeline(apps, validate_pipeline_payload, get_preset)
    ensure_seo_pipeline(apps, validate_pipeline_payload, get_preset)
    ensure_donations_pipeline(apps, validate_pipeline_payload, get_preset)
    ensure_distribution_pipeline(apps, validate_pipeline_payload, get_preset)
    ensure_seo_pipeline(apps, validate_pipeline_payload, get_preset)


def backwards(apps, schema_editor):
    AutomationPipeline = apps.get_model("Asistent", "AutomationPipeline")
    AutomationPipeline.objects.filter(metadata__preset_slug="article-ai-assist-flow").delete()
    AutomationPipeline.objects.filter(metadata__preset_slug="seo-recrawl-flow").delete()
    AutomationPipeline.objects.filter(metadata__preset_slug="donations-report-flow").delete()
    AutomationPipeline.objects.filter(metadata__preset_slug="distribution-flow").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("Asistent", "0050_seed_pipeline_presets"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]

