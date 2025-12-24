from django.db import migrations


def _convert_charset(connection, charset, collate):
    if connection.settings_dict.get("ENGINE") != "django.db.backends.mysql":
        return

    database_name = connection.settings_dict.get("NAME")
    if not database_name:
        return

    with connection.cursor() as cursor:
        cursor.execute(
            f"ALTER DATABASE `{database_name}` CHARACTER SET {charset} COLLATE {collate};"
        )

        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s
            """,
            [database_name],
        )
        tables = [row[0] for row in cursor.fetchall()]

        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        try:
            for table_name in tables:
                cursor.execute(
                    f"ALTER TABLE `{table_name}` "
                    f"CONVERT TO CHARACTER SET {charset} COLLATE {collate};"
                )
        finally:
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")


def convert_to_utf8mb4(apps, schema_editor):
    _convert_charset(schema_editor.connection, "utf8mb4", "utf8mb4_unicode_ci")


def revert_to_utf8(apps, schema_editor):
    _convert_charset(schema_editor.connection, "utf8", "utf8_general_ci")


class Migration(migrations.Migration):

    dependencies = [
        ("Asistent", "0042_seed_prompt_templates"),
    ]

    operations = [
        migrations.RunPython(convert_to_utf8mb4, revert_to_utf8),
    ]

