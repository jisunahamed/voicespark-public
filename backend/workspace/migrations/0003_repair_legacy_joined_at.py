from django.db import migrations


def repair_legacy_joined_at(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'workspace_membership'
                  AND column_name = 'joined_at'
            ) THEN
                UPDATE workspace_membership
                SET joined_at = now()
                WHERE joined_at IS NULL;

                ALTER TABLE workspace_membership
                ALTER COLUMN joined_at SET DEFAULT now();
            END IF;
        END $$;
    """)


class Migration(migrations.Migration):

    dependencies = [
        ('workspace', '0002_repair_timestamp_columns'),
    ]

    operations = [
        migrations.RunPython(repair_legacy_joined_at, migrations.RunPython.noop),
    ]
