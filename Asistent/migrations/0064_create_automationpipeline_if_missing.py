# Generated manually to fix missing AutomationPipeline table
# This migration creates AutomationPipeline and PipelineRunLog tables if they don't exist

from django.db import migrations


def create_automationpipeline_tables(apps, schema_editor):
    """Создает таблицы AutomationPipeline и PipelineRunLog, если они не существуют"""
    with schema_editor.connection.cursor() as cursor:
        # Проверяем наличие таблицы AutomationPipeline
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'Asistent_automationpipeline'
        """)
        pipeline_exists = cursor.fetchone()[0] > 0
        
        if not pipeline_exists:
            # Создаем таблицу AutomationPipeline
            cursor.execute("""
                CREATE TABLE Asistent_automationpipeline (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(150) NOT NULL,
                    slug VARCHAR(160) UNIQUE,
                    description LONGTEXT NOT NULL,
                    kind VARCHAR(32) NOT NULL DEFAULT 'article',
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    steps JSON,
                    triggers JSON,
                    actions JSON,
                    metadata JSON,
                    created_at DATETIME(6) NOT NULL,
                    updated_at DATETIME(6) NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("Created table Asistent_automationpipeline")
        
        # Проверяем наличие таблицы PipelineRunLog
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'Asistent_pipelinerunlog'
        """)
        runlog_exists = cursor.fetchone()[0] > 0
        
        if not runlog_exists:
            # Создаем таблицу PipelineRunLog
            cursor.execute("""
                CREATE TABLE Asistent_pipelinerunlog (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    status VARCHAR(16) NOT NULL DEFAULT 'pending',
                    payload JSON,
                    result JSON,
                    started_at DATETIME(6) NOT NULL,
                    finished_at DATETIME(6) NULL,
                    error_message LONGTEXT NOT NULL,
                    pipeline_id BIGINT NOT NULL,
                    FOREIGN KEY (pipeline_id) REFERENCES Asistent_automationpipeline(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("Created table Asistent_pipelinerunlog")


def reverse_migration(apps, schema_editor):
    """Откат миграции"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('Asistent', '0063_add_missing_pipeline_fields'),
    ]

    operations = [
        migrations.RunPython(create_automationpipeline_tables, reverse_migration),
    ]

