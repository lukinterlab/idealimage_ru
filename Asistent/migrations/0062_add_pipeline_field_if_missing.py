# Generated manually to fix missing pipeline_id column
# This migration adds only the pipeline field if it doesn't exist

from django.db import migrations


def check_and_add_pipeline_field(apps, schema_editor):
    """Проверяет наличие полей pipeline и добавляет их, если отсутствуют"""
    fields_to_add = [
        ('pipeline_id', 'BIGINT NULL'),
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
        
        # Пытаемся добавить внешний ключ для pipeline_id, если его еще нет
        if not exists:
            try:
                cursor.execute("""
                    ALTER TABLE Asistent_aischedule 
                    ADD CONSTRAINT Asistent_aischedule_pipeline_id_fk 
                    FOREIGN KEY (pipeline_id) REFERENCES Asistent_automationpipeline(id) 
                    ON DELETE SET NULL
                """)
            except Exception as e:
                # Если внешний ключ не создался, это не критично
                print(f"Warning: Could not create foreign key: {e}")


def reverse_migration(apps, schema_editor):
    """Откат миграции"""
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            ALTER TABLE Asistent_aischedule 
            DROP FOREIGN KEY Asistent_aischedule_pipeline_id_fk,
            DROP COLUMN pipeline_id
        """)


class Migration(migrations.Migration):

    dependencies = [
        ('Asistent', '0061_create_priority_horoscope_schedule'),
    ]

    operations = [
        migrations.RunPython(check_and_add_pipeline_field, reverse_migration),
    ]

