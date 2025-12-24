# Generated manually to fix missing pipeline fields
# This migration adds pipeline_slug, payload_template, schedule_kind, cron_expression, interval_minutes, weekday

from django.db import migrations


def add_missing_fields(apps, schema_editor):
    """Добавляет недостающие поля pipeline"""
    fields_to_add = [
        ('pipeline_slug', 'VARCHAR(160) NOT NULL DEFAULT ""'),
        ('payload_template', 'JSON'),
        ('schedule_kind', 'VARCHAR(16) NOT NULL DEFAULT "daily"'),
        ('cron_expression', 'VARCHAR(120) NOT NULL DEFAULT ""'),
        ('interval_minutes', 'INT NULL'),
        ('weekday', 'INT NULL'),
    ]
    
    with schema_editor.connection.cursor() as cursor:
        for field_name, field_type in fields_to_add:
            # Проверяем наличие столбца
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'Asistent_aischedule' 
                AND COLUMN_NAME = %s
            """, (field_name,))
            exists = cursor.fetchone()[0] > 0
            
            if not exists:
                # Добавляем столбец
                try:
                    cursor.execute(f"""
                        ALTER TABLE Asistent_aischedule 
                        ADD COLUMN {field_name} {field_type}
                    """)
                    print(f"Added column {field_name}")
                except Exception as e:
                    print(f"Warning: Could not add column {field_name}: {e}")


def reverse_migration(apps, schema_editor):
    """Откат миграции"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('Asistent', '0062_add_pipeline_field_if_missing'),
    ]

    operations = [
        migrations.RunPython(add_missing_fields, reverse_migration),
    ]

