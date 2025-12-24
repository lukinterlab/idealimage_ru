from django.db import migrations


ADD_COLUMN_SQL = """
ALTER TABLE Asistent_prompttemplate
ADD COLUMN IF NOT EXISTS debug_script longtext NULL;
"""

DROP_COLUMN_SQL = """
ALTER TABLE Asistent_prompttemplate
DROP COLUMN IF EXISTS debug_script;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("Asistent", "0044_add_daily_horoscope_prompt"),
    ]

    operations = [
        migrations.RunSQL(
            sql=ADD_COLUMN_SQL,
            reverse_sql=DROP_COLUMN_SQL,
        ),
    ]

