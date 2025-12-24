# Generated manually to add foreign key for pipeline_id
# This migration adds foreign key constraint if it doesn't exist

from django.db import migrations


def add_pipeline_foreign_key(apps, schema_editor):
    """Добавляет внешний ключ для pipeline_id, если его нет"""
    with schema_editor.connection.cursor() as cursor:
        # Проверяем наличие внешнего ключа
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.KEY_COLUMN_USAGE 
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'Asistent_aischedule' 
            AND COLUMN_NAME = 'pipeline_id'
            AND REFERENCED_TABLE_NAME = 'Asistent_automationpipeline'
        """)
        fk_exists = cursor.fetchone()[0] > 0
        
        if not fk_exists:
            try:
                cursor.execute("""
                    ALTER TABLE Asistent_aischedule 
                    ADD CONSTRAINT Asistent_aischedule_pipeline_id_fk 
                    FOREIGN KEY (pipeline_id) REFERENCES Asistent_automationpipeline(id) 
                    ON DELETE SET NULL
                """)
                print("Added foreign key constraint for pipeline_id")
            except Exception as e:
                print(f"Warning: Could not create foreign key: {e}")


def reverse_migration(apps, schema_editor):
    """Откат миграции"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('Asistent', '0064_create_automationpipeline_if_missing'),
    ]

    operations = [
        migrations.RunPython(add_pipeline_foreign_key, reverse_migration),
    ]

